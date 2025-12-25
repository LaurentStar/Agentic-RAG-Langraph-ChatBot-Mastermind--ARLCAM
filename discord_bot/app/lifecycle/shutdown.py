"""
Shutdown Management.

Graceful shutdown and cleanup handlers.
"""

import asyncio
import logging
from typing import Any, Optional


logger = logging.getLogger("discord_bot")


async def graceful_shutdown(
    loop: asyncio.AbstractEventLoop,
    flask_server: Optional[Any] = None,
    bot: Optional[Any] = None
) -> None:
    """
    Perform graceful shutdown of all services.
    
    Args:
        loop: The asyncio event loop
        flask_server: The werkzeug server instance (optional)
        bot: The Discord bot instance (optional)
    """
    from app.lifecycle.flask_server import stop_flask_server
    
    logger.info("Initiating graceful shutdown...")
    
    # Stop Flask server
    if flask_server:
        try:
            stop_flask_server(flask_server)
        except Exception as e:
            logger.warning(f"Error stopping Flask server: {e}")
    
    # Close Discord bot
    if bot:
        try:
            await bot.close()
            logger.info("Discord bot closed")
        except Exception as e:
            logger.warning(f"Error closing bot: {e}")
    
    # Cancel pending tasks
    pending = asyncio.all_tasks(loop)
    for task in pending:
        task.cancel()
    
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)
        logger.info(f"Cancelled {len(pending)} pending tasks")
    
    logger.info("Graceful shutdown complete")

