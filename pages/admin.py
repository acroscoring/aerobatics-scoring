import streamlit as st
from pages.header import load
import util.messages as msg
from io import StringIO
from util.acro_parser import CtxParser

app_ctrl = load(title="⚙️ Administration")

def render_admin_page():
    st.markdown("Upload a `.ctx` file to update Judges, Pilots and Sequences.")

    uploaded_file = st.file_uploader("Choose a CTX file", type="ctx")

    if uploaded_file is not None:
        # 1. Read File
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        file_content = stringio.read()

        # 2. Preview Data
        st.info("Parsing file...")
        parser = CtxParser()
        df_judges, df_pilots, df_sequences, df_marks = parser.parse_file(file_content)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Judges", len(df_judges))
        col2.metric("Pilots", len(df_pilots))
        col3.metric("Sequences", len(df_sequences))
        col4.metric("Marks", len(df_marks))

        with st.expander("Preview 5 Rows of Extracted Data"):
            st.write("### Judges", df_judges.head())
            st.write("### Pilots", df_pilots.head())
            st.write("### Sequences", df_sequences.head())
            st.write("### Marks", df_marks.head())

        # 3. Update Action
        if st.button("Confirm Update", type="primary", icon="🚀"):
            assert app_ctrl.db is not None
            progress_bar = st.progress(0)
            status_area = st.empty()

            status_area.text("Saving Raw File...")
            df_raw = parser.raw_file_to_df(file_content)
            success_r, msg_r = app_ctrl.db.update_tab_from_df("ACRO File", df_raw)
            if not success_r: 
                st.error(msg_r)
                return
            progress_bar.progress(20)
            
            status_area.text("Updating Judges...")
            success_j, msg_j = app_ctrl.db.update_tab_from_df("ACRO Judges", df_judges)
            if not success_j:
                st.error(msg_j)
                return
            progress_bar.progress(40)

            status_area.text("Updating Pilots...")
            success_p, msg_p = app_ctrl.db.update_tab_from_df("ACRO Pilots", df_pilots)
            if not success_p: 
                st.error(msg_p)
                return
            progress_bar.progress(60)

            status_area.text("Updating Sequences...")
            success_s, msg_s = app_ctrl.db.update_tab_from_df("ACRO Sequences", df_sequences)
            if not success_s: 
                st.error(msg_s)
                return
            progress_bar.progress(80)

            status_area.text("Updating Marks...")
            success_m, msg_m = app_ctrl.db.update_tab_from_df("ACRO Marks", df_marks)
            if not success_m: 
                st.error(msg_m)
                return
            progress_bar.progress(100)

            status_area.text("Done!")
            st.success("Database successfully updated from CTX file.")



if app_ctrl.is_user_logged_in():
    assert app_ctrl.db is not None
    st.header(app_ctrl.db.title)
    st.subheader("👩🏼‍💻 Admin Controls")

    tab_ctx, tab_other = st.tabs(["Acro Import", "Other"])
    with tab_ctx:
        render_admin_page()

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
                  