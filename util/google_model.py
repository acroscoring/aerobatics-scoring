#import streamlit as st
from streamlit import cache_resource, secrets, context
import requests
import gspread
from typing import cast, Literal, Any, List, Tuple, Dict
from pydantic import BaseModel, EmailStr, HttpUrl
from google import genai
from PIL import Image
from util.streamlit_model import get_session_state_singleton, set_session_state
import util.data_model as dm
import util.security_model as sec
from gspread_dataframe import set_with_dataframe, get_as_dataframe # type: ignore
import pandas as pd
import util.constants as const


# --------------------------------------------------------------------------------------------------------------

class CompetitionPayload(BaseModel):
    comp_name: str
    admin_email: EmailStr
    bot_email: EmailStr
    app_url: HttpUrl

class EmailPayload(BaseModel):
    recipient: str
    copy_to: str
    subject: str
    htmlBody: str


class CompetitionRequest(BaseModel):
    api_name: Literal["CREATE_COMPETITION"]
    api_secret: str
    payload: CompetitionPayload

class EmailRequest(BaseModel):
    api_name: Literal["SEND_EMAIL"]
    api_secret: str
    payload: EmailPayload


class CompetitionResponse(BaseModel):
    status: Literal["Success", "Error"]
    message: str | None = None
    sheet_id: str | None = None

class EmailResponse(BaseModel):
    status: Literal["Success", "Error"]
    message: str | None = None


class DatabaseConnectionError(Exception):
    pass

class AiConnectionError(Exception):
    pass

class UserAlreadyExistsError(Exception):
    pass

class UserEmailNotFound(Exception):
    pass

class UserRoleAndIdNotFound(Exception):
    pass

class UserInvalidAuth(Exception):
    pass

class JudgeNotFound(Exception):
    pass

class MarkNotFound(Exception):
    pass

# --------------------------------------------------------------------------------------------------------------

@cache_resource(show_spinner="Getting Connection...", show_time=True)
def _get_gspread_client(creds_dict: dict[str, Any]) -> gspread.Client:
    try:
        return gspread.service_account_from_dict(creds_dict)
    except Exception as e:
        raise DatabaseConnectionError(f"Bot Authentication Failed: {e}")
        

@cache_resource(show_spinner="Getting DB...", show_time=True)
def _get_sheet_by_id(sheet_id: str) -> gspread.spreadsheet.Spreadsheet:
    try:
        creds_dict = dict(secrets["gcp_service_account"])
        gspread_client = _get_gspread_client(creds_dict)
        return gspread_client.open_by_key(sheet_id)
    except KeyError as e:
        raise DatabaseConnectionError(f"Missing Bot Secret Configuration: {e}")
    except Exception as e:
        raise DatabaseConnectionError(f"Failed to open competition sheet (DB): {e}")

@cache_resource(show_spinner="Getting AI Connection...", show_time=True)
def _get_genai_client(api_key: str):
    try:
        return genai.Client(api_key=api_key)
    except Exception as e:
        raise AiConnectionError(f"AI Authentication Failed: {e}")
    
def _get_google_app_script_url() -> str:
    return secrets["google_app_script"]["prod_url"] if secrets["env"]["type"] == "prod" else secrets["google_app_script"]["dev_url"]

# --------------------------------------------------------------------------------------------------------------

def get_scoring_sheet_data_using_ai(image: Image.Image) -> dm.ScoreSheet:
        try:
            api_key: str = secrets["google_gemini"]["api_key"]
            genai_client = _get_genai_client(api_key)
            prompt = "Extract the data from this aerobatics score sheet. Return 0 for missing values."
            response = genai_client.models.generate_content(
                model=secrets["google_gemini"]["model"],
                contents=[
                    image,  # Image 1st
                    prompt  # Prompt 2nd as per Google best practice https://ai.google.dev/gemini-api/docs/image-understanding#tips-best-practices
                ],
                config={
                    "response_mime_type": "application/json",
                    "response_schema": dm.ScoreSheet,
                },
            )
            return cast(dm.ScoreSheet, response.parsed)
        except KeyError as e:
            raise Exception(f"Missing AI Secret Configuration: {e}")
        except Exception as e:
            raise Exception(f"AI getting score error: {e}")
        
def call_email_api(payload: EmailPayload) -> Tuple[bool, str]:
            try:
                api_request = EmailRequest(
                    api_name="SEND_EMAIL",
                    api_secret=secrets["google_app_script"]["api_secret"],
                    payload=payload
                )
                
                api_url: str = _get_google_app_script_url()
                response = requests.post(api_url, json=api_request.model_dump(mode='json'))
                
                if response.status_code != 200:
                    return False, f"HTTP Error: {response.status_code} - {response.text}"
                
                result = EmailResponse(**response.json())
                
                if result.status == "Success":
                    return True, "Email sent successfully"
                else:
                    return False, f"Send email error: {result.message}"
                    
            except Exception as e:
                return False, f"Send email failed: {e}"

