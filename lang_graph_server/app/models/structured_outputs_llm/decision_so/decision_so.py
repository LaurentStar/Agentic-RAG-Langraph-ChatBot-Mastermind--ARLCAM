#*******************************************************************#
# Developed by Laurent Star 
# https://www.linkedin.com/in/christian-mundell-90733555
#*******************************************************************#
from pydantic import BaseModel, Field

class LLMDecideToReply_SO(BaseModel):
    llm_response : str = Field(description='LLM Response')
    llm_thoughts : str = Field(description='LLM thoughts')
    io : bool = Field(description="A value of true or false. This represent a decision from the llm to speak or stay silent")