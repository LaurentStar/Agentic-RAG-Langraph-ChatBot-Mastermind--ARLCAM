"""
Decision nodes for the Coup agent graph.

Each node handles one of the three entry points:
    - select_action_node: SELECT_ACTION (your turn)
    - react_node: REACT (voluntary response)
    - resolve_node: RESOLVE (forced completion)

Sub-routing within REACT and RESOLVE is handled via their respective enums.
The nodes use the decision blender to combine heuristic and LLM reasoning.
"""

from typing import Any, Dict

from app.constants import (
    CoupAction,
    InfluenceCard,
    ReactionType,
    ResolutionType,
)
from app.models.graph_state_models.coup_agent_state import CoupAgentState, PublicEvent


# =============================================
# SELECT_ACTION Node
# =============================================
def select_action_node(state: CoupAgentState) -> Dict[str, Any]:
    """
    SELECT_ACTION: It's the agent's turn - choose an action.

    This node uses the decision blender to combine heuristic and LLM reasoning
    based on agent modulators.

    Returns state update with chosen_action.
    """
    from app.services.decision_blender_service import get_blended_action

    me = state.get("me", "agent")

    # Get blended decision (heuristic + optional LLM)
    decision = get_blended_action(state)

    # Build the chosen action as a PublicEvent
    chosen_action: PublicEvent = {
        "actor": me,
        "action": decision.action,
        "target": decision.target,
        "succeeded": None,  # Will be set by game engine
        "challenged_by": None,
        "blocked_by": None,
    }

    return {
        "chosen_action": chosen_action,
    }


# =============================================
# REACT Node
# =============================================
def react_node(state: CoupAgentState) -> Dict[str, Any]:
    """
    REACT: Voluntary response to another player's action.

    Sub-routes based on reaction_type:
        - CHALLENGE: Should we challenge the actor's claim?
        - CHALLENGE_BLOCK: Should we challenge the blocker's claim?
        - BLOCK: Should we block the action targeting us?

    Returns state update with chosen_reaction.
    """
    from app.services.coup_heuristics import (
        decide_block_heuristic,
        decide_challenge_heuristic,
    )

    reaction_type = state.get("reaction_type")
    pending_reaction = state.get("pending_reaction")
    hand = state.get("hand", [])
    agent_profile = state.get("agent_profile")

    if reaction_type == ReactionType.CHALLENGE:
        # Decide whether to challenge the actor's claim
        should_challenge, reasoning = decide_challenge_heuristic(
            event=pending_reaction,
            hand=hand,
            agent_profile=agent_profile,
            is_block_challenge=False,
        )
        chosen_reaction = CoupAction.CHALLENGE if should_challenge else CoupAction.PASS

    elif reaction_type == ReactionType.CHALLENGE_BLOCK:
        # Decide whether to challenge the blocker's claim
        should_challenge, reasoning = decide_challenge_heuristic(
            event=pending_reaction,
            hand=hand,
            agent_profile=agent_profile,
            is_block_challenge=True,
        )
        chosen_reaction = CoupAction.CHALLENGE if should_challenge else CoupAction.PASS

    elif reaction_type == ReactionType.BLOCK:
        # Decide whether to block and with what role
        should_block, block_action, reasoning = decide_block_heuristic(
            event=pending_reaction,
            hand=hand,
            agent_profile=agent_profile,
        )
        if should_block and block_action:
            chosen_reaction = block_action
        else:
            chosen_reaction = CoupAction.PASS

    else:
        # Default: pass
        chosen_reaction = CoupAction.PASS

    return {
        "chosen_reaction": chosen_reaction,
    }


# =============================================
# RESOLVE Node
# =============================================
def resolve_node(state: CoupAgentState) -> Dict[str, Any]:
    """
    RESOLVE: Forced completion (must respond).

    Sub-routes based on resolution_type:
        - REVEAL_CARD: Choose which card to lose
        - EXCHANGE_CARDS: Choose which cards to keep (Ambassador)

    Returns state update with chosen_reveal or chosen_exchange.
    """
    from app.services.coup_heuristics import (
        select_exchange_heuristic,
        select_reveal_heuristic,
    )

    resolution_type = state.get("resolution_type")
    hand = state.get("hand", [])
    agent_profile = state.get("agent_profile")

    if resolution_type == ResolutionType.REVEAL_CARD:
        # Choose which card to lose
        card_to_reveal, reasoning = select_reveal_heuristic(
            hand=hand,
            agent_profile=agent_profile,
        )
        return {
            "chosen_reveal": card_to_reveal,
        }

    elif resolution_type == ResolutionType.EXCHANGE_CARDS:
        # Choose which cards to keep from the pool
        # Note: For exchange, the hand should include the 2 drawn cards
        cards_to_keep, reasoning = select_exchange_heuristic(
            available_cards=hand,
            num_to_keep=min(2, len([c for c in state.get("hand", []) if c not in state.get("revealed", [])])),
            agent_profile=agent_profile,
        )
        return {
            "chosen_exchange": cards_to_keep,
        }

    else:
        # Should not happen - return empty update
        return {}