# --------------------------------------------------------------------------------------------------------------

class SheetDB:
    def __init__(self, sheet_id: str):
        try:
            self._sheet = _get_sheet_by_id(sheet_id)
            if not self._sheet:
                raise DatabaseConnectionError(f"Competition not found ({sheet_id})")

            self.title = self._sheet.title
            self.id = sheet_id

            self.users = self.UsersDB(self)
            self.judges = self.JudgesDB(self)
            self.marks = self.MarksDB(self)
        except Exception as e:
            raise DatabaseConnectionError(f"Error getting sheet (DB) details: {e}")
    
    @classmethod
    def connect(cls, sheet_id: str) -> "SheetDB":
        session_key = f"SheetDB_{sheet_id}"
        return get_session_state_singleton(session_key, lambda: cls(sheet_id))
        
    def refresh(self):
        self.users.refresh()
        self.judges.refresh()
        self.marks.refresh()
    
    @classmethod
    def create(cls, comp_name: str, admin_email: str) -> "SheetDB":
        try:
            if not context.url:
                raise Exception(f"Error getting context URL.")

            payload = CompetitionPayload(
                comp_name = comp_name,
                admin_email = admin_email,
                bot_email = secrets["gcp_service_account"]["client_email"],
                app_url = HttpUrl(context.url),
            )

            api_request = CompetitionRequest(
                api_name="CREATE_COMPETITION",
                api_secret = secrets["google_app_script"]["api_secret"],
                payload=payload
            )
            
            api_url: str = _get_google_app_script_url()
            response = requests.post(api_url, json=api_request.model_dump(mode='json'))
            
            if response.status_code != 200:
                raise DatabaseConnectionError(f"HTTP Error: {response.status_code} - {response.text}")
        
            result = CompetitionResponse(**response.json())
            
            if result.status != "Success":
                raise DatabaseConnectionError(f"Create Competition Apps Script Error: {result.message}")
            
            if not result.sheet_id:
                raise DatabaseConnectionError(f"Sheet (DB) ID Error")
            
            return SheetDB.connect(result.sheet_id)
        except KeyError as e:
            raise DatabaseConnectionError(f"Missing API URL Secret Configuration: {e}")
        except Exception as e:
            raise DatabaseConnectionError(f"Failed to create competition sheet (DB): {e}")
    
    class UsersDB:
        def __init__(self, parent_instance: SheetDB):
            try:
                self.parent = parent_instance
                self._users_ws = self.parent._sheet.worksheet(const.DBTabs.USERS)
                self._users_headers = self._users_ws.row_values(1)
                if not self._users_headers:
                    raise DatabaseConnectionError("Users tab headers row missing")

                self.all_users: List[dm.User] = get_session_state_singleton("db_users_data", lambda: self.get_all())
            except Exception as e:
                raise DatabaseConnectionError(f"Error getting Users in sheet (DB): {e}")
    
        def refresh(self):
            self.all_users: List[dm.User] = set_session_state("db_users_data", self.get_all())

        def get_all(self) -> List[dm.User]:
            try:
                records = self._users_ws.get_all_records()
                users = [dm.User.from_sheet_record(r) for r in records]
                return users
            except Exception as e:
                raise Exception(f"Error fetching users: {e}")
    
        def get_by_email(self, email: str) -> Tuple[int, dm.User]:
            email = dm.User.clean_email(email)
            for i, u in enumerate(self.all_users):
                if u.email == email:
                    return i, u
            raise UserEmailNotFound(f"User {email} not found in sheet (DB)")
    
        def get_by_role_and_id(self, role: dm.RoleType, id: int) -> Tuple[int, dm.User]:
            for i, u in enumerate(self.all_users):
                if u.role == role and u.id == id:
                    return i, u
            raise UserRoleAndIdNotFound(f"User with role {role} and ID {id} not found in sheet (DB)")

        def register(self, user: dm.User):
            try:
                self.get_by_email(user.email)
                raise UserAlreadyExistsError(f"Email {user.email} already exists.")
            except UserEmailNotFound:
                try:
                    row_data = user.to_sheet_row(self._users_headers)
                    self._users_ws.append_row(row_data)
                    self.refresh()
                except Exception as e:
                    raise Exception(f"Register user error: {e}")
            
        def delete(self, user: dm.User):
            try:
                index = -1
                try:
                    index, _ = self.get_by_email(user.email)
                except UserEmailNotFound:
                    return

                row_num = index + 2 # +2 for 1-based index + header
                self._users_ws.delete_rows(row_num)
                self.refresh()
            except Exception as e:
                raise Exception(f"Failed to delete user row: {e}")
        
        def update(self, user: dm.User):
            try:
                index = -1
                try:
                    index, _ = self.get_by_email(user.email)
                except UserEmailNotFound:
                    raise Exception(f"User {user.email} not found to update.")

                row_values = list(user.model_dump().values())
                row_num = index + 2 # +2 for 1-based index + header
                self._users_ws.update(range_name=f"A{row_num}", values=[row_values])
                self.refresh()
            except Exception as e:
                raise Exception(f"Failed to update user {user.email} ({user.id}): {e}")

        def authenticate(self, email: str, password: str) -> dm.User:
            try:
                _ , user = self.get_by_email(email)
                if user and sec.verify_password(password, user.password):
                    return user
                
                raise UserInvalidAuth("Invalid password")
            except UserEmailNotFound:
                raise UserInvalidAuth("Invalid email")
            except Exception as e:
                raise Exception(f"Auth user error: {e}")

    class JudgesDB:
        def __init__(self, parent_instance: SheetDB):
            try:
                self.parent = parent_instance
                self._judges_ws = self.parent._sheet.worksheet(const.DBTabs.JUDGES)
                self._judges_headers = self._judges_ws.row_values(1)
                if not self._judges_headers:
                    raise DatabaseConnectionError("Judges tab headers row missing")
                
                self.all_judges: List[dm.Judge] = get_session_state_singleton("db_judges_data", lambda: self.get_all())
            except Exception as e:
                raise DatabaseConnectionError(f"Error getting Judges in sheet (DB): {e}")
    
        def refresh(self):
            self.all_judges: List[dm.Judge] = set_session_state("db_judges_data", self.get_all())

        def get_all(self) -> List[dm.Judge]:
            try:
                records = self._judges_ws.get_all_records()
                judges = [dm.Judge.from_sheet_record(r) for r in records]
                return judges
            except Exception as e:
                raise Exception(f"Error fetching judges: {e}")

        def get_by_id(self, judge_id: int) -> Tuple[int, dm.Judge]:
            for i, j in enumerate(self.all_judges):
                if j.id == judge_id:
                    return i, j
            raise JudgeNotFound(f"Judge with ID {judge_id} not found in sheet (DB).")
            
        def update_name_by_id(self, new_judge: dm.AcroJudge) -> Tuple[bool, str]:
            try:
                index = -1
                old_judge = dm.Judge
                try:
                    index, old_judge = self.get_by_id(new_judge.id)
                except JudgeNotFound:
                    return False, f"Judge ID {new_judge.id} not found in DB."

                new_name = dm.Judge.full_name_from_acro_judge(new_judge)
                if old_judge.name == new_name:
                    return True, f"No name update required on {old_judge.name}."

                old_judge.name = new_name
                row_values = list(old_judge.model_dump().values())
                row_num = index + 2 # +2 for 1-based index + header
                self._judges_ws.update(range_name=f"A{row_num}", values=[row_values])
                self.refresh()
                return True, f"Updated Judge name {old_judge.name} ({old_judge.id})."
            except Exception as e:
                return False, f"Error updating judge name: {e}"
            
        def update_email_by_id(self, judge: dm.Judge) -> Tuple[bool, str]:
            try:
                index = -1
                old_judge = dm.Judge
                try:
                    index, old_judge = self.get_by_id(judge.id)
                except JudgeNotFound:
                    return False, f"Judge ID {judge.id} not found in DB."

                if old_judge.email == judge.email:
                    return True, f"No email update required on {old_judge.name} ({old_judge.id})."

                old_judge.email = judge.email
                row_values = list(old_judge.model_dump().values())
                row_num = index + 2 # +2 for 1-based index + header
                self._judges_ws.update(range_name=f"A{row_num}", values=[row_values])
                self.refresh()
                return True, f"Updated Judge name {old_judge.name} ({old_judge.id}) with email {old_judge.email}."
            except Exception as e:
                return False, f"Error updating judge email: {e}"
            
        def sync_judges(self, df_acro_judges: pd.DataFrame) -> Tuple[bool, str]:
            try:
                current_judges = self.all_judges
                current_ids = {j.id for j in current_judges}
                
                acro_ids = set(df_acro_judges['id'].astype(int).tolist())

                extra_ids = current_ids - acro_ids
                if extra_ids:
                    return False, f"Validation Error: The AeroScoring App Judges list has IDs {extra_ids} which are missing from the AcroScoring uploaded ctx file. Please update the legacy ACRO system to include these judges or remove them from the AeroScoring App Judges tab manually."

                process_status: List[str] = []
                common_ids = current_ids.intersection(acro_ids)
                if common_ids:                
                    common_df = df_acro_judges[df_acro_judges['id'].isin(common_ids)] # type: ignore
                    records = cast(List[Dict[str, Any]], common_df.to_dict('records')) # type: ignore
                    
                    for record in records:
                        acro_judge = dm.AcroJudge(**record)
                        ok, msg = self.update_name_by_id(acro_judge)
                        if not ok:
                            return False, f"Update judge name error: {msg}"
                    
                    process_status.append(f"Updated judge names.")
                
                missing_ids = acro_ids - current_ids
                if missing_ids:
                    new_judges_rows: List[List[Any]] = []
                    
                    missing_df = df_acro_judges[df_acro_judges['id'].isin(missing_ids)] # type: ignore
                    records = cast(List[Dict[str, Any]], missing_df.to_dict('records')) # type: ignore
                    
                    for record in records:
                        acro_judge = dm.AcroJudge(**record)
                        new_judge = dm.Judge.from_acro_judge(acro_judge)
                        new_judges_rows.append(new_judge.to_sheet_row(self._judges_headers))

                    if new_judges_rows:
                        self._judges_ws.append_rows(new_judges_rows)
                        process_status.append(f"Added {len(new_judges_rows)} new judges.")

                if len(process_status) > 0:
                    self.refresh()
                    return True, " ".join(process_status)
                else:
                    return True, "No judge updates needed."
            except Exception as e:
                return False, f"Judge sync error: {e}"
            
        def delete(self, judge: dm.Judge) -> Tuple[bool, str]:
            try:
                index = -1
                try:
                    index, _ = self.get_by_id(judge.id)
                except JudgeNotFound:
                    return False, f"Judge ID {judge.id} not found in DB."
                
                try:
                    _, user = self.parent.users.get_by_role_and_id("judge", judge.id)
                    self.parent.users.delete(user)
                except UserRoleAndIdNotFound:
                    pass
                
                row_num = index + 2 # +2 for 1-based index + header
                self._judges_ws.delete_rows(row_num)
                self.refresh()
                return True, f"Deleted Judge {judge.id}."
            except Exception as e:
                return False, f"Error deleting judge {judge.id}: {e}"
            
        def update_email(self, judge: dm.Judge, new_email: str) -> Tuple[bool, str]:
            try:
                old_email = judge.email
                new_email = dm.Judge.clean_email(new_email)
                
                if old_email == new_email:
                    return True, f"{judge.name} ({judge.id}) no change on email."
                
                judge.email = new_email

                for j in self.all_judges:
                    if j.id != judge.id and j.email and j.email == new_email:
                        return False, f"Email '{new_email}' is already assigned to Judge {j.name} ({j.id})."
                    
                try:
                    _ , existing_user = self.parent.users.get_by_email(new_email)
                    is_same_person = (existing_user.role == "judge" and existing_user.id == judge.id)
                    if not is_same_person:
                        return False, f"Email '{new_email}' is already registered to another User ({existing_user.username}). Delete the User first."
                except UserEmailNotFound:
                    pass

                ok, msg = self.update_email_by_id(judge)
                if not ok:
                    return False, f"Error updating judge email: {msg}."

                if old_email:
                    try:
                        _ , user = self.parent.users.get_by_email(old_email)
                        if user:
                            self.parent.users.delete(user)
                            self.refresh()
                            return True, f"Updated Judge {judge.name} ({judge.id}) email to {judge.email}. Deleted User account on old email {old_email}."
                    except UserEmailNotFound:
                        pass

                self.refresh()
                return True, f"Updated Judge {judge.name} ({judge.id}) email to {judge.email}."
            except Exception as e:
                return False, f"Error updating judge email: {e}"
            
        def send_judge_invite(self, judge: dm.Judge, admin_user: dm.AuthUser) -> Tuple[bool, str]:
            try:
                if not judge.email:
                    return False, f"Judge {judge.name} ({judge.id}) has no email."
                
                base_url = HttpUrl(str(context.url))
                base_url = f"{base_url.scheme}://{base_url.host}"
                reg_url = f"{base_url}/register?comp_id={self.parent.id}&judge_id={judge.id}"
                app_url = f"{base_url}/comp?comp_id={self.parent.id}"

                html_content = f"""
                <div style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #2E86C1;">✈️ Invitation to {self.parent.title}</h2>
                    <p>Hi <strong>{judge.name}</strong>,</p>
                    <p><strong>{admin_user.username}</strong> has invited you to join the <b>AeroScoring</b> app for this competition.</p>
                    <p>We are using AI to make scoring faster and easier. You simply take a photo of your score sheet, and the app does the rest!</p>
                    
                    <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                    
                    <h3>Step 1: Register</h3>
                    <p>Please register your account for this specific competition (Comp Name: {self.parent.title}) by clicking the button below:</p>
                    <br>
                    <p style="text-align: center;">
                        <a href="{reg_url}" style="background-color: #28B463; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                            📝 Register Now
                        </a>
                    </p>

                    <br>
                    
                    <h3>Step 2: Submit Scores</h3>
                    <p>Once registered, use the link below during the competition to scan your sheets:</p>
                    <br>
                    <p style="text-align: center;">
                        <a href="{app_url}" style="background-color: #2E86C1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                            🏆 Open Scoring App
                        </a>
                    </p>

                    <br>
                    
                    <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                    <p style="font-size: 12px; color: #888;">
                        <strong>Tip:</strong> Keep this email handy so you can quickly access the links during the competition day.<br>
                    </p>
                </div>
                """

                payload = EmailPayload(
                    recipient=judge.email,
                    copy_to=admin_user.email,
                    subject=f"Invitation: {self.parent.title} Scoring App",
                    htmlBody=html_content
                )

                return call_email_api(payload)

            except Exception as e:
                return False, f"Error preparing email for {judge.name}: {e}"
        
    class MarksDB:
        def __init__(self, parent_instance: SheetDB):
            try:
                self.parent = parent_instance
                self._marks_ws = self.parent._sheet.worksheet(const.DBTabs.MARKS)
                self._marks_headers = self._marks_ws.row_values(1)
                if not self._marks_headers:
                    raise DatabaseConnectionError("Marks tab headers row missing")

                self.all_marks: List[dm.AcroMark] = get_session_state_singleton("db_marks_data", lambda: self.get_all())
            except Exception as e:
                raise DatabaseConnectionError(f"Error getting Marks in sheet (DB): {e}")
        
        def refresh(self):
            self.all_marks: List[dm.AcroMark] = set_session_state("db_marks_data", self.get_all())

        def get_all(self) -> List[dm.AcroMark]:
            try:
                records = self._marks_ws.get_all_records()
                marks = [dm.AcroMark(**r) for r in records] # type: ignore
                return marks
            except Exception as e:
                raise Exception(f"Error fetching marks: {e}")
            
        def get_by_id(self, seq_id: int, pilot_id: int, judge_id: int) -> Tuple[int, dm.AcroMark]:
            for i, m in enumerate(self.all_marks):
                if m.sequence_id == seq_id and m.pilot_id == pilot_id and m.judge_id == judge_id:
                    return i, m
                    
            raise MarkNotFound(f"Mark with seq_id={seq_id}, pilot_id={pilot_id} and judge_id={judge_id} not found in sheet (DB)")
        
        def upsert(self, mark: dm.AcroMark) -> Tuple[bool, str]:
            try:
                row_values = list(mark.model_dump().values())
                index = -1
                try:
                    index, _ = self.get_by_id(mark.sequence_id, mark.pilot_id, mark.judge_id)
                except MarkNotFound:
                    self._marks_ws.append_row(row_values)
                    self.refresh()
                    return True, f"Added score for Sequence {mark.sequence_id}, Pilot {mark.pilot_id}, Judge {mark.judge_id}."

                row_num = index + 2 # +2 for 1-based index + header
                self._marks_ws.update(range_name=f"A{row_num}", values=[row_values])
                self.refresh()
                return True, f"Updated score for Sequence {mark.sequence_id}, Pilot {mark.pilot_id}, Judge {mark.judge_id}."
            except Exception as e:
                return False, f"Mark upsert Error: {str(e)}"
            

    def update_tab_from_df(self, tab_name: str, df: pd.DataFrame) -> Tuple[bool, str]:
        try:
            ws = self._sheet.worksheet(tab_name)
            ws.clear()
            set_with_dataframe(ws, df) # Write headers and data
            return True, f"Updated {tab_name} with {len(df)} rows."
        except Exception as e:
            return False, f"Error updating {tab_name}: {str(e)}"

    def get_table_df(self, tab_name: str) -> pd.DataFrame:
        try:
            ws = self._sheet.worksheet(tab_name)
            return get_as_dataframe(ws) # type: ignore
        except Exception as e:
            raise Exception(f"Error getting tab {tab_name}: {str(e)}")
        
