import streamlit as st
from util.controller import AppController

def load_sidebar():
    pages = [
        st.Page("pages/home.py", title="Home", icon="✈️"),
        st.Page("pages/read_me.py", title="Read Me", icon="📖"),
        st.Page("pages/admin.py", title="Admin", icon="⚙️"),
    ]

    app_ctrl = AppController.connect()
    app_ctrl.refresh_auth()
    if app_ctrl.is_user_logged_in() :
        pages.append(st.Page("pages/login.py", title="Login", icon="🔐"))
        pages.append(st.Page("pages/comp.py", title="Competition", icon="🏆"))
        
        with st.sidebar:
            assert app_ctrl.db is not None
            st.markdown(f"##### {app_ctrl.db.title}")
            
            assert app_ctrl.auth_user is not None
            user = app_ctrl.auth_user
            user_id = f" ({user.id})" if user.id else ""
            st.caption(f"{user.role.capitalize()}{user_id}: {user.username}")

    elif app_ctrl.is_comp_setup():
        pages.append(st.Page("pages/login.py", title="Login", icon="🔐"))
        pages.append(st.Page("pages/register.py", title="Register", icon="📝"))
    else:
        pass

    with st.sidebar:
        st.write(st.session_state)

    page = st.navigation(pages)
    page.run()