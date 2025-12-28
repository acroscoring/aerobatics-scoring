import streamlit as st
from util.google_services import SheetDB, get_scoring_sheet_data_using_ai
import util.streamlit_services as st_service
from PIL import Image
import pandas as pd
import util.scoring_services as score_service
from typing import cast, List, Dict, Any

# Page Configuration (Must be the first Streamlit command)
st.set_page_config(page_title="Competition", page_icon="🏆", layout="wide")

# Main Content
st.title("🏆 Competition Scoring")
    
# Query Params
query_params = st.query_params
comp_id = query_params.get("comp_id")
if not comp_id:
    st.error("Invalid Competition Link", icon="❌")
    st.stop()

db = SheetDB.connect(comp_id)

st.header(db.get_title())

st.markdown("### 📸 Capture Score Sheet")
st.divider()

current_score_sheet: score_service.ScoreSheet = st_service.get_session_state_singleton("current_score_sheet", None)
if not current_score_sheet:
    input_method = st.radio("Input method:", ["Upload Image", "Use Camera"], horizontal=True)
    img_file = st.camera_input("Take a picture", key="widget_camera") if input_method == "Use Camera" else st.file_uploader("Choose file", type=["jpg", "jpeg", "png", "heic", "heif", "webp"], key="widget_uploader")

    if img_file:
        image = Image.open(img_file)
        
        # Only show the large image if we haven't extracted data yet (saves screen space)
        if not current_score_sheet:
            st.image(image, caption="Image uploaded, looks correct?")

        if st.button("Extract Scores from Image", type="primary", icon="👀"):
            with st.spinner("AI is analyzing handwriting..."):
                new_score_sheet = get_scoring_sheet_data_using_ai(image)
                if new_score_sheet:
                    current_score_sheet = new_score_sheet
                    st_service.set_session_state("current_score_sheet", current_score_sheet)
                    st.rerun() # Force a refresh to show the edit form immediately

        

if current_score_sheet:
    st.subheader("📝 Verify & Edit Data")

    # Editable Metadata (Columns for better layout)
    col1, col2, col3 = st.columns(3)
    with col1:
        pilot_id = st.number_input("Pilot ID", value=current_score_sheet.pilot_id, min_value=0, step=1)
    with col2:
        flight_num = st.number_input("Flight #", value=current_score_sheet.flight_number, min_value=0, step=1)
    with col3:
        judge_id = st.number_input("Judge ID", value=current_score_sheet.judge_id, min_value=0, step=1)

    # Editable Table
    # Convert Pydantic list to DataFrame
    figures_data = [f.model_dump() for f in current_score_sheet.figures]
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
        display_avg = f"{avg_score:.1f}" if pd.notna(avg_score) else "0.00" # Handle NaN if table is empty
        st.metric("Average Score", display_avg)

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Submit Verified Scores", type="primary", icon="✅"):
            try:
                # Convert DataFrame to a list of dicts
                raw_data = cast(List[Dict[str, Any]], edited_df.to_dict(orient="records")) # type: ignore

                # Re-construct Figures safely
                updated_figures = [score_service.FigureScore(**row) for row in raw_data]

                final_score_sheet = score_service.ScoreSheet(
                    pilot_id=pilot_id,
                    flight_number=flight_num,
                    judge_id=judge_id,
                    figures=updated_figures
                )

                db.save_to_sheet(final_score_sheet)
                
            except Exception as e:
                st.error(f"Validation Error: {e}", icon="❌")
        
    with col2:
        if st.button("Reset", type="secondary", icon="❌"):
            st_service.delete_session_state("current_score_sheet")
            st_service.delete_session_state("widget_uploader")
            st_service.delete_session_state("widget_camera")
            st.rerun()