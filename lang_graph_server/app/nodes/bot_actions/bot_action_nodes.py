from typing import Any, Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder

# from graph.chains.generation import generation_chain
from app.models.graph_state_models.states import AgentJBallGraphState 

from app.chains.text_extraction.literature_extractor import TextExtractionChains
from app.constants import Tone

def extract_message_meta_details_node(state: AgentJBallGraphState) -> Dict[str, Any]:
    """Extract meta details from the user message"""
    message = state["message"]
    message_tone = TextExtractionChains.tone_extraction_chain.invoke({
        "message": message, 
        "enum_tone": [member.name for member in Tone]
    })
    # context =  TextExtractionChains.exaggeration_score_extraction_chain.invoke({"message": message })
    exaggeration_score = TextExtractionChains.exaggeration_score_extraction_chain.invoke({"message": message})
    vagueness_score = TextExtractionChains.vagueness_score_extraction_chain.invoke({"message": message})

    graph_state_update = {'message_tone'         : message_tone,
                          'exaggeration_score'   : exaggeration_score,
                          'vagueness_score'      : vagueness_score 
    }

    return graph_state_update 
