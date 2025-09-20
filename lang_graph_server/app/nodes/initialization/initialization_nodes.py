from app.models.graph_state_models.states import AgentJBallGraphState 
from typing import Any, Dict


def initialize_jball_state_graph_node(state: AgentJBallGraphState) -> Dict[str, Any]:
    """initialize agent jball at the end of the workflow creation"""
    relevant_score_range = (-0.5, 1)
    initialized_values = {'relevant_score_range': relevant_score_range}
    return initialized_values
