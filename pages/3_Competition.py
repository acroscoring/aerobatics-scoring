import streamlit as st
from util.google_services import get_service

# Page Configuration (Must be the first Streamlit command)
st.set_page_config(page_title="Competition", page_icon="🏆", layout="wide")

# Main Content
st.title("🏆 Competition Scoring")
    
# Query Params
query_params = st.query_params
comp_id: str = query_params.get("comp_id", "")
if not comp_id:
    st.error("❌ Invalid Competition Link")
    st.stop()

# Get Services
service = get_service()
sheet = service.get_sheet_by_id(comp_id)

if not sheet:
    st.error("❌ Competition Not Found")
    st.info("The ID in the link is invalid or you do not have access.")
    st.stop()

# Valid Sheet Found - Show Title
st.header(sheet.title)

service.get_scoring_sheet_data()