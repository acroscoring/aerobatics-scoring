import streamlit as st
from util.google_services import create_competition_sheet_db
from util.scoring_services import try_create_user
from util.streamlit_services import error_and_stop, set_comp_id_session_state, get_db_or_stop

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
        try:
            user = try_create_user(user_name, admin_email, password, "admin")
            with st.spinner("Creating competition..."):
                sheet_id = create_competition_sheet_db(comp_name=comp_name, admin_email=admin_email)
                
                st.success(f"Competition created successfully and an email sent to you {user.username}!", icon="✅")
                set_comp_id_session_state(sheet_id)
                
                db = get_db_or_stop(sheet_id)
                db.register_user(user)
                st.success(f"Admin user ({user.username}) added!", icon="✅")
                
                # Login?
        except Exception as e:
            error_and_stop(e)
        

        