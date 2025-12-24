import streamlit as st
from services import get_service

def render_admin_dashboard() -> None:
    st.header("🛠 Admin Dashboard")
    st.write("Create a new competition.")

    with st.form("create_comp_form"):
        comp_name: str = st.text_input("Competition Name", placeholder="e.g. Australian National & Freestyle Championships 2025")
        admin_email: str = st.text_input("Admin Gmail", placeholder="you@gmail.com")
        
        submitted: bool = st.form_submit_button("🚀 Create Competition")

        if submitted:
            if not comp_name or not admin_email:
                st.warning("Please fill in both fields.")
                return

            with st.spinner("Cloning template and configuring permissions..."):
                service = get_service()
                new_sheet_id = service.create_competition_sheet(
                    comp_name=comp_name,
                    admin_email=admin_email
                )

            if new_sheet_id:
                st.success("Competition Created Successfully and Sent to Your Email!")
                
                st.link_button("Open '{comp_name}' Google Sheet!", url="https://docs.google.com/spreadsheets/d/{new_sheet_id}", type="primary", icon="⚙️")

                st.link_button("Open '{comp_name}' Page!", url="/?comp_id={new_sheet_id}", type="secondary", icon="🚀")
                
            else:
                st.error("Could not create competition.")