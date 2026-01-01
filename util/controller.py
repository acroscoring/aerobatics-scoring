import streamlit as st
from typing import Any, List, Dict, cast
import util.google_model as gm
import util.data_model as dm
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
# UI
# --------------------------------------------------------------------------------------------------------------

def _error_and_stop(e: Exception):
    st.error(e, icon="❌")
    st.stop()

# --------------------------------------------------------------------------------------------------------------
# Comp ID & DB
# --------------------------------------------------------------------------------------------------------------

class CompDB:
    def __init__(self, comp_id: str):
        self.db = gm.SheetDB.connect(comp_id)
        self.comp_id = comp_id
        CompDB._set_id_session_state(comp_id)
        
    @classmethod
    def connect(cls, sheet_id: str) -> "CompDB":
        session_key = f"CompDB_{sheet_id}"
        return get_session_state_singleton(session_key, cls(sheet_id))

    @classmethod
    def connect_or_stop(cls) -> "CompDB":
        try:
            comp_id = CompDB.get_id_or_stop()
            return CompDB.connect(comp_id)
        except Exception as e:
            _error_and_stop(e)
            raise

    @classmethod
    def create(cls, comp_name: str, user_name: str, admin_email: str, password: str) -> "CompDB":
        try:
            user = dm.User.create(user_name, admin_email, password, "admin", None)
            db = gm.SheetDB.create(comp_name=comp_name, admin_email=admin_email)
            db.register_user(user)
            return CompDB.connect(db.id)
        except Exception as e:
            _error_and_stop(e)
            raise

    @staticmethod
    def _set_id_session_state(sheet_id: str) -> str:
        return _set_session_state("comp_id", sheet_id)

    @staticmethod
    def _get_id_session_state() -> str:
        return _get_session_state("comp_id")

    @staticmethod
    def _delete_id_session_state():
        _delete_session_state("comp_id")

    @staticmethod
    def _get_id_from_query_params() -> str:
        comp_id = st.query_params.get("comp_id")
        
        if not comp_id:
            raise MissingCompId("No competition ID found.")
        
        return comp_id
    
    @staticmethod
    def get_id() -> str:
        try:
            return CompDB._get_id_from_query_params()
        except MissingCompId as e:
            comp_id = CompDB._get_id_session_state()
            if comp_id:
                return comp_id
            else:
                raise MissingCompId(f"Missing competition ID.")
        except Exception as e:
            raise Exception(f"Missing competition ID: {e}")

    @staticmethod
    def get_id_or_stop() -> str:
        try:
            return CompDB.get_id()   
        except Exception as e:
            _error_and_stop(e)
            raise

# --------------------------------------------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------------------------------------------

class AuthService:
    def __init__(self):
        self._cookie_name = "aeroscore_auth_token"
        self._cookie_manager = get_session_state_singleton("cookie_manager", stx.CookieManager())

        auth_user = _get_session_state("auth_user")
        if not auth_user:
            cookies = self._cookie_manager.get_all()
            token = cookies.get(self._cookie_name)
            if token:
                auth_user = sec.decode_token(token)
            
        self._set_user(auth_user)

    def _set_user(self, auth_user: dm.AuthUser | None):
        _set_session_state("auth_user", auth_user)
        self.user = auth_user

    def login(self, db: gm.SheetDB, email: str, password: str):
        try:
            user = db.authenticate_user(email=email, password=password)
            auth_user = dm.AuthUser.from_user(user=user, comp_id=db.id)
            token = sec.create_token(auth_user)
            self._cookie_manager.set(self._cookie_name, token, sec.get_token_expire())
            self._set_user(auth_user)
            st.toast(f"Logged in {auth_user.username}! Reloading...")
            st.rerun()
        except Exception as e:
            _error_and_stop(e)

    def forgot_password(self, db: gm.SheetDB, email: str):
        try:
            db.get_user_by_email(email)    
            temp_pass = str(uuid.uuid4())[:6]
            db.update_user_password(email, temp_pass)
            # Send email with new password
            st.toast("Check your email for the temporary password.")
        except Exception as e:
            _error_and_stop(e)

    def logout(self):
        if self._cookie_manager.get(self._cookie_name):
            self._cookie_manager.delete(self._cookie_name)
        
        self._set_user(None)
        st.rerun()

# --------------------------------------------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------------------------------------------

