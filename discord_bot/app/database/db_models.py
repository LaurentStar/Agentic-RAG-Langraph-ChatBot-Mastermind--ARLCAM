"""
Database Models.

SQLAlchemy ORM models for Discord bot logging.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Text, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class DiscordBotLog(db.Model):
    """
    Discord Bot Log Table.
    
    Stores command executions, game messages, and errors.
    """
    __tablename__ = 'discord_bot_log'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    log_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    guild_id: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, index=True)
    channel_id: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, index=True)
    user_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True
    )
    
    def __repr__(self):
        return f"<DiscordBotLog {self.id} {self.log_type}>"
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'log_type': self.log_type,
            'guild_id': self.guild_id,
            'channel_id': self.channel_id,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'content': self.content,
            'extra_data': self.extra_data,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
