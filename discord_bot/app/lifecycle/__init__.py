"""
Lifecycle Module.

Runtime lifecycle management for the application.
Handles server start/stop, shutdown, and cleanup.
"""

from app.lifecycle.flask_server import start_flask_server, stop_flask_server
from app.lifecycle.shutdown import graceful_shutdown
from app.lifecycle.runner import run, cleanup_sync

__all__ = [
    'start_flask_server',
    'stop_flask_server',
    'graceful_shutdown',
    'run',
    'cleanup_sync',
]

