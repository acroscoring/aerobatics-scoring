import streamlit as st
from util.controller import CompScoreSheetAi
from PIL import Image
import pandas as pd
from pages.header import load
from typing import Tuple
from util.data_model import AcroMark
import util.constants as const
from datetime import datetime
import re
import time

app_ctrl = load(title="🏆 Competition Scoring")
ctrl = CompScoreSheetAi.connect(app_ctrl)
st.header(ctrl.db.title)

st.subheader("📸 Capture Score Sheet")
st.divider()


def validate_submission(flight_num: int, pilot_id: int, judge_id: int, user_id: int, is_admin: bool) -> Tuple[bool, str, str]:
    """
    Checks permissions, sequence validity, and duplicates.
    Returns: (is_valid, error_message, warning_message)
    """
    
    # 1. Check User Permission
    if not is_admin:
        if user_id != judge_id:
            return False, f"You are logged in as Judge #{user_id} but trying to submit for Judge #{judge_id}. Only the Admin can submit for other judges.", ""

    # 2. Check "ACRO Sequences"
    seq_df: pd.DataFrame = ctrl.db.get_table_df(const.DBTabs.ACRO_SEQUENCES)
    
    seq_row = seq_df[seq_df['id'] == flight_num]
    if seq_row.empty:
        return False, f"Sequence #{flight_num} not found in 'ACRO Sequences'. Please check with the Admin and ACRO Scoring.", ""
    
    row = seq_row.iloc[0]
    
    # Check Pilot in fly_order
    fly_order = str(row.get('fly_order'))
    # Clean split to handle "1 - 2" vs "1-2"
    valid_pilots = [p.strip() for p in fly_order.split('-')]
    
    if str(pilot_id) not in valid_pilots:
        return False, f"Pilot #{pilot_id} is not in the flying order for Seq #{flight_num}. Please check with the Admin and ACRO Scoring.", ""

    # Check Judge in judges_config
    judges_config = str(row.get('judges_config'))
    assigned_judge_ids = re.findall(r"(\d+)(?=\()", judges_config)
    valid_judges = {int(j) for j in assigned_judge_ids}
    if judge_id not in valid_judges:
         return False, f"Judge #{judge_id} is not assigned to Seq #{flight_num}. Please check with the Admin and ACRO Scoring.", ""

    # 3. Check Duplicate in "Marks"
    marks_df: pd.DataFrame = ctrl.db.get_table_df(const.DBTabs.MARKS)

    if marks_df.empty:
        exists = pd.DataFrame()
    else:
        exists = marks_df[
            (marks_df['sequence_id'] == flight_num) & 
            (marks_df['pilot_id'] == pilot_id) & 
            (marks_df['judge_id'] == judge_id)
        ]

    if not exists.empty:
        if is_admin:
            return True, "", f"Score already exists. As Admin, you can overwrite."
        else:
            return False, f"Score already exists. Ask the Admin to overwrite it.", ""

    return True, "", ""


current_score_sheet = ctrl.get_score_sheet_singleton()
if not current_score_sheet:
    input_method = st.radio("Input method:", ["⬆️ Upload Image", "📱 Use Camera"], horizontal=True, key="method_rd")
    img_file = st.camera_input("Take a picture", key="widget_camera") if input_method == "📱 Use Camera" else st.file_uploader("Choose file", type=["jpg", "jpeg", "png", "heic", "heif", "webp"], key="widget_uploader")

    if img_file:
        with st.spinner("AI is analyzing the image...", show_time=True):
            status_area = st.container()
            image = Image.open(img_file)
            st.image(image, caption="Image uploaded, looks correct?")
            ctrl.get_scoring_using_ai(image, status_area)
            st.rerun()

