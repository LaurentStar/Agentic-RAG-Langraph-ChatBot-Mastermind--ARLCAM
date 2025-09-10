from typing import List, TypedDict
from app.constants import Tone

class AgentJBallGraphState(TypedDict):
    """
    Represents the state of our graph represent the character J-Ball

    Attributes:
        message: message from chat
        message_tone: tone of message tone
        working_memory: relevant details saved for later use. This is filled programmatically by chance. The chance is influnced by the relevant_score but not ganruteed 
        context: Context regarding the message. Context is w
        relevant_score: How important is this message
        truth_score: how likely this is to be truth -1 = lie, 0 = unsure 1 = truth
        lie_score: how likely this is to be lie -1 = lie, 0 = unsure 1 = truth
    """
    message: str
    message_tone: Tone
    working_memory: list
    context: str
    relevant_score: float
    truth_score: float
    lie_score: float
    llm_generation: str
    


# class GraphState(TypedDict):
#     """
#     Represents the state of our graph.

#     Attributes:
#         question: question
#         generation: LLM generation
#         web_search: whether to add search
#         documents: list of documents
#     """

#     question: str
#     generation: str
#     web_search: bool
#     documents: List[str]
