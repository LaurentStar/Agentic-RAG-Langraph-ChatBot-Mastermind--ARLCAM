"""
Pydantic structured output models for Coup agent decisions.

These models are used for LLM responses and can be validated against legal game moves.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.constants import CoupAction, InfluenceCard


class ActionDecisionSO(BaseModel):
    """
    Structured output for SELECT_ACTION decisions (agent's turn).

    The agent picks an action and optionally a target.
    """

    action: CoupAction = Field(
        description="The action to take on your turn (income, foreign_aid, coup, tax, assassinate, steal, exchange)"
    )
    target: Optional[str] = Field(
        default=None,
        description="Target player for actions that require one (coup, assassinate, steal). None for untargeted actions."
    )
    claimed_role: Optional[InfluenceCard] = Field(
        default=None,
        description="The role being claimed for this action (e.g., Duke for tax, Captain for steal). None for actions that don't claim a role."
    )
    reasoning: str = Field(
        description="Brief explanation of why this action was chosen, considering game state and strategy."
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence in this decision (0=uncertain, 1=certain). Used for blending with heuristics."
    )


class ReactionDecisionSO(BaseModel):
    """
    Structured output for REACT decisions (challenge, block, or pass).

    Used when responding to another player's action or block claim.
    """

    reaction: CoupAction = Field(
        description="The reaction to take: challenge, block_steal, block_foreign_aid, block_assassinate, or pass"
    )
    claimed_role: Optional[InfluenceCard] = Field(
        default=None,
        description="The role being claimed when blocking (e.g., Duke for blocking foreign aid, Contessa for blocking assassination). None when challenging or passing."
    )
    reasoning: str = Field(
        description="Brief explanation of why this reaction was chosen, considering bluff detection and risk."
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence in this decision (0=uncertain, 1=certain)."
    )


class RevealDecisionSO(BaseModel):
    """
    Structured output for RESOLVE.REVEAL_CARD decisions.

    Used when the agent must lose an influence card (failed challenge, assassination, coup).
    """

    card_to_reveal: InfluenceCard = Field(
        description="Which card from your hand to reveal (lose). Choose the card you value least."
    )
    reasoning: str = Field(
        description="Brief explanation of why this card was chosen to reveal."
    )


class ExchangeDecisionSO(BaseModel):
    """
    Structured output for RESOLVE.EXCHANGE_CARDS decisions (Ambassador ability).

    After drawing 2 cards from the deck, the agent picks which cards to keep.
    """

    cards_to_keep: List[InfluenceCard] = Field(
        description="Which cards to keep from the pool (your hand + 2 drawn). Keep 1 if you have 1 influence, 2 if you have 2.",
        min_length=1,
        max_length=2
    )
    reasoning: str = Field(
        description="Brief explanation of why these cards were chosen."
    )

