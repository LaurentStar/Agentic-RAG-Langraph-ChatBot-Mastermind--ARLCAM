"""
Event Router Workflow.

LangGraph workflow for classifying and routing incoming events
to the appropriate handlers with checkpointing for conversation context.

Architecture:
    CLASSIFY → RESOLVE_AGENTS → (conditional) → HANDLER → FINALIZE → END

Checkpointing:
    - Conversation history is persisted per game+agent thread
    - Enables context-aware responses across multiple events
    - Thread ID format: "{game_id}:{agent_id}" or "{game_id}:broadcast"
"""

from typing import Literal

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from app.constants import EventType
from app.models.graph_state_models.event_router_state import EventRouterState


# =============================================
# Node Names
# =============================================
class EventRouterNode:
    """Node names for the event router workflow."""
    CLASSIFY = "classify_event"
    RESOLVE_AGENTS = "resolve_agents"
    HANDLE_CHAT = "handle_chat"
    HANDLE_GAME_STATE = "handle_game_state"
    HANDLE_PLAYER_ACTION = "handle_player_action"
    HANDLE_SUPERVISOR = "handle_supervisor"
    HANDLE_PROFILE_SYNC = "handle_profile_sync"
    HANDLE_BROADCAST = "handle_broadcast"
    # Phase 2 handlers
    HANDLE_PHASE_TRANSITION = "handle_phase_transition"
    HANDLE_REACTION_REQUIRED = "handle_reaction_required"
    HANDLE_REACTIONS_VISIBLE = "handle_reactions_visible"
    HANDLE_CARD_SELECTION = "handle_card_selection"
    FINALIZE = "finalize"


# =============================================
# Node Wrappers (lazy imports to avoid circular deps)
# =============================================
def classify_event_node(state: EventRouterState) -> dict:
    """Wrapper for classify event node."""
    from app.nodes.coup_agent.event_classifier_nodes import classify_event_node as impl
    return impl(state)


def resolve_agents_node(state: EventRouterState) -> dict:
    """Wrapper for resolve agents node."""
    from app.nodes.coup_agent.event_classifier_nodes import resolve_target_agents_node as impl
    return impl(state)


def handle_chat_node(state: EventRouterState) -> dict:
    """Wrapper for chat handler node."""
    from app.nodes.coup_agent.event_classifier_nodes import handle_chat_message_node as impl
    return impl(state)


def handle_game_state_node(state: EventRouterState) -> dict:
    """Wrapper for game state handler node."""
    from app.nodes.coup_agent.event_classifier_nodes import handle_game_state_update_node as impl
    return impl(state)


def handle_player_action_node(state: EventRouterState) -> dict:
    """Wrapper for player action handler node."""
    from app.nodes.coup_agent.event_classifier_nodes import handle_player_action_change_node as impl
    return impl(state)


def handle_supervisor_node(state: EventRouterState) -> dict:
    """Wrapper for supervisor instruction handler node."""
    from app.nodes.coup_agent.event_classifier_nodes import handle_supervisor_instruction_node as impl
    return impl(state)


def handle_profile_sync_node(state: EventRouterState) -> dict:
    """Wrapper for profile sync handler node."""
    from app.nodes.coup_agent.event_classifier_nodes import handle_profile_sync_node as impl
    return impl(state)


def handle_broadcast_node(state: EventRouterState) -> dict:
    """Wrapper for broadcast handler node."""
    from app.nodes.coup_agent.event_classifier_nodes import handle_broadcast_results_node as impl
    return impl(state)


def handle_phase_transition_node(state: EventRouterState) -> dict:
    """Wrapper for phase transition handler node."""
    from app.nodes.coup_agent.event_classifier_nodes import handle_phase_transition_node as impl
    return impl(state)


def handle_reaction_required_node(state: EventRouterState) -> dict:
    """Wrapper for reaction required handler node."""
    from app.nodes.coup_agent.event_classifier_nodes import handle_reaction_required_node as impl
    return impl(state)


