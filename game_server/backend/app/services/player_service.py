"""
Player Service.

Handles player game state management within sessions.
For account operations, use UserAccountService instead.

This service is transitioning from the old Player model to the new
three-tier architecture (UserAccount, PlayerProfile, PlayerGameState).
"""

from typing import List, Optional
from uuid import UUID

from app.constants import GamePrivilege, PlayerStatus, PlayerType, SocialMediaPlatform
from app.crud import UserAccountCRUD, PlayerProfileCRUD, PlayerGameStateCRUD
from app.models.postgres_sql_db_models import UserAccount, PlayerGameState
from app.services.auth_service import AuthService
from app.services.user_account_service import UserAccountService


class PlayerService:
    """
    Service for player management.
    
    NOTE: This service is being refactored. For account operations,
    use UserAccountService. This service now focuses on game state.
    """
    
    # =============================================
    # Account Operations (Delegated to UserAccountService)
    # =============================================
    
    @staticmethod
    def register_player(
        display_name: str,
        password: str,
        social_media_platform_display_name: str,
        platform: SocialMediaPlatform,
        player_type: PlayerType = PlayerType.HUMAN,
        game_privileges: Optional[List[GamePrivilege]] = None
    ) -> UserAccount:
        """
        Register a new player.
        
        DEPRECATED: Use UserAccountService.register() instead.
        This method is kept for backward compatibility.
        """
        # Generate user_name from display_name
        user_name = display_name.lower().replace(' ', '_')
        
        return UserAccountService.register(
            user_name=user_name,
            display_name=display_name,
            password=password,
            platform=platform,
            platform_display_name=social_media_platform_display_name,
            player_type=player_type,
            game_privileges=game_privileges
        )
    
    @staticmethod
    def register_llm_agent(
        display_name: str,
        password: str,
        social_media_platform_display_name: str,
        platform: SocialMediaPlatform,
        personality_type: str = "balanced",
        modulators: Optional[dict] = None
    ) -> UserAccount:
        """
        Register a new LLM agent with profile.
        
        DEPRECATED: Use UserAccountService.register_agent() instead.
        """
        user_name = display_name.lower().replace(' ', '_')
        
        return UserAccountService.register_agent(
            user_name=user_name,
            display_name=display_name,
            password=password,
            platform=platform,
            personality_type=personality_type,
            modulators=modulators
        )
    
    @staticmethod
    def get_player(display_name: str) -> Optional[UserAccount]:
        """
        Get a player by display name.
        
        NOTE: Returns UserAccount now, not legacy Player model.
        """
        return UserAccountCRUD.get_by_display_name(display_name)
    
    @staticmethod
    def get_player_by_id(user_id: UUID) -> Optional[UserAccount]:
        """Get a player by user_id."""
        return UserAccountCRUD.get_by_id(user_id)
    
    @staticmethod
    def get_player_or_404(display_name: str) -> UserAccount:
        """Get a player by display name or raise error."""
        user = PlayerService.get_player(display_name)
        if not user:
            raise ValueError(f"Player '{display_name}' not found")
        return user
    
    @staticmethod
    def authenticate(display_name: str, password: str) -> Optional[UserAccount]:
        """
        Authenticate a player with display name and password.
        
        NOTE: For new code, use AuthService.authenticate() with user_name instead.
        This method is kept for backward compatibility during transition.
        """
        # First try display_name as user_name
        user = AuthService.authenticate(display_name, password)
        if user:
            return user
        
        # Then try finding by display_name and authenticating
        user = UserAccountCRUD.get_by_display_name(display_name)
        if user and user.password_hash and user.is_active:
            if AuthService.verify_password(password, user.password_hash):
                UserAccountCRUD.update_last_login(user.user_id)
                return user
        
        return None
    
    @staticmethod
    def list_players(
        player_type: Optional[PlayerType] = None,
        session_id: Optional[str] = None,
        is_alive: Optional[bool] = None
    ) -> List[UserAccount]:
        """
        List players with optional filters.
        
        NOTE: When session_id is provided, this now queries game state
        and returns the associated user accounts.
        """
        if session_id:
            # Get game states for session, return associated accounts
            game_states = PlayerGameStateCRUD.get_by_session(session_id)
            
            if is_alive is not None:
                if is_alive:
                    game_states = [gs for gs in game_states if gs.is_alive]
                else:
                    game_states = [gs for gs in game_states if gs.is_dead]
            
            # Get associated user accounts
            users = []
            for gs in game_states:
                user = UserAccountCRUD.get_by_id(gs.user_id)
                if user and (player_type is None or user.player_type == player_type):
                    users.append(user)
            return users
        
        if player_type:
            return UserAccountCRUD.get_by_player_type(player_type)
        
        return UserAccountCRUD.get_active_accounts()
    
    @staticmethod
    def update_player(display_name: str, **updates) -> UserAccount:
        """Update player fields."""
        user = PlayerService.get_player_or_404(display_name)
        
        allowed_fields = {
            'social_media_platform_display_name',
            'preferred_social_media_platform',
            'game_privileges'
        }
        
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if filtered_updates:
            return UserAccountCRUD.update(user.user_id, **filtered_updates)
        return user
    
    @staticmethod
    def delete_player(display_name: str) -> bool:
        """Delete a player."""
        user = PlayerService.get_player(display_name)
        if not user:
            return False
        
        return UserAccountCRUD.delete(user.user_id)
    
    @staticmethod
    def grant_privilege(display_name: str, privilege: GamePrivilege) -> UserAccount:
        """Grant a privilege to a player."""
        user = PlayerService.get_player_or_404(display_name)
        return UserAccountService.grant_privilege(user.user_id, privilege)
    
    @staticmethod
    def revoke_privilege(display_name: str, privilege: GamePrivilege) -> UserAccount:
        """Revoke a privilege from a player."""
        user = PlayerService.get_player_or_404(display_name)
        return UserAccountService.revoke_privilege(user.user_id, privilege)
    
    # =============================================
    # Game State Operations
    # =============================================
    
    @staticmethod
    def get_game_state(user_id: UUID, session_id: str) -> Optional[PlayerGameState]:
        """Get a player's game state in a specific session."""
        return PlayerGameStateCRUD.get_by_user_and_session(user_id, session_id)
    
    @staticmethod
    def get_active_game_state(user_id: UUID) -> Optional[PlayerGameState]:
        """Get a player's active game state (if in a session)."""
        return PlayerGameStateCRUD.get_active_for_user(user_id)
    
    @staticmethod
    def join_session(user_id: UUID, session_id: str, starting_coins: int = 2) -> PlayerGameState:
        """Create a game state for a player joining a session."""
        # Check if already in this session
        existing = PlayerGameStateCRUD.get_by_user_and_session(user_id, session_id)
        if existing:
            return existing
        
        return PlayerGameStateCRUD.create_for_session(user_id, session_id, starting_coins)
    
    @staticmethod
    def leave_session(user_id: UUID, session_id: str) -> bool:
        """Remove a player from a session."""
        game_state = PlayerGameStateCRUD.get_by_user_and_session(user_id, session_id)
        if game_state:
            PlayerGameStateCRUD.leave_session(game_state.id)
            return True
        return False
    
    @staticmethod
    def get_session_players(session_id: str, alive_only: bool = False) -> List[PlayerGameState]:
        """Get all players in a session."""
        if alive_only:
            return PlayerGameStateCRUD.get_alive_players(session_id)
        return PlayerGameStateCRUD.get_by_session(session_id)
