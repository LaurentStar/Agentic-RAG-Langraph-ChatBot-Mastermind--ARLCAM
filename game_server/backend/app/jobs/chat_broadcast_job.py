"""
Chat Broadcast Job.

Recurring job that pushes chat messages to registered bot endpoints.
Runs every N minutes per session (default: 5 minutes).

Trigger: interval
Default Interval: 5 minutes
Job ID Format: chat_broadcast_{session_id}
"""

from typing import Optional


class ChatBroadcastJob:
    """
    Recurring job for broadcasting chat messages to bot endpoints.
    
    This job handles the scheduling logic. Actual broadcast is delegated
    to ChatBroadcastService.broadcast_chat().
    """
    
    # ==================== Configuration ====================
    JOB_ID_PREFIX = "chat_broadcast"
    DEFAULT_INTERVAL_MINUTES = 5
    
    # ==================== Public API ====================
    
    @classmethod
    def schedule(cls, session_id: str, interval_minutes: Optional[int] = None) -> str:
        """
        Schedule recurring broadcast job for a session.
        
        Args:
            session_id: Game session ID
            interval_minutes: Broadcast interval (default: 5)
        
        Returns:
            Job ID (format: chat_broadcast_{session_id})
        """
        from app import scheduler
        
        if interval_minutes is None:
            interval_minutes = cls.DEFAULT_INTERVAL_MINUTES
        
        job_id = cls._make_job_id(session_id)
        
        # Remove existing job if any
        existing_job = scheduler.get_job(job_id)
        if existing_job:
            scheduler.remove_job(job_id)
        
        # Schedule new job
        scheduler.add_job(
            id=job_id,
            func=cls.run,
            args=[session_id],
            trigger='interval',
            minutes=interval_minutes,
            misfire_grace_time=60
        )
        
        return job_id
    
    @classmethod
    def cancel(cls, session_id: str) -> bool:
        """
        Cancel scheduled broadcast job for a session.
        
        Args:
            session_id: Game session ID
        
        Returns:
            True if cancelled, False if not found
        """
        from app import scheduler
        
        job_id = cls._make_job_id(session_id)
        existing_job = scheduler.get_job(job_id)
        
        if existing_job:
            scheduler.remove_job(job_id)
            return True
        
        return False
    
    # ==================== Execution ====================
    
    @classmethod
    def run(cls, session_id: str) -> dict:
        """
        Execute the broadcast (called by APScheduler).
        
        Runs within Flask app context for database access.
        Delegates to ChatBroadcastService for actual broadcast logic.
        
        Args:
            session_id: Game session ID
        
        Returns:
            Broadcast result dict
        """
        from flask import current_app
        from app.services.chat_broadcast_service import ChatBroadcastService
        
        with current_app.app_context():
            result = ChatBroadcastService.broadcast_chat(session_id)
            
            # Log results
            if result["message_count"] > 0:
                success_count = sum(1 for r in result["results"] if r["success"])
                print(
                    f"[JOB: ChatBroadcast] Session {session_id}: "
                    f"Sent {result['message_count']} messages to "
                    f"{success_count}/{result['endpoint_count']} endpoints"
                )
            
            return result
    
    # ==================== Helpers ====================
    
    @classmethod
    def _make_job_id(cls, session_id: str) -> str:
        """Generate job ID for a session."""
        return f"{cls.JOB_ID_PREFIX}_{session_id}"

