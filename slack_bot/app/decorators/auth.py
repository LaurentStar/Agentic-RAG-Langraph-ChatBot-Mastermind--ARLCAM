"""
Authentication Decorators.

Decorators for requiring linked accounts on Slack commands.
"""

import logging
from functools import wraps
from typing import Callable, TypeVar, Optional

logger = logging.getLogger("slack_bot")

T = TypeVar('T')


def requires_linked_account(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator for Slack commands that require a linked game account.
    
    Checks if the Slack user has a linked account in the game server.
    If not linked, sends a message with instructions to link their account.
    
    Usage:
        @app.command("/game_session-list")
        @requires_linked_account
        def handle_list(ack, respond, command, client, token=None, player_name=None):
            # token and player_name are injected if account is linked
            ...
    
    The decorator injects:
    - token: JWT access token for game server API calls
    - player_name: Player's display name in the game
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Import here to avoid circular imports
        from app.services import TokenCacheService
        
        # Extract command context from kwargs
        command = kwargs.get('command', {})
        respond = kwargs.get('respond')
        ack = kwargs.get('ack')
        
        # Acknowledge immediately
        if ack:
            ack()
        
        user_id = command.get("user_id", "")
        
        if not user_id:
            if respond:
                respond(":x: Could not identify user.")
            return None
        
        # Get or fetch token
        token, error = TokenCacheService.get_token(user_id)
        
        if error == "not_linked":
            login_url = TokenCacheService.get_oauth_login_url()
            if respond:
                respond(
                    ":warning: *Account Not Linked*\n\n"
                    "Your Slack account is not connected to a game account.\n"
                    f"Please <{login_url}|click here> to link your account.\n\n"
                    "_After linking, try the command again._"
                )
            return None
        
        if error:
            logger.error(f"Auth error for Slack user {user_id}: {error}")
            if respond:
                respond(f":x: Authentication error: {error}")
            return None
        
        # Get player name from cache
        player_name = TokenCacheService.get_cached_player_name(user_id)
        
        # Inject token and player_name into kwargs
        kwargs['token'] = token
        kwargs['player_name'] = player_name
        
        return func(*args, **kwargs)
    
    return wrapper


def admin_only(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator for Slack commands that require admin privileges.
    
    Must be used after @requires_linked_account.
    Checks the cached player_type to verify admin status.
    
    Usage:
        @app.command("/admin-only-command")
        @requires_linked_account
        @admin_only
        def handle_admin_command(ack, respond, command, client, token=None, player_name=None):
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Import here to avoid circular imports
        from app.services import TokenCacheService
        
        respond = kwargs.get('respond')
        command = kwargs.get('command', {})
        user_id = command.get("user_id", "")
        
        # Check if token was injected (means @requires_linked_account was called)
        token = kwargs.get('token')
        if not token:
            if respond:
                respond(":x: Authentication required.")
            return None
        
        # Get player type from cache
        from app.database.db_models import TokenCache
        from app.extensions import db
        from app.utils import requires_flask_db
        
        @requires_flask_db
        def get_player_type(slack_user_id: str) -> Optional[str]:
            cached = db.session.get(TokenCache, slack_user_id)
            return cached.player_type if cached else None
        
        # Note: We need to use the Flask app context for this
        # This is handled by the TokenCacheService which has _app reference
        player_type = get_player_type(user_id)
        
        if player_type != "admin":
            if respond:
                respond(":x: This command requires admin privileges.")
            return None
        
        return func(*args, **kwargs)
    
    return wrapper
