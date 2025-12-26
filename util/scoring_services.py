from pydantic import BaseModel, Field
from typing import Optional, List


# --- Define Strongly Typed Schema (Pydantic) ---
# This acts as the "Contract" for the AI. It MUST return data in this shape.
class FigureScore(BaseModel):
    figure_number: int = Field(description="The Figure/Fig/No number (1, 2, 3...) that normally is the 1st column in a table. Each figure is a row in the table")
    score: Optional[float] = Field(description="The handwritten Score/Grade given (0.0 to 10.0) next to each figure. If 'HZ' or 'Hard Zero', use 0.0")

class ScoreSheet(BaseModel):
    pilot_id: int = Field(description="ID/Number of the pilot normally at the top of the sheet")
    judge_id: int = Field(description="ID/Number of the judge normally next to the judge name and signature")
    flight_number: int = Field(description="The pilot's flight number/# normally at the top of the sheet")
    figures: List[FigureScore] = Field(description="List/table of all figures and respective scores")