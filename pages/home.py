import streamlit as st
from util.controller import AppController
from pages.sidebar import load_sidebar

st.set_page_config(page_title="AeroScore", page_icon="✈️", layout="wide")
st.title("✈️ Aerobatics Scoring System")

load_sidebar()

app_ctrl = AppController.connect()
if app_ctrl.is_user_logged_in():
    assert app_ctrl.db is not None
    st.header(app_ctrl.db.title)

elif app_ctrl.is_comp_setup():
    assert app_ctrl.db is not None
    st.header(app_ctrl.db.title)

else:
    st.write("No competition found. Please open the link sent by your Admin with the competition id.")

