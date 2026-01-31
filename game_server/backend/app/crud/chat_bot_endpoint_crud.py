"""
Chat Bot Endpoint CRUD Operations.

Data access layer for chat_bot_endpoint table.
"""

from typing import List, Optional

from app.crud.base import BaseCRUD
from app.models.postgres_sql_db_models import ChatBotEndpoint


class ChatBotEndpointCRUD(BaseCRUD[ChatBotEndpoint]):
    """CRUD operations for ChatBotEndpoint."""
    
    model = ChatBotEndpoint
    
    @classmethod
    def get_active(cls) -> List[ChatBotEndpoint]:
        """Get all active bot endpoints."""
        return cls.model.query.filter_by(is_active=True).all()
    
    @classmethod
    def get_by_platform(cls, platform: str) -> List[ChatBotEndpoint]:
        """Get endpoints for a specific platform."""
        return cls.model.query.filter_by(platform=platform).all()
    
    @classmethod
    def get_active_by_platform(cls, platform: str) -> List[ChatBotEndpoint]:
        """Get active endpoints for a specific platform."""
        return cls.model.query.filter_by(
            platform=platform,
            is_active=True
        ).all()
    
    @classmethod
    def deactivate(cls, endpoint_id: int) -> Optional[ChatBotEndpoint]:
        """Deactivate an endpoint."""
        return cls.update(endpoint_id, is_active=False)
    
    @classmethod
    def activate(cls, endpoint_id: int) -> Optional[ChatBotEndpoint]:
        """Activate an endpoint."""
        return cls.update(endpoint_id, is_active=True)
