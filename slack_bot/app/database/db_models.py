"""
Database Models.

SQLAlchemy ORM models for Slack bot logging and caching.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Text, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class TokenCache(db.Model):
    """
    Slack Token Cache Table.
    
    Caches JWT tokens for Slack users who have linked their accounts.
    Avoids repeated calls to game server for token lookup.
    """
    __tablename__ = 'slack_cache_tokens'
    
    # Slack user ID as primary key (one cache entry per user)
    slack_user_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    
    # Cached tokens
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Player info from game server
    player_display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    player_type: Mapped[str] = mapped_column(String(20), default="human")
    
    # Cache metadata
    cached_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    
    def __repr__(self):
        return f"<TokenCache {self.slack_user_id} -> {self.player_display_name}>"
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'slack_user_id': self.slack_user_id,
            'player_display_name': self.player_display_name,
            'player_type': self.player_type,
            'cached_at': self.cached_at.isoformat() if self.cached_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }
    
    def is_expired(self) -> bool:
        """Check if the cached token has expired."""
        return datetime.now(timezone.utc) >= self.expires_at


class SlackBotLog(db.Model):
    """
    Slack Bot Log Table.
    
    Stores command executions, game messages, and errors.
    """
    __tablename__ = 'slack_bot_log'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    log_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    team_id: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, index=True)
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
        return f"<SlackBotLog {self.id} {self.log_type}>"
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'log_type': self.log_type,
            'team_id': self.team_id,
            'channel_id': self.channel_id,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'content': self.content,
            'extra_data': self.extra_data,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
