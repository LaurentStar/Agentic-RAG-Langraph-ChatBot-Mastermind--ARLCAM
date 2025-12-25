"""
Action Result Model.

Dataclass representing the result of a single action resolution.
"""

from dataclasses import dataclass
from typing import List, Optional

from app.constants import ResolutionOutcome, ToBeInitiated


@dataclass
class ActionResult:
    """Result of a single action resolution."""
    actor: str
    action: ToBeInitiated
    target: Optional[str]
    outcome: ResolutionOutcome
    cards_revealed: List[str]
    coins_transferred: int
    description: str

