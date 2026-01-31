"""
Operations Status Service.

Provides system status information: version, uptime, environment, and counts.
"""

import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any

# Track server start time
_SERVER_START_TIME = datetime.now(timezone.utc)


class OpsStatusService:
    """Service for system status and metrics."""
    
    # Version info - update this when releasing
    VERSION = "1.0.0"
    SERVICE_NAME = "game_server"
    
    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """
        Get full system status.
        
        Returns:
            Dict with service info, version, uptime, environment
        """
        now = datetime.now(timezone.utc)
        uptime = now - _SERVER_START_TIME
        
        return {
            "service": cls.SERVICE_NAME,
            "version": cls.VERSION,
            "environment": os.getenv("ENVIRONMENT", "local"),
            "uptime_seconds": int(uptime.total_seconds()),
            "started_at": _SERVER_START_TIME.isoformat() + "Z",
            "python_version": sys.version.split()[0],
            "timestamp": now.isoformat() + "Z"
        }
    
    @classmethod
    def get_summary(cls) -> Dict[str, Any]:
        """
        Get quick summary with counts.
        
        Returns:
            Dict with session, player, and job counts
        """
        from app.models.postgres_sql_db_models import GameSession, UserAccount
        from app.constants import SessionStatus
        from app import scheduler
        
        # Count active sessions
        active_sessions = GameSession.query.filter_by(
            status=SessionStatus.ACTIVE
        ).count()
        
        total_sessions = GameSession.query.count()
        
        # Count users
        total_players = UserAccount.query.count()
        
        # Count scheduled jobs
        jobs = scheduler.get_jobs()
        
        return {
            "sessions": {
                "active": active_sessions,
                "total": total_sessions
            },
            "players": {
                "total": total_players
            },
            "scheduled_jobs": len(jobs),
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
        }

