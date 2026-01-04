from pydantic import BaseModel, Field, EmailStr, field_validator, ValidationError
from typing import Optional, List, Dict, Any
import util.security_model as sec
from typing import Literal

class FigureScore(BaseModel):
    figure_number: int = Field(description="The Figure/Fig/No number (1, 2, 3...) that normally is the 1st column in a table. Each figure is a row in the table")
    score: Optional[float] = Field(description="The handwritten Score/Grade given (0.0 to 10.0) next to each figure. If 'HZ' or 'Hard Zero', use 0.0")

class ScoreSheet(BaseModel):
    pilot_id: int = Field(description="ID/Number of the pilot normally at the top of the sheet")
    judge_id: int = Field(description="ID/Number of the judge normally next to the judge name and signature")
    flight_number: int = Field(description="The pilot's flight number/# normally at the top of the sheet")
    figures: List[FigureScore] = Field(description="List/table of all figures and respective scores")


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
    fps_mode: Optional[int] = Field(alias="fps", default=None)
    
    # Scoring/K-Factor details could be added here as needed
    k_factors: str = Field(alias="knownkfacts", default="")