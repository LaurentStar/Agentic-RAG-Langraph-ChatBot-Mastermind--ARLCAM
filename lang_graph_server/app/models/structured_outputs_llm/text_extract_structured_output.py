#*******************************************************************#
# Developed by Laurent Star 
# https://www.linkedin.com/in/christian-mundell-90733555
#*******************************************************************#
from pydantic import BaseModel, Field
from app.constants import Tone, UnitBall_SO

class TextMetaDetailsExtractor_SO(BaseModel):
    message_meta_tone                   : list[Tone]    = Field(description="The tones of the message")

    message_meta_exaggeration_score     : float = Field(description="How much did the user exaggerate given the context.", ge=-1.0, le=1.0) #UnitBall_SO   = Field(description="How much did the user exaggerate given the context.")
    message_meta_vagueness_score        : float = Field(description="How vague was the user statement", ge=-1.0, le=1.0)                    #UnitBall_SO   = Field(description="How vague was the user statement")
    message_meta_relevant_score         : float = Field(description="Given the mconversation history, represent how relevant the statement are.", ge=-1.0, le=1.0) #UnitBall_SO   = Field(description="Given the mconversation history, represent how relevant the statement are.")