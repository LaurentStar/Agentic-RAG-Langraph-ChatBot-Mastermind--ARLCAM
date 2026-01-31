"""
Gameplay Service.

Handles in-game actions, reactions, card selection, and game state retrieval.
"""

from typing import Any, Dict, List, Optional, Tuple

from app.constants import (
    ACTION_TO_INITIATED,
    CardType,
    CoupAction,
    GamePhase,
    ReactionType,
    TARGETED_ACTIONS,
    ToBeInitiated,
)
from app.extensions import db
from app.models.postgres_sql_db_models import GameSession, UserAccount, PlayerGameState
from app.models.postgres_sql_db_models.player_game_state import ToBeInitiatedUpgradeDetails
from app.crud import UserAccountCRUD, PlayerGameStateCRUD, GameSessionCRUD


class GameplayService:
    """Service for in-game actions and state management."""
    
    @staticmethod
    def get_session_and_player(
        session_id: str,
        player_name: str
    ) -> Tuple[Optional[GameSession], Optional[Tuple[UserAccount, PlayerGameState]], Optional[Dict], Optional[int]]:
        """
        Get session and player, validating they exist and player is in session.
        
        Returns:
            Tuple of (session, (user, game_state), error_dict, error_code)
            If valid, error_dict and error_code are None.
        """
        session = GameSession.query.filter_by(session_id=session_id).first()
        if not session:
            return None, None, {'error': 'Session not found'}, 404
        
        # Look up by display_name and get game state
        result = PlayerGameStateCRUD.get_user_and_state_by_display_name(player_name)
        if not result:
            # Check if user exists but has no active game state
            user = UserAccountCRUD.get_by_display_name(player_name)
            if not user:
                return None, None, {'error': 'Player not found'}, 404
            return None, None, {'error': 'Player not in any session'}, 403
        
        user, game_state = result
        if game_state.session_id != session_id:
            return None, None, {'error': 'Player not in this session'}, 403
        
        return session, (user, game_state), None, None
    
    @staticmethod
    def get_pending_actions(session_id: str) -> Dict[str, Any]:
        """
        Get all visible pending actions for a session.
        
        Returns:
            Dict with pending_actions, current_phase, and phase_end_time
        """
        session = GameSession.query.filter_by(session_id=session_id).first()
        if not session:
            return {'error': 'Session not found'}
        
        # Get all players in session with their user accounts
        player_data = PlayerGameStateCRUD.get_session_with_users(session_id)
        
        pending_actions = []
        for user, game_state in player_data:
            if game_state.to_be_initiated and ToBeInitiated.NO_EVENT not in game_state.to_be_initiated:
                # Check if player has upgrade details
                upgrade = game_state.upgrade_details
                is_upgraded = upgrade is not None and (
                    upgrade.assassination_priority or
                    upgrade.kleptomania_steal or
                    upgrade.trigger_identity_crisis
                )
                
                for action in game_state.to_be_initiated:
                    if action != ToBeInitiated.NO_EVENT:
                        pending_actions.append({
                            'player_display_name': user.display_name,
                            'action': action.value,
                            'target_display_name': game_state.target_display_name,
                            'claimed_role': None,
                            'is_upgraded': is_upgraded
                        })
        
        return {
            'pending_actions': pending_actions,
            'current_phase': session.current_phase.value if session.current_phase else None,
            'phase_end_time': session.phase_end_time.isoformat() if session.phase_end_time else None
        }
    
    @staticmethod
    def set_action(
        session: GameSession,
        player_data: Tuple[UserAccount, PlayerGameState],
        action_str: str,
        target_display_name: Optional[str] = None,
        claimed_role: Optional[str] = None,
        upgrade_enabled: bool = False
    ) -> Tuple[Optional[Dict], int]:
        """
        Set or update a player's pending action.
        
        Args:
            session: Game session
            player_data: Tuple of (UserAccount, PlayerGameState)
            action_str: Action to perform
            target_display_name: Target player's display name (for targeted actions)
            claimed_role: Role claimed for bluffing
            upgrade_enabled: Whether to apply upgrade
        
        Returns:
            Tuple of (response_dict, status_code)
        """
        user, game_state = player_data
        
        # Check if in action phase
        if session.current_phase not in [GamePhase.PHASE1_ACTIONS]:
            return {'error': 'Not in action phase'}, 400
        
        if not game_state.is_alive:
            return {'error': 'Dead players cannot take actions'}, 400
        
        try:
            action = CoupAction(action_str)
        except ValueError:
            return {'error': f"Invalid action: {action_str}"}, 400
        
        # Validate target for targeted actions
        if action in TARGETED_ACTIONS:
            if not target_display_name:
                return {'error': f'{action.value} requires a target'}, 400
            
            target_state = PlayerGameStateCRUD.get_by_display_name_and_session(
                target_display_name, session.session_id
            )
            if not target_state:
                return {'error': 'Target not in session'}, 400
            if not target_state.is_alive:
                return {'error': 'Cannot target dead player'}, 400
        
        # Set the pending action
        initiated = ACTION_TO_INITIATED.get(action)
        if not initiated:
            return {'error': f'Unknown action: {action.value}'}, 400
        
        game_state.to_be_initiated = [initiated]
        game_state.target_display_name = target_display_name
        
        # Handle upgrade if enabled
        if upgrade_enabled:
            upgrade = game_state.upgrade_details
            
            if not upgrade:
                upgrade = ToBeInitiatedUpgradeDetails(game_state_id=game_state.id)
                db.session.add(upgrade)
            
            # Set appropriate upgrade based on action
            if action == CoupAction.ASSASSINATE and claimed_role:
                try:
                    upgrade.assassination_priority = CardType(claimed_role)
                except ValueError:
                    pass
            elif action == CoupAction.STEAL:
                upgrade.kleptomania_steal = True
            elif action == CoupAction.SWAP:
                upgrade.trigger_identity_crisis = True
        
        db.session.commit()
        
        return {'message': f'Action {action.value} set successfully'}, 200
    
    @staticmethod
    def get_pending_reactions(session_id: str) -> Dict[str, Any]:
        """
        Get pending reactions and actions requiring reaction.
        
        Returns:
            Dict with pending_reactions and actions_requiring_reaction
        """
        from app.services.reaction_service import ReactionService
        from app.models.postgres_sql_db_models import Reaction
        
        session = GameSession.query.filter_by(session_id=session_id).first()
        if not session:
            return {'error': 'Session not found'}
        
        # Get actions that can be reacted to
        actions_requiring = ReactionService.get_actions_requiring_reaction(session_id)
        
        # Get all pending (unresolved) reactions for this turn
        reactions = Reaction.query.filter_by(
            session_id=session_id,
            turn_number=session.turn_number,
            is_resolved=False
        ).all()
        
        pending_reactions = [
            {
                'reactor_display_name': r.reactor_display_name,
                'actor_display_name': r.actor_display_name,
                'target_action': r.target_action.value,
                'reaction_type': r.reaction_type.value,
                'block_with_role': r.block_with_role,
                'is_locked': r.is_locked
            }
            for r in reactions
        ]
        
        return {
            'pending_reactions': pending_reactions,
            'actions_requiring_reaction': actions_requiring,
            'current_phase': session.current_phase.value if session.current_phase else None
        }
    
    @staticmethod
    def set_reaction(
        session: GameSession,
        player_data: Tuple[UserAccount, PlayerGameState],
        reaction_type_str: str,
        target_player: str,
        block_with_role: Optional[str] = None
    ) -> Tuple[Dict, int]:
        """
        Set a player's reaction to another player's action.
        
        Args:
            session: Game session
            player_data: Tuple of (UserAccount, PlayerGameState) for reactor
            reaction_type_str: Type of reaction (challenge, block, pass)
            target_player: Player whose action is being reacted to
            block_with_role: Role claimed for blocking (if blocking)
        
        Returns:
            Tuple of (response_dict, status_code)
        """
        from app.services.reaction_service import ReactionService
        
        user, game_state = player_data
        
        # Check if in reaction phase
        if session.current_phase not in [GamePhase.PHASE2_REACTIONS]:
            return {'error': 'Not in reaction phase'}, 400
        
        if not game_state.is_alive:
            return {'error': 'Dead players cannot react'}, 400
        
        try:
            reaction_type = ReactionType(reaction_type_str)
        except ValueError:
            return {'error': f"Invalid reaction type: {reaction_type_str}"}, 400
        
        # Get the target player's pending action
        target_state = PlayerGameStateCRUD.get_by_display_name_and_session(
            target_player, session.session_id
        )
        if not target_state:
            return {'error': 'Target player not found'}, 404
        
        if not target_state.to_be_initiated:
            return {'error': 'Target player has no pending action'}, 400
        
        # Get the first non-NO_EVENT action
        target_action = None
        for action in target_state.to_be_initiated:
            if action != ToBeInitiated.NO_EVENT:
                target_action = action
                break
        
        if not target_action:
            return {'error': 'Target player has no pending action'}, 400
        
        # Create the reaction
        try:
            reaction = ReactionService.create_reaction(
                session_id=session.session_id,
                reactor_display_name=user.display_name,
                actor_display_name=target_player,
                target_action=target_action,
                reaction_type=reaction_type,
                block_with_role=block_with_role
            )
            
            return {
                'message': f'Reaction {reaction_type.value} recorded',
                'reaction_id': reaction.id
            }, 200
            
        except ValueError as e:
            return {'error': str(e)}, 400
    
    @staticmethod
    def select_cards(
        session: GameSession,
        player_data: Tuple[UserAccount, PlayerGameState],
        cards: List[str]
    ) -> Tuple[Dict, int]:
        """
        Select cards for reveal or exchange.
        
        Args:
            session: Game session
            player_data: Tuple of (UserAccount, PlayerGameState)
            cards: List of card type strings to select
        
        Returns:
            Tuple of (response_dict, status_code)
        """
        user, game_state = player_data
        
        if not cards:
            return {'error': 'No cards selected'}, 400
        
        # Validate cards are in player's hand
        player_cards = [c.value for c in (game_state.card_types or [])]
        for card in cards:
            if card not in player_cards:
                return {'error': f'Card {card} not in your hand'}, 400
        
        # TODO: Implement card selection logic
        return {'message': 'Cards selected'}, 200
    
    @staticmethod
    def get_game_state(session_id: str, current_player_name: str) -> Dict[str, Any]:
        """
        Get the current game state for a session.
        
        Args:
            session_id: Session to get state for
            current_player_name: Name of the requesting player (to show their cards)
        
        Returns:
            Dict with full game state
        """
        session = GameSession.query.filter_by(session_id=session_id).first()
        if not session:
            return {'error': 'Session not found'}
        
        # Get current player for their cards
        current_player_data = PlayerGameStateCRUD.get_user_and_state_by_display_name(current_player_name)
        
        # Build player states
        player_data = PlayerGameStateCRUD.get_session_with_users(session_id)
        player_states = []
        
        for user, game_state in player_data:
            action = None
            if game_state.to_be_initiated:
                for a in game_state.to_be_initiated:
                    if a != ToBeInitiated.NO_EVENT:
                        action = a.value
                        break
            
            player_states.append({
                'display_name': user.display_name,
                'coins': game_state.coins,
                'cards_count': len(game_state.card_types or []),
                'is_alive': game_state.is_alive,
                'pending_action': action,
                'target': game_state.target_display_name
            })
        
        # Get current player's cards (only they can see their own)
        my_cards = []
        if current_player_data:
            current_user, current_state = current_player_data
            if current_state.session_id == session_id:
                my_cards = [c.value for c in (current_state.card_types or [])]
        
        return {
            'session_id': session.session_id,
            'current_phase': session.current_phase.value if session.current_phase else None,
            'phase_end_time': session.phase_end_time.isoformat() if session.phase_end_time else None,
            'turn_number': session.turn_number,
            'turn_limit': session.turn_limit,
            'players': player_states,
            'revealed_cards': [c.value for c in (session.revealed_cards or [])],
            'my_cards': my_cards
        }

