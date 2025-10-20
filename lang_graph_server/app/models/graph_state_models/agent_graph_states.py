from typing import List, TypedDict
from app.constants import Tone, SocialMediaPlatform

class AgentGraphStateBase(TypedDict):
    """
    Represents the baseline for an agent. 

    Attributes:
        message: message from chat
        message_tone: tone of message tone    
        exaggeration_score: How much a message is exagerrated 
        vagueness_score: The vagueness of the statement
        relevant_score: How important is this message
        message_social_media_platform: The platform which the message came from
        play_style: Agent jball play style during the games
        personality: agent jball personality for responding
        agent_name: name of the agent. When people say jball, they are refering to your. speak in first person.

        working_memory: relevant details saved for later use. This is filled programmatically by chance. The chance is influnced by the relevant_score but not ganruteed 
        
        context: Context regarding the message. Context is w
        
        truth_score: how likely this is to be truth -1 = lie, 0 = unsure 1 = truth
        lie_score: how likely this is to be lie -1 = lie, 0 = unsure 1 = truth
        relevant_score_range: If the determined the relevant of a message is between these values, you can respond otherwise stay silent. 
    """
    message                         : str
    message_tone                    : Tone
    exaggeration_score              : float
    vagueness_score                 : float
    relevant_score                  : float
    message_social_media_platform   : SocialMediaPlatform
    relevant_score_range            : tuple[float, float]
    play_style                      : str 
    personality                     : str
    agent_name                      : str
    
    truth_score                     : float
    lie_score                       : float
    llm_generation                  : str
    working_memory                  : list
    context                         : str


class AgentJBallGraphState(AgentGraphStateBase):
    """A graph model exclusive to agent jball built on top of the base graph state."""

    name = "JBall Menrolle"


