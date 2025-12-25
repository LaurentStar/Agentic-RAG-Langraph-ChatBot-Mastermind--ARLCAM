"""
Game API.

In-game actions, reactions, state, session interactions, and chat.
"""

from app.apis.game.actions_ns import actions_ns
from app.apis.game.chat_ns import chat_ns
from app.apis.game.reactions_ns import reactions_ns
from app.apis.game.state_ns import state_ns
from app.apis.game.game_session_ns import game_session_ns

__all__ = ["actions_ns", "chat_ns", "reactions_ns", "state_ns", "game_session_ns"]

