"""
User Account Service.

Handles user registration, account management, and authentication logic.
Uses UserAccountCRUD and PlayerProfileCRUD for data access.
"""

from typing import List, Optional
from uuid import UUID

from app.constants import GamePrivilege, PlayerType, SocialMediaPlatform
from app.crud import UserAccountCRUD, PlayerProfileCRUD, AgentProfileCRUD
from app.models.postgres_sql_db_models import UserAccount, PlayerProfile, AgentProfile
from app.services.auth_service import AuthService
from app.extensions import db


class UserAccountService:
    """Service for user account management."""
    
    @classmethod
    def register(
        cls,
        user_name: str,
        display_name: str,
        password: str,
        platform: SocialMediaPlatform = SocialMediaPlatform.DEFAULT,
        platform_display_name: Optional[str] = None,
        email: Optional[str] = None,
        player_type: PlayerType = PlayerType.HUMAN,
        game_privileges: Optional[List[GamePrivilege]] = None
    ) -> UserAccount:
        """
        Register a new user account.
        
        Creates both UserAccount and PlayerProfile records.
        
        Args:
            user_name: Unique login identifier
            display_name: Unique public display name
            password: Plain text password (will be hashed)
            platform: Registration platform
            platform_display_name: Username on the platform
            email: Optional email address
            player_type: Type of player (human, llm_agent, admin)
            game_privileges: List of privileges for non-admin players
        
        Returns:
            Created UserAccount object
        
        Raises:
            ValueError: If user_name, display_name, or email already exists
        """
        # Validate uniqueness
        if UserAccountCRUD.user_name_exists(user_name):
            raise ValueError(f"Username '{user_name}' is already taken")
        
        if UserAccountCRUD.display_name_exists(display_name):
            raise ValueError(f"Display name '{display_name}' is already taken")
        
        if email and UserAccountCRUD.email_exists(email):
            raise ValueError(f"Email '{email}' is already registered")
        
        # Create user account
        user = UserAccountCRUD.create_no_commit(
            user_name=user_name,
            display_name=display_name,
            password_hash=AuthService.hash_password(password),
            email=email,
            player_type=player_type,
            game_privileges=game_privileges or [],
            social_media_platforms=[platform],
            preferred_social_media_platform=platform,
            social_media_platform_display_name=platform_display_name or display_name
        )
        
        # Flush to ensure user_id is generated before creating profile
        db.session.flush()
        
        # Create player profile
        PlayerProfileCRUD.create_no_commit(user_id=user.user_id)
        
        # Commit both together
        db.session.commit()
        
        return user
    
    @classmethod
    def register_oauth(
        cls,
        user_name: str,
        display_name: str,
        platform: SocialMediaPlatform,
        platform_display_name: Optional[str] = None,
        email: Optional[str] = None
    ) -> UserAccount:
        """
        Register a new user via OAuth (no password required).
        
        Creates both UserAccount and PlayerProfile records.
        
        Args:
            user_name: Unique login identifier
            display_name: Unique public display name
            platform: Registration platform
            platform_display_name: Username on the platform
            email: Optional email address from OAuth provider
        
        Returns:
            Created UserAccount object
        
        Raises:
            ValueError: If user_name, display_name, or email already exists
        """
        # Validate uniqueness
        if UserAccountCRUD.user_name_exists(user_name):
            raise ValueError(f"Username '{user_name}' is already taken")
        
        if UserAccountCRUD.display_name_exists(display_name):
            raise ValueError(f"Display name '{display_name}' is already taken")
        
        if email and UserAccountCRUD.email_exists(email):
            raise ValueError(f"Email '{email}' is already registered")
        
        # Create user account (no password for OAuth users)
        user = UserAccountCRUD.create_no_commit(
            user_name=user_name,
            display_name=display_name,
            password_hash=None,  # OAuth users don't have passwords
            email=email,
            email_verified=True if email else False,  # OAuth emails are verified
            player_type=PlayerType.HUMAN,
            game_privileges=[],
            social_media_platforms=[platform],
            preferred_social_media_platform=platform,
            social_media_platform_display_name=platform_display_name or display_name
        )
        
        # Flush to ensure user_id is generated before creating profile
        db.session.flush()
        
        # Create player profile
        PlayerProfileCRUD.create_no_commit(user_id=user.user_id)
        
        # Commit both together
        db.session.commit()
        
        return user
    
    @classmethod
    def add_platform(cls, user_id: UUID, platform: SocialMediaPlatform) -> bool:
        """
        Add a platform to user's registered platforms.
        
        Args:
            user_id: User to update
            platform: Platform to add
        
        Returns:
            True if platform was added, False if already present
        """
        user = cls.get_or_404(user_id)
        current_platforms = list(user.social_media_platforms or [])
        
        if platform not in current_platforms:
            current_platforms.append(platform)
            UserAccountCRUD.update(user_id, social_media_platforms=current_platforms)
            return True
        
        return False
    
    @classmethod
    def register_agent(
        cls,
        user_name: str,
        display_name: str,
        password: str,
        platform: SocialMediaPlatform = SocialMediaPlatform.DEFAULT,
        personality_type: str = "balanced",
        modulators: Optional[dict] = None,
        model_name: str = "gpt-4",
        temperature: float = 0.7
    ) -> UserAccount:
        """
        Register a new LLM agent with profile.
        
        Args:
            user_name: Unique login identifier
            display_name: Unique public display name
            password: API key or password for agent authentication
            platform: Registration platform
            personality_type: Agent personality style
            modulators: Dict of modulator values
            model_name: LLM model to use
            temperature: LLM temperature setting
        
        Returns:
            Created UserAccount object with AgentProfile
        """
        # Create account first
        user = cls.register(
            user_name=user_name,
            display_name=display_name,
            password=password,
            platform=platform,
            player_type=PlayerType.LLM_AGENT
        )
        
        # Create agent profile
        mods = modulators or {}
        AgentProfileCRUD.create(
            user_id=user.user_id,
            personality_type=personality_type,
            aggression=mods.get('aggression', 0.5),
            bluff_confidence=mods.get('bluff_confidence', 0.5),
            challenge_tendency=mods.get('challenge_tendency', 0.5),
            block_tendency=mods.get('block_tendency', 0.5),
            risk_tolerance=mods.get('risk_tolerance', 0.5),
            llm_reliance=mods.get('llm_reliance', 0.5),
            model_name=model_name,
            temperature=temperature
        )
        
        return user
    
    @classmethod
    def get_by_id(cls, user_id: UUID) -> Optional[UserAccount]:
        """Get user by UUID."""
        return UserAccountCRUD.get_by_id(user_id)
    
    @classmethod
    def get_by_user_name(cls, user_name: str) -> Optional[UserAccount]:
        """Get user by login username."""
        return UserAccountCRUD.get_by_user_name(user_name)
    
    @classmethod
    def get_by_display_name(cls, display_name: str) -> Optional[UserAccount]:
        """Get user by display name."""
        return UserAccountCRUD.get_by_display_name(display_name)
    
    @classmethod
    def get_by_email(cls, email: str) -> Optional[UserAccount]:
        """Get user by email."""
        return UserAccountCRUD.get_by_email(email)
    
    @classmethod
    def get_or_404(cls, user_id: UUID) -> UserAccount:
        """Get user by ID or raise ValueError."""
        user = cls.get_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")
        return user
    
    @classmethod
    def list_users(
        cls,
        player_type: Optional[PlayerType] = None,
        account_status: str = 'active'
    ) -> List[UserAccount]:
        """
        List users with optional filters.
        
        Args:
            player_type: Filter by player type
            account_status: Filter by account status
        
        Returns:
            List of matching users
        """
        if player_type:
            return UserAccountCRUD.get_by_player_type(player_type)
        return UserAccountCRUD.get_active_accounts()
    
    @classmethod
    def update_profile(
        cls,
        user_id: UUID,
        display_name: Optional[str] = None,
        email: Optional[str] = None,
        preferred_platform: Optional[SocialMediaPlatform] = None
    ) -> UserAccount:
        """
        Update user profile fields.
        
        Args:
            user_id: User to update
            display_name: New display name (must be unique)
            email: New email (must be unique)
            preferred_platform: New preferred platform
        
        Returns:
            Updated UserAccount
        """
        user = cls.get_or_404(user_id)
        updates = {}
        
        if display_name and display_name != user.display_name:
            if UserAccountCRUD.display_name_exists(display_name):
                raise ValueError(f"Display name '{display_name}' is already taken")
            updates['display_name'] = display_name
        
        if email and email != user.email:
            if UserAccountCRUD.email_exists(email):
                raise ValueError(f"Email '{email}' is already registered")
            updates['email'] = email
            updates['email_verified'] = False
        
        if preferred_platform:
            updates['preferred_social_media_platform'] = preferred_platform
            # Add to platforms list if not present
            platforms = list(user.social_media_platforms or [])
            if preferred_platform not in platforms:
                platforms.append(preferred_platform)
                updates['social_media_platforms'] = platforms
        
        if updates:
            return UserAccountCRUD.update(user_id, **updates)
        return user
    
    @classmethod
    def change_password(cls, user_id: UUID, new_password: str) -> UserAccount:
        """Change a user's password."""
        password_hash = AuthService.hash_password(new_password)
        return UserAccountCRUD.update_password(user_id, password_hash)
    
    @classmethod
    def grant_privilege(cls, user_id: UUID, privilege: GamePrivilege) -> UserAccount:
        """Grant a privilege to a user."""
        user = cls.get_or_404(user_id)
        
        current_privileges = list(user.game_privileges or [])
        if privilege not in current_privileges:
            current_privileges.append(privilege)
            return UserAccountCRUD.update(user_id, game_privileges=current_privileges)
        return user
    
    @classmethod
    def revoke_privilege(cls, user_id: UUID, privilege: GamePrivilege) -> UserAccount:
        """Revoke a privilege from a user."""
        user = cls.get_or_404(user_id)
        
        current_privileges = list(user.game_privileges or [])
        if privilege in current_privileges:
            current_privileges.remove(privilege)
            return UserAccountCRUD.update(user_id, game_privileges=current_privileges)
        return user
    
    @classmethod
    def suspend(cls, user_id: UUID) -> UserAccount:
        """Suspend a user account."""
        return UserAccountCRUD.suspend_account(user_id)
    
    @classmethod
    def ban(cls, user_id: UUID) -> UserAccount:
        """Ban a user account."""
        return UserAccountCRUD.ban_account(user_id)
    
    @classmethod
    def activate(cls, user_id: UUID) -> UserAccount:
        """Reactivate a suspended/deactivated account."""
        return UserAccountCRUD.activate_account(user_id)
    
    @classmethod
    def delete(cls, user_id: UUID) -> bool:
        """Delete a user account and all associated data."""
        return UserAccountCRUD.delete(user_id)
    
    @classmethod
    def invalidate_all_sessions(cls, user_id: UUID) -> bool:
        """
        Invalidate all active sessions for a user.
        
        Increments token_version, which causes all existing JWTs
        to fail validation (even if not expired).
        
        Use cases:
        - Password change
        - Security breach suspected
        - User requests "log out everywhere"
        
        Args:
            user_id: The user's UUID
        
        Returns:
            True if successful, False if user not found
        """
        user = UserAccountCRUD.get_by_id(user_id)
        if not user:
            return False
        
        user.token_version = (user.token_version or 0) + 1
        db.session.commit()
        
        return True
