import streamlit as st
from typing import Any, List, Dict, cast
import util.google_model as gm
import util.scoring_model as sm
import util.security_model as sec
from PIL.Image import Image
from pandas import DataFrame
import extra_streamlit_components as stx # type: ignore
import uuid

# --------------------------------------------------------------------------------------------------------------

class MissingCompId(Exception):
    pass

class MissingJudgeId(Exception):
    pass

class InvalidJudgeId(Exception):
    pass

# --------------------------------------------------------------------------------------------------------------
# Session State
# --------------------------------------------------------------------------------------------------------------

def _get_session_state(name: str) -> Any:
    return st.session_state.get(name, None)

def _set_session_state(name: str, value: Any) -> Any:
    st.session_state[name] = value
    return _get_session_state(name)

def _delete_session_state(name: str):
    if name in st.session_state:
        del st.session_state[name]

def get_session_state_singleton(name: str, value: Any) -> Any:
    if name not in st.session_state:
        _set_session_state(name, value)
    
    return _get_session_state(name)

# --------------------------------------------------------------------------------------------------------------
# Comp ID
# --------------------------------------------------------------------------------------------------------------

def _set_comp_id_session_state(sheet_id: str) -> str:
    return _set_session_state("comp_id", sheet_id)

def _get_comp_id_session_state() -> str:
    return _get_session_state("comp_id")

#def _delete_comp_id_session_state():
#    _delete_session_state("comp_id")

def _get_comp_id_from_query_params() -> str:
    comp_id = st.query_params.get("comp_id")
    
    if not comp_id:
        raise MissingCompId("No competition ID found. Please use the link provided by the competition admin.")
    
    _set_comp_id_session_state(comp_id)
    return comp_id

# --------------------------------------------------------------------------------------------------------------
# Judge ID
# --------------------------------------------------------------------------------------------------------------

def _set_judge_id_session_state(judge_id: str) -> str:
    return _set_session_state("judge_id", judge_id)

def _get_judge_id_from_query_params() -> str:
    judge_id = st.query_params.get("judge_id")
    
    if not judge_id:
        raise MissingJudgeId("No judge ID found in URL (query parameter judge_id).")
    
    judge_id_int = int(judge_id)
    
    if (judge_id_int < 1) or (judge_id_int > 99):
        raise InvalidJudgeId("Invalid judge ID (not between 01 and 99).")

    _set_judge_id_session_state(judge_id)
    return judge_id

# --------------------------------------------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------------------------------------------

def _error_and_stop(e: Exception):
    st.error(e, icon="❌")
    st.stop()

def _get_comp_id_or_stop() -> str:
    try:
        return _get_comp_id_from_query_params()
    except MissingCompId as e:
        comp_id = _get_comp_id_session_state()
        if comp_id:
            return comp_id
        else:
            _error_and_stop(e)
            raise    
    except Exception as e:
        _error_and_stop(e)
        raise

def _get_db_or_stop() -> gm.SheetDB:
    try:
        comp_id = _get_comp_id_session_state()
        if not comp_id:
            MissingCompId("No competition ID found in session state.")
        return gm.SheetDB.connect(comp_id)
    except Exception as e:
        _error_and_stop(e)
        raise

def create_sheet_db_and_admin(comp_name: str, user_name: str, admin_email: str, password: str):
    try:
        user = sm.try_create_user(user_name, admin_email, password, "admin")
        sheet_id = gm.create_competition_sheet_db(comp_name=comp_name, admin_email=admin_email)
        _set_comp_id_session_state(sheet_id)
        db = _get_db_or_stop()
        db.register_user(user)
    except Exception as e:
        _error_and_stop(e)


class CompScoreSheetAi:
    def __init__(self):
        _get_comp_id_or_stop()
        self._db = _get_db_or_stop()

    def get_comp_title(self) -> str:
        return self._db.sheet_title
    
    def get_score_sheet_singleton(self) -> sm.ScoreSheet:
        return get_session_state_singleton("current_score_sheet", None)

    def get_scoring_using_ai(self, image: Image):
        try:
            new_score_sheet = gm.get_scoring_sheet_data_using_ai(image)
            if new_score_sheet:
                _set_session_state("current_score_sheet", new_score_sheet)
            else:
                raise Exception("AI didn't return any score sheet result.")
        except Exception as e:
            _error_and_stop(e)

    def save_scoring_sheet_data_to_db(self, pilot_id: int, flight_num: int, judge_id: int, df: DataFrame):
        try:
            raw_data = cast(List[Dict[str, Any]], df.to_dict(orient="records")) # type: ignore

            # Re-construct Figures safely
            updated_figures = [sm.FigureScore(**row) for row in raw_data]

            final_score_sheet = sm.ScoreSheet(
                pilot_id=pilot_id,
                flight_number=flight_num,
                judge_id=judge_id,
                figures=updated_figures
            )

            self._db.save_scoring_sheet_data(final_score_sheet)
        except Exception as e:
            _error_and_stop(e)

    def reset_comp_ai_ui(self):
        _delete_session_state("current_score_sheet")
        _delete_session_state("widget_uploader")
        _delete_session_state("widget_camera")


class RegisterNewJudge:
    def __init__(self):
        try:
            _get_comp_id_from_query_params()
            self._db = _get_db_or_stop()
            judge_id = _get_judge_id_from_query_params()
            self.judge_details = self._db.get_judge_details(judge_id)
        except Exception as e:
            _error_and_stop(e)

    def get_comp_title(self) -> str:
        return self._db.sheet_title

    def create_judge_user(self, user_name: str, password: str):
        try:
            user = sm.try_create_user(user_name, self.judge_details.email, password, "judge")
            self._db.register_user(user)
        except Exception as e:
            _error_and_stop(e)


class AuthService:
    def __init__(self):
        self._cookie_name = "aeroscore_auth_token"
        self._cookie_manager = get_session_state_singleton("cookie_manager", stx.CookieManager())
        cookies = self._cookie_manager.get_all()

        comp_id = None
        try:
            comp_id = _get_comp_id_or_stop()
        except MissingCompId:
            comp_id = None

        token = cookies.get(self._cookie_name)
        if token:
            auth_user = sec.decode_token(token)
            if auth_user:
                _set_session_state("auth_user", auth_user)
                self.auth_user = auth_user

                if not comp_id:
                    comp_id = auth_user.comp_id
                    _set_comp_id_session_state(auth_user.comp_id)
                
                if comp_id != auth_user.comp_id:
                    self.logout()

        self.comp_id = comp_id
        self._db = _get_db_or_stop()


    def login(self, email: str, password: str):
        try:
            user = dict(self._db.authenticate_user(email=email, password=password))
            user["comp_id"] = _get_comp_id_or_stop()
            auth_user = sm.try_create_authuser(user)
            _set_session_state("auth_user", auth_user)
            self.auth_user = auth_user
            token = sec.create_token(auth_user)
            self._cookie_manager.set(self._cookie_name, token, sec.get_token_expire())
            st.toast(f"Logged in {auth_user.username}! Reloading...")
            st.rerun()
        except Exception as e:
            _error_and_stop(e)

    def forgot_password(self, email: str):
        try:
            self._db.get_user_by_email(email)    
            temp_pass = str(uuid.uuid4())[:6] # Simple 6 char random string
            self._db.update_user_password(email, temp_pass)
            # Send email with new password
            st.toast("Check your email for the temporary password.")
        except Exception as e:
            _error_and_stop(e)

    def logout(self):
        self._cookie_manager.delete(self._cookie_name)
        _delete_session_state("auth_user")
        self.auth_user = None
        st.rerun()
        
