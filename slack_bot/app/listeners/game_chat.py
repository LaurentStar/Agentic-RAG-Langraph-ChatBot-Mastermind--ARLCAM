"""
Game Chat Listener.

Forwards messages from game channels to the game server.
"""

import os
import logging
from typing import Optional

import httpx
from slack_bolt import App

logger = logging.getLogger("slack_bot")

# Configuration
GAME_SERVER_URL = os.getenv("GAME_SERVER_URL", "http://localhost:5000")
SLACK_GAME_CHANNEL = os.getenv("SLACK_GAME_CHANNEL", "")
GAME_SESSION_ID = os.getenv("GAME_SESSION_ID", "")


# User display name cache
_user_cache: dict = {}


def get_display_name(client, user_id: str) -> str:
    """Get a user's display name, with caching."""
    if user_id in _user_cache:
        return _user_cache[user_id]
    
    try:
        result = client.users_info(user=user_id)
        if result.get("ok"):
            user = result.get("user", {})
            # Prefer display_name, fall back to real_name, then user name
            display_name = (
                user.get("profile", {}).get("display_name") or
                user.get("real_name") or
                user.get("name") or
                user_id
            )
            _user_cache[user_id] = display_name
            return display_name
    except Exception as e:
        logger.warning(f"Failed to get user info for {user_id}: {e}")
    
    return user_id


def send_to_game_server(
    sender: str,
    content: str,
    channel_id: str,
    team_id: str,
    session_id: Optional[str] = None
) -> bool:
    """
    Send a message to the game server.
    
    Args:
        sender: Sender display name
        content: Message content
        channel_id: Slack channel ID
        team_id: Slack team/workspace ID
        session_id: Game session ID (optional)
    
    Returns:
        True if successful
    """
    url = f"{GAME_SERVER_URL}/game/chat/incoming"
    
    payload = {
        "session_id": session_id or GAME_SESSION_ID,
        "sender": sender,
        "content": content,
        "platform": "slack",
        "platform_channel_id": channel_id,
        "platform_metadata": {
            "team_id": team_id,
            "channel_id": channel_id
        }
    }
    
    try:
        response = httpx.post(url, json=payload, timeout=10.0)
        
        if response.status_code in (200, 201):
            logger.debug(f"Message sent to game server: {sender}")
            return True
        else:
            logger.warning(f"Game server returned {response.status_code}: {response.text}")
            return False
            
    except httpx.HTTPError as e:
        logger.error(f"Failed to send message to game server: {e}")
        return False


def register(app: App) -> None:
    """
    Register game chat listeners with the Slack Bolt app.
    
    Args:
        app: Slack Bolt App instance
    """
    
    @app.message("")
    def handle_message(client, message, say, logger):
        """
        Handle incoming messages and forward to game server.
        
        Only forwards messages from the configured game channel.
        """
        # Ignore bot messages
        if message.get("subtype") == "bot_message":
            return
        if message.get("bot_id"):
            return
        
        channel_id = message.get("channel", "")
        team_id = message.get("team", "")
        user_id = message.get("user", "")
        text = message.get("text", "")
        
        # Only process messages from game channel
        if SLACK_GAME_CHANNEL and channel_id != SLACK_GAME_CHANNEL:
            return
        
        # Skip empty messages
        if not text.strip():
            return
        
        # Get user display name
        display_name = get_display_name(client, user_id)
        
        # Send to game server
        success = send_to_game_server(
            sender=display_name,
            content=text,
            channel_id=channel_id,
            team_id=team_id
        )
        
        if not success:
            logger.warning(f"Failed to forward message from {display_name}")
    
    logger.info("Registered game_chat listener")
