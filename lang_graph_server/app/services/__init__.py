"""
Services Module.

Contains business logic services for the LangGraph server.

Naming conventions:
- *_service.py: Classes with business logic (e.g., ProfileSyncService)
- *_factory.py: Factory pattern classes (e.g., CheckpointerFactory)
- *_router.py: Router pattern classes (e.g., PlatformResponseRouter)
- No suffix: Utility/helper functions (e.g., coup_heuristics.py)

Note: Imports are kept minimal at module level to avoid circular dependencies.
Import specific services directly from their modules when needed.
"""

# Only expose non-circular imports at module level
# Services that depend on agents should be imported directly from their modules

__all__ = [
    # Service classes (import from individual modules)
    "ChatService",
    "CheckpointerFactory",
    "ConditionalReactionService",
    "CoupEventService",
    "DecisionBlenderService",
    "DecisionBlender",
    "GameServerClient",
    "GameServerClientFactory",
    "InfrastructureService",
    "MessageCounterService",
    "PendingEventsDBService",
    "PlatformResponseRouter",
    "ProfileSyncService",
    "UpgradeDecisionService",
    # Utility functions
    "select_action_heuristic",
    "select_action_heuristic_with_upgrade",
    "decide_challenge_heuristic",
    "decide_block_heuristic",
    "select_reveal_heuristic",
    "select_exchange_heuristic",
    "get_blended_action",
]


def __getattr__(name):
    """Lazy import to avoid circular dependencies."""
    if name == "ChatService":
        from app.services.chat_service import ChatService
        return ChatService
    elif name == "CheckpointerFactory":
        from app.services.checkpointer_factory import CheckpointerFactory
        return CheckpointerFactory
    elif name == "ConditionalReactionService":
        from app.services.conditional_reaction_service import ConditionalReactionService
        return ConditionalReactionService
    elif name == "CoupEventService":
        from app.services.coup_event_service import CoupEventService
        return CoupEventService
    elif name in ("DecisionBlenderService", "DecisionBlender"):
        from app.services.decision_blender_service import DecisionBlenderService
        return DecisionBlenderService
    elif name == "InfrastructureService":
        from app.services.infrastructure_service import InfrastructureService
        return InfrastructureService
    elif name == "MessageCounterService":
        from app.services.message_counter_service import MessageCounterService
        return MessageCounterService
    elif name == "PendingEventsDBService":
        from app.services.pending_events_db_service import PendingEventsDBService
        return PendingEventsDBService
    elif name == "PlatformResponseRouter":
        from app.services.platform_response_router import PlatformResponseRouter
        return PlatformResponseRouter
    elif name == "ProfileSyncService":
        from app.services.profile_sync_service import ProfileSyncService
        return ProfileSyncService
    elif name == "UpgradeDecisionService":
        from app.services.upgrade_decision_service import UpgradeDecisionService
        return UpgradeDecisionService
    elif name == "GameServerClient":
        from app.services.game_server_client import GameServerClient
        return GameServerClient
    elif name == "GameServerClientFactory":
        from app.services.game_server_client import GameServerClientFactory
        return GameServerClientFactory
    elif name == "get_blended_action":
        from app.services.decision_blender_service import get_blended_action
        return get_blended_action
    elif name in ("select_action_heuristic", "select_action_heuristic_with_upgrade",
                  "decide_challenge_heuristic", "decide_block_heuristic",
                  "select_reveal_heuristic", "select_exchange_heuristic"):
        import app.services.coup_heuristics as heuristics
        return getattr(heuristics, name)
    
    raise AttributeError(f"module 'app.services' has no attribute '{name}'")
