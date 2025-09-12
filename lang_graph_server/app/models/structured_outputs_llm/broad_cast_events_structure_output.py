#*******************************************************************#
# Developed by Laurent Star 
# https://www.linkedin.com/in/christian-mundell-90733555
#*******************************************************************#
from pydantic import BaseModel, Field
from constants import Tone


class BroadCast_SO(BaseModel):
    broadcast_message: str = Field(
        description="Typical format for a major broadcast."
    )


class BroadCastMarketManipulation_SO(BaseModel):
    broadcast_message: str = Field(
        description="The player has put down a lot of coins for 'market Manipulation'  This action can potentially trigger multiple player into a death"
    )

class Tone_OS(BaseModel):

    binary_score: Tone = Field(
        description="The tone of the message'"
    ) 