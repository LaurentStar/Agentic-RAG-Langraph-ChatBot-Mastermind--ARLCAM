"""
Reaction Nodes for Phase 2 Decision Making.

These nodes handle the reaction workflow during Phase 2 of the hourly Coup game:
1. Analyze actions targeting the agent
2. Decide whether to react (challenge, block, pass)
3. Set specific or conditional reactions
4. Update the pending reactions in PostgreSQL
5. Optionally generate chat about the reaction
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid

from app.constants import (
    CoupAction,
    InfluenceCard,
    MessageTargetType,
    ReactionType,
    SocialMediaPlatform,
)
from app.models.graph_state_models.game_phase_state import (
    ActionRequiringReaction,
    PendingReaction,
)
from app.models.graph_state_models.hourly_coup_state import HourlyCoupAgentState


# =============================================
# Reaction State Model
# =============================================

class ReactionWorkflowState(HourlyCoupAgentState, total=False):
    """
    Extended state for the reaction workflow.
    
    Adds workflow-specific fields for tracking analysis and decisions.
    """
    # Analysis results
    analyzed_actions: List[Dict[str, Any]]  # Actions analyzed with threat assessment
    
    # Decision for each action
    reaction_decisions: List[Dict[str, Any]]  # List of decisions (react, pass, conditional)
    
    # Generated reactions
    new_pending_reactions: List[PendingReaction]
    
    # Chat generation
    should_chat_about_reactions: bool
    reaction_chat_content: Optional[str]
    
    # Workflow status
    reactions_updated_in_db: bool


# =============================================
# Node Functions
# =============================================

def analyze_actions_node(state: ReactionWorkflowState) -> Dict[str, Any]:
    """
    Analyze all actions that require this agent's reaction.
    
    For each action, assess:
    - Threat level (how dangerous is this to me?)
    - Bluff likelihood (is this a bluff I should challenge?)
    - Block opportunity (can I block this?)
    - Strategic value (is it worth reacting?)
    """
    actions_to_analyze = state.get("actions_requiring_my_reaction", [])
    agent_id = state.get("me", "")
    hand = state.get("hand", [])
    coins = state.get("coins", 0)
    
    analyzed_actions = []
    
    for action in actions_to_analyze:
        analysis = {
            "action_id": action.get("action_id"),
            "actor_id": action.get("actor_id"),
            "action": action.get("action"),
            "target_id": action.get("target_id"),
            "claimed_role": action.get("claimed_role"),
            "is_upgraded": action.get("is_upgraded", False),
            "affects_me": action.get("affects_me", False),
            "reaction_options": action.get("reaction_options", []),
            
            # Computed analysis
            "threat_level": _compute_threat_level(action, agent_id, hand, coins),
            "bluff_likelihood": _compute_bluff_likelihood(action, hand),
            "can_block": _can_block_action(action, hand),
            "strategic_value": _compute_strategic_value(action, agent_id, hand),
        }
        analyzed_actions.append(analysis)
    
    return {"analyzed_actions": analyzed_actions}


def decide_reactions_node(state: ReactionWorkflowState) -> Dict[str, Any]:
    """
    Decide how to react to each analyzed action.
    
    Uses agent modulators (challenge_tendency, block_tendency, risk_tolerance)
    to influence decisions.
    
    Decision types:
    - specific_challenge: Challenge a specific action
    - specific_block: Block a specific action
    - conditional_challenge: Set a conditional rule (e.g., "challenge any Duke")
    - conditional_block: Set a conditional block rule
    - pass: Take no action
    """
    analyzed_actions = state.get("analyzed_actions", [])
    agent_profile = state.get("agent_profile", {})
    hand = state.get("hand", [])
    
    # Get modulator values (default to 0.5 if not set)
    modulators = agent_profile.get("modulators", {})
    challenge_tendency = modulators.get("challenge_tendency", 0.5)
    block_tendency = modulators.get("block_tendency", 0.5)
    risk_tolerance = modulators.get("risk_tolerance", 0.5)
    
    reaction_decisions = []
    
    for action_analysis in analyzed_actions:
        decision = _make_reaction_decision(
            action_analysis,
            hand,
            challenge_tendency,
            block_tendency,
            risk_tolerance,
        )
        reaction_decisions.append(decision)
    
    return {"reaction_decisions": reaction_decisions}


def set_specific_reactions_node(state: ReactionWorkflowState) -> Dict[str, Any]:
    """
    Create PendingReaction objects for specific reactions.
    
    These target a specific action by ID.
    """
    reaction_decisions = state.get("reaction_decisions", [])
    hand = state.get("hand", [])
    
    new_pending_reactions = []
    priority = 1
    
    for decision in reaction_decisions:
        if decision.get("decision_type") in ("specific_challenge", "specific_block"):
            reaction_type = (
                ReactionType.CHALLENGE if "challenge" in decision.get("decision_type")
                else ReactionType.BLOCK
            )
            
            # For blocks, determine which role to claim
            claimed_role = None
            if reaction_type == ReactionType.BLOCK:
                claimed_role = _get_block_role(decision.get("action"), hand)
            
            pending_reaction = PendingReaction(
                reaction_id=str(uuid.uuid4()),
                reaction_type=reaction_type,
                target_action_id=decision.get("action_id"),
                target_player_id=decision.get("actor_id"),
                conditional_rule=None,
                claimed_role=claimed_role,
                priority=priority,
                reasoning=decision.get("reasoning"),
            )
            new_pending_reactions.append(pending_reaction)
            priority += 1
    
    return {"new_pending_reactions": new_pending_reactions}


def set_conditional_reactions_node(state: ReactionWorkflowState) -> Dict[str, Any]:
    """
    Add conditional reaction rules.
    
    These trigger automatically based on rules like "challenge_any_duke".
    """
    reaction_decisions = state.get("reaction_decisions", [])
    existing_reactions = state.get("new_pending_reactions", [])
    hand = state.get("hand", [])
    
    new_pending_reactions = list(existing_reactions)  # Copy existing
    priority = len(new_pending_reactions) + 1
    
    for decision in reaction_decisions:
        if decision.get("decision_type") in ("conditional_challenge", "conditional_block"):
            reaction_type = (
                ReactionType.CHALLENGE if "challenge" in decision.get("decision_type")
                else ReactionType.BLOCK
            )
            
            # For conditional blocks, we might need to claim a role
            claimed_role = None
            if reaction_type == ReactionType.BLOCK:
                claimed_role = _get_block_role_for_conditional(
                    decision.get("conditional_rule"),
                    hand
                )
            
            pending_reaction = PendingReaction(
                reaction_id=str(uuid.uuid4()),
                reaction_type=reaction_type,
                target_action_id=None,  # Not specific to one action
                target_player_id=None,
                conditional_rule=decision.get("conditional_rule"),
                claimed_role=claimed_role,
                priority=priority,
                reasoning=decision.get("reasoning"),
            )
            new_pending_reactions.append(pending_reaction)
            priority += 1
    
    return {"new_pending_reactions": new_pending_reactions}


def update_db_node(state: ReactionWorkflowState) -> Dict[str, Any]:
    """
    Update the pending reactions in PostgreSQL.
    
    This makes the reactions visible to other players and
    ready for the game server to process.
    """
    from app.extensions import db_connection
    
    agent_id = state.get("me", "")
    game_id = state.get("game_id", "")
    new_pending_reactions = state.get("new_pending_reactions", [])
    
    try:
        # TODO: Implement actual DB update when schema is defined
        # For now, just mark as successful
        # with db_connection.get_session() as session:
        #     ... update pending_reactions table ...
        
        return {
            "reactions_updated_in_db": True,
            "pending_reactions": new_pending_reactions,
        }
    except Exception as e:
        return {
            "reactions_updated_in_db": False,
            "error": f"Failed to update reactions in DB: {str(e)}",
        }


def decide_chat_about_reactions_node(state: ReactionWorkflowState) -> Dict[str, Any]:
    """
    Decide whether the agent should chat about their reactions.
    
    Consider:
    - Message limits
    - Strategic value of revealing/hiding reaction intent
    - Agent personality (some agents are more vocal)
    """
    new_pending_reactions = state.get("new_pending_reactions", [])
    agent_profile = state.get("agent_profile", {})
    human_messages_sent = state.get("human_messages_sent", 0)
    mixed_messages_sent = state.get("mixed_messages_sent", 0)
    
    # Check if we have message budget
    from app.constants import MESSAGE_LIMITS
    can_message = (
        human_messages_sent < MESSAGE_LIMITS[MessageTargetType.HUMAN_ONLY]
        or mixed_messages_sent < MESSAGE_LIMITS[MessageTargetType.MIXED]
    )
    
    # Check if there are significant reactions to discuss
    has_significant_reactions = any(
        r.get("reaction_type") != ReactionType.PASS
        for r in new_pending_reactions
    )
    
    # Agent personality affects chat tendency
    modulators = agent_profile.get("modulators", {})
    # Higher bluff confidence might mean more trash talk
    bluff_confidence = modulators.get("bluff_confidence", 0.5)
    
    should_chat = (
        can_message
        and has_significant_reactions
        and bluff_confidence > 0.3  # Shy agents might not chat
    )
    
    return {"should_chat_about_reactions": should_chat}


def generate_reaction_chat_node(state: ReactionWorkflowState) -> Dict[str, Any]:
    """
    Generate chat content about the agent's reactions.
    
    This can be:
    - Threatening ("I see that steal attempt...")
    - Bluffing ("Go ahead, try me...")
    - Strategic misdirection
    """
    new_pending_reactions = state.get("new_pending_reactions", [])
    agent_profile = state.get("agent_profile", {})
    
    # For now, generate a simple message
    # TODO: Use LLM for more sophisticated chat generation
    
    chat_content = None
    
    if new_pending_reactions:
        # Find the most significant reaction
        for reaction in new_pending_reactions:
            if reaction.get("reaction_type") == ReactionType.CHALLENGE:
                chat_content = "I have some doubts about what's happening here..."
                break
            elif reaction.get("reaction_type") == ReactionType.BLOCK:
                chat_content = "I might have something to say about that..."
                break
    
    return {"reaction_chat_content": chat_content}


# =============================================
# Helper Functions
# =============================================

def _compute_threat_level(
    action: ActionRequiringReaction,
    agent_id: str,
    hand: List[InfluenceCard],
    coins: int
) -> float:
    """Compute how threatening an action is (0.0 to 1.0)."""
    threat = 0.0
    
    action_type = action.get("action")
    target = action.get("target_id")
    
    # Direct targeting is threatening
    if target == agent_id:
        if action_type == CoupAction.ASSASSINATE:
            threat = 0.9
        elif action_type == CoupAction.STEAL:
            threat = 0.5 if coins > 2 else 0.3
        elif action_type == CoupAction.COUP:
            threat = 1.0  # Can't block a Coup
    
    # Upgraded actions are more threatening
    if action.get("is_upgraded"):
        threat = min(threat + 0.1, 1.0)
    
    return threat


def _compute_bluff_likelihood(
    action: ActionRequiringReaction,
    hand: List[InfluenceCard]
) -> float:
    """Estimate likelihood the action is a bluff (0.0 to 1.0)."""
    claimed_role = action.get("claimed_role")
    
    if not claimed_role:
        return 0.0  # No claim to challenge
    
    # If I have the claimed role, they're more likely bluffing
    my_claimed_copies = sum(1 for card in hand if card.value == claimed_role)
    
    # Base probability (3 copies in deck, I have some)
    if my_claimed_copies >= 2:
        return 0.7  # I have 2+, very likely bluff
    elif my_claimed_copies == 1:
        return 0.4  # I have 1, moderate chance
    else:
        return 0.2  # I have 0, low chance


def _can_block_action(
    action: ActionRequiringReaction,
    hand: List[InfluenceCard]
) -> bool:
    """Check if agent has cards that can block this action."""
    action_type = action.get("action")
    
    block_cards = {
        CoupAction.STEAL: [InfluenceCard.CAPTAIN, InfluenceCard.AMBASSADOR],
        CoupAction.ASSASSINATE: [InfluenceCard.CONTESSA],
        CoupAction.FOREIGN_AID: [InfluenceCard.DUKE],
    }
    
    blocking_cards = block_cards.get(action_type, [])
    return any(card in blocking_cards for card in hand)


def _compute_strategic_value(
    action: ActionRequiringReaction,
    agent_id: str,
    hand: List[InfluenceCard]
) -> float:
    """Compute strategic value of reacting (0.0 to 1.0)."""
    # Higher value = more worth reacting to
    value = 0.5  # Base value
    
    # High threat actions are worth reacting to
    if action.get("target_id") == agent_id:
        value += 0.3
    
    # If we have blocking cards, blocking is valuable
    if _can_block_action(action, hand):
        value += 0.2
    
    return min(value, 1.0)


def _make_reaction_decision(
    action_analysis: Dict[str, Any],
    hand: List[InfluenceCard],
    challenge_tendency: float,
    block_tendency: float,
    risk_tolerance: float,
) -> Dict[str, Any]:
    """Make a reaction decision for a single action."""
    decision = {
        "action_id": action_analysis.get("action_id"),
        "actor_id": action_analysis.get("actor_id"),
        "action": action_analysis.get("action"),
        "decision_type": "pass",
        "reasoning": "No action taken",
    }
    
    threat_level = action_analysis.get("threat_level", 0)
    bluff_likelihood = action_analysis.get("bluff_likelihood", 0)
    can_block = action_analysis.get("can_block", False)
    
    # Decide to challenge if bluff likelihood is high enough
    challenge_threshold = 1.0 - challenge_tendency  # Higher tendency = lower threshold
    if bluff_likelihood > challenge_threshold and risk_tolerance > 0.3:
        decision["decision_type"] = "specific_challenge"
        decision["reasoning"] = f"High bluff likelihood ({bluff_likelihood:.2f}), challenging"
        return decision
    
    # Decide to block if we can and threat is high
    block_threshold = 1.0 - block_tendency
    if can_block and threat_level > block_threshold:
        decision["decision_type"] = "specific_block"
        decision["reasoning"] = f"High threat ({threat_level:.2f}), blocking"
        return decision
    
    # Default to pass
    decision["reasoning"] = "Threat level acceptable, no reaction needed"
    return decision


def _get_block_role(action: CoupAction, hand: List[InfluenceCard]) -> Optional[InfluenceCard]:
    """Get the role to claim for blocking an action."""
    block_cards = {
        CoupAction.STEAL: [InfluenceCard.CAPTAIN, InfluenceCard.AMBASSADOR],
        CoupAction.ASSASSINATE: [InfluenceCard.CONTESSA],
        CoupAction.FOREIGN_AID: [InfluenceCard.DUKE],
    }
    
    blocking_cards = block_cards.get(action, [])
    
    # Prefer to claim a card we actually have
    for card in blocking_cards:
        if card in hand:
            return card
    
    # Otherwise, bluff with first available option
    return blocking_cards[0] if blocking_cards else None


def _get_block_role_for_conditional(
    conditional_rule: str,
    hand: List[InfluenceCard]
) -> Optional[InfluenceCard]:
    """Get the role to claim for a conditional block rule."""
    # Map conditional rules to blocking roles
    rule_to_role = {
        "block_any_steal_on_me": [InfluenceCard.CAPTAIN, InfluenceCard.AMBASSADOR],
        "always_block_assassination": [InfluenceCard.CONTESSA],
        "block_foreign_aid": [InfluenceCard.DUKE],
    }
    
    blocking_cards = rule_to_role.get(conditional_rule, [])
    
    # Prefer to claim a card we actually have
    for card in blocking_cards:
        if card in hand:
            return card
    
    return blocking_cards[0] if blocking_cards else None

