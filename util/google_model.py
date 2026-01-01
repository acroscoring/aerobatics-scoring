#import streamlit as st
from streamlit import cache_resource, secrets, context
import requests
import gspread
from typing import Optional, cast, Literal, Any, List
from pydantic import BaseModel, EmailStr, HttpUrl
from google import genai
from PIL import Image
import util.controller as controller
import util.data_model as dm
import util.security_model as sec

# --------------------------------------------------------------------------------------------------------------

class CreateCompetition(BaseModel):
    comp_name: str
    admin_email: EmailStr
    bot_email: EmailStr
    app_url: HttpUrl
    api_secret: str

class CreateCompetitionResponse(BaseModel):
    status: Literal["Success", "Error"]
    message: Optional[str] = None
    sheet_id: Optional[str] = None
    comp_url: Optional[HttpUrl] = None

class DatabaseConnectionError(Exception):
    pass

class AiConnectionError(Exception):
    pass

class UserAlreadyExistsError(Exception):
    pass

class UserEmailNotFound(Exception):
    pass

class UserInvalidAuth(Exception):
    pass

# --------------------------------------------------------------------------------------------------------------

@cache_resource(show_spinner="Getting Connection...", show_time=True)
def _get_gspread_client(creds_dict: dict[str, Any]) -> gspread.Client:
    try:
        return gspread.service_account_from_dict(creds_dict)
    except Exception as e:
        raise DatabaseConnectionError(f"Bot Authentication Failed: {e}")
        

@cache_resource(show_spinner="Getting DB...", show_time=True)
def _get_sheet_by_id(sheet_id: str) -> gspread.spreadsheet.Spreadsheet:
    try:
        creds_dict = dict(secrets["gcp_service_account"])
        gspread_client = _get_gspread_client(creds_dict)
        return gspread_client.open_by_key(sheet_id)
    except KeyError as e:
        raise DatabaseConnectionError(f"Missing Bot Secret Configuration: {e}")
    except Exception as e:
        raise DatabaseConnectionError(f"Failed to open competition sheet (DB): {e}")

@cache_resource(show_spinner="Getting AI Connection...", show_time=True)
def _get_genai_client(api_key: str):
    try:
        return genai.Client(api_key=api_key)
    except Exception as e:
        raise AiConnectionError(f"AI Authentication Failed: {e}")

# --------------------------------------------------------------------------------------------------------------



# --------------------------------------------------------------------------------------------------------------

