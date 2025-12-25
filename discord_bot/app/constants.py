"""
Discord Bot Constants.

Enums and constants used throughout the Discord bot application.
"""

from enum import Enum


class LogType(str, Enum):
    """Types of log entries stored in discord_bot_log table."""
    COMMAND = "command"      # Slash/hybrid command executions
    MESSAGE = "message"      # Game chat messages sent/received
    ERROR = "error"          # Exceptions and errors
    BROADCAST = "broadcast"  # Incoming broadcasts from game_server
    SYSTEM = "system"        # System events (startup, shutdown, etc.)


class ReadinessCheck(str, Enum):
    """Components checked during readiness probe."""
    BOT_CONNECTED = "bot_connected"
    BOT_READY = "bot_ready"
    DATABASE = "database"
    COGS_LOADED = "cogs_loaded"

