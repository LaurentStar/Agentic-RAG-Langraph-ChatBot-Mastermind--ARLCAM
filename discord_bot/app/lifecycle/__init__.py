"""
Lifecycle Module.

Runtime lifecycle management for the application.
Handles server start/stop, shutdown, and cleanup.
"""

from app.lifecycle.flask_server import start_flask_server, stop_flask_server
from app.lifecycle.shutdown import graceful_shutdown

__all__ = [
    'start_flask_server',
    'stop_flask_server',
    'graceful_shutdown',
]

