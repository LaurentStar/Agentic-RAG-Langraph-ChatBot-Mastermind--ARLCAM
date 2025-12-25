"""
Platform Response Router Service.

Routes agent responses to the appropriate social media platform with
platform-specific formatting and constraints.

Supported Platforms:
    - Discord: Rich embeds, markdown, @mentions
    - Slack: Slack-flavored markdown, @mentions
    - Twitter: 280 char limit, hashtags
    - Bluesky: 300 char limit
    - Email: Full HTML support
    - Default: Plain text
"""

import re
from typing import Dict, List, Optional

from app.constants import SocialMediaPlatform
from app.models.config_models.platform_configs import (
    PlatformConfig,
    PLATFORM_CONFIGS,
    get_platform_config,
)
from app.models.rest_api_models.formatted_response import FormattedResponse


class PlatformResponseRouter:
    """
    Routes and formats responses for different platforms.
    
    Usage:
        router = PlatformResponseRouter()
        formatted = router.format_response(
            content="Hello @player1!",
            platform=SocialMediaPlatform.TWITTER,
            mentions=["player1"],
        )
    """
    
    def format_response(
        self,
        content: str,
        platform: SocialMediaPlatform,
        mentions: Optional[List[str]] = None,
        thread_id: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> FormattedResponse:
        """
        Format a response for a specific platform.
        
        Args:
            content: The raw response content
            platform: Target platform
            mentions: List of user IDs to mention
            thread_id: Optional thread to reply in
            reply_to: Optional message ID to reply to
            
        Returns:
            FormattedResponse with platform-appropriate formatting
        """
        config = get_platform_config(platform)
        original_length = len(content)
        
        # Format mentions
        formatted_content = content
        formatted_mentions = []
        if mentions and config.supports_mentions:
            formatted_content, formatted_mentions = self._format_mentions(
                content, mentions, config
            )
        
        # Handle markdown stripping for non-markdown platforms
        if not config.supports_markdown:
            formatted_content = self._strip_markdown(formatted_content)
        
        # Handle newlines for email/HTML
        if config.newline_style != "\n":
            formatted_content = formatted_content.replace("\n", config.newline_style)
        
        # Truncate if needed
        was_truncated = False
        if config.max_chars and len(formatted_content) > config.max_chars:
            formatted_content = self._truncate(formatted_content, config)
            was_truncated = True
        
        # Build metadata
        metadata = self._build_metadata(
            platform=platform,
            thread_id=thread_id,
            reply_to=reply_to,
            config=config,
        )
        
        return FormattedResponse(
            platform=platform,
            content=formatted_content,
            was_truncated=was_truncated,
            original_length=original_length,
            mentions=formatted_mentions,
            metadata=metadata,
        )
    
    def _format_mentions(
        self,
        content: str,
        mentions: List[str],
        config: PlatformConfig,
    ) -> tuple[str, List[str]]:
        """Format @mentions for the target platform."""
        formatted_mentions = []
        
        for mention in mentions:
            plain_mention = f"@{mention}"
            platform_mention = f"{config.mention_prefix}{mention}{config.mention_suffix}"
            
            if plain_mention in content:
                content = content.replace(plain_mention, platform_mention)
                formatted_mentions.append(mention)
        
        return content, formatted_mentions
    
    def _strip_markdown(self, content: str) -> str:
        """Remove markdown formatting for platforms that don't support it."""
        # Remove bold/italic
        content = re.sub(r'\*\*(.+?)\*\*', r'\1', content)
        content = re.sub(r'\*(.+?)\*', r'\1', content)
        content = re.sub(r'__(.+?)__', r'\1', content)
        content = re.sub(r'_(.+?)_', r'\1', content)
        
        # Remove code blocks
        content = re.sub(r'```[\s\S]*?```', '', content)
        content = re.sub(r'`(.+?)`', r'\1', content)
        
        # Remove headers
        content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
        
        # Remove links but keep text
        content = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', content)
        
        return content
    
    def _truncate(self, content: str, config: PlatformConfig) -> str:
        """Truncate content to fit platform limits."""
        max_length = config.max_chars - len(config.truncation_suffix)
        
        if len(content) <= config.max_chars:
            return content
        
        truncated = content[:max_length]
        last_space = truncated.rfind(' ')
        
        if last_space > max_length * 0.8:
            truncated = truncated[:last_space]
        
        return truncated + config.truncation_suffix
    
    def _build_metadata(
        self,
        platform: SocialMediaPlatform,
        thread_id: Optional[str],
        reply_to: Optional[str],
        config: PlatformConfig,
    ) -> Dict:
        """Build platform-specific metadata."""
        metadata = {
            "platform": platform.value,
            "supports_embeds": config.supports_embeds,
            "supports_threads": config.supports_threads,
        }
        
        if thread_id and config.supports_threads:
            metadata["thread_id"] = thread_id
        
        if reply_to:
            metadata["reply_to"] = reply_to
        
        return metadata
    
    def route_response(
        self,
        content: str,
        source_platform: SocialMediaPlatform,
        target_platform: Optional[SocialMediaPlatform] = None,
        mentions: Optional[List[str]] = None,
        thread_id: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> FormattedResponse:
        """Route a response, defaulting to source platform if no target specified."""
        platform = target_platform or source_platform
        return self.format_response(
            content=content,
            platform=platform,
            mentions=mentions,
            thread_id=thread_id,
            reply_to=reply_to,
        )
    
    def format_for_all_platforms(
        self,
        content: str,
        mentions: Optional[List[str]] = None,
    ) -> Dict[SocialMediaPlatform, FormattedResponse]:
        """Format a response for all platforms."""
        results = {}
        for platform in PLATFORM_CONFIGS.keys():
            results[platform] = self.format_response(
                content=content,
                platform=platform,
                mentions=mentions,
            )
        return results


# =============================================
# Convenience Functions
# =============================================

def format_for_platform(
    content: str,
    platform: SocialMediaPlatform,
    mentions: Optional[List[str]] = None,
) -> str:
    """Quick formatting for a single platform. Returns just the formatted string."""
    router = PlatformResponseRouter()
    result = router.format_response(content, platform, mentions)
    return result.content


def get_char_limit(platform: SocialMediaPlatform) -> Optional[int]:
    """Get character limit for a platform."""
    return get_platform_config(platform).max_chars


def platform_supports_feature(platform: SocialMediaPlatform, feature: str) -> bool:
    """Check if a platform supports a specific feature."""
    config = get_platform_config(platform)
    return getattr(config, f"supports_{feature}", False)
