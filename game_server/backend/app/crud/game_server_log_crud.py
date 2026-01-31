"""
Game Server Log CRUD Operations.

Data access layer for game_server_log table.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional

from app.crud.base import BaseCRUD
from app.models.postgres_sql_db_models import GameServerLog


class GameServerLogCRUD(BaseCRUD[GameServerLog]):
    """CRUD operations for GameServerLog."""
    
    model = GameServerLog
    
    @classmethod
    def get_recent(cls, limit: int = 100) -> List[GameServerLog]:
        """Get recent logs."""
        return cls.model.query.order_by(
            GameServerLog.created_at.desc()
        ).limit(limit).all()
    
    @classmethod
    def get_by_level(cls, level: str, limit: int = 100) -> List[GameServerLog]:
        """Get logs by level (INFO, WARNING, ERROR, etc.)."""
        return cls.model.query.filter_by(level=level).order_by(
            GameServerLog.created_at.desc()
        ).limit(limit).all()
    
    @classmethod
    def get_errors(cls, limit: int = 100) -> List[GameServerLog]:
        """Get error logs."""
        return cls.get_by_level('ERROR', limit)
    
    @classmethod
    def get_by_session(cls, session_id: str, limit: int = 100) -> List[GameServerLog]:
        """Get logs for a specific session."""
        return cls.model.query.filter_by(session_id=session_id).order_by(
            GameServerLog.created_at.desc()
        ).limit(limit).all()
    
    @classmethod
    def get_since(cls, since: datetime, limit: int = 1000) -> List[GameServerLog]:
        """Get logs since a specific time."""
        return cls.model.query.filter(
            GameServerLog.created_at >= since
        ).order_by(GameServerLog.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_last_hours(cls, hours: int = 24, limit: int = 1000) -> List[GameServerLog]:
        """Get logs from the last N hours."""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        return cls.get_since(since, limit)
    
    @classmethod
    def cleanup_old_logs(cls, days: int = 30) -> int:
        """Delete logs older than N days. Returns count deleted."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        from app.extensions import db
        result = cls.model.query.filter(GameServerLog.created_at < cutoff).delete()
        db.session.commit()
        return result
