"""
Formatted Response Model.

Result of formatting a response for a specific social media platform.
"""

from dataclasses import dataclass
from typing import Dict, List

from app.constants import SocialMediaPlatform


@dataclass
class FormattedResponse:
    """A response formatted for a specific platform."""
    platform: SocialMediaPlatform
    content: str
    was_truncated: bool
    original_length: int
    mentions: List[str]
    metadata: Dict  # Platform-specific metadata

