import streamlit as st
from util.controller import AppController
from streamlit_cookies_manager import CookieManager # type: ignore

def load(title: str) -> AppController:
    cookies = CookieManager()
    if not cookies.ready():
        st.stop()

    app_ctrl = AppController.connect(cookies)
    
    st.title(title, text_alignment="center")

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