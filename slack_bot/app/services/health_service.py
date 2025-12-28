"""
Health Service.

Health and readiness check logic for the Slack bot.
"""

import logging
from typing import Dict, Any

from app.constants import ReadinessCheck
from app.extensions import db

logger = logging.getLogger(__name__)


class HealthService:
    """
    Service for health and readiness checks.
    
    Used by Kubernetes-style probes:
    - /health (liveness) - is the server running?
    - /ready (readiness) - is the bot fully operational?
    """
    
    # Required listeners for the bot to be considered ready
    REQUIRED_LISTENERS = ["game_chat", "admin_commands"]
    
    @staticmethod
    def check_health() -> Dict[str, Any]:
        """
        Basic health check (liveness probe).
        
        Returns:
            Health status dict
        """
        return {
            "status": "ok",
            "service": "slack_bot"
        }
    
    @staticmethod
    def check_readiness(slack_bot, app=None) -> Dict[str, Any]:
        """
        Full readiness check.
        
        Checks:
        - Bot is connected to Slack
        - Database connection is working
        - Required listeners are registered
        
        Args:
            slack_bot: The Slack bot instance
            app: Flask app instance (optional, for db check)
        
        Returns:
            Readiness status dict with details for each check
        """
        checks: Dict[str, bool] = {}
        details: Dict[str, str] = {}
        
        # Check 1: Bot connected
        if slack_bot:
            checks[ReadinessCheck.BOT_CONNECTED.value] = True
            details[ReadinessCheck.BOT_CONNECTED.value] = "Bot instance exists"
        else:
            checks[ReadinessCheck.BOT_CONNECTED.value] = False
            details[ReadinessCheck.BOT_CONNECTED.value] = "Bot instance not set"
        
        # Check 2: Bot ready (can make API calls)
        if slack_bot and slack_bot.is_connected():
            bot_info = slack_bot.get_bot_info()
            checks[ReadinessCheck.BOT_READY.value] = True
            details[ReadinessCheck.BOT_READY.value] = f"Connected as {bot_info.get('user', 'unknown')}"
        else:
            checks[ReadinessCheck.BOT_READY.value] = False
            details[ReadinessCheck.BOT_READY.value] = "Bot not connected to Slack"
        
        # Check 3: Database
        try:
            db.session.execute(db.text("SELECT 1"))
            checks[ReadinessCheck.DATABASE.value] = True
            details[ReadinessCheck.DATABASE.value] = "Connection OK"
        except Exception as e:
            checks[ReadinessCheck.DATABASE.value] = False
            details[ReadinessCheck.DATABASE.value] = f"Connection failed: {str(e)}"
        
        # Check 4: Listeners loaded
        if slack_bot and slack_bot._initialized:
            checks[ReadinessCheck.LISTENERS_LOADED.value] = True
            details[ReadinessCheck.LISTENERS_LOADED.value] = "All listeners registered"
        else:
            checks[ReadinessCheck.LISTENERS_LOADED.value] = False
            details[ReadinessCheck.LISTENERS_LOADED.value] = "Listeners not initialized"
        
        # Overall readiness
        all_ready = all(checks.values())
        
        return {
            "ready": all_ready,
            "checks": checks,
            "details": details
        }
