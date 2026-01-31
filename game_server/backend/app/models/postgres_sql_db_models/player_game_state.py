"""
Player Game State ORM Model.

SQLAlchemy model for per-session game state.
This is transient data that exists only during an active game session.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import ForeignKey, String, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID, ARRAY, ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import CardType, PlayerStatus, ToBeInitiated
from app.extensions import db


class PlayerGameState(db.Model):
    """
    Player Game State table ORM model.
    
    Per-session transient state - coins, cards, status within a game.
    A new record is created when a player joins a game session.
    """
    
    __bind_key__ = 'db_players'
    __tablename__ = 'gs_player_game_state_table_orm'
    
    # =============================================
    # Identity
    # =============================================
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # =============================================
    # User Reference
    # =============================================
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gs_user_account_table_orm.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # =============================================
    # Session Reference
    # =============================================
    session_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("gs_game_session_table_orm.session_id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # =============================================
    # Game State
    # =============================================
    card_types: Mapped[List[CardType]] = mapped_column(
        ARRAY(ENUM(CardType, name="card_type_enum", create_type=True)),
        default=[]
    )
    
    player_statuses: Mapped[List[PlayerStatus]] = mapped_column(
        ARRAY(ENUM(PlayerStatus, name="player_status_enum", create_type=True)),
        default=[]
    )
    
    coins: Mapped[int] = mapped_column(
        Integer,
        default=2
    )
    
    debt: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    
    # =============================================
    # Pending Actions
    # =============================================
    target_display_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    # Display name of the player being targeted (for UI display)
    # Note: This remains as display_name for user-facing targeting
    
    to_be_initiated: Mapped[List[ToBeInitiated]] = mapped_column(
        ARRAY(ENUM(ToBeInitiated, name="to_be_initiated_enum", create_type=True)),
        default=[]
    )
    
    # =============================================
    # Timestamps
    # =============================================
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    
    # =============================================
    # Relationships
    # =============================================
    user = relationship(
        "UserAccount",
        back_populates="game_states"
    )
    
    upgrade_details = relationship(
        "ToBeInitiatedUpgradeDetails",
        back_populates="game_state",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    # =============================================
    # Helper Properties
    # =============================================
    @property
    def is_alive(self) -> bool:
        """Check if player is alive in this game."""
        return PlayerStatus.ALIVE in (self.player_statuses or [])
    
    @property
    def is_dead(self) -> bool:
        """Check if player is dead in this game."""
        return PlayerStatus.DEAD in (self.player_statuses or [])
    
    @property
    def card_count(self) -> int:
        """Number of cards (influences) remaining."""
        return len(self.card_types or [])
    
    @property
    def has_pending_action(self) -> bool:
        """Check if player has a pending action."""
        return len(self.to_be_initiated or []) > 0
    
    def __repr__(self):
        status = "ALIVE" if self.is_alive else "DEAD"
        return f"<PlayerGameState {self.id} user={self.user_id} session={self.session_id} [{status}]>"
    
    def to_dict(self, include_cards: bool = False) -> dict:
        """Convert to dictionary.
        
        Args:
            include_cards: If True, include card types (only for owner or admin).
        """
        result = {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'session_id': self.session_id,
            'coins': self.coins,
            'debt': self.debt,
            'is_alive': self.is_alive,
            'card_count': self.card_count,
            'player_statuses': [s.value for s in (self.player_statuses or [])],
            'target_display_name': self.target_display_name,
            'to_be_initiated': [a.value for a in (self.to_be_initiated or [])],
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
        }
        
        if include_cards:
            result['card_types'] = [c.value for c in (self.card_types or [])]
        
        return result


class ToBeInitiatedUpgradeDetails(db.Model):
    """
    Upgrade details for pending actions.
    
    Stores additional options for special action upgrades.
    """
    
    __bind_key__ = 'db_players'
    __tablename__ = 'gs_pending_action_upgrades_table_orm'
    
    # =============================================
    # Identity (FK to PlayerGameState)
    # =============================================
    game_state_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gs_player_game_state_table_orm.id", ondelete="CASCADE"),
        primary_key=True
    )
    
    # =============================================
    # Upgrade Options
    # =============================================
    assassination_priority: Mapped[Optional[CardType]] = mapped_column(
        ENUM(CardType, name="card_type_enum", create_type=True),
        nullable=True
    )
    
    kleptomania_steal: Mapped[bool] = mapped_column(default=False)
    trigger_identity_crisis: Mapped[bool] = mapped_column(default=False)
    identify_as_tax_liability: Mapped[bool] = mapped_column(default=False)
    tax_debt: Mapped[int] = mapped_column(default=0)
    
    # =============================================
    # Relationships
    # =============================================
    game_state = relationship(
        "PlayerGameState",
        back_populates="upgrade_details"
    )
    
    def __repr__(self):
        return f"<UpgradeDetails game_state={self.game_state_id}>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'game_state_id': str(self.game_state_id),
            'assassination_priority': self.assassination_priority.value if self.assassination_priority else None,
            'kleptomania_steal': self.kleptomania_steal,
            'trigger_identity_crisis': self.trigger_identity_crisis,
            'identify_as_tax_liability': self.identify_as_tax_liability,
            'tax_debt': self.tax_debt,
        }
