"""
Upgrade Decision Service.

Helps LLM agents decide whether to upgrade their actions.

Available Upgrades:
    - Assassinate + 2 coins = assassination_priority (target specific card)
    - Steal + 1 coin = kleptomania_steal (enhanced stealing)
    - Swap Influence + 4 coins = trigger_identity_crisis (force target swap)

Decision factors:
    - Available coins vs upgrade cost
    - Strategic value of the upgrade
    - Agent modulators (aggression, risk tolerance)
    - Game state (players remaining, known information)

Note: Other players can see THAT an action is upgraded, but NOT the upgrade type.
This creates bluffing opportunities in chat.
"""

from typing import List, Optional, Tuple

from app.constants import (
    AgentModulator,
    CoupAction,
    InfluenceCard,
)
from app.models.config_models.action_configs import (
    ActionConfig,
    ACTION_CONFIGS,
    get_action_config,
)
from app.models.graph_state_models.coup_agent_state import AgentProfile
from app.models.graph_state_models.hourly_coup_state import (
    UpgradeDecision,
    VisiblePendingAction,
)


class UpgradeDecisionService:
    """
    Service for deciding whether to upgrade actions.
    
    Usage:
        decision = UpgradeDecisionService.should_upgrade(
            action=CoupAction.ASSASSINATE,
            coins=7,
            hand=[InfluenceCard.ASSASSIN],
            target="player2",
            agent_profile=profile,
        )
    """
    
    @staticmethod
    def get_config(action: CoupAction) -> ActionConfig:
        """Get the configuration for an action."""
        return get_action_config(action)
    
    @staticmethod
    def can_upgrade(action: CoupAction) -> bool:
        """Check if an action can be upgraded."""
        return get_action_config(action).can_upgrade
    
    @staticmethod
    def get_upgrade_type(action: CoupAction):
        """Get the upgrade type for an action."""
        return get_action_config(action).upgrade_type
    
    @staticmethod
    def get_upgrade_cost(action: CoupAction) -> int:
        """Get the additional cost to upgrade an action."""
        return get_action_config(action).upgrade_cost
    
    @staticmethod
    def get_total_cost(action: CoupAction, upgraded: bool = False) -> int:
        """Get total cost of action (base + upgrade if applicable)."""
        config = get_action_config(action)
        if upgraded and config.can_upgrade:
            return config.total_upgraded_cost
        return config.base_cost
    
    @staticmethod
    def can_afford_upgrade(action: CoupAction, coins: int) -> bool:
        """Check if agent can afford the upgraded action."""
        return get_action_config(action).can_afford_upgraded(coins)
    
    @staticmethod
    def should_upgrade(
        action: CoupAction,
        coins: int,
        hand: List[InfluenceCard],
        target: Optional[str] = None,
        agent_profile: Optional[AgentProfile] = None,
        visible_pending_actions: Optional[List[VisiblePendingAction]] = None,
        players_alive: Optional[List[str]] = None,
    ) -> UpgradeDecision:
        """
        Decide whether to upgrade an action.
        
        Args:
            action: The action being taken
            coins: Agent's current coins
            hand: Agent's current hand
            target: Target player (for targeted actions)
            agent_profile: Agent's personality/modulators
            visible_pending_actions: What other players are doing
            players_alive: Who's still in the game
            
        Returns:
            UpgradeDecision with recommendation
        """
        # Can't upgrade non-upgradeable actions
        if not UpgradeDecisionService.can_upgrade(action):
            return UpgradeDecision(
                action=action,
                upgrade=False,
                upgrade_type=None,
                total_cost=UpgradeDecisionService.get_total_cost(action),
            )
        
        # Can't afford upgrade
        if not UpgradeDecisionService.can_afford_upgrade(action, coins):
            return UpgradeDecision(
                action=action,
                upgrade=False,
                upgrade_type=None,
                total_cost=UpgradeDecisionService.get_total_cost(action),
            )
        
        # Get modulators
        modulators = (agent_profile or {}).get("agent_modulators", {})
        aggression = modulators.get(AgentModulator.AGGRESSION, 0.5)
        risk_tolerance = modulators.get(AgentModulator.RISK_TOLERANCE, 0.5)
        
        config = get_action_config(action)
        upgrade_type = config.upgrade_type
        total_cost = config.total_upgraded_cost
        
        # Decision logic per action type
        should_upgrade = False
        
        if action == CoupAction.ASSASSINATE:
            should_upgrade = UpgradeDecisionService._should_upgrade_assassinate(
                coins=coins,
                hand=hand,
                target=target,
                aggression=aggression,
                risk_tolerance=risk_tolerance,
                players_alive=players_alive,
            )
        
        elif action == CoupAction.STEAL:
            should_upgrade = UpgradeDecisionService._should_upgrade_steal(
                coins=coins,
                aggression=aggression,
                risk_tolerance=risk_tolerance,
                target=target,
                visible_pending_actions=visible_pending_actions,
            )
        
        elif action == CoupAction.EXCHANGE:
            should_upgrade = UpgradeDecisionService._should_upgrade_exchange(
                coins=coins,
                hand=hand,
                target=target,
                aggression=aggression,
                risk_tolerance=risk_tolerance,
                players_alive=players_alive,
            )
        
        return UpgradeDecision(
            action=action,
            upgrade=should_upgrade,
            upgrade_type=upgrade_type if should_upgrade else None,
            total_cost=total_cost if should_upgrade else UpgradeDecisionService.get_total_cost(action),
        )
    
    # =============================================
    # Per-Action Upgrade Logic
    # =============================================
    
    @staticmethod
    def _should_upgrade_assassinate(
        coins: int,
        hand: List[InfluenceCard],
        target: Optional[str],
        aggression: float,
        risk_tolerance: float,
        players_alive: Optional[List[str]],
    ) -> bool:
        """
        Decide whether to upgrade Assassinate to assassination_priority.
        
        Upgrade effect: Target a SPECIFIC card type to eliminate.
        Cost: 3 + 2 = 5 coins total
        """
        if coins < 5:
            return False
        
        if aggression >= 0.7:
            return True
        
        if aggression >= 0.5 and coins >= 7:
            return True
        
        if risk_tolerance >= 0.6 and coins >= 6:
            return True
        
        if players_alive and len(players_alive) <= 3:
            if aggression >= 0.4:
                return True
        
        return False
    
    @staticmethod
    def _should_upgrade_steal(
        coins: int,
        aggression: float,
        risk_tolerance: float,
        target: Optional[str],
        visible_pending_actions: Optional[List[VisiblePendingAction]],
    ) -> bool:
        """
        Decide whether to upgrade Steal to kleptomania_steal.
        
        Upgrade effect: Enhanced stealing (steal more/steal despite blocks).
        Cost: 0 + 1 = 1 coin total
        """
        if coins < 1:
            return False
        
        if aggression >= 0.6:
            return True
        
        if coins <= 3 and aggression >= 0.3:
            return True
        
        if aggression >= 0.4 and coins >= 2:
            return True
        
        if risk_tolerance >= 0.5:
            return True
        
        return coins >= 2
    
    @staticmethod
    def _should_upgrade_exchange(
        coins: int,
        hand: List[InfluenceCard],
        target: Optional[str],
        aggression: float,
        risk_tolerance: float,
        players_alive: Optional[List[str]],
    ) -> bool:
        """
        Decide whether to upgrade Exchange to trigger_identity_crisis.
        
        Upgrade effect: Force TARGET player to also swap their cards.
        Cost: 0 + 4 = 4 coins total
        """
        if coins < 4:
            return False
        
        if not target:
            return False
        
        if aggression >= 0.7 and coins >= 6:
            return True
        
        if risk_tolerance >= 0.7 and coins >= 5:
            return True
        
        if players_alive and len(players_alive) <= 3:
            if aggression >= 0.5 and coins >= 5:
                return True
        
        return False


