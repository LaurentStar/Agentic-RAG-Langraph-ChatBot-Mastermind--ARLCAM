from enum import Enum, IntEnum
from pydantic import BaseModel, Field

#-------#
# ENUMS #
#-------#
class AnnouncementStates(str,Enum):
    RETRIEVE = "retrieve"
    GRADE_DOCUMENTS = "grade_documents"
    GENERATE = "generate"
    WEBSEARCH = "websearch"
    BROADCAST_NORMAL = 'broadcast_normal'

class BotActions(str, Enum):
    DETERMINE_IF_CHAT_MESSAGE_OR_ANNOUNCEMENT = 'determine_if_chat_message_or_annoncement'
    DECIDE_TO_RESPONSE = 'decide_to_response'

class Tone(str,Enum):
    AMUSED = 'amused'           ; ANGRY = 'angry'           ; ANXIOUS = 'anxious'       ; ACCUSATORY = 'accusatory'
    AGGRESSIVE = 'aggressive'   ; APOLOGETIC = 'apologetic' ; APATHETIC = 'apathetic'   ; ASSERTIVE = 'assertive'
    BITTER = 'bitter'           ; BOLD = 'bold'             ; BOORISH = 'boorish'       ; BEWILDERED = 'bewildered'
    CALM = 'calm'               ; CRITICAL = 'critical'     ; CHEERFUL = 'cheerful'     ; CONFUSED = 'confused'
    ESSIMISTIC = 'essimistic'   ; EXCITED = 'excited'
    FORMAL='formal'             ; FOREBODING = 'foreboding'
    HAPPY = 'happy'
    SAD = 'sad'                 ; SEDUCTIVE = 'seductive'
    TENDER='tender'             ; TENSE = 'tense'
    UNSURE = 'unsure'
    NOT_WITHIN_SCOPE = 'not_within_scope'

class SocialMediaPlatform(str,Enum):
    TWITTER = 'twitter'
    DISCORD = 'discord'  
    SLACK = 'slack'
    FACEBOOK = 'facebook'
    BLUESKY = 'bluesky'
    EMAIL = 'email'
    DEFUALT = 'defualt'

class PromptFileExtension(str, Enum):
    MARKDOWN = ".md"

class AllowedUploadFileTypes(str, Enum):
    CSV = '.csv'
    EXCEL = '.xlsx'

class Node(str, Enum):
    INITIALIZATION = 'initialization'


class AgentModulator(str, Enum):
    """Knobs that influence agent playstyle/decision tendencies."""

    AGGRESSION = "aggression"              # preference for offensive actions (coup/assassinate)
    BLUFF_CONFIDENCE = "bluff_confidence"  # willingness to claim roles without backing
    CHALLENGE_TENDENCY = "challenge_tendency"  # likelihood to challenge opponent claims
    BLOCK_TENDENCY = "block_tendency"      # likelihood to block steal/aid/assassinate
    RISK_TOLERANCE = "risk_tolerance"      # comfort taking risky lines (e.g., low coins challenges)
    LLM_RELIANCE = "llm_reliance"          # preference for LLM vs heuristics (0=heuristics, 1=LLM)

#---------------------------#
# COUP GAME ENUMS / CONSTANTS
#---------------------------#

class DecisionType(str, Enum):
    """Top-level routing for agent decisions in Coup."""
    ACTION = "action"      # Your turn - pick an action
    REACT = "react"        # Voluntary reaction to others
    RESOLVE = "resolve"    # Forced completion


class ReactionType(str, Enum):
    """Sub-types for REACT decisions."""
    CHALLENGE = "challenge"              # Challenge an action claim
    CHALLENGE_BLOCK = "challenge_block"  # Challenge a block claim
    BLOCK = "block"                      # Block an action targeting you


class ResolutionType(str, Enum):
    """Sub-types for RESOLVE decisions."""
    REVEAL_CARD = "reveal_card"       # Choose card to lose
    EXCHANGE_CARDS = "exchange_cards"  # Ambassador - pick cards to keep


class CoupAction(str, Enum):
    """All actions an agent can take or respond with in Coup."""

    INCOME = "income"
    FOREIGN_AID = "foreign_aid"
    COUP = "coup"
    TAX = "tax"
    ASSASSINATE = "assassinate"
    STEAL = "steal"
    EXCHANGE = "exchange"

    # Reactions
    BLOCK_STEAL = "block_steal"
    BLOCK_FOREIGN_AID = "block_foreign_aid"
    BLOCK_ASSASSINATE = "block_assassinate"
    CHALLENGE = "challenge"
    PASS = "pass"


