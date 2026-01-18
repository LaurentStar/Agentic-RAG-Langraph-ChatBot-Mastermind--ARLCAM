"""
Phase Transition Job.

One-shot job that advances the game to the next phase.
Scheduled based on the session's phase duration settings.

Trigger: date (one-shot)
Job ID Format: phase_transition_{session_id}
"""

from datetime import datetime, timedelta, timezone
from typing import Optional


class PhaseTransitionJob:
    """
    One-shot job for transitioning game phases.
    
    This job handles the scheduling logic. Actual phase transition is
    delegated to PhaseTransitionService.transition_to_next_phase().
    
    After each transition, the job re-schedules itself for the next phase.
    """
    
    # ==================== Configuration ====================
    JOB_ID_PREFIX = "phase_transition"
    
    # ==================== Public API ====================
    
    @classmethod
    def schedule(cls, session_id: str) -> Optional[str]:
        """
        Schedule the next phase transition for a session.
        
        Calculates the next transition time based on session's phase duration.
        
        Args:
            session_id: Game session ID
        
        Returns:
            Job ID if scheduled, None if session not found/inactive
        """
        from app import scheduler
        from app.models.postgres_sql_db_models import GameSession
        from app.constants import SessionStatus
        
        session = GameSession.query.filter_by(session_id=session_id).first()
        
        if not session or not session.is_game_started:
            return None
        
        if session.status != SessionStatus.ACTIVE:
            return None
        
        # Calculate next transition time using session-specific duration
        duration = session.get_phase_duration(session.current_phase)
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
        
        return job_id
    
    @classmethod
    def cancel(cls, session_id: str) -> bool:
        """
        Cancel scheduled phase transition for a session.
        
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
    def run(cls, session_id: str) -> Optional[dict]:
        """
        Execute the phase transition (called by APScheduler).
        
        Runs within Flask app context for database access.
        Delegates to PhaseTransitionService for transition logic.
        After transitioning, schedules the next transition automatically.
        
        Args:
            session_id: Game session ID
        
        Returns:
            Dict with new phase info, or None if transition failed
        """
        from flask import current_app
        from app.services.phase_transition_service import PhaseTransitionService
        from app.constants import SessionStatus, GamePhase
        from app.jobs.ending_phase_job import EndingPhaseJob
        
        with current_app.app_context():
            service = PhaseTransitionService()
            session = service.transition_to_next_phase(session_id)
            
            if session:
                print(
                    f"[JOB: PhaseTransition] Session {session_id}: "
                    f"Transitioned to {session.current_phase.value}, "
                    f"Turn {session.turn_number}"
                )
                
                # Check if we transitioned to ENDING phase
                if session.current_phase == GamePhase.ENDING:
                    # Schedule the ending phase job instead of another phase transition
                    EndingPhaseJob.schedule(session_id)
                    print(
                        f"[JOB: PhaseTransition] Session {session_id}: "
                        f"Game ending, scheduled EndingPhaseJob"
                    )
                elif session.is_game_started and session.status == SessionStatus.ACTIVE:
                    # Schedule next phase transition if game is still active
                    cls.schedule(session_id)
                
                return {
                    "session_id": session_id,
                    "new_phase": session.current_phase.value,
                    "turn_number": session.turn_number
                }
            
            return None
    
    # ==================== Helpers ====================
    
    @classmethod
    def _make_job_id(cls, session_id: str) -> str:
        """Generate job ID for a session."""
        return f"{cls.JOB_ID_PREFIX}_{session_id}"

