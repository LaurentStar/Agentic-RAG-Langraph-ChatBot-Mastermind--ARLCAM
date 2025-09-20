from typing import List, TypedDict
from app.constants import Tone, SocialMediaPlatform

class AgentJBallGraphState(TypedDict):
    """
    Represents the state of our graph represent the character J-Ball

    Attributes:
        message: message from chat
        message_tone: tone of message tone    
        exaggeration_score: How much a message is exagerrated 
        vagueness_score: The vagueness of the statement
        relevant_score: How important is this message
        message_social_media_platform: The platform which the message came from


        working_memory: relevant details saved for later use. This is filled programmatically by chance. The chance is influnced by the relevant_score but not ganruteed 
        
        context: Context regarding the message. Context is w
        
        truth_score: how likely this is to be truth -1 = lie, 0 = unsure 1 = truth
        lie_score: how likely this is to be lie -1 = lie, 0 = unsure 1 = truth
        relevant_score_range: If the determined the relevant of a message is between these values, you can respond otherwise stay silent. 
    """
    message: str
    message_tone: Tone
    exaggeration_score: float
    vagueness_score: float
    relevant_score: float
    message_social_media_platform: SocialMediaPlatform
    relevant_score_range: tuple[float, float]
    
    truth_score: float
    lie_score: float
    llm_generation: str
    working_memory: list
    context: str
    binary_decision_speak: bool 
    


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