class AppController:
    def __init__(self):
        self._auth = AuthService()
        self.auth_user = None
        comp_id_from_auth = None
        if self._auth.user:
            self.auth_user = self._auth.user
            comp_id_from_auth = self._auth.user.comp_id
        
        comp_id_from_db = None
        try:
            comp_id_from_db = CompDB.get_id()
        except MissingCompId:
            pass

        comp_id = comp_id_from_db if comp_id_from_db else comp_id_from_auth
        
        self.db = CompDB.connect(comp_id).db if comp_id else None

        if (comp_id is None) or (comp_id != comp_id_from_auth):
            self._auth.logout()
    
    def is_comp_setup(self) -> bool:
        return self.db is not None
    
    def is_user_logged_in(self) -> bool:
        return self.auth_user is not None
    
    def login(self, email: str, password: str):
        if self.db:
            self._auth.login(self.db, email, password)
        else:
            raise Exception("Competition not set up for login!")

    def forgot_password(self, email: str):
        if self.db:
            self._auth.forgot_password(self.db, email)
        else:
            raise Exception("Competition not set up for forgot password!")
        
    def logout(self):
        self._auth.logout()
        
# --------------------------------------------------------------------------------------------------------------
# Judge
# --------------------------------------------------------------------------------------------------------------

class Register:
    def __init__(self):
        try:
            self.app_ctrl = AppController()

            if self.app_ctrl.is_comp_setup():
                assert self.app_ctrl.db is not None
                self.db = self.app_ctrl.db
            else:
                raise Exception(f"No competition found. Please use the link provided by your admin (via email) to register.")
            
            if self.app_ctrl.is_user_logged_in():
                raise Exception(f"Logout to register a new user.")
            else:
                self.auth = self.app_ctrl._auth

            judge_id = Register._get_judge_id_from_query_params()
            self.judge_details = self.db.get_judge_details(judge_id)
        except Exception as e:
            _error_and_stop(e)

    def create_judge_user(self, user_name: str, password: str):
        try:
            user = dm.User.create(user_name, self.judge_details.email, password, "judge", self.judge_details.id)
            self.db.register_user(user)
        except Exception as e:
            _error_and_stop(e)

    @staticmethod
    def _get_judge_id_from_query_params() -> int:
        judge_id = st.query_params.get("judge_id")
        
        if not judge_id:
            raise MissingJudgeId("No judge ID found in URL (query parameter judge_id).")

        return int(judge_id)

# --------------------------------------------------------------------------------------------------------------
# Score Sheet
# --------------------------------------------------------------------------------------------------------------

class CompScoreSheetAi:
    def __init__(self):
        try:
            self.app_ctrl = AppController()

            if self.app_ctrl.is_comp_setup():
                assert self.app_ctrl.db is not None
                self.db = self.app_ctrl.db
            else:
                raise Exception(f"No competition found. Please use the link provided by your admin (via email).")
            
            if not self.app_ctrl.is_user_logged_in():
                raise Exception(f"Login to scan add a score sheet.")
            else:
                self.auth = self.app_ctrl._auth
        except Exception as e:
            _error_and_stop(e)
    
    def get_score_sheet_singleton(self) -> dm.ScoreSheet:
        return get_session_state_singleton("current_score_sheet", None)

    def get_scoring_using_ai(self, image: Image):
        try:
            new_score_sheet = self.db.get_scoring_sheet_data_using_ai(image)
            if new_score_sheet:
                _set_session_state("current_score_sheet", new_score_sheet)
            else:
                raise Exception("AI didn't return any score sheet result.")
        except Exception as e:
            _error_and_stop(e)

    def save_scoring_sheet_data_to_db(self, pilot_id: int, flight_num: int, judge_id: int, df: DataFrame):
        try:
            raw_data = cast(List[Dict[str, Any]], df.to_dict(orient="records")) # type: ignore

            updated_figures = [dm.FigureScore(**row) for row in raw_data]

            final_score_sheet = dm.ScoreSheet(
                pilot_id=pilot_id,
                flight_number=flight_num,
                judge_id=judge_id,
                figures=updated_figures
            )

            self.db.save_scoring_sheet_data(final_score_sheet)
        except Exception as e:
            _error_and_stop(e)

    def reset_comp_ai_ui(self):
        _delete_session_state("current_score_sheet")
        _delete_session_state("widget_uploader")
        _delete_session_state("widget_camera")






        
