"""
Lifecycle module.

Application lifecycle management functions.
"""

from app.lifecycle.runner import run
from app.lifecycle.flask_server import start_flask_server, stop_flask_server
from app.lifecycle.shutdown import (
    setup_signal_handlers,
    set_shutdown_callback,
    graceful_shutdown,
    request_shutdown,
    is_shutdown_requested
)

__all__ = [
    'run',
    'start_flask_server',
    'stop_flask_server',
    'setup_signal_handlers',
    'set_shutdown_callback',
    'graceful_shutdown',
    'request_shutdown',
    'is_shutdown_requested'
]
