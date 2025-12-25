"""
Phase Transition Service.

Handles automatic phase cycling using APScheduler.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from app.constants import (
    GamePhase,
    SessionStatus,
    PHASE_ORDER,
)
from app.extensions import db
from app.models.postgres_sql_db_models import GameSession


class PhaseTransitionService:
    """Service for managing game phase transitions."""
    
    def __init__(self, scheduler=None):
        """Initialize with optional scheduler instance."""
        self._scheduler = scheduler
    
    @property
    def scheduler(self):
        """Get scheduler, importing from app if not set."""
        if self._scheduler is None:
            from app import scheduler as app_scheduler
            self._scheduler = app_scheduler
        return self._scheduler
    
    def schedule_next_transition(self, session_id: str, app=None) -> Optional[str]:
        """
        Schedule the next phase transition for a session.
        
        Args:
            session_id: Session to schedule transition for
            app: Flask app for context (optional, uses current_app if not provided)
        
        Returns:
            Job ID if scheduled, None if session not found/inactive
        """
        session = GameSession.query.filter_by(session_id=session_id).first()
        
        if not session or not session.is_game_started:
            return None
        
        if session.status != SessionStatus.ACTIVE:
            return None
        
        # Calculate next transition time using session-specific duration
        duration = session.get_phase_duration(session.current_phase)
        run_time = datetime.now(timezone.utc) + timedelta(minutes=duration)
        
        job_id = f"phase_transition_{session_id}"
        
        # Remove existing job if any
        existing_job = self.scheduler.get_job(job_id)
        if existing_job:
            self.scheduler.remove_job(job_id)
        
        # Schedule new job
        self.scheduler.add_job(
            id=job_id,
            func=self._execute_transition,
            args=[session_id],
            trigger='date',
            run_date=run_time,
            misfire_grace_time=60
        )
        
        return job_id
    
    def _execute_transition(self, session_id: str):
        """Execute a phase transition (called by scheduler)."""
        from flask import current_app
        
        # Need app context for database access
        with current_app.app_context():
            self.transition_to_next_phase(session_id)
    
    def transition_to_next_phase(self, session_id: str) -> Optional[GameSession]:
        """
        Transition session to the next phase.
        
        Args:
            session_id: Session to transition
        
        Returns:
            Updated GameSession or None if not found
        """
        session = GameSession.query.filter_by(session_id=session_id).first()
        
        if not session:
            return None
        
        if not session.is_game_started or session.status != SessionStatus.ACTIVE:
            return None
        
        current_phase = session.current_phase
        current_index = PHASE_ORDER.index(current_phase)
        next_index = (current_index + 1) % len(PHASE_ORDER)
        next_phase = PHASE_ORDER[next_index]
        
        # Execute phase-specific logic
        if current_phase == GamePhase.PHASE1_ACTIONS:
            self._on_lockout1_start(session)
        elif current_phase == GamePhase.LOCKOUT1:
            self._on_phase2_start(session)
        elif current_phase == GamePhase.PHASE2_REACTIONS:
            self._on_lockout2_start(session)
        elif current_phase == GamePhase.LOCKOUT2:
            self._on_broadcast_start(session)
        elif current_phase == GamePhase.BROADCAST:
            self._on_new_turn_start(session)
        
        # Update phase
        session.current_phase = next_phase
        session.phase_end_time = datetime.now(timezone.utc) + timedelta(
            minutes=session.get_phase_duration(next_phase)
        )
        
        # Check for turn limit
        if next_phase == GamePhase.PHASE1_ACTIONS and current_index > 0:
            session.turn_number += 1
            
            if session.turn_limit > 0 and session.turn_number > session.turn_limit:
                session.status = SessionStatus.COMPLETED
                session.is_game_started = False
                db.session.commit()
                return session
        
        db.session.commit()
        
        # Schedule next transition
        self.schedule_next_transition(session_id)
        
        return session
    
    def _on_lockout1_start(self, session: GameSession):
        """
        Called when LOCKOUT1 phase starts.
        
        Actions are locked, calculate which actions require reactions.
        No more action changes allowed.
        """
        from app.services.reaction_service import ReactionService
        
        # Log pending actions for debugging
        actions = ReactionService.get_actions_requiring_reaction(session.session_id)
        print(f"[LOCKOUT1] Session {session.session_id}: {len(actions)} actions pending")
    
    def _on_phase2_start(self, session: GameSession):
        """
        Called when PHASE2_REACTIONS phase starts.
        
        Players can now submit reactions to pending actions.
        """
        from app.services.reaction_service import ReactionService
        
        # Get reactable actions for logging
        actions = ReactionService.get_actions_requiring_reaction(session.session_id)
        print(f"[PHASE2] Session {session.session_id}: Players can react to {len(actions)} actions")
    
    def _on_lockout2_start(self, session: GameSession):
        """
        Called when LOCKOUT2 phase starts.
        
        Reactions are locked, resolve all actions.
        """
        from app.services.reaction_service import ReactionService
        from app.services.action_resolution_service import ActionResolutionService
        
        # Lock all reactions
        locked_count = ReactionService.lock_reactions_for_turn(
            session.session_id, 
            session.turn_number
        )
        print(f"[LOCKOUT2] Session {session.session_id}: Locked {locked_count} reactions")
        
        # Resolve all actions
        try:
            result = ActionResolutionService.resolve_turn(session.session_id)
            print(f"[LOCKOUT2] Session {session.session_id}: Resolved turn - {result.summary}")
            
            # Store result for broadcast phase
            session.last_turn_result = result.summary
        except Exception as e:
            print(f"[LOCKOUT2] Session {session.session_id}: Resolution error - {e}")
    
    def _on_broadcast_start(self, session: GameSession):
        """
        Called when BROADCAST phase starts.
        
        Send results to all broadcast destinations.
        """
        from app.services.broadcast_service import BroadcastService
        from app.models.postgres_sql_db_models import TurnResultORM
        
        # Get the turn result from database
        turn_result_orm = TurnResultORM.query.filter_by(
            session_id=session.session_id,
            turn_number=session.turn_number
        ).first()
        
        if turn_result_orm:
            # Reconstruct TurnResult for broadcasting
            from app.models.game_models import TurnResult, ActionResult
            from app.constants import ResolutionOutcome, ToBeInitiated
            
            action_results = []
            for ar_data in turn_result_orm.results_json.get('action_results', []):
                action_results.append(ActionResult(
                    actor=ar_data['actor'],
                    action=ToBeInitiated(ar_data['action']),
                    target=ar_data['target'],
                    outcome=ResolutionOutcome(ar_data['outcome']),
                    cards_revealed=ar_data['cards_revealed'],
                    coins_transferred=ar_data['coins_transferred'],
                    description=ar_data['description']
                ))
            
            turn_result = TurnResult(
                session_id=session.session_id,
                turn_number=session.turn_number,
                action_results=action_results,
                players_eliminated=turn_result_orm.players_eliminated or [],
                summary=turn_result_orm.summary
            )
            
            # Broadcast to all destinations
            broadcast_results = BroadcastService.broadcast_results(
                session.session_id,
                turn_result
            )
            
            success_count = sum(1 for r in broadcast_results if r.success)
            print(f"[BROADCAST] Session {session.session_id}: Sent to {success_count}/{len(broadcast_results)} destinations")
        else:
            print(f"[BROADCAST] Session {session.session_id}: No turn result found")
    
    def _on_new_turn_start(self, session: GameSession):
        """
        Called when a new turn begins (PHASE1 after BROADCAST).
        
        Reset player pending actions, check for game end.
        """
        from app.models.postgres_sql_db_models import Player
        
        # Clear all pending actions for the session
        players = Player.query.filter_by(session_id=session.session_id).all()
        for player in players:
            player.to_be_initiated = []
            player.target_display_name = None
        
        # Check for winner (only one player alive)
        alive_count = sum(1 for p in players if p.is_alive)
        if alive_count <= 1:
            session.status = SessionStatus.COMPLETED
            session.is_game_started = False
    
    def cancel_scheduled_transition(self, session_id: str) -> bool:
        """
        Cancel a scheduled phase transition.
        
        Args:
            session_id: Session to cancel transition for
        
        Returns:
            True if job was cancelled, False if not found
        """
        job_id = f"phase_transition_{session_id}"
        existing_job = self.scheduler.get_job(job_id)
        
        if existing_job:
            self.scheduler.remove_job(job_id)
            return True
        
        return False


# Singleton instance
phase_transition_service = PhaseTransitionService()

