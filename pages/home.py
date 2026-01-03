import streamlit as st
from pages.header import load
import util.messages as msg

app_ctrl = load(title="✈️ Aerobatics Scoring System")

if app_ctrl.is_user_logged_in():
    assert app_ctrl.db is not None
    st.header(app_ctrl.db.title)

elif app_ctrl.is_comp_setup():
    assert app_ctrl.db is not None
    st.header(app_ctrl.db.title)

else:
    st.warning(msg.ErrorMsgs.NO_COMP_FOUND, icon="⚠️")

