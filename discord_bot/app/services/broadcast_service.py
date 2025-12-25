"""
Broadcast Service.

Handles routing of game_server broadcasts to Discord channels.
Migrated from broadcast_server.py.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class BroadcastService:
    """
    Service for handling game_server broadcast messages.
    
    Routes messages to the correct Discord channel based on session_id,
    using the GameChat cog's channel registry.
    """
    
    @staticmethod
    async def post_to_discord(
        bot,
        session_id: str,
        messages: List[Dict[str, Any]]
    ) -> bool:
        """
        Post broadcast messages to the appropriate Discord channel.
        
        Routes the broadcast to the correct channel based on session_id
        using the GameChat cog's channel registry.
        
        Args:
            bot: The Discord bot instance
            session_id: Game session ID to route to
            messages: List of message dicts with sender, platform, content
        
        Returns:
            True if successful, False otherwise
        """
        if not bot:
            logger.error("Bot instance not provided")
            return False
        
        # Use the GameChat cog for routing
        game_chat_cog = bot.get_cog("game_chat")
        if not game_chat_cog:
            logger.error("GameChat cog not loaded")
            return False
        
        # Route via the cog (which uses session_id to find the right channel)
        try:
            return await game_chat_cog.post_broadcast(session_id, messages)
        except Exception as e:
            logger.error(f"Error posting broadcast: {e}")
            return False
    
    @staticmethod
    def post_to_discord_sync(
        bot,
        bot_loop,
        session_id: str,
        messages: List[Dict[str, Any]],
        timeout: float = 10.0
    ) -> tuple:
        """
        Synchronous wrapper for posting to Discord.
        
        Used by Flask endpoints which run in a different thread.
        
        Args:
            bot: The Discord bot instance
            bot_loop: The bot's asyncio event loop
            session_id: Game session ID
            messages: List of message dicts
            timeout: Timeout in seconds
        
        Returns:
            Tuple of (success: bool, error: Optional[str])
        """
        if not bot:
            return False, "Bot not initialized"
        
        if not bot.is_ready():
            return False, "Bot not ready"
        
        if not messages:
            return True, None  # No messages is not an error
        
        try:
            # Schedule the async post on the bot's event loop
            future = asyncio.run_coroutine_threadsafe(
                BroadcastService.post_to_discord(bot, session_id, messages),
                bot_loop
            )
            
            # Wait for result with timeout
            success = future.result(timeout=timeout)
            
            if success:
                return True, None
            else:
                return False, "Failed to post to Discord - no channel registered?"
                
        except asyncio.TimeoutError:
            logger.error("Timeout posting to Discord")
            return False, "Timeout"
        except Exception as e:
            logger.error(f"Error posting to Discord: {e}")
            return False, str(e)

