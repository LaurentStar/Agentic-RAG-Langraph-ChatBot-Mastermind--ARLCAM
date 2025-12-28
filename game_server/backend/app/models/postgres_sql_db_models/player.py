"""
Player ORM Models.

SQLAlchemy models for player-related tables.
"""

from typing import List, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import (
    CardType,
    GamePrivilege,
    PlayerStatus,
    PlayerType,
    SocialMediaPlatform,
    ToBeInitiated,
)
from app.extensions import db


class Player(db.Model):
    """Player table ORM model."""
    
    __bind_key__ = 'db_players'
    __tablename__ = 'player_table_orm'
    
    # ---------------------- Player Identity ---------------------- #
    display_name: Mapped[str] = mapped_column(primary_key=True)
    social_media_platform_display_name: Mapped[str] = mapped_column(String, nullable=False)
    
    # ---------------------- Platform Loyalty ---------------------- #
    # Tracks all platforms the player has registered on (for loyalty bonuses)
    social_media_platforms: Mapped[List[SocialMediaPlatform]] = mapped_column(
        postgresql.ARRAY(postgresql.ENUM(SocialMediaPlatform, name="social_media_platform_enum", create_type=True)),
        default=[]
    )
    # Player's preferred platform (for tribalistic grouping)
    preferred_social_media_platform: Mapped[Optional[SocialMediaPlatform]] = mapped_column(
        postgresql.ENUM(SocialMediaPlatform, name="social_media_platform_enum", create_type=True),
        nullable=True
    )
    
    # ---------------------- Player Type & Auth ---------------------- #
    player_type: Mapped[PlayerType] = mapped_column(
        postgresql.ENUM(PlayerType, name="player_type_enum", create_type=True),
        default=PlayerType.HUMAN
    )
    password_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    game_privileges: Mapped[List[GamePrivilege]] = mapped_column(
        postgresql.ARRAY(postgresql.ENUM(GamePrivilege, name="game_privilege_enum", create_type=True)),
        default=[]
    )
    
    # ---------------------- Game Session ---------------------- #
    session_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("game_session_table_orm.session_id"),
        nullable=True
    )
    
    # ---------------------- Player Game State ---------------------- #
    card_types: Mapped[List[CardType]] = mapped_column(
        postgresql.ARRAY(postgresql.ENUM(CardType, name="card_type_enum", create_type=True)),
        default=[]
    )
    player_statuses: Mapped[List[PlayerStatus]] = mapped_column(
        postgresql.ARRAY(postgresql.ENUM(PlayerStatus, name="player_status_enum", create_type=True)),
        default=[]
    )
    coins: Mapped[int] = mapped_column(default=2)
    debt: Mapped[int] = mapped_column(default=0)
    
    # ---------------------- Pending Actions ---------------------- #
    target_display_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    to_be_initiated: Mapped[List[ToBeInitiated]] = mapped_column(
        postgresql.ARRAY(postgresql.ENUM(ToBeInitiated, name="to_be_initiated_enum", create_type=True)),
        default=[]
    )
    
    # ---------------------- Relationships ---------------------- #
    upgrade_details = relationship(
        "ToBeInitiatedUpgradeDetails",
        back_populates="player",
        uselist=False
    )
    agent_profile = relationship(
        "AgentProfile",
        back_populates="player",
        uselist=False
    )
    oauth_identities = relationship(
        "OAuthIdentity",
        back_populates="player",
        cascade="all, delete-orphan"
    )
    
    # ---------------------- Helper Properties ---------------------- #
    @property
    def is_alive(self) -> bool:
        """Check if player is alive."""
        return PlayerStatus.ALIVE in (self.player_statuses or [])
    
    @property
    def is_admin(self) -> bool:
        """Check if player is an admin."""
        return self.player_type == PlayerType.ADMIN
    
    def has_privilege(self, privilege: GamePrivilege) -> bool:
        """Check if player has a specific privilege."""
        if self.is_admin:
            return True
        return privilege in (self.game_privileges or [])
    
    # ---------------------- Platform Loyalty Helpers ---------------------- #
    @property
    def platform_count(self) -> int:
        """Number of platforms registered on."""
        return len(self.social_media_platforms or [])
    
    @property
    def is_multi_platform(self) -> bool:
        """True if registered on 2+ platforms."""
        return self.platform_count >= 2
    
    def has_platform(self, platform: SocialMediaPlatform) -> bool:
        """Check if player has registered on a specific platform."""
        return platform in (self.social_media_platforms or [])


class ToBeInitiatedUpgradeDetails(db.Model):
    """Upgrade details for pending actions."""
    
    __bind_key__ = 'db_players'
    __tablename__ = 'to_be_initiated_upgrade_details_table_orm'
    
    # ---------------------- Identity ---------------------- #
    display_name: Mapped[str] = mapped_column(
        ForeignKey("player_table_orm.display_name"),
        primary_key=True
    )
    
    # ---------------------- Upgrade Options ---------------------- #
    assassination_priority: Mapped[Optional[CardType]] = mapped_column(
        postgresql.ENUM(CardType, name="card_type_enum", create_type=True),
        nullable=True
    )
    kleptomania_steal: Mapped[bool] = mapped_column(default=False)
    trigger_identity_crisis: Mapped[bool] = mapped_column(default=False)
    identify_as_tax_liability: Mapped[bool] = mapped_column(default=False)
    tax_debt: Mapped[int] = mapped_column(default=0)
    
    # ---------------------- Relationships ---------------------- #
    player = relationship("Player", back_populates="upgrade_details")

