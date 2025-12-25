"""
Blended Decision Model.

Result of blending heuristic and LLM decisions.
"""

from dataclasses import dataclass
from typing import Any, Optional

from app.constants import InfluenceCard


@dataclass
class BlendedDecision:
    """Result of blending heuristic and LLM decisions."""
    action: Any  # CoupAction or InfluenceCard depending on context
    target: Optional[str] = None
    claimed_role: Optional[InfluenceCard] = None
    reasoning: str = ""
    confidence: float = 0.5
    source: str = "heuristic"  # "heuristic", "llm", or "blended"

