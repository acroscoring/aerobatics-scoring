from pydantic import BaseModel, Field, EmailStr, field_validator, ValidationError
from typing import Optional, List, Dict, Any
import bcrypt
from typing import Literal


# --- Define Strongly Typed Schema (Pydantic) ---
# This acts as the "Contract" for the AI. It MUST return data in this shape.
class FigureScore(BaseModel):
    figure_number: int = Field(..., description="The Figure/Fig/No number (1, 2, 3...) that normally is the 1st column in a table. Each figure is a row in the table")
    score: Optional[float] = Field(..., description="The handwritten Score/Grade given (0.0 to 10.0) next to each figure. If 'HZ' or 'Hard Zero', use 0.0")

class ScoreSheet(BaseModel):
    pilot_id: int = Field(..., description="ID/Number of the pilot normally at the top of the sheet")
    judge_id: int = Field(..., description="ID/Number of the judge normally next to the judge name and signature")
    flight_number: int = Field(..., description="The pilot's flight number/# normally at the top of the sheet")
    figures: List[FigureScore] = Field(..., description="List/table of all figures and respective scores")

RoleType = Literal["admin", "judge"]

class User(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, description="Will be hashed automatically")
    role: RoleType = "judge"

    @field_validator('password')
    @classmethod
    def hash_password(cls, v: str) -> str:
        hashed = bcrypt.hashpw(v.encode('utf-8'), bcrypt.gensalt())
        return hashed.decode('utf-8')

    def to_sheet_row(self, headers: List[str]) -> List[str]:
        data = self.model_dump()
        return [str(data.get(h)) for h in headers]

    @classmethod
    def from_sheet_record(cls, record: Dict[str, Any]) -> "User":
        return cls(**record)
    
    def verify_password(self, plain_password: str) -> bool:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            self.password.encode('utf-8')
        )
    
def try_create_user(username: str, email: str, password: str, role: RoleType) -> User:
    try:
        user = User(
            username=username,
            email=email,
            password=password,
            role=role
        )
        return user

    except ValidationError as e:
        # Loop through errors and display them nicely in the UI
        for error in e.errors():
            # 'loc' is a tuple like ('email',), so we get the first item
            field_name = str(error['loc'][0])
            message = error['msg']
            
            # Display a specific error message for the specific field
            if field_name == "password":
                raise ValueError(f"Password Error: {message}")
            elif field_name == "email":
                raise ValueError(f"Email Error: {message}")
            else:
                raise ValueError(f"{field_name.title()}: {message}")
        
        raise Exception("Pydantic user ValidationError didn't work")
    except Exception as e:
        raise Exception(f"Error creating user: {e}")


class Judge(BaseModel):
    id: str = Field(..., min_length=2, max_length=2)
    name: str = Field(..., min_length=3, max_length=50)
    email: EmailStr

    def to_sheet_row(self, headers: List[str]) -> List[str]:
        data = self.model_dump()
        return [str(data.get(h)) for h in headers]

    @classmethod
    def from_sheet_record(cls, record: Dict[str, Any]) -> "Judge":
        return cls(**record)
