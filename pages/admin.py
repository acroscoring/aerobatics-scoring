import streamlit as st
from util.controller import AppController, CompDB

st.set_page_config(page_title="Admin", page_icon="⚙️", layout="wide")
st.title("⚙️ Administration")

app_ctrl = AppController.connect()
if app_ctrl.is_user_logged_in():
    assert app_ctrl.db is not None
    st.header(app_ctrl.db.title)
    st.write("Admin controls")

elif app_ctrl.is_comp_setup():
    assert app_ctrl.db is not None
    st.header(app_ctrl.db.title)
    st.write("Login to manage the current competition or create a new competition")
    if st.button("Create New Comp", type="primary", key="create_new_comp_bt"):
        assert app_ctrl.db is not None
        app_ctrl.logout()

else:
    st.header("Create a new competition")

    with st.form("create_comp_form"):
        comp_name: str = st.text_input("Competition Name", placeholder="e.g. Australian National & Freestyle Championships 2025", help="A name to use in the pages", icon="🏆", max_chars=70)
        admin_email: str = st.text_input("Email", placeholder="you@gmail.com", help="Valid email to send access links", icon="📧")
        user_name: str = st.text_input("Name", placeholder="Maverik", help="Just used for salutation", icon="👋🏻", max_chars=50)
        password: str = st.text_input("Password", type="password", help="Something so the system knows it's you", icon="🔐")
        submitted: bool = st.form_submit_button("Create Competition", icon="🚀", type="primary")

        if submitted:
            with st.spinner("Creating competition...", show_time=True):
                CompDB.create(comp_name=comp_name, user_name=user_name, admin_email=admin_email, password=password)
                app_ctrl.login(admin_email, password)
                st.success(f"Competition created successfully and an email was sent to you {user_name}!", icon="✅")    
                


        