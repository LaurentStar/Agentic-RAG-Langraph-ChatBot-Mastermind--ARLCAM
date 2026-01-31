"""
Chat Message ORM Model.

SQLAlchemy model for cross-platform game chat messages.
Messages are queued here and broadcast to all platforms periodically.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import Mapped, mapped_column

from app.constants import SocialMediaPlatform
from app.extensions import db


class ChatMessage(db.Model):
    """
    Chat message queue table.
    
    Messages from all platforms are stored here temporarily,
    then broadcast to all registered bot endpoints and cleared.
    """
    
    __bind_key__ = 'db_players'
    __tablename__ = 'gs_chat_message_table_orm'
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Session reference
    session_id: Mapped[str] = mapped_column(
        ForeignKey("gs_game_session_table_orm.session_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Sender reference (user_id for lookups)
    sender_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gs_user_account_table_orm.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Sender display info (denormalized for broadcast performance)
    sender_display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Stored at message time - display names might change later
    
    sender_platform: Mapped[SocialMediaPlatform] = mapped_column(
        ENUM(SocialMediaPlatform, name="social_media_platform_enum", create_type=True),
        nullable=False
    )
    
    # Message content (max 2000 chars to fit most platform limits)
    content: Mapped[str] = mapped_column(String(2000), nullable=False)
    
    # Broadcast status
    is_broadcast: Mapped[bool] = mapped_column(default=False)
    # True once message has been broadcast to all platforms
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    
    def __repr__(self):
        return f"<ChatMessage {self.id}: {self.sender_display_name} in {self.session_id}>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'sender_user_id': str(self.sender_user_id),
            'sender_display_name': self.sender_display_name,
            'sender_platform': self.sender_platform.value,
            'content': self.content,
            'is_broadcast': self.is_broadcast,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
