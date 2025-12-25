"""
Hourly Coup Agent State Model.

Extends CoupAgentState with hourly-specific tracking:
- Message counters per target type (LLM/Human/Mixed)
- Pending action with optional upgrade
- Cross-platform context
- Visible pending actions from other players

This state is per-agent - each LLM agent in a game has their own instance.
"""

from datetime import datetime
from typing import Dict, List, Optional, TypedDict

from app.constants import (
    CoupAction,
    EventType,
    GamePhase,
    InfluenceCard,
    MessageTargetType,
    SocialMediaPlatform,
    UpgradeType,
)
from app.models.graph_state_models.coup_agent_state import CoupAgentState, PublicEvent
from app.models.graph_state_models.game_phase_state import (
    PendingReaction,
    VisiblePendingReaction,
    ActionRequiringReaction,
    PendingCardSelection,
)


# =============================================
# Supporting Models
# =============================================

class ChatMessage(TypedDict, total=False):
    """A chat message in the conversation history."""
    sender_id: str
    sender_is_llm: bool
    platform: SocialMediaPlatform
    content: str
    timestamp: datetime
    game_id: str


class UpgradeDecision(TypedDict, total=False):
    """Details about an action upgrade decision."""
    action: CoupAction
    upgrade: bool
    upgrade_type: Optional[UpgradeType]
    total_cost: int


class VisiblePendingAction(TypedDict, total=False):
    """
    What agents can see of other players' pending actions.
    
    Note: upgrade_type is intentionally NOT included - it's hidden information.
    Players can see THAT someone upgraded, but not WHAT the upgrade does.
    """
    player_id: str
    action: CoupAction
    target: Optional[str]
    is_upgraded: bool  # Visible to all
    timestamp: datetime


class IncomingEvent(TypedDict, total=False):
    """
    Unified event model for all incoming events to the LangGraph server.
    
    Every event carries platform metadata so agents know:
    - Where the event came from
    - Who sent it (and if they're an LLM)
    - Which game it belongs to
    - Which agent should process it
    """
    event_type: EventType
    source_platform: SocialMediaPlatform
    sender_id: str
    sender_is_llm: bool
    game_id: str
    timestamp: datetime
    payload: dict  # Event-specific data
    reply_to_platform: SocialMediaPlatform
    
    # Routing
    target_agent_id: Optional[str]  # Specific agent to process this
    broadcast_to_all_agents: bool   # True for game-wide events


# =============================================
# Hourly Coup Agent State
# =============================================

class HourlyCoupAgentState(CoupAgentState, total=False):
    """
    Extended agent state for hourly Coup gameplay.
    
    Adds to CoupAgentState:
    - Message tracking per target type with enforced limits
    - Pending action with optional upgrade for this hour (Phase 1)
    - Pending reactions (Phase 2)
    - Cross-platform awareness
    - Visible pending actions/reactions from other players
    
    Each LLM agent has their own isolated instance of this state.
    
    Two-Phase Game Flow:
        Phase 1 (50 min): Set pending_action, pending_upgrade
        Lockout 1 (10 min): action_locked = True
        Phase 2 (20 min): Set pending_reactions, pending_card_selection
        Lockout 2 (10 min): reactions_locked = True
        Broadcast (1 min): Results announced
    """
    
    # =============================================
    # Message Tracking (per hourly turn)
    # =============================================
    llm_messages_sent: int        # Max 30 per hour
    human_messages_sent: int      # Max 150 per hour
    mixed_messages_sent: int      # Max 30 per hour
    
    # =============================================
    # Phase Tracking
    # =============================================
    current_phase: GamePhase      # Which phase we're in
    
    # =============================================
    # Phase 1: Pending Action
    # =============================================
    pending_action: Optional[PublicEvent]
    pending_upgrade: Optional[UpgradeDecision]
    action_locked: bool           # True during Lockout 1 and later
    
    # =============================================
    # Phase 2: Pending Reactions
    # =============================================
    pending_reactions: List[PendingReaction]        # Multiple reactions allowed
    pending_card_selection: Optional[PendingCardSelection]  # Ambassador exchange / reveal
    reactions_locked: bool        # True during Lockout 2 and later
    
    # What actions I need to react to (received at Phase 2 start)
    actions_requiring_my_reaction: List[ActionRequiringReaction]
    
    # What reactions others have set (visible during Phase 2)
    visible_pending_reactions: List[VisiblePendingReaction]
    
    # =============================================
    # Chat Context
    # =============================================
    chat_history: List[ChatMessage]
    persuasion_targets: List[str]  # Players this agent wants to influence
    
    # =============================================
    # Hour Tracking
    # =============================================
    hour_start_time: datetime
    minutes_remaining: int
    
    # =============================================
    # Visible Game State (from PostgreSQL)
    # =============================================
    # Shows: player, action, target, is_upgraded (bool) - but NOT upgrade_type
    visible_pending_actions: List[VisiblePendingAction]
    
    # =============================================
    # Cross-Platform Context
    # =============================================
    current_event_platform: SocialMediaPlatform
    player_platforms: Dict[str, SocialMediaPlatform]  # {player_id: platform}


