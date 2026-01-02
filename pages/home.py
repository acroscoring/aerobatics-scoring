import streamlit as st
from pages.header import load

app_ctrl, cookies = load(title="✈️ Aerobatics Scoring System")

if app_ctrl.is_user_logged_in():
    assert app_ctrl.db is not None
    st.header(app_ctrl.db.title)

elif app_ctrl.is_comp_setup():
    assert app_ctrl.db is not None
    st.header(app_ctrl.db.title)

else:
    st.write("No competition found. Please open the link sent by your Admin with the competition id.")