class InfluenceCard(str, Enum):
    """Influence cards in the base Coup deck."""

    DUKE = "duke"
    ASSASSIN = "assassin"
    CAPTAIN = "captain"
    AMBASSADOR = "ambassador"
    CONTESSA = "contessa"

#----------------------------------#
# HOURLY COUP EVENT ROUTER ENUMS   #
#----------------------------------#

class EventType(str, Enum):
    """Types of events that can be received by the LangGraph server."""
    # Core events
    CHAT_MESSAGE = "chat_message"                  # Player chat from any platform
    GAME_STATE_UPDATE = "game_state_update"        # Game state changed
    PLAYER_ACTION_CHANGE = "player_action_change"  # Another player changed their pending action
    SUPERVISOR_INSTRUCTION = "supervisor_instruction"  # Admin command
    PROFILE_SYNC = "profile_sync"                  # Sync agent profile from DB
    BROADCAST_RESULTS = "broadcast_results"        # End-of-hour game results
    
    # Phase transition events (Two-Phase Hourly Coup)
    PHASE_TRANSITION = "phase_transition"          # Game phase changed (Phase1 -> Lockout1 -> Phase2, etc.)
    
    # Phase 2 specific events
    REACTION_REQUIRED = "reaction_required"        # "Your action is being challenged" / actions need your reaction
    REACTIONS_VISIBLE = "reactions_visible"        # "Here's who is reacting to what" - all pending reactions
    CARD_SELECTION_REQUIRED = "card_selection_required"  # Ambassador exchange or reveal selection needed


class MessageTargetType(str, Enum):
    """Who the message is being sent to (for limit tracking)."""
    LLM_ONLY = "llm_only"        # Message to LLM agents only (limit: 30)
    HUMAN_ONLY = "human_only"    # Message to humans only (limit: 150)
    MIXED = "mixed"              # Message to both LLMs and humans (limit: 30)


class UpgradeType(str, Enum):
    """Types of action upgrades available in hourly Coup."""
    ASSASSINATION_PRIORITY = "assassination_priority"  # Target specific card (Assassinate +2 coins)
    KLEPTOMANIA_STEAL = "kleptomania_steal"            # Enhanced stealing (Steal +1 coin)
    TRIGGER_IDENTITY_CRISIS = "trigger_identity_crisis"  # Force target swap (Swap +4 coins)


# Message limits per hourly turn
MESSAGE_LIMITS = {
    MessageTargetType.LLM_ONLY: 30,
    MessageTargetType.HUMAN_ONLY: 150,
    MessageTargetType.MIXED: 30,
}


class GamePhase(str, Enum):
    """
    The five phases of each hourly Coup round.
    
    The game server sends PHASE_TRANSITION events when these change.
    """
    PHASE1_ACTIONS = "phase1_actions"      # 50 min - Set pending actions
    LOCKOUT1 = "lockout1"                  # 10 min - Chat only, actions locked
    PHASE2_REACTIONS = "phase2_reactions"  # 20 min - Set pending reactions
    LOCKOUT2 = "lockout2"                  # 10 min - Chat only, reactions locked
    BROADCAST = "broadcast"                # 1 min - Results announced


class ConditionalRuleType(str, Enum):
    """Available conditional reaction rules."""
    
    # Challenge rules - challenge any claim of a specific role
    CHALLENGE_ANY_DUKE = "challenge_any_duke"
    CHALLENGE_ANY_ASSASSIN = "challenge_any_assassin"
    CHALLENGE_ANY_CAPTAIN = "challenge_any_captain"
    CHALLENGE_ANY_AMBASSADOR = "challenge_any_ambassador"
    CHALLENGE_ANY_CONTESSA = "challenge_any_contessa"
    
    # Block rules - block specific actions targeting me
    BLOCK_ANY_STEAL_ON_ME = "block_any_steal_on_me"
    BLOCK_ANY_ASSASSINATION_ON_ME = "block_any_assassination_on_me"
    BLOCK_ANY_FOREIGN_AID = "block_any_foreign_aid"
    
    # Defensive rules
    ALWAYS_BLOCK_ASSASSINATION = "always_block_assassination"
    ALWAYS_CHALLENGE_UPGRADED_ACTIONS = "always_challenge_upgraded_actions"


#----------------------------------------#
# CARD / ACTION MAPPINGS                  #
#----------------------------------------#

# Which actions each card enables
ROLE_TO_ACTION = {
    InfluenceCard.DUKE: [CoupAction.TAX, CoupAction.BLOCK_FOREIGN_AID],
    InfluenceCard.ASSASSIN: [CoupAction.ASSASSINATE],
    InfluenceCard.CAPTAIN: [CoupAction.STEAL, CoupAction.BLOCK_STEAL],
    InfluenceCard.AMBASSADOR: [CoupAction.EXCHANGE, CoupAction.BLOCK_STEAL],
    InfluenceCard.CONTESSA: [CoupAction.BLOCK_ASSASSINATE],
}

