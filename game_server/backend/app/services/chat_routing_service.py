"""
Chat Routing Service.

Routes LLM agent responses immediately to the target platform.
Bypasses the scheduled broadcast system for real-time delivery.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import httpx

from app.constants import SocialMediaPlatform
from app.models.postgres_sql_db_models import ChatBotEndpoint


logger = logging.getLogger(__name__)


class ChatRoutingService:
    """Service for routing messages immediately to platform bots."""
    
    @staticmethod
    def route_message(
        session_id: str,
        platform: str,
        sender: str,
        content: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Route a message immediately to the target platform.
        
        Used by LLM agents when they decide to respond.
        Looks up the registered bot endpoint and POSTs directly.
        
        Args:
            session_id: Game session ID
            platform: Target platform (discord, slack, etc.)
            sender: Sender display name (LLM agent name)
            content: Message content
        
        Returns:
            Tuple of (result_dict, error_message)
        """
        # Validate inputs
        if not session_id:
            return None, "session_id is required"
        if not platform:
            return None, "platform is required"
        if not content:
            return None, "content is required"
        
        # Parse platform
        try:
            platform_enum = SocialMediaPlatform(platform.lower())
        except ValueError:
            return None, f"Invalid platform: {platform}"
        
        # Look up endpoint for session + platform
        endpoint = ChatBotEndpoint.query.filter_by(
            session_id=session_id,
            platform=platform_enum,
            is_active=True
        ).first()
        
        if not endpoint:
            return None, f"No active endpoint registered for platform '{platform}' in session '{session_id}'"
        
        # Build payload matching the /api/broadcast format
        payload = {
            "session_id": session_id,
            "broadcast_time": datetime.utcnow().isoformat() + "Z",
            "message_count": 1,
            "messages": [
                {
                    "sender": sender,
                    "platform": platform_enum.value,
                    "content": content,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            ]
        }
        
        # POST to bot endpoint
        success, error = ChatRoutingService._post_to_endpoint(
            endpoint.endpoint_url,
            payload
        )
        
        if not success:
            return None, f"Failed to route message: {error}"
        
        # Update last broadcast time
        endpoint.last_broadcast_at = datetime.utcnow()
        from app.extensions import db
        db.session.commit()
        
        logger.info(
            f"Routed message from {sender} to {platform} for session {session_id}"
        )
        
        return {
            "status": "routed",
            "session_id": session_id,
            "platform": platform_enum.value,
            "endpoint_url": endpoint.endpoint_url
        }, None
    
    @staticmethod
    def _post_to_endpoint(
        endpoint_url: str,
        payload: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        POST payload to a bot endpoint.
        
        Args:
            endpoint_url: URL to POST to
            payload: JSON payload
        
        Returns:
            Tuple of (success: bool, error: Optional[str])
        """
        try:
            response = httpx.post(
                endpoint_url,
                json=payload,
                timeout=10.0
            )
            
            if response.status_code == 200:
                return True, None
            else:
                return False, f"HTTP {response.status_code}: {response.text[:100]}"
                
        except httpx.ConnectError as e:
            return False, f"Connection refused: {str(e)}"
        except httpx.TimeoutException:
            return False, "Request timeout"
        except Exception as e:
            return False, str(e)

