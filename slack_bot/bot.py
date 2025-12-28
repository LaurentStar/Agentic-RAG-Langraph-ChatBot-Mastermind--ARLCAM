"""
Slack Bot for Coup Game.

Main entry point for the Slack bot.
Runs the bot alongside a Flask-RESTX server for API operations.
"""
from dotenv import load_dotenv; load_dotenv('.env')
import os
import sys
import logging

from app.config import logger
from app.lifecycle import run

if os.getenv("ENVIRONMENT", "local") == "local":
    logger.info(f"SLACK_BOT_TOKEN: {os.getenv('SLACK_BOT_TOKEN', 'NOT SET')[:20]}...")


def main():
    """Main entry point."""
    try:
        run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
        logger.info("Shutdown complete")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        sys.exit(0)


if __name__ == "__main__":
    main()

