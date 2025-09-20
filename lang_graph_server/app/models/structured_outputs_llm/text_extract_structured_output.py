#*******************************************************************#
# Developed by Laurent Star 
# https://www.linkedin.com/in/christian-mundell-90733555
#*******************************************************************#
from pydantic import BaseModel, Field
from app.constants import Tone

class Tone_SO(BaseModel):
    tone : list[Tone] = Field(
        description="The tones of the message"
    )
    
class UnitBall_SO(BaseModel):
    unit_ball_score : float = Field(
        description="A score that goes from -1 to 1. It is the closest universal representation of this range I could find within 10 seconds of research.",
        ge=-1.0, le=1.0
    )

class IO_SO(BaseModel):
    io : bool = Field(
        description="A value of true or false. This represent a decision from the llm "
    )