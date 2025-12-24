import streamlit as st
from services import get_service

def render_competition_interface(sheet_id: str) -> None:
    """
    Load the specific competition DB and show the scoring form.
    """
    service = get_service()
    sheet = service.get_sheet_by_id(sheet_id)
    
    if not sheet:
        st.error("❌ Competition Not Found")
        st.info("The ID in the link is invalid or you do not have access.")
        if st.button("Go to Admin Home"):
            st.query_params.clear()
            st.rerun()
        return

    # Valid Sheet Found - Show Title
    st.title(f"Scoring: {sheet.title}")
    st.caption(f"Database ID: {sheet_id}")
    
    # ... (Judge Logic goes here later) ...
    st.info("📸 Judge Camera Input would appear here.")