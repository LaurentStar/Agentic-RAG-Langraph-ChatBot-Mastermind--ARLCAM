"""
Game Phase State Models.

Defines TypedDicts for pending reactions and card selections in the
two-phase hourly Coup game cycle.

Game Flow (91 minutes per round):
    Phase 1 (50 min) - Action selection, chat, persuasion
    Lockout 1 (10 min) - Game server calculates which actions need reactions
    Phase 2 (20 min) - Rebuttals, blocks, challenges, card selections
    Lockout 2 (10 min) - Game server calculates final outcomes
    Broadcast (1 min) - Results announced, cards revealed, eliminations

Note: GamePhase enum is now in app.constants for centralized access.
"""

from typing import List, Optional, TypedDict

from app.constants import CoupAction, GamePhase, InfluenceCard, ReactionType


# =============================================
# Pending Reaction Models
# =============================================

class PendingReaction(TypedDict, total=False):
    """
    A pending reaction set during Phase 2.
    
    Agents can set multiple pending reactions. During resolution,
    the game server processes them in priority order.
    
    Reactions can be:
    - Specific: "I challenge Player1's Duke claim" (target_action_id set)
    - Conditional: "I challenge any Duke claim" (conditional_rule set)
    """
    reaction_id: str                       # Unique identifier for this reaction
    reaction_type: ReactionType            # challenge, challenge_block, block, pass
    target_action_id: Optional[str]        # Specific: which action to react to
    target_player_id: Optional[str]        # Who performed the action
    conditional_rule: Optional[str]        # Conditional: "challenge_any_duke", etc.
    claimed_role: Optional[InfluenceCard]  # For blocks: which role you claim
    priority: int                          # If multiple reactions trigger, which first (lower = higher priority)
    reasoning: Optional[str]               # Agent's reasoning for this reaction


class VisiblePendingReaction(TypedDict, total=False):
    """
    What other players can see about a pending reaction.
    
    During Phase 2, all pending reactions are visible to all players.
    This allows for counter-reactions and strategic chat.
    """
    reaction_id: str
    player_id: str                         # Who set this reaction
    reaction_type: ReactionType            # challenge, block, etc.
    target_action_id: Optional[str]        # Which action they're reacting to
    target_player_id: Optional[str]        # Who performed the action
    is_conditional: bool                   # True if using a conditional rule
    claimed_role: Optional[InfluenceCard]  # For blocks: what role they claim


class ActionRequiringReaction(TypedDict, total=False):
    """
    An action from Phase 1 that requires this agent's reaction.
    
    Sent to agents at the start of Phase 2 so they know what
    actions they need to respond to.
    """
    action_id: str                         # Unique identifier for the action
    actor_id: str                          # Who performed the action
    action: CoupAction                     # steal, assassinate, etc.
    target_id: Optional[str]               # Target of the action (if any)
    claimed_role: Optional[InfluenceCard]  # Role claimed for the action
    is_upgraded: bool                      # Whether the action is upgraded
    affects_me: bool                       # True if I'm the target or can react
    reaction_options: List[str]            # What reactions I can make: ["challenge", "block", "pass"]


# =============================================
# Card Selection Models
# =============================================

class PendingCardSelection(TypedDict, total=False):
    """
    A pending card selection for Ambassador exchange or card reveal.
    
    Set during Phase 2 when an agent's action requires them to
    select cards (e.g., Ambassador exchange, or pre-selecting
    which card to reveal if they lose a challenge).
    """
    selection_id: str                      # Unique identifier
    selection_type: str                    # "exchange" or "reveal"
    triggered_by_action_id: str            # Which action triggered this
    available_cards: List[InfluenceCard]   # Cards agent can choose from
    selected_cards: List[InfluenceCard]    # Cards agent has selected
    num_required: int                      # How many cards must be selected
    is_finalized: bool                     # True if selection is locked


class CardRevealPreference(TypedDict, total=False):
    """
    Agent's preference for which card to reveal if they lose influence.
    
    Set during Phase 2 to pre-declare which card to reveal in various
    scenarios (e.g., "if I lose a challenge, reveal my Captain first").
    """
    preference_id: str
    scenario: str                          # "challenge_lost", "assassination", "coup"
    card_priority: List[InfluenceCard]     # Order of preference (first = reveal first)
    reasoning: Optional[str]


# =============================================
# Phase Transition Models
# =============================================

class PhaseTransitionInfo(TypedDict, total=False):
    """
    Information about a phase transition.
    
    Sent by game server when the phase changes.
    """
    previous_phase: GamePhase
    new_phase: GamePhase
    phase_duration_minutes: int            # How long this phase lasts
    phase_end_time: str                    # ISO timestamp when phase ends
    actions_to_react_to: List[ActionRequiringReaction]  # Only in Phase 2 transition
    summary: str                           # Human-readable summary of what happened
