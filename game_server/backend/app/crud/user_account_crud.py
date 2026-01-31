"""
User Account CRUD Operations.

Data access layer for user_account table.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from app.crud.base import BaseCRUD
from app.models.postgres_sql_db_models import UserAccount
from app.constants import PlayerType, SocialMediaPlatform


class UserAccountCRUD(BaseCRUD[UserAccount]):
    """CRUD operations for UserAccount."""
    
    model = UserAccount
    
    # =============================================
    # Custom Query Methods
    # =============================================
    
    @classmethod
    def get_by_user_id(cls, user_id: UUID) -> Optional[UserAccount]:
        """Get user account by user_id (alias for get_by_id)."""
        return cls.get_by_id(user_id)
    
    @classmethod
    def get_by_user_name(cls, user_name: str) -> Optional[UserAccount]:
        """
        Get user account by login username.
        
        Args:
            user_name: Login username (case-insensitive)
        
        Returns:
            UserAccount or None
        """
        return cls.model.query.filter(
            cls.model.user_name.ilike(user_name)
        ).first()
    
    @classmethod
    def get_by_display_name(cls, display_name: str) -> Optional[UserAccount]:
        """
        Get user account by display name.
        
        Args:
            display_name: Public display name
        
        Returns:
            UserAccount or None
        """
        return cls.model.query.filter_by(display_name=display_name).first()
    
    @classmethod
    def get_by_email(cls, email: str) -> Optional[UserAccount]:
        """
        Get user account by email.
        
        Args:
            email: Email address (case-insensitive)
        
        Returns:
            UserAccount or None
        """
        return cls.model.query.filter(
            cls.model.email.ilike(email)
        ).first()
    
    @classmethod
    def get_by_player_type(cls, player_type: PlayerType) -> List[UserAccount]:
        """
        Get all accounts of a specific player type.
        
        Args:
            player_type: PlayerType enum value
        
        Returns:
            List of matching accounts
        """
        return cls.model.query.filter_by(player_type=player_type).all()
    
    @classmethod
    def get_active_accounts(cls) -> List[UserAccount]:
        """Get all active (non-suspended/banned) accounts."""
        return cls.model.query.filter_by(account_status='active').all()
    
    @classmethod
    def get_admins(cls) -> List[UserAccount]:
        """Get all admin accounts."""
        return cls.get_by_player_type(PlayerType.ADMIN)
    
    @classmethod
    def get_agents(cls) -> List[UserAccount]:
        """Get all LLM agent accounts."""
        return cls.get_by_player_type(PlayerType.LLM_AGENT)
    
    # =============================================
    # Validation Methods
    # =============================================
    
    @classmethod
    def user_name_exists(cls, user_name: str) -> bool:
        """Check if a username is already taken."""
        return cls.get_by_user_name(user_name) is not None
    
    @classmethod
    def display_name_exists(cls, display_name: str) -> bool:
        """Check if a display name is already taken."""
        return cls.get_by_display_name(display_name) is not None
    
    @classmethod
    def email_exists(cls, email: str) -> bool:
        """Check if an email is already registered."""
        if not email:
            return False
        return cls.get_by_email(email) is not None
    
    # =============================================
    # Update Methods
    # =============================================
    
    @classmethod
    def update_last_login(cls, user_id: UUID) -> Optional[UserAccount]:
        """Update the last login timestamp for a user."""
        return cls.update(user_id, last_login_at=datetime.now(timezone.utc))
    
    @classmethod
    def update_password(cls, user_id: UUID, password_hash: str) -> Optional[UserAccount]:
        """Update the password hash for a user."""
        return cls.update(user_id, password_hash=password_hash)
    
    @classmethod
    def update_email(cls, user_id: UUID, email: str, verified: bool = False) -> Optional[UserAccount]:
        """Update email and verification status."""
        return cls.update(user_id, email=email, email_verified=verified)
    
    @classmethod
    def verify_email(cls, user_id: UUID) -> Optional[UserAccount]:
        """Mark email as verified."""
        return cls.update(user_id, email_verified=True)
    
    @classmethod
    def suspend_account(cls, user_id: UUID) -> Optional[UserAccount]:
        """Suspend an account."""
        return cls.update(user_id, account_status='suspended')
    
    @classmethod
    def ban_account(cls, user_id: UUID) -> Optional[UserAccount]:
        """Ban an account."""
        return cls.update(user_id, account_status='banned')
    
    @classmethod
    def activate_account(cls, user_id: UUID) -> Optional[UserAccount]:
        """Reactivate a suspended/deactivated account."""
        return cls.update(user_id, account_status='active')
    
    @classmethod
    def add_platform(cls, user_id: UUID, platform: SocialMediaPlatform) -> Optional[UserAccount]:
        """Add a platform to user's registered platforms."""
        user = cls.get_by_id(user_id)
        if not user:
            return None
        
        platforms = list(user.social_media_platforms or [])
        if platform not in platforms:
            platforms.append(platform)
            return cls.update(user_id, social_media_platforms=platforms)
        return user
