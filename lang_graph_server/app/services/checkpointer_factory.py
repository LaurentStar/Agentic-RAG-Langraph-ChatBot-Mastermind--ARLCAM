"""
Checkpointer Factory.

Creates and manages the LangGraph checkpointer for conversation persistence.

Supports:
- PostgresSaver for production (persistent across restarts)
- MemorySaver for development/testing (in-memory only)

The checkpointer is graph-level, not agent-level. Thread IDs provide
isolation between different agents/games:
- Format: "{game_id}:{agent_id}" for single agent
- Format: "{game_id}:broadcast" for broadcast events
"""

import os
from typing import Optional

from langgraph.checkpoint.memory import MemorySaver


class CheckpointerFactory:
    """
    Factory for creating LangGraph checkpointers.
    
    Manages checkpointer lifecycle:
    - Lazy initialization
    - Connection management
    - Fallback to MemorySaver if PostgreSQL unavailable
    
    Usage:
        factory = CheckpointerFactory()
        factory.init_app()  # Initialize with PostgreSQL
        checkpointer = factory.get_checkpointer()  # Get the checkpointer
    """
    
    _checkpointer = None
    _initialized = False
    _use_postgres = False
    
    def init_app(self, connection_string: Optional[str] = None, use_postgres: bool = True) -> None:
        """
        Initialize the checkpointer.
        
        Args:
            connection_string: PostgreSQL connection string.
                              If None, uses DATABASE_URL env var or default.
            use_postgres: If True, attempts PostgresSaver. Falls back to MemorySaver on failure.
        """
        if self._initialized:
            return
        
        self._use_postgres = use_postgres
        
        if use_postgres:
            self._checkpointer = self._create_postgres_checkpointer(connection_string)
        
        # Fallback to MemorySaver
        if self._checkpointer is None:
            print("Using MemorySaver (in-memory checkpointing - data lost on restart)")
            self._checkpointer = MemorySaver()
        
        self._initialized = True
    
    def _create_postgres_checkpointer(self, connection_string: Optional[str] = None):
        """
        Attempt to create a PostgresSaver checkpointer.
        
        Returns None if PostgreSQL is not available or fails.
        """
        try:
            # Try to import PostgresSaver
            from langgraph.checkpoint.postgres import PostgresSaver
        except ImportError:
            print("langgraph-checkpoint-postgres not installed. Install with:")
            print("  pip install langgraph-checkpoint-postgres")
            return None
        
        # Get connection string
        if connection_string is None:
            connection_string = self._build_connection_string()
        
        try:
            # Create PostgresSaver
            checkpointer = PostgresSaver.from_conn_string(connection_string)
            
            # Setup tables if needed
            checkpointer.setup()
            
            print(f"PostgresSaver initialized successfully")
            return checkpointer
            
        except Exception as e:
            print(f"Failed to initialize PostgresSaver: {e}")
            print("Falling back to MemorySaver")
            return None
    
    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string from environment variables."""
        # Check for DATABASE_URL first (common pattern)
        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            return database_url
        
        # Build from individual components (match DatabaseConfig defaults)
        host = os.environ.get("POSTGRES_HOST", "localhost")
        port = os.environ.get("POSTGRES_PORT", "5432")
        database = os.environ.get("POSTGRES_DATABASE", "postgres")
        user = os.environ.get("POSTGRES_USER", "postgres")
        password = os.environ.get("POSTGRES_PASSWORD", "mysecretpassword")
        
        return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}"
    
    def get_checkpointer(self):
        """
        Get the checkpointer instance.
        
        Lazy-initializes with MemorySaver if init_app() wasn't called.
        """
        if not self._initialized:
            # Lazy init with MemorySaver as fallback
            self.init_app(use_postgres=False)
        
        return self._checkpointer
    
    def is_persistent(self) -> bool:
        """Check if using persistent storage (PostgreSQL)."""
        return self._use_postgres and self._checkpointer is not None
    
    def get_status(self) -> dict:
        """Get checkpointer status information."""
        return {
            "initialized": self._initialized,
            "type": "PostgresSaver" if self._use_postgres else "MemorySaver",
            "persistent": self.is_persistent(),
        }
    
    # =============================================
    # Thread ID Helpers
    # =============================================
    
    @staticmethod
    def build_thread_id(game_id: str, agent_id: Optional[str] = None) -> str:
        """
        Build a thread ID for checkpointing.
        
        Args:
            game_id: The game identifier
            agent_id: Agent ID (or None for broadcast)
            
        Returns:
            Thread ID string
        """
        if agent_id:
            return f"{game_id}:{agent_id}"
        return f"{game_id}:broadcast"
    
    @staticmethod
    def parse_thread_id(thread_id: str) -> tuple:
        """
        Parse a thread ID back to game_id and agent_id.
        
        Returns:
            (game_id, agent_id) tuple. agent_id is None for broadcast.
        """
        parts = thread_id.split(":", 1)
        game_id = parts[0]
        agent_id = parts[1] if len(parts) > 1 and parts[1] != "broadcast" else None
        return game_id, agent_id

