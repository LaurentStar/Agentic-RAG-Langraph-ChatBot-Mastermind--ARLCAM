"""
Chat Reasoning State Model.

State for the chat reasoning workflow that processes incoming messages
and generates responses for Coup LLM agents.

The workflow:
1. Analyzes the incoming message intent
2. Decides whether to respond
3. Checks message limits
4. Generates a response (if appropriate)
5. Optionally decides to update pending action
"""

from datetime import datetime
from typing import Dict, List, Optional, TypedDict

from app.constants import (
    CoupAction,
    InfluenceCard,
    MessageTargetType,
    SocialMediaPlatform,
    UpgradeType,
)
from app.models.graph_state_models.hourly_coup_state import (
    ChatMessage,
    VisiblePendingAction,
)


class MessageAnalysis(TypedDict, total=False):
    """Analysis of an incoming message."""
    
    # Intent classification
    intent: str  # "question", "accusation", "persuasion", "threat", "smalltalk", "game_talk"
    
    # Scores (0.0 to 1.0)
    relevance_score: float      # How relevant is this to the agent
    urgency_score: float        # How urgently should agent respond
    threat_level: float         # Is this a threat to the agent
    opportunity_score: float    # Is this an opportunity to persuade/manipulate
    
    # Extracted info
    mentions_agent: bool        # Does message mention this agent
    mentions_action: Optional[CoupAction]  # Does it reference a game action
    mentioned_players: List[str]  # Other players mentioned
    
    # Tone
    sender_tone: str  # "friendly", "hostile", "neutral", "suspicious", "deceptive"


class ResponseDecision(TypedDict, total=False):
    """Decision about whether and how to respond."""
    
    should_respond: bool
    response_priority: str  # "high", "medium", "low", "none"
    reason: str  # Why the decision was made
    
    # If should_respond is False
    skip_reason: Optional[str]  # "limit_reached", "not_relevant", "strategic_silence"


class GeneratedResponse(TypedDict, total=False):
    """A generated chat response."""
    
    content: str
    tone: str  # "friendly", "defensive", "aggressive", "deceptive", "casual"
    
    # Strategy
    strategy: str  # "deflect", "accuse", "ally", "bluff", "honest", "vague"
    bluffing: bool  # Is agent lying/bluffing in this response
    
    # Metadata
    confidence: float  # How confident agent is in this response


class ActionUpdateDecision(TypedDict, total=False):
    """Decision about whether to update pending action based on conversation."""
    
    should_update: bool
    reason: str
    
    # New action details (if updating)
    new_action: Optional[CoupAction]
    new_target: Optional[str]
    new_upgrade: bool
    new_upgrade_type: Optional[UpgradeType]


class ChatReasoningState(TypedDict, total=False):
    """
    State for the chat reasoning workflow.
    
    Tracks the full context needed to analyze a message and generate a response.
    """
    
    # =============================================
    # Agent Identity & Context
    # =============================================
    agent_id: str
    game_id: str
    agent_name: str
    agent_personality: str
    agent_play_style: str
    
    # =============================================
    # Incoming Message
    # =============================================
    incoming_message: ChatMessage
    sender_id: str
    sender_is_llm: bool
    source_platform: SocialMediaPlatform
    
    # =============================================
    # Agent's Game State (snapshot)
    # =============================================
    coins: int
    hand: List[InfluenceCard]
    revealed: List[InfluenceCard]
    players_alive: List[str]
    
    # Current pending action
    pending_action: Optional[Dict]
    pending_upgrade: Optional[Dict]
    action_locked: bool
    
    # What agent sees of other players
    visible_pending_actions: List[VisiblePendingAction]
    
    # =============================================
    # Message Limits
    # =============================================
    target_type: MessageTargetType
    can_respond: bool
    messages_remaining: int
    
    # =============================================
    # Chat History (recent)
    # =============================================
    recent_chat_history: List[ChatMessage]  # Last N messages for context
    
    # =============================================
    # Workflow Outputs (filled by nodes)
    # =============================================
    
    # Analysis node output
    message_analysis: Optional[MessageAnalysis]
    
    # Decision node output
    response_decision: Optional[ResponseDecision]
    
    # Generation node output
    generated_response: Optional[GeneratedResponse]
    
    # Action update node output
    action_update_decision: Optional[ActionUpdateDecision]
    
    # =============================================
    # Final Output
    # =============================================
    final_response: Optional[str]  # The actual response to send (or None)
    response_platform: SocialMediaPlatform  # Where to send response


def create_chat_reasoning_state(
    agent,  # BaseCoupAgent
    incoming_message: ChatMessage,
    sender_id: str,
    sender_is_llm: bool,
    source_platform: SocialMediaPlatform,
    recent_history: Optional[List[ChatMessage]] = None,
) -> ChatReasoningState:
    """
    Create a chat reasoning state from an agent and incoming message.
    
    Args:
        agent: The BaseCoupAgent processing this message
        incoming_message: The message to process
        sender_id: Who sent the message
        sender_is_llm: Whether sender is an LLM agent
        source_platform: Platform the message came from
        recent_history: Recent chat history for context
        
    Returns:
        Initialized ChatReasoningState
    """
    from app.constants import MESSAGE_LIMITS
    
    # Determine target type for response
    if sender_is_llm:
        target_type = MessageTargetType.LLM_ONLY
    else:
        target_type = MessageTargetType.HUMAN_ONLY
    
    # Check if can respond
    can_respond = agent.can_send_message(target_type)
    
    # Get remaining messages
    from app.services.message_counter_service import MessageCounterService
    messages_remaining = MessageCounterService.get_remaining(agent.state, target_type)
    
    return ChatReasoningState(
        # Identity
        agent_id=agent.agent_id,
        game_id=agent.game_id,
        agent_name=agent.name,
        agent_personality=agent.personality,
        agent_play_style=agent.play_style,
        
        # Incoming
        incoming_message=incoming_message,
        sender_id=sender_id,
        sender_is_llm=sender_is_llm,
        source_platform=source_platform,
        
        # Game state
        coins=agent.get_coins(),
        hand=agent.get_hand(),
        revealed=agent.get_revealed(),
        players_alive=agent.state.get("players_alive", []),
        pending_action=agent.get_pending_action(),
        pending_upgrade=agent.get_pending_upgrade(),
        action_locked=agent.is_action_locked(),
        visible_pending_actions=agent.get_visible_pending_actions(),
        
        # Limits
        target_type=target_type,
        can_respond=can_respond,
        messages_remaining=messages_remaining,
        
        # History
        recent_chat_history=recent_history or [],
        
        # Outputs (to be filled)
        message_analysis=None,
        response_decision=None,
        generated_response=None,
        action_update_decision=None,
        final_response=None,
        response_platform=source_platform,
    )

