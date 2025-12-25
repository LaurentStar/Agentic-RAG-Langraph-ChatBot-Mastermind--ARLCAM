"""
OAuth Service.

Handles OAuth2 authentication flows for Discord, Google, and Slack.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any
from urllib.parse import urlencode

import httpx

from app.constants import PlayerType, SocialMediaPlatform
from app.extensions import db
from app.models.postgres_sql_db_models import Player, OAuthIdentity
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)


class OAuthService:
    """
    Service for OAuth2 authentication.
    
    Supports:
    - Discord OAuth2
    - Google OAuth2
    - Slack OAuth2
    """
    
    # =============================================
    # Discord OAuth Configuration
    # =============================================
    
    DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
    DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
    DISCORD_REDIRECT_URI = os.getenv(
        "DISCORD_REDIRECT_URI", 
        "http://localhost:5000/auth/oauth/discord/callback"
    )
    DISCORD_AUTH_URL = "https://discord.com/api/oauth2/authorize"
    DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"
    DISCORD_USER_URL = "https://discord.com/api/users/@me"
    
    # =============================================
    # Google OAuth Configuration
    # =============================================
    
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI = os.getenv(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:5000/auth/oauth/google/callback"
    )
    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USER_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    
    # =============================================
    # Slack OAuth Configuration
    # =============================================
    
    SLACK_CLIENT_ID = os.getenv("SLACK_CLIENT_ID", "")
    SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET", "")
    SLACK_REDIRECT_URI = os.getenv(
        "SLACK_REDIRECT_URI",
        "http://localhost:5000/auth/oauth/slack/callback"
    )
    SLACK_AUTH_URL = "https://slack.com/oauth/v2/authorize"
    SLACK_TOKEN_URL = "https://slack.com/api/oauth.v2.access"
    SLACK_USER_URL = "https://slack.com/api/users.identity"
    
    # =============================================
    # Discord OAuth Methods
    # =============================================
    
    @classmethod
    def get_discord_auth_url(cls, state: Optional[str] = None) -> str:
        """
        Generate Discord OAuth2 authorization URL.
        
        Args:
            state: Optional state parameter for CSRF protection
        
        Returns:
            Authorization URL to redirect user to
        """
        params = {
            "client_id": cls.DISCORD_CLIENT_ID,
            "redirect_uri": cls.DISCORD_REDIRECT_URI,
            "response_type": "code",
            "scope": "identify email"
        }
        if state:
            params["state"] = state
        
        return f"{cls.DISCORD_AUTH_URL}?{urlencode(params)}"
    
    @classmethod
    async def handle_discord_callback(cls, code: str) -> Tuple[Optional[Player], Optional[str], Optional[str]]:
        """
        Handle Discord OAuth2 callback.
        
        Args:
            code: Authorization code from Discord
        
        Returns:
            Tuple of (player, access_token, error_message)
        """
        # Exchange code for access token
        token_data = {
            "client_id": cls.DISCORD_CLIENT_ID,
            "client_secret": cls.DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": cls.DISCORD_REDIRECT_URI
        }
        
        try:
            async with httpx.AsyncClient() as client:
                # Get access token
                token_response = await client.post(
                    cls.DISCORD_TOKEN_URL,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if token_response.status_code != 200:
                    logger.error(f"Discord token error: {token_response.text}")
                    return None, None, "Failed to get access token from Discord"
                
                token_json = token_response.json()
                access_token = token_json.get("access_token")
                
                # Get user info
                user_response = await client.get(
                    cls.DISCORD_USER_URL,
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                if user_response.status_code != 200:
                    logger.error(f"Discord user error: {user_response.text}")
                    return None, None, "Failed to get user info from Discord"
                
                user_info = user_response.json()
                
                # Get or create player
                player = cls._get_or_create_player_from_oauth(
                    provider="discord",
                    provider_user_id=user_info["id"],
                    provider_username=user_info.get("username"),
                    provider_email=user_info.get("email"),
                    provider_avatar_url=cls._get_discord_avatar_url(user_info),
                    platform=SocialMediaPlatform.DISCORD
                )
                
                return player, access_token, None
                
        except Exception as e:
            logger.error(f"Discord OAuth error: {e}")
            return None, None, str(e)
    
    @staticmethod
    def _get_discord_avatar_url(user_info: Dict[str, Any]) -> Optional[str]:
        """Build Discord avatar URL from user info."""
        user_id = user_info.get("id")
        avatar = user_info.get("avatar")
        if user_id and avatar:
            return f"https://cdn.discordapp.com/avatars/{user_id}/{avatar}.png"
        return None
    
    # =============================================
    # Google OAuth Methods
    # =============================================
    
    @classmethod
    def get_google_auth_url(cls, state: Optional[str] = None) -> str:
        """
        Generate Google OAuth2 authorization URL.
        
        Args:
            state: Optional state parameter for CSRF protection
        
        Returns:
            Authorization URL to redirect user to
        """
        params = {
            "client_id": cls.GOOGLE_CLIENT_ID,
            "redirect_uri": cls.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline"
        }
        if state:
            params["state"] = state
        
        return f"{cls.GOOGLE_AUTH_URL}?{urlencode(params)}"
    
    @classmethod
    async def handle_google_callback(cls, code: str) -> Tuple[Optional[Player], Optional[str], Optional[str]]:
        """
        Handle Google OAuth2 callback.
        
        Args:
            code: Authorization code from Google
        
        Returns:
            Tuple of (player, access_token, error_message)
        """
        token_data = {
            "client_id": cls.GOOGLE_CLIENT_ID,
            "client_secret": cls.GOOGLE_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": cls.GOOGLE_REDIRECT_URI
        }
        
        try:
            async with httpx.AsyncClient() as client:
                # Get access token
                token_response = await client.post(
                    cls.GOOGLE_TOKEN_URL,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if token_response.status_code != 200:
                    logger.error(f"Google token error: {token_response.text}")
                    return None, None, "Failed to get access token from Google"
                
                token_json = token_response.json()
                access_token = token_json.get("access_token")
                
                # Get user info
                user_response = await client.get(
                    cls.GOOGLE_USER_URL,
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                if user_response.status_code != 200:
                    logger.error(f"Google user error: {user_response.text}")
                    return None, None, "Failed to get user info from Google"
                
                user_info = user_response.json()
                
                # Get or create player
                player = cls._get_or_create_player_from_oauth(
                    provider="google",
                    provider_user_id=user_info["id"],
                    provider_username=user_info.get("name"),
                    provider_email=user_info.get("email"),
                    provider_avatar_url=user_info.get("picture"),
                    platform=SocialMediaPlatform.DEFAULT
                )
                
                return player, access_token, None
                
        except Exception as e:
            logger.error(f"Google OAuth error: {e}")
            return None, None, str(e)
    
    # =============================================
    # Slack OAuth Methods
    # =============================================
    
    @classmethod
    def get_slack_auth_url(cls, state: Optional[str] = None) -> str:
        """
        Generate Slack OAuth2 authorization URL.
        
        Args:
            state: Optional state parameter for CSRF protection
        
        Returns:
            Authorization URL to redirect user to
        """
        params = {
            "client_id": cls.SLACK_CLIENT_ID,
            "redirect_uri": cls.SLACK_REDIRECT_URI,
            "user_scope": "identity.basic,identity.email,identity.avatar"
        }
        if state:
            params["state"] = state
        
        return f"{cls.SLACK_AUTH_URL}?{urlencode(params)}"
    
    @classmethod
    async def handle_slack_callback(cls, code: str) -> Tuple[Optional[Player], Optional[str], Optional[str]]:
        """
        Handle Slack OAuth2 callback.
        
        Args:
            code: Authorization code from Slack
        
        Returns:
            Tuple of (player, access_token, error_message)
        """
        token_data = {
            "client_id": cls.SLACK_CLIENT_ID,
            "client_secret": cls.SLACK_CLIENT_SECRET,
            "code": code,
            "redirect_uri": cls.SLACK_REDIRECT_URI
        }
        
        try:
            async with httpx.AsyncClient() as client:
                # Get access token
                token_response = await client.post(
                    cls.SLACK_TOKEN_URL,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if token_response.status_code != 200:
                    logger.error(f"Slack token error: {token_response.text}")
                    return None, None, "Failed to get access token from Slack"
                
                token_json = token_response.json()
                
                if not token_json.get("ok"):
                    error = token_json.get("error", "Unknown error")
                    logger.error(f"Slack OAuth error: {error}")
                    return None, None, f"Slack error: {error}"
                
                access_token = token_json.get("authed_user", {}).get("access_token")
                user_info = token_json.get("authed_user", {})
                
                # For Slack, we may need to make an additional API call
                # to get full user identity
                identity_response = await client.get(
                    cls.SLACK_USER_URL,
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                if identity_response.status_code == 200:
                    identity_json = identity_response.json()
                    if identity_json.get("ok"):
                        user_info = identity_json.get("user", {})
                
                # Get or create player
                player = cls._get_or_create_player_from_oauth(
                    provider="slack",
                    provider_user_id=user_info.get("id", token_json.get("authed_user", {}).get("id")),
                    provider_username=user_info.get("name"),
                    provider_email=user_info.get("email"),
                    provider_avatar_url=user_info.get("image_192"),
                    platform=SocialMediaPlatform.SLACK
                )
                
                return player, access_token, None
                
        except Exception as e:
            logger.error(f"Slack OAuth error: {e}")
            return None, None, str(e)
    
    # =============================================
    # Player Management
    # =============================================
    
    @classmethod
    def _get_or_create_player_from_oauth(
        cls,
        provider: str,
        provider_user_id: str,
        provider_username: Optional[str],
        provider_email: Optional[str],
        provider_avatar_url: Optional[str],
        platform: SocialMediaPlatform
    ) -> Player:
        """
        Get existing player or create new one from OAuth info.
        
        Args:
            provider: OAuth provider name ("discord", "google", "slack")
            provider_user_id: User ID from the provider
            provider_username: Username from the provider
            provider_email: Email from the provider
            provider_avatar_url: Avatar URL from the provider
            platform: Social media platform enum
        
        Returns:
            Player object
        """
        # Check if OAuth identity already exists
        oauth_identity = OAuthIdentity.query.filter_by(
            provider=provider,
            provider_user_id=provider_user_id
        ).first()
        
        if oauth_identity:
            # Update last login time
            oauth_identity.last_login_at = datetime.now(timezone.utc)
            oauth_identity.provider_username = provider_username
            oauth_identity.provider_email = provider_email
            oauth_identity.provider_avatar_url = provider_avatar_url
            db.session.commit()
            
            logger.info(f"OAuth login: {provider}:{provider_user_id} -> {oauth_identity.player_display_name}")
            return oauth_identity.player
        
        # Create new player with OAuth identity
        # Generate display name from provider username or email
        display_name = cls._generate_display_name(provider, provider_username, provider_email)
        
        # Check if player with this display name exists
        existing_player = Player.query.filter_by(display_name=display_name).first()
        
        if existing_player:
            # Link OAuth identity to existing player
            oauth_identity = OAuthIdentity(
                player_display_name=display_name,
                provider=provider,
                provider_user_id=provider_user_id,
                provider_username=provider_username,
                provider_email=provider_email,
                provider_avatar_url=provider_avatar_url
            )
            db.session.add(oauth_identity)
            db.session.commit()
            
            logger.info(f"OAuth linked: {provider}:{provider_user_id} -> existing player {display_name}")
            return existing_player
        
        # Create new player
        player = Player(
            display_name=display_name,
            social_media_platform_display_name=provider_username or display_name,
            social_media_platform=platform,
            player_type=PlayerType.HUMAN,
            password_hash=None,  # No password for OAuth users
            game_privileges=[]
        )
        db.session.add(player)
        
        # Create OAuth identity
        oauth_identity = OAuthIdentity(
            player_display_name=display_name,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_username=provider_username,
            provider_email=provider_email,
            provider_avatar_url=provider_avatar_url
        )
        db.session.add(oauth_identity)
        
        db.session.commit()
        
        logger.info(f"OAuth new player: {provider}:{provider_user_id} -> {display_name}")
        return player
    
    @staticmethod
    def _generate_display_name(
        provider: str,
        username: Optional[str],
        email: Optional[str]
    ) -> str:
        """Generate a unique display name for a new player."""
        if username:
            base_name = username
        elif email:
            base_name = email.split("@")[0]
        else:
            base_name = f"{provider}_user"
        
        # Clean the name (alphanumeric and underscores only)
        import re
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', base_name)[:20]
        
        # Check if name exists, if so add a suffix
        original_name = clean_name
        counter = 1
        while Player.query.filter_by(display_name=clean_name).first():
            clean_name = f"{original_name}_{counter}"
            counter += 1
        
        return clean_name
    
    # =============================================
    # JWT Token Generation
    # =============================================
    
    @classmethod
    def create_tokens_for_player(cls, player: Player) -> Tuple[str, str]:
        """
        Create JWT access and refresh tokens for a player.
        
        Args:
            player: Player object
        
        Returns:
            Tuple of (access_token, refresh_token)
        """
        access_token = AuthService.create_access_token(player)
        refresh_token = AuthService.create_refresh_token(player)
        return access_token, refresh_token

