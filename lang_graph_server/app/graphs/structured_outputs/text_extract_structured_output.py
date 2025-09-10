#*******************************************************************#
# Developed by Laurent Star 
# https://www.linkedin.com/in/christian-mundell-90733555
#*******************************************************************#
from pydantic import BaseModel, Field
from app.constants import Tone




class Tone_SO(BaseModel):

    tone : Tone = Field(
        description="The tone of the message"
    )
    