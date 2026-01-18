"""
Ending Phase Job.

One-shot job that completes a game session after the ENDING phase timer expires.
This allows players a window to request a rematch before the session is finalized.

Trigger: date (one-shot)
Job ID Format: ending_phase_{session_id}
"""

from datetime import datetime, timedelta, timezone
from typing import Optional


class EndingPhaseJob:
    """
    One-shot job for completing a session after the ENDING phase.
    
    When a game ends (turn limit reached or only one player alive), the session
    transitions to the ENDING phase. This job is scheduled for when that phase
    expires. If no rematch is requested during ENDING, this job finalizes the
    session to COMPLETED status.
    
    If a player requests a rematch, this job should be cancelled via cancel().
    """
    
    # ==================== Configuration ====================
    JOB_ID_PREFIX = "ending_phase"
    
    # ==================== Public API ====================
    
    @classmethod
    def schedule(cls, session_id: str) -> Optional[str]:
        """
        Schedule session completion after ENDING phase duration.
        
        Args:
            session_id: Game session ID
        
        Returns:
            Job ID if scheduled, None if session not found or not in ENDING phase
        """
        from app import scheduler
        from app.models.postgres_sql_db_models import GameSession
        from app.constants import GamePhase
        
        session = GameSession.query.filter_by(session_id=session_id).first()
        
        if not session:
            return None
        
        if session.current_phase != GamePhase.ENDING:
            return None
        
        # Calculate completion time using session-specific ENDING duration
        duration = session.get_phase_duration(GamePhase.ENDING)
        run_time = datetime.now(timezone.utc) + timedelta(minutes=duration)
        
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
            trigger='date',
            run_date=run_time,
            misfire_grace_time=60
        )
        
        print(
            f"[JOB: EndingPhase] Scheduled for session {session_id}, "
            f"will complete in {duration} minutes"
        )
        
        return job_id
    
    @classmethod
    def cancel(cls, session_id: str) -> bool:
        """
        Cancel scheduled session completion (e.g., when rematch is requested).
        
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
            print(f"[JOB: EndingPhase] Cancelled for session {session_id}")
            return True
        
        return False
    
    # ==================== Execution ====================
    
    @classmethod
    def run(cls, session_id: str) -> Optional[dict]:
        """
        Execute session completion (called by APScheduler).
        
        Runs within Flask app context for database access.
        Calls SessionService.complete_session_from_ending() to finalize.
        
        Args:
            session_id: Game session ID
        
        Returns:
            Dict with completion info, or None if completion failed
        """
        from flask import current_app
        from app.services.session_service import SessionService
        from app.constants import GamePhase
        
        with current_app.app_context():
            try:
                session = SessionService.complete_session_from_ending(session_id)
                
                print(
                    f"[JOB: EndingPhase] Session {session_id} completed. "
                    f"Winners: {session.winners}"
                )
                
                return {
                    "session_id": session_id,
                    "status": "completed",
                    "winners": session.winners or []
                }
                
            except ValueError as e:
                print(f"[JOB: EndingPhase] Session {session_id} completion failed: {e}")
                return None
    
    # ==================== Helpers ====================
    
    @classmethod
    def _make_job_id(cls, session_id: str) -> str:
        """Generate job ID for a session."""
        return f"{cls.JOB_ID_PREFIX}_{session_id}"