# =============================================
# Factory Functions
# =============================================

def create_initial_hourly_state(
    agent_id: str,
    game_id: str,
    coins: int = 2,
    hand: Optional[List[InfluenceCard]] = None,
    players_alive: Optional[List[str]] = None,
) -> HourlyCoupAgentState:
    """
    Create a fresh hourly state for an agent at the start of a game/hour.
    
    Args:
        agent_id: Unique identifier for this agent
        game_id: Current game ID
        coins: Starting coins (default 2)
        hand: Starting influence cards
        players_alive: List of all players in the game
    
    Returns:
        Initialized HourlyCoupAgentState
    """
    return HourlyCoupAgentState(
        # Identity
        me=agent_id,
        coins=coins,
        hand=hand or [],
        revealed=[],
        players_alive=players_alive or [],
        public_events=[],
        
        # Message counters (reset each hour)
        llm_messages_sent=0,
        human_messages_sent=0,
        mixed_messages_sent=0,
        
        # Phase tracking
        current_phase=GamePhase.PHASE1_ACTIONS,
        
        # Phase 1: Pending action
        pending_action=None,
        pending_upgrade=None,
        action_locked=False,
        
        # Phase 2: Pending reactions
        pending_reactions=[],
        pending_card_selection=None,
        reactions_locked=False,
        actions_requiring_my_reaction=[],
        visible_pending_reactions=[],
        
        # Chat
        chat_history=[],
        persuasion_targets=[],
        
        # Hour tracking
        hour_start_time=datetime.now(),
        minutes_remaining=60,
        
        # Visible state
        visible_pending_actions=[],
        
        # Platform context
        current_event_platform=SocialMediaPlatform.DEFUALT,
        player_platforms={},
    )


def reset_hourly_counters(state: HourlyCoupAgentState) -> HourlyCoupAgentState:
    """
    Reset message counters and action/reaction state at the start of a new hour.
    
    Called by AgentRegistry at hour boundaries.
    """
    # Message counters
    state["llm_messages_sent"] = 0
    state["human_messages_sent"] = 0
    state["mixed_messages_sent"] = 0
    
    # Phase tracking
    state["current_phase"] = GamePhase.PHASE1_ACTIONS
    
    # Phase 1: Pending action
    state["pending_action"] = None
    state["pending_upgrade"] = None
    state["action_locked"] = False
    
    # Phase 2: Pending reactions
    state["pending_reactions"] = []
    state["pending_card_selection"] = None
    state["reactions_locked"] = False
    state["actions_requiring_my_reaction"] = []
    state["visible_pending_reactions"] = []
    
    # Hour tracking
    state["hour_start_time"] = datetime.now()
    state["minutes_remaining"] = 60
    state["chat_history"] = []
    
    return state

