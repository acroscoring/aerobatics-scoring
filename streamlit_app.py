import streamlit as st
from util.controller import AppController

app_ctrl = AppController.connect()

pages = [
    st.Page("pages/home.py", title="Home", icon="✈️"),
    st.Page("pages/read_me.py", title="Read Me", icon="📖"),
    st.Page("pages/admin.py", title="Admin", icon="⚙️"),
]

if app_ctrl.is_user_logged_in():
    pages.append(st.Page("pages/login.py", title="Login", icon="🔐"))
    pages.append(st.Page("pages/comp.py", title="Competition", icon="🏆"))
elif app_ctrl.is_comp_setup():
    pages.append(st.Page("pages/login.py", title="Login", icon="🔐"))
    pages.append(st.Page("pages/register.py", title="Register", icon="📝"))
else:
    pass

page = st.navigation(pages)
page.run()