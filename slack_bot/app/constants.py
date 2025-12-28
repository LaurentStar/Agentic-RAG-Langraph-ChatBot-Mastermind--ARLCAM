"""
Slack Bot Constants.

Platform-specific constants and configuration values.
"""

from enum import Enum


# Platform identifier
PLATFORM = "slack"

# API version
API_VERSION = "1.0"

# Default ports
DEFAULT_FLASK_PORT = 3002

# Slack-specific
SLACK_API_BASE_URL = "https://slack.com/api"


class LogType(str, Enum):
    """Log entry types."""
    COMMAND = "command"
    MESSAGE = "message"
    ERROR = "error"
    BROADCAST = "broadcast"
    SYSTEM = "system"


class ReadinessCheck(str, Enum):
    """Readiness check identifiers."""
    BOT_CONNECTED = "bot_connected"
    BOT_READY = "bot_ready"
    DATABASE = "database"
    LISTENERS_LOADED = "listeners_loaded"
