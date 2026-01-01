import streamlit as st
from util.controller import Register

st.set_page_config(page_title="Registration", page_icon="📝", layout="wide")
st.title("📝 Create Judge User to Upload Scores")

app_reg = Register.connect()
st.header(app_reg.db.title)

st.subheader(f"Welcome {app_reg.judge_details.name}!")

with st.form("register_judge"):
    email: str = st.text_input("Email", value=app_reg.judge_details.email, help="Valid email to send access links", icon="📧", disabled=True)
    user_name: str = st.text_input("Name", value=app_reg.judge_details.name, help="Just used for salutation", icon="👋🏻", max_chars=50)
    password: str = st.text_input("Password", type="password", help="Something so the system knows it's you", icon="🔐")
    submitted: bool = st.form_submit_button("Create User", icon="🚀", type="primary")

    if submitted:
        with st.spinner("Creating user...", show_time=True):
            app_reg.create_judge_user(user_name=user_name, password=password)
            st.success(f"User created successfully!", icon="✅")         