import streamlit as st
import requests
import gspread
from typing import Optional, Dict, Any
from gspread.spreadsheet import Spreadsheet

class SheetService:
    """
    Singleton service to handle Google Sheets interactions securely.
    """
    
    def __init__(self, secrets: Dict[str, Any]):
        self._secrets: Dict[str, Any] = secrets
        self._client: Optional[gspread.Client] = None

    def _get_client(self) -> gspread.Client:
        """Lazily authenticates and returns the gspread client."""
        if self._client is None:
            try:
                creds_dict = self._secrets["gcp_service_account"]
                self._client = gspread.service_account_from_dict(creds_dict)
            except KeyError as e:
                st.error(f"Missing Secret Configuration: {e}")
                raise
            except Exception as e:
                st.error(f"Authentication Failed: {e}")
                raise
        return self._client

    def create_competition_sheet(
        self, 
        comp_name: str, 
        admin_email: str
    ) -> Optional[str]:
        """
        Calls the Apps Script API to create the comp sheet
        """

        try:
            # 1. Get Config
            api_url: str = self._secrets["google_app_script"]["url"]
            #st.info(api_url)
            api_secret: str = self._secrets["google_app_script"]["api_secret"]
            bot_email: str = self._secrets["gcp_service_account"]["client_email"]

            # 2. Prepare Payload
            payload = {
                "comp_name": comp_name,
                "admin_email": admin_email,
                "bot_email": bot_email,
                "api_secret": api_secret
            }

            # 3. Call the API
            # requests.post handles the JSON serialization automatically
            response = requests.post(api_url, json=payload)
            
            # 4. Handle Response
            if response.status_code == 200:
                result = response.json()
                
                if result.get("status") == "Success":
                    sheet_id = result.get("sheet_id")
                    return sheet_id
                else:
                    st.error(f"App Script Error: {result.get('message')}")
                    return None
            else:
                st.error(f"HTTP Error: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            st.error(f"Failed to connect to Factory API: {e}")
            return None

    def get_sheet_by_id(self, sheet_id: str) -> Optional[Spreadsheet]:
        """Fetches a specific sheet by ID (used for Judges)."""
        client = self._get_client()
        try:
            return client.open_by_key(sheet_id)
        except Exception as e:
            st.error(f"Failed to open competition: {e}")
            return None

# --- Convenience Function (Singleton Pattern) ---
# This prevents re-initializing the service on every rerun
def get_service() -> SheetService:
    if "sheet_service" not in st.session_state:
        st.session_state["sheet_service"] = SheetService(dict(st.secrets))
    return st.session_state["sheet_service"]