"""
Discord Bot for Coup Game.

Main entry point for the Discord bot.
Runs the bot alongside a Flask-RESTX server for API operations.
"""
from dotenv import load_dotenv; load_dotenv('.env')
import asyncio
import os
import sys





from app.config import logger
from app.lifecycle import run, cleanup_sync


def main():
    """Main entry point."""
    # Windows-specific event loop policy
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
        cleanup_sync()
        logger.info("Shutdown complete")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        os._exit(0)


if __name__ == "__main__":
    main()
