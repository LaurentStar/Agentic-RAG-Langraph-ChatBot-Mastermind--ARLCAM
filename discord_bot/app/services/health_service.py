"""
Health Service.

Health and readiness check logic for the Discord bot.
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
    
    # Required cogs for the bot to be considered ready
    REQUIRED_COGS = ["game_chat"]
    
    @staticmethod
    def check_health() -> Dict[str, Any]:
        """
        Basic health check (liveness probe).
        
        Returns:
            Health status dict
        """
        return {
            "status": "ok",
            "service": "discord_bot"
        }
    
    @staticmethod
    def check_readiness(bot, app=None) -> Dict[str, Any]:
        """
        Full readiness check.
        
        Checks:
        - Bot is connected to Discord
        - Bot is ready (logged in, caches populated)
        - Database connection is working
        - Required cogs are loaded
        
        Args:
            bot: The Discord bot instance
            app: Flask app instance (optional, for db check)
        
        Returns:
            Readiness status dict with details for each check
        """
        checks: Dict[str, bool] = {}
        details: Dict[str, str] = {}
        
        # Check 1: Bot connected
        if bot:
            checks[ReadinessCheck.BOT_CONNECTED] = True
            details[ReadinessCheck.BOT_CONNECTED] = "Bot instance exists"
        else:
            checks[ReadinessCheck.BOT_CONNECTED] = False
            details[ReadinessCheck.BOT_CONNECTED] = "Bot instance not set"
        
        # Check 2: Bot ready
        if bot and bot.is_ready():
            checks[ReadinessCheck.BOT_READY] = True
            details[ReadinessCheck.BOT_READY] = f"Logged in as {bot.user}"
        else:
            checks[ReadinessCheck.BOT_READY] = False
            details[ReadinessCheck.BOT_READY] = "Bot not ready"
        
        # Check 3: Database
        try:
            db.session.execute(db.text("SELECT 1"))
            checks[ReadinessCheck.DATABASE] = True
            details[ReadinessCheck.DATABASE] = "Connection OK"
        except Exception as e:
            checks[ReadinessCheck.DATABASE] = False
            details[ReadinessCheck.DATABASE] = f"Connection failed: {str(e)}"
        
        # Check 4: Required cogs loaded
        if bot:
            loaded_cogs = list(bot.cogs.keys()) if bot.cogs else []
            missing_cogs = [
                cog for cog in HealthService.REQUIRED_COGS 
                if cog not in [c.lower() for c in loaded_cogs]
            ]
            
            if not missing_cogs:
                checks[ReadinessCheck.COGS_LOADED] = True
                details[ReadinessCheck.COGS_LOADED] = f"Loaded: {loaded_cogs}"
            else:
                checks[ReadinessCheck.COGS_LOADED] = False
                details[ReadinessCheck.COGS_LOADED] = f"Missing: {missing_cogs}"
        else:
            checks[ReadinessCheck.COGS_LOADED] = False
            details[ReadinessCheck.COGS_LOADED] = "Bot not available"
        
        # Overall readiness
        all_ready = all(checks.values())
        
        return {
            "ready": all_ready,
            "checks": {k.value: v for k, v in checks.items()},
            "details": {k.value: v for k, v in details.items()}
        }
