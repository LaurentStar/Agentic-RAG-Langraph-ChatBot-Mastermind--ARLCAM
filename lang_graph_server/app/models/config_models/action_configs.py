"""
Action Configuration Models.

Immutable configuration for Coup actions including base costs and upgrade options.
This is the single source of truth for action costs.
"""

from dataclasses import dataclass
from typing import Dict, Optional

from app.constants import CoupAction, UpgradeType


@dataclass(frozen=True)
class ActionConfig:
    """Immutable configuration for a Coup action."""
    action: CoupAction
    base_cost: int
    can_upgrade: bool
    upgrade_type: Optional[UpgradeType] = None
    upgrade_cost: int = 0
    
    @property
    def total_upgraded_cost(self) -> int:
        """Total cost when upgraded (base + upgrade)."""
        return self.base_cost + self.upgrade_cost
    
    def can_afford(self, coins: int) -> bool:
        """Check if agent can afford the base action."""
        return coins >= self.base_cost
    
    def can_afford_upgraded(self, coins: int) -> bool:
        """Check if agent can afford the upgraded action."""
        return self.can_upgrade and coins >= self.total_upgraded_cost


# Single source of truth for all action configurations
ACTION_CONFIGS: Dict[CoupAction, ActionConfig] = {
    CoupAction.ASSASSINATE: ActionConfig(
        action=CoupAction.ASSASSINATE,
        base_cost=3,
        can_upgrade=True,
        upgrade_type=UpgradeType.ASSASSINATION_PRIORITY,
        upgrade_cost=2,  # Total: 5 coins
    ),
    CoupAction.STEAL: ActionConfig(
        action=CoupAction.STEAL,
        base_cost=0,
        can_upgrade=True,
        upgrade_type=UpgradeType.KLEPTOMANIA_STEAL,
        upgrade_cost=1,  # Total: 1 coin
    ),
    CoupAction.EXCHANGE: ActionConfig(
        action=CoupAction.EXCHANGE,
        base_cost=0,
        can_upgrade=True,
        upgrade_type=UpgradeType.TRIGGER_IDENTITY_CRISIS,
        upgrade_cost=4,  # Total: 4 coins
    ),
    CoupAction.COUP: ActionConfig(
        action=CoupAction.COUP,
        base_cost=7,
        can_upgrade=False,
    ),
    CoupAction.INCOME: ActionConfig(
        action=CoupAction.INCOME,
        base_cost=0,
        can_upgrade=False,
    ),
    CoupAction.FOREIGN_AID: ActionConfig(
        action=CoupAction.FOREIGN_AID,
        base_cost=0,
        can_upgrade=False,
    ),
    CoupAction.TAX: ActionConfig(
        action=CoupAction.TAX,
        base_cost=0,
        can_upgrade=False,
    ),
}


def get_action_config(action: CoupAction) -> ActionConfig:
    """
    Get configuration for an action.
    
    Returns a default non-upgradeable config if action not found.
    """
    return ACTION_CONFIGS.get(
        action,
        ActionConfig(action=action, base_cost=0, can_upgrade=False)
    )

