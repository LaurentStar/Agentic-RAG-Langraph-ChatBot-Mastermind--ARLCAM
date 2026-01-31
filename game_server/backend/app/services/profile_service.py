"""
Profile Service.

Handles player profile operations (stats, avatar, bio).
Uses PlayerProfileCRUD for data access.
"""

from typing import Optional
from uuid import UUID

from app.crud import PlayerProfileCRUD, UserAccountCRUD
from app.models.postgres_sql_db_models import PlayerProfile


class ProfileService:
    """Service for player profile management."""
    
    @classmethod
    def get_by_user_id(cls, user_id: UUID) -> Optional[PlayerProfile]:
        """Get profile by user ID."""
        return PlayerProfileCRUD.get_by_user_id(user_id)
    
    @classmethod
    def get_or_404(cls, user_id: UUID) -> PlayerProfile:
        """Get profile by user ID or raise ValueError."""
        profile = cls.get_by_user_id(user_id)
        if not profile:
            raise ValueError(f"Profile not found for user: {user_id}")
        return profile
    
    @classmethod
    def get_by_identifier(cls, identifier: str) -> Optional[PlayerProfile]:
        """
        Get profile by user_name or display_name.
        
        Args:
            identifier: User name or display name
        
        Returns:
            PlayerProfile or None
        """
        # Look up user first
        user = UserAccountCRUD.get_by_user_name(identifier)
        if not user:
            user = UserAccountCRUD.get_by_display_name(identifier)
        
        if not user:
            return None
        
        return PlayerProfileCRUD.get_by_user_id(user.user_id)
    
    @classmethod
    def update_profile(
        cls,
        user_id: UUID,
        avatar_url: Optional[str] = None,
        bio: Optional[str] = None
    ) -> PlayerProfile:
        """
        Update profile fields (avatar, bio).
        
        Args:
            user_id: User ID
            avatar_url: New avatar URL
            bio: New bio text
        
        Returns:
            Updated PlayerProfile
        
        Raises:
            ValueError: If profile not found or validation fails
        """
        profile = cls.get_or_404(user_id)
        
        updates = {}
        
        if avatar_url is not None:
            # Could add URL validation here
            updates['avatar_url'] = avatar_url
        
        if bio is not None:
            # Validate bio length
            if len(bio) > 500:
                raise ValueError("Bio must be 500 characters or less")
            updates['bio'] = bio
        
        if updates:
            return PlayerProfileCRUD.update(user_id, **updates)
        
        return profile
