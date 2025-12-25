"""
Broadcast Destination ORM Model.

SQLAlchemy model for managing where game results are broadcast.
"""

from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import SocialMediaPlatform
from app.extensions import db


class BroadcastDestination(db.Model):
    """Broadcast destination table ORM model."""
    
    __bind_key__ = 'db_players'
    __tablename__ = 'broadcast_destination_table_orm'
    
    # ---------------------- Identity ---------------------- #
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("game_session_table_orm.session_id"),
        nullable=False
    )
    
    # ---------------------- Platform Info ---------------------- #
    platform: Mapped[SocialMediaPlatform] = mapped_column(
        postgresql.ENUM(SocialMediaPlatform, name="social_media_platform_enum", create_type=True)
    )
    channel_id: Mapped[str] = mapped_column(String, nullable=False)
    channel_name: Mapped[str] = mapped_column(String, nullable=False)
    webhook_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # ---------------------- Relationships ---------------------- #
    session = relationship("GameSession", back_populates="broadcast_destinations")

