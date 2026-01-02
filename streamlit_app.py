import streamlit as st

pages = [
    st.Page("pages/home.py", title="Home", icon="✈️"),
    st.Page("pages/read_me.py", title="Read Me", icon="📖"),
    st.Page("pages/admin.py", title="Admin", icon="⚙️"),
]

page = st.navigation(pages)
page.run()