"""
Database Connection Manager.

Manages connections to the game server's PostgreSQL database.
The lang_graph_server has READ-ONLY access to query:
- Player pending actions
- Agent profiles
- Game state

WRITE operations (updating pending actions) should go through
the game server's API, not direct DB access.
"""

import os
from contextlib import contextmanager
from typing import Optional, Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool


class DatabaseConfig:
    """Database configuration loaded from environment variables."""
    
    # Default values match game_server configuration
    DEFAULT_HOST = "localhost"
    DEFAULT_PORT = "5432"
    DEFAULT_DATABASE = "postgres"      # Changed from "player"
    DEFAULT_USER = "postgres"          # Changed from "player_manager"
    DEFAULT_PASSWORD = "mysecretpassword"  # Changed from "pm_manager1"
    
    @classmethod
    def get_connection_string(cls) -> str:
        """Build PostgreSQL connection string from environment or defaults."""
        host = os.environ.get("POSTGRES_HOST", cls.DEFAULT_HOST)
        port = os.environ.get("POSTGRES_PORT", cls.DEFAULT_PORT)
        database = os.environ.get("POSTGRES_DATABASE", cls.DEFAULT_DATABASE)
        user = os.environ.get("POSTGRES_USER", cls.DEFAULT_USER)
        password = os.environ.get("POSTGRES_PASSWORD", cls.DEFAULT_PASSWORD)
        
        return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}"


class DatabaseConnection:
    """
    Singleton database connection manager.
    
    Provides connection pooling and session management for
    read-only access to the game server's PostgreSQL database.
    """
    
    _instance: Optional["DatabaseConnection"] = None
    _engine = None
    _session_factory = None
    
    def __new__(cls) -> "DatabaseConnection":
        """Singleton pattern - only one connection manager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def init_app(self, connection_string: Optional[str] = None) -> None:
        """
        Initialize the database connection.
        
        Args:
            connection_string: Optional custom connection string.
                              Uses environment/defaults if not provided.
        """
        if self._initialized:
            return
        
        conn_str = connection_string or DatabaseConfig.get_connection_string()
        
        self._engine = create_engine(
            conn_str,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,  # Recycle connections after 30 minutes
            echo=False,  # Set to True for SQL debugging
        )
        
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
        )
        
        self._initialized = True
    
    @property
    def engine(self):
        """Get the SQLAlchemy engine."""
        if not self._initialized:
            self.init_app()
        return self._engine
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a database session with automatic cleanup.
        
        Usage:
            with db.get_session() as session:
                result = session.execute(query)
        """
        if not self._initialized:
            self.init_app()
        
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def test_connection(self) -> bool:
        """Test if the database connection is working."""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            print(f"Database connection test failed: {e}")
            return False
    
    def close(self) -> None:
        """Close all connections and dispose of the engine."""
        if self._engine:
            self._engine.dispose()
            self._initialized = False


# Global instance is declared in app/extensions.py
# Initialize via: db_connection.init_app() in app/__init__.py

