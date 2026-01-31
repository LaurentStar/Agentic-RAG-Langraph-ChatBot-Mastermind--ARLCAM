"""
Player Profile CRUD Operations.

Data access layer for player_profile table.
"""

from typing import Optional
from uuid import UUID

from app.crud.base import BaseCRUD
from app.models.postgres_sql_db_models import PlayerProfile
from app.extensions import db


class PlayerProfileCRUD(BaseCRUD[PlayerProfile]):
    """CRUD operations for PlayerProfile."""
    
    model = PlayerProfile
    
    # =============================================
    # Custom Query Methods
    # =============================================
    
    @classmethod
    def get_by_user_id(cls, user_id: UUID) -> Optional[PlayerProfile]:
        """
        Get player profile by user_id.
        
        Args:
            user_id: User account UUID
        
        Returns:
            PlayerProfile or None
        """
        return cls.get_by_id(user_id)
    
    @classmethod
    def create_for_user(cls, user_id: UUID, **kwargs) -> PlayerProfile:
        """
        Create a new profile for a user.
        
        Args:
            user_id: User account UUID
            **kwargs: Optional profile fields (avatar_url, bio, etc.)
        
        Returns:
            Created PlayerProfile
        """
        return cls.create(user_id=user_id, **kwargs)
    
    # =============================================
    # Stats Update Methods
    # =============================================
    
    @classmethod
    def increment_games_played(cls, user_id: UUID) -> Optional[PlayerProfile]:
        """Increment games_played counter."""
        profile = cls.get_by_user_id(user_id)
        if profile:
            profile.games_played += 1
            db.session.commit()
        return profile
    
    @classmethod
    def record_win(cls, user_id: UUID, xp_earned: int = 50) -> Optional[PlayerProfile]:
        """
        Record a game win.
        
        Args:
            user_id: User account UUID
            xp_earned: XP to award (default 50)
        
        Returns:
            Updated PlayerProfile
        """
        profile = cls.get_by_user_id(user_id)
        if profile:
            profile.games_won += 1
            profile.xp += xp_earned
            # Check for level up (simple formula: 100 XP per level)
            new_level = (profile.xp // 100) + 1
            if new_level > profile.level:
                profile.level = new_level
            db.session.commit()
        return profile
    
    @classmethod
    def record_loss(cls, user_id: UUID, xp_earned: int = 10) -> Optional[PlayerProfile]:
        """
        Record a game loss.
        
        Args:
            user_id: User account UUID
            xp_earned: XP to award (default 10)
        
        Returns:
            Updated PlayerProfile
        """
        profile = cls.get_by_user_id(user_id)
        if profile:
            profile.games_lost += 1
            profile.xp += xp_earned
            db.session.commit()
        return profile
    
    @classmethod
    def record_abandon(cls, user_id: UUID) -> Optional[PlayerProfile]:
        """Record an abandoned game (left early)."""
        profile = cls.get_by_user_id(user_id)
        if profile:
            profile.games_abandoned += 1
            db.session.commit()
        return profile
    
    @classmethod
    def update_elo(cls, user_id: UUID, new_elo: int) -> Optional[PlayerProfile]:
        """
        Update ELO rating.
        
        Args:
            user_id: User account UUID
            new_elo: New ELO rating value
        
        Returns:
            Updated PlayerProfile
        """
        return cls.update(user_id, elo=new_elo)
    
    @classmethod
    def update_rank(cls, user_id: UUID, rank: str) -> Optional[PlayerProfile]:
        """
        Update player rank.
        
        Args:
            user_id: User account UUID
            rank: Rank string (e.g., "Gold", "Diamond")
        
        Returns:
            Updated PlayerProfile
        """
        return cls.update(user_id, rank=rank)
    
    # =============================================
    # Profile Update Methods
    # =============================================
    
    @classmethod
    def update_avatar(cls, user_id: UUID, avatar_url: str) -> Optional[PlayerProfile]:
        """Update avatar URL."""
        return cls.update(user_id, avatar_url=avatar_url)
    
    @classmethod
    def update_bio(cls, user_id: UUID, bio: str) -> Optional[PlayerProfile]:
        """Update bio text."""
        return cls.update(user_id, bio=bio)
    
    @classmethod
    def add_achievement(cls, user_id: UUID, achievement_id: str) -> Optional[PlayerProfile]:
        """
        Add an achievement to the profile.
        
        Args:
            user_id: User account UUID
            achievement_id: Achievement identifier
        
        Returns:
            Updated PlayerProfile
        """
        from datetime import datetime, timezone
        
        profile = cls.get_by_user_id(user_id)
        if profile:
            achievements = dict(profile.achievements or {})
            if achievement_id not in achievements:
                achievements[achievement_id] = datetime.now(timezone.utc).isoformat()
                profile.achievements = achievements
                db.session.commit()
        return profile
