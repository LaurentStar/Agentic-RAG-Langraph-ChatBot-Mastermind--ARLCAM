"""
Discord Bot for Coup Game.

Main entry point for the Discord bot.
Runs the bot alongside a Flask-RESTX server for API operations.
"""

# ---------------------- Standard Library ---------------------- #
import asyncio
import os
import sys

# ---------------------- External ---------------------- #
from dotenv import load_dotenv

# Load environment variables (must be before app imports)
load_dotenv('.env')

# ---------------------- App ---------------------- #
from app import create_app
from app.config import logger
from app.lifecycle import start_flask_server, graceful_shutdown


# Flask server reference (for shutdown)
_flask_server = None
_bot = None


async def main():
    """Main entry point."""
    global _flask_server, _bot
    
    loop = asyncio.get_event_loop()
    
    # Create Flask app and get bot instance
    flask_app, _bot = create_app(bot_loop=loop)
    
    # Start Flask-RESTX server
    try:
        _flask_server, _ = start_flask_server(flask_app)
        logger.info("Flask-RESTX server started")
    except Exception as e:
        logger.error(f"Failed to start Flask server: {e}")
    
    # Start the Discord bot
    async with _bot:
        await _bot.start(os.getenv("TOKEN"))


if __name__ == "__main__":
    # Windows-specific event loop policy
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
    finally:
        logger.info("Cleaning up...")
        
        # Graceful shutdown
        loop.run_until_complete(
            graceful_shutdown(loop, _flask_server, _bot)
        )
        
        loop.close()
        logger.info("Bot shutdown complete")
        
        # Force exit to terminate all threads
        os._exit(0)
