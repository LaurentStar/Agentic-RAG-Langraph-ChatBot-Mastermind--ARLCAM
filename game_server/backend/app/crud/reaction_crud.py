"""
Reaction CRUD Operations.

Data access layer for reaction table.
"""

from typing import List, Optional
from uuid import UUID

from app.crud.base import BaseCRUD
from app.models.postgres_sql_db_models import Reaction
from app.constants import ReactionType, ToBeInitiated
from app.extensions import db


class ReactionCRUD(BaseCRUD[Reaction]):
    """CRUD operations for Reaction."""
    
    model = Reaction
    
    @classmethod
    def get_by_session(cls, session_id: str) -> List[Reaction]:
        """Get all reactions in a session."""
        return cls.model.query.filter_by(session_id=session_id).all()
    
    @classmethod
    def get_by_session_and_turn(cls, session_id: str, turn_number: int) -> List[Reaction]:
        """Get reactions for a specific turn."""
        return cls.model.query.filter_by(
            session_id=session_id,
            turn_number=turn_number
        ).all()
    
    @classmethod
    def get_by_reactor(cls, session_id: str, reactor_user_id: UUID) -> List[Reaction]:
        """Get reactions made by a specific user in a session."""
        return cls.model.query.filter_by(
            session_id=session_id,
            reactor_user_id=reactor_user_id
        ).all()
    
    @classmethod
    def get_reactions_to_actor(cls, session_id: str, actor_user_id: UUID, turn_number: int) -> List[Reaction]:
        """Get all reactions to a specific actor's actions this turn."""
        return cls.model.query.filter_by(
            session_id=session_id,
            actor_user_id=actor_user_id,
            turn_number=turn_number
        ).all()
    
    @classmethod
    def get_challenges(cls, session_id: str, turn_number: int) -> List[Reaction]:
        """Get all challenge reactions for a turn."""
        return cls.model.query.filter_by(
            session_id=session_id,
            turn_number=turn_number,
            reaction_type=ReactionType.CHALLENGE
        ).all()
    
    @classmethod
    def get_blocks(cls, session_id: str, turn_number: int) -> List[Reaction]:
        """Get all block reactions for a turn."""
        return cls.model.query.filter_by(
            session_id=session_id,
            turn_number=turn_number,
            reaction_type=ReactionType.BLOCK
        ).all()
    
    @classmethod
    def get_unresolved(cls, session_id: str) -> List[Reaction]:
        """Get unresolved reactions in a session."""
        return cls.model.query.filter_by(
            session_id=session_id,
            is_resolved=False
        ).all()
    
    @classmethod
    def lock_reactions(cls, session_id: str, turn_number: int) -> int:
        """Lock all reactions for a turn. Returns count."""
        reactions = cls.get_by_session_and_turn(session_id, turn_number)
        for r in reactions:
            r.is_locked = True
        db.session.commit()
        return len(reactions)
    
    @classmethod
    def resolve_reaction(cls, reaction_id: int) -> Optional[Reaction]:
        """Mark a reaction as resolved."""
        return cls.update(reaction_id, is_resolved=True)
    
    @classmethod
    def resolve_all_in_turn(cls, session_id: str, turn_number: int) -> int:
        """Resolve all reactions for a turn. Returns count."""
        reactions = cls.get_by_session_and_turn(session_id, turn_number)
        for r in reactions:
            r.is_resolved = True
        db.session.commit()
        return len(reactions)
