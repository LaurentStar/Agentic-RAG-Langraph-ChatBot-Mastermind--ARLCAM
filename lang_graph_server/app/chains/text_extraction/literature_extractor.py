#------------------------------------------------------------------------------------------------------#
# This file is for extracting values from text. This can be anything from numbers/setiment/tone/intent #
#------------------------------------------------------------------------------------------------------#

from typing import Any, Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder

# from graph.chains.generation import generation_chain
from app.models.graph_state_models.states import AgentJBallGraphState 
from app.extensions import markdown_prompts 
from app.models.structured_outputs_llm.text_extract_structured_output import Tone_SO, UnitBall_SO

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableSequence




#------------------------#
# Extract Tone from Text #
#------------------------#
class TextExtractionChains():
    
    @staticmethod
    def extract_tone():
        prompt = ChatPromptTemplate.from_messages([
                    ("system", markdown_prompts['tone_extractor_prompt.md'])
                ])
        llm =  ChatOpenAI(model="gpt-4o", temperature=0, verbose=True)
        structured_output_llm_tone = llm.with_structured_output(Tone_SO)
        tone_extraction_chain :  RunnableSequence  =  prompt |  structured_output_llm_tone 
        return tone_extraction_chain
    
    @staticmethod
    def extract_exaggeration_score():
        prompt = ChatPromptTemplate.from_messages([
                    ("system", markdown_prompts['exaggeration_score_extractor_prompt.md'])
                ])
        llm =  ChatOpenAI(model="gpt-4o", temperature=0, verbose=True)
        structured_output_llm_tone = llm.with_structured_output(UnitBall_SO)
        exaggeration_score_extraction_chain :  RunnableSequence  =  prompt |  structured_output_llm_tone 
        return exaggeration_score_extraction_chain
    
    @staticmethod
    def extract_vagueness_score():
        prompt = ChatPromptTemplate.from_messages([
                    ("system", markdown_prompts['vagueness_score_extractor_prompt.md'])
                ])
        llm =  ChatOpenAI(model="gpt-4o", temperature=0, verbose=True)
        structured_output_llm_tone = llm.with_structured_output(UnitBall_SO)
        vagueness_score_extraction_chain :  RunnableSequence  =  prompt |  structured_output_llm_tone 
        return vagueness_score_extraction_chain

    # ---------------------- class variables as chains ---------------------- #
    tone_extraction_chain = extract_tone()
    exaggeration_score_extraction_chain = extract_exaggeration_score()
    vagueness_score_extraction_chain = extract_vagueness_score()


