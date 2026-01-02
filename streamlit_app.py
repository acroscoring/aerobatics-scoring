import streamlit as st

pages = [
    st.Page("pages/home.py", title="Home", icon="✈️"),
    st.Page("pages/read_me.py", title="Read Me", icon="📖"),
    st.Page("pages/admin.py", title="Admin", icon="⚙️"),
    st.Page("pages/register.py", title="Register", icon="📝"),
    st.Page("pages/login.py", title="Login", icon="🔐"),
    st.Page("pages/comp.py", title="Competition", icon="🏆"),
]

page = st.navigation(pages)
page.run()