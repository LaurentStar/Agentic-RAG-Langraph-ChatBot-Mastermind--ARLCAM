"""
Game Server Client.

HTTP client for lang_graph_server to interact with game_server APIs.
Used by LLM agents to submit game actions and reactions.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.constants import CoupAction, ReactionType


class GameServerClient:
    """
    HTTP client for game_server API.
    
    Handles authentication and provides typed methods for game operations.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0
    ):
        """
        Initialize the client.
        
        Args:
            base_url: Game server URL (default: from env or localhost:5000)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or os.getenv("GAME_SERVER_URL", "http://localhost:5000")
        self.timeout = timeout
        
        # Token management
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        
        # Agent credentials (set per-agent)
        # Note: user_name is used for login, display_name is the public name
        self._agent_user_name: Optional[str] = None
        self._agent_display_name: Optional[str] = None
        self._agent_password: Optional[str] = None
    
    def configure_agent(
        self,
        display_name: str,
        password: str,
        user_name: Optional[str] = None
    ) -> None:
        """
        Configure credentials for an LLM agent.
        
        Args:
            display_name: Agent's display name (public identifier)
            password: Agent's password
            user_name: Agent's login username (defaults to display_name for backwards compat)
        """
        self._agent_display_name = display_name
        # Use user_name if provided, otherwise fall back to display_name
        # (for OAuth users, user_name == display_name)
        self._agent_user_name = user_name or display_name
        self._agent_password = password
        # Clear existing tokens
        self._access_token = None
        self._refresh_token = None
        self._token_expires_at = None
    
    def _get_client(self) -> httpx.Client:
        """Get configured HTTP client."""
        headers = {}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        
        return httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=headers
        )
    
    async def _get_async_client(self) -> httpx.AsyncClient:
        """Get configured async HTTP client."""
        headers = {}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=headers
        )
    
    def _ensure_authenticated(self) -> bool:
        """
        Ensure we have a valid access token.
        
        Returns:
            True if authenticated, False otherwise
        """
        # Check if token is still valid
        if self._access_token and self._token_expires_at:
            if datetime.now(timezone.utc) < self._token_expires_at - timedelta(minutes=5):
                return True
        
        # Try to refresh if we have a refresh token
        if self._refresh_token:
            if self._refresh_access_token():
                return True
        
        # Login with credentials
        if self._agent_user_name and self._agent_password:
            return self._login()
        
        return False
    
    def _login(self) -> bool:
        """Login and get access token."""
        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
                response = client.post(
                    "/auth/login",
                    json={
                        "user_name": self._agent_user_name,
                        "password": self._agent_password
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self._access_token = data.get("access_token")
                    self._refresh_token = data.get("refresh_token")
                    expires_in = data.get("expires_in", 3600)
                    self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                    return True
                else:
                    print(f"[GameServerClient] Login failed: {response.status_code} - {response.text}")
                    return False
                    
        except httpx.HTTPError as e:
            print(f"[GameServerClient] Login error: {e}")
            return False
    
    def _refresh_access_token(self) -> bool:
        """Refresh the access token."""
        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
                response = client.post(
                    "/auth/refresh",
                    json={"refresh_token": self._refresh_token}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self._access_token = data.get("access_token")
                    expires_in = data.get("expires_in", 3600)
                    self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                    return True
                else:
                    return False
                    
        except httpx.HTTPError:
            return False
    
    # =============================================
    # Session Operations
    # =============================================
    
    def list_sessions(self, status: Optional[str] = None) -> Dict[str, Any]:
        """List available game sessions."""
        if not self._ensure_authenticated():
            return {"error": "Not authenticated"}
        
        params = {}
        if status:
            params["status"] = status
        
        with self._get_client() as client:
            response = client.get("/game/sessions", params=params)
            return response.json()
    
    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session details."""
        if not self._ensure_authenticated():
            return {"error": "Not authenticated"}
        
        with self._get_client() as client:
            response = client.get(f"/game/sessions/{session_id}")
            return response.json()
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get detailed session status."""
        if not self._ensure_authenticated():
            return {"error": "Not authenticated"}
        
        with self._get_client() as client:
            response = client.get(f"/game/sessions/{session_id}/status")
            return response.json()
    
    def join_session(self, session_id: str) -> Dict[str, Any]:
        """Join a game session."""
        if not self._ensure_authenticated():
            return {"error": "Not authenticated"}
        
        with self._get_client() as client:
            response = client.post(f"/game/sessions/{session_id}/join", json={})
            return response.json()
    
    def leave_session(self, session_id: str) -> Dict[str, Any]:
        """Leave a game session."""
        if not self._ensure_authenticated():
            return {"error": "Not authenticated"}
        
        with self._get_client() as client:
            response = client.post(f"/game/sessions/{session_id}/leave", json={})
            return response.json()
    
    # =============================================
    # Action Operations
    # =============================================
    
    def get_pending_actions(self, session_id: str) -> Dict[str, Any]:
        """Get all visible pending actions for a session."""
        if not self._ensure_authenticated():
            return {"error": "Not authenticated"}
        
        with self._get_client() as client:
            response = client.get(f"/game/actions/{session_id}")
            return response.json()
    
    def set_action(
        self,
        session_id: str,
        action: CoupAction,
        target_display_name: Optional[str] = None,
        claimed_role: Optional[str] = None,
        upgrade_enabled: bool = False
    ) -> Dict[str, Any]:
        """
        Set pending action for the current turn.
        
        Args:
            session_id: Game session ID
            action: Action to take
            target_display_name: Target player (for targeted actions)
            claimed_role: Role claimed for action
            upgrade_enabled: Whether to use upgrade
        
        Returns:
            Response from game server
        """
        if not self._ensure_authenticated():
            return {"error": "Not authenticated"}
        
        payload = {
            "action": action.value if isinstance(action, CoupAction) else action,
            "upgrade_enabled": upgrade_enabled
        }
        
        if target_display_name:
            payload["target_display_name"] = target_display_name
        if claimed_role:
            payload["claimed_role"] = claimed_role
        
        with self._get_client() as client:
            response = client.post(f"/game/actions/{session_id}", json=payload)
            return response.json()
    
    # =============================================
    # Reaction Operations
    # =============================================
    
    def get_pending_reactions(self, session_id: str) -> Dict[str, Any]:
        """Get pending reactions and actions requiring reaction."""
        if not self._ensure_authenticated():
            return {"error": "Not authenticated"}
        
        with self._get_client() as client:
            response = client.get(f"/game/reactions/{session_id}")
            return response.json()
    
    def set_reaction(
        self,
        session_id: str,
        target_player: str,
        reaction_type: ReactionType,
        block_with_role: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Set reaction to another player's action.
        
        Args:
            session_id: Game session ID
            target_player: Player whose action to react to
            reaction_type: Type of reaction
            block_with_role: Role claimed for blocking
        
        Returns:
            Response from game server
        """
        if not self._ensure_authenticated():
            return {"error": "Not authenticated"}
        
        payload = {
            "target_player": target_player,
            "reaction_type": reaction_type.value if isinstance(reaction_type, ReactionType) else reaction_type
        }
        
        if block_with_role:
            payload["block_with_role"] = block_with_role
        
        with self._get_client() as client:
            response = client.post(f"/game/reactions/{session_id}", json=payload)
            return response.json()
    
    def select_cards(
        self,
        session_id: str,
        cards: List[str]
    ) -> Dict[str, Any]:
        """
        Select cards for reveal or exchange.
        
        Args:
            session_id: Game session ID
            cards: List of card names to select
        
        Returns:
            Response from game server
        """
        if not self._ensure_authenticated():
            return {"error": "Not authenticated"}
        
        with self._get_client() as client:
            response = client.post(
                f"/game/reactions/{session_id}/cards",
                json={"cards": cards}
            )
            return response.json()
    
    # =============================================
    # Game State
    # =============================================
    
    def get_game_state(self, session_id: str) -> Dict[str, Any]:
        """
        Get current game state.
        
        Returns full game state including:
        - Current phase and time remaining
        - All players' public info (coins, card count, pending actions)
        - Agent's own cards (private)
        - Revealed cards
        """
        if not self._ensure_authenticated():
            return {"error": "Not authenticated"}
        
        with self._get_client() as client:
            response = client.get(f"/game/state/{session_id}")
            return response.json()
    
    # =============================================
    # Chat Operations
    # =============================================
    
    def send_chat_message(self, session_id: str, content: str) -> Dict[str, Any]:
        """
        Send a chat message as this agent.
        
        Messages are queued and broadcast to all platforms every 5 minutes.
        
        Args:
            session_id: Game session ID
            content: Message content (max 2000 chars)
        
        Returns:
            Response dict with message details or error
        """
        if not self._ensure_authenticated():
            return {"error": "Not authenticated"}
        
        with self._get_client() as client:
            response = client.post(
                f"/game/chat/{session_id}/send",
                json={"content": content}
            )
            return response.json()
    
    def get_pending_chat_messages(self, session_id: str) -> Dict[str, Any]:
        """
        Get pending chat messages for a session.
        
        Useful for seeing what messages are queued before broadcast.
        
        Args:
            session_id: Game session ID
        
        Returns:
            Response dict with message list
        """
        if not self._ensure_authenticated():
            return {"error": "Not authenticated"}
        
        with self._get_client() as client:
            response = client.get(f"/game/chat/{session_id}/messages")
            return response.json()


