import streamlit as st
from pydantic import BaseModel, Field, EmailStr, field_validator, ValidationError
from typing import Optional, List
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
        """
        Automatically hashes the password when the model is created.
        If the password is already hashed (starts with $2b$), leave it alone.
        """
        if v.startswith("$2b$"): 
            return v
        
        # Hash the plain text password
        # bcrypt requires bytes, so we encode, hash, then decode back to str
        hashed = bcrypt.hashpw(v.encode('utf-8'), bcrypt.gensalt())
        return hashed.decode('utf-8')

    def to_sheet_row(self) -> List[str]:
        """Helper to convert the object to a list for Google Sheets"""
        return [self.username, self.email, self.password, self.role]
    
    def verify_password(self, plain_password: str) -> bool:
        """Helper to check if a plain password matches this user's hash"""
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            self.password.encode('utf-8')
        )
    
def try_create_user(username: str, email: str, password: str, role: RoleType) -> User | None:
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
                st.error(f"Password Error: {message}", icon="🔐")
            elif field_name == "email":
                st.error(f"Email Error: {message}", icon="📧")
            else:
                st.error(f"{field_name.title()}: {message}", icon="❌")
                
        return None
        
    except Exception as e:
        st.error(f"Error creating user: {e}", icon="❌")
        return None