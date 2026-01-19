import streamlit as st
from pages.header import load
import util.constants as const
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

    Tabs = const.DBTabs

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

        status_area = st.container()
        progress_bar = status_area.progress(0)

        # 3. Update Action
        if st.button("Confirm Update", type="primary", icon="🚀"):
            assert app_ctrl.db is not None
            
            def render_error_or_progress(progress_value: int, process_tuple: Tuple[bool, str]) -> bool:
                success, msg = process_tuple
                if not success:
                    st.error(msg, icon="🚫")
                    return False
                progress_bar.progress(value=progress_value, text=msg)
                return True

            # ------- Sync CTX File & App -------
            if not render_error_or_progress(10, app_ctrl.db.judges.sync_judges(df_judges)): return


            # ------- Save CTX File -------
            df_raw = parser.raw_file_to_df(file_content)
            if not render_error_or_progress(60, app_ctrl.db.update_tab_from_df(Tabs.ACRO_FILE, df_raw)): return
            if not render_error_or_progress(70, app_ctrl.db.update_tab_from_df(Tabs.ACRO_JUDGES, df_judges)): return
            if not render_error_or_progress(80, app_ctrl.db.update_tab_from_df(Tabs.ACRO_PILOTS, df_pilots)): return
            if not render_error_or_progress(90, app_ctrl.db.update_tab_from_df(Tabs.ACRO_SEQUENCES, df_sequences)): return
            if not render_error_or_progress(100, app_ctrl.db.update_tab_from_df(Tabs.ACRO_MARKS, df_marks)): return

            status_area.success("Database successfully updated with CTX file.")
            progress_bar.empty()

