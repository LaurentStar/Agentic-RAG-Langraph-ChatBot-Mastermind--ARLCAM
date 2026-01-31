"""
Game Session CRUD Operations.

Data access layer for game_session_table_orm table.
"""

from datetime import datetime
from typing import List, Optional

from app.crud.base import BaseCRUD
from app.models.postgres_sql_db_models import GameSession
from app.constants import SessionStatus, GamePhase
from app.extensions import db


class GameSessionCRUD(BaseCRUD[GameSession]):
    """CRUD operations for GameSession."""
    
    model = GameSession
    
    @classmethod
    def get_by_session_id(cls, session_id: str) -> Optional[GameSession]:
        """Get session by ID."""
        return cls.get_by_id(session_id)
    
    @classmethod
    def get_active(cls) -> List[GameSession]:
        """Get all active game sessions."""
        return cls.model.query.filter_by(status=SessionStatus.ACTIVE).all()
    
    @classmethod
    def get_waiting(cls) -> List[GameSession]:
        """Get all sessions waiting for players."""
        return cls.model.query.filter_by(status=SessionStatus.WAITING).all()
    
    @classmethod
    def get_by_status(cls, status: SessionStatus) -> List[GameSession]:
        """Get sessions by status."""
        return cls.model.query.filter_by(status=status).all()
    
    @classmethod
    def get_by_discord_channel(cls, channel_id: str) -> Optional[GameSession]:
        """Get session bound to a Discord channel."""
        return cls.model.query.filter_by(discord_channel_id=channel_id).first()
    
    @classmethod
    def get_by_slack_channel(cls, channel_id: str) -> Optional[GameSession]:
        """Get session bound to a Slack channel."""
        return cls.model.query.filter_by(slack_channel_id=channel_id).first()
    
    @classmethod
    def start_game(cls, session_id: str) -> Optional[GameSession]:
        """Mark session as started."""
        return cls.update(
            session_id,
            is_game_started=True,
            status=SessionStatus.ACTIVE,
            current_phase=GamePhase.PHASE1_ACTIONS
        )
    
    @classmethod
    def advance_phase(cls, session_id: str, new_phase: GamePhase, phase_end_time: datetime) -> Optional[GameSession]:
        """Advance to next phase."""
        return cls.update(
            session_id,
            current_phase=new_phase,
            phase_end_time=phase_end_time
        )
    
    @classmethod
    def advance_turn(cls, session_id: str) -> Optional[GameSession]:
        """Advance to next turn."""
        session = cls.get_by_session_id(session_id)
        if session:
            return cls.update(session_id, turn_number=session.turn_number + 1)
        return None
    
    @classmethod
    def complete_game(cls, session_id: str, winners: List[str]) -> Optional[GameSession]:
        """Mark game as completed with winners."""
        return cls.update(
            session_id,
            status=SessionStatus.COMPLETED,
            winners=winners
        )
    
    @classmethod
    def cancel_game(cls, session_id: str) -> Optional[GameSession]:
        """Cancel a game session."""
        return cls.update(session_id, status=SessionStatus.CANCELLED)
    
    @classmethod
    def bind_discord(cls, session_id: str, channel_id: str) -> Optional[GameSession]:
        """Bind session to a Discord channel."""
        return cls.update(session_id, discord_channel_id=channel_id)
    
    @classmethod
    def bind_slack(cls, session_id: str, channel_id: str) -> Optional[GameSession]:
        """Bind session to a Slack channel."""
        return cls.update(session_id, slack_channel_id=channel_id)
    
    @classmethod
    def update_deck(cls, session_id: str, deck_state: List, revealed_cards: List) -> Optional[GameSession]:
        """Update deck state."""
        return cls.update(
            session_id,
            deck_state=deck_state,
            revealed_cards=revealed_cards
        )
