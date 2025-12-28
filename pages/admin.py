import streamlit as st
from util.google_services import create_competition_sheet
from util.scoring_services import try_create_user
from util.google_services import SheetDB

# Page Configuration (Must be the first Streamlit command)
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
        user = try_create_user(user_name, admin_email, password, "admin")
        if not user:
            st.stop()

        with st.spinner("Creating competition file..."):
            sheet_id, comp_url = create_competition_sheet(comp_name=comp_name, admin_email=admin_email) or (None, None)

        if sheet_id and comp_url:
            st.success(f"Competition created successfully and an email sent to you {user.username}!")

            db = SheetDB.connect(sheet_id)
            success, msg = db.register_user(user)
            if success:
                st.success(msg, icon="✅")
            else:
                st.error(msg, icon="❌")
            
            st.link_button("Login", url=comp_url, type="secondary", icon="⚙️")
            st.link_button("Configure Comp", url=comp_url, type="secondary", icon="⚙️")
        else:
            st.error("Could not create competition sheet (DB).", icon="❌")
        

        