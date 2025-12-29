import streamlit as st
from typing import Any
import util.google_services as gs

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

def reset_session_state_to_none(name: str):
    st.session_state[name] = None

def get_session_state_singleton(name: str, value: Any) -> Any:
    if name not in st.session_state:
        set_session_state(name, value)
    
    return get_session_state(name)

# --------------------------------------------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------------------------------------------

def error_and_stop(e: Exception):
    st.error(e, icon="❌")
    st.stop()

def get_comp_id_or_stop() -> str:
    try:
        return get_comp_id_from_query_params()
    except MissingCompId as e:
        comp_id = get_comp_id_session_state()
        if comp_id:
            return comp_id
        else:
            error_and_stop(e)
            raise    
    except Exception as e:
        error_and_stop(e)
        raise

def get_db_or_stop(comp_id: str) -> gs.SheetDB:
    try:
        return gs.SheetDB.connect(comp_id)
    except Exception as e:
        error_and_stop(e)
        raise


# --------------------------------------------------------------------------------------------------------------
# Comp ID
# --------------------------------------------------------------------------------------------------------------

class MissingCompId(Exception):
    pass

def set_comp_id_session_state(sheet_id: str) -> str:
    return set_session_state("comp_id", sheet_id)

def get_comp_id_session_state() -> str:
    return get_session_state("comp_id")

def delete_comp_id_session_state():
    delete_session_state("comp_id")

def get_comp_id_from_query_params() -> str:
    comp_id = st.query_params.get("comp_id")
    
    if not comp_id:
        raise MissingCompId("No competition ID found in URL (query parameter comp_id).")
    
    set_comp_id_session_state(comp_id)
    return comp_id