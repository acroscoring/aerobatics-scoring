from pydantic import BaseModel, Field, EmailStr, field_validator, ValidationError, ConfigDict
from typing import List, Dict, Any
import util.security_model as sec
from typing import Literal
import pandas as pd

class FigureScore(BaseModel):
    figure_number: int = Field(description="The Figure/Fig/No number (1, 2, 3...) that normally is the 1st column in a table. Each figure is a row in the table")
    score: float | Literal["AV", "HZ", "PZ"] = Field(description="The handwritten Score/Grade given next to each figure: 0.0 to 10.0 in 0.5 increments (e.g. 1.5 or 7.5) or AV (average) or HZ (hard zero) or PZ (perceived zero)")
    
class OverallScore(BaseModel):
    item: str = Field(description="The item name; normally the 1st item is positioning/pos")
    score: float | Literal["AV"] | None = Field(description="The handwritten Score/Grade given next to each item: 0.0 to 10.0 in 0.5 increments (e.g. 1.5 or 7.5) or AV (average) or blank (not used)")

class Penalty(BaseModel):
    item: str = Field(description="The item name; normally items like too low, too high, interruptions, insertions, trg violation, wing rocks, disqual, etc.")
    count: int = Field(description="The handwritten number of times it happened or blank/zero")
    
class ScoreSheet(BaseModel):
    flight_number: int = Field(description="The flight number/# normally at the top of the sheet")
    pilot_id: int = Field(description="ID/Number of the pilot normally at the top of the sheet")
    judge_id: int = Field(description="ID/Number of the judge normally next to the judge name and signature")
    figures: List[FigureScore] = Field(description="The main table with all the figures and respective scores/grades/marks")
    overall_items: List[OverallScore] = Field(description="Small table with 1 to 3 items and respective scores/grades/marks")
    penalties: List[Penalty] = Field(description="Small table with 6 to 8 items and respective count")
    

RoleType = Literal["admin", "judge"]

class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    role: RoleType
    id: int | Literal[""]

    @field_validator('email')
    @classmethod
    def clean_email(cls, email: str) -> str:
        return email.lower().strip()
    
    def to_sheet_row(self, headers: List[str]) -> List[str]:
        data = self.model_dump()
        return [str(data.get(h)) for h in headers]

class User(UserBase):
    password: str = Field(min_length=6, description="Will be hashed automatically")

    @field_validator('password')
    @classmethod
    def hash_password(cls, password: str) -> str:
        if len(password) == 60 and password.startswith(("$2b$", "$2a$", "$2y$")):
            return password
        return sec.hash_password(password)
    
    @classmethod
    def from_sheet_record(cls, record: Dict[str, Any]) -> "User":
        return cls(**record)
    
    @classmethod
    def create(cls, username: str, email: str, password: str, role: RoleType, id: int | Literal[""] = "") -> "User":
        try:
            user = User(
                username=username,
                email=email,
                password=password,
                role=role,
                id=id
            )
            return user
        except ValidationError as e:
            errors = e.errors(include_url=False)
            messages: list[str] = []
            for err in errors:
                field_name = " -> ".join(str(loc) for loc in err['loc']).title()
                msg = err['msg']
                messages.append(f"{field_name} error: {msg}")
            raise ValueError("; ".join(messages))
        except Exception as e:
            raise Exception(f"Create user error: {e}")

class AuthUser(UserBase):
    comp_id: str

    @classmethod
    def from_user(cls, user: User, comp_id: str) -> "AuthUser":
        user_data = user.model_dump(exclude={'password'})
        return cls(**user_data, comp_id=comp_id)


