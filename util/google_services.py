import streamlit as st
import requests
import gspread
from typing import Optional, Dict, Any, List, cast
from gspread.spreadsheet import Spreadsheet
from google import genai
from pydantic import BaseModel, Field
from PIL import Image
import pandas as pd

# --- Define Strongly Typed Schema (Pydantic) ---
# This acts as the "Contract" for the AI. It MUST return data in this shape.
class FigureScore(BaseModel):
    figure_number: int = Field(description="The Figure/Fig/No number (1, 2, 3...) that normally is the 1st column in a table. Each figure is a row in the table")
    score: Optional[float] = Field(description="The handwritten Score/Grade given (0.0 to 10.0) next to each figure. If 'HZ' or 'Hard Zero', use 0.0")

class ScoreSheet(BaseModel):
    pilot_id: int = Field(description="ID/Number of the pilot normally at the top of the sheet")
    judge_id: int = Field(description="ID/Number of the judge normally next to the judge name and signature")
    flight_number: int = Field(description="The pilot's flight number/# normally at the top of the sheet")
    figures: List[FigureScore] = Field(description="List/table of all figures and respective scores")


class GoogleServices:
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
    ) -> Optional[tuple[str, str]]:
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
                    return result.get("sheet_id"), result.get("sheet_url")
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
        
    def save_to_sheet(self, sheet_data: ScoreSheet) -> None:
        """Placeholder for your future backend logic"""
        st.toast("Saving data to cloud...", icon="☁️")
        # Convert Pydantic object to a clean dictionary for the API/JSON
        # exclude_none=True helps keep the payload clean if fields are empty
        payload = sheet_data.model_dump(exclude_none=True)
        
        # In a real app, you would do: requests.post(url, json=payload)
        st.code(payload, language="json") 
        st.success("Success! Payload constructed from strongly typed class.")
    
    def get_scoring_sheet_data(self) -> None:
        st.markdown("### 📸 Capture Score Sheet")

        input_method = st.radio("Input method:", ["Upload Image", "Use Camera"], horizontal=True)
        img_file = st.camera_input("Take a picture") if input_method == "Use Camera" else st.file_uploader("Choose file", type=["jpg", "jpeg", "png", "heic", "heif", "webp"])

        if "current_score_sheet" not in st.session_state:
                st.session_state.current_score_sheet = None

        if img_file:
            image = Image.open(img_file)
            
            # Only show the large image if we haven't extracted data yet (saves screen space)
            if not st.session_state.current_score_sheet:
                st.image(image, caption="Preview")

            # Extraction Button
            if st.button("🤖 Extract Scores from Image", type="primary"):
                try:
                    with st.spinner("AI is analyzing handwriting..."):
                        api_key: str = self._secrets["google_gemini"]["api_key"]
                        client = genai.Client(api_key=api_key)

                        prompt = "Extract the data from this aerobatics score sheet. Return 0 for missing values."
                        response = client.models.generate_content(
                            model="gemini-3-flash-preview", # gemini-3-flash-preview -> gemini-2.5-pro -> gemini-2.5-flash
                            contents=[
                                image,  # Image 1st
                                prompt  # Prompt 2nd as per Google best practice https://ai.google.dev/gemini-api/docs/image-understanding#tips-best-practices
                            ],
                            config={
                                "response_mime_type": "application/json",
                                "response_schema": ScoreSheet,
                            },
                        )
                        
                        # Store result in session state
                        st.session_state.current_score_sheet = cast(ScoreSheet, response.parsed)
                        st.rerun() # Force a refresh to show the edit form immediately

                except Exception as e:
                    st.error(f"Extraction failed: {e}")

        # This block only runs if we have data in memory
        if st.session_state.current_score_sheet:
            st.divider()
            st.subheader("📝 Verify & Edit Data")

            # Editable Metadata (Columns for better layout)
            col1, col2, col3 = st.columns(3)
            with col1:
                pilot_id = st.number_input("Pilot ID", value=st.session_state.current_score_sheet.pilot_id, min_value=0, step=1)
            with col2:
                flight_num = st.number_input("Flight #", value=st.session_state.current_score_sheet.flight_number, min_value=0, step=1)
            with col3:
                judge_id = st.number_input("Judge ID", value=st.session_state.current_score_sheet.judge_id, min_value=0, step=1)

            # Editable Table
            # Convert Pydantic list to DataFrame
            figures_data = [f.model_dump() for f in st.session_state.current_score_sheet.figures]
            df = pd.DataFrame(figures_data)

            edited_df = st.data_editor(
                df,
                column_config={
                    "figure_number": st.column_config.NumberColumn("Fig #", step=1),
                    "score": st.column_config.NumberColumn("Score", format="%.1f", step=0.5, min_value=0, max_value=10)
                },
                width="content",
                num_rows="dynamic", # Allows adding/deleting rows
                hide_index=True,
                key="editor_changes" # Unique key
            )

            # Average Score
            if not edited_df.empty:
                avg_score = edited_df["score"].mean()
                # Handle NaN if table is empty
                display_avg = f"{avg_score:.1f}" if pd.notna(avg_score) else "0.00"
                st.metric("Average Score", display_avg)

            # Final Action: Save
            if st.button("✅ Submit Verified Scores", type="primary"):
                try:
                    # Convert DataFrame to a list of dicts
                    raw_data = cast(List[Dict[str, Any]], edited_df.to_dict(orient="records")) # type: ignore

                    # Re-construct Figures safely
                    updated_figures = [FigureScore(**row) for row in raw_data]

                    final_sheet = ScoreSheet(
                        pilot_id=pilot_id,
                        flight_number=flight_num,
                        judge_id=judge_id,
                        figures=updated_figures
                    )

                    self.save_to_sheet(final_sheet)
                    
                except Exception as e:
                    st.error(f"Validation Error: {e}")
                
                if st.button("Process Next Sheet"):
                    st.session_state.current_score_sheet = None
                    st.rerun()


# --- Convenience Function (Singleton Pattern) ---
# This prevents re-initializing the service on every rerun
def get_service() -> GoogleServices:
    if "google_services" not in st.session_state:
        st.session_state["google_services"] = GoogleServices(dict(st.secrets))
    return st.session_state["google_services"]