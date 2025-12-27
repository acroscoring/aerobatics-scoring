import streamlit as st
from util.google_services import get_google_service
from streamlit_javascript import st_javascript # type: ignore

# Page Configuration (Must be the first Streamlit command)
st.set_page_config(page_title="Admin", page_icon="⚙️", layout="wide")

# Main Content
st.title("⚙️ Administration")

st.write("Create a new competition.")

with st.sidebar: # To not consume space in the UI, Streamlit bug
    current_url = st_javascript("window.parent.location.href") # Needs to run 2x, 1st time it's zero then URL

with st.form("create_comp_form"):
    comp_name: str = st.text_input("Competition Name", placeholder="e.g. Australian National & Freestyle Championships 2025")
    admin_email: str = st.text_input("Admin Gmail", placeholder="you@gmail.com")
    submitted: bool = st.form_submit_button("🚀 Create Competition")

    if submitted:
        if not comp_name or not admin_email:
            st.warning("Please fill in both fields.")

        with st.spinner("Creating competition file..."):
            service = get_google_service()
            new_sheet_id, comp_url = service.create_competition_sheet(comp_name=comp_name, admin_email=admin_email, current_url=current_url) or (None, None)

        if new_sheet_id and comp_url:
            st.success("Competition created successfully and sent to your email!")
            st.link_button("Open Comp App!", url=comp_url, type="secondary", icon="⚙️")
        else:
            st.error("Could not create competition.")