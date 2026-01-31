"""
Profile Sync Service.

Syncs LLM agent profiles/configurations from PostgreSQL.

Agent profiles include:
- Display name and identity
- Personality traits
- Play style
- Modulators (aggression, bluff_confidence, etc.)

The profile sync:
- Called on game/hour start
- Can be triggered manually
- Caches profiles to reduce DB load
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from app.database.models import UserAccount, PlayerGameState
from app.constants import (
    AgentModulator,
    PLAY_STYLE_MODULATORS,
    PERSONALITIES,
)
from app.models.graph_state_models.coup_agent_state import AgentProfile


class ProfileCache:
    """Simple in-memory cache for agent profiles."""
    
    def __init__(self, ttl_seconds: int = 300):
        """Initialize cache with TTL (default 5 minutes)."""
        self._cache: Dict[str, Dict] = {}
        self._timestamps: Dict[str, datetime] = {}
        self._ttl = timedelta(seconds=ttl_seconds)
    
    def get(self, key: str) -> Optional[Dict]:
        """Get cached profile if not expired."""
        if key not in self._cache:
            return None
        
        if datetime.now() - self._timestamps[key] > self._ttl:
            del self._cache[key]
            del self._timestamps[key]
            return None
        
        return self._cache[key]
    
    def set(self, key: str, value: Dict) -> None:
        """Cache a profile."""
        self._cache[key] = value
        self._timestamps[key] = datetime.now()
    
    def invalidate(self, key: str) -> None:
        """Remove a profile from cache."""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
    
    def clear(self) -> None:
        """Clear all cached profiles."""
        self._cache.clear()
        self._timestamps.clear()


class ProfileSyncService:
    """
    Service for syncing agent profiles from PostgreSQL.
    
    Profiles are cached to reduce database load.
    """
    
    _cache = ProfileCache(ttl_seconds=300)
    
    @classmethod
    def get_profile_from_db(cls, display_name: str) -> Optional[Tuple[UserAccount, PlayerGameState]]:
        """Fetch player data from database (returns user account and game state)."""
        from app.services.pending_events_db_service import PendingEventsDBService
        return PendingEventsDBService.get_player(display_name)
    
    @classmethod
    def build_agent_profile(
        cls,
        display_name: str,
        play_style: str = "balanced",
        personality: str = "friendly",
        custom_modulators: Optional[Dict[AgentModulator, float]] = None,
    ) -> AgentProfile:
        """Build an AgentProfile from parameters."""
        # Get base modulators from play style
        modulators = PLAY_STYLE_MODULATORS.get(
            play_style.lower(), 
            PLAY_STYLE_MODULATORS["balanced"]
        ).copy()
        
        # Apply custom overrides
        if custom_modulators:
            modulators.update(custom_modulators)
        
        # Get personality description
        personality_desc = PERSONALITIES.get(
            personality.lower(),
            personality
        )
        
        return AgentProfile(
            agent_name=display_name,
            agent_play_style=play_style,
            agent_personality=personality_desc,
            agent_modulators=modulators,
        )
    
    @classmethod
    def sync_profile(
        cls,
        display_name: str,
        play_style: str = "balanced",
        personality: str = "friendly",
        force_refresh: bool = False,
    ) -> Optional[AgentProfile]:
        """Sync an agent's profile, using cache when available."""
        cache_key = f"profile:{display_name}"
        
        if not force_refresh:
            cached = cls._cache.get(cache_key)
            if cached:
                return cached
        
        try:
            player_data = cls.get_profile_from_db(display_name)
        except Exception as e:
            print(f"Failed to fetch profile for {display_name}: {e}")
            player_data = None
        
        if player_data:
            user, game_state = player_data
            profile = cls.build_agent_profile(
                display_name=user.display_name,
                play_style=play_style,
                personality=personality,
            )
        else:
            profile = cls.build_agent_profile(
                display_name=display_name,
                play_style=play_style,
                personality=personality,
            )
        
        cls._cache.set(cache_key, profile)
        return profile
    
    @classmethod
    def sync_agent(cls, agent, force_refresh: bool = False) -> bool:
        """Sync profile for a BaseCoupAgent."""
        profile = cls.sync_profile(
            display_name=agent.agent_id,
            play_style=agent.play_style,
            personality=agent.personality,
            force_refresh=force_refresh,
        )
        
        if profile:
            agent.update_profile(profile)
            return True
        return False
    
    @classmethod
    def sync_all_agents_in_registry(cls, game_id: str, force_refresh: bool = False) -> int:
        """Sync profiles for all agents in a game."""
        from app.extensions import agent_registry
        
        agents = agent_registry.get_all_agents_in_game(game_id)
        synced = 0
        
        for agent in agents:
            if cls.sync_agent(agent, force_refresh):
                synced += 1
        
        return synced
    
    @classmethod
    def invalidate_cache(cls, display_name: Optional[str] = None) -> None:
        """Invalidate cached profiles."""
        if display_name:
            cls._cache.invalidate(f"profile:{display_name}")
        else:
            cls._cache.clear()
    
    @classmethod
    def get_available_play_styles(cls) -> List[str]:
        """Get list of available play styles."""
        return list(PLAY_STYLE_MODULATORS.keys())
    
    @classmethod
    def get_available_personalities(cls) -> List[str]:
        """Get list of available personalities."""
        return list(PERSONALITIES.keys())

