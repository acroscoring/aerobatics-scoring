import streamlit as st
from typing import Any

def get_session_state(name: str) -> Any:
    return st.session_state.get(name, None)

def set_session_state(name: str, value: Any) -> Any:
    st.session_state[name] = value
    return get_session_state(name)

def delete_session_state(name: str):
    if name in st.session_state:
        del st.session_state[name]

def reset_session_state_to_none(name: str):
    st.session_state[name] = None

def get_session_state_singleton(name: str, value: Any) -> Any:
    if name not in st.session_state:
        set_session_state(name, value)
    
    return get_session_state(name)