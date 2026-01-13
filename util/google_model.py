#import streamlit as st
from streamlit import cache_resource, secrets, context
import requests
import gspread
from typing import cast, Literal, Any, List, Tuple, Dict
from pydantic import BaseModel, EmailStr, HttpUrl
from google import genai
from PIL import Image
from util.streamlit_model import get_session_state_singleton
import util.data_model as dm
import util.security_model as sec
from gspread_dataframe import set_with_dataframe, get_as_dataframe # type: ignore
import pandas as pd
import util.constants as const


# --------------------------------------------------------------------------------------------------------------

class CompetitionPayload(BaseModel):
    comp_name: str
    admin_email: EmailStr
    bot_email: EmailStr
    app_url: HttpUrl

class EmailPayload(BaseModel):
    recipient: str
    copy_to: str
    subject: str
    htmlBody: str


class CompetitionRequest(BaseModel):
    api_name: Literal["CREATE_COMPETITION"]
    api_secret: str
    payload: CompetitionPayload

class EmailRequest(BaseModel):
    api_name: Literal["SEND_EMAIL"]
    api_secret: str
    payload: EmailPayload


class CompetitionResponse(BaseModel):
    status: Literal["Success", "Error"]
    message: str | None = None
    sheet_id: str | None = None

class EmailResponse(BaseModel):
    status: Literal["Success", "Error"]
    message: str | None = None


class DatabaseConnectionError(Exception):
    pass

class AiConnectionError(Exception):
    pass

class UserAlreadyExistsError(Exception):
    pass

class UserEmailNotFound(Exception):
    pass

class UserRoleAndIdNotFound(Exception):
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
    
