from pydantic import BaseModel, Field, EmailStr, field_validator, ValidationError
from typing import List, Dict, Any
import util.security_model as sec
from typing import Literal

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
    email: EmailStr

    def to_sheet_row(self, headers: List[str]) -> List[str]:
        data = self.model_dump()
        return [str(data.get(h)) for h in headers]

    @classmethod
    def from_sheet_record(cls, record: Dict[str, Any]) -> "Judge":
        return cls(**record)
    
    @field_validator('id')
    @classmethod
    def valid_id(cls, id: int) -> int:
        if (id < 1) or (id > 99):
            raise ValueError("Invalid judge ID (should be between 01 and 99).")
        return id



# --------------------------------------------------------------------------------------------------------------
# ACRO
# --------------------------------------------------------------------------------------------------------------

class AcroJudge(BaseModel):
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