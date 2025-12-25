"""
Heuristic functions for Coup agent decisions.

These provide rule-based recommendations that can be used alone or blended
with LLM reasoning via the decision blender.

Key heuristics:
    - Must coup at 10+ coins (forced by rules)
    - Block assassination if you have Contessa
    - Don't challenge if opponent likely has the card
    - Prefer safe plays when low on influence

Upgrade Integration:
    - select_action_heuristic_with_upgrade includes upgrade recommendations
    - Uses UpgradeDecisionService for upgrade logic
"""

from typing import List, Optional, Tuple

from app.constants import (
    AgentModulator,
    CoupAction,
    InfluenceCard,
    UpgradeType,
    # Card/Action mappings from constants
    ROLE_TO_ACTION,
    ACTION_TO_ROLE,
    UNCLAIMED_ACTIONS,
    TARGETED_ACTIONS,
    ACTION_COST,
)
from app.models.graph_state_models.coup_agent_state import AgentProfile, PublicEvent
from app.models.graph_state_models.hourly_coup_state import UpgradeDecision, VisiblePendingAction


# =============================================
# SELECT_ACTION Heuristic
# =============================================
def select_action_heuristic(
    coins: int,
    hand: List[InfluenceCard],
    players_alive: List[str],
    forced_targets: Optional[List[str]] = None,
    agent_profile: Optional[AgentProfile] = None,
) -> Tuple[CoupAction, Optional[str], Optional[InfluenceCard], str]:
    """
    Determine the best action based on game state and agent profile.

    Returns:
        (action, target, claimed_role, reasoning)
    """
    modulators = (agent_profile or {}).get("agent_modulators", {})
    aggression = modulators.get(AgentModulator.AGGRESSION, 0.5)
    bluff_confidence = modulators.get(AgentModulator.BLUFF_CONFIDENCE, 0.3)

    # Get valid targets (exclude self)
    me = (agent_profile or {}).get("agent_name", "me")
    valid_targets = [p for p in players_alive if p != me]
    if forced_targets:
        valid_targets = [t for t in valid_targets if t in forced_targets]

    target = valid_targets[0] if valid_targets else None

    # ========== FORCED PLAYS ==========

    # Rule: Must coup at 10+ coins
    if coins >= 10:
        return (
            CoupAction.COUP,
            target,
            None,
            "Forced coup at 10+ coins (game rules)."
        )

    # ========== AGGRESSIVE PLAYS (if coins allow) ==========

    # Can coup (7+ coins) - always safe, high aggression favors this
    if coins >= 7 and aggression > 0.6:
        return (
            CoupAction.COUP,
            target,
            None,
            f"Coup with {coins} coins (high aggression)."
        )

    # Can assassinate (3+ coins) with Assassin card
    if coins >= 3 and InfluenceCard.ASSASSIN in hand and aggression > 0.4:
        return (
            CoupAction.ASSASSINATE,
            target,
            InfluenceCard.ASSASSIN,
            "Assassinate with actual Assassin card."
        )

    # ========== SAFE ECONOMIC PLAYS ==========

    # Tax with Duke (3 coins, can be challenged but we have the card)
    if InfluenceCard.DUKE in hand:
        return (
            CoupAction.TAX,
            None,
            InfluenceCard.DUKE,
            "Tax with actual Duke - safe and efficient."
        )

    # Steal with Captain (2 coins from target, can be challenged/blocked)
    if InfluenceCard.CAPTAIN in hand and target:
        return (
            CoupAction.STEAL,
            target,
            InfluenceCard.CAPTAIN,
            "Steal with actual Captain."
        )

    # Exchange with Ambassador (refresh hand)
    if InfluenceCard.AMBASSADOR in hand and len(hand) < 2:
        return (
            CoupAction.EXCHANGE,
            None,
            InfluenceCard.AMBASSADOR,
            "Exchange to improve hand with Ambassador."
        )

    # ========== BLUFF PLAYS (if bluff_confidence is high) ==========

    if bluff_confidence > 0.5:
        # Bluff Duke for tax
        if InfluenceCard.DUKE not in hand:
            return (
                CoupAction.TAX,
                None,
                InfluenceCard.DUKE,
                f"Bluff Duke for tax (bluff_confidence={bluff_confidence:.2f})."
            )

    # ========== FALLBACK: SAFE PLAYS ==========

    # Foreign aid (2 coins, can be blocked by Duke)
    if coins < 7:
        return (
            CoupAction.FOREIGN_AID,
            None,
            None,
            "Foreign aid - safe 2 coins."
        )

    # Income (1 coin, cannot be blocked or challenged)
    return (
        CoupAction.INCOME,
        None,
        None,
        "Income - safest option."
    )


