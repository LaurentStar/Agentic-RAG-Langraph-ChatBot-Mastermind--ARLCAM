"""
Game Server Constants.

All enums and constant values used across the game server.
"""

from enum import Enum, IntEnum


# =============================================
# IMPORTANT: Enum Naming Convention for PostgreSQL
# =============================================
# SQLAlchemy's postgresql.ENUM uses the Python enum MEMBER NAMES
# (uppercase, e.g., PHASE1_ACTIONS) for PostgreSQL storage.
# The .value attribute (lowercase, e.g., 'phase1_actions') is used
# for API serialization only.
#
# When writing SQL migrations to add new enum values:
#   CORRECT:   ALTER TYPE game_phase_enum ADD VALUE 'NEW_MEMBER';
#   INCORRECT: ALTER TYPE game_phase_enum ADD VALUE 'new_member';
#
# The database stores the MEMBER NAME, not the .value!
# =============================================


# =============================================
# Card and Player Enums (Existing)
# =============================================

class CardType(str, Enum):
    """Card types in Coup."""
    DUKE = 'duke'
    ASSASSIN = 'assassin'
    CAPTAIN = 'captain'
    AMBASSADOR = 'ambassador'
    CONTESSA = 'contessa'
    DEFAULT = 'default'


class SocialMediaPlatform(str, Enum):
    """Supported social media platforms."""
    TWITTER = 'twitter'
    DISCORD = 'discord'
    SLACK = 'slack'
    FACEBOOK = 'facebook'
    BLUESKY = 'bluesky'
    EMAIL = 'email'
    DEFAULT = 'default'


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
    ACT_INCOME = 'act_income'
    ACT_TAX = 'act_tax'
    OCCURRENCE_ASSASSINATED = 'occurrence_assassinated'
    NO_EVENT = 'no_event'


class SpecialAbilityCost(IntEnum):
    """Coin costs for special abilities."""
    COUP = 7
    ASSASSINATE = 3
    ASSASSINATE_UPGRADE = 2
    STEAL = 0
    STEAL_UPGRADE = 1
    SWAP_INFLUENCE = 0
    SWAP_INFLUENCE_UPGRADE = 4


# =============================================
# Player Type and Privileges (New)
# =============================================

class PlayerType(str, Enum):
    """Types of players in the game."""
    HUMAN = 'human'
    LLM_AGENT = 'llm_agent'
    ADMIN = 'admin'


class GamePrivilege(str, Enum):
    """Granular permissions for non-admin players."""
    START_GAME = 'start_game'
    END_GAME = 'end_game'
    KICK_PLAYER = 'kick_player'
    MANAGE_BROADCASTS = 'manage_broadcasts'
    MANAGE_CONFIG = 'manage_config'
    VIEW_ALL_CARDS = 'view_all_cards'


# =============================================
# Game Session Enums (New)
# =============================================

class SessionStatus(str, Enum):
    """Game session status."""
    WAITING = 'waiting'
    ACTIVE = 'active'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'


class GamePhase(str, Enum):
    """Phases within an hourly turn.
    
    Note: ENDING is a terminal phase, not part of the regular turn cycle.
    It occurs after the game ends to allow rematch requests.
    """
    PHASE1_ACTIONS = 'phase1_actions'
    LOCKOUT1 = 'lockout1'
    PHASE2_REACTIONS = 'phase2_reactions'
    LOCKOUT2 = 'lockout2'
    BROADCAST = 'broadcast'
    ENDING = 'ending'  # Terminal phase - NOT in PHASE_ORDER


class ReactionType(str, Enum):
    """Types of reactions to pending actions."""
    CHALLENGE = 'challenge'
    BLOCK = 'block'
    PASS = 'pass'


class CoupAction(str, Enum):
    """All possible Coup actions."""
    INCOME = 'income'
    FOREIGN_AID = 'foreign_aid'
    COUP = 'coup'
    TAX = 'tax'
    STEAL = 'steal'
    ASSASSINATE = 'assassinate'
    SWAP = 'swap'


# =============================================
# Phase Timing Constants
# =============================================

PHASE_DURATIONS_MINUTES = {
    GamePhase.PHASE1_ACTIONS: 50,
    GamePhase.LOCKOUT1: 10,
    GamePhase.PHASE2_REACTIONS: 20,
    GamePhase.LOCKOUT2: 10,
    GamePhase.BROADCAST: 1,
    GamePhase.ENDING: 5,  # Terminal phase - rematch window duration
}

PHASE_ORDER = [
    GamePhase.PHASE1_ACTIONS,
    GamePhase.LOCKOUT1,
    GamePhase.PHASE2_REACTIONS,
    GamePhase.LOCKOUT2,
    GamePhase.BROADCAST,
]


# =============================================
# Action Resolution Enums and Mappings
# =============================================

class ResolutionOutcome(str, Enum):
    """Possible outcomes of action resolution."""
    SUCCESS = 'success'
    BLOCKED = 'blocked'
    CHALLENGED_WON = 'challenged_won'
    CHALLENGED_LOST = 'challenged_lost'
    FAILED = 'failed'


# Maps CoupAction to ToBeInitiated for pending action storage
ACTION_TO_INITIATED = {
    CoupAction.INCOME: ToBeInitiated.ACT_INCOME,
    CoupAction.FOREIGN_AID: ToBeInitiated.ACT_FOREIGN_AID,
    CoupAction.COUP: ToBeInitiated.ACT_COUP,
    CoupAction.TAX: ToBeInitiated.ACT_TAX,
    CoupAction.STEAL: ToBeInitiated.ACT_STEAL,
    CoupAction.ASSASSINATE: ToBeInitiated.ACT_ASSASSINATION,
    CoupAction.SWAP: ToBeInitiated.ACT_SWAP_INFLUENCE,
}

# Cards that can block each action
BLOCK_ROLES = {
    ToBeInitiated.ACT_FOREIGN_AID: [CardType.DUKE],
    ToBeInitiated.ACT_ASSASSINATION: [CardType.CONTESSA],
    ToBeInitiated.ACT_STEAL: [CardType.AMBASSADOR, CardType.CAPTAIN],
}

# Roles required for each action (for challenge resolution)
ACTION_ROLES = {
    ToBeInitiated.ACT_TAX: CardType.DUKE,
    ToBeInitiated.ACT_ASSASSINATION: CardType.ASSASSIN,
    ToBeInitiated.ACT_STEAL: CardType.CAPTAIN,
    ToBeInitiated.ACT_SWAP_INFLUENCE: CardType.AMBASSADOR,
}

# Coin costs for actions
ACTION_COSTS = {
    ToBeInitiated.ACT_COUP: 7,
    ToBeInitiated.ACT_ASSASSINATION: 3,
}

# Actions that require a target
TARGETED_ACTIONS = [
    CoupAction.COUP,
    CoupAction.STEAL,
    CoupAction.ASSASSINATE,
]


# =============================================
# Platform Configuration
# =============================================

# Character limits per platform for broadcasting
PLATFORM_CHAR_LIMITS = {
    SocialMediaPlatform.TWITTER: 280,
    SocialMediaPlatform.DISCORD: 2000,
    SocialMediaPlatform.SLACK: 4000,
    SocialMediaPlatform.BLUESKY: 300,
    SocialMediaPlatform.EMAIL: 10000,
    SocialMediaPlatform.DEFAULT: 2000,
}

