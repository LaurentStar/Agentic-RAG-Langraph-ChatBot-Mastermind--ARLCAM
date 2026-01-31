"""
Pending Events Database Service.

Provides LLM agents with direct PostgreSQL access to query pending game events.

Key difference from human players:
- Humans: Call Discord/Slack/API to view pending events
- LLM Agents: Direct DB connection for faster, more comprehensive access

This service provides:
- Query all pending actions for a game
- Get specific player's pending action
- Get upgrade details for actions
- Build visible action lists for agent state

Architecture:
- Uses three-tier model: UserAccount + PlayerGameState + UpgradeDetails
- Queries join UserAccount (for display_name) with PlayerGameState (for game state)
"""

from typing import Dict, List, Optional, Tuple

from app.extensions import db_connection
from app.database.models import (
    UserAccount,
    PlayerGameState,
    UpgradeDetails,
    ToBeInitiated,
)
from app.models.graph_state_models.hourly_coup_state import VisiblePendingAction
from app.constants import CoupAction


class PendingEventsDBService:
    """
    Service for querying pending game events from PostgreSQL.
    
    LLM agents use this for direct DB access to see:
    - What actions other players have queued
    - Whether actions are upgraded
    - Current game state
    """
    
    # Mapping from DB action types to CoupAction
    ACTION_MAPPING = {
        ToBeInitiated.ACT_ASSASSINATION: CoupAction.ASSASSINATE,
        ToBeInitiated.ACT_FOREIGN_AID: CoupAction.FOREIGN_AID,
        ToBeInitiated.ACT_COUP: CoupAction.COUP,
        ToBeInitiated.ACT_STEAL: CoupAction.STEAL,
        ToBeInitiated.ACT_BLOCK: CoupAction.PASS,
        ToBeInitiated.ACT_SWAP_INFLUENCE: CoupAction.EXCHANGE,
        ToBeInitiated.ACT_TAX: CoupAction.TAX,
    }
    
    @staticmethod
    def get_all_game_states() -> List[Tuple[UserAccount, PlayerGameState]]:
        """Get all active game states with their user accounts."""
        with db_connection.get_session() as session:
            return session.query(UserAccount, PlayerGameState).join(
                PlayerGameState, UserAccount.user_id == PlayerGameState.user_id
            ).filter(
                PlayerGameState.session_id.isnot(None)
            ).all()
    
    @staticmethod
    def get_alive_players() -> List[Tuple[UserAccount, PlayerGameState]]:
        """Get all alive players with their user accounts."""
        with db_connection.get_session() as session:
            return session.query(UserAccount, PlayerGameState).join(
                PlayerGameState, UserAccount.user_id == PlayerGameState.user_id
            ).filter(
                PlayerGameState.player_statuses.any('alive'),
                PlayerGameState.session_id.isnot(None)
            ).all()
    
    @staticmethod
    def get_player(display_name: str) -> Optional[Tuple[UserAccount, PlayerGameState]]:
        """Get a specific player by display name (returns user and game state)."""
        with db_connection.get_session() as session:
            result = session.query(UserAccount, PlayerGameState).join(
                PlayerGameState, UserAccount.user_id == PlayerGameState.user_id
            ).filter(
                UserAccount.display_name == display_name,
                PlayerGameState.session_id.isnot(None)
            ).first()
            return result
    
    @staticmethod
    def get_game_state_by_display_name(display_name: str) -> Optional[PlayerGameState]:
        """Get active game state by display name (for backwards compatibility)."""
        result = PendingEventsDBService.get_player(display_name)
        if result:
            return result[1]  # Return just the game state
        return None
    
    @staticmethod
    def get_players_with_pending_actions() -> List[Tuple[UserAccount, PlayerGameState]]:
        """Get all players who have pending actions."""
        with db_connection.get_session() as session:
            results = session.query(UserAccount, PlayerGameState).join(
                PlayerGameState, UserAccount.user_id == PlayerGameState.user_id
            ).filter(
                PlayerGameState.to_be_initiated.isnot(None),
                PlayerGameState.session_id.isnot(None)
            ).all()
            
            return [(u, gs) for u, gs in results if gs.has_pending_action]
    
    @staticmethod
    def get_upgrade_details_by_game_state_id(game_state_id) -> Optional[UpgradeDetails]:
        """Get upgrade details for a player's pending action by game state ID."""
        with db_connection.get_session() as session:
            return session.query(UpgradeDetails).filter_by(
                game_state_id=game_state_id
            ).first()
    
    @staticmethod
    def get_all_upgrade_details() -> Dict[str, UpgradeDetails]:
        """Get all upgrade details, keyed by game_state_id string."""
        with db_connection.get_session() as session:
            upgrades = session.query(UpgradeDetails).all()
            return {str(u.game_state_id): u for u in upgrades}
    
    @staticmethod
    def get_visible_pending_actions(exclude_player: Optional[str] = None) -> List[VisiblePendingAction]:
        """
        Get pending actions formatted for agent visibility.
        
        This is what LLM agents see - they can see:
        - Player ID (display_name)
        - Action type
        - Target
        - Whether it's upgraded (but NOT what the upgrade is)
        """
        player_data = PendingEventsDBService.get_players_with_pending_actions()
        upgrades = PendingEventsDBService.get_all_upgrade_details()
        
        visible_actions = []
        
        for user, game_state in player_data:
            if exclude_player and user.display_name == exclude_player:
                continue
            
            pending_action = game_state.pending_action
            if not pending_action:
                continue
            
            coup_action = PendingEventsDBService.ACTION_MAPPING.get(pending_action)
            if not coup_action:
                continue
            
            upgrade = upgrades.get(str(game_state.id))
            is_upgraded = upgrade.has_any_upgrade if upgrade else False
            
            visible_actions.append(VisiblePendingAction(
                player_id=user.display_name,
                action=coup_action,
                target=game_state.target_display_name,
                is_upgraded=is_upgraded,
            ))
        
        return visible_actions
    
    @staticmethod
    def get_game_state_summary() -> Dict:
        """Get a summary of the current game state."""
        player_data = PendingEventsDBService.get_all_game_states()
        alive_players = [(u, gs) for u, gs in player_data if gs.is_alive]
        pending_actions = PendingEventsDBService.get_visible_pending_actions()
        
        return {
            "total_players": len(player_data),
            "alive_players": len(alive_players),
            "players_with_actions": len(pending_actions),
            "alive_player_names": [u.display_name for u, gs in alive_players],
            "pending_action_summary": [
                {
                    "player": a.player_id if hasattr(a, 'player_id') else a.get("player_id"),
                    "action": (a.action.value if hasattr(a, 'action') else a.get("action").value) if (hasattr(a, 'action') and a.action) or (isinstance(a, dict) and a.get("action")) else None,
                    "has_target": (a.target is not None if hasattr(a, 'target') else a.get("target") is not None),
                    "is_upgraded": a.is_upgraded if hasattr(a, 'is_upgraded') else a.get("is_upgraded"),
                }
                for a in pending_actions
            ],
        }
    
    @staticmethod
    def refresh_agent_visible_actions(agent) -> None:
        """Refresh an agent's visible pending actions from the database."""
        visible_actions = PendingEventsDBService.get_visible_pending_actions(
            exclude_player=agent.agent_id
        )
        agent.update_visible_pending_actions(visible_actions)

