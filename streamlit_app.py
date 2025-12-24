import streamlit as st
from admin_page import render_admin_dashboard
from comp_page import render_competition_interface
#from check_quota import check_quotas

def main() -> None:
    # Page Config
    st.set_page_config(page_title="AeroScore", page_icon="✈️")

    # Query Params
    query_params = st.query_params
    comp_id: str = query_params.get("comp_id", "")

    #check_quotas()

    # ROUTING LOGIC
    if not comp_id:
        # Route 1: No ID provided -> Show Admin Dashboard
        render_admin_dashboard()
    else:
        # Route 2: ID provided -> Show Judge Interface
        render_competition_interface(comp_id)

if __name__ == "__main__":
    main()