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

@st.cache_resource
def _get_global_gspread_client():
    try:
        creds_dict = st.secrets["gcp_service_account"]
        return gspread.service_account_from_dict(creds_dict)
    except KeyError as e:
        st.error(f"Missing Secret Configuration: {e}")
        raise
    except Exception as e:
        st.error(f"Authentication Failed: {e}")
        raise

class GoogleServices:
    """
    Singleton service to handle Google Sheets interactions securely.
    """
    
    def __init__(self):
        self._client = _get_global_gspread_client()
        self._api_url: str = st.secrets["google_app_script"]["prod_url"] if st.secrets["env"]["type"] == "prod" else st.secrets["google_app_script"]["dev_url"]
        self._api_secret: str = st.secrets["google_app_script"]["api_secret"]
        self._bot_email: str = st.secrets["gcp_service_account"]["client_email"]
        self._api_key: str = st.secrets["google_gemini"]["api_key"]

    def create_competition_sheet(self, comp_name: str, admin_email: str, current_url: HttpUrl) -> Optional[tuple[str, str]]:
        try:
            payload = CreateCompetition(
                comp_name = comp_name,
                admin_email = admin_email,
                bot_email = self._bot_email,
                app_url = current_url,
                api_secret = self._api_secret
            )
            
            response = requests.post(self._api_url, json=payload.model_dump(mode='json'))
            
            if response.status_code == 200:
                result = CreateCompetitionResponse(**response.json())
                
                if result.status == "Success":
                    return str(result.sheet_id), str(result.comp_url)
                else:
                    st.error(f"App Script Error: {result.message}")
                    return None
            else:
                st.error(f"HTTP Error: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            st.error(f"Failed to connect to Factory API: {e}")
            return None

    def get_sheet_by_id(self, sheet_id: str) -> Optional[gspread.spreadsheet.Spreadsheet]:
        try:
            return self._client.open_by_key(sheet_id)
        except Exception as e:
            st.error(f"Failed to open competition: {e}")
            return None
        
    def save_to_sheet(self, sheet_data: score_service.ScoreSheet) -> None:
        """Placeholder for your future backend logic"""
        st.toast("Saving data to cloud...", icon="☁️")
        # Convert Pydantic object to a clean dictionary for the API/JSON
        # exclude_none=True helps keep the payload clean if fields are empty
        payload = sheet_data.model_dump(exclude_none=True)
        
        # In a real app, you would do: requests.post(url, json=payload)
        st.code(payload, language="json") 
        st.success("Success! Payload constructed from strongly typed class.")
    
    def get_scoring_sheet_data_using_ai(self, image: Image.Image) -> Optional[score_service.ScoreSheet]:
        try:
            client = genai.Client(api_key=self._api_key)
            prompt = "Extract the data from this aerobatics score sheet. Return 0 for missing values."
            response = client.models.generate_content(
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
            st.error(f"Extraction failed: {e}")

# --------------------------------------------------------------------------------------------------------------

# --- Convenience Function (Singleton Pattern) ---
# This prevents re-initializing the service on every rerun
def get_google_service() -> GoogleServices:
    return st_service.get_session_state_singleton("google_services", GoogleServices())
    