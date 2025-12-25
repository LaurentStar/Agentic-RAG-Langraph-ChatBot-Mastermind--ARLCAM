"""
Conditional Reaction Service.

Evaluates conditional reaction rules that agents can set during Phase 2.
These rules automatically trigger when matching actions occur.

Conditional rules allow agents to set reactions like:
- "Challenge any Duke claim"
- "Block any steal targeting me"
- "Always block assassination attempts on me"

This is useful when agents want to react to multiple potential
actions without specifying each one individually.
"""

from typing import Callable, Dict, List, Optional, Any

from app.constants import ConditionalRuleType, CoupAction, InfluenceCard, ReactionType
from app.models.config_models.reaction_configs import (
    ConditionalRuleConfig,
    CONDITIONAL_RULE_CONFIGS,
    get_rule_config,
)
from app.models.graph_state_models.game_phase_state import (
    ActionRequiringReaction,
    PendingReaction,
)


class ConditionalReactionService:
    """
    Evaluates conditional reaction rules.
    
    Used during Phase 2 lockout when the game server processes
    pending reactions. Conditional rules are expanded into
    specific reactions based on the actions that occurred.
    """
    
    # Map of rule types to their evaluation functions
    _EVALUATORS: Dict[ConditionalRuleType, Callable] = {}
    
    @classmethod
    def _register_evaluators(cls):
        """Register all rule evaluators."""
        cls._EVALUATORS = {
            ConditionalRuleType.CHALLENGE_ANY_DUKE: cls._eval_challenge_role(InfluenceCard.DUKE),
            ConditionalRuleType.CHALLENGE_ANY_ASSASSIN: cls._eval_challenge_role(InfluenceCard.ASSASSIN),
            ConditionalRuleType.CHALLENGE_ANY_CAPTAIN: cls._eval_challenge_role(InfluenceCard.CAPTAIN),
            ConditionalRuleType.CHALLENGE_ANY_AMBASSADOR: cls._eval_challenge_role(InfluenceCard.AMBASSADOR),
            ConditionalRuleType.CHALLENGE_ANY_CONTESSA: cls._eval_challenge_role(InfluenceCard.CONTESSA),
            ConditionalRuleType.BLOCK_ANY_STEAL_ON_ME: cls._eval_block_action_on_me(CoupAction.STEAL),
            ConditionalRuleType.BLOCK_ANY_ASSASSINATION_ON_ME: cls._eval_block_action_on_me(CoupAction.ASSASSINATE),
            ConditionalRuleType.ALWAYS_BLOCK_ASSASSINATION: cls._eval_block_action_on_me(CoupAction.ASSASSINATE),
            ConditionalRuleType.BLOCK_ANY_FOREIGN_AID: cls._eval_block_foreign_aid(),
            ConditionalRuleType.ALWAYS_CHALLENGE_UPGRADED_ACTIONS: cls._eval_challenge_upgraded(),
        }
    
    @staticmethod
    def _eval_challenge_role(role: InfluenceCard) -> Callable:
        """Create evaluator for challenging a specific role claim."""
        def evaluator(action: ActionRequiringReaction, agent_id: str) -> bool:
            claimed_role = action.get("claimed_role")
            if claimed_role and claimed_role == role.value:
                return True
            return False
        return evaluator
    
    @staticmethod
    def _eval_block_action_on_me(action_type: CoupAction) -> Callable:
        """Create evaluator for blocking an action targeting the agent."""
        def evaluator(action: ActionRequiringReaction, agent_id: str) -> bool:
            return (
                action.get("action") == action_type.value
                and action.get("target_id") == agent_id
            )
        return evaluator
    
    @staticmethod
    def _eval_block_foreign_aid() -> Callable:
        """Create evaluator for blocking any foreign aid."""
        def evaluator(action: ActionRequiringReaction, agent_id: str) -> bool:
            return action.get("action") == CoupAction.FOREIGN_AID.value
        return evaluator
    
    @staticmethod
    def _eval_challenge_upgraded() -> Callable:
        """Create evaluator for challenging upgraded actions."""
        def evaluator(action: ActionRequiringReaction, agent_id: str) -> bool:
            return action.get("is_upgraded", False)
        return evaluator
    
    def __init__(self):
        """Initialize the service and register evaluators."""
        if not self._EVALUATORS:
            self._register_evaluators()
    
    def evaluate_conditional(
        self,
        rule: str,
        action: ActionRequiringReaction,
        agent_id: str
    ) -> bool:
        """
        Check if a conditional rule triggers for an action.
        
        Args:
            rule: The conditional rule string (e.g., "challenge_any_duke")
            action: The action to evaluate against
            agent_id: The agent evaluating the rule
        
        Returns:
            True if the rule triggers for this action
        """
        try:
            rule_type = ConditionalRuleType(rule)
        except ValueError:
            return False
        
        evaluator = self._EVALUATORS.get(rule_type)
        if not evaluator:
            return False
        
        return evaluator(action, agent_id)
    
    def expand_conditional_reactions(
        self,
        pending_reactions: List[PendingReaction],
        actions: List[ActionRequiringReaction],
        agent_id: str
    ) -> List[PendingReaction]:
        """
        Expand conditional reactions into specific reactions.
        
        Takes a list of pending reactions (some conditional, some specific)
        and expands any conditional ones into specific reactions based
        on the actions that match.
        """
        expanded_reactions = []
        
        for reaction in pending_reactions:
            conditional_rule = reaction.get("conditional_rule")
            
            if conditional_rule:
                matching_actions = [
                    action for action in actions
                    if self.evaluate_conditional(conditional_rule, action, agent_id)
                ]
                
                for action in matching_actions:
                    specific_reaction = PendingReaction(
                        reaction_id=f"{reaction.get('reaction_id')}_{action.get('action_id')}",
                        reaction_type=reaction.get("reaction_type"),
                        target_action_id=action.get("action_id"),
                        target_player_id=action.get("actor_id"),
                        conditional_rule=None,
                        claimed_role=reaction.get("claimed_role"),
                        priority=reaction.get("priority", 99),
                        reasoning=f"Expanded from conditional rule: {conditional_rule}",
                    )
                    expanded_reactions.append(specific_reaction)
            else:
                expanded_reactions.append(reaction)
        
        return expanded_reactions
    
    def get_config(self, rule: str) -> Optional[ConditionalRuleConfig]:
        """Get the configuration for a conditional rule."""
        try:
            rule_type = ConditionalRuleType(rule)
            return get_rule_config(rule_type)
        except ValueError:
            return None
    
    def get_available_rules(self) -> List[Dict[str, Any]]:
        """Get a list of all available conditional rules."""
        return [
            {
                "rule": config.rule_type.value,
                "reaction_type": config.reaction_type.value,
                "description": config.description,
                "required_role": config.required_role_for_block.value if config.required_role_for_block else None,
            }
            for config in CONDITIONAL_RULE_CONFIGS.values()
        ]
    
    def validate_rule(self, rule: str) -> bool:
        """Check if a rule string is valid."""
        try:
            ConditionalRuleType(rule)
            return True
        except ValueError:
            return False