if current_score_sheet:
    st.subheader("📝 Verify & Edit Data")

    # Top Header Inputs
    c1, c2, c3 = st.columns(3)
    with c1:
        new_flight_num = st.number_input("Flight #", value=current_score_sheet.flight_number, min_value=1, max_value=99, step=1)
    with c2:
        new_pilot_id = st.number_input("Pilot ID", value=current_score_sheet.pilot_id, min_value=1, max_value=99, step=1)
    with c3:
        new_judge_id = st.number_input("Judge ID", value=current_score_sheet.judge_id, min_value=1, max_value=99, step=1)
    
    # Update singleton state so values persist
    current_score_sheet.pilot_id = new_pilot_id
    current_score_sheet.flight_number = new_flight_num
    current_score_sheet.judge_id = new_judge_id

    st.divider()

    # Organized Tabs
    tab_figs, tab_overall, tab_pens = st.tabs(["📊 Figures", "📋 Overall Items", "⚠️ Penalties"])

    with tab_figs:
        st.caption("Edit figure scores. Use numbers (7.5) or codes (AV, HZ, PZ).")
        figs_data = [f.model_dump() for f in current_score_sheet.figures]
        df_figs = pd.DataFrame(figs_data)

        df_figs['score'] = df_figs['score'].astype(str)
        
        # Using TextColumn for 'score' allows "AV", "HZ" and numbers
        edited_figs_df = st.data_editor(
            df_figs,
            column_config={
                "figure_number": st.column_config.NumberColumn("Fig #", min_value=1, max_value=20, step=1, width="small", required=True),
                "score": st.column_config.TextColumn("Score", width="medium", required=True) 
            },
            num_rows="dynamic",
            width="stretch",
            hide_index=True,
            key="editor_figs"
        )

    with tab_overall:
        st.caption("Positioning, Harmony, etc.")
        overall_data = [o.model_dump() for o in current_score_sheet.overall_items]
        df_overall = pd.DataFrame(overall_data)

        df_overall['score'] = df_overall['score'].astype(str)

        edited_overall_df = st.data_editor(
            df_overall,
            column_config={
                "item": st.column_config.TextColumn("Item Name"),
                "score": st.column_config.TextColumn("Score")
            },
            num_rows="dynamic",
            width="stretch",
            hide_index=True,
            key="editor_overall"
        )

    with tab_pens:
        st.caption("Counts for penalties (e.g. 1 Too Low, 2 interruptions, etc.).")
        pen_data = [p.model_dump() for p in current_score_sheet.penalties]
        df_pen = pd.DataFrame(pen_data)

        edited_pen_df = st.data_editor(
            df_pen,
            column_config={
                "item": st.column_config.TextColumn("Penalty Type"),
                "count": st.column_config.NumberColumn("Count", step=1, min_value=0, max_value=999)
            },
            num_rows="dynamic",
            width="stretch",
            hide_index=True,
            key="editor_pen"
        )

    st.divider()
    
    # Validate instantly on every UI interaction
    assert app_ctrl.auth_user is not None
    user_id = app_ctrl.auth_user.id if app_ctrl.auth_user.id else 0
    user_email = app_ctrl.auth_user.email
    is_admin = app_ctrl.auth_user.role == "admin"

    is_valid, err_msg, warn_msg = validate_submission(new_flight_num, new_pilot_id, new_judge_id, user_id, is_admin)

    if err_msg:
        st.error(err_msg, icon="⛔")
        submit_disabled = True
    else:
        if warn_msg:
            st.warning(warn_msg, icon="⚠️")
        submit_disabled = False

    # --- Buttons ---
    col_sub, col_rst = st.columns([1, 1])
    
    with col_sub:
        if st.button("Submit Verified Scores", type="primary", icon="✅", disabled=submit_disabled):
            
            db_model = AcroMark.from_ai_score_sheet(
                current_score_sheet, 
                edited_figs_df, 
                edited_overall_df, 
                edited_pen_df,
                user_email=user_email,
                timestamp=datetime.now().strftime("%a %d-%b-%Y %H:%M:%S")
            )

            result_ok, msg = ctrl.db.marks.upsert(db_model) 
            
            if result_ok:
                st.success("Scores submitted successfully!", icon="✅")
                st.toast("Scores saved to database!", icon="🎉")
                ctrl.reset_comp_ai_ui()
                time.sleep(2)
                st.rerun()
            else:
                st.error(f"Submit Score Error: {msg}")

    with col_rst:
        if st.button("Reset / Cancel", type="secondary", icon="⏪"):
            ctrl.reset_comp_ai_ui()
            st.rerun()