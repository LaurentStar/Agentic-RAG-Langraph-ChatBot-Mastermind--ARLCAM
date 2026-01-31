"""
Application lifecycle management.

Contains modules for startup and shutdown operations.
"""
from app.lifecycle.ngrok_tunnel import start_tunnel, stop_tunnel
from app.lifecycle.startup import create_default_admin_if_enabled

__all__ = ["start_tunnel", "stop_tunnel", "create_default_admin_if_enabled"]

