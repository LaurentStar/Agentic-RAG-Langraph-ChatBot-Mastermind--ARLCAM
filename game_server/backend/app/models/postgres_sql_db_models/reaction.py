"""
Reaction ORM Model.

Stores player reactions (challenge, block, pass) to pending actions.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, DateTime, String
from sqlalchemy.dialects.postgresql import UUID, ENUM, ARRAY

from app.extensions import db
from app.constants import ReactionType, ToBeInitiated


class Reaction(db.Model):
    """
    Player reaction to another player's pending action.
    
    During Phase 2, players can react to visible pending actions with:
    - CHALLENGE: Challenge the action's claimed role
    - BLOCK: Attempt to block the action (if blockable)
    - PASS: Take no reaction
    """
    __bind_key__ = 'db_players'
    __tablename__ = 'gs_reaction_table_orm'
    
    # Identity
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Session context
    session_id: Mapped[str] = mapped_column(
        ForeignKey("gs_game_session_table_orm.session_id", ondelete="CASCADE"),
        index=True
    )
    turn_number: Mapped[int]
    
    # Reactor (user making the reaction)
    reactor_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gs_user_account_table_orm.user_id", ondelete="CASCADE"),
        index=True
    )
    
    # Actor (user whose action is being reacted to)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gs_user_account_table_orm.user_id", ondelete="CASCADE"),
        index=True
    )
    
    # Target action
    target_action: Mapped[ToBeInitiated] = mapped_column(
        ENUM(ToBeInitiated, name="to_be_initiated_enum", create_type=True)
    )
    
    # Reaction details
    reaction_type: Mapped[ReactionType] = mapped_column(
        ENUM(ReactionType, name="reaction_type_enum", create_type=True)
    )
    block_with_role: Mapped[str] = mapped_column(String(50), nullable=True)
    # Role claimed for block
    
    # Status
    is_locked: Mapped[bool] = mapped_column(default=False)
    # Locked during LOCKOUT2
    
    is_resolved: Mapped[bool] = mapped_column(default=False)
    # After resolution
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc)
    )
    
    @property
    def is_challenge(self) -> bool:
        """Check if this is a challenge reaction."""
        return self.reaction_type == ReactionType.CHALLENGE
    
    @property
    def is_block(self) -> bool:
        """Check if this is a block reaction."""
        return self.reaction_type == ReactionType.BLOCK
    
    @property
    def is_pass(self) -> bool:
        """Check if this is a pass reaction."""
        return self.reaction_type == ReactionType.PASS
    
    def __repr__(self):
        return f"<Reaction {self.id}: {self.reaction_type.value} by user={self.reactor_user_id}>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'turn_number': self.turn_number,
            'reactor_user_id': str(self.reactor_user_id),
            'actor_user_id': str(self.actor_user_id),
            'target_action': self.target_action.value,
            'reaction_type': self.reaction_type.value,
            'block_with_role': self.block_with_role,
            'is_locked': self.is_locked,
            'is_resolved': self.is_resolved,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class TurnResult(db.Model):
    """
    Stores the results of a resolved turn for history/broadcasting.
    """
    __bind_key__ = 'db_players'
    __tablename__ = 'gs_turn_result_table_orm'
    
    # Identity
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Session context
    session_id: Mapped[str] = mapped_column(
        ForeignKey("gs_game_session_table_orm.session_id", ondelete="CASCADE"),
        index=True
    )
    turn_number: Mapped[int]
    
    # Results (stored as JSON for flexibility)
    results_json: Mapped[dict] = mapped_column(db.JSON, default=dict)
    summary: Mapped[str] = mapped_column(String(1000), default="")
    
    # Players eliminated this turn (display names for broadcast)
    players_eliminated: Mapped[list] = mapped_column(
        ARRAY(String(100)),
        default=list
    )
    # Note: Using display names here for human-readable broadcasts
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    
    def __repr__(self):
        return f"<TurnResult session={self.session_id} turn={self.turn_number}>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'turn_number': self.turn_number,
            'results_json': self.results_json,
            'summary': self.summary,
            'players_eliminated': self.players_eliminated,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