def render_judges_page():
    st.markdown("""
                ##### Add the Judges email and invite them to use the AeroScore App.
                
                1. Add each judge's email and **save**.
                    - You can update the email in case of mistake, but if there is a AeroScore App user with that incorrect email then it will be deleted.
                2. Select the judges you want to send the invite email (for them to register and be able to use the AeroScore App).
                """)
    st.divider()

    def reset_all():
        assert app_ctrl.db is not None
        sm.set_session_state("judge_selection", set[int])
        sm.set_session_state("dynamic_table_session_key", sm.get_session_state("dynamic_table_session_key")+1)
        app_ctrl.db.judges.refresh()
        app_ctrl.db.users.refresh()
        st.rerun()

    assert app_ctrl.db is not None
    assert app_ctrl.auth_user is not None
    all_judges = app_ctrl.db.judges.all_judges
    all_users = app_ctrl.db.users.all_users

    if not all_judges:
        st.error(f"No Judges uploaded yet, please cofigure them in AcroScoring first and then import here.", icon="❌")
        return

    Tbl = dm.JudgeTableRow 
    Cols = Tbl.Cols

    # Build DF table
    user_map = {u.id: u for u in all_users if (u.role == "judge" or u.role == "admin") and u.id != ""}
    
    sm.get_session_state_singleton("judge_selection", lambda: set[int])

    table_data: List[Dict[str, Any]] = []
    for j in all_judges:
        user = user_map.get(j.id)
        table_row = Tbl(
            id=j.id,
            name=j.name,
            email=j.email,
            registered=(user is not None),
            is_admin=((user.role == "admin") if user else False),
            selected=(j.id in sm.get_session_state("judge_selection"))
        )
        table_data.append(table_row.to_row())
    
    df = pd.DataFrame(table_data)

    if st.button("Select All to Send Email", help="Selects all judges who haven't registered yet and have an email.", type="secondary", icon="✅"):
        unreg_ids = {j.id for j in all_judges if j.id not in user_map and j.email}
        sm.set_session_state("judge_selection", unreg_ids)
        st.rerun()

    current_session_key = f"judges_editor_{sm.get_session_state_singleton("dynamic_table_session_key", lambda: 0)}"
    
    edited_df = st.data_editor(
        df,
        column_config={
            Cols.SELECTED: st.column_config.CheckboxColumn("Invite", help="Select to send email to the judge so she/he can register in AeroScore App"),
            Cols.ID: st.column_config.NumberColumn("ID", format="%d", disabled=True, help="ID for ACRO Scoring"),
            Cols.NAME: st.column_config.TextColumn("Judge Name", disabled=True, help="Name for ACRO Scoring", width="medium"),
            Cols.EMAIL: st.column_config.TextColumn("Email (Editable)", help="Add the Judge's email so it can register in the AeroScoring App", width="medium"),
            Cols.REGISTERED: st.column_config.CheckboxColumn("User?", disabled=True, help="A user was created in AeroScoring App using this email (the judge registered)"),
            Cols.IS_ADMIN: st.column_config.CheckboxColumn("Admin?", disabled=True, help="This user has Admin privileges"),
        },
        disabled=[Cols.ID, Cols.NAME, Cols.REGISTERED, Cols.IS_ADMIN], 
        num_rows="dynamic",
        key=current_session_key,
        hide_index=True,
    )

    current_selected_ids = set(edited_df[edited_df[Cols.SELECTED] == True][Cols.ID].tolist())
    sm.set_session_state("judge_selection", current_selected_ids)
  
    status_area = st.container()

    # --- Buttons ---
    col_save, col_email, col_cancel = st.columns([1, 1, 1])

    with col_cancel:
        if st.button("Reset / Cancel", type="secondary", icon="⏪"):
            reset_all()
        
    with col_email:
        num_selected = len(current_selected_ids)
        if st.button(f"Send Invite ({num_selected})", type="primary", icon="📧", disabled=(num_selected==0), help="Remember to save any change before sending the emails."):
            
            progress_bar = status_area.progress(0, text="Sending emails...")
            
            targets = [j for j in all_judges if j.id in current_selected_ids]
            
            success_count = 0
            for i, judge in enumerate(targets):
                progress = int(((i + 1) / len(targets)) * 100)
                progress_bar.progress(progress, text=f"Sending to {judge.name}...")
                
                ok, msg = app_ctrl.db.judges.send_judge_invite(judge, app_ctrl.auth_user)
                if ok:
                    success_count += 1
                else:
                    status_area.error(f"Failed to send email to {judge.name}: {msg}", icon="❌")
            
            progress_bar.empty()
            if success_count > 0:
                status_area.success(f"Successfully sent {success_count} invitation emails!", icon="✅")
                time.sleep(5)
                reset_all()

    with col_save:
        if st.button("Save Changes", type="primary", icon="💾"):
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
                    judge_to_del = Tbl(**df.iloc[index].to_dict()) # type: ignore

                    if judge_to_del.is_admin:
                        status_area.error(f"Cannot delete Judge {judge_to_del.name} ({judge_to_del.id}) because she/he is an Admin.", icon="🚫")
                        has_error = True
                        continue
                    
                    _ , judge_to_delete = app_ctrl.db.judges.get_by_id(judge_to_del.id)
                    success, msg = app_ctrl.db.judges.delete(judge_to_delete)
                    if success:
                        status_area.info(msg, icon="🗑️")
                    else:
                        status_area.error(msg, icon="❌")
                        has_error = True

            # edited_rows is a dict: {row_index: {"col_name": "new_value"}}
            if changes["edited_rows"]:
                admin_email_map = {u.email: u for u in all_users if u.role == "admin" and u.id == ""} # Check for Admins with blank User ID
                for index, updates in changes["edited_rows"].items():
                    if Cols.EMAIL in updates:
                        judge_to_update = Tbl(**df.iloc[index].to_dict()) # type: ignore
                        judge_to_update.email = dm.Judge.clean_email(updates[Cols.EMAIL])

                        if judge_to_update.email in admin_email_map:
                            try:
                                user = admin_email_map[judge_to_update.email]
                                user.id = judge_to_update.id
                                app_ctrl.db.users.update(user)
                                status_area.info(f"Linked Admin {user.username} to Judge ID {user.id}", icon="🔗")
                            except Exception as e:
                                status_area.error(f"Error linking admin: {e}", icon="❌")
                                has_error = True
                                continue
                        elif judge_to_update.is_admin:
                            status_area.error(f"Cannot alter Judge {judge_to_update.name} ({judge_to_update.id}) email because she/he is an Admin.", icon="🚫")
                            has_error = True
                            continue
                        
                        try:
                            _ , judge = app_ctrl.db.judges.get_by_id(judge_to_update.id)
                            success, msg = app_ctrl.db.judges.update_email(judge, str(judge_to_update.email))
                            if success:
                                status_area.info(msg, icon="✅")
                            else:
                                status_area.error(msg, icon="❌")
                                has_error = True
                        except Exception as e:
                            status_area.error(f"Invalid email format for Judge {judge_to_update.name} ({judge_to_update.id}): {e}", icon="❌")
                            has_error = True

            if has_error:
                status_area.error("There were warnings/errors above. Please check them and when ready 'Reset / Cancel' so the table load with the latest data.", icon="👀")
            else:
                time.sleep(5)
                reset_all()
    

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
    st.error(const.ErrorMsgs.LOGIN_TO_MNG_COMP, icon="❌")
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
                  