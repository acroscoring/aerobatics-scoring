import streamlit as st
from util.controller import AppController

pages = [
    st.Page("pages/home.py", title="Home", icon="✈️"),
    st.Page("pages/read_me.py", title="Read Me",icon="📖"),
    st.Page("pages/admin.py", title="Admin",icon="⚙️")
]

app_ctrl = AppController()
if app_ctrl.is_user_logged_in() :
    pages.append(st.Page("pages/comp.py", title="Competition",icon="🏆"))
    
    with st.sidebar:
        assert app_ctrl.auth_user is not None
        user = app_ctrl.auth_user
        st.caption(f"{user.role}({user.id}): {user.username}")
        if st.button("Logout"):
            app_ctrl.logout()

elif app_ctrl.is_comp_setup():
    tab_login, tab_forgot = st.tabs(["Login", "Forgot Password"])
    
    with tab_login:
        st.header("🔐 Login")
        email: str = st.text_input("Email", icon="📧")
        password: str = st.text_input("Password", type="password", icon="🔐")
        if st.button("Log In", type="primary"):
            assert app_ctrl.db is not None
            app_ctrl.login(email, password)
        
    with tab_forgot:
        st.header("🤔 Reset Password")
        email: str = st.text_input("Email", icon="📧")
        if st.button("Send Temporary Password", type="primary"):
            app_ctrl.forgot_password(email)

else:
    st.header("Hi!")

page = st.navigation(pages)
page.run()