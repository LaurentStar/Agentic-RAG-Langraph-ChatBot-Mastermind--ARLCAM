"""
OAuth Identity ORM Model.

SQLAlchemy model for storing OAuth provider identities linked to user accounts.
Supports Discord, Google, and Slack OAuth providers.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import ForeignKey, String, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class OAuthIdentity(db.Model):
    """
    OAuth Identity table ORM model.
    
    Links external OAuth provider accounts to user accounts.
    A user can have multiple OAuth identities (one per provider).
    """
    
    __bind_key__ = 'db_players'
    __tablename__ = 'gs_oauth_identity_table_orm'
    
    # ---------------------- Identity ---------------------- #
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # ---------------------- User Link ---------------------- #
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gs_user_account_table_orm.user_id", ondelete="CASCADE"),
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
    
    # ---------------------- Soft Delete ---------------------- #
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        index=True
    )
    # When set, identity is soft-deleted with 7-day grace period for restoration
    
    # ---------------------- Relationships ---------------------- #
    user = relationship("UserAccount", back_populates="oauth_identities")
    
    # ---------------------- Unique Constraint ---------------------- #
    __table_args__ = (
        db.UniqueConstraint('provider', 'provider_user_id', name='uix_provider_user'),
    )
    
    # ---------------------- Helper Properties ---------------------- #
    @property
    def is_deleted(self) -> bool:
        """Check if identity is soft-deleted."""
        return self.deleted_at is not None
    
    @property
    def is_active(self) -> bool:
        """Check if identity is active (not deleted)."""
        return self.deleted_at is None
    
    def __repr__(self):
        status = " [DELETED]" if self.is_deleted else ""
        return f"<OAuthIdentity {self.provider}:{self.provider_user_id} -> {self.user_id}{status}>"
    
    def to_dict(self, include_deleted: bool = False):
        """Convert to dictionary."""
        result = {
            'id': self.id,
            'user_id': str(self.user_id),
            'provider': self.provider,
            'provider_user_id': self.provider_user_id,
            'provider_username': self.provider_username,
            'provider_email': self.provider_email,
            'provider_avatar_url': self.provider_avatar_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'is_active': self.is_active
        }
        if include_deleted:
            result['deleted_at'] = self.deleted_at.isoformat() if self.deleted_at else None
        return result
