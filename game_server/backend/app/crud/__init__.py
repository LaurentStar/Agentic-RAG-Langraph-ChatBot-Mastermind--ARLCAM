"""
CRUD Layer.

Provides predictable data access patterns for all database tables.
Services should use CRUD operations instead of direct ORM queries.

Architecture:
    Routes -> Services -> CRUD -> ORM Models -> Database
"""

from app.crud.base import BaseCRUD
from app.crud.user_account_crud import UserAccountCRUD
from app.crud.player_profile_crud import PlayerProfileCRUD
from app.crud.player_game_state_crud import PlayerGameStateCRUD
from app.crud.oauth_identity_crud import OAuthIdentityCRUD
from app.crud.account_flag_crud import AccountFlagCRUD
from app.crud.account_link_request_crud import AccountLinkRequestCRUD
from app.crud.agent_profile_crud import AgentProfileCRUD
from app.crud.game_session_crud import GameSessionCRUD
from app.crud.reaction_crud import ReactionCRUD
from app.crud.turn_result_crud import TurnResultCRUD
from app.crud.chat_message_crud import ChatMessageCRUD
from app.crud.broadcast_destination_crud import BroadcastDestinationCRUD
from app.crud.chat_bot_endpoint_crud import ChatBotEndpointCRUD
from app.crud.game_server_log_crud import GameServerLogCRUD
from app.crud.upgrade_details_crud import UpgradeDetailsCRUD

__all__ = [
    "BaseCRUD",
    "UserAccountCRUD",
    "PlayerProfileCRUD",
    "PlayerGameStateCRUD",
    "OAuthIdentityCRUD",
    "AccountFlagCRUD",
    "AccountLinkRequestCRUD",
    "AgentProfileCRUD",
    "GameSessionCRUD",
    "ReactionCRUD",
    "TurnResultCRUD",
    "ChatMessageCRUD",
    "BroadcastDestinationCRUD",
    "ChatBotEndpointCRUD",
    "GameServerLogCRUD",
    "UpgradeDetailsCRUD",
]
