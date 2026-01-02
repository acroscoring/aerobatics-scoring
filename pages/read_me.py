import streamlit as st
from pages.sidebar import load_sidebar

st.set_page_config(page_title="Read Me", page_icon="📖", layout="wide")
st.title("📖 Documentation")

load_sidebar()