class Judge(BaseModel):
    id: int
    name: str = Field(min_length=3, max_length=50)
    email: EmailStr | Literal[""]

    def to_sheet_row(self, headers: List[str]) -> List[Any]:
        data = self.model_dump()
        return [data.get(h) for h in headers]

    @classmethod
    def from_sheet_record(cls, record: Dict[str, Any]) -> "Judge":
        return cls(**record)
    
    @classmethod
    def full_name_from_acro_judge(cls, acro_judge: AcroJudge) -> str:
        return f"{acro_judge.first_name} {acro_judge.surname}"

    @classmethod
    def from_acro_judge(cls, acro_judge: AcroJudge) -> "Judge":    
        new_judge = Judge(
            id=acro_judge.id,
            name=Judge.full_name_from_acro_judge(acro_judge),
            email=""
        )
        return new_judge

    @field_validator('id')
    @classmethod
    def valid_id(cls, id: int) -> int:
        if (id < 1) or (id > 99):
            raise ValueError("Invalid judge ID (should be between 01 and 99).")
        return id
    
    @field_validator('email')
    @classmethod
    def clean_email(cls, email: str) -> str:
        return User.clean_email(email)



# --------------------------------------------------------------------------------------------------------------
# ACRO
# --------------------------------------------------------------------------------------------------------------

class AcroJudge(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: int
    first_name: str = Field(alias="name1", default="")
    surname: str = Field(alias="name2", default="")

class AcroPilot(BaseModel):
    id: int
    first_name: str = Field(alias="name1", default="")
    surname: str = Field(alias="name2", default="")
    category: str = Field(alias="lev1", default="")
    active: str = Field(default="A") # 'A' or 'N'
    registration: str = Field(alias="acreg", default="")
    aircraft: str = Field(alias="actype", default="")

class AcroSequence(BaseModel):
    id: int
    title: str = Field(default="")
    rpt_header: str = Field(alias="rpthdr", default="")
    active: str = Field(default="A")
    level: str = Field(default="")
    type_code: str = Field(alias="type", default="")
    is_locked: str = Field(alias="lock", default="N")
    
    # Complex fields parsed into strings/JSON for the sheet
    fly_order: str = Field(alias="flyorder", default="") # e.g., "001, 002, 003"
    judges_config: str = Field(alias="judges", default="") # e.g., "05(AC), 06(AJ)"
    fps_mode: int | None = Field(alias="fps", default=None)
    
    # Scoring/K-Factor details could be added here as needed
    k_factors: str = Field(alias="knownkfacts", default="")
    
    oak1_active: str = Field(alias="oak1active", default="A")
    oak1_title: str = Field(alias="oak1title", default="Positioning")
    oak2_active: str = Field(alias="oak2active", default="N")
    oak2_title: str = Field(alias="oak2title", default="")
    oak3_active: str = Field(alias="oak3active", default="N")
    oak3_title: str = Field(alias="oak3title", default="")

    pen01_active: str = Field(alias="pen01active", default="N")
    pen01_title: str = Field(alias="pen01title", default="")
    pen02_active: str = Field(alias="pen02active", default="N")
    pen02_title: str = Field(alias="pen02title", default="")
    pen03_active: str = Field(alias="pen03active", default="N")
    pen03_title: str = Field(alias="pen03title", default="")
    pen04_active: str = Field(alias="pen04active", default="N")
    pen04_title: str = Field(alias="pen04title", default="")
    pen05_active: str = Field(alias="pen05active", default="N")
    pen05_title: str = Field(alias="pen05title", default="")
    pen06_active: str = Field(alias="pen06active", default="N")
    pen06_title: str = Field(alias="pen06title", default="")
    pen07_active: str = Field(alias="pen07active", default="N")
    pen07_title: str = Field(alias="pen07title", default="")
    pen08_active: str = Field(alias="pen08active", default="N")
    pen08_title: str = Field(alias="pen08title", default="")
    pen09_active: str = Field(alias="pen09active", default="N")
    pen09_title: str = Field(alias="pen09title", default="")
    pen10_active: str = Field(alias="pen10active", default="N")
    pen10_title: str = Field(alias="pen10title", default="")

class AcroMark(BaseModel):
    sequence_id: int
    pilot_id: int
    judge_id: int
    
    fig01: str = Field(default="")
    fig02: str = Field(default="")
    fig03: str = Field(default="")
    fig04: str = Field(default="")
    fig05: str = Field(default="")
    fig06: str = Field(default="")
    fig07: str = Field(default="")
    fig08: str = Field(default="")
    fig09: str = Field(default="")
    fig10: str = Field(default="")
    fig11: str = Field(default="")
    fig12: str = Field(default="")
    fig13: str = Field(default="")
    fig14: str = Field(default="")
    fig15: str = Field(default="")
    fig16: str = Field(default="")
    fig17: str = Field(default="")
    fig18: str = Field(default="")
    fig19: str = Field(default="")
    fig20: str = Field(default="")

    oak1: str = Field(default="")
    oak2: str = Field(default="")
    oak3: str = Field(default="")

    pen01: str = Field(default="")
    pen02: str = Field(default="")
    pen03: str = Field(default="")
    pen04: str = Field(default="")
    pen05: str = Field(default="")
    pen06: str = Field(default="")
    pen07: str = Field(default="")
    pen08: str = Field(default="")
    pen09: str = Field(default="")
    pen10: str = Field(default="")

    submitted_by: str | None = None
    timestamp: str | None = None

    @classmethod
    def from_ai_score_sheet(cls, sheet: "ScoreSheet", figures_df: pd.DataFrame, overall_df: pd.DataFrame, penalty_df: pd.DataFrame, user_email: str, timestamp: str) -> "AcroMark":

        # --- Helper: Safe String Conversion ---
        def safe_str_score(val: Any) -> str:
            if pd.isna(val) or val is None or str(val).strip() == "":
                return ""
            s = str(val).strip()
            if s.endswith(".0"): 
                s = s[:-2] # Convert "8.0" to "8"
            if s == "10": 
                return "Tn"
            return s

        def safe_str_count(val: Any) -> str:
            if pd.isna(val) or val is None:
                return ""
            try:
                # Handle cases like 1.0 coming from float column
                i_val = int(float(val))
                return str(i_val) if i_val > 0 else ""
            except ValueError:
                return ""

        # 1. Map Figures
        figs: Dict[str, str] = {}
        if not figures_df.empty:
            # Sort to ensure fig01 maps to figure_number 1
            figures_df = figures_df.sort_values("figure_number")
            records = figures_df.to_dict('records') # type: ignore
            for i in range(20):
                if i < len(records):
                    figs[f"fig{i+1:02d}"] = safe_str_score(records[i].get('score'))
                else:
                    figs[f"fig{i+1:02d}"] = "" # Default empty string

        # 2. Map OAKs
        oaks: Dict[str, str] = {}
        if not overall_df.empty:
            records = overall_df.to_dict('records') # type: ignore
            for i in range(3):
                if i < len(records):
                    oaks[f"oak{i+1}"] = safe_str_score(records[i].get('score'))
                else:
                    oaks[f"oak{i+1}"] = ""

        # 3. Map Penalties
        pens: Dict[str, str] = {}
        if not penalty_df.empty:
            records = penalty_df.to_dict('records') # type: ignore
            for i in range(10):
                if i < len(records):
                    pens[f"pen{i+1:02d}"] = safe_str_count(records[i].get('count'))
                else:
                    pens[f"pen{i+1:02d}"] = ""

        return cls(
            sequence_id=int(sheet.flight_number),
            pilot_id=int(sheet.pilot_id),
            judge_id=int(sheet.judge_id),
            submitted_by=str(user_email),
            timestamp=str(timestamp),
            **figs,
            **oaks,
            **pens
        )
    
class JudgeTableRow(BaseModel):
    class Cols:
        SELECTED = "selected"
        ID = "id"
        NAME = "name"
        EMAIL = "email"
        REGISTERED = "registered"
        IS_ADMIN = "is_admin"

    selected: bool = Field(default=False, alias=Cols.SELECTED)
    id: int = Field(alias=Cols.ID)
    name: str = Field(alias=Cols.NAME)
    email: str | None = Field(alias=Cols.EMAIL) 
    registered: bool = Field(alias=Cols.REGISTERED)
    is_admin: bool = Field(alias=Cols.IS_ADMIN)
    
    model_config = ConfigDict(populate_by_name=True)

    def to_row(self) -> Dict[str, Any]:
        return self.model_dump(by_alias=True)