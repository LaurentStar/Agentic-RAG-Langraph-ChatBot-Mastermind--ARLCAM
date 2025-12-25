"""
Flask Server Management.

Functions for starting and stopping the Flask server
in a background thread alongside the Discord bot.
"""

import logging
import os
from threading import Thread

from werkzeug.serving import make_server


logger = logging.getLogger("discord_bot")


def start_flask_server(app, port: int = None, host: str = '0.0.0.0'):
    """
    Start Flask server in a background thread.
    
    Args:
        app: Flask application
        port: Port to listen on (default: BROADCAST_PORT env or 3001)
        host: Host to bind to
    
    Returns:
        Tuple of (server, thread)
    """
    if port is None:
        port = int(os.getenv("BROADCAST_PORT", "3001"))
    
    server = make_server(host, port, app, threaded=True)
    
    def run_server():
        logger.info(f"Flask server listening on {host}:{port}")
        server.serve_forever()
        logger.info("Flask server stopped")
    
    thread = Thread(target=run_server, daemon=True)
    thread.start()
    
    logger.info(f"Flask server started on port {port}")
    
    return server, thread


def stop_flask_server(server):
    """
    Stop the Flask server gracefully.
    
    Args:
        server: The werkzeug server instance
    """
    if server:
        logger.info("Shutting down Flask server...")
        server.shutdown()
        logger.info("Flask server shutdown complete")

