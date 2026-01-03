import streamlit as st
from pages.header import load
import util.messages as msg

app_ctrl = load(title="⚙️ Administration")

if app_ctrl.is_user_logged_in():
    assert app_ctrl.db is not None
    st.header(app_ctrl.db.title)
    st.subheader("👩🏼‍💻 Admin Controls")
    st.divider()

elif app_ctrl.is_comp_setup():
    assert app_ctrl.db is not None
    st.header(app_ctrl.db.title)
    st.error(msg.ErrorMsgs.LOGIN_TO_MNG_COMP, icon="❌")
    st.info("Logout of the competition to create a new competition (or reload the page).", icon="ℹ️")

else:
    st.header("Create a New Competition")

    with st.form("create_comp_form"):
        comp_name: str = st.text_input("Competition Name", placeholder="e.g. Australian National & Freestyle Championships 2025", help="A name to use in the pages", icon="🏆", max_chars=70)
        admin_email: str = st.text_input("Email", placeholder="you@gmail.com", help="Valid email to send access links", icon="📧")
        user_name: str = st.text_input("Name", placeholder="Maverik", help="Just used for salutation", icon="👋🏻", max_chars=50)
        password: str = st.text_input("Password", type="password", help="Something so the system knows it's you", icon="🔑")
        submitted: bool = st.form_submit_button("Create Competition", icon="🚀", type="primary")

        if submitted:
            with st.spinner("Creating competition...", show_time=True):
                app_ctrl.create_new_comp(comp_name=comp_name, user_name=user_name, admin_email=admin_email, password=password)
                st.success(f"Competition created successfully and an email was sent to you {user_name}!", icon="✅")
                st.toast("Loging you in...", icon="🔐")
                app_ctrl.login(admin_email, password)
                  
        