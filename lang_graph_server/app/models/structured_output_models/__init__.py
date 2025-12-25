"""
Structured Output Models.

Pydantic models for LLM structured outputs.
These models enforce valid game moves and provide type-safe responses.
"""

from app.models.structured_output_models.coup_decision_so import (
    ActionDecisionSO,
    ReactionDecisionSO,
    RevealDecisionSO,
    ExchangeDecisionSO,
)

__all__ = [
    "ActionDecisionSO",
    "ReactionDecisionSO",
    "RevealDecisionSO",
    "ExchangeDecisionSO",
]

