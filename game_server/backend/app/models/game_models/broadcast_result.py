"""
Broadcast Result Model.

Dataclass representing the result of a broadcast attempt.
"""

from dataclasses import dataclass
from typing import Optional

from app.constants import SocialMediaPlatform


@dataclass
class BroadcastResult:
    """Result of a broadcast attempt."""
    destination_id: int
    platform: SocialMediaPlatform
    channel_name: str
    success: bool
    error: Optional[str] = None