class GameServerClientFactory:
    """
    Factory for creating per-agent GameServerClient instances.
    
    Follows the init_app pattern used throughout the application.
    Declared in extensions.py, initialized in __init__.py.
    """
    
    def __init__(self):
        """Declare the factory (not yet initialized)."""
        self._base_url: Optional[str] = None
        self._initialized: bool = False
        self._clients: Dict[str, GameServerClient] = {}  # Cache clients by agent_id
    
    def init_app(self, base_url: Optional[str] = None) -> None:
        """
        Initialize the factory with game server configuration.
        
        Args:
            base_url: Game server URL (default: from env or localhost:5000)
        """
        self._base_url = base_url or os.getenv("GAME_SERVER_URL", "http://localhost:5000")
        self._initialized = True
    
    def create_client(self, agent_id: str, password: str) -> GameServerClient:
        """
        Create a GameServerClient for a specific agent.
        
        Args:
            agent_id: Agent's display name
            password: Agent's password
        
        Returns:
            Configured GameServerClient
        """
        if not self._initialized:
            # Auto-initialize with defaults if not explicitly initialized
            self.init_app()
        
        client = GameServerClient(base_url=self._base_url)
        client.configure_agent(agent_id, password)
        
        # Cache the client
        self._clients[agent_id] = client
        
        return client
    
    def get_client(self, agent_id: str) -> Optional[GameServerClient]:
        """
        Get an existing client for an agent.
        
        Args:
            agent_id: Agent's display name
        
        Returns:
            Cached GameServerClient or None if not created
        """
        return self._clients.get(agent_id)
    
    def get_or_create_client(self, agent_id: str, password: str) -> GameServerClient:
        """
        Get existing client or create a new one.
        
        Args:
            agent_id: Agent's display name
            password: Agent's password
        
        Returns:
            GameServerClient (cached or newly created)
        """
        existing = self.get_client(agent_id)
        if existing:
            return existing
        return self.create_client(agent_id, password)
    
    def get_status(self) -> Dict[str, Any]:
        """Get factory status for logging/debugging."""
        return {
            "initialized": self._initialized,
            "base_url": self._base_url,
            "active_clients": len(self._clients),
            "client_ids": list(self._clients.keys())
        }

