import requests
import json 
from typing import Any, Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder



from app.models.graph_state_models.agent_graph_states import AgentJBallGraphState

# ---------------------- chains ---------------------- #
from app.chains.text_extraction.literature_extractor import TextExtractionChains



from app.constants import Tone



#-------#
# NODES #
#-------#
def extract_message_meta_details_node(state: AgentJBallGraphState) -> Dict[str, Any]:
    """Extract meta details from the user message"""
    chat_message = state["message"]
    prompt_input = {"message": chat_message,
                    "detectable_tones": [member.name for member in Tone]}
    llm_response = TextExtractionChains.extract_text_meta_data_chain.invoke(prompt_input) 
    graph_state_update = {'message_meta_tone'                   : llm_response.message_meta_tone,
                          'message_meta_exaggeration_score'     : llm_response.message_meta_exaggeration_score,
                          'message_meta_vagueness_score'        : llm_response.message_meta_vagueness_score,
                          'message_meta_relevant_score'         : llm_response.message_meta_relevant_score}
    return graph_state_update 

def decide_how_to_response_node(state: AgentJBallGraphState) -> Dict[str, Any]:
    """Response to the user based on the meta data and context collected earlier"""
    message = state["message"]
    context = {
        'message_meta_data' : {
            'exaggeration_score' : f"{state['exaggeration_score'].unit_ball_score}  ——— -1 (understate), 1 (exaggerate), 0 (neither understate nor exaggerate)",
            'message_tone'       : f"{[tone.name for tone in state['message_tone'].tone]}  ——— tones of message",
            'vagueness_score'    : f"{state['vagueness_score'].unit_ball_score} ——— -1 (vague), 1 (clear), 0 (neither vague nor clear)"},
        'your_meta_data': {
            'your_name'         : 'J-Ball',
            'your_cards'        : ['DUKE', 'ASSASSIN'],
            'your_playstyle'    : 'quiet and likes to let events play out. Unlikely to respond. Response during critical moments otherwise watches',
            'your_personality'  : 'quiet, unlikely to engage in irrelevant discussion'
        }
    }

    return graph_state_update


#-------------------#
# ROUTING FUNCTIONS #
#-------------------#
def decide_to_respond_router(state:AgentJBallGraphState) -> bool:
    """Determine rather the agent will respond or not to the incoming message"""
    # ---------------------- Red Lines ---------------------- #
    cross_red_line = True
    will_response = False
    agent_tolerated_relevant_score_range = state.get("agent_tolerated_relevant_score_range")
    message_meta_relevant_score = state.get("message_meta_relevant_score")

    
    cross_red_line = agent_tolerated_relevant_score_range[0] < message_meta_relevant_score < agent_tolerated_relevant_score_range[1]
    
    # ---------------------- LLMs Final Decision ---------------------- #
    if cross_red_line == False:
        will_response = True


    return will_response
