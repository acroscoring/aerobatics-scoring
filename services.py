import streamlit as st
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
                # Type-safe casting of the secrets dict
                creds_dict = dict(self._secrets["gcp_service_account"])
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
        Clones the template, renames it, shares with Admin, and returns the new ID.
        """
        client = self._get_client()
        
        try:
            # 1. Clone the template
            new_sheet: Spreadsheet = client.copy(
                file_id=self._secrets["google_sheets"]["template_id"], 
                title=f"🏆 {comp_name} - Scoring DB",
                copy_permissions=True,
                folder_id=self._secrets["google_sheets"]["comp_folder"]
            )
            
            # 2. Share with Admin (Editor Access)
            new_sheet.share(
                email_address=admin_email, 
                perm_type='user', 
                role='writer',
                notify=True,
                email_message=f"Link to the '{comp_name}' scoring sheet. Use this sheet to manage the competion and import/export data from AcroScoring."
            )
            
            # 3. Return the new unique ID
            return new_sheet.id
            
        except Exception as e:
            st.error(f"Failed to create competition: {e}")
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