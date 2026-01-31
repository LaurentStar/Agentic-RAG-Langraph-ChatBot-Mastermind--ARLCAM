"""
User Account ORM Model.

SQLAlchemy model for user identity and authentication.
This is the permanent account record - identity, auth, and account status.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID, ARRAY, ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import GamePrivilege, PlayerType, SocialMediaPlatform
from app.extensions import db


class AccountStatus:
    """Account status constants."""
    ACTIVE = 'active'
    SUSPENDED = 'suspended'
    BANNED = 'banned'
    DEACTIVATED = 'deactivated'


class UserAccount(db.Model):
    """
    User Account table ORM model.
    
    Permanent account data - identity, authentication, and account status.
    This table owns the user_id which is the FK for all other user-related tables.
    """
    
    __bind_key__ = 'db_players'
    __tablename__ = 'gs_user_account_table_orm'
    
    # =============================================
    # Identity
    # =============================================
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    user_name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    # Login identifier - human-readable, rarely changes
    
    display_name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )
    # Public-facing name - what other players see
    
    # =============================================
    # Contact & Verification
    # =============================================
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True
    )
    
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )
    
    # =============================================
    # Authentication
    # =============================================
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    # Nullable for OAuth-only accounts
    
    token_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False
    )
    # Increment to invalidate all active sessions/tokens for this user
    
    # =============================================
    # Account Status
    # =============================================
    account_status: Mapped[str] = mapped_column(
        String(20),
        default=AccountStatus.ACTIVE,
        nullable=False,
        index=True
    )
    # Values: active, suspended, banned, deactivated
    
    # =============================================
    # Player Type & Privileges
    # =============================================
    player_type: Mapped[PlayerType] = mapped_column(
        ENUM(PlayerType, name="player_type_enum", create_type=True),
        default=PlayerType.HUMAN
    )
    
    game_privileges: Mapped[List[GamePrivilege]] = mapped_column(
        ARRAY(ENUM(GamePrivilege, name="game_privilege_enum", create_type=True)),
        default=[]
    )
    
    # =============================================
    # Platform Loyalty (from original player table)
    # =============================================
    social_media_platforms: Mapped[List[SocialMediaPlatform]] = mapped_column(
        ARRAY(ENUM(SocialMediaPlatform, name="social_media_platform_enum", create_type=True)),
        default=[]
    )
    
    preferred_social_media_platform: Mapped[Optional[SocialMediaPlatform]] = mapped_column(
        ENUM(SocialMediaPlatform, name="social_media_platform_enum", create_type=True),
        nullable=True
    )
    
    social_media_platform_display_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    # Display name on the social media platform (may differ from game display_name)
    
    # =============================================
    # Timestamps
    # =============================================
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # =============================================
    # Relationships
    # =============================================
    profile = relationship(
        "PlayerProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    game_states = relationship(
        "PlayerGameState",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    agent_profile = relationship(
        "AgentProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    oauth_identities = relationship(
        "OAuthIdentity",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    account_flags = relationship(
        "AccountFlag",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    link_requests = relationship(
        "AccountLinkRequest",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    # =============================================
    # Helper Properties
    # =============================================
    @property
    def is_active(self) -> bool:
        """Check if account is active."""
        return self.account_status == AccountStatus.ACTIVE
    
    @property
    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.player_type == PlayerType.ADMIN
    
    @property
    def is_agent(self) -> bool:
        """Check if user is an LLM agent."""
        return self.player_type == PlayerType.LLM_AGENT
    
    def has_privilege(self, privilege: GamePrivilege) -> bool:
        """Check if user has a specific privilege."""
        if self.is_admin:
            return True
        return privilege in (self.game_privileges or [])
    
    @property
    def platform_count(self) -> int:
        """Number of platforms registered on."""
        return len(self.social_media_platforms or [])
    
    @property
    def is_multi_platform(self) -> bool:
        """True if registered on 2+ platforms."""
        return self.platform_count >= 2
    
    def has_platform(self, platform: SocialMediaPlatform) -> bool:
        """Check if user has registered on a specific platform."""
        return platform in (self.social_media_platforms or [])
    
    def __repr__(self):
        return f"<UserAccount {self.user_name} ({self.display_name}) [{self.account_status}]>"
    
    def to_dict(self, include_private: bool = False) -> dict:
        """Convert to dictionary."""
        result = {
            'user_id': str(self.user_id),
            'user_name': self.user_name,
            'display_name': self.display_name,
            'player_type': self.player_type.value if self.player_type else None,
            'social_media_platforms': [p.value for p in (self.social_media_platforms or [])],
            'preferred_social_media_platform': self.preferred_social_media_platform.value if self.preferred_social_media_platform else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_private:
            result['email'] = self.email
            result['email_verified'] = self.email_verified
            result['account_status'] = self.account_status
            result['game_privileges'] = [p.value for p in (self.game_privileges or [])]
            result['last_login_at'] = self.last_login_at.isoformat() if self.last_login_at else None
        
        return result
