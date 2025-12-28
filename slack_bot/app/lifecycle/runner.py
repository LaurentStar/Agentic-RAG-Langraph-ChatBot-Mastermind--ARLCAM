"""
Application Runner.

Main entry point for running the Slack bot and Flask server.
"""

import os
import time
import logging
from typing import Optional

from app import create_app
from app.config import logger, setup_logging
from app.lifecycle.flask_server import start_flask_server
from app.lifecycle.shutdown import (
    setup_signal_handlers,
    set_shutdown_callback,
    is_shutdown_requested,
    graceful_shutdown
)


def run() -> None:
    """
    Run the Slack bot and Flask server.
    
    This is the main entry point for the application.
    Starts the Flask server (which includes Slack event handlers)
    and keeps the main thread alive until shutdown is requested.
    
    Note: Ngrok tunnel is now handled by game_server which proxies
    Slack traffic to this server (when ENVIRONMENT=local).
    """
    # Setup logging
    setup_logging()
    logger.info("Starting Slack Bot...")
    
    # Check environment
    environment = os.getenv("ENVIRONMENT", "local").lower()
    logger.info(f"Environment: {environment}")
    
    # Setup signal handlers for graceful shutdown
    setup_signal_handlers()
    set_shutdown_callback(graceful_shutdown)
    
    # Create the Flask app and Slack bot
    app, slack_bot = create_app()
    
    # Start Flask server
    port = int(os.getenv("SLACK_BOT_PORT", "3002"))
    if not start_flask_server(app, port):
        logger.error("Failed to start Flask server. Exiting.")
        return
    
    # Display startup info
    logger.info("=" * 60)
    logger.info("Slack Bot is running!")
    logger.info(f"  Environment: {environment}")
    logger.info(f"  Flask API: http://localhost:{port}")
    logger.info(f"  Swagger UI: http://localhost:{port}/docs")
    logger.info(f"  Slack Events: http://localhost:{port}/slack/events")
    
    if environment == "local":
        logger.info("")
        logger.info("  NOTE: Slack traffic is proxied through game_server.")
        logger.info("  Start game_server first - it provides the ngrok tunnel.")
    
    logger.info("=" * 60)
    logger.info("Press Ctrl+C to stop.")
    
    # Keep main thread alive
    try:
        while not is_shutdown_requested():
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    
    # Cleanup
    graceful_shutdown()
    logger.info("Slack Bot stopped.")
