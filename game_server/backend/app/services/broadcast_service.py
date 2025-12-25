"""
Broadcast Service.

Handles sending game results to configured broadcast destinations.
"""

from typing import List

import httpx

from app.constants import PLATFORM_CHAR_LIMITS, SocialMediaPlatform
from app.models.game_models import BroadcastResult, TurnResult
from app.models.postgres_sql_db_models import BroadcastDestination, GameSession


class BroadcastService:
    """Service for broadcasting game results to external platforms."""
    
    @staticmethod
    def broadcast_results(session_id: str, results: TurnResult) -> List[BroadcastResult]:
        """
        Send turn results to all configured broadcast destinations.
        
        Args:
            session_id: Session to broadcast for
            results: Turn results to broadcast
        
        Returns:
            List of broadcast results
        """
        session = GameSession.query.filter_by(session_id=session_id).first()
        if not session:
            return []
        
        destinations = BroadcastDestination.query.filter_by(session_id=session_id).all()
        broadcast_results = []
        
        for destination in destinations:
            # Format message for platform
            message = BroadcastService.format_results_message(
                results,
                destination.platform
            )
            
            # Send to platform
            result = BroadcastService._send_to_platform(destination, message)
            broadcast_results.append(result)
        
        return broadcast_results
    
    @staticmethod
    def format_results_message(results: TurnResult, platform: SocialMediaPlatform) -> str:
        """
        Format results into a human-readable message.
        
        Args:
            results: Turn results to format
            platform: Target platform (for character limits)
        
        Returns:
            Formatted message string
        """
        char_limit = PLATFORM_CHAR_LIMITS.get(platform, 2000)
        
        # Build message parts
        lines = [
            f"🎲 **Turn {results.turn_number} Results**",
            ""
        ]
        
        # Add action summaries
        for action_result in results.action_results:
            emoji = "✅" if action_result.outcome.value == "success" else "❌"
            lines.append(f"{emoji} {action_result.description}")
        
        # Add eliminations
        if results.players_eliminated:
            lines.append("")
            lines.append(f"☠️ Eliminated: {', '.join(results.players_eliminated)}")
        
        # Join and truncate if needed
        message = "\n".join(lines)
        
        if len(message) > char_limit:
            # Truncate with ellipsis
            message = message[:char_limit - 3] + "..."
        
        return message
    
    @staticmethod
    def _send_to_platform(
        destination: BroadcastDestination,
        message: str
    ) -> BroadcastResult:
        """Send a message to a specific platform."""
        
        try:
            if destination.platform == SocialMediaPlatform.DISCORD:
                return BroadcastService._send_to_discord(destination, message)
            elif destination.platform == SocialMediaPlatform.SLACK:
                return BroadcastService._send_to_slack(destination, message)
            elif destination.platform == SocialMediaPlatform.TWITTER:
                return BroadcastService._send_to_twitter(destination, message)
            elif destination.platform == SocialMediaPlatform.BLUESKY:
                return BroadcastService._send_to_bluesky(destination, message)
            elif destination.platform == SocialMediaPlatform.EMAIL:
                return BroadcastService._send_email(destination, message)
            else:
                return BroadcastResult(
                    destination_id=destination.id,
                    platform=destination.platform,
                    channel_name=destination.channel_name,
                    success=False,
                    error=f"Unsupported platform: {destination.platform}"
                )
        except Exception as e:
            return BroadcastResult(
                destination_id=destination.id,
                platform=destination.platform,
                channel_name=destination.channel_name,
                success=False,
                error=str(e)
            )
    
    @staticmethod
    def _send_to_discord(destination: BroadcastDestination, message: str) -> BroadcastResult:
        """Send message to Discord via webhook."""
        if not destination.webhook_url:
            return BroadcastResult(
                destination_id=destination.id,
                platform=destination.platform,
                channel_name=destination.channel_name,
                success=False,
                error="No webhook URL configured"
            )
        
        try:
            response = httpx.post(
                destination.webhook_url,
                json={"content": message},
                timeout=10.0
            )
            response.raise_for_status()
            
            return BroadcastResult(
                destination_id=destination.id,
                platform=destination.platform,
                channel_name=destination.channel_name,
                success=True
            )
        except httpx.HTTPError as e:
            return BroadcastResult(
                destination_id=destination.id,
                platform=destination.platform,
                channel_name=destination.channel_name,
                success=False,
                error=str(e)
            )
    
    @staticmethod
    def _send_to_slack(destination: BroadcastDestination, message: str) -> BroadcastResult:
        """Send message to Slack via webhook."""
        if not destination.webhook_url:
            return BroadcastResult(
                destination_id=destination.id,
                platform=destination.platform,
                channel_name=destination.channel_name,
                success=False,
                error="No webhook URL configured"
            )
        
        try:
            response = httpx.post(
                destination.webhook_url,
                json={"text": message},
                timeout=10.0
            )
            response.raise_for_status()
            
            return BroadcastResult(
                destination_id=destination.id,
                platform=destination.platform,
                channel_name=destination.channel_name,
                success=True
            )
        except httpx.HTTPError as e:
            return BroadcastResult(
                destination_id=destination.id,
                platform=destination.platform,
                channel_name=destination.channel_name,
                success=False,
                error=str(e)
            )
    
    @staticmethod
    def _send_to_twitter(destination: BroadcastDestination, message: str) -> BroadcastResult:
        """Send message to Twitter (requires API integration)."""
        # TODO: Implement Twitter API integration
        return BroadcastResult(
            destination_id=destination.id,
            platform=destination.platform,
            channel_name=destination.channel_name,
            success=False,
            error="Twitter API not implemented"
        )
    
    @staticmethod
    def _send_to_bluesky(destination: BroadcastDestination, message: str) -> BroadcastResult:
        """Send message to Bluesky (requires AT Protocol integration)."""
        # TODO: Implement Bluesky AT Protocol integration
        return BroadcastResult(
            destination_id=destination.id,
            platform=destination.platform,
            channel_name=destination.channel_name,
            success=False,
            error="Bluesky API not implemented"
        )
    
    @staticmethod
    def _send_email(destination: BroadcastDestination, message: str) -> BroadcastResult:
        """Send message via email (requires SMTP configuration)."""
        # TODO: Implement email sending
        return BroadcastResult(
            destination_id=destination.id,
            platform=destination.platform,
            channel_name=destination.channel_name,
            success=False,
            error="Email not implemented"
        )


# Singleton instance
broadcast_service = BroadcastService()
