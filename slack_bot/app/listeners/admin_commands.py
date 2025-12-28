"""
Admin Command Listeners.

Slack slash commands for admin operations.
"""

import os
import logging

import httpx
from slack_bolt import App

logger = logging.getLogger("slack_bot")

# Configuration
GAME_SERVER_URL = os.getenv("GAME_SERVER_URL", "http://localhost:5000")


def register(app: App) -> None:
    """
    Register admin command listeners with the Slack Bolt app.
    
    Args:
        app: Slack Bolt App instance
    """
    
    @app.command("/game_session-list")
    def handle_game_session_list(ack, respond, command, client):
        """
        List all game sessions.
        
        /game_session-list
        """
        ack()
        
        user_id = command.get("user_id", "")
        
        # Get user token
        from app.services import TokenCacheService
        token, error = TokenCacheService.get_token(user_id)
        
        if error == "not_linked":
            login_url = TokenCacheService.get_oauth_login_url()
            respond(
                f":warning: Your Slack account is not linked.\n"
                f"Please visit <{login_url}|this link> to connect your account."
            )
            return
        
        if error:
            respond(f":x: Authentication error: {error}")
            return
        
        # Fetch sessions from game server
        url = f"{GAME_SERVER_URL}/game/sessions"
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            response = httpx.get(url, headers=headers, timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                sessions = data.get("sessions", [])
                
                if not sessions:
                    respond(":clipboard: No active game sessions.")
                    return
                
                # Format response
                blocks = [
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": "📋 Game Sessions", "emoji": True}
                    },
                    {"type": "divider"}
                ]
                
                for session in sessions:
                    status_emoji = ":green_circle:" if session.get("status") == "active" else ":white_circle:"
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"{status_emoji} *{session.get('name', 'Unnamed')}*\n"
                                f"ID: `{session.get('id', 'N/A')}`\n"
                                f"Players: {session.get('player_count', 0)}"
                            )
                        }
                    })
                
                respond(blocks=blocks)
            
            elif response.status_code == 401:
                # Token expired, invalidate cache
                TokenCacheService.invalidate(user_id)
                respond(":x: Session expired. Please try again.")
            
            else:
                respond(f":x: Failed to fetch sessions: {response.status_code}")
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to connect to game server: {e}")
            respond(":x: Failed to connect to game server.")
    
    @app.command("/game_session-create")
    def handle_game_session_create(ack, respond, command, client):
        """
        Create a new game session.
        
        /game_session-create [name]
        """
        ack()
        
        user_id = command.get("user_id", "")
        session_name = command.get("text", "").strip() or "New Game Session"
        
        # Get user token
        from app.services import TokenCacheService
        token, error = TokenCacheService.get_token(user_id)
        
        if error == "not_linked":
            login_url = TokenCacheService.get_oauth_login_url()
            respond(
                f":warning: Your Slack account is not linked.\n"
                f"Please visit <{login_url}|this link> to connect your account."
            )
            return
        
        if error:
            respond(f":x: Authentication error: {error}")
            return
        
        # Create session on game server
        url = f"{GAME_SERVER_URL}/admin/sessions"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"name": session_name}
        
        try:
            response = httpx.post(url, headers=headers, json=payload, timeout=10.0)
            
            if response.status_code in (200, 201):
                data = response.json()
                session_id = data.get("session", {}).get("id", "N/A")
                respond(
                    f":white_check_mark: Game session created!\n"
                    f"*Name:* {session_name}\n"
                    f"*ID:* `{session_id}`"
                )
            
            elif response.status_code == 403:
                respond(":x: You don't have permission to create game sessions.")
            
            elif response.status_code == 401:
                TokenCacheService.invalidate(user_id)
                respond(":x: Session expired. Please try again.")
            
            else:
                respond(f":x: Failed to create session: {response.status_code}")
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to connect to game server: {e}")
            respond(":x: Failed to connect to game server.")
    
    @app.command("/game_session-register-channel")
    def handle_register_channel(ack, respond, command, client):
        """
        Register the current channel for a game session.
        
        /game_session-register-channel [session_id]
        """
        ack()
        
        user_id = command.get("user_id", "")
        channel_id = command.get("channel_id", "")
        session_id = command.get("text", "").strip()
        
        if not session_id:
            respond(":warning: Please provide a session ID: `/game_session-register-channel <session_id>`")
            return
        
        # Get user token
        from app.services import TokenCacheService
        token, error = TokenCacheService.get_token(user_id)
        
        if error == "not_linked":
            login_url = TokenCacheService.get_oauth_login_url()
            respond(
                f":warning: Your Slack account is not linked.\n"
                f"Please visit <{login_url}|this link> to connect your account."
            )
            return
        
        if error:
            respond(f":x: Authentication error: {error}")
            return
        
        # Register channel on game server
        url = f"{GAME_SERVER_URL}/game/sessions/{session_id}/channels"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "platform": "slack",
            "channel_id": channel_id
        }
        
        try:
            response = httpx.post(url, headers=headers, json=payload, timeout=10.0)
            
            if response.status_code in (200, 201):
                respond(
                    f":white_check_mark: Channel registered!\n"
                    f"This channel is now linked to session `{session_id}`"
                )
            
            elif response.status_code == 404:
                respond(f":x: Session `{session_id}` not found.")
            
            elif response.status_code == 403:
                respond(":x: You don't have permission to register channels.")
            
            elif response.status_code == 401:
                TokenCacheService.invalidate(user_id)
                respond(":x: Session expired. Please try again.")
            
            else:
                respond(f":x: Failed to register channel: {response.status_code}")
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to connect to game server: {e}")
            respond(":x: Failed to connect to game server.")
    
    logger.info("Registered admin_commands listeners")
