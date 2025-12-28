"""
Logging Service.

Handles database logging of commands, messages, and errors using SQLAlchemy.
"""

import logging
from typing import Dict, Any, Optional

from app.constants import LogType
from app.extensions import db
from app.database.db_models import SlackBotLog

logger = logging.getLogger(__name__)


class LoggingService:
    """
    Service for logging Slack bot events to PostgreSQL.
    
    Logs are stored in the slack_bot_log table and include:
    - Command executions
    - Game chat messages
    - Errors and exceptions
    - Broadcast events
    """
    
    @staticmethod
    def _create_log(
        log_type: LogType,
        team_id: Optional[str] = None,
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
        try:
            log_entry = SlackBotLog(
                log_type=log_type.value,
                team_id=str(team_id) if team_id else None,
                channel_id=str(channel_id) if channel_id else None,
                user_id=str(user_id) if user_id else None,
                user_name=user_name,
                content=content[:2000] if content else None,
                extra_data=metadata
            )
            db.session.add(log_entry)
            db.session.commit()
            return log_entry.id
        except Exception as e:
            logger.error(f"Failed to create log entry: {e}")
            db.session.rollback()
            return None
    
    @staticmethod
    def log_command(
        team_id: str,
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
            team_id: Slack team/workspace ID
            channel_id: Slack channel ID
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
            team_id=team_id,
            channel_id=channel_id,
            user_id=user_id,
            user_name=user_name,
            content=command_name,
            metadata=metadata
        )
    
    @staticmethod
    def log_message(
        team_id: str,
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
            team_id: Slack team/workspace ID
            channel_id: Slack channel ID
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
            team_id=team_id,
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
        team_id: Optional[str] = None,
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
            team_id: Slack team/workspace ID (optional)
            channel_id: Slack channel ID (optional)
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
            team_id=team_id,
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
