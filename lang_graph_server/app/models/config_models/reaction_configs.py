"""
Reaction Configuration Models.

Immutable configuration for conditional reaction rules.
These define automatic reactions that trigger when matching actions occur.
"""

from dataclasses import dataclass
from typing import Dict, Optional

from app.constants import ConditionalRuleType, InfluenceCard, ReactionType


@dataclass(frozen=True)
class ConditionalRuleConfig:
    """Configuration for a conditional rule."""
    rule_type: ConditionalRuleType
    reaction_type: ReactionType
    description: str
    required_role_for_block: Optional[InfluenceCard] = None
    
    def __hash__(self):
        return hash(self.rule_type)


# Single source of truth for all conditional rule configurations
CONDITIONAL_RULE_CONFIGS: Dict[ConditionalRuleType, ConditionalRuleConfig] = {
    # Challenge rules
    ConditionalRuleType.CHALLENGE_ANY_DUKE: ConditionalRuleConfig(
        rule_type=ConditionalRuleType.CHALLENGE_ANY_DUKE,
        reaction_type=ReactionType.CHALLENGE,
        description="Challenge any action that claims Duke",
    ),
    ConditionalRuleType.CHALLENGE_ANY_ASSASSIN: ConditionalRuleConfig(
        rule_type=ConditionalRuleType.CHALLENGE_ANY_ASSASSIN,
        reaction_type=ReactionType.CHALLENGE,
        description="Challenge any action that claims Assassin",
    ),
    ConditionalRuleType.CHALLENGE_ANY_CAPTAIN: ConditionalRuleConfig(
        rule_type=ConditionalRuleType.CHALLENGE_ANY_CAPTAIN,
        reaction_type=ReactionType.CHALLENGE,
        description="Challenge any action that claims Captain",
    ),
    ConditionalRuleType.CHALLENGE_ANY_AMBASSADOR: ConditionalRuleConfig(
        rule_type=ConditionalRuleType.CHALLENGE_ANY_AMBASSADOR,
        reaction_type=ReactionType.CHALLENGE,
        description="Challenge any action that claims Ambassador",
    ),
    ConditionalRuleType.CHALLENGE_ANY_CONTESSA: ConditionalRuleConfig(
        rule_type=ConditionalRuleType.CHALLENGE_ANY_CONTESSA,
        reaction_type=ReactionType.CHALLENGE,
        description="Challenge any block that claims Contessa",
    ),
    
    # Block rules
    ConditionalRuleType.BLOCK_ANY_STEAL_ON_ME: ConditionalRuleConfig(
        rule_type=ConditionalRuleType.BLOCK_ANY_STEAL_ON_ME,
        reaction_type=ReactionType.BLOCK,
        description="Block any steal attempt targeting me",
        required_role_for_block=InfluenceCard.CAPTAIN,  # or Ambassador
    ),
    ConditionalRuleType.BLOCK_ANY_ASSASSINATION_ON_ME: ConditionalRuleConfig(
        rule_type=ConditionalRuleType.BLOCK_ANY_ASSASSINATION_ON_ME,
        reaction_type=ReactionType.BLOCK,
        description="Block any assassination attempt targeting me",
        required_role_for_block=InfluenceCard.CONTESSA,
    ),
    ConditionalRuleType.BLOCK_ANY_FOREIGN_AID: ConditionalRuleConfig(
        rule_type=ConditionalRuleType.BLOCK_ANY_FOREIGN_AID,
        reaction_type=ReactionType.BLOCK,
        description="Block any Foreign Aid attempt by any player",
        required_role_for_block=InfluenceCard.DUKE,
    ),
    
    # Defensive rules
    ConditionalRuleType.ALWAYS_BLOCK_ASSASSINATION: ConditionalRuleConfig(
        rule_type=ConditionalRuleType.ALWAYS_BLOCK_ASSASSINATION,
        reaction_type=ReactionType.BLOCK,
        description="Always block assassination (same as BLOCK_ANY_ASSASSINATION_ON_ME)",
        required_role_for_block=InfluenceCard.CONTESSA,
    ),
    ConditionalRuleType.ALWAYS_CHALLENGE_UPGRADED_ACTIONS: ConditionalRuleConfig(
        rule_type=ConditionalRuleType.ALWAYS_CHALLENGE_UPGRADED_ACTIONS,
        reaction_type=ReactionType.CHALLENGE,
        description="Challenge any upgraded action",
    ),
}


def get_rule_config(rule_type: ConditionalRuleType) -> Optional[ConditionalRuleConfig]:
    """Get the configuration for a conditional rule."""
    return CONDITIONAL_RULE_CONFIGS.get(rule_type)

