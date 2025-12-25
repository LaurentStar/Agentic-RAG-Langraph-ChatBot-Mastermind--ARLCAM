"""
Reaction ORM Model.

Stores player reactions (challenge, block, pass) to pending actions.
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.dialects import postgresql

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
    __tablename__ = 'reaction_table_orm'
    
    # Identity
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Session context
    session_id: Mapped[str] = mapped_column(ForeignKey("game_session_table_orm.session_id"))
    turn_number: Mapped[int]
    
    # Reactor (player making the reaction)
    reactor_display_name: Mapped[str] = mapped_column(ForeignKey("player_table_orm.display_name"))
    
    # Target action
    actor_display_name: Mapped[str] = mapped_column(ForeignKey("player_table_orm.display_name"))
    target_action: Mapped[ToBeInitiated] = mapped_column(
        postgresql.ENUM(ToBeInitiated, name="to_be_initiated_enum", create_type=False)
    )
    
    # Reaction details
    reaction_type: Mapped[ReactionType] = mapped_column(
        postgresql.ENUM(ReactionType, name="reaction_type_enum", create_type=True)
    )
    block_with_role: Mapped[str] = mapped_column(nullable=True)  # Role claimed for block
    
    # Status
    is_locked: Mapped[bool] = mapped_column(default=False)  # Locked during LOCKOUT2
    is_resolved: Mapped[bool] = mapped_column(default=False)  # After resolution
    
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


class TurnResult(db.Model):
    """
    Stores the results of a resolved turn for history/broadcasting.
    """
    __tablename__ = 'turn_result_table_orm'
    
    # Identity
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Session context
    session_id: Mapped[str] = mapped_column(ForeignKey("game_session_table_orm.session_id"))
    turn_number: Mapped[int]
    
    # Results (stored as JSON for flexibility)
    results_json: Mapped[str] = mapped_column(postgresql.JSON, default=dict)
    summary: Mapped[str] = mapped_column(default="")
    
    # Players eliminated this turn
    players_eliminated: Mapped[list] = mapped_column(
        postgresql.ARRAY(db.String),
        default=list
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