def handle_reactions_visible_node(state: EventRouterState) -> dict:
    """Wrapper for reactions visibility handler node."""
    from app.nodes.coup_agent.event_classifier_nodes import handle_reactions_visible_node as impl
    return impl(state)


def handle_card_selection_node(state: EventRouterState) -> dict:
    """Wrapper for card selection required handler node."""
    from app.nodes.coup_agent.event_classifier_nodes import handle_card_selection_required_node as impl
    return impl(state)


def finalize_node(state: EventRouterState) -> dict:
    """Wrapper for finalize node."""
    from app.nodes.coup_agent.event_classifier_nodes import finalize_response_node as impl
    return impl(state)


# =============================================
# Conditional Routers
# =============================================
def should_continue_router(state: EventRouterState) -> Literal["resolve_agents", "finalize"]:
    """
    Check if we should continue processing or finalize with error.
    
    If classification failed, go straight to finalize.
    """
    if state.get("error"):
        return EventRouterNode.FINALIZE
    return EventRouterNode.RESOLVE_AGENTS


def agents_resolved_and_route(state: EventRouterState) -> str:
    """
    Check if agents were resolved successfully and route to appropriate handler.
    
    Combined router that:
    1. Checks for errors or missing agents → FINALIZE
    2. Routes to handler based on event type
    """
    # Check for errors first
    if state.get("error") or not state.get("agent_ids_to_process"):
        return EventRouterNode.FINALIZE
    
    # Route based on event type
    event_type = state.get("classified_event_type")
    
    if not event_type:
        return EventRouterNode.FINALIZE
    
    routing = {
        EventType.CHAT_MESSAGE: EventRouterNode.HANDLE_CHAT,
        EventType.GAME_STATE_UPDATE: EventRouterNode.HANDLE_GAME_STATE,
        EventType.PLAYER_ACTION_CHANGE: EventRouterNode.HANDLE_PLAYER_ACTION,
        EventType.SUPERVISOR_INSTRUCTION: EventRouterNode.HANDLE_SUPERVISOR,
        EventType.PROFILE_SYNC: EventRouterNode.HANDLE_PROFILE_SYNC,
        EventType.BROADCAST_RESULTS: EventRouterNode.HANDLE_BROADCAST,
        # Phase 2 event types
        EventType.PHASE_TRANSITION: EventRouterNode.HANDLE_PHASE_TRANSITION,
        EventType.REACTION_REQUIRED: EventRouterNode.HANDLE_REACTION_REQUIRED,
        EventType.REACTIONS_VISIBLE: EventRouterNode.HANDLE_REACTIONS_VISIBLE,
        EventType.CARD_SELECTION_REQUIRED: EventRouterNode.HANDLE_CARD_SELECTION,
    }
    
    return routing.get(event_type, EventRouterNode.FINALIZE)


