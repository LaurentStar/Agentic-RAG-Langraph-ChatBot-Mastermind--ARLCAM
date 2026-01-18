"""
Game Session ORM Model.

SQLAlchemy model for game session management.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import String
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import CardType, GamePhase, SessionStatus
from app.extensions import db


class GameSession(db.Model):
    """Game session table ORM model."""
    
    __bind_key__ = 'db_players'
    __tablename__ = 'game_session_table_orm'
    
    # ---------------------- Identity ---------------------- #
    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    session_name: Mapped[str] = mapped_column(String, nullable=False)
    
    # ---------------------- Phase Timing ---------------------- #
    current_phase: Mapped[GamePhase] = mapped_column(
        postgresql.ENUM(GamePhase, name="game_phase_enum", create_type=True),
        default=GamePhase.PHASE1_ACTIONS
    )
    phase_end_time: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    turn_number: Mapped[int] = mapped_column(default=1)
    turn_limit: Mapped[int] = mapped_column(default=10)  # 0 = unlimited
    
    # ---------------------- Game Config ---------------------- #
    max_players: Mapped[int] = mapped_column(default=6)
    hourly_duration_minutes: Mapped[int] = mapped_column(default=60)  # Legacy, kept for reference
    upgrades_enabled: Mapped[bool] = mapped_column(default=True)
    
    # ---------------------- Phase Durations (minutes) ---------------------- #
    # Column names match migration: phase{N}_{name}_duration for clarity
    phase1_action_duration: Mapped[int] = mapped_column(default=50)      # Discussion & action selection
    phase2_lockout_duration: Mapped[int] = mapped_column(default=10)     # Server processes actions
    phase3_reaction_duration: Mapped[int] = mapped_column(default=20)    # Reactions (challenge/block)
    phase4_lockout_duration: Mapped[int] = mapped_column(default=10)     # Server resolves outcomes
    phase5_broadcast_duration: Mapped[int] = mapped_column(default=1)    # Results announcement
    phase6_ending_duration: Mapped[int] = mapped_column(default=5)       # Rematch window
    
    # ---------------------- Rematch Tracking ---------------------- #
    rematch_count: Mapped[int] = mapped_column(default=0)  # Max 3 rematches allowed
    winners: Mapped[List[str]] = mapped_column(
        postgresql.ARRAY(String),
        default=[]
    )  # Winner display names
    
    # ---------------------- Status ---------------------- #
    is_game_started: Mapped[bool] = mapped_column(default=False)
    status: Mapped[SessionStatus] = mapped_column(
        postgresql.ENUM(SessionStatus, name="session_status_enum", create_type=True),
        default=SessionStatus.WAITING
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    # ---------------------- Platform Bindings ---------------------- #
    # Discord channel ID bound to this session (for cross-platform chat)
    discord_channel_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # Slack channel ID bound to this session
    slack_channel_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # ---------------------- Deck State ---------------------- #
    deck_state: Mapped[List[CardType]] = mapped_column(
        postgresql.ARRAY(postgresql.ENUM(CardType, name="card_type_enum", create_type=True)),
        default=[]
    )
    revealed_cards: Mapped[List[CardType]] = mapped_column(
        postgresql.ARRAY(postgresql.ENUM(CardType, name="card_type_enum", create_type=True)),
        default=[]
    )
    
    # ---------------------- Relationships ---------------------- #
    players = relationship("Player", backref="session", lazy="dynamic")
    broadcast_destinations = relationship(
        "BroadcastDestination",
        back_populates="session",
        cascade="all, delete-orphan"
    )
    
    # ---------------------- Helper Properties ---------------------- #
    @property
    def is_active(self) -> bool:
        """Check if game is currently active."""
        return self.status == SessionStatus.ACTIVE and self.is_game_started
    
    @property
    def is_full(self) -> bool:
        """Check if session has reached max players."""
        return self.players.count() >= self.max_players
    
    @property
    def has_reached_turn_limit(self) -> bool:
        """Check if game has reached turn limit."""
        if self.turn_limit == 0:
            return False
        return self.turn_number > self.turn_limit
    
    def get_phase_duration(self, phase: GamePhase) -> int:
        """
        Get duration in minutes for a specific phase.
        
        Args:
            phase: The game phase
        
        Returns:
            Duration in minutes
        """
        phase_durations = {
            GamePhase.PHASE1_ACTIONS: self.phase1_action_duration,
            GamePhase.LOCKOUT1: self.phase2_lockout_duration,
            GamePhase.PHASE2_REACTIONS: self.phase3_reaction_duration,
            GamePhase.LOCKOUT2: self.phase4_lockout_duration,
            GamePhase.BROADCAST: self.phase5_broadcast_duration,
            GamePhase.ENDING: self.phase6_ending_duration,
        }
        return phase_durations.get(phase, 10)  # Default 10 if unknown

