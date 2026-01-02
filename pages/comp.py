import streamlit as st
from util.controller import CompScoreSheetAi
from PIL import Image
import pandas as pd
from pages.header import load

app_ctrl, cookies = load(title="🏆 Competition Scoring")
ctrl = CompScoreSheetAi.connect(app_ctrl)
st.header(ctrl.db.title)

st.markdown("### 📸 Capture Score Sheet")
st.divider()

current_score_sheet = ctrl.get_score_sheet_singleton()
if not current_score_sheet:
    input_method = st.radio("Input method:", ["Upload Image", "Use Camera"], horizontal=True, key="method_rd")
    img_file = st.camera_input("Take a picture", key="widget_camera") if input_method == "Use Camera" else st.file_uploader("Choose file", type=["jpg", "jpeg", "png", "heic", "heif", "webp"], key="widget_uploader")

    if img_file:
        image = Image.open(img_file)
        
        # Only show the large image if we haven't extracted data yet (saves screen space)
        if not current_score_sheet:
            st.image(image, caption="Image uploaded, looks correct?")

        with st.spinner("AI is analyzing the image...", show_time=True):
            ctrl.get_scoring_using_ai(image)
            st.rerun()

else:
    st.subheader("📝 Verify & Edit Data")

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

    if st.button("Submit Verified Scores", type="primary", icon="✅", key="save_score_bt"):
        ctrl.save_scoring_sheet_data_to_db(pilot_id=pilot_id, flight_num=flight_num, judge_id=judge_id, df=edited_df)
        
    if st.button("Reset", type="secondary", icon="⏪", help="Clear all back to the start", key="reset_bt"):
        ctrl.reset_comp_ai_ui()
        st.rerun()