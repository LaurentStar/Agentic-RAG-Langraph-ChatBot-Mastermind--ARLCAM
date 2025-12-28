"""
Bot Runner.

Main async runner for the Discord bot and Flask server.
"""

import asyncio
import os
import signal
import sys
import logging

from app import create_app
from app.lifecycle.flask_server import start_flask_server, stop_flask_server
from app.lifecycle.shutdown import graceful_shutdown


logger = logging.getLogger("discord_bot")

# Global references for shutdown access
flask_server = None
bot = None


async def run():
    """
    Run the Discord bot alongside Flask server.
    
    This is the main async entry point that:
    1. Creates the Flask app and Discord bot
    2. Starts the Flask server in a background thread
    3. Runs the Discord bot
    4. Handles graceful shutdown on signals/interrupts
    """
    global flask_server, bot
    
    loop = asyncio.get_running_loop()
    shutdown_event = asyncio.Event()
    
    # Create Flask app and get bot instance
    flask_app, bot = create_app(bot_loop=loop)
    
    # Start Flask-RESTX server
    try:
        flask_server, _ = start_flask_server(flask_app)
        logger.info("Flask-RESTX server started")
    except Exception as e:
        logger.error(f"Failed to start Flask server: {e}")
        return
    
    # Setup signal handlers (Unix only - Windows uses KeyboardInterrupt)
    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: shutdown_event.set())
    
    try:
        # Start the Discord bot
        async with bot:
            bot_task = asyncio.create_task(bot.start(os.getenv("TOKEN")))
            
            if sys.platform == "win32":
                # On Windows, we rely on KeyboardInterrupt
                await bot_task
            else:
                # On Unix, wait for either bot to finish or shutdown signal
                shutdown_task = asyncio.create_task(shutdown_event.wait())
                done, pending = await asyncio.wait(
                    [bot_task, shutdown_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                        
    except asyncio.CancelledError:
        logger.info("Bot task cancelled")
    finally:
        # Graceful shutdown
        await graceful_shutdown(loop, flask_server, bot)


def cleanup_sync():
    """
    Synchronous cleanup for Windows KeyboardInterrupt.
    
    Called when asyncio.run() is interrupted and we can't
    run async cleanup code.
    """
    global flask_server
    if flask_server:
        stop_flask_server(flask_server)

