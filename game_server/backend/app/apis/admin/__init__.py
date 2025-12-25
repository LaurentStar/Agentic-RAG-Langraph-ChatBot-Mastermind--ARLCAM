"""
Admin API.

Privileged operations for session and player management.
"""

from app.apis.admin.admin_session_ns import admin_session_ns
from app.apis.admin.admin_player_ns import admin_player_ns

__all__ = ["admin_session_ns", "admin_player_ns"]

