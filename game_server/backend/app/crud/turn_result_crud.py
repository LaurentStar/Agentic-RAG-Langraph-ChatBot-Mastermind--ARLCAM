"""
Turn Result CRUD Operations.

Data access layer for turn_result table.
"""

from typing import List, Optional

from app.crud.base import BaseCRUD
from app.models.postgres_sql_db_models import TurnResultORM


class TurnResultCRUD(BaseCRUD[TurnResultORM]):
    """CRUD operations for TurnResult."""
    
    model = TurnResultORM
    
    @classmethod
    def get_by_session(cls, session_id: str) -> List[TurnResultORM]:
        """Get all turn results for a session."""
        return cls.model.query.filter_by(session_id=session_id).order_by(
            TurnResultORM.turn_number
        ).all()
    
    @classmethod
    def get_by_session_and_turn(cls, session_id: str, turn_number: int) -> Optional[TurnResultORM]:
        """Get result for a specific turn."""
        return cls.model.query.filter_by(
            session_id=session_id,
            turn_number=turn_number
        ).first()
    
    @classmethod
    def get_latest(cls, session_id: str) -> Optional[TurnResultORM]:
        """Get the most recent turn result for a session."""
        return cls.model.query.filter_by(session_id=session_id).order_by(
            TurnResultORM.turn_number.desc()
        ).first()
    
    @classmethod
    def create_result(
        cls,
        session_id: str,
        turn_number: int,
        results_json: dict,
        summary: str,
        players_eliminated: List[str] = None
    ) -> TurnResultORM:
        """Create a turn result record."""
        return cls.create(
            session_id=session_id,
            turn_number=turn_number,
            results_json=results_json,
            summary=summary,
            players_eliminated=players_eliminated or []
        )
