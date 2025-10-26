from app.models.graph_state_models.agent_graph_states import AgentJBallGraphState
from typing import Any, Dict


def initialize_jball_state_graph_node(state: AgentJBallGraphState) -> Dict[str, Any]:
    """initialize agent jball at the end of the workflow creation"""
    message = state.get("message")
    social_media_platform = state.get("social_media_platform")



    relevant_score_range = (-0.5, 1)
    agent_name = 'J-Ball'
    play_style = "quiet and likes to let events play out. Unlikely to respond. Response during critical moments otherwise watches"
    personality = 'Cheerful yet polite. You lift people mood even when you need to lie or betray hhowever You are not arrogant'
    initialized_values = {'relevant_score_range'    : relevant_score_range,
                          'play_style'              : play_style,
                          'personality'             : personality,
                          'agent_name'              : agent_name,
                          'chat_message'            : message,
                          'social_media_platform'   : social_media_platform}
    return initialized_values