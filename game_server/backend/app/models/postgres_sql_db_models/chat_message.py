"""
Chat Message ORM Model.

SQLAlchemy model for cross-platform game chat messages.
Messages are queued here and broadcast to all platforms periodically.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Boolean, DateTime
from sqlalchemy.dialects import postgresql
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
    __tablename__ = 'chat_message_table_orm'
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Session reference
    session_id: Mapped[str] = mapped_column(
        ForeignKey("game_session_table_orm.session_id"),
        nullable=False
    )
    
    # Sender information
    sender_display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    sender_platform: Mapped[SocialMediaPlatform] = mapped_column(
        postgresql.ENUM(SocialMediaPlatform, name="social_media_platform_enum", create_type=False),
        nullable=False
    )
    
    # Message content (max 2000 chars to fit most platform limits)
    content: Mapped[str] = mapped_column(String(2000), nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )

