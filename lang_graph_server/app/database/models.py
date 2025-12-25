"""
Database ORM Models (Read-Only).

SQLAlchemy ORM models that mirror the game server's PostgreSQL tables.
These are used for READ-ONLY queries - writes should go through game server API.

Tables:
- player_table_orm: Player data, pending actions, cards, coins
- to_be_initiated_upgrade_details_table_orm: Upgrade details for actions
"""

from enum import Enum
from typing import List, Optional

from sqlalchemy import Column, String, Integer, Boolean, ARRAY
from sqlalchemy.orm import declarative_base

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


# =============================================
# SQLAlchemy ORM Models
# =============================================

class Player(Base):
    """
    Player ORM model mapping to player_table_orm.
    
    This is a read-only view of player state from the game server.
    """
    __tablename__ = 'player_table_orm'
    
    display_name = Column(String, primary_key=True)
    social_media_platform_display_name = Column(String)
    social_media_platform = Column(String)
    card_types = Column(ARRAY(String))
    player_statuses = Column(ARRAY(String))
    coins = Column(Integer, default=0)
    debt = Column(Integer, default=0)
    target_display_name = Column(String, nullable=True)
    to_be_initiated = Column(ARRAY(String))
    
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
    def platform_enum(self) -> SocialMediaPlatform:
        """Get social media platform as enum."""
        try:
            return SocialMediaPlatform(self.social_media_platform)
        except (ValueError, TypeError):
            return SocialMediaPlatform.DEFAULT


class UpgradeDetails(Base):
    """
    Upgrade details ORM model mapping to to_be_initiated_upgrade_details_table_orm.
    
    Contains the upgrade configuration for a player's pending action.
    """
    __tablename__ = 'to_be_initiated_upgrade_details_table_orm'
    
    display_name = Column(String, primary_key=True)
    assassination_priority = Column(String, nullable=True)
    kleptomania_steal = Column(Boolean, default=False)
    trigger_identity_crisis = Column(Boolean, default=False)
    identify_as_tax_liabity = Column(Boolean, default=False)  # Note: typo matches DB
    tax_debt = Column(Integer, default=0)
    
    @property
    def has_any_upgrade(self) -> bool:
        """Check if any upgrade is active."""
        return (
            self.assassination_priority is not None or
            self.kleptomania_steal or
            self.trigger_identity_crisis or
            self.identify_as_tax_liabity or
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
# These can be removed once all code is migrated

PlayerModel = Player
UpgradeDetailsModel = UpgradeDetails