def _get_google_app_script_url() -> str:
    return secrets["google_app_script"]["prod_url"] if secrets["env"]["type"] == "prod" else secrets["google_app_script"]["dev_url"]

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
            self._users_ws = self._sheet.worksheet(const.DBTabs.USERS)
            self._users_headers = self._users_ws.row_values(1)
            if not self._users_headers:
                raise DatabaseConnectionError("Users tab headers row missing")
            
            self._judges_ws = self._sheet.worksheet(const.DBTabs.JUDGES)
            self._judges_headers = self._judges_ws.row_values(1)
            if not self._judges_headers:
                raise DatabaseConnectionError("Judges tab headers row missing")

            self.id = sheet_id
        except Exception as e:
            raise DatabaseConnectionError(f"Error getting sheet (DB) details: {e}")
    
    @classmethod
    def connect(cls, sheet_id: str) -> "SheetDB":
        session_key = f"SheetDB_{sheet_id}"
        return get_session_state_singleton(session_key, lambda: cls(sheet_id))
    
    @classmethod
    def create(cls, comp_name: str, admin_email: str) -> "SheetDB":
        try:
            if not context.url:
                raise Exception(f"Error getting context URL.")

            payload = CompetitionPayload(
                comp_name = comp_name,
                admin_email = admin_email,
                bot_email = secrets["gcp_service_account"]["client_email"],
                app_url = HttpUrl(context.url),
            )

            api_request = CompetitionRequest(
                api_name="CREATE_COMPETITION",
                api_secret = secrets["google_app_script"]["api_secret"],
                payload=payload
            )
            
            api_url: str = _get_google_app_script_url()
            response = requests.post(api_url, json=api_request.model_dump(mode='json'))
            
            if response.status_code != 200:
                raise DatabaseConnectionError(f"HTTP Error: {response.status_code} - {response.text}")
        
            result = CompetitionResponse(**response.json())
            
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
    
    def get_user_by_role_and_id(self, role: dm.RoleType, id: int) -> dm.User:
        users = self.get_all_users()
        user = next((u for u in users if u.role == role and u.id == id), None)
        if user:
            return user

        raise UserRoleAndIdNotFound(f"User with role {role} and ID {id} not found in sheet (DB)")

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
            
    def _delete_user_row(self, email: str):
        try:
            email_col = self._users_headers.index("email") + 1
            cell = self._users_ws.find(email, in_column=email_col) # type: ignore
            if cell:
                self._users_ws.delete_rows(cell.row)
        except Exception as e:
            raise Exception(f"Failed to delete user row: {e}")
        
    def update_admin_user_id(self, email: str, new_id: int):
        try:
            email_col = self._users_headers.index("email") + 1
            cell = self._users_ws.find(email, in_column=email_col) # type: ignore
            if cell:
                id_col = self._users_headers.index("id") + 1
                self._users_ws.update_cell(cell.row, id_col, new_id)
        except Exception as e:
            raise Exception(f"Failed to link Admin user {email} to Judge ID {new_id}: {e}")

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
        
    def update_tab_from_df(self, tab_name: str, df: pd.DataFrame) -> Tuple[bool, str]:
        try:
            ws = self._sheet.worksheet(tab_name)
            ws.clear()
            # Write headers and data
            set_with_dataframe(ws, df) 
            return True, f"Updated {tab_name} with {len(df)} rows."
        except Exception as e:
            return False, f"Error updating {tab_name}: {str(e)}"
    
    def get_table_df(self, tab_name: str) -> pd.DataFrame:
        try:
            ws = self._sheet.worksheet(tab_name)
            return get_as_dataframe(ws) # type: ignore
        except Exception as e:
            raise Exception(f"Error getting tab {tab_name}: {str(e)}")
    
    def upsert_mark(self, mark: dm.AcroMark) -> Tuple[bool, str]:
        try:
            ws = self._sheet.worksheet(const.DBTabs.MARKS)

            # "Blank Sheet"
            model_data = mark.model_dump()
            headers = list(model_data.keys())
            values = list(model_data.values())

            existing_headers = ws.row_values(1)
            if not existing_headers:
                ws.append_row(headers)
                ws.append_row(values)
                return True, f"Initialized 'Marks' and added Sequence {mark.sequence_id}, Pilot {mark.pilot_id}, Judge {mark.judge_id}.."

            # Sheet has data
            data = ws.get_all_records()
            df = pd.DataFrame(data)

            match = df[
                (df['sequence_id'] == mark.sequence_id) & 
                (df['pilot_id'] == mark.pilot_id) & 
                (df['judge_id'] == mark.judge_id)
            ]

            # Assume the sheet columns match the model field order exactly.
            row_values = list(mark.model_dump().values())
            
            if not match.empty:
                # Update existing row
                row_num = match.index[0] + 2 # +2 for 1-based index + header
                ws.update(range_name=f"A{row_num}", values=[row_values])
                return True, f"Updated score for Sequence {mark.sequence_id}, Pilot {mark.pilot_id}, Judge {mark.judge_id}."
            else:
                # Append new row
                ws.append_row(row_values)
                return True, f"Added score for Sequence {mark.sequence_id}, Pilot {mark.pilot_id}, Judge {mark.judge_id}."

        except Exception as e:
            return False, f"Upsert Error: {str(e)}"
        
    def sync_acro_judges(self, df_acro_judges: pd.DataFrame) -> Tuple[bool, str]:
        try:
            current_judges = self.get_all_judges()
            current_ids = {j.id for j in current_judges}
            
            acro_ids = set(df_acro_judges['id'].astype(int).tolist())

            extra_ids = current_ids - acro_ids
            if extra_ids:
                return False, f"Validation Error: The AeroScoring App Judges list has IDs {extra_ids} which are missing from the AcroScoring uploaded ctx file. Please update the legacy ACRO system to include these judges or remove them from the AeroScoring App Judges tab manually."

            process_status: List[str] = []
            common_ids = current_ids.intersection(acro_ids)
            if common_ids:                
                common_df = df_acro_judges[df_acro_judges['id'].isin(common_ids)] # type: ignore
                records = cast(List[Dict[str, Any]], common_df.to_dict('records')) # type: ignore
                
                for record in records:
                    acro_judge = dm.AcroJudge(**record)
                    ok, msg = self.update_judge_name(acro_judge)
                    if not ok:
                        return False, f"Update judge name error: {msg}"
                
                process_status.append(f"Updated judge names.")
            
            missing_ids = acro_ids - current_ids
            if missing_ids:
                new_judges_rows: List[List[Any]] = []
                
                missing_df = df_acro_judges[df_acro_judges['id'].isin(missing_ids)] # type: ignore
                records = cast(List[Dict[str, Any]], missing_df.to_dict('records')) # type: ignore
                
                for record in records:
                    acro_judge = dm.AcroJudge(**record)
                    new_judge = dm.Judge.from_acro_judge(acro_judge)
                    new_judges_rows.append(new_judge.to_sheet_row(self._judges_headers))

                if new_judges_rows:
                    self._judges_ws.append_rows(new_judges_rows)
                    process_status.append(f"Added {len(new_judges_rows)} new judges.")

            if len(process_status) > 0:
                return True, " ".join(process_status)
            else:
                return True, "No judge updates needed."
        except Exception as e:
            return False, f"Judge sync error: {e}"
        
    def delete_judge(self, judge_id: int) -> Tuple[bool, str]:
        try:
            id_col = self._judges_headers.index("id") + 1
            cell = self._judges_ws.find(str(judge_id), in_column=id_col) # type: ignore
            if not cell:
                return False, f"Judge ID {judge_id} not found."
            
            try:
                user = self.get_user_by_role_and_id("judge", judge_id)
                self._delete_user_row(user.email)
            except UserRoleAndIdNotFound:
                pass
            
            self._judges_ws.delete_rows(cell.row)
            return True, f"Deleted Judge {judge_id}."
        except Exception as e:
            return False, f"Error deleting judge {judge_id}: {e}"

    def update_judge_email(self, judge_id: int, new_email: str) -> Tuple[bool, str]:
        try:
            judge = self.get_judge_details(judge_id)
            old_email = judge.email
            new_email = dm.Judge.clean_email(new_email)
            
            if old_email == new_email:
                return True, f"{judge.name} ({judge.id}) no change on email."
            
            all_judges = self.get_all_judges()
            for j in all_judges:
                if j.id != judge_id and j.email and j.email == new_email:
                    return False, f"Email '{new_email}' is already assigned to Judge {j.name} ({j.id})."
                
            try:
                existing_user = self.get_user_by_email(new_email)
                is_same_person = (existing_user.role == "judge" and existing_user.id == judge_id)
                if not is_same_person:
                    return False, f"Email '{new_email}' is already registered to another User ({existing_user.username})."
            
            except UserEmailNotFound:
                pass

            id_col = self._judges_headers.index("id") + 1
            cell = self._judges_ws.find(str(judge_id), in_column=id_col) # type: ignore
            if not cell:
                return False, f"Judge ID {judge_id} not found in DB."
            
            email_col = self._judges_headers.index("email") + 1
            self._judges_ws.update_cell(cell.row, email_col, new_email)

            if old_email:
                try:
                    user = self.get_user_by_email(old_email)
                    if user:
                        self._delete_user_row(old_email)
                        return True, f"Updated Judge {judge.name} ({judge_id}) email to {new_email}. Deleted User account on old email {old_email}."
                except UserEmailNotFound:
                    pass

            return True, f"Updated Judge {judge.name} ({judge_id}) email to {new_email}."

        except Exception as e:
            return False, f"Error updating judge email: {e}"
    
    def update_judge_name(self, new_judge: dm.AcroJudge) -> Tuple[bool, str]:
        try:
            old_judge = self.get_judge_details(new_judge.id)
            new_name = dm.Judge.full_name_from_acro_judge(new_judge)

            if old_judge.name == new_name:
                return True, f"No name update required on {old_judge.name}."

            id_col = self._judges_headers.index("id") + 1
            cell = self._judges_ws.find(str(new_judge.id), in_column=id_col) # type: ignore
            if not cell:
                return False, f"Judge ID {new_judge.id} not found in DB."
            
            old_judge.name = new_name

            # Assume the sheet columns match the model field order exactly.
            row_values = list(old_judge.model_dump().values())
            self._judges_ws.update(range_name=f"A{cell.row}", values=[row_values])
            return True, f"Updated Judge name {old_judge.name}."
        except Exception as e:
            return False, f"Error updating judge name: {e}"

    def _call_email_api(self, payload: EmailPayload) -> Tuple[bool, str]:
        try:
            api_request = EmailRequest(
                api_name="SEND_EMAIL",
                api_secret=secrets["google_app_script"]["api_secret"],
                payload=payload
            )
            
            api_url: str = _get_google_app_script_url()
            response = requests.post(api_url, json=api_request.model_dump(mode='json'))
            
            if response.status_code != 200:
                return False, f"HTTP Error: {response.status_code} - {response.text}"
            
            result = EmailResponse(**response.json())
            
            if result.status == "Success":
                return True, "Email sent successfully"
            else:
                return False, f"Send email error: {result.message}"
                
        except Exception as e:
            return False, f"Send email failed: {e}"
    
    def send_judge_invite(self, judge: dm.Judge, admin_user: dm.AuthUser) -> Tuple[bool, str]:
        try:
            if not judge.email:
                return False, f"Judge {judge.name} ({judge.id}) has no email."
            
            base_url = HttpUrl(str(context.url))
            base_url = f"{base_url.scheme}://{base_url.host}"
            reg_url = f"{base_url}/register?comp_id={self.id}&judge_id={judge.id}"
            app_url = f"{base_url}/comp?comp_id={self.id}"

            html_content = f"""
            <div style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #2E86C1;">✈️ Invitation to {self.title}</h2>
                <p>Hi <strong>{judge.name}</strong>,</p>
                <p><strong>{admin_user.username}</strong> has invited you to join the <b>AeroScoring</b> app for this competition.</p>
                <p>We are using AI to make scoring faster and easier. You simply take a photo of your score sheet, and the app does the rest!</p>
                
                <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                
                <h3>Step 1: Register</h3>
                <p>Please register your account for this specific competition (Comp Name: {self.title}) by clicking the button below:</p>
                <br>
                <p style="text-align: center;">
                    <a href="{reg_url}" style="background-color: #28B463; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                        📝 Register Now
                    </a>
                </p>

                <br>
                
                <h3>Step 2: Submit Scores</h3>
                <p>Once registered, use the link below during the competition to scan your sheets:</p>
                <br>
                <p style="text-align: center;">
                    <a href="{app_url}" style="background-color: #2E86C1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                        🏆 Open Scoring App
                    </a>
                </p>

                <br>
                
                <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="font-size: 12px; color: #888;">
                    <strong>Tip:</strong> Keep this email handy so you can quickly access the links during the competition day.<br>
                </p>
            </div>
            """

            payload = EmailPayload(
                recipient=judge.email,
                copy_to=admin_user.email,
                subject=f"Invitation: {self.title} Scoring App",
                htmlBody=html_content
            )

            return self._call_email_api(payload)

        except Exception as e:
            return False, f"Error preparing email for {judge.name}: {e}"

    

