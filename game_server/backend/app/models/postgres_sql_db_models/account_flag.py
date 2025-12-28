"""
Account Flag ORM Model.

SQLAlchemy model for storing internal flags for developer review.
Used to flag potentially suspicious account activity like similar usernames.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import ForeignKey, String, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class AccountFlag(db.Model):
    """
    Account Flag table ORM model.
    
    Internal flags for developer review. These are NOT user-facing.
    Used to track suspicious account patterns that may need investigation.
    """
    
    __bind_key__ = 'db_players'
    __tablename__ = 'account_flag'
    
    # ---------------------- Identity ---------------------- #
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # ---------------------- Flagged Player ---------------------- #
    player_display_name: Mapped[str] = mapped_column(
        ForeignKey("player_table_orm.display_name"),
        nullable=False,
        index=True
    )
    
    # ---------------------- Flag Details ---------------------- #
    flag_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # Flag types: "similar_username", "rapid_creation", "suspicious_linking", etc.
    
    related_player: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Display name of related/similar account (if applicable)
    
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Additional context as JSON (e.g., similarity score, timestamps)
    
    # ---------------------- Review Status ---------------------- #
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True
    )
    # Status options: "pending", "reviewed", "dismissed", "actioned"
    
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Admin who reviewed this flag
    
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Notes from the reviewing admin
    
    # ---------------------- Timestamps ---------------------- #
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True
    )
    
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # ---------------------- Relationships ---------------------- #
    player = relationship("Player", backref="account_flags")
    
    # ---------------------- Helper Properties ---------------------- #
    @property
    def is_pending(self) -> bool:
        """Check if flag is still pending review."""
        return self.status == "pending"
    
    def __repr__(self):
        return f"<AccountFlag {self.id}: {self.flag_type} for {self.player_display_name} [{self.status}]>"
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'player_display_name': self.player_display_name,
            'flag_type': self.flag_type,
            'related_player': self.related_player,
            'details': self.details,
            'status': self.status,
            'reviewed_by': self.reviewed_by,
            'review_notes': self.review_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None
        }

