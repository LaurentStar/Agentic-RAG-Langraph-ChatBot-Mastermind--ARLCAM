"""
Graceful Shutdown.

Handles graceful shutdown of the application.
"""

import logging
import signal
import sys
from typing import Optional, Callable

logger = logging.getLogger("slack_bot")

# Shutdown state
_shutdown_requested = False
_shutdown_callback: Optional[Callable] = None


def request_shutdown() -> None:
    """Request application shutdown."""
    global _shutdown_requested
    _shutdown_requested = True
    logger.info("Shutdown requested")
    
    if _shutdown_callback:
        try:
            _shutdown_callback()
        except Exception as e:
            logger.error(f"Error in shutdown callback: {e}")


def is_shutdown_requested() -> bool:
    """Check if shutdown has been requested."""
    return _shutdown_requested


def set_shutdown_callback(callback: Callable) -> None:
    """
    Set a callback to be called when shutdown is requested.
    
    Args:
        callback: Function to call on shutdown
    """
    global _shutdown_callback
    _shutdown_callback = callback


def setup_signal_handlers() -> None:
    """Setup signal handlers for graceful shutdown."""
    
    def signal_handler(signum, frame):
        sig_name = signal.Signals(signum).name
        logger.info(f"Received {sig_name}, initiating shutdown...")
        request_shutdown()
    
    # Handle SIGINT (Ctrl+C) and SIGTERM
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.debug("Signal handlers configured")


def graceful_shutdown() -> None:
    """
    Perform graceful shutdown of all components.
    
    Stops:
    1. Flask server
    2. Any running tasks
    """
    from app.lifecycle.flask_server import stop_flask_server
    
    logger.info("Performing graceful shutdown...")
    
    # Stop Flask server
    stop_flask_server()
    
    logger.info("Graceful shutdown complete")
