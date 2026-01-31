"""
Database ORM Models (Read-Only).

SQLAlchemy ORM models that mirror the game server's PostgreSQL tables.
These are used for READ-ONLY queries - writes should go through game server API.

Tables (Three-Tier Architecture):
- user_account: User identity and authentication
- player_profile: Persistent stats and progression
- player_game_state: Per-session game state (cards, coins, actions)
- to_be_initiated_upgrade_details: Upgrade details for actions
"""

from enum import Enum
from typing import List, Optional
import uuid

from sqlalchemy import Column, String, Integer, Boolean, ARRAY, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

# Base class for all ORM models
Base = declarative_base()


# =============================================
# Enums (matching game_server/app/constants.py)
# =============================================

class CardType(str, Enum):
    """Card types in Coup."""
    DUKE = 'duke'
    ASSASSIN = 'assassin'
    CAPTAIN = 'captain'
    AMBASSADOR = 'ambassador'
    CONTESSA = 'countessa'  # Note: spelled 'countessa' in game_server DB
    DEFAULT = 'defualt'     # Note: typo matches game_server DB


class PlayerStatus(str, Enum):
    """Player status flags."""
    DEAD = 'dead'
    ALIVE = 'alive'
    ACTING = 'acting'
    HIDDEN = 'hidden'
    WAITING = 'waiting'
    DISABLED = 'disabled'
    EMPOWERED = 'empowered'
    CLAIRAUDIENT = 'clairaudient'


class ToBeInitiated(str, Enum):
    """Pending action types."""
    ACT_ASSASSINATION = 'act_assassination'
    ACT_FOREIGN_AID = 'act_foreign_aid'
    ACT_COUP = 'act_coup'
    ACT_STEAL = 'act_steal'
    ACT_BLOCK = 'act_block'
    ACT_SWAP_INFLUENCE = 'act_swap_influence'
    ACT_TAX = 'act_tax'
    OCCURRENCE_ASSASSINATED = 'occurance_assassinated'  # Note: typo matches DB
    NO_EVENT = 'no_event'


class SocialMediaPlatform(str, Enum):
    """Social media platforms."""
    TWITTER = 'twitter'
    DISCORD = 'discord'
    SLACK = 'slack'
    FACEBOOK = 'facebook'
    BLUESKY = 'bluesky'
    EMAIL = 'email'
    DEFAULT = 'defualt'  # Note: typo matches game_server DB


class PlayerType(str, Enum):
    """Player types."""
    HUMAN = 'human'
    LLM_AGENT = 'llm_agent'
    ADMIN = 'admin'


# =============================================
# SQLAlchemy ORM Models (Three-Tier Architecture)
# =============================================

class UserAccount(Base):
    """
    User Account ORM model mapping to user_account table.
    
    This is the permanent identity record - auth, account status, platform loyalty.
    Read-only from lang_graph_server perspective.
    """
    __tablename__ = 'gs_user_account_table_orm'
    
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), nullable=True)
    player_type = Column(String(20), default='human')
    account_status = Column(String(20), default='active')
    social_media_platforms = Column(ARRAY(String))
    preferred_social_media_platform = Column(String, nullable=True)
    social_media_platform_display_name = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True))
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    game_states = relationship("PlayerGameState", back_populates="user")
    
    @property
    def is_active(self) -> bool:
        """Check if account is active."""
        return self.account_status == 'active'
    
    @property
    def is_agent(self) -> bool:
        """Check if user is an LLM agent."""
        return self.player_type == PlayerType.LLM_AGENT.value
    
    @property
    def platform_enum(self) -> SocialMediaPlatform:
        """Get preferred social media platform as enum."""
        try:
            return SocialMediaPlatform(self.preferred_social_media_platform)
        except (ValueError, TypeError):
            return SocialMediaPlatform.DEFAULT


class PlayerGameState(Base):
    """
    Player Game State ORM model mapping to player_game_state table.
    
    This is per-session transient state - coins, cards, pending actions.
    Read-only from lang_graph_server perspective.
    """
    __tablename__ = 'gs_player_game_state_table_orm'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('gs_user_account_table_orm.user_id'), nullable=False)
    session_id = Column(String, nullable=True)
    card_types = Column(ARRAY(String))
    player_statuses = Column(ARRAY(String))
    coins = Column(Integer, default=2)
    debt = Column(Integer, default=0)
    target_display_name = Column(String, nullable=True)
    to_be_initiated = Column(ARRAY(String))
    joined_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("UserAccount", back_populates="game_states")
    
    @property
    def is_alive(self) -> bool:
        """Check if player is alive."""
        return PlayerStatus.ALIVE.value in (self.player_statuses or [])
    
    @property
    def pending_action(self) -> Optional[ToBeInitiated]:
        """Get the primary pending action (first non-NO_EVENT action)."""
        for action_str in (self.to_be_initiated or []):
            if action_str != ToBeInitiated.NO_EVENT.value:
                try:
                    return ToBeInitiated(action_str)
                except ValueError:
                    continue
        return None
    
    @property
    def has_pending_action(self) -> bool:
        """Check if player has a pending action."""
        return self.pending_action is not None
    
    @property
    def card_types_enum(self) -> List[CardType]:
        """Get card types as enum values."""
        result = []
        for card in (self.card_types or []):
            try:
                result.append(CardType(card))
            except ValueError:
                pass
        return result
    
    @property
    def player_statuses_enum(self) -> List[PlayerStatus]:
        """Get player statuses as enum values."""
        result = []
        for status in (self.player_statuses or []):
            try:
                result.append(PlayerStatus(status))
            except ValueError:
                pass
        return result
    
    @property
    def card_count(self) -> int:
        """Number of cards remaining."""
        return len(self.card_types or [])


class UpgradeDetails(Base):
    """
    Upgrade details ORM model mapping to to_be_initiated_upgrade_details table.
    
    Contains the upgrade configuration for a player's pending action.
    Now linked to PlayerGameState via game_state_id.
    """
    __tablename__ = 'gs_pending_action_upgrades_table_orm'
    
    game_state_id = Column(UUID(as_uuid=True), ForeignKey('gs_player_game_state_table_orm.id'), primary_key=True)
    assassination_priority = Column(String, nullable=True)
    kleptomania_steal = Column(Boolean, default=False)
    trigger_identity_crisis = Column(Boolean, default=False)
    identify_as_tax_liability = Column(Boolean, default=False)
    tax_debt = Column(Integer, default=0)
    
    @property
    def has_any_upgrade(self) -> bool:
        """Check if any upgrade is active."""
        return (
            self.assassination_priority is not None or
            self.kleptomania_steal or
            self.trigger_identity_crisis or
            self.identify_as_tax_liability or
            (self.tax_debt or 0) > 0
        )
    
    @property
    def assassination_priority_enum(self) -> Optional[CardType]:
        """Get assassination priority as enum."""
        if not self.assassination_priority:
            return None
        try:
            return CardType(self.assassination_priority)
        except ValueError:
            return None


# =============================================
# Legacy Aliases (for backwards compatibility)
# =============================================
# These map to the new models for code that still uses old names

# The old Player model combined identity + game state
# New code should use UserAccount + PlayerGameState separately
Player = PlayerGameState  # Game state operations use PlayerGameState
PlayerModel = PlayerGameState
UpgradeDetailsModel = UpgradeDetails
