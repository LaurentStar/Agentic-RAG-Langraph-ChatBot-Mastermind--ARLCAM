"""
Broadcast Destination CRUD Operations.

Data access layer for broadcast_destination table.
"""

from typing import List, Optional

from app.crud.base import BaseCRUD
from app.models.postgres_sql_db_models import BroadcastDestination


class BroadcastDestinationCRUD(BaseCRUD[BroadcastDestination]):
    """CRUD operations for BroadcastDestination."""
    
    model = BroadcastDestination
    
    @classmethod
    def get_by_session(cls, session_id: str) -> List[BroadcastDestination]:
        """Get all broadcast destinations for a session."""
        return cls.model.query.filter_by(session_id=session_id).all()
    
    @classmethod
    def get_active_by_session(cls, session_id: str) -> List[BroadcastDestination]:
        """Get active broadcast destinations for a session."""
        return cls.model.query.filter_by(
            session_id=session_id,
            is_active=True
        ).all()
    
    @classmethod
    def get_by_platform(cls, session_id: str, platform: str) -> List[BroadcastDestination]:
        """Get destinations for a specific platform in a session."""
        return cls.model.query.filter_by(
            session_id=session_id,
            platform=platform
        ).all()
    
    @classmethod
    def deactivate(cls, destination_id: int) -> Optional[BroadcastDestination]:
        """Deactivate a broadcast destination."""
        return cls.update(destination_id, is_active=False)
    
    @classmethod
    def activate(cls, destination_id: int) -> Optional[BroadcastDestination]:
        """Activate a broadcast destination."""
        return cls.update(destination_id, is_active=True)
