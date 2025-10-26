#*******************************************************************#
# Developed by Laurent Star 
# https://www.linkedin.com/in/christian-mundell-90733555
#*******************************************************************#
from pydantic import BaseModel, Field
from app.constants import Tone, UnitBall_SO

class TextMetaDetailsExtractor_SO(BaseModel):
    message_tone            : list[Tone]    = Field(description="The tones of the message")
    exaggeration_score      : UnitBall_SO   = Field(description="How much did the user exaggerate given the context.")
    vagueness_score         : UnitBall_SO   = Field(description="How vague was the user statement")
    relevant_score          : UnitBall_SO   = Field(description="Given the mconversation history, represent how relevant the statement are.")
   

class IO_SO(BaseModel):
    io : bool = Field(description="A value of true or false. This represent a decision from the llm ")