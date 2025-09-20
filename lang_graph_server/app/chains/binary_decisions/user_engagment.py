#*******************************************************************#
# Developed by Laurent Star 
# https://www.linkedin.com/in/christian-mundell-90733555
#*******************************************************************#

#-------------------------------------------#
# This file is for deciding user engagments #
#-------------------------------------------#

from typing import Any, Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder

# from graph.chains.generation import generation_chain
from app.models.graph_state_models.states import AgentJBallGraphState 
from app.extensions import markdown_prompts 


from app.models.structured_outputs_llm.text_extract_structured_output import Tone_SO, UnitBall_SO, IO_SO
from app.models.structured_outputs_llm.decision_so.decision_so import LLMDecideToReply_SO
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableSequence




#------------------------#
# Extract Tone from Text #
#------------------------#
class BinaryUserEngagmentChains():
    
    @staticmethod
    def decide_to_speak():
        """After listening to the chat and having context, decide to speak or stay silent"""
        prompt = ChatPromptTemplate.from_messages([
                    ("system", markdown_prompts['response_binary_decision_prompt.md'])
                ])
        llm =  ChatOpenAI(model="gpt-4o", temperature=0, verbose=True)
        structured_output_llm_tone = llm.with_structured_output(LLMDecideToReply_SO)
        decision_speak_chain :  RunnableSequence  =  prompt |  structured_output_llm_tone 
        return decision_speak_chain 
    

    # ---------------------- class variables as chains ---------------------- #
    decision_speak_chain = decide_to_speak()