# =============================================
# SELECT_ACTION with UPGRADE Heuristic
# =============================================
def select_action_heuristic_with_upgrade(
    coins: int,
    hand: List[InfluenceCard],
    players_alive: List[str],
    forced_targets: Optional[List[str]] = None,
    agent_profile: Optional[AgentProfile] = None,
    visible_pending_actions: Optional[List[VisiblePendingAction]] = None,
) -> Tuple[CoupAction, Optional[str], Optional[InfluenceCard], Optional[UpgradeDecision], str]:
    """
    Determine the best action with upgrade recommendation.
    
    Extends select_action_heuristic to include upgrade decisions.

    Returns:
        (action, target, claimed_role, upgrade_decision, reasoning)
    """
    from app.services.upgrade_decision_service import UpgradeDecisionService
    
    # First get the base action recommendation
    action, target, claimed_role, reasoning = select_action_heuristic(
        coins=coins,
        hand=hand,
        players_alive=players_alive,
        forced_targets=forced_targets,
        agent_profile=agent_profile,
    )
    
    # Check if action can be upgraded
    if not UpgradeDecisionService.can_upgrade(action):
        return action, target, claimed_role, None, reasoning
    
    # Get upgrade recommendation
    upgrade_decision = UpgradeDecisionService.should_upgrade(
        action=action,
        coins=coins,
        hand=hand,
        target=target,
        agent_profile=agent_profile,
        visible_pending_actions=visible_pending_actions,
        players_alive=players_alive,
    )
    
    # Update reasoning if upgrading
    if upgrade_decision.get("upgrade"):
        upgrade_type = upgrade_decision.get("upgrade_type")
        total_cost = upgrade_decision.get("total_cost", 0)
        reasoning = f"{reasoning} UPGRADED with {upgrade_type.value} (total cost: {total_cost} coins)."
    
    return action, target, claimed_role, upgrade_decision, reasoning


# =============================================
# CHALLENGE Heuristic
# =============================================
def decide_challenge_heuristic(
    event: Optional[PublicEvent],
    hand: List[InfluenceCard],
    agent_profile: Optional[AgentProfile] = None,
    is_block_challenge: bool = False,
) -> Tuple[bool, str]:
    """
    Decide whether to challenge an action or block claim.

    Returns:
        (should_challenge, reasoning)
    """
    if not event:
        return False, "No event to challenge."

    modulators = (agent_profile or {}).get("agent_modulators", {})
    challenge_tendency = modulators.get(AgentModulator.CHALLENGE_TENDENCY, 0.3)
    risk_tolerance = modulators.get(AgentModulator.RISK_TOLERANCE, 0.5)

    action = event.get("action")

    # Determine what role is being claimed
    if action in ACTION_TO_ROLE:
        claimed_role = ACTION_TO_ROLE[action]
        if isinstance(claimed_role, list):
            claimed_roles = claimed_role
        else:
            claimed_roles = [claimed_role]
    else:
        return False, "Action doesn't claim a role."

    # If we hold the claimed role(s), more likely they're bluffing
    we_hold_claimed = any(role in hand for role in claimed_roles)

    if we_hold_claimed:
        if challenge_tendency > 0.2 or risk_tolerance > 0.5:
            return True, f"Challenge: we hold {claimed_roles[0]}, opponent likely bluffing."

    if challenge_tendency < 0.3:
        return False, "Low challenge tendency - let it pass."

    if challenge_tendency > 0.6 and risk_tolerance > 0.4:
        return True, f"High challenge tendency ({challenge_tendency:.2f}) - risky challenge."

    return False, "Default: don't challenge without strong evidence."