# =============================================
# Workflow Class
# =============================================
class EventRouterWorkflow:
    """
    LangGraph workflow for event classification and routing.
    
    Features:
    - Classifies incoming events by type
    - Routes to appropriate handler nodes
    - Checkpoints conversation history for context
    - Supports both single-agent and broadcast events
    
    Architecture:
        CLASSIFY → (error?) → RESOLVE_AGENTS → (error?) → HANDLER → FINALIZE → END
    
    Thread ID Format:
        - Single agent: "{game_id}:{agent_id}"
        - Broadcast: "{game_id}:broadcast"
    """
    
    def __init__(self, checkpointer=None):
        """
        Initialize the event router workflow.
        
        Args:
            checkpointer: LangGraph checkpointer for state persistence.
                         If None, uses MemorySaver (in-memory).
        """
        # Use provided checkpointer or default to MemorySaver
        self.checkpointer = checkpointer or MemorySaver()
        
        # Build the graph
        self.workflow = StateGraph(EventRouterState)
        
        # Add all nodes
        self.workflow.add_node(EventRouterNode.CLASSIFY, classify_event_node)
        self.workflow.add_node(EventRouterNode.RESOLVE_AGENTS, resolve_agents_node)
        self.workflow.add_node(EventRouterNode.HANDLE_CHAT, handle_chat_node)
        self.workflow.add_node(EventRouterNode.HANDLE_GAME_STATE, handle_game_state_node)
        self.workflow.add_node(EventRouterNode.HANDLE_PLAYER_ACTION, handle_player_action_node)
        self.workflow.add_node(EventRouterNode.HANDLE_SUPERVISOR, handle_supervisor_node)
        self.workflow.add_node(EventRouterNode.HANDLE_PROFILE_SYNC, handle_profile_sync_node)
        self.workflow.add_node(EventRouterNode.HANDLE_BROADCAST, handle_broadcast_node)
        # Phase 2 handler nodes
        self.workflow.add_node(EventRouterNode.HANDLE_PHASE_TRANSITION, handle_phase_transition_node)
        self.workflow.add_node(EventRouterNode.HANDLE_REACTION_REQUIRED, handle_reaction_required_node)
        self.workflow.add_node(EventRouterNode.HANDLE_REACTIONS_VISIBLE, handle_reactions_visible_node)
        self.workflow.add_node(EventRouterNode.HANDLE_CARD_SELECTION, handle_card_selection_node)
        self.workflow.add_node(EventRouterNode.FINALIZE, finalize_node)
        
        # Set entry point
        self.workflow.set_entry_point(EventRouterNode.CLASSIFY)
        
        # Add edges
        # CLASSIFY → conditional → RESOLVE_AGENTS or FINALIZE
        self.workflow.add_conditional_edges(
            EventRouterNode.CLASSIFY,
            should_continue_router,
            {
                EventRouterNode.RESOLVE_AGENTS: EventRouterNode.RESOLVE_AGENTS,
                EventRouterNode.FINALIZE: EventRouterNode.FINALIZE,
            }
        )
        
        # RESOLVE_AGENTS → conditional → HANDLER or FINALIZE
        # Combined router checks for errors and routes by event type in one step
        self.workflow.add_conditional_edges(
            EventRouterNode.RESOLVE_AGENTS,
            agents_resolved_and_route,
            {
                EventRouterNode.HANDLE_CHAT: EventRouterNode.HANDLE_CHAT,
                EventRouterNode.HANDLE_GAME_STATE: EventRouterNode.HANDLE_GAME_STATE,
                EventRouterNode.HANDLE_PLAYER_ACTION: EventRouterNode.HANDLE_PLAYER_ACTION,
                EventRouterNode.HANDLE_SUPERVISOR: EventRouterNode.HANDLE_SUPERVISOR,
                EventRouterNode.HANDLE_PROFILE_SYNC: EventRouterNode.HANDLE_PROFILE_SYNC,
                EventRouterNode.HANDLE_BROADCAST: EventRouterNode.HANDLE_BROADCAST,
                # Phase 2 handlers
                EventRouterNode.HANDLE_PHASE_TRANSITION: EventRouterNode.HANDLE_PHASE_TRANSITION,
                EventRouterNode.HANDLE_REACTION_REQUIRED: EventRouterNode.HANDLE_REACTION_REQUIRED,
                EventRouterNode.HANDLE_REACTIONS_VISIBLE: EventRouterNode.HANDLE_REACTIONS_VISIBLE,
                EventRouterNode.HANDLE_CARD_SELECTION: EventRouterNode.HANDLE_CARD_SELECTION,
                EventRouterNode.FINALIZE: EventRouterNode.FINALIZE,
            }
        )
        
        # All handlers go to FINALIZE
        self.workflow.add_edge(EventRouterNode.HANDLE_CHAT, EventRouterNode.FINALIZE)
        self.workflow.add_edge(EventRouterNode.HANDLE_GAME_STATE, EventRouterNode.FINALIZE)
        self.workflow.add_edge(EventRouterNode.HANDLE_PLAYER_ACTION, EventRouterNode.FINALIZE)
        self.workflow.add_edge(EventRouterNode.HANDLE_SUPERVISOR, EventRouterNode.FINALIZE)
        self.workflow.add_edge(EventRouterNode.HANDLE_PROFILE_SYNC, EventRouterNode.FINALIZE)
        self.workflow.add_edge(EventRouterNode.HANDLE_BROADCAST, EventRouterNode.FINALIZE)
        # Phase 2 handlers to FINALIZE
        self.workflow.add_edge(EventRouterNode.HANDLE_PHASE_TRANSITION, EventRouterNode.FINALIZE)
        self.workflow.add_edge(EventRouterNode.HANDLE_REACTION_REQUIRED, EventRouterNode.FINALIZE)
        self.workflow.add_edge(EventRouterNode.HANDLE_REACTIONS_VISIBLE, EventRouterNode.FINALIZE)
        self.workflow.add_edge(EventRouterNode.HANDLE_CARD_SELECTION, EventRouterNode.FINALIZE)
        
        # FINALIZE → END
        self.workflow.add_edge(EventRouterNode.FINALIZE, END)
        
        # Compile with checkpointer
        self.app = self.workflow.compile(checkpointer=self.checkpointer)
    
    def build_thread_id(self, game_id: str, agent_id: str = None, broadcast: bool = False) -> str:
        """
        Build a thread ID for checkpointing.
        
        Args:
            game_id: The game identifier
            agent_id: Target agent (if single agent)
            broadcast: True if broadcasting to all agents
            
        Returns:
            Thread ID string
        """
        if broadcast or not agent_id:
            return f"{game_id}:broadcast"
        return f"{game_id}:{agent_id}"
    
    def run(self, initial_state: dict, thread_id: str = None) -> dict:
        """
        Synchronous invocation of the workflow.
        
        Args:
            initial_state: EventRouterState dict
            thread_id: Thread identifier for checkpointing.
                      If None, builds from game_id/agent_id.
            
        Returns:
            Final state with response
        """
        # Build thread_id if not provided
        if not thread_id:
            thread_id = self.build_thread_id(
                game_id=initial_state.get("game_id", "unknown"),
                agent_id=initial_state.get("target_agent_id"),
                broadcast=initial_state.get("broadcast_to_all_agents", False),
            )
        
        # Initialize default state values
        state_with_defaults = {
            "handler_responses": [],
            "conversation_messages": [],
            "events_processed_this_hour": 0,
            "processing_complete": False,
            **initial_state,
        }
        
        return self.app.invoke(
            state_with_defaults,
            {"configurable": {"thread_id": thread_id}}
        )
    
    async def arun(self, initial_state: dict, thread_id: str = None) -> dict:
        """Asynchronous invocation of the workflow."""
        if not thread_id:
            thread_id = self.build_thread_id(
                game_id=initial_state.get("game_id", "unknown"),
                agent_id=initial_state.get("target_agent_id"),
                broadcast=initial_state.get("broadcast_to_all_agents", False),
            )
        
        state_with_defaults = {
            "handler_responses": [],
            "conversation_messages": [],
            "events_processed_this_hour": 0,
            "processing_complete": False,
            **initial_state,
        }
        
        return await self.app.ainvoke(
            state_with_defaults,
            {"configurable": {"thread_id": thread_id}}
        )
    
    def get_conversation_history(self, thread_id: str) -> list:
        """
        Get the conversation history for a thread.
        
        Args:
            thread_id: The thread identifier
            
        Returns:
            List of conversation messages
        """
        try:
            state = self.app.get_state({"configurable": {"thread_id": thread_id}})
            if state and state.values:
                return state.values.get("conversation_messages", [])
        except Exception:
            pass
        return []
    
    def get_graph_image(self):
        """Get a visual representation of the workflow graph."""
        try:
            return self.app.get_graph().draw_mermaid()
        except Exception:
            return None


# =============================================
# Factory Function
# =============================================
def create_event_router_workflow(checkpointer=None) -> EventRouterWorkflow:
    """
    Factory function to create an EventRouterWorkflow.
    
    Args:
        checkpointer: Optional checkpointer. If None, uses MemorySaver.
        
    Returns:
        Configured EventRouterWorkflow instance
    """
    return EventRouterWorkflow(checkpointer=checkpointer)

