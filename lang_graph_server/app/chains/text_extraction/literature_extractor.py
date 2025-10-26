#********************************************************************
#* Developed by Laurent Star                                        *
#* Linkedin: https://www.linkedin.com/in/christian-mundell-90733555 *
#* Github: https://github.com/LaurentStar
#* 
#********************************************************************

from typing import Any, Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder

from app.models.graph_state_models.agent_graph_states import AgentJBallGraphState 
from app.extensions import LoadedPromptTemplates
from app.models.structured_outputs_llm.text_extract_structured_output import TextMetaDetailsExtractor_SO

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableSequence



class TextExtractionChains():
    
    # @staticmethod
    # def extract_tone():
    #     """Determines the tone of a user message. Selects a list of tones provided"""
    #     prompt = ChatPromptTemplate.from_messages([
    #                 ("system", LoadedPromptTemplates.markdown_prompt_templates['tone_extractor_prompt.md'])
    #             ])
    #     llm =  ChatOpenAI(model="gpt-4o", temperature=0, verbose=True)
    #     structured_output_llm_tone = llm.with_structured_output(Tone_SO)
    #     tone_extraction_chain :  RunnableSequence  =  prompt |  structured_output_llm_tone 
    #     return tone_extraction_chain
    
    # @staticmethod
    # def extract_exaggeration_score():
    #     """Grades a message based on how much the user exaggerated"""
    #     prompt = ChatPromptTemplate.from_messages([
    #                 ("system", LoadedPromptTemplates.markdown_prompt_templates['exaggeration_score_extractor_prompt.md'])
    #             ])
    #     llm =  ChatOpenAI(model="gpt-4o", temperature=0, verbose=True)
    #     structured_output_llm_tone = llm.with_structured_output(UnitBall_SO)
    #     exaggeration_score_extraction_chain :  RunnableSequence  =  prompt |  structured_output_llm_tone 
    #     return exaggeration_score_extraction_chain
    
    # @staticmethod
    # def extract_vagueness_score():
    #     """Determines how vague the user message is"""
    #     prompt = ChatPromptTemplate.from_messages([
    #                 ("system", LoadedPromptTemplates.markdown_prompt_templates['vagueness_score_extractor_prompt.md'])
    #             ])
    #     llm =  ChatOpenAI(model="gpt-4o", temperature=0, verbose=True)
    #     structured_output_llm_tone = llm.with_structured_output(UnitBall_SO)
    #     vagueness_score_extraction_chain :  RunnableSequence  =  prompt |  structured_output_llm_tone 
    #     return vagueness_score_extraction_chain

    # @staticmethod
    # def extract_relevant_score():
    #     """Uses meta data collected earlier to determine how relevant the current message is to the agent"""
    #     prompt = ChatPromptTemplate.from_messages([
    #                 ("system", LoadedPromptTemplates.markdown_prompt_templates['relevant_score_extractor_prompt.md'])
    #             ])
    #     llm =  ChatOpenAI(model="gpt-4o", temperature=0, verbose=True)
    #     structured_output_llm_tone = llm.with_structured_output(UnitBall_SO)
    #     relevant_score_extraction_chain :  RunnableSequence  =  prompt |  structured_output_llm_tone 
    #     return relevant_score_extraction_chain
    

    @staticmethod
    def extract_text_meta_data_chain():
        """Extract meta data from text to determine next move"""
        prompt = ChatPromptTemplate.from_messages([
                    ("system", LoadedPromptTemplates.markdown_prompt_templates['text_literture_metadata_extraction.md'])
                ])
        llm =  ChatOpenAI(model="gpt-4o", temperature=0, verbose=True)
        structured_output_llm_tone = llm.with_structured_output(TextMetaDetailsExtractor_SO)
        extract_text_meta_data_chain :  RunnableSequence  =  prompt |  structured_output_llm_tone 
        return extract_text_meta_data_chain
    
    # ---------------------- class variables as chains ---------------------- #
    # tone_extraction_chain = extract_tone()
    # exaggeration_score_extraction_chain = extract_exaggeration_score()
    # vagueness_score_extraction_chain = extract_vagueness_score()
    # relevant_score_extraction_chain = extract_relevant_score()
    extract_text_meta_data_chain = extract_text_meta_data_chain()