# Which role is required for each action
ACTION_TO_ROLE = {
    CoupAction.TAX: InfluenceCard.DUKE,
    CoupAction.BLOCK_FOREIGN_AID: InfluenceCard.DUKE,
    CoupAction.ASSASSINATE: InfluenceCard.ASSASSIN,
    CoupAction.STEAL: InfluenceCard.CAPTAIN,
    CoupAction.BLOCK_STEAL: [InfluenceCard.CAPTAIN, InfluenceCard.AMBASSADOR],  # Multiple can block
    CoupAction.EXCHANGE: InfluenceCard.AMBASSADOR,
    CoupAction.BLOCK_ASSASSINATE: InfluenceCard.CONTESSA,
}

# Actions that don't require claiming a role
UNCLAIMED_ACTIONS = {CoupAction.INCOME, CoupAction.FOREIGN_AID, CoupAction.COUP}

# Actions that require a target
TARGETED_ACTIONS = {CoupAction.COUP, CoupAction.ASSASSINATE, CoupAction.STEAL}

# Base cost of actions (without upgrades)
ACTION_COST = {
    CoupAction.COUP: 7,
    CoupAction.ASSASSINATE: 3,
}


#----------------------------------------#
# AGENT PROFILE DEFAULTS                  #
#----------------------------------------#

# Default modulators for different play styles
PLAY_STYLE_MODULATORS = {
    "aggressive": {
        AgentModulator.AGGRESSION: 0.8,
        AgentModulator.BLUFF_CONFIDENCE: 0.6,
        AgentModulator.CHALLENGE_TENDENCY: 0.7,
        AgentModulator.BLOCK_TENDENCY: 0.4,
        AgentModulator.RISK_TOLERANCE: 0.7,
        AgentModulator.LLM_RELIANCE: 0.6,
    },
    "defensive": {
        AgentModulator.AGGRESSION: 0.3,
        AgentModulator.BLUFF_CONFIDENCE: 0.2,
        AgentModulator.CHALLENGE_TENDENCY: 0.3,
        AgentModulator.BLOCK_TENDENCY: 0.8,
        AgentModulator.RISK_TOLERANCE: 0.3,
        AgentModulator.LLM_RELIANCE: 0.2,
    },
    "balanced": {
        AgentModulator.AGGRESSION: 0.5,
        AgentModulator.BLUFF_CONFIDENCE: 0.4,
        AgentModulator.CHALLENGE_TENDENCY: 0.5,
        AgentModulator.BLOCK_TENDENCY: 0.5,
        AgentModulator.RISK_TOLERANCE: 0.5,
        AgentModulator.LLM_RELIANCE: 0.5,
    },
    "chaotic": {
        AgentModulator.AGGRESSION: 0.6,
        AgentModulator.BLUFF_CONFIDENCE: 0.8,
        AgentModulator.CHALLENGE_TENDENCY: 0.7,
        AgentModulator.BLOCK_TENDENCY: 0.4,
        AgentModulator.RISK_TOLERANCE: 0.9,
        AgentModulator.LLM_RELIANCE: 0.8,
    },
    "cautious": {
        AgentModulator.AGGRESSION: 0.2,
        AgentModulator.BLUFF_CONFIDENCE: 0.2,
        AgentModulator.CHALLENGE_TENDENCY: 0.2,
        AgentModulator.BLOCK_TENDENCY: 0.6,
        AgentModulator.RISK_TOLERANCE: 0.2,
        AgentModulator.LLM_RELIANCE: 0.3,
    },
}

# Default personalities
PERSONALITIES = {
    "friendly": "Warm and approachable. Tries to build alliances and avoids direct confrontation when possible.",
    "cunning": "Calculating and strategic. Always looking for an angle and willing to deceive.",
    "aggressive": "Bold and direct. Prefers action over talk and isn't afraid to make enemies.",
    "paranoid": "Suspicious of everyone. Questions everything and trusts no one.",
    "charming": "Charismatic and persuasive. Uses wit and charm to manipulate others.",
    "stoic": "Calm and unreadable. Gives little away and speaks only when necessary.",
}


#----------------------------------------#
# BUILDING BLOCK STUCTURED OUTPUT MODELS #
#----------------------------------------#
class UnitBall_SO(BaseModel):
    unit_ball_score : float = Field(
        description="A score that goes from -1 to 1",
        ge=-1.0, le=1.0
    )