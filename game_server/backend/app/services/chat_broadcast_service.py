"""
Chat Broadcast Service.

Handles pushing chat messages to registered bot endpoints.
This service contains ONLY the broadcast BUSINESS LOGIC.
Scheduling is handled by ChatBroadcastJob in app/jobs/.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional

import httpx

from app.services.chat_service import ChatService


class ChatBroadcastService:
    """
    Service for broadcasting chat messages to platform bots.
    
    This service handles ONLY the business logic of broadcasting messages.
    Scheduling is handled by ChatBroadcastJob in app/jobs/.
    """
    
    @staticmethod
    def broadcast_chat(session_id: str) -> Dict[str, Any]:
        """
        Push pending messages to all registered bot endpoints.
        
        Called by APScheduler every 5 minutes.
        
        Args:
            session_id: Game session ID
        
        Returns:
            Dict with broadcast results:
            - message_count: Number of messages broadcast
            - endpoint_count: Number of endpoints notified
            - cleared: Number of messages cleared
            - results: List of per-endpoint results
        """
        # Get pending messages
        messages = ChatService.get_pending_messages(session_id)
        
        if not messages:
            return {
                "message_count": 0,
                "endpoint_count": 0,
                "cleared": 0,
                "results": []
            }
        
        # Get active endpoints
        endpoints = ChatService.get_active_endpoints(session_id)
        
        if not endpoints:
            # No endpoints registered, just clear the queue
            cleared = ChatService.clear_messages(session_id)
            return {
                "message_count": len(messages),
                "endpoint_count": 0,
                "cleared": cleared,
                "results": [],
                "warning": "No active endpoints registered"
            }
        
        # Build payload
        payload = {
            "session_id": session_id,
            "broadcast_time": datetime.utcnow().isoformat() + "Z",
            "message_count": len(messages),
            "messages": [
                {
                    "id": m.id,
                    "sender": m.sender_display_name,
                    "platform": m.sender_platform.value,
                    "content": m.content,
                    "timestamp": m.created_at.isoformat() + "Z"
                }
                for m in messages
            ]
        }
        
        # Push to each endpoint
        results = []
        for endpoint in endpoints:
            success, error = ChatBroadcastService._push_to_bot(
                endpoint.endpoint_url,
                payload
            )
            results.append({
                "platform": endpoint.platform.value,
                "endpoint_url": endpoint.endpoint_url,
                "success": success,
                "error": error
            })
        
        # Update last broadcast time
        ChatService.update_last_broadcast(session_id)
        
        # Clear the queue after broadcast
        cleared = ChatService.clear_messages(session_id)
        
        return {
            "message_count": len(messages),
            "endpoint_count": len(endpoints),
            "cleared": cleared,
            "results": results
        }
    
    @staticmethod
    def _push_to_bot(endpoint_url: str, payload: Dict[str, Any]) -> tuple:
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
    
    @staticmethod
    def trigger_immediate_broadcast(session_id: str) -> Dict[str, Any]:
        """
        Trigger an immediate broadcast (bypasses scheduler).
        
        Useful for admin commands or testing.
        
        Args:
            session_id: Game session ID
        
        Returns:
            Broadcast result dict
        """
        return ChatBroadcastService.broadcast_chat(session_id)

