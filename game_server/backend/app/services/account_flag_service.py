"""
Account Flag Service.

Service for managing internal account flags for developer review.
These flags are NOT user-facing - they're for dev team to review
potentially suspicious account activity.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from difflib import SequenceMatcher

from app.extensions import db
from app.models.postgres_sql_db_models import AccountFlag, UserAccount
from app.crud import UserAccountCRUD

logger = logging.getLogger(__name__)


class AccountFlagService:
    """
    Service for managing account flags.
    
    Account flags are internal markers for developer review.
    They help identify potentially suspicious patterns like:
    - Similar usernames (possible duplicate accounts)
    - Rapid account creation
    - Suspicious linking patterns
    """
    
    # =============================================
    # Flag Creation
    # =============================================
    
    @classmethod
    def flag_similar_username(
        cls,
        new_player_name: str,
        existing_player_name: str,
        similarity_score: float,
        details: Optional[Dict[str, Any]] = None
    ) -> AccountFlag:
        """
        Create a flag for similar usernames.
        
        Args:
            new_player_name: Display name of the new player
            existing_player_name: Display name of the similar existing player
            similarity_score: Similarity ratio (0.0 to 1.0)
            details: Additional context
        
        Returns:
            Created AccountFlag
        """
        flag_details = details or {}
        flag_details["similarity_score"] = round(similarity_score, 3)
        
        flag = AccountFlag(
            player_display_name=new_player_name,
            flag_type="similar_username",
            related_player=existing_player_name,
            details=flag_details,
            status="pending"
        )
        
        db.session.add(flag)
        db.session.commit()
        
        logger.info(
            f"Created similar_username flag: {new_player_name} ~ "
            f"{existing_player_name} (score: {similarity_score:.2f})"
        )
        
        return flag
    
    @classmethod
    def flag_suspicious_linking(
        cls,
        player_name: str,
        details: Dict[str, Any]
    ) -> AccountFlag:
        """
        Create a flag for suspicious account linking patterns.
        
        Args:
            player_name: Display name of the player
            details: Details about the suspicious activity
        
        Returns:
            Created AccountFlag
        """
        flag = AccountFlag(
            player_display_name=player_name,
            flag_type="suspicious_linking",
            details=details,
            status="pending"
        )
        
        db.session.add(flag)
        db.session.commit()
        
        logger.info(f"Created suspicious_linking flag for {player_name}")
        
        return flag
    
    @classmethod
    def flag_rapid_creation(
        cls,
        player_name: str,
        details: Dict[str, Any]
    ) -> AccountFlag:
        """
        Create a flag for rapid account creation.
        
        Args:
            player_name: Display name of the player
            details: Details about the rapid creation pattern
        
        Returns:
            Created AccountFlag
        """
        flag = AccountFlag(
            player_display_name=player_name,
            flag_type="rapid_creation",
            details=details,
            status="pending"
        )
        
        db.session.add(flag)
        db.session.commit()
        
        logger.info(f"Created rapid_creation flag for {player_name}")
        
        return flag
    
    # =============================================
    # Flag Retrieval
    # =============================================
    
    @classmethod
    def get_pending_flags(
        cls,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[AccountFlag], int]:
        """
        Get all pending flags for review.
        
        Args:
            limit: Maximum number of flags to return
            offset: Number of flags to skip
        
        Returns:
            Tuple of (flags list, total count)
        """
        query = AccountFlag.query.filter_by(status="pending")
        total = query.count()
        
        flags = query.order_by(AccountFlag.created_at.desc()) \
            .offset(offset) \
            .limit(limit) \
            .all()
        
        return flags, total
    
    @classmethod
    def get_flags_by_status(
        cls,
        status: str,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[AccountFlag], int]:
        """
        Get flags by status.
        
        Args:
            status: Flag status ("pending", "reviewed", "dismissed", "actioned")
            limit: Maximum number of flags to return
            offset: Number of flags to skip
        
        Returns:
            Tuple of (flags list, total count)
        """
        query = AccountFlag.query.filter_by(status=status)
        total = query.count()
        
        flags = query.order_by(AccountFlag.created_at.desc()) \
            .offset(offset) \
            .limit(limit) \
            .all()
        
        return flags, total
    
    @classmethod
    def get_flags_for_player(cls, player_name: str) -> List[AccountFlag]:
        """
        Get all flags for a specific player.
        
        Args:
            player_name: Display name of the player
        
        Returns:
            List of AccountFlag objects
        """
        return AccountFlag.query.filter_by(
            player_display_name=player_name
        ).order_by(AccountFlag.created_at.desc()).all()
    
    @classmethod
    def get_flag_by_id(cls, flag_id: int) -> Optional[AccountFlag]:
        """
        Get a specific flag by ID.
        
        Args:
            flag_id: The flag ID
        
        Returns:
            AccountFlag or None
        """
        return db.session.get(AccountFlag, flag_id)
    
    # =============================================
    # Flag Review
    # =============================================
    
    @classmethod
    def review_flag(
        cls,
        flag_id: int,
        action: str,
        admin_name: str,
        notes: Optional[str] = None
    ) -> Tuple[Optional[AccountFlag], Optional[str]]:
        """
        Review and update a flag's status.
        
        Args:
            flag_id: The flag ID to review
            action: The review action ("reviewed", "dismissed", "actioned")
            admin_name: Name of the admin performing the review
            notes: Optional review notes
        
        Returns:
            Tuple of (updated flag, error message)
        """
        valid_actions = {"reviewed", "dismissed", "actioned"}
        if action not in valid_actions:
            return None, f"Invalid action. Must be one of: {valid_actions}"
        
        flag = db.session.get(AccountFlag, flag_id)
        if not flag:
            return None, f"Flag {flag_id} not found"
        
        flag.status = action
        flag.reviewed_by = admin_name
        flag.reviewed_at = datetime.now(timezone.utc)
        
        if notes:
            flag.review_notes = notes
        
        db.session.commit()
        
        logger.info(f"Flag {flag_id} {action} by {admin_name}")
        
        return flag, None
    
    # =============================================
    # Similar Username Detection
    # =============================================
    
    @classmethod
    def find_similar_usernames(
        cls,
        username: str,
        threshold: float = 0.8
    ) -> List[Tuple[UserAccount, float]]:
        """
        Find players with similar usernames.
        
        Args:
            username: Username to compare
            threshold: Minimum similarity ratio (0.0 to 1.0)
        
        Returns:
            List of (user, similarity_score) tuples
        """
        similar_users = []
        all_users = UserAccountCRUD.get_active_accounts()
        
        username_lower = username.lower()
        
        for user in all_users:
            if user.display_name.lower() == username_lower:
                continue
            
            # Compare against display name
            ratio1 = SequenceMatcher(
                None,
                username_lower,
                user.display_name.lower()
            ).ratio()
            
            # Compare against social media display name
            sm_name = user.social_media_platform_display_name or ""
            ratio2 = SequenceMatcher(
                None,
                username_lower,
                sm_name.lower()
            ).ratio() if sm_name else 0
            
            max_ratio = max(ratio1, ratio2)
            
            if max_ratio >= threshold:
                similar_users.append((user, max_ratio))
        
        # Sort by similarity (highest first)
        similar_users.sort(key=lambda x: x[1], reverse=True)
        
        return similar_users
    
    # =============================================
    # Statistics
    # =============================================
    
    @classmethod
    def get_flag_stats(cls) -> Dict[str, int]:
        """
        Get statistics about account flags.
        
        Returns:
            Dictionary with flag counts by status
        """
        stats = {}
        
        for status in ["pending", "reviewed", "dismissed", "actioned"]:
            stats[status] = AccountFlag.query.filter_by(status=status).count()
        
        stats["total"] = sum(stats.values())
        
        return stats

