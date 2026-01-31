"""
Player Profile ORM Model.

SQLAlchemy model for persistent player statistics and preferences.
This data accumulates over time and persists across game sessions.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import ForeignKey, String, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class PlayerProfile(db.Model):
    """
    Player Profile table ORM model.
    
    Persistent game-related data that accumulates over time.
    One profile per user account (1:1 relationship).
    """
    
    __bind_key__ = 'db_players'
    __tablename__ = 'gs_player_profile_table_orm'
    
    # =============================================
    # Identity (FK to UserAccount)
    # =============================================
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gs_user_account_table_orm.user_id", ondelete="CASCADE"),
        primary_key=True
    )
    
    # =============================================
    # Profile Information
    # =============================================
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    
    bio: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    # Max ~500 characters for profile bio
    
    # =============================================
    # Game Statistics
    # =============================================
    games_played: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    
    games_won: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    
    games_lost: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    
    games_abandoned: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    # Left game early / disconnected
    
    # =============================================
    # Ranking (Future Use)
    # =============================================
    rank: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    # e.g., "Bronze", "Silver", "Gold", "Platinum", "Diamond"
    
    elo: Mapped[int] = mapped_column(
        Integer,
        default=1000
    )
    # ELO rating for matchmaking (default 1000)
    
    # =============================================
    # Progression (Future Use)
    # =============================================
    level: Mapped[int] = mapped_column(
        Integer,
        default=1
    )
    
    xp: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    
    # =============================================
    # Achievements & Badges (Future Use)
    # =============================================
    achievements: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        default=dict
    )
    # JSON object storing achievement IDs and unlock dates
    
    # =============================================
    # Timestamps
    # =============================================
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    # =============================================
    # Relationships
    # =============================================
    user = relationship(
        "UserAccount",
        back_populates="profile"
    )
    
    # =============================================
    # Helper Properties
    # =============================================
    @property
    def win_rate(self) -> float:
        """Calculate win rate as a percentage."""
        total = self.games_won + self.games_lost
        if total == 0:
            return 0.0
        return (self.games_won / total) * 100
    
    @property
    def total_games_completed(self) -> int:
        """Total games that reached completion (win or loss)."""
        return self.games_won + self.games_lost
    
    def __repr__(self):
        return f"<PlayerProfile user_id={self.user_id} W:{self.games_won}/L:{self.games_lost}>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'user_id': str(self.user_id),
            'avatar_url': self.avatar_url,
            'bio': self.bio,
            'games_played': self.games_played,
            'games_won': self.games_won,
            'games_lost': self.games_lost,
            'games_abandoned': self.games_abandoned,
            'win_rate': round(self.win_rate, 2),
            'rank': self.rank,
            'elo': self.elo,
            'level': self.level,
            'xp': self.xp,
            'achievements': self.achievements,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def to_stats_dict(self) -> dict:
        """Return just the statistics for API responses."""
        return {
            'games_played': self.games_played,
            'games_won': self.games_won,
            'games_lost': self.games_lost,
            'games_abandoned': self.games_abandoned,
            'win_rate': round(self.win_rate, 2),
            'rank': self.rank,
            'elo': self.elo,
            'level': self.level,
            'xp': self.xp,
        }
