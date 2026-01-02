import streamlit as st
from typing import Any, Callable

# --------------------------------------------------------------------------------------------------------------
# Session State
# --------------------------------------------------------------------------------------------------------------

def get_session_state(name: str) -> Any:
    return st.session_state.get(name, None)

def set_session_state(name: str, value: Any) -> Any:
    st.session_state[name] = value
    return get_session_state(name)

def delete_session_state(name: str):
    if name in st.session_state:
        del st.session_state[name]

def get_session_state_singleton(name: str, call_lambda: Callable[[], Any]) -> Any:
    if name not in st.session_state:
        set_session_state(name, call_lambda())
    
    return get_session_state(name)