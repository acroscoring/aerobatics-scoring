import streamlit as st
from util.controller import AuthService

pages = [
    st.Page("pages/home.py", title="Home", icon="✈️"),
    st.Page("pages/read_me.py", title="Read Me",icon="📖"),
    st.Page("pages/admin.py", title="Admin",icon="⚙️")
]
page = st.navigation(pages)
page.run()

auth = AuthService()
if auth.auth_user:
    pages.append(st.Page("pages/comp.py", title="Competition",icon="🏆"))
    
    with st.sidebar:
        st.caption(f"{auth.auth_user.role}({auth.auth_user.id}): {auth.auth_user.username}")
        if st.button("Logout"):
            auth.logout()
else:
    tab_login, tab_forgot = st.tabs(["Login", "Forgot Password"])
    
    with tab_login:
        st.header("🔐 Login")
        email: str = st.text_input("Email", icon="📧")
        password: str = st.text_input("Password", type="password", icon="🔐")
        if st.button("Log In", type="primary"):
            auth.login(email, password)
        
    with tab_forgot:
        st.header("Reset Password")
        email: str = st.text_input("Email", icon="📧")
        if st.button("Send Temporary Password", type="primary"):
            auth.forgot_password(email)




#with st.sidebar:
#    st.write(st.session_state)

page = st.navigation(pages)
page.run()