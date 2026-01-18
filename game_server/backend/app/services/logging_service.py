"""
Game Server Logging Service.

Handles database logging of chat flow events, LangGraph communication, and errors.
Follows the same pattern as Discord bot's LoggingService.
"""

import logging
from typing import Dict, Any, Optional

from app.extensions import db
from app.models.postgres_sql_db_models.game_server_log import GameServerLog

logger = logging.getLogger(__name__)


class GameServerLoggingService:
    """
    Service for logging game server events to PostgreSQL.
    
    Log Types:
    - chat_flow: Message received/forwarded through the system
    - langgraph_push: Communication with LangGraph server
    - error: Errors and exceptions
    - system: System events (startup, shutdown, etc.)
    """
    
    # =============================================
    # Core Log Creation
    # =============================================
    
    @staticmethod
    def _create_log(
        log_type: str,
        session_id: Optional[str] = None,
        sender_id: Optional[str] = None,
        platform: Optional[str] = None,
        content: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Create a log entry in the database.
        
        Returns:
            Log entry ID or None on failure
        """
        try:
            log_entry = GameServerLog(
                log_type=log_type,
                session_id=session_id,
                sender_id=sender_id,
                platform=platform,
                content=content[:2000] if content else None,
                extra_data=extra_data
            )
            db.session.add(log_entry)
            db.session.commit()
            return log_entry.id
        except Exception as e:
            logger.error(f"Failed to create log entry: {e}")
            db.session.rollback()
            return None
    
    # =============================================
    # Chat Flow Logging
    # =============================================
    
    @staticmethod
    def log_chat_flow(
        session_id: str,
        sender_id: str,
        platform: str,
        content: str,
        direction: str,
        extra: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Log a chat message flowing through the system.
        
        Args:
            session_id: Game session ID
            sender_id: Sender's display name
            platform: Source platform (discord, slack, etc.)
            content: Message content (will be truncated)
            direction: 'received' (from bot) or 'queued' (to broadcast)
            extra: Additional context
        
        Returns:
            Log entry ID or None on failure
        """
        # Also log to terminal with [CHAT-FLOW] prefix
        content_preview = content[:50] + "..." if len(content) > 50 else content
        logger.info(
            f"[CHAT-FLOW] {direction}: session={session_id} "
            f"sender={sender_id} platform={platform} content=\"{content_preview}\""
        )
        
        metadata = {
            "direction": direction,
            **(extra or {})
        }
        
        return GameServerLoggingService._create_log(
            log_type="chat_flow",
            session_id=session_id,
            sender_id=sender_id,
            platform=platform,
            content=content_preview,
            extra_data=metadata
        )
    
    # =============================================
    # LangGraph Communication Logging
    # =============================================
    
    @staticmethod
    def log_langgraph_push(
        session_id: str,
        sender_id: str,
        status: str,
        response: Optional[str] = None,
        error: Optional[str] = None
    ) -> Optional[int]:
        """
        Log communication with LangGraph server.
        
        Args:
            session_id: Game session ID
            sender_id: Original message sender
            status: 'sent', 'success', 'failed', 'timeout', 'unreachable'
            response: Response content preview (on success)
            error: Error message (on failure)
        
        Returns:
            Log entry ID or None on failure
        """
        # Also log to terminal
        if status in ('success', 'sent'):
            logger.info(
                f"[CHAT-FLOW] GameServer → LangGraph: session={session_id} "
                f"sender={sender_id} status={status}"
            )
        else:
            logger.warning(
                f"[CHAT-FLOW] GameServer → LangGraph: session={session_id} "
                f"sender={sender_id} status={status} error={error}"
            )
        
        metadata = {
            "status": status,
            "response_preview": response[:100] if response else None,
            "error": error
        }
        
        content = f"LangGraph push: {status}"
        if error:
            content += f" - {error}"
        
        return GameServerLoggingService._create_log(
            log_type="langgraph_push",
            session_id=session_id,
            sender_id=sender_id,
            content=content,
            extra_data=metadata
        )
    
    # =============================================
    # Error Logging
    # =============================================
    
    @staticmethod
    def log_error(
        error_type: str,
        message: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Log an error or exception.
        
        Args:
            error_type: Type of error (e.g., 'ChatError', 'LangGraphError')
            message: Error message
            session_id: Related session ID (optional)
            context: Additional context
        
        Returns:
            Log entry ID or None on failure
        """
        logger.error(f"[ERROR] {error_type}: {message}")
        
        metadata = {
            "error_type": error_type,
            "context": context or {}
        }
        
        return GameServerLoggingService._create_log(
            log_type="error",
            session_id=session_id,
            content=f"{error_type}: {message}",
            extra_data=metadata
        )
    
    # =============================================
    # System Logging
    # =============================================
    
    @staticmethod
    def log_system(
        event: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Log a system event.
        
        Args:
            event: Event description (e.g., 'startup', 'shutdown')
            details: Additional details
        
        Returns:
            Log entry ID or None on failure
        """
        logger.info(f"[SYSTEM] {event}")
        
        return GameServerLoggingService._create_log(
            log_type="system",
            content=event,
            extra_data=details
        )

