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
    
    # Stop Flask server first (synchronous, runs in thread)
    if flask_server:
        try:
            stop_flask_server(flask_server)
        except Exception as e:
            logger.warning(f"Error stopping Flask server: {e}")
    
    # Close Discord bot
    if bot and not bot.is_closed():
        try:
            await bot.close()
            logger.info("Discord bot closed")
        except Exception as e:
            logger.warning(f"Error closing bot: {e}")
    
    # Cancel pending tasks (except current one)
    current_task = asyncio.current_task()
    pending = [
        task for task in asyncio.all_tasks(loop) 
        if task is not current_task and not task.done()
    ]
    
    if pending:
        logger.info(f"Cancelling {len(pending)} pending tasks...")
        for task in pending:
            task.cancel()
        
        # Wait for tasks to finish with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(*pending, return_exceptions=True),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            logger.warning("Some tasks did not cancel within timeout")
        
        logger.info("Pending tasks cancelled")
    
    logger.info("Graceful shutdown complete")

