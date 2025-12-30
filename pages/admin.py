import streamlit as st
from util.controller import create_sheet_db_and_admin

st.set_page_config(page_title="Admin", page_icon="⚙️", layout="wide")

# Main Content
st.title("⚙️ Administration")

st.header("Create a new competition")

with st.form("create_comp_form"):
    comp_name: str = st.text_input("Competition Name", placeholder="e.g. Australian National & Freestyle Championships 2025", help="A name to use in the pages", icon="🏆", max_chars=70)
    admin_email: str = st.text_input("Email", placeholder="you@gmail.com", help="Valid email to send access links", icon="📧")
    user_name: str = st.text_input("Name", placeholder="Maverik", help="Just used for salutation", icon="👋🏻", max_chars=50)
    password: str = st.text_input("Password", type="password", help="Something so the system knows it's you", icon="🔐")
    submitted: bool = st.form_submit_button("Create Competition", icon="🚀", type="primary")

    if submitted:
        with st.spinner("Creating competition...", show_time=True):
            create_sheet_db_and_admin(comp_name=comp_name, user_name=user_name, admin_email=admin_email, password=password)
            st.success(f"Competition created successfully and an email was sent to you {user_name}!", icon="✅")    
            # To do: Login Admin user
        

        