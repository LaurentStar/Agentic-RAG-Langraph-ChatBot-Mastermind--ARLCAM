"""
Chat Message CRUD Operations.

Data access layer for chat_message table.
"""

from typing import List, Optional
from uuid import UUID

from app.crud.base import BaseCRUD
from app.models.postgres_sql_db_models import ChatMessage
from app.constants import SocialMediaPlatform
from app.extensions import db


class ChatMessageCRUD(BaseCRUD[ChatMessage]):
    """CRUD operations for ChatMessage."""
    
    model = ChatMessage
    
    @classmethod
    def get_by_session(cls, session_id: str, limit: int = 100) -> List[ChatMessage]:
        """Get messages for a session, most recent first."""
        return cls.model.query.filter_by(session_id=session_id).order_by(
            ChatMessage.created_at.desc()
        ).limit(limit).all()
    
    @classmethod
    def get_recent(cls, session_id: str, limit: int = 20) -> List[ChatMessage]:
        """Get recent messages for a session."""
        return cls.get_by_session(session_id, limit=limit)
    
    @classmethod
    def get_unbroadcast(cls, session_id: str) -> List[ChatMessage]:
        """Get messages that haven't been broadcast yet."""
        return cls.model.query.filter_by(
            session_id=session_id,
            is_broadcast=False
        ).order_by(ChatMessage.created_at).all()
    
    @classmethod
    def get_by_sender(cls, session_id: str, sender_user_id: UUID) -> List[ChatMessage]:
        """Get messages from a specific sender in a session."""
        return cls.model.query.filter_by(
            session_id=session_id,
            sender_user_id=sender_user_id
        ).order_by(ChatMessage.created_at.desc()).all()
    
    @classmethod
    def create_message(
        cls,
        session_id: str,
        sender_user_id: UUID,
        sender_display_name: str,
        sender_platform: SocialMediaPlatform,
        content: str
    ) -> ChatMessage:
        """Create a new chat message."""
        return cls.create(
            session_id=session_id,
            sender_user_id=sender_user_id,
            sender_display_name=sender_display_name,
            sender_platform=sender_platform,
            content=content
        )
    
    @classmethod
    def mark_broadcast(cls, message_id: int) -> Optional[ChatMessage]:
        """Mark a message as broadcast."""
        return cls.update(message_id, is_broadcast=True)
    
    @classmethod
    def mark_all_broadcast(cls, session_id: str) -> int:
        """Mark all unbroadcast messages in a session as broadcast."""
        messages = cls.get_unbroadcast(session_id)
        for msg in messages:
            msg.is_broadcast = True
        db.session.commit()
        return len(messages)
