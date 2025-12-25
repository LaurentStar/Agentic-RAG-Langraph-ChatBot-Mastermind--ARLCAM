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
"""

from typing import Dict, List, Optional

from app.extensions import db_connection
from app.database.models import (
    Player,
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
    }
    
    @staticmethod
    def get_all_players() -> List[Player]:
        """Get all players from the database."""
        with db_connection.get_session() as session:
            return session.query(Player).all()
    
    @staticmethod
    def get_alive_players() -> List[Player]:
        """Get all alive players."""
        with db_connection.get_session() as session:
            return session.query(Player).filter(
                Player.player_statuses.any('alive')
            ).all()
    
    @staticmethod
    def get_player(display_name: str) -> Optional[Player]:
        """Get a specific player by display name."""
        with db_connection.get_session() as session:
            return session.query(Player).filter_by(
                display_name=display_name
            ).first()
    
    @staticmethod
    def get_players_with_pending_actions() -> List[Player]:
        """Get all players who have pending actions."""
        with db_connection.get_session() as session:
            players = session.query(Player).filter(
                Player.to_be_initiated.isnot(None)
            ).all()
            
            return [p for p in players if p.has_pending_action]
    
    @staticmethod
    def get_upgrade_details(display_name: str) -> Optional[UpgradeDetails]:
        """Get upgrade details for a player's pending action."""
        with db_connection.get_session() as session:
            return session.query(UpgradeDetails).filter_by(
                display_name=display_name
            ).first()
    
    @staticmethod
    def get_all_upgrade_details() -> Dict[str, UpgradeDetails]:
        """Get all upgrade details."""
        with db_connection.get_session() as session:
            upgrades = session.query(UpgradeDetails).all()
            return {u.display_name: u for u in upgrades}
    
    @staticmethod
    def get_visible_pending_actions(exclude_player: Optional[str] = None) -> List[VisiblePendingAction]:
        """
        Get pending actions formatted for agent visibility.
        
        This is what LLM agents see - they can see:
        - Player ID
        - Action type
        - Target
        - Whether it's upgraded (but NOT what the upgrade is)
        """
        players = PendingEventsDBService.get_players_with_pending_actions()
        upgrades = PendingEventsDBService.get_all_upgrade_details()
        
        visible_actions = []
        
        for player in players:
            if exclude_player and player.display_name == exclude_player:
                continue
            
            pending_action = player.pending_action
            if not pending_action:
                continue
            
            coup_action = PendingEventsDBService.ACTION_MAPPING.get(pending_action)
            if not coup_action:
                continue
            
            upgrade = upgrades.get(player.display_name)
            is_upgraded = upgrade.has_any_upgrade if upgrade else False
            
            visible_actions.append(VisiblePendingAction(
                player_id=player.display_name,
                action=coup_action,
                target=player.target_display_name,
                is_upgraded=is_upgraded,
            ))
        
        return visible_actions
    
    @staticmethod
    def get_game_state_summary() -> Dict:
        """Get a summary of the current game state."""
        players = PendingEventsDBService.get_all_players()
        alive_players = [p for p in players if p.is_alive]
        pending_actions = PendingEventsDBService.get_visible_pending_actions()
        
        return {
            "total_players": len(players),
            "alive_players": len(alive_players),
            "players_with_actions": len(pending_actions),
            "alive_player_names": [p.display_name for p in alive_players],
            "pending_action_summary": [
                {
                    "player": a.get("player_id"),
                    "action": a.get("action").value if a.get("action") else None,
                    "has_target": a.get("target") is not None,
                    "is_upgraded": a.get("is_upgraded"),
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