# =============================================
# BLOCK Heuristic
# =============================================
def decide_block_heuristic(
    event: Optional[PublicEvent],
    hand: List[InfluenceCard],
    agent_profile: Optional[AgentProfile] = None,
) -> Tuple[bool, Optional[CoupAction], str]:
    """
    Decide whether to block an action and with what.

    Returns:
        (should_block, block_action, reasoning)
    """
    if not event:
        return False, None, "No event to block."

    modulators = (agent_profile or {}).get("agent_modulators", {})
    block_tendency = modulators.get(AgentModulator.BLOCK_TENDENCY, 0.5)
    bluff_confidence = modulators.get(AgentModulator.BLUFF_CONFIDENCE, 0.3)

    action = event.get("action")

    # ========== MUST BLOCK: Assassination with Contessa ==========
    if action == CoupAction.ASSASSINATE and InfluenceCard.CONTESSA in hand:
        return True, CoupAction.BLOCK_ASSASSINATE, "Block assassination with actual Contessa (must block)."

    # ========== CAN BLOCK: Foreign Aid with Duke ==========
    if action == CoupAction.FOREIGN_AID:
        if InfluenceCard.DUKE in hand:
            if block_tendency > 0.3:
                return True, CoupAction.BLOCK_FOREIGN_AID, "Block foreign aid with actual Duke."
        elif bluff_confidence > 0.5:
            return True, CoupAction.BLOCK_FOREIGN_AID, "Bluff Duke to block foreign aid."

    # ========== CAN BLOCK: Steal with Captain/Ambassador ==========
    if action == CoupAction.STEAL:
        if InfluenceCard.CAPTAIN in hand:
            if block_tendency > 0.3:
                return True, CoupAction.BLOCK_STEAL, "Block steal with actual Captain."
        elif InfluenceCard.AMBASSADOR in hand:
            if block_tendency > 0.3:
                return True, CoupAction.BLOCK_STEAL, "Block steal with actual Ambassador."
        elif bluff_confidence > 0.6:
            return True, CoupAction.BLOCK_STEAL, "Bluff to block steal."

    # ========== BLUFF BLOCK: Assassination without Contessa ==========
    if action == CoupAction.ASSASSINATE and InfluenceCard.CONTESSA not in hand:
        if bluff_confidence > 0.7:
            return True, CoupAction.BLOCK_ASSASSINATE, "Desperate bluff: block assassination without Contessa."

    return False, None, "No block available or tendency too low."


# =============================================
# REVEAL Heuristic
# =============================================
def select_reveal_heuristic(
    hand: List[InfluenceCard],
    agent_profile: Optional[AgentProfile] = None,
) -> Tuple[Optional[InfluenceCard], str]:
    """
    Choose which card to reveal (lose) when forced.

    Returns:
        (card_to_reveal, reasoning)
    """
    if not hand:
        return None, "No cards to reveal."

    if len(hand) == 1:
        return hand[0], "Only one card left - must reveal it."

    # Card value ranking (higher = more valuable to keep)
    card_values = {
        InfluenceCard.CONTESSA: 5,
        InfluenceCard.DUKE: 4,
        InfluenceCard.CAPTAIN: 3,
        InfluenceCard.AMBASSADOR: 2,
        InfluenceCard.ASSASSIN: 3,
    }

    hand_with_values = [(card, card_values.get(card, 0)) for card in hand]
    hand_with_values.sort(key=lambda x: x[1])

    card_to_reveal = hand_with_values[0][0]
    return card_to_reveal, f"Reveal {card_to_reveal.value} as least valuable card."


# =============================================
# EXCHANGE Heuristic
# =============================================
def select_exchange_heuristic(
    available_cards: List[InfluenceCard],
    num_to_keep: int,
    agent_profile: Optional[AgentProfile] = None,
) -> Tuple[List[InfluenceCard], str]:
    """
    Choose which cards to keep from the exchange pool.

    Args:
        available_cards: Current hand + 2 drawn cards
        num_to_keep: Number of cards to keep (1 or 2)

    Returns:
        (cards_to_keep, reasoning)
    """
    if not available_cards:
        return [], "No cards available."

    if len(available_cards) <= num_to_keep:
        return available_cards, "Keep all available cards."

    modulators = (agent_profile or {}).get("agent_modulators", {})
    aggression = modulators.get(AgentModulator.AGGRESSION, 0.5)

    # Dynamic card values based on playstyle
    base_values = {
        InfluenceCard.CONTESSA: 5,
        InfluenceCard.DUKE: 4,
        InfluenceCard.CAPTAIN: 3,
        InfluenceCard.AMBASSADOR: 2,
        InfluenceCard.ASSASSIN: 3,
    }

    # Adjust for aggression
    if aggression > 0.6:
        base_values[InfluenceCard.ASSASSIN] = 5
        base_values[InfluenceCard.CAPTAIN] = 4

    cards_with_values = [(card, base_values.get(card, 0)) for card in available_cards]
    cards_with_values.sort(key=lambda x: x[1], reverse=True)

    cards_to_keep = [card for card, _ in cards_with_values[:num_to_keep]]
    kept_names = [c.value for c in cards_to_keep]

    return cards_to_keep, f"Keep {kept_names} as highest value cards."
