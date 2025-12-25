"""
Platform Configuration Models.

Immutable configuration for social media platforms including character limits,
markdown support, and mention formatting.
"""

from dataclasses import dataclass
from typing import Dict, Optional

from app.constants import SocialMediaPlatform


@dataclass(frozen=True)
class PlatformConfig:
    """Immutable configuration for a social media platform."""
    platform: SocialMediaPlatform
    max_chars: Optional[int]  # None = unlimited
    supports_markdown: bool
    supports_mentions: bool
    mention_prefix: str  # e.g., "@" for Discord, "<@" for Slack
    mention_suffix: str  # e.g., "" for Discord, ">" for Slack
    supports_embeds: bool
    supports_threads: bool
    newline_style: str  # "\n" or "<br>" for HTML
    truncation_suffix: str  # e.g., "..." or "…"


PLATFORM_CONFIGS: Dict[SocialMediaPlatform, PlatformConfig] = {
    SocialMediaPlatform.DISCORD: PlatformConfig(
        platform=SocialMediaPlatform.DISCORD,
        max_chars=2000,
        supports_markdown=True,
        supports_mentions=True,
        mention_prefix="<@",
        mention_suffix=">",
        supports_embeds=True,
        supports_threads=True,
        newline_style="\n",
        truncation_suffix="...",
    ),
    SocialMediaPlatform.SLACK: PlatformConfig(
        platform=SocialMediaPlatform.SLACK,
        max_chars=40000,  # Block kit limit
        supports_markdown=True,
        supports_mentions=True,
        mention_prefix="<@",
        mention_suffix=">",
        supports_embeds=True,
        supports_threads=True,
        newline_style="\n",
        truncation_suffix="...",
    ),
    SocialMediaPlatform.TWITTER: PlatformConfig(
        platform=SocialMediaPlatform.TWITTER,
        max_chars=280,
        supports_markdown=False,
        supports_mentions=True,
        mention_prefix="@",
        mention_suffix="",
        supports_embeds=False,
        supports_threads=True,
        newline_style="\n",
        truncation_suffix="…",
    ),
    SocialMediaPlatform.BLUESKY: PlatformConfig(
        platform=SocialMediaPlatform.BLUESKY,
        max_chars=300,
        supports_markdown=False,
        supports_mentions=True,
        mention_prefix="@",
        mention_suffix="",
        supports_embeds=True,
        supports_threads=True,
        newline_style="\n",
        truncation_suffix="…",
    ),
    SocialMediaPlatform.EMAIL: PlatformConfig(
        platform=SocialMediaPlatform.EMAIL,
        max_chars=None,  # No limit
        supports_markdown=False,  # Use HTML instead
        supports_mentions=False,
        mention_prefix="",
        mention_suffix="",
        supports_embeds=True,
        supports_threads=True,
        newline_style="<br>",
        truncation_suffix="...",
    ),
    SocialMediaPlatform.DEFUALT: PlatformConfig(
        platform=SocialMediaPlatform.DEFUALT,
        max_chars=None,
        supports_markdown=True,
        supports_mentions=True,
        mention_prefix="@",
        mention_suffix="",
        supports_embeds=False,
        supports_threads=False,
        newline_style="\n",
        truncation_suffix="...",
    ),
}


def get_platform_config(platform: SocialMediaPlatform) -> PlatformConfig:
    """Get configuration for a platform."""
    return PLATFORM_CONFIGS.get(
        platform,
        PLATFORM_CONFIGS[SocialMediaPlatform.DEFUALT]
    )

