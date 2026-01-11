import streamlit as st
from pages.header import load
import util.messages as msg
from io import StringIO
from util.acro_parser import CtxParser
from typing import Tuple, List, Dict, Any
import pandas as pd
import util.data_model as dm
import time
import util.streamlit_model as sm

app_ctrl = load(title="⚙️ Administration")

# --------------------------------------------------------------------------------------------------------------
# Helper Functions
# --------------------------------------------------------------------------------------------------------------

def render_import_page():
    st.markdown("Upload the competition's `.ctx` file to define Judges, Pilots and Sequences.")

    uploaded_file = st.file_uploader("Choose a CTX file", type="ctx")

    if uploaded_file is not None:
        # 1. Read File
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        file_content = stringio.read()

        # 2. Preview Data
        #st.info("Parsing file...")
        parser = CtxParser()
        df_judges, df_pilots, df_sequences, df_marks = parser.parse_file(file_content)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Judges", len(df_judges))
        col2.metric("Pilots", len(df_pilots))
        col3.metric("Sequences", len(df_sequences))
        col4.metric("Marks", len(df_marks))

        with st.expander("Preview the first 5 rows of the ctx file to validate it's the correct one"):
            st.write("### Judges", df_judges.head())
            st.write("### Pilots", df_pilots.head())
            st.write("### Sequences", df_sequences.head())
            st.write("### Marks", df_marks.head())

        # 3. Update Action
        if st.button("Confirm Update", type="primary", icon="🚀"):
            assert app_ctrl.db is not None
            progress_bar = st.progress(0)
            status_area = st.empty()

            def render_error_or_progress(progress_value: int, process_tuple: Tuple[bool, str]) -> bool:
                success, msg = process_tuple
                if not success:
                    st.error(msg, icon="🚫")
                    return False
                progress_bar.progress(value=progress_value, text=msg)
                return True

            # ------- Sync CTX File & App -------
            status_area.text("Syncing Data...")
            if not render_error_or_progress(10, app_ctrl.db.sync_acro_judges(df_judges)): return


            # ------- Save CTX File -------
            status_area.text("Saving ACRO File...")
            df_raw = parser.raw_file_to_df(file_content)
            if not render_error_or_progress(60, app_ctrl.db.update_tab_from_df("ACRO File", df_raw)): return
            if not render_error_or_progress(70, app_ctrl.db.update_tab_from_df("ACRO Judges", df_judges)): return
            if not render_error_or_progress(80, app_ctrl.db.update_tab_from_df("ACRO Pilots", df_pilots)): return
            if not render_error_or_progress(90, app_ctrl.db.update_tab_from_df("ACRO Sequences", df_sequences)): return
            if not render_error_or_progress(100, app_ctrl.db.update_tab_from_df("ACRO Marks", df_marks)): return

            status_area.text("Done!")
            st.success("Database successfully updated from CTX file.")

