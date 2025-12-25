"""
OAuth Identity ORM Model.

SQLAlchemy model for storing OAuth provider identities linked to players.
Supports Discord, Google, and Slack OAuth providers.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import ForeignKey, String, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class OAuthIdentity(db.Model):
    """
    OAuth Identity table ORM model.
    
    Links external OAuth provider accounts to player accounts.
    A player can have multiple OAuth identities (one per provider).
    """
    
    __bind_key__ = 'db_players'
    __tablename__ = 'oauth_identity'
    
    # ---------------------- Identity ---------------------- #
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # ---------------------- Player Link ---------------------- #
    player_display_name: Mapped[str] = mapped_column(
        ForeignKey("player_table_orm.display_name"),
        nullable=False,
        index=True
    )
    
    # ---------------------- Provider Info ---------------------- #
    provider: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # Provider options: "discord", "google", "slack"
    
    provider_user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    # Unique user ID from the OAuth provider
    
    provider_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Display name from the OAuth provider (e.g., Discord username)
    
    provider_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Email from the OAuth provider (if available)
    
    provider_avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # Avatar/profile picture URL from the provider
    
    # ---------------------- Timestamps ---------------------- #
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # ---------------------- Relationships ---------------------- #
    player = relationship("Player", back_populates="oauth_identities")
    
    # ---------------------- Unique Constraint ---------------------- #
    __table_args__ = (
        db.UniqueConstraint('provider', 'provider_user_id', name='uix_provider_user'),
    )
    
    def __repr__(self):
        return f"<OAuthIdentity {self.provider}:{self.provider_user_id} -> {self.player_display_name}>"
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'player_display_name': self.player_display_name,
            'provider': self.provider,
            'provider_user_id': self.provider_user_id,
            'provider_username': self.provider_username,
            'provider_email': self.provider_email,
            'provider_avatar_url': self.provider_avatar_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None
        }

