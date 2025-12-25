"""
Configuration Models.

Frozen dataclasses that define immutable configuration for game mechanics.
These are the single source of truth for action costs, platform limits, etc.
"""

from app.models.config_models.action_configs import (
    ActionConfig,
    ACTION_CONFIGS,
    get_action_config,
)
from app.models.config_models.platform_configs import (
    PlatformConfig,
    PLATFORM_CONFIGS,
    get_platform_config,
)
from app.models.config_models.reaction_configs import (
    ConditionalRuleConfig,
    CONDITIONAL_RULE_CONFIGS,
    get_rule_config,
)

__all__ = [
    # Action configs
    "ActionConfig",
    "ACTION_CONFIGS",
    "get_action_config",
    # Platform configs
    "PlatformConfig",
    "PLATFORM_CONFIGS",
    "get_platform_config",
    # Reaction configs
    "ConditionalRuleConfig",
    "CONDITIONAL_RULE_CONFIGS",
    "get_rule_config",
]

