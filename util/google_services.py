import streamlit as st
import requests
import gspread
from typing import Optional, cast, Literal
from google import genai
from PIL import Image
import util.streamlit_services as st_service
import util.scoring_services as score_service
from pydantic import BaseModel, EmailStr, HttpUrl

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

# --------------------------------------------------------------------------------------------------------------

@st.cache_resource(show_spinner="Getting Connection...", show_time=True)
def _get_gspread_client() -> gspread.Client:
    try:
        creds_dict = st.secrets["gcp_service_account"]
        return gspread.service_account_from_dict(creds_dict)
    except KeyError as e:
        st.error(f"Missing Bot Secret Configuration: {e}", icon="❌")
        raise
    except Exception as e:
        st.error(f"Bot Authentication Failed: {e}", icon="❌")
        raise

@st.cache_resource(show_spinner="Getting DB...", show_time=True)
def _get_sheet_by_id(sheet_id: str) -> Optional[gspread.spreadsheet.Spreadsheet]:
    try:
        gspread_client = _get_gspread_client()
        return gspread_client.open_by_key(sheet_id)
    except Exception as e:
        st.error(f"Failed to open competition sheet (DB): {e}", icon="❌")
        return None

@st.cache_resource(show_spinner="Getting AI Connection...", show_time=True)
def _get_genai_client():
    try:
        api_key: str = st.secrets["google_gemini"]["api_key"]
        return genai.Client(api_key=api_key)
    except KeyError as e:
        st.error(f"Missing AI Secret Configuration: {e}", icon="❌")
        raise
    except Exception as e:
        st.error(f"AI Authentication Failed: {e}", icon="❌")
        raise

# --------------------------------------------------------------------------------------------------------------

def create_competition_sheet(comp_name: str, admin_email: str) -> Optional[tuple[str, str]]:
    try:
        if not st.context.url:
            st.error(f"Error getting context URL.", icon="❌")
            return None

        payload = CreateCompetition(
            comp_name = comp_name,
            admin_email = admin_email,
            bot_email = st.secrets["gcp_service_account"]["client_email"],
            app_url = HttpUrl(st.context.url), # no query parameters
            api_secret = st.secrets["google_app_script"]["api_secret"]
        )
        
        api_url: str = st.secrets["google_app_script"]["prod_url"] if st.secrets["env"]["type"] == "prod" else st.secrets["google_app_script"]["dev_url"]
        response = requests.post(api_url, json=payload.model_dump(mode='json'))
        
        if response.status_code == 200:
            result = CreateCompetitionResponse(**response.json())
            
            if result.status == "Success":
                return str(result.sheet_id), str(result.comp_url)
            else:
                st.error(f"Create Competition Apps Script Error: {result.message}", icon="❌")
                return None
        else:
            st.error(f"HTTP Error: {response.status_code} - {response.text}", icon="❌")
            return None

    except KeyError as e:
        st.error(f"Missing API URL Secret Configuration: {e}", icon="❌")
        return None
    except Exception as e:
        st.error(f"Failed to create competition sheet (DB): {e}", icon="❌")
        return None

def get_scoring_sheet_data_using_ai(image: Image.Image) -> Optional[score_service.ScoreSheet]:
    try:
        genai_client = _get_genai_client()
        prompt = "Extract the data from this aerobatics score sheet. Return 0 for missing values."
        response = genai_client.models.generate_content(
            model="gemini-3-flash-preview", # gemini-3-flash-preview -> gemini-2.5-pro -> gemini-2.5-flash
            contents=[
                image,  # Image 1st
                prompt  # Prompt 2nd as per Google best practice https://ai.google.dev/gemini-api/docs/image-understanding#tips-best-practices
            ],
            config={
                "response_mime_type": "application/json",
                "response_schema": score_service.ScoreSheet,
            },
        )
        return cast(score_service.ScoreSheet, response.parsed)
    except Exception as e:
        st.error(f"AI getting score error: {e}", icon="❌")

# --------------------------------------------------------------------------------------------------------------

class SheetDB:
    """
    Singleton service to handle Google Sheets interactions securely.
    Usage: db = SheetDB.connect("your_sheet_id_here")
    """
    def __init__(self, sheet_id: str):
        sheet = _get_sheet_by_id(sheet_id)
        if not sheet:
            st.error("Competition Not Found", icon="❌")
            st.stop()
        
        self._sheet = sheet
        self.sheet_id = sheet_id
    
    @classmethod
    def connect(cls, sheet_id: str) -> "SheetDB":
        session_key = f"SheetDB_{sheet_id}"
        return st_service.get_session_state_singleton(session_key, cls(sheet_id))

    def get_title(self) -> str:
        return self._sheet.title
    
    def register_user(self, user: score_service.User) -> tuple[bool, str]:
        """
        Checks if email exists. If not, adds the user.
        Returns: (Success Boolean, Message String)
        """
        try:
            ws = self._sheet.worksheet("Users")

            # col_values(2) returns a list of all strings in the 2nd column (email)
            existing_emails = ws.col_values(2)
            
            if user.email in existing_emails:
                return False, f"User with email {user.email} already exists. Please login."

            row_data = user.to_sheet_row()
            ws.append_row(row_data)
            return True, "User created successfully!"

        except Exception as e:
            return False, f"Register User Error: {str(e)}"

    def save_to_sheet(self, sheet_data: score_service.ScoreSheet) -> None:
        """Placeholder for your future backend logic"""
        st.toast("Saving data to cloud...", icon="☁️")
        # Convert Pydantic object to a clean dictionary for the API/JSON
        # exclude_none=True helps keep the payload clean if fields are empty
        payload = sheet_data.model_dump(exclude_none=True)
        
        # In a real app, you would do: requests.post(url, json=payload)
        st.code(payload, language="json") 
        st.success("Success! Payload constructed from strongly typed class.")


    