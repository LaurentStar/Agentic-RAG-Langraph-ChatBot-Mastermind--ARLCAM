"""
Phase Transition Service.

Handles game phase transition BUSINESS LOGIC only.
Scheduling is handled by PhaseTransitionJob in app/jobs/.
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
    """
    Service for managing game phase transitions.
    
    This service handles ONLY the business logic of transitioning phases.
    Scheduling is handled by PhaseTransitionJob in app/jobs/.
    """
    
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
        should_end_game = False
        
        if current_phase == GamePhase.PHASE1_ACTIONS:
            self._on_lockout1_start(session)
        elif current_phase == GamePhase.LOCKOUT1:
            self._on_phase2_start(session)
        elif current_phase == GamePhase.PHASE2_REACTIONS:
            self._on_lockout2_start(session)
        elif current_phase == GamePhase.LOCKOUT2:
            self._on_broadcast_start(session)
        elif current_phase == GamePhase.BROADCAST:
            should_end_game = self._on_new_turn_start(session)
        
        # Check for turn limit (if transitioning to a new turn)
        if next_phase == GamePhase.PHASE1_ACTIONS and current_index > 0:
            session.turn_number += 1
            
            if session.turn_limit > 0 and session.turn_number > session.turn_limit:
                should_end_game = True
        
        # If game should end, transition to ENDING phase instead of next phase
        if should_end_game:
            from app.services.session_service import SessionService
            
            # Commit any player changes before transitioning
            db.session.commit()
            
            # Transition to ENDING phase
            return SessionService.transition_to_ending(session.session_id)
        
        # Normal phase transition
        session.current_phase = next_phase
        session.phase_end_time = datetime.now(timezone.utc) + timedelta(
            minutes=session.get_phase_duration(next_phase)
        )
        
        db.session.commit()
        
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
    
    def _on_new_turn_start(self, session: GameSession) -> bool:
        """
        Called when a new turn begins (PHASE1 after BROADCAST).
        
        Reset player pending actions, check for game end.
        
        Returns:
            True if game should end (transition to ENDING), False to continue
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
            return True  # Signal to transition to ENDING phase
        
        return False
    
# Singleton instance
phase_transition_service = PhaseTransitionService()

