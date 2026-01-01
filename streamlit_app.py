import streamlit as st
from util.controller import AppController

pages = [
    st.Page("pages/home.py", title="Home", icon="✈️"),
    st.Page("pages/read_me.py", title="Read Me",icon="📖"),
    st.Page("pages/admin.py", title="Admin",icon="⚙️")
]

app_ctrl = AppController.connect()
if app_ctrl.is_user_logged_in() :
    pages.append(st.Page("pages/comp.py", title="Competition",icon="🏆"))
    
    with st.sidebar:
        assert app_ctrl.db is not None
        st.write(app_ctrl.db.title)
        assert app_ctrl.auth_user is not None
        user = app_ctrl.auth_user
        st.caption(f"{user.role} ({user.id}): {user.username}")
        if st.button("Logout", key="app_logout_bt"):
            app_ctrl.logout()

elif app_ctrl.is_comp_setup():
    pages.append(st.Page("pages/login.py", title="Login",icon="🔐"))
else:
    pass

page = st.navigation(pages)
page.run()