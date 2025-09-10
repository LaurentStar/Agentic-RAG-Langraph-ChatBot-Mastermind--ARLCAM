from typing import Any, Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder

# from graph.chains.generation import generation_chain
from app.graphs.states import AgentJBallGraphState 

from app.graphs.chains.text_extraction.literature_extractor import TextExtractionChains
from app.constants import Tone

def extract_tone_node(state: AgentJBallGraphState) -> Dict[str, Any]:
    """Use the existing context to determine rather this message needs a response"""
    message = state["message"]
    tone = TextExtractionChains.tone_extraction_chain.invoke({
        "message": message, 
        "enum_tone": [member.name for member in Tone]
    })

    # print(tone)

    return {"message_tone": tone}
