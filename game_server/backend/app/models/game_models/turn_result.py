"""
Turn Result Model.

Dataclass representing the complete result of resolving a turn.
"""

from dataclasses import dataclass
from typing import List

from app.models.game_models.action_result import ActionResult


@dataclass
class TurnResult:
    """Complete result of resolving a turn."""
    session_id: str
    turn_number: int
    action_results: List[ActionResult]
    players_eliminated: List[str]
    summary: str

