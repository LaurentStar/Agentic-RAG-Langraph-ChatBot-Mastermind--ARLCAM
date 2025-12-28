"""
Token Cache Service.

Caches JWT tokens for Discord users who have linked their accounts.
Uses PostgreSQL for persistent caching instead of in-memory.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

import aiohttp
from flask import Flask

from app.extensions import db
from app.database.db_models import TokenCache
from app.utils import requires_flask_db

logger = logging.getLogger("discord_bot")


class TokenCacheService:
    """
    Service for caching and retrieving JWT tokens for Discord users.
    
    Uses PostgreSQL for persistence, avoiding memory issues with many users.
    All database methods use @requires_flask_db decorator for clean code.
    
    Flow:
    1. Discord user runs a command
    2. Check DB cache for valid token
    3. If not cached/expired, call game server to get token
    4. If game server returns 404, user needs to link account
    5. Cache successful tokens in DB for future use
    """
    
    # Cache duration (shorter than actual token lifetime for safety)
    CACHE_DURATION = timedelta(hours=1)
    
    # Game server configuration
    GAME_SERVER_URL = os.getenv("GAME_SERVER_URL", "http://localhost:5000")
    
    # Flask app reference (set during app initialization)
    _app: Optional[Flask] = None
    
    @classmethod
    def init_app(cls, app: Flask) -> None:
        """
        Initialize service with Flask app reference.
        
        Must be called during app creation to enable database access
        from outside Flask's request context.
        """
        cls._app = app
        logger.info("TokenCacheService initialized with Flask app")
    
    # =========================================
    # Public API
    # =========================================
    
    @classmethod
    async def get_token(
        cls,
        discord_user_id: str,
        http_session: Optional[aiohttp.ClientSession] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Get a valid JWT token for a Discord user.
        
        Returns:
            Tuple of (access_token, error_message)
        """
        # Check DB cache first
        cached = cls._get_from_cache(discord_user_id)
        if cached:
            logger.debug(f"Token cache hit for Discord user {discord_user_id}")
            return cached["access_token"], None
        
        # Fetch from game server
        logger.debug(f"Token cache miss for Discord user {discord_user_id}")
        return await cls._fetch_from_game_server(discord_user_id, http_session)
    
    @classmethod
    @requires_flask_db
    def get_cached_player_name(cls, discord_user_id: str) -> Optional[str]:
        """Get cached player display name if available."""
        cached = db.session.get(TokenCache, discord_user_id)
        return cached.player_display_name if cached else None
    
    @classmethod
    @requires_flask_db
    def invalidate(cls, discord_user_id: str) -> None:
        """Remove a user's token from cache."""
        cached = db.session.get(TokenCache, discord_user_id)
        if cached:
            db.session.delete(cached)
            db.session.commit()
            logger.debug(f"Invalidated token cache for Discord user {discord_user_id}")
    
    @classmethod
    @requires_flask_db
    def get_cache_stats(cls) -> Dict[str, int]:
        """Get cache statistics."""
        now = datetime.now(timezone.utc)
        total = db.session.query(TokenCache).count()
        valid = db.session.query(TokenCache).filter(TokenCache.expires_at > now).count()
        return {
            "total_cached": total,
            "valid_tokens": valid,
            "expired_tokens": total - valid
        }
    
    @classmethod
    @requires_flask_db
    def cleanup_expired(cls) -> int:
        """Remove expired tokens from cache. Returns count deleted."""
        now = datetime.now(timezone.utc)
        deleted = db.session.query(TokenCache).filter(
            TokenCache.expires_at <= now
        ).delete()
        db.session.commit()
        logger.info(f"Cleaned up {deleted} expired token cache entries")
        return deleted
    
    @classmethod
    def get_oauth_login_url(cls) -> str:
        """Get the OAuth login URL for users to link their account."""
        return f"{cls.GAME_SERVER_URL}/auth/oauth/login"
    
    # =========================================
    # Private Methods
    # =========================================
    
    @classmethod
    @requires_flask_db
    def _get_from_cache(cls, discord_user_id: str) -> Optional[Dict]:
        """Get token from database cache if valid."""
        cached = db.session.get(TokenCache, discord_user_id)
        
        if not cached:
            return None
        
        # Check if expired
        if cached.is_expired():
            logger.debug(f"Cached token expired for Discord user {discord_user_id}")
            db.session.delete(cached)
            db.session.commit()
            return None
        
        # Return as dict (detached from session)
        return {
            "access_token": cached.access_token,
            "refresh_token": cached.refresh_token,
            "player_display_name": cached.player_display_name,
            "player_type": cached.player_type
        }
    
    @classmethod
    @requires_flask_db
    def _save_to_cache(
        cls,
        discord_user_id: str,
        access_token: str,
        refresh_token: str,
        player_display_name: str,
        player_type: str
    ) -> None:
        """Save token to database cache (upsert)."""
        now = datetime.now(timezone.utc)
        expires_at = now + cls.CACHE_DURATION
        
        existing = db.session.get(TokenCache, discord_user_id)
        
        if existing:
            existing.access_token = access_token
            existing.refresh_token = refresh_token
            existing.player_display_name = player_display_name
            existing.player_type = player_type
            existing.cached_at = now
            existing.expires_at = expires_at
        else:
            cache_entry = TokenCache(
                discord_user_id=discord_user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                player_display_name=player_display_name,
                player_type=player_type,
                cached_at=now,
                expires_at=expires_at
            )
            db.session.add(cache_entry)
        
        db.session.commit()
    
    @classmethod
    async def _fetch_from_game_server(
        cls,
        discord_user_id: str,
        http_session: Optional[aiohttp.ClientSession] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """Fetch token from game server."""
        url = f"{cls.GAME_SERVER_URL}/auth/oauth/token-by-provider"
        payload = {
            "provider": "discord",
            "provider_user_id": discord_user_id
        }
        
        close_session = False
        if http_session is None:
            http_session = aiohttp.ClientSession()
            close_session = True
        
        try:
            async with http_session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Cache the token
                    cls._save_to_cache(
                        discord_user_id=discord_user_id,
                        access_token=data["access_token"],
                        refresh_token=data["refresh_token"],
                        player_display_name=data["player_display_name"],
                        player_type=data.get("player_type", "human")
                    )
                    
                    logger.info(
                        f"Token cached for Discord user {discord_user_id} "
                        f"-> {data['player_display_name']}"
                    )
                    
                    return data["access_token"], None
                
                elif response.status == 404:
                    return None, "not_linked"
                
                else:
                    error_text = await response.text()
                    logger.error(f"Game server error: {response.status} - {error_text}")
                    return None, f"Game server error: {response.status}"
                    
        except aiohttp.ClientError as e:
            logger.error(f"Failed to connect to game server: {e}")
            return None, "Failed to connect to game server"
        except Exception as e:
            logger.error(f"Unexpected error fetching token: {e}")
            return None, str(e)
        finally:
            if close_session:
                await http_session.close()
