from typing import List, TypedDict
from app.constants import Tone, SocialMediaPlatform, UnitBall_SO

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
    # ---------------------- Message & Meta Data ---------------------- #
    message                             : str
    message_meta_social_media_platform  : SocialMediaPlatform
    message_meta_tone                   : Tone
    message_meta_exaggeration_score     : float
    message_meta_vagueness_score        : float
    message_meta_relevant_score         : float
    message_meta_truth_score            : float
    message_meta_lie_score              : float


    llm_generation                  : str
    working_memory                  : list
    context                         : str



    # ---------------------- Agent Attributes ---------------------- #
    agent_name                              : str
    agent_play_style                        : str 
    agent_personality                       : str 
    agent_tolerated_relevant_score_range    : tuple[float, float]



class AgentJBallGraphState(AgentGraphStateBase):
    """A graph model exclusive to agent jball built on top of the base graph state."""

    agent_name = "JBall Menrolle"
    agent_play_style = "quiet and likes to let events play out. Unlikely to respond. Response during critical moments otherwise watches"
    agent_personality = 'Cheerful yet polite. You lift people mood even when you need to lie or betray hhowever You are not arrogant'

    # ------------------------------------------------------------ #
    # How to weight the values of each attribute making a decision #
    # ------------------------------------------------------------ #
    agent_decision_weights = { 
        'relevvant_score': 0.30,
        'tone': 0.05,
    }

    # ------------------------------------------------------------------------------------- #
    # Hard play style ranges. These values are the red lines for the bot in decision making #
    # ------------------------------------------------------------------------------------- #
    agent_tolerated_relevant_score_range = (-0.5, 1)



