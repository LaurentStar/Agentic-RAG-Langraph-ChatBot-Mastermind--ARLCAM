"""
Logging Service.

Handles database logging of commands, messages, and errors.

Uses a standalone SQLAlchemy engine to work outside Flask's application context.
This is necessary because Discord.py's event loop runs independently of Flask.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import sessionmaker, declarative_base

from app.constants import LogType

logger = logging.getLogger(__name__)


# ============================================================================
# STANDALONE DATABASE CONNECTION
# ============================================================================
# This engine is independent of Flask-SQLAlchemy and can be used from any thread
# or async context without requiring Flask's application context.

_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URI")
_engine = None
_SessionLocal = None
_StandaloneBase = declarative_base()


class _StandaloneDiscordBotLog(_StandaloneBase):
    """Standalone ORM model for discord_bot_log table (mirrors db_models.DiscordBotLog)."""
    __tablename__ = 'discord_bot_log'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    log_type = Column(String(20), nullable=False, index=True)
    guild_id = Column(String(30), nullable=True, index=True)
    channel_id = Column(String(30), nullable=True)
    user_id = Column(String(30), nullable=True, index=True)
    user_name = Column(String(100), nullable=True)
    content = Column(Text, nullable=True)
    extra_data = Column(JSON, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True
    )


def _get_session():
    """
    Get a standalone database session.
    
    Lazily initializes the engine on first use.
    Returns None if DATABASE_URL is not configured.
    """
    global _engine, _SessionLocal
    
    if not _DATABASE_URL:
        return None
    
    if _engine is None:
        _engine = create_engine(
            _DATABASE_URL,
            pool_size=5,
            pool_recycle=300,
            pool_pre_ping=True
        )
        _SessionLocal = sessionmaker(bind=_engine)
        logger.debug("Standalone database engine initialized for LoggingService")
    
    return _SessionLocal()


# ============================================================================
# LOGGING SERVICE
# ============================================================================

class LoggingService:
    """
    Service for logging Discord bot events to PostgreSQL.
    
    Uses a standalone database connection that works outside Flask's app context.
    This is essential for logging from Discord.py's event loop.
    
    Logs are stored in the discord_bot_log table and include:
    - Command executions
    - Game chat messages
    - Errors and exceptions
    - Broadcast events
    """
    
    @staticmethod
    def _create_log(
        log_type: LogType,
        guild_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Create a log entry in the database.
        
        Returns:
            Log entry ID or None on failure
        """
        session = _get_session()
        if session is None:
            logger.debug("Database not configured - skipping log entry")
            return None
        
        try:
            log_entry = _StandaloneDiscordBotLog(
                log_type=log_type.value,
                guild_id=str(guild_id) if guild_id else None,
                channel_id=str(channel_id) if channel_id else None,
                user_id=str(user_id) if user_id else None,
                user_name=user_name,
                content=content[:2000] if content else None,
                extra_data=metadata,
                created_at=datetime.now(timezone.utc)
            )
            session.add(log_entry)
            session.commit()
            log_id = log_entry.id
            return log_id
        except Exception as e:
            logger.error(f"Failed to create log entry: {e}")
            session.rollback()
            return None
        finally:
            session.close()
    
    @staticmethod
    def log_command(
        guild_id: str,
        channel_id: str,
        user_id: str,
        user_name: str,
        command_name: str,
        args: Optional[Dict[str, Any]] = None,
        success: bool = True
    ) -> Optional[int]:
        """
        Log a command execution.
        
        Args:
            guild_id: Discord guild ID
            channel_id: Discord channel ID
            user_id: User who executed the command
            user_name: User's display name
            command_name: Name of the command
            args: Command arguments (optional)
            success: Whether command succeeded
        
        Returns:
            Log entry ID or None on failure
        """
        metadata = {
            "command": command_name,
            "args": args or {},
            "success": success
        }
        
        return LoggingService._create_log(
            log_type=LogType.COMMAND,
            guild_id=guild_id,
            channel_id=channel_id,
            user_id=user_id,
            user_name=user_name,
            content=command_name,
            metadata=metadata
        )
    
    @staticmethod
    def log_message(
        guild_id: str,
        channel_id: str,
        user_id: str,
        user_name: str,
        content: str,
        session_id: Optional[str] = None,
        direction: str = "outgoing"
    ) -> Optional[int]:
        """
        Log a game chat message.
        
        Args:
            guild_id: Discord guild ID
            channel_id: Discord channel ID
            user_id: User who sent the message
            user_name: User's display name
            content: Message content
            session_id: Game session ID (optional)
            direction: 'incoming' (from game_server) or 'outgoing' (to game_server)
        
        Returns:
            Log entry ID or None on failure
        """
        metadata = {
            "session_id": session_id,
            "direction": direction
        }
        
        return LoggingService._create_log(
            log_type=LogType.MESSAGE,
            guild_id=guild_id,
            channel_id=channel_id,
            user_id=user_id,
            user_name=user_name,
            content=content,
            metadata=metadata
        )
    
    @staticmethod
    def log_error(
        error_type: str,
        error_message: str,
        guild_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Log an error or exception.
        
        Args:
            error_type: Type of error (e.g., 'CommandError', 'BroadcastError')
            error_message: Error message/description
            guild_id: Discord guild ID (optional)
            channel_id: Discord channel ID (optional)
            user_id: User involved (optional)
            user_name: User's display name (optional)
            context: Additional context (optional)
        
        Returns:
            Log entry ID or None on failure
        """
        metadata = {
            "error_type": error_type,
            "context": context or {}
        }
        
        return LoggingService._create_log(
            log_type=LogType.ERROR,
            guild_id=guild_id,
            channel_id=channel_id,
            user_id=user_id,
            user_name=user_name,
            content=error_message,
            metadata=metadata
        )
    
    @staticmethod
    def log_broadcast(
        session_id: str,
        message_count: int,
        success: bool,
        channel_id: Optional[str] = None,
        error: Optional[str] = None
    ) -> Optional[int]:
        """
        Log a broadcast event.
        
        Args:
            session_id: Game session ID
            message_count: Number of messages in broadcast
            success: Whether broadcast succeeded
            channel_id: Target channel ID (optional)
            error: Error message if failed (optional)
        
        Returns:
            Log entry ID or None on failure
        """
        metadata = {
            "session_id": session_id,
            "message_count": message_count,
            "success": success,
            "error": error
        }
        
        return LoggingService._create_log(
            log_type=LogType.BROADCAST,
            channel_id=channel_id,
            content=f"Broadcast: {message_count} messages for session {session_id}",
            metadata=metadata
        )
    
    @staticmethod
    def log_system(
        event: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Log a system event.
        
        Args:
            event: Event description (e.g., 'startup', 'shutdown')
            details: Additional details (optional)
        
        Returns:
            Log entry ID or None on failure
        """
        return LoggingService._create_log(
            log_type=LogType.SYSTEM,
            content=event,
            metadata=details
        )
