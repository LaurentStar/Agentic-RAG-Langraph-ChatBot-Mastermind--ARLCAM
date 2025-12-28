"""
Broadcast Service.

Posts broadcast messages to Slack channels.
"""

import logging
import os
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class BroadcastService:
    """
    Service for posting chat broadcasts to Slack channels.
    
    Receives message batches from game_server and formats them
    as Slack Block Kit messages.
    """
    
    @staticmethod
    def format_broadcast_blocks(
        messages: List[Dict[str, Any]],
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Format messages as Slack Block Kit blocks.
        
        Args:
            messages: List of message dicts with sender, platform, content
            session_id: Game session ID (for header)
        
        Returns:
            List of Slack blocks
        """
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "📢 Game Chat Update", "emoji": True}
            },
            {"type": "divider"}
        ]
        
        for msg in messages:
            # Platform indicator
            platform = msg.get('platform', 'unknown')
            if platform == 'discord':
                icon = ":video_game:"
            elif platform == 'slack':
                icon = ":slack:"
            else:
                icon = ":speech_balloon:"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{icon} *{msg.get('sender', 'Unknown')}*: {msg.get('content', '')}"
                }
            })
        
        return blocks
    
    @staticmethod
    def post_broadcast(
        slack_client,
        channel_id: str,
        messages: List[Dict[str, Any]],
        session_id: Optional[str] = None
    ) -> bool:
        """
        Post a broadcast to a Slack channel.
        
        Args:
            slack_client: Slack Web API client
            channel_id: Target channel ID
            messages: List of message dicts
            session_id: Game session ID
        
        Returns:
            True if successful
        """
        if not messages:
            logger.debug(f"No messages to broadcast for session {session_id}")
            return True
        
        blocks = BroadcastService.format_broadcast_blocks(messages, session_id)
        
        try:
            result = slack_client.chat_postMessage(
                channel=channel_id,
                blocks=blocks,
                text=f"Game Chat Update: {len(messages)} new messages"  # Fallback text
            )
            
            if result.get("ok"):
                logger.info(f"Posted broadcast with {len(messages)} messages to {channel_id}")
                return True
            else:
                logger.error(f"Slack API error: {result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to post broadcast: {e}")
            return False
    
    @staticmethod
    def post_single_message(
        slack_client,
        channel_id: str,
        sender: str,
        content: str,
        platform: str = "unknown"
    ) -> bool:
        """
        Post a single message to a Slack channel.
        
        Used for immediate routing of LLM agent responses.
        
        Args:
            slack_client: Slack Web API client
            channel_id: Target channel ID
            sender: Sender display name
            content: Message content
            platform: Source platform
        
        Returns:
            True if successful
        """
        # Platform indicator
        if platform == 'discord':
            icon = ":video_game:"
        elif platform == 'slack':
            icon = ":slack:"
        elif platform == 'llm':
            icon = ":robot_face:"
        else:
            icon = ":speech_balloon:"
        
        try:
            result = slack_client.chat_postMessage(
                channel=channel_id,
                text=f"{icon} *{sender}*: {content}",
                mrkdwn=True
            )
            
            if result.get("ok"):
                logger.debug(f"Posted message from {sender} to {channel_id}")
                return True
            else:
                logger.error(f"Slack API error: {result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to post message: {e}")
            return False
