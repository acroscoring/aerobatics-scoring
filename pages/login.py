import streamlit as st
from util.controller import AppController

st.set_page_config(page_title="Login", page_icon="🔐", layout="wide")
st.title("🔐 AeroScoring Login")

app_ctrl = AppController.connect()
if app_ctrl.is_user_logged_in():
    assert app_ctrl.db is not None
    st.header(app_ctrl.db.title)
    if st.button("Logout User", key="logout_bt"):
        app_ctrl.logout_user()

elif app_ctrl.is_comp_setup():
    assert app_ctrl.db is not None
    st.header(app_ctrl.db.title)
        
    if st.button("Logout Comp", key="app_logout_comp_bt"):
        app_ctrl.logout_comp()

    tab_login, tab_forgot = st.tabs(["Login", "Forgot Password"])
    
    with tab_login:
        st.header("🫣 Login")
        email: str = st.text_input("Email", icon="📧", key="email_login_txt")
        password: str = st.text_input("Password", type="password", icon="🔐", key="password_txt")
        if st.button("Log In", type="primary", key="login_bt"):
            app_ctrl.login(email, password)
        
    with tab_forgot:
        st.header("🤔 Reset Password")
        email: str = st.text_input("Email", icon="📧", key="email_forgot_txt")
        if st.button("Send Temporary Password", type="primary", key="send_bt"):
            app_ctrl.forgot_password(email)
else:
    st.error("No competition found. Please open the link sent by your Admin with the competition id.", icon="❌")

