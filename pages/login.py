import streamlit as st
from pages.header import load
import util.constants as const

app_ctrl = load(title="🔐 AeroScoring Login")

if app_ctrl.is_user_logged_in():
    assert app_ctrl.db is not None and app_ctrl.auth_user is not None
    st.header(app_ctrl.db.title)
    if st.button("Logout User", key="logout_bt", icon="👋", help=f"Logout of the current user {app_ctrl.auth_user.username}"):
        app_ctrl.logout_user()

elif app_ctrl.is_comp_setup():
    assert app_ctrl.db is not None
    st.header(app_ctrl.db.title)
        
    if st.button("Logout Comp", key="app_logout_comp_bt", icon="👋", help=f"Logout of the current competition '{app_ctrl.db.title}'"):
        app_ctrl.logout_comp()

    tab_login, tab_forgot = st.tabs(["Login", "Forgot Password"])
    
    with tab_login:
        st.header("🫣 Login")
        email: str = st.text_input("Email", icon="📧", key="email_login_txt")
        password: str = st.text_input("Password", type="password", icon="🔑", key="password_txt")
        if st.button("Log In", type="primary", key="login_bt", icon="🔓", help=f"Login into the current competition '{app_ctrl.db.title}'"):
            app_ctrl.login(email, password)
        
    with tab_forgot:
        st.header("🤔 Reset Password")
        email: str = st.text_input("Email", icon="📧", key="email_forgot_txt")
        if st.button("Send New Password", type="primary", key="send_bt", icon="👋", help=f"Will send a new password to your email (if the email exists in this competition)"):
            app_ctrl.forgot_password(email)
else:
    st.error(const.ErrorMsgs.NO_COMP_FOUND, icon="❌")

