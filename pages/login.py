import streamlit as st
from util.controller import AuthService

st.set_page_config(page_title="Registration", page_icon="📝", layout="wide")
st.title("📝 Create Judge User to Upload Scores")

controller = AuthService()
st.header(controller.get_comp_title())

controller.login()