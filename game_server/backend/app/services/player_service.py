"""
Player Service.

Handles player registration, retrieval, and management.
"""

from typing import List, Optional

from app.constants import GamePrivilege, PlayerStatus, PlayerType, SocialMediaPlatform
from app.extensions import db
from app.models.postgres_sql_db_models import AgentProfile, Player
from app.services.auth_service import AuthService


class PlayerService:
    """Service for player management."""
    
    @staticmethod
    def register_player(
        display_name: str,
        password: str,
        social_media_platform_display_name: str,
        platform: SocialMediaPlatform,
        player_type: PlayerType = PlayerType.HUMAN,
        game_privileges: Optional[List[GamePrivilege]] = None
    ) -> Player:
        """
        Register a new player.
        
        Args:
            display_name: Unique player identifier
            password: Plain text password (will be hashed)
            social_media_platform_display_name: Username on platform
            platform: Platform enum value (added to platforms list and set as preferred)
            player_type: Type of player (human, llm_agent, admin)
            game_privileges: List of privileges for non-admin players
        
        Returns:
            Created Player object
        
        Raises:
            ValueError: If player already exists
        """
        # Check if player exists
        existing = Player.query.filter_by(display_name=display_name).first()
        if existing:
            raise ValueError(f"Player '{display_name}' already exists")
        
        # Create player with platform loyalty fields
        player = Player(
            display_name=display_name,
            password_hash=AuthService.hash_password(password),
            social_media_platform_display_name=social_media_platform_display_name,
            social_media_platforms=[platform],
            preferred_social_media_platform=platform,
            player_type=player_type,
            game_privileges=game_privileges or [],
            player_statuses=[PlayerStatus.WAITING],
            coins=2,
            card_types=[],
            to_be_initiated=[]
        )
        
        db.session.add(player)
        db.session.commit()
        
        return player
    
    @staticmethod
    def register_llm_agent(
        display_name: str,
        password: str,
        social_media_platform_display_name: str,
        platform: SocialMediaPlatform,
        personality_type: str = "balanced",
        modulators: Optional[dict] = None
    ) -> Player:
        """
        Register a new LLM agent with profile.
        
        Args:
            display_name: Unique agent identifier
            password: API key or password for agent authentication
            social_media_platform_display_name: Bot username on platform
            platform: Platform enum value
            personality_type: Agent personality style
            modulators: Dict of modulator values (aggression, bluff_confidence, etc.)
        
        Returns:
            Created Player object with AgentProfile
        """
        # Create player first
        player = PlayerService.register_player(
            display_name=display_name,
            password=password,
            social_media_platform_display_name=social_media_platform_display_name,
            platform=platform,
            player_type=PlayerType.LLM_AGENT
        )
        
        # Create agent profile
        mods = modulators or {}
        agent_profile = AgentProfile(
            display_name=display_name,
            personality_type=personality_type,
            aggression=mods.get('aggression', 0.5),
            bluff_confidence=mods.get('bluff_confidence', 0.5),
            challenge_tendency=mods.get('challenge_tendency', 0.5),
            block_tendency=mods.get('block_tendency', 0.5),
            risk_tolerance=mods.get('risk_tolerance', 0.5),
            llm_reliance=mods.get('llm_reliance', 0.5),
            model_name=mods.get('model_name', 'gpt-4'),
            temperature=mods.get('temperature', 0.7)
        )
        
        db.session.add(agent_profile)
        db.session.commit()
        
        return player
    
    @staticmethod
    def get_player(display_name: str) -> Optional[Player]:
        """Get a player by display name."""
        return Player.query.filter_by(display_name=display_name).first()
    
    @staticmethod
    def get_player_or_404(display_name: str) -> Player:
        """Get a player by display name or raise 404."""
        player = PlayerService.get_player(display_name)
        if not player:
            raise ValueError(f"Player '{display_name}' not found")
        return player
    
    @staticmethod
    def authenticate(display_name: str, password: str) -> Optional[Player]:
        """
        Authenticate a player with display name and password.
        
        Returns:
            Player if authentication successful, None otherwise
        """
        player = PlayerService.get_player(display_name)
        if not player or not player.password_hash:
            return None
        
        if AuthService.verify_password(password, player.password_hash):
            return player
        
        return None
    
    @staticmethod
    def list_players(
        player_type: Optional[PlayerType] = None,
        session_id: Optional[str] = None,
        is_alive: Optional[bool] = None
    ) -> List[Player]:
        """
        List players with optional filters.
        
        Args:
            player_type: Filter by player type
            session_id: Filter by game session
            is_alive: Filter by alive status
        
        Returns:
            List of matching players
        """
        query = Player.query
        
        if player_type:
            query = query.filter_by(player_type=player_type)
        
        if session_id:
            query = query.filter_by(session_id=session_id)
        
        if is_alive is not None:
            if is_alive:
                query = query.filter(Player.player_statuses.contains([PlayerStatus.ALIVE]))
            else:
                query = query.filter(Player.player_statuses.contains([PlayerStatus.DEAD]))
        
        return query.all()
    
    @staticmethod
    def update_player(
        display_name: str,
        **updates
    ) -> Player:
        """
        Update player fields.
        
        Args:
            display_name: Player to update
            **updates: Fields to update
        
        Returns:
            Updated Player object
        """
        player = PlayerService.get_player_or_404(display_name)
        
        allowed_fields = {
            'social_media_platform_display_name',
            'preferred_social_media_platform',
            'game_privileges'
        }
        
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(player, field, value)
            # Add new platform to list if setting preferred
            elif field == 'preferred_social_media_platform' and value:
                platforms = list(player.social_media_platforms or [])
                if value not in platforms:
                    platforms.append(value)
                    player.social_media_platforms = platforms
        
        db.session.commit()
        return player
    
    @staticmethod
    def delete_player(display_name: str) -> bool:
        """
        Delete a player.
        
        Returns:
            True if deleted, False if not found
        """
        player = PlayerService.get_player(display_name)
        if not player:
            return False
        
        db.session.delete(player)
        db.session.commit()
        return True
    
    @staticmethod
    def grant_privilege(display_name: str, privilege: GamePrivilege) -> Player:
        """Grant a privilege to a player."""
        player = PlayerService.get_player_or_404(display_name)
        
        current_privileges = list(player.game_privileges or [])
        if privilege not in current_privileges:
            current_privileges.append(privilege)
            player.game_privileges = current_privileges
            db.session.commit()
        
        return player
    
    @staticmethod
    def revoke_privilege(display_name: str, privilege: GamePrivilege) -> Player:
        """Revoke a privilege from a player."""
        player = PlayerService.get_player_or_404(display_name)
        
        current_privileges = list(player.game_privileges or [])
        if privilege in current_privileges:
            current_privileges.remove(privilege)
            player.game_privileges = current_privileges
            db.session.commit()
        
        return player

