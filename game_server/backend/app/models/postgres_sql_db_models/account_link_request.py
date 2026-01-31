"""
Account Link Request ORM Model.

SQLAlchemy model for storing pending account link requests
that require email confirmation from both providers.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import ForeignKey, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class AccountLinkRequest(db.Model):
    """
    Account Link Request table ORM model.
    
    Stores pending link requests awaiting email confirmation.
    Both emails must be confirmed for the link to be established.
    Requests expire after 24 hours.
    """
    
    __bind_key__ = 'db_players'
    __tablename__ = 'gs_account_link_request_table_orm'
    
    # ---------------------- Identity ---------------------- #
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # ---------------------- User Link ---------------------- #
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gs_user_account_table_orm.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # ---------------------- Target Provider ---------------------- #
    target_provider: Mapped[str] = mapped_column(String(20), nullable=False)
    # Provider to link: "discord", "google", "slack"
    
    target_email: Mapped[str] = mapped_column(String(255), nullable=False)
    # Email address for the target provider account
    
    # ---------------------- Confirmation Tokens ---------------------- #
    token_primary: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True
    )
    # Token sent to user's existing/primary email
    
    token_secondary: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True
    )
    # Token sent to target provider email
    
    # ---------------------- Confirmation Status ---------------------- #
    primary_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    # True when primary email link has been clicked
    
    secondary_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    # True when secondary email link has been clicked
    
    # ---------------------- Timestamps ---------------------- #
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc) + timedelta(hours=24),
        index=True
    )
    
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    # Set when both confirmations received and link established
    
    # ---------------------- Relationships ---------------------- #
    user = relationship("UserAccount", back_populates="link_requests")
    
    # ---------------------- Helper Properties ---------------------- #
    @property
    def is_expired(self) -> bool:
        """Check if request has expired."""
        return datetime.now(timezone.utc) >= self.expires_at
    
    @property
    def is_complete(self) -> bool:
        """Check if both emails have been confirmed."""
        return self.primary_confirmed and self.secondary_confirmed
    
    @property
    def is_pending(self) -> bool:
        """Check if request is still pending (not expired, not complete)."""
        return not self.is_expired and not self.completed_at
    
    def __repr__(self):
        status = "complete" if self.is_complete else ("expired" if self.is_expired else "pending")
        return f"<AccountLinkRequest user={self.user_id} -> {self.target_provider} [{status}]>"
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'target_provider': self.target_provider,
            'target_email': self.target_email,
            'primary_confirmed': self.primary_confirmed,
            'secondary_confirmed': self.secondary_confirmed,
            'is_complete': self.is_complete,
            'is_expired': self.is_expired,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
