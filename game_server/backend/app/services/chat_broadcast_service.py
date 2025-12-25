"""
Chat Broadcast Service.

Handles pushing chat messages to registered bot endpoints.
Called by APScheduler every 5 minutes per session.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional

import httpx

from app.services.chat_service import ChatService


class ChatBroadcastService:
    """Service for broadcasting chat messages to platform bots."""
    
    # Default broadcast interval in minutes
    DEFAULT_INTERVAL_MINUTES = 5
    
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
    def schedule_broadcast(session_id: str, interval_minutes: int = None) -> str:
        """
        Schedule recurring broadcast job for a session.
        
        Args:
            session_id: Game session ID
            interval_minutes: Broadcast interval (default: 5)
        
        Returns:
            Job ID
        """
        from app import scheduler
        
        if interval_minutes is None:
            interval_minutes = ChatBroadcastService.DEFAULT_INTERVAL_MINUTES
        
        job_id = f"chat_broadcast_{session_id}"
        
        # Remove existing job if any
        existing_job = scheduler.get_job(job_id)
        if existing_job:
            scheduler.remove_job(job_id)
        
        # Schedule new job
        scheduler.add_job(
            id=job_id,
            func=ChatBroadcastService._scheduled_broadcast,
            args=[session_id],
            trigger='interval',
            minutes=interval_minutes,
            misfire_grace_time=60
        )
        
        return job_id
    
    @staticmethod
    def _scheduled_broadcast(session_id: str) -> None:
        """
        Wrapper for scheduled broadcast (runs in app context).
        
        Called by APScheduler.
        """
        from flask import current_app
        
        with current_app.app_context():
            result = ChatBroadcastService.broadcast_chat(session_id)
            
            # Log results
            if result["message_count"] > 0:
                success_count = sum(1 for r in result["results"] if r["success"])
                print(
                    f"[CHAT BROADCAST] Session {session_id}: "
                    f"Sent {result['message_count']} messages to "
                    f"{success_count}/{result['endpoint_count']} endpoints"
                )
    
    @staticmethod
    def cancel_broadcast(session_id: str) -> bool:
        """
        Cancel scheduled broadcast job for a session.
        
        Args:
            session_id: Game session ID
        
        Returns:
            True if cancelled, False if not found
        """
        from app import scheduler
        
        job_id = f"chat_broadcast_{session_id}"
        existing_job = scheduler.get_job(job_id)
        
        if existing_job:
            scheduler.remove_job(job_id)
            return True
        
        return False
    
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

