"""
Slack Bot Class.

Wraps Slack Bolt App with listener registration and lifecycle management.
"""

import os
import logging
from typing import Optional

from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request

logger = logging.getLogger("slack_bot")


class SlackBotApp:
    """
    Slack Bot Application wrapper.
    
    Wraps Slack Bolt App and handles:
    - Listener registration from modules
    - Flask route registration for events
    - Lifecycle management
    """
    
    def __init__(self):
        """Initialize the Slack Bot (lazy - actual app created on first use)."""
        self._app: Optional[App] = None
        self._handler: Optional[SlackRequestHandler] = None
        self._initialized = False
    
    @property
    def app(self) -> App:
        """Get or create the Slack Bolt app."""
        if self._app is None:
            self._app = self._create_app()
        return self._app
    
    @property
    def client(self):
        """Get the Slack Web API client."""
        return self.app.client
    
    def _create_app(self) -> App:
        """Create and configure the Slack Bolt app."""
        token = os.getenv("SLACK_BOT_TOKEN")
        signing_secret = os.getenv("SLACK_SIGNING_SECRET")
        
        if not token:
            logger.warning("SLACK_BOT_TOKEN not set - Slack features will not work")
        if not signing_secret:
            logger.warning("SLACK_SIGNING_SECRET not set - Slack events will not verify")
        
        app = App(
            token=token,
            signing_secret=signing_secret,
            token_verification_enabled=bool(token)
        )
        
        logger.info("Slack Bolt app created")
        return app
    
    def register_listeners(self) -> None:
        """Register all listeners from the listeners module."""
        if self._initialized:
            return
        
        # Import and register listeners
        from app.listeners import admin_commands, game_chat
        
        admin_commands.register(self.app)
        logger.info("Registered admin_commands listeners")
        
        game_chat.register(self.app)
        logger.info("Registered game_chat listeners")
        
        self._initialized = True
        logger.info("All Slack listeners registered")
    
    def register_flask_routes(self, flask_app: Flask) -> None:
        """
        Register Slack event routes with Flask app.
        
        Args:
            flask_app: Flask application instance
        """
        # Ensure listeners are registered
        self.register_listeners()
        
        # Create handler
        self._handler = SlackRequestHandler(self.app)
        
        @flask_app.route('/slack/events', methods=['POST'])
        def slack_events():
            """Handle Slack events (including URL verification)."""
            return self._handler.handle(request)
        
        @flask_app.route('/slack/interactions', methods=['POST'])
        def slack_interactions():
            """Handle Slack interactive components."""
            return self._handler.handle(request)
        
        @flask_app.route('/slack/commands', methods=['POST'])
        def slack_commands():
            """Handle Slack slash commands."""
            return self._handler.handle(request)
        
        @flask_app.route('/slack/options', methods=['POST'])
        def slack_options():
            """Handle Slack options requests (dynamic select menus)."""
            return self._handler.handle(request)
        
        logger.info("Slack Flask routes registered: events, interactions, commands, options")
    
    def is_connected(self) -> bool:
        """Check if the Slack bot is connected."""
        if self._app is None:
            return False
        
        try:
            # Try to make a simple API call
            result = self.client.auth_test()
            return result.get("ok", False)
        except Exception as e:
            logger.warning(f"Slack connection check failed: {e}")
            return False
    
    def get_bot_info(self) -> dict:
        """Get information about the bot."""
        if self._app is None:
            return {"connected": False}
        
        try:
            result = self.client.auth_test()
            if result.get("ok"):
                return {
                    "connected": True,
                    "user": result.get("user"),
                    "user_id": result.get("user_id"),
                    "team": result.get("team"),
                    "team_id": result.get("team_id")
                }
        except Exception as e:
            logger.warning(f"Failed to get bot info: {e}")
        
        return {"connected": False}
