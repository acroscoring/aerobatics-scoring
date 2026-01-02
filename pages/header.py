import streamlit as st
from util.controller import AppController

def load(page_title: str, page_icon: str, frame_title: str) -> AppController:

    #st.set_page_config(page_title=page_title, page_icon=page_icon, layout="wide")
    st.title(frame_title, text_alignment="center")

    app_ctrl = AppController.connect()
    app_ctrl.refresh_auth()

    with st.sidebar:
        if app_ctrl.is_comp_setup():
            assert app_ctrl.db is not None
            st.badge(app_ctrl.db.title)
        
        if app_ctrl.is_user_logged_in():
            assert app_ctrl.auth_user is not None
            user = app_ctrl.auth_user
            user_id = f" {user.id}" if user.id else ""
            st.badge(f"{user.username} ({user.role.capitalize()}{user_id})", color="green")

        with st.expander("Debug State"):
            st.write(st.session_state)

    return app_ctrl