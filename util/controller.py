import streamlit as st
#from typing import Any, List, Dict, cast
import util.google_model as gm
import util.data_model as dm
import util.security_model as sec
import util.streamlit_model as sm
from PIL.Image import Image
from pandas import DataFrame
import uuid
from streamlit_cookies_manager import CookieManager # type: ignore
import util.constants as const
from streamlit.delta_generator import DeltaGenerator

# --------------------------------------------------------------------------------------------------------------

class MissingCompId(Exception):
    pass

class MissingJudgeId(Exception):
    pass

class judgeIdAlreadyRegistered(Exception):
    pass

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
        return sm.get_session_state_singleton(session_key, lambda: cls(sheet_id))

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
            user = dm.User.create(user_name, admin_email, password, "admin", "")
            db = gm.SheetDB.create(comp_name=comp_name, admin_email=admin_email)
            db.users.register(user)
            return CompDB.connect(db.id)
        except Exception as e:
            _error_and_stop(e)
            raise

    @staticmethod
    def _set_id_session_state(sheet_id: str) -> str:
        return sm.set_session_state("comp_id", sheet_id)

    @staticmethod
    def _get_id_session_state() -> str:
        return sm.get_session_state("comp_id")

    @staticmethod
    def delete_id_session_state():
        sm.delete_session_state("comp_id")

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
    def __init__(self, cookies: CookieManager):
        self._cookie_name = "auth_token"
        self.user = None
        self._cookies = cookies

    def refresh(self, cookies: CookieManager):
        self._cookies = cookies
        auth_user = sm.get_session_state("auth_user")
        if not auth_user:
            token = cookies.get(self._cookie_name)
            if token:
                auth_user = sec.decode_token(token)

        self._set_user(auth_user)

    @classmethod
    def connect(cls, cookies: CookieManager) -> "AuthService":
        session_key = f"AuthService"
        return sm.get_session_state_singleton(session_key, lambda: cls(cookies))
    
    def _set_user(self, auth_user: dm.AuthUser | None):
        sm.set_session_state("auth_user", auth_user)
        self.user = auth_user
        
    def login(self, db: gm.SheetDB, email: str, password: str):
        try:
            user = db.users.authenticate(email=email, password=password)
            auth_user = dm.AuthUser.from_user(user=user, comp_id=db.id)
            token = sec.create_token(auth_user)
            self._cookies[self._cookie_name] = token
            self._cookies.save()
            self._set_user(auth_user)
        except Exception as e:
            _error_and_stop(e)

    def forgot_password(self, db: gm.SheetDB, email: str):
        try:
            _ , user = db.users.get_by_email(email)
            user.password = str(uuid.uuid4())[:6]
            db.users.update(user)
            self.logout()
            # Send email with new password
            st.toast("Check your email for the temporary password.")
        except Exception as e:
            _error_and_stop(e)

    def logout(self):
        del self._cookies[self._cookie_name]
        self._cookies.save()
        self._set_user(None)

# --------------------------------------------------------------------------------------------------------------
# App Controller
# --------------------------------------------------------------------------------------------------------------

class AppController:
    def __init__(self, cookies: CookieManager):
        self._auth = AuthService.connect(cookies)
        self.auth_user = None
        self._comp_db = None
        self.db = None

    def refresh_auth(self, cookies: CookieManager):
        self._auth.refresh(cookies)
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
        self._comp_db = CompDB.connect(comp_id) if comp_id else None
        self.db = CompDB.connect(comp_id).db if comp_id else None

        if (comp_id is None) or (comp_id != comp_id_from_auth):
            self._auth.logout()
            self.auth_user = None
    
    @classmethod
    def connect(cls, cookies: CookieManager) -> "AppController":
        session_key = f"AppController"
        ctlr: AppController = sm.get_session_state_singleton(session_key, lambda: cls(cookies))
        ctlr.refresh_auth(cookies)
        return ctlr
    
    def is_comp_setup(self) -> bool:
        return self.db is not None
    
    def is_user_logged_in(self) -> bool:
        return self.auth_user is not None
    
    def create_new_comp(self, comp_name: str, user_name: str, admin_email: str, password: str):
        self._comp_db = CompDB.create(comp_name=comp_name, user_name=user_name, admin_email=admin_email, password=password)
        self.db = self._comp_db.db
    
    def login(self, email: str, password: str):
        if self.db:
            self._auth.login(self.db, email, password)
            self.auth_user = self._auth.user
            assert self.auth_user is not None
            st.toast(f"Logged in {self.auth_user.username}!")
            st.rerun()
        else:
            raise Exception("Competition not set up for login!")

    def forgot_password(self, email: str):
        if self.db:
            self._auth.forgot_password( self.db, email)
        else:
            raise Exception("Competition not set up for forgot password!")
        
    def logout_user(self):
        self._auth.logout()
        self.auth_user = None
        st.rerun()
    
    def logout_comp(self):
        if self._comp_db:
            self._comp_db.delete_id_session_state()
        self._comp_db = None
        self.db = None
        self.logout_user()

# --------------------------------------------------------------------------------------------------------------
# Judge
# --------------------------------------------------------------------------------------------------------------

class Register:
    def __init__(self, app_ctrl: AppController):
        try:
            self.app_ctrl = app_ctrl

            if self.app_ctrl.is_comp_setup():
                assert self.app_ctrl.db is not None
                self.db = self.app_ctrl.db
            else:
                raise Exception(const.ErrorMsgs.NO_COMP_FOUND)
            
            judge_id = Register._get_judge_id_from_query_params()
            _ , self.judge_details = self.db.judges.get_by_id(judge_id)
            try:
                self.db.users.get_by_role_and_id(role="judge", id=judge_id)
                raise judgeIdAlreadyRegistered(f"Judge ID {judge_id} is already registered.")
            except gm.UserRoleAndIdNotFound as e:
                pass
        except Exception as e:
            _error_and_stop(e)

    @classmethod
    def connect(cls, app_ctrl: AppController) -> "Register":
        session_key = f"Register"
        return sm.get_session_state_singleton(session_key, lambda: cls(app_ctrl))
    
    def create_judge_user(self, user_name: str, password: str):
        try:
            user = dm.User.create(user_name, self.judge_details.email, password, "judge", self.judge_details.id)
            self.db.users.register(user)
        except Exception as e:
            _error_and_stop(e)

    @staticmethod
    def _get_judge_id_from_query_params() -> int:
        judge_id = st.query_params.get("judge_id")
        
        if not judge_id:
            raise MissingJudgeId(const.ErrorMsgs.NO_JUDGE_ID)

        return int(judge_id)

# --------------------------------------------------------------------------------------------------------------
# Score Sheet
# --------------------------------------------------------------------------------------------------------------

class CompScoreSheetAi:
    def __init__(self, app_ctrl: AppController):
        try:
            self.app_ctrl = app_ctrl

            if self.app_ctrl.is_comp_setup():
                assert self.app_ctrl.db is not None
                self.db = self.app_ctrl.db
            else:
                raise Exception(const.ErrorMsgs.NO_COMP_FOUND)
            
            if not self.app_ctrl.is_user_logged_in():
                raise Exception(const.ErrorMsgs.LOGIN_TO_MNG_COMP)
            else:
                self.auth_user = self.app_ctrl.auth_user
        except Exception as e:
            _error_and_stop(e)
    
    @classmethod
    def connect(cls, app_ctrl: AppController) -> "CompScoreSheetAi":
        session_key = f"CompScoreSheetAi"
        return sm.get_session_state_singleton(session_key, lambda: cls(app_ctrl))
    
    def get_score_sheet_singleton(self) -> dm.ScoreSheet:
        return sm.get_session_state_singleton("current_score_sheet", lambda: None)

    def get_scoring_using_ai(self, image: Image, status_area: DeltaGenerator):
        try:
            new_score_sheet = gm.get_scoring_sheet_data_using_ai(image, status_area)
            if new_score_sheet:
                sm.set_session_state("current_score_sheet", new_score_sheet)
            else:
                raise Exception("AI didn't return any score sheet result.")
        except Exception as e:
            _error_and_stop(e)

    def save_scoring_sheet_data_to_db(self, pilot_id: int, flight_num: int, judge_id: int, df: DataFrame):
        pass
        # try:
        #     raw_data = cast(List[Dict[str, Any]], df.to_dict(orient="records")) # type: ignore

        #     updated_figures = [dm.FigureScore(**row) for row in raw_data]

        #     final_score_sheet = dm.ScoreSheet(
        #         pilot_id=pilot_id,
        #         flight_number=flight_num,
        #         judge_id=judge_id,
        #         figures=updated_figures
        #     )

        #     self.db.save_scoring_sheet_data(final_score_sheet)
        # except Exception as e:
        #     _error_and_stop(e)

    def reset_comp_ai_ui(self):
        sm.delete_session_state("current_score_sheet")
        sm.delete_session_state("widget_uploader")
        sm.delete_session_state("widget_camera")






        
