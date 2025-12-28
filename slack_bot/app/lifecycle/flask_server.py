"""
Flask Server Lifecycle.

Functions for starting and stopping the Flask server.
"""

import os
import logging
import threading
from typing import Optional
from werkzeug.serving import make_server

from flask import Flask

logger = logging.getLogger("slack_bot")

# Server instance (for shutdown)
_server = None
_server_thread: Optional[threading.Thread] = None


def start_flask_server(app: Flask, port: Optional[int] = None) -> bool:
    """
    Start the Flask server in a background thread.
    
    Args:
        app: Flask application instance
        port: Port to listen on (default: SLACK_BOT_PORT env or 3002)
    
    Returns:
        True if server started successfully
    """
    global _server, _server_thread
    
    if port is None:
        port = int(os.getenv("SLACK_BOT_PORT", "3002"))
    
    try:
        _server = make_server("0.0.0.0", port, app, threaded=True)
        
        _server_thread = threading.Thread(
            target=_server.serve_forever,
            name="FlaskServer",
            daemon=True
        )
        _server_thread.start()
        
        logger.info(f"Flask server started on http://0.0.0.0:{port}")
        logger.info(f"  Swagger UI: http://localhost:{port}/docs")
        return True
        
    except Exception as e:
        logger.error(f"Failed to start Flask server: {e}")
        return False


def stop_flask_server() -> None:
    """Stop the Flask server gracefully."""
    global _server, _server_thread
    
    if _server:
        logger.info("Stopping Flask server...")
        try:
            _server.shutdown()
        except Exception as e:
            logger.warning(f"Error shutting down Flask server: {e}")
        _server = None
    
    if _server_thread and _server_thread.is_alive():
        _server_thread.join(timeout=5.0)
        if _server_thread.is_alive():
            logger.warning("Flask server thread did not stop in time")
    
    _server_thread = None
    logger.info("Flask server stopped")


def is_running() -> bool:
    """Check if the Flask server is running."""
    return _server is not None and _server_thread is not None and _server_thread.is_alive()