# =============================================
# Integration Helpers
# =============================================

def get_upgrade_recommendation(
    action: CoupAction,
    agent,  # BaseCoupAgent
    target: Optional[str] = None,
) -> UpgradeDecision:
    """
    Get upgrade recommendation for an agent's action.
    
    Convenience function that pulls agent state automatically.
    """
    return UpgradeDecisionService.should_upgrade(
        action=action,
        coins=agent.get_coins(),
        hand=agent.get_hand(),
        target=target,
        agent_profile=agent.profile,
        visible_pending_actions=agent.get_visible_pending_actions(),
        players_alive=agent.state.get("players_alive", []),
    )


def apply_upgrade_to_action(
    agent,  # BaseCoupAgent
    action: CoupAction,
    target: Optional[str] = None,
    force_upgrade: Optional[bool] = None,
) -> Tuple[bool, Optional[UpgradeDecision]]:
    """
    Apply upgrade logic and update agent's pending action.
    
    Args:
        agent: The BaseCoupAgent
        action: The action to take
        target: Target player
        force_upgrade: If True/False, override the recommendation.
    
    Returns:
        (success, upgrade_decision)
    """
    decision = get_upgrade_recommendation(action, agent, target)
    
    if force_upgrade is not None:
        config = get_action_config(action)
        if force_upgrade and config.can_upgrade:
            if config.can_afford_upgraded(agent.get_coins()):
                decision = UpgradeDecision(
                    action=action,
                    upgrade=True,
                    upgrade_type=config.upgrade_type,
                    total_cost=config.total_upgraded_cost,
                )
        else:
            decision = UpgradeDecision(
                action=action,
                upgrade=False,
                upgrade_type=None,
                total_cost=config.base_cost,
            )
    
    success = agent.update_pending_action(
        action=action,
        target=target,
        upgrade=decision.get("upgrade", False),
        upgrade_type=decision.get("upgrade_type"),
    )
    
    return success, decision