class SheetDB:
    """
    Singleton service to handle Google Sheets interactions securely.
    Usage: db = SheetDB.connect("your_sheet_id_here")
    """
    def __init__(self, sheet_id: str):
        try:
            self._sheet = _get_sheet_by_id(sheet_id)
            if not self._sheet:
                raise DatabaseConnectionError(f"Competition not found ({sheet_id})")

            self.title = self._sheet.title
            self._users_ws = self._sheet.worksheet("Users")
            self._users_headers = self._users_ws.row_values(1)
            if not self._users_headers:
                raise DatabaseConnectionError("Users tab headers row missing")
            
            self._judges_ws = self._sheet.worksheet("Judges")
            self._judges_headers = self._users_ws.row_values(1)
            if not self._judges_headers:
                raise DatabaseConnectionError("Judges tab headers row missing")

            self.id = sheet_id
        except Exception as e:
            raise DatabaseConnectionError(f"Error getting sheet (DB) details: {e}")
    
    @classmethod
    def connect(cls, sheet_id: str) -> "SheetDB":
        session_key = f"SheetDB_{sheet_id}"
        return controller.get_session_state_singleton(session_key, lambda: cls(sheet_id))
    
    @classmethod
    def create(cls, comp_name: str, admin_email: str) -> "SheetDB":
        try:
            if not context.url:
                raise Exception(f"Error getting context URL.")

            payload = CreateCompetition(
                comp_name = comp_name,
                admin_email = admin_email,
                bot_email = secrets["gcp_service_account"]["client_email"],
                app_url = HttpUrl(context.url), # no query parameters
                api_secret = secrets["google_app_script"]["api_secret"]
            )
            
            api_url: str = secrets["google_app_script"]["prod_url"] if secrets["env"]["type"] == "prod" else secrets["google_app_script"]["dev_url"]
            response = requests.post(api_url, json=payload.model_dump(mode='json'))
            
            if response.status_code != 200:
                raise DatabaseConnectionError(f"HTTP Error: {response.status_code} - {response.text}")
        
            result = CreateCompetitionResponse(**response.json())
            
            if result.status != "Success":
                raise DatabaseConnectionError(f"Create Competition Apps Script Error: {result.message}")
            
            if not result.sheet_id:
                raise DatabaseConnectionError(f"Sheet (DB) ID Error")
            
            return SheetDB.connect(result.sheet_id)
        except KeyError as e:
            raise DatabaseConnectionError(f"Missing API URL Secret Configuration: {e}")
        except Exception as e:
            raise DatabaseConnectionError(f"Failed to create competition sheet (DB): {e}")
    
    def get_all_users(self) -> List[dm.User]:
        try:
            records = self._users_ws.get_all_records()
            users = [dm.User.from_sheet_record(r) for r in records]
            return users
        except Exception as e:
            raise Exception(f"Error fetching users: {e}")
    
    def get_user_by_email(self, email: str) -> dm.User:
        email = email.lower().strip()
        users = self.get_all_users()
        user = next((u for u in users if u.email == email), None)
        if user:
            return user

        raise UserEmailNotFound(f"User {email} not found in sheet (DB)")

    def register_user(self, user: dm.User):
        try:
            self.get_user_by_email(user.email)
            raise UserAlreadyExistsError(f"Email {user.email} already exists.")
        except UserEmailNotFound:
            try:
                row_data = user.to_sheet_row(self._users_headers)
                self._users_ws.append_row(row_data)
            except Exception as e:
                raise Exception(f"Register user error: {e}")

    def authenticate_user(self, email: str, password: str) -> dm.User:
        try:
            user = self.get_user_by_email(email)
            if user and sec.verify_password(password, user.password):
                return user
            
            raise UserInvalidAuth("Invalid password")
        except UserEmailNotFound:
            raise UserInvalidAuth("Invalid email")
        except Exception as e:
            raise Exception(f"Auth user error: {e}")

    def update_user_password(self, email: str, new_password: str):
        try:
            password_col = self._users_headers.index("password") + 1
            cell = self._users_ws.find(email, in_column=password_col) # type: ignore
            if not cell:
                raise Exception("User not found to update password")
            
            hashed_pw = sec.hash_password(new_password)
            self._users_ws.update_cell(cell.row, cell.col, hashed_pw)
        except Exception as e:
            raise Exception(f"Password update error: {e}")
    
    def save_scoring_sheet_data(self, score_data: dm.ScoreSheet):
        #to do
        pass    

    def get_all_judges(self) -> List[dm.Judge]:
        try:
            records = self._judges_ws.get_all_records()
            judges = [dm.Judge.from_sheet_record(r) for r in records]
            return judges
        except Exception as e:
            raise Exception(f"Error fetching judges: {e}")

    def get_judge_details(self, judge_id: int) -> dm.Judge:
        all_judges = self.get_all_judges()    
        judge = next((j for j in all_judges if j.id == judge_id), None)

        if judge is None:
            raise Exception(f"Judge with ID {judge_id} not found in sheet (DB)")

        return judge
    
    def get_scoring_sheet_data_using_ai(self, image: Image.Image) -> dm.ScoreSheet:
        try:
            api_key: str = secrets["google_gemini"]["api_key"]
            genai_client = _get_genai_client(api_key)
            prompt = "Extract the data from this aerobatics score sheet. Return 0 for missing values."
            response = genai_client.models.generate_content(
                model=secrets["google_gemini"]["model"],
                contents=[
                    image,  # Image 1st
                    prompt  # Prompt 2nd as per Google best practice https://ai.google.dev/gemini-api/docs/image-understanding#tips-best-practices
                ],
                config={
                    "response_mime_type": "application/json",
                    "response_schema": dm.ScoreSheet,
                },
            )
            return cast(dm.ScoreSheet, response.parsed)
        except KeyError as e:
            raise Exception(f"Missing AI Secret Configuration: {e}")
        except Exception as e:
            raise Exception(f"AI getting score error: {e}")