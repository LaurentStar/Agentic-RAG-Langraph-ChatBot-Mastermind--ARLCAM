"""
Game Server Services.

Business logic layer for the game server.

Architecture:
    Routes (APIs) -> Services (business logic) -> CRUD (data access) -> ORM Models
"""

from app.services.action_resolution_service import ActionResolutionService, action_resolution_service
from app.services.auth_service import AuthService, admin_required, jwt_required, privilege_required
from app.services.broadcast_service import BroadcastService, broadcast_service
from app.services.deck_service import DeckService, deck_service
from app.services.gameplay_service import GameplayService
from app.services.phase_transition_service import PhaseTransitionService, phase_transition_service
from app.services.player_service import PlayerService
from app.services.reaction_service import ReactionService, reaction_service
from app.services.session_service import SessionService
from app.services.user_account_service import UserAccountService

__all__ = [
    # Auth
    "AuthService",
    "jwt_required",
    "admin_required",
    "privilege_required",
    # Account & Player
    "UserAccountService",
    "PlayerService",
    "SessionService",
    # Game Logic
    "GameplayService",
    "DeckService",
    "deck_service",
    "ActionResolutionService",
    "action_resolution_service",
    "ReactionService",
    "reaction_service",
    "PhaseTransitionService",
    "phase_transition_service",
    "BroadcastService",
    "broadcast_service",
]

