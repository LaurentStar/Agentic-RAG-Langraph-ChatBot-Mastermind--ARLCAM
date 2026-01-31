"""
PostgreSQL ORM Models.

All SQLAlchemy models for the game server database.

Three-Tier Architecture:
- UserAccount: Identity, authentication, account status (permanent)
- PlayerProfile: Persistent stats, preferences, achievements (1:1 with UserAccount)
- PlayerGameState: Per-session game state (many per UserAccount)
"""

# Core Account Models (Three-Tier)
from app.models.postgres_sql_db_models.user_account import UserAccount, AccountStatus
from app.models.postgres_sql_db_models.player_profile import PlayerProfile
from app.models.postgres_sql_db_models.player_game_state import PlayerGameState, ToBeInitiatedUpgradeDetails

# Account Management
from app.models.postgres_sql_db_models.account_flag import AccountFlag
from app.models.postgres_sql_db_models.account_link_request import AccountLinkRequest
from app.models.postgres_sql_db_models.oauth_identity import OAuthIdentity

# Agent Configuration
from app.models.postgres_sql_db_models.agent_profile import AgentProfile

# Game Session & State
from app.models.postgres_sql_db_models.game_session import GameSession
from app.models.postgres_sql_db_models.reaction import Reaction, TurnResult as TurnResultORM

# Communication
from app.models.postgres_sql_db_models.broadcast_destination import BroadcastDestination
from app.models.postgres_sql_db_models.chat_bot_endpoint import ChatBotEndpoint
from app.models.postgres_sql_db_models.chat_message import ChatMessage

# Logging
from app.models.postgres_sql_db_models.game_server_log import GameServerLog

__all__ = [
    # Three-Tier Account Models
    "UserAccount",
    "AccountStatus",
    "PlayerProfile",
    "PlayerGameState",
    "ToBeInitiatedUpgradeDetails",
    # Account Management
    "AccountFlag",
    "AccountLinkRequest",
    "OAuthIdentity",
    # Agent
    "AgentProfile",
    # Game Session
    "GameSession",
    "Reaction",
    "TurnResultORM",
    # Communication
    "BroadcastDestination",
    "ChatBotEndpoint",
    "ChatMessage",
    # Logging
    "GameServerLog",
]
