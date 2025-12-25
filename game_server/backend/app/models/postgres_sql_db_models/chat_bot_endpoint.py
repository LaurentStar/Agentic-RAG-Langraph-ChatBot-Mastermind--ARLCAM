"""
Chat Bot Endpoint ORM Model.

SQLAlchemy model for registered bot endpoints that receive broadcast pushes.
"""

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Boolean, DateTime
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from app.constants import SocialMediaPlatform
from app.extensions import db


class ChatBotEndpoint(db.Model):
    """
    Registered bot endpoints for chat broadcast.
    
    Each session can have multiple bot endpoints registered
    (one per platform). When chat broadcast occurs, game_server
    POSTs the message batch to each registered endpoint.
    """
    
    __bind_key__ = 'db_players'
    __tablename__ = 'chat_bot_endpoint_table_orm'
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Session reference
    session_id: Mapped[str] = mapped_column(
        ForeignKey("game_session_table_orm.session_id"),
        nullable=False
    )
    
    # Platform identification
    platform: Mapped[SocialMediaPlatform] = mapped_column(
        postgresql.ENUM(SocialMediaPlatform, name="social_media_platform_enum", create_type=False),
        nullable=False
    )
    
    # Endpoint URL (e.g., http://localhost:3001/api/broadcast)
    endpoint_url: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    last_broadcast_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

