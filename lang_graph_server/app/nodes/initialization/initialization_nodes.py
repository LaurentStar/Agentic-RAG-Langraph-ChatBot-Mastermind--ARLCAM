from app.models.graph_state_models.agent_graph_states import AgentJBallGraphState
from app.constants import SocialMediaPlatform
from typing import Any, Dict


def initialize_jball_state_graph_node(state: AgentJBallGraphState) -> Dict[str, Any]:
    """initialize agent jball at the end of the workflow creation"""
    message = state.get("message")
    message_meta_social_media_platform = SocialMediaPlatform[state.get("message_meta_social_media_platform", "DEFUALT")]


    
    agent_name = AgentJBallGraphState.agent_name
    agent_play_style = AgentJBallGraphState.agent_play_style
    agent_personality = AgentJBallGraphState.agent_personality
    agent_tolerated_relevant_score_range = AgentJBallGraphState.agent_tolerated_relevant_score_range

    initialized_values = {
        'message'                               : message,
        'message_meta_social_media_platform'    : message_meta_social_media_platform,
        'agent_name'                            : agent_name,
        'agent_play_style'                      : agent_play_style,
        'agent_personality'                     : agent_personality,
        'agent_tolerated_relevant_score_range'  : agent_tolerated_relevant_score_range,
    }
    return initialized_values