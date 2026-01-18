"""
Game Server APIs.

Organized into domains:
- auth/    - Authentication (login, token refresh, OAuth)
- admin/   - Privileged operations (session/player management)
- account/ - Account management (linking, identities)
- game/    - Gameplay (actions, reactions, state, sessions)
- players/ - Player self-service (registration, profile)
- system/  - Infrastructure (health checks)
- ops/     - Developer operations (debugging, monitoring)
"""

# Auth
from app.apis.auth import auth_ns, oauth_ns

# Admin
from app.apis.admin import admin_session_ns, admin_player_ns, admin_flags_ns

# Account
from app.apis.account import link_ns, identity_ns

# Game
from app.apis.game import actions_ns, chat_ns, reactions_ns, state_ns, game_session_ns

# Players
from app.apis.players import player_ns

# System
from app.apis.system import health_ns

# Ops (Developer)
from app.apis.ops import status_ns, jobs_ns, connections_ns

__all__ = [
    # Auth
    "auth_ns",
    "oauth_ns",
    # Admin
    "admin_session_ns",
    "admin_player_ns",
    "admin_flags_ns",
    # Account
    "link_ns",
    "identity_ns",
    # Game
    "actions_ns",
    "chat_ns",
    "reactions_ns",
    "state_ns",
    "game_session_ns",
    # Players
    "player_ns",
    # System
    "health_ns",
    # Ops
    "status_ns",
    "jobs_ns",
    "connections_ns",
]

