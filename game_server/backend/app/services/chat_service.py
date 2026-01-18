"""
Chat Service.

Handles chat message queue operations and bot endpoint management.
All business logic for chat endpoints lives here.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from app.constants import SocialMediaPlatform
from app.extensions import db
from app.models.postgres_sql_db_models import ChatMessage, ChatBotEndpoint
from app.services.lang_graph_client import LangGraphClient
from app.services.logging_service import GameServerLoggingService

logger = logging.getLogger(__name__)


class ChatService:
    """Service for managing cross-platform game chat."""
    
    # =============================================
    # API Response Methods (called by namespace)
    # =============================================
    
    @staticmethod
    def send_message(
        session_id: str,
        sender_display_name: str,
        platform_str: str,
        content: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Send a chat message (API entry point).
        
        Args:
            session_id: Game session ID
            sender_display_name: Sender's display name
            platform_str: Platform string (e.g., 'discord', 'slack')
            content: Message content
        
        Returns:
            Tuple of (response_dict, error_message)
        """
        # Validate content
        content = content.strip() if content else ''
        if not content:
            return None, 'Message content is required'
        
        # Parse platform
        try:
            platform = SocialMediaPlatform(platform_str.lower())
        except ValueError:
            platform = SocialMediaPlatform.DEFAULT
        
        # Queue the message
        message = ChatService.queue_message(
            session_id=session_id,
            sender_display_name=sender_display_name,
            sender_platform=platform,
            content=content
        )
        
        return {
            'id': message.id,
            'sender': message.sender_display_name,
            'platform': message.sender_platform.value,
            'content': message.content,
            'timestamp': message.created_at.isoformat() + 'Z'
        }, None
    
    @staticmethod
    def get_messages_response(session_id: str) -> Dict[str, Any]:
        """
        Get pending messages as API response.
        
        Args:
            session_id: Game session ID
        
        Returns:
            Formatted response dict
        """
        messages = ChatService.get_pending_messages(session_id)
        
        return {
            'session_id': session_id,
            'message_count': len(messages),
            'messages': [
                {
                    'id': m.id,
                    'sender': m.sender_display_name,
                    'platform': m.sender_platform.value,
                    'content': m.content,
                    'timestamp': m.created_at.isoformat() + 'Z'
                }
                for m in messages
            ]
        }
    
    @staticmethod
    def register_endpoint(
        session_id: str,
        platform_str: str,
        endpoint_url: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Register a bot endpoint (API entry point).
        
        Args:
            session_id: Game session ID
            platform_str: Platform string
            endpoint_url: URL to POST broadcasts to
        
        Returns:
            Tuple of (response_dict, error_message)
        """
        # Validate inputs
        if not platform_str:
            return None, 'Platform is required'
        
        endpoint_url = endpoint_url.strip() if endpoint_url else ''
        if not endpoint_url:
            return None, 'Endpoint URL is required'
        
        # Parse platform
        try:
            platform = SocialMediaPlatform(platform_str.lower())
        except ValueError:
            return None, f'Invalid platform: {platform_str}'
        
        # Register endpoint
        endpoint = ChatService.register_bot_endpoint(
            session_id=session_id,
            platform=platform,
            endpoint_url=endpoint_url
        )
        
        return {
            'id': endpoint.id,
            'platform': endpoint.platform.value,
            'endpoint_url': endpoint.endpoint_url,
            'is_active': endpoint.is_active
        }, None
    
    @staticmethod
    def get_endpoints_response(session_id: str) -> Dict[str, Any]:
        """
        Get active endpoints as API response.
        
        Args:
            session_id: Game session ID
        
        Returns:
            Formatted response dict
        """
        endpoints = ChatService.get_active_endpoints(session_id)
        
        return {
            'session_id': session_id,
            'endpoint_count': len(endpoints),
            'endpoints': [
                {
                    'id': e.id,
                    'platform': e.platform.value,
                    'endpoint_url': e.endpoint_url,
                    'is_active': e.is_active,
                    'last_broadcast_at': e.last_broadcast_at.isoformat() + 'Z' if e.last_broadcast_at else None
                }
                for e in endpoints
            ]
        }
    
    # =============================================
    # Message Queue Operations
    # =============================================
    
    @staticmethod
    def queue_message(
        session_id: str,
        sender_display_name: str,
        sender_platform: SocialMediaPlatform,
        content: str
    ) -> ChatMessage:
        """
        Add a message to the chat queue.
        
        Args:
            session_id: Game session ID
            sender_display_name: Name of the sender
            sender_platform: Platform the message came from
            content: Message content (max 2000 chars)
        
        Returns:
            Created ChatMessage object
        """
        # Truncate content if too long
        if len(content) > 2000:
            content = content[:1997] + "..."
        
        message = ChatMessage(
            session_id=session_id,
            sender_display_name=sender_display_name,
            sender_platform=sender_platform,
            content=content
        )
        
        db.session.add(message)
        db.session.commit()
        
        # Log the message received
        GameServerLoggingService.log_chat_flow(
            session_id=session_id,
            sender_id=sender_display_name,
            platform=sender_platform.value,
            content=content,
            direction="received"
        )
        
        # Push to lang_graph_server (fire-and-forget)
        # LLM agents will receive this event and decide whether to respond
        logger.info(
            f"[CHAT-FLOW] Pushing to LangGraph: session={session_id} "
            f"sender={sender_display_name} platform={sender_platform.value}"
        )
        LangGraphClient.push_chat_event(
            session_id=session_id,
            sender_id=sender_display_name,
            platform=sender_platform.value,
            content=content
        )
        
        return message
    
    @staticmethod
    def get_pending_messages(session_id: str) -> List[ChatMessage]:
        """
        Get all pending messages for a session.
        
        Args:
            session_id: Game session ID
        
        Returns:
            List of pending ChatMessage objects, ordered by creation time
        """
        return ChatMessage.query.filter_by(
            session_id=session_id
        ).order_by(ChatMessage.created_at.asc()).all()
    
    @staticmethod
    def clear_messages(session_id: str) -> int:
        """
        Delete all messages for a session.
        
        Args:
            session_id: Game session ID
        
        Returns:
            Number of messages deleted
        """
        count = ChatMessage.query.filter_by(session_id=session_id).delete()
        db.session.commit()
        return count
    
    @staticmethod
    def get_message_count(session_id: str) -> int:
        """Get count of pending messages for a session."""
        return ChatMessage.query.filter_by(session_id=session_id).count()
    
    # =============================================
    # Bot Endpoint Management
    # =============================================
    
    @staticmethod
    def register_bot_endpoint(
        session_id: str,
        platform: SocialMediaPlatform,
        endpoint_url: str
    ) -> ChatBotEndpoint:
        """
        Register a bot endpoint for broadcast pushes.
        
        If an endpoint for this session+platform already exists,
        updates the URL instead of creating a new one.
        
        Args:
            session_id: Game session ID
            platform: Platform (discord, slack, etc.)
            endpoint_url: URL to POST broadcasts to
        
        Returns:
            Created or updated ChatBotEndpoint object
        """
        # Check for existing endpoint
        existing = ChatBotEndpoint.query.filter_by(
            session_id=session_id,
            platform=platform
        ).first()
        
        if existing:
            existing.endpoint_url = endpoint_url
            existing.is_active = True
            db.session.commit()
            return existing
        
        # Create new endpoint
        endpoint = ChatBotEndpoint(
            session_id=session_id,
            platform=platform,
            endpoint_url=endpoint_url
        )
        
        db.session.add(endpoint)
        db.session.commit()
        
        return endpoint
    
    @staticmethod
    def get_active_endpoints(session_id: str) -> List[ChatBotEndpoint]:
        """
        Get all active bot endpoints for a session.
        
        Args:
            session_id: Game session ID
        
        Returns:
            List of active ChatBotEndpoint objects
        """
        return ChatBotEndpoint.query.filter_by(
            session_id=session_id,
            is_active=True
        ).all()
    
    @staticmethod
    def deactivate_endpoint(session_id: str, platform: SocialMediaPlatform) -> bool:
        """
        Deactivate a bot endpoint.
        
        Args:
            session_id: Game session ID
            platform: Platform to deactivate
        
        Returns:
            True if deactivated, False if not found
        """
        endpoint = ChatBotEndpoint.query.filter_by(
            session_id=session_id,
            platform=platform
        ).first()
        
        if not endpoint:
            return False
        
        endpoint.is_active = False
        db.session.commit()
        return True
    
    @staticmethod
    def update_last_broadcast(session_id: str) -> None:
        """
        Update last_broadcast_at for all active endpoints in a session.
        
        Called after a successful broadcast.
        """
        endpoints = ChatBotEndpoint.query.filter_by(
            session_id=session_id,
            is_active=True
        ).all()
        
        now = datetime.utcnow()
        for endpoint in endpoints:
            endpoint.last_broadcast_at = now
        
        db.session.commit()