def render_judges_page():
    st.text("Manage the Judges list and their emails. If you update an email, the existing User account (if any) will be reset.")

    assert app_ctrl.db is not None
    all_judges = app_ctrl.db.get_all_judges()
    all_users = app_ctrl.db.get_all_users()

    # Check for Admins with blank User ID
    judge_email_map = {dm.UserBase.clean_email(j.email): j.id for j in all_judges if j.email}

    for user in all_users:
        if user.role == "admin" and user.id == "" and user.email in judge_email_map:
            match_judge_id = judge_email_map[user.email]
            
            try:
                app_ctrl.db.update_admin_user_id(user.email, match_judge_id)
                st.toast(f"Linked Admin {user.username} to Judge ID {match_judge_id}", icon="🔗")
            except Exception as e:
                st.error(f"Error linking admin: {e}")
                return
            
            user.id = match_judge_id

    # Build DF table
    user_map = {u.id: u for u in all_users if (u.role == "judge" or u.role == "admin") and u.id != ""}

    table_data: List[Dict[str, Any]] = []
    for j in all_judges:
        user = user_map.get(j.id)
        is_registered = user is not None
        is_admin = (user.role == "admin") if user else False
        table_data.append({
            "id": j.id,
            "name": j.name,
            "email": j.email,
            "registered": is_registered,
            "is_admin": is_admin
        })
    df = pd.DataFrame(table_data)

    current_session_key = f"judges_editor_{sm.get_session_state_singleton("dynamic_table_session_key", lambda: 0)}"
    
    st.data_editor(
        df,
        column_config={
            "id": st.column_config.NumberColumn("ID", format="%d", disabled=True),
            "name": st.column_config.TextColumn("Judge Name", disabled=True),
            "email": st.column_config.TextColumn("Email (Editable)", help="Add the Judge's email so it can register in the AeroScoring App."),
            "registered": st.column_config.CheckboxColumn("Registered?", disabled=True, help="A user was created in AeroScoring App using this email."),
            "is_admin": st.column_config.CheckboxColumn("Admin?", disabled=True, help="This user has Admin privileges."),
        },
        disabled=["id", "name", "registered", "is_admin"], 
        num_rows="dynamic",
        key=current_session_key,
        hide_index=True,
    )
  
    status_area = st.container()

    # --- Buttons ---
    col_save, col_cancel = st.columns([1, 1])

    with col_cancel:
        if st.button("Reset / Cancel", type="secondary", icon="⏪"):
            sm.set_session_state("dynamic_table_session_key", sm.get_session_state("dynamic_table_session_key")+1)
            st.rerun()
        
    with col_save:
        if st.button("Save Changes", type="primary", icon="✅"):
            # st.data_editor state is stored in st.session_state["judges_editor"]
            # It contains: {"added_rows": [], "deleted_rows": [], "edited_rows": {}}  
            changes = sm.get_session_state(current_session_key)
            has_error = False

            if changes["added_rows"]:
                status_area.warning("Please add new Judges in ACRO and then import here via the 'Acro Import' tab (CTX file). Manual addition is disabled here.", icon="⚠️")
                has_error = True

            # deleted_rows is a list of indices (integers) from the ORIGINAL dataframe
            if changes["deleted_rows"]:
                for index in changes["deleted_rows"]:
                    judge_to_del = df.iloc[index] # type: ignore
                    judge_id = int(judge_to_del["id"]) # type: ignore

                    if judge_to_del["is_admin"]:
                        status_area.error(f"Cannot delete Judge {judge_id} ({judge_to_del["name"]}) because she/he is an Admin.", icon="🚫")
                        has_error = True
                        continue
                    
                    success, msg = app_ctrl.db.delete_judge(judge_id)
                    if success:
                        status_area.info(msg, icon="🗑️")
                    else:
                        status_area.error(msg, icon="❌")
                        has_error = True

            # edited_rows is a dict: {row_index: {"col_name": "new_value"}}
            if changes["edited_rows"]:
                for index, updates in changes["edited_rows"].items():
                    if "email" in updates:
                        new_email = updates["email"]
                        judge_row = df.iloc[index] # type: ignore
                        judge_id = int(judge_row["id"]) # type: ignore

                        if judge_row["is_admin"]:
                            status_area.error(f"Cannot alter Judge {judge_id} ({judge_row["name"]}) email because she/he is an Admin.", icon="🚫")
                            has_error = True
                            continue
                        
                        try:
                            valid_email = dm.UserBase.clean_email(new_email)
                            success, msg = app_ctrl.db.update_judge_email(judge_id, valid_email)
                            if success:
                                status_area.info(msg, icon="✅")
                            else:
                                status_area.error(msg, icon="❌")
                                has_error = True
                        except Exception as e:
                            status_area.error(f"Invalid email format for Judge ID {judge_id} ({judge_row["name"]}): {e}", icon="❌")
                            has_error = True

            if has_error:
                status_area.error("There were warnings/errors above. Please check them and when ready 'Reset / Cancel' so the table load with the latest data.", icon="👀")
            else:
                time.sleep(3)
                sm.set_session_state("dynamic_table_session_key", sm.get_session_state("dynamic_table_session_key")+1)
                st.rerun()

# --------------------------------------------------------------------------------------------------------------
# Main Page
# --------------------------------------------------------------------------------------------------------------

if app_ctrl.is_user_logged_in():
    assert app_ctrl.db is not None
    st.header(app_ctrl.db.title)
    st.subheader("👩🏼‍💻 Admin Controls")

    tab_import, tab_judges, tab_users, tab_other = st.tabs(["Acro Import", "Judges", "Users", "Other"])
    with tab_import:
        render_import_page()
    with tab_judges:
        render_judges_page()
        

elif app_ctrl.is_comp_setup():
    assert app_ctrl.db is not None
    st.header(app_ctrl.db.title)
    st.error(msg.ErrorMsgs.LOGIN_TO_MNG_COMP, icon="❌")
    st.info("Logout of the competition to create a new competition (or reload the page).", icon="ℹ️")

else:
    st.header("Create a New Competition")

    with st.form("create_comp_form"):
        comp_name: str = st.text_input("Competition Name", placeholder="e.g. Australian National & Freestyle Championships 2025", help="A name to use in the pages", icon="🏆", max_chars=70)
        admin_email: str = st.text_input("Email", placeholder="you@gmail.com", help="Valid email to send access links", icon="📧")
        user_name: str = st.text_input("Name", placeholder="Maverik", help="Just used for salutation", icon="👋🏻", max_chars=50)
        password: str = st.text_input("Password", type="password", help="Something so the system knows it's you", icon="🔑")
        submitted: bool = st.form_submit_button("Create Competition", icon="🚀", type="primary")

        if submitted:
            with st.spinner("Creating competition...", show_time=True):
                app_ctrl.create_new_comp(comp_name=comp_name, user_name=user_name, admin_email=admin_email, password=password)
                st.success(f"Competition created successfully and an email was sent to you {user_name}!", icon="✅")
                st.toast("Loging you in...", icon="🔐")
                app_ctrl.login(admin_email, password)
                  