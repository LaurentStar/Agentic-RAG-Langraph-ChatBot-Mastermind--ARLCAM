"""
Coup Agent Workflow - Internal LangGraph StateGraph with 3 entry points.

This workflow is an INTERNAL SERVICE - it is NOT exposed via REST API.
It is called by:
    - Phase 1 handlers: When agents set/change their pending action
    - Phase 2 handlers: When agents set/change their pending reactions
    - ReactionWorkflow: When reactions need heuristic/LLM decision support

Architecture:
    Entry Router → SELECT_ACTION | REACT | RESOLVE → END

The graph topology stays stable; new decision types are added via enums,
not by modifying the graph structure.

Two-Phase Hourly Coup Integration:
    Phase 1 (50 min): Use SELECT_ACTION to decide pending action
    Phase 2 (20 min): Use REACT/RESOLVE for pending reactions
    
    Unlike real-time Coup, these decisions populate pending states
    that are resolved at phase boundaries, not immediately.
"""

from typing import Literal

from langgraph.graph import END, StateGraph

from app.constants import DecisionType
from app.models.graph_state_models.coup_agent_state import CoupAgentState


# =============================================
# Node Names (constants for type safety)
# =============================================
class CoupNode:
    """Node names for the Coup agent graph."""
    ENTRY_ROUTER = "entry_router"
    SELECT_ACTION = "select_action"
    REACT = "react"
    RESOLVE = "resolve"


# =============================================
# Entry Router
# =============================================
def entry_router(state: CoupAgentState) -> Literal["select_action", "react", "resolve"]:
    """
    Route to the appropriate decision node based on decision_type.

    This is the only conditional edge in the graph - all sub-routing
    happens within the individual nodes via their respective enums.
    """
    decision_type = state.get("decision_type")

    if decision_type == DecisionType.ACTION:
        return CoupNode.SELECT_ACTION
    elif decision_type == DecisionType.REACT:
        return CoupNode.REACT
    elif decision_type == DecisionType.RESOLVE:
        return CoupNode.RESOLVE
    else:
        # Default to ACTION if not specified (backwards compatibility)
        return CoupNode.SELECT_ACTION


# =============================================
# Placeholder Nodes (to be implemented in decision_nodes.py)
# =============================================
def select_action_node(state: CoupAgentState) -> dict:
    """
    SELECT_ACTION: Agent's turn - choose an action.

    This is a placeholder that will be replaced by the actual implementation
    in app/nodes/coup_agent/decision_nodes.py
    """
    # Import here to avoid circular imports at module level
    from app.nodes.coup_agent.decision_nodes import select_action_node as impl
    return impl(state)


def react_node(state: CoupAgentState) -> dict:
    """
    REACT: Voluntary response to another player's action.

    Routes internally based on reaction_type (CHALLENGE, CHALLENGE_BLOCK, BLOCK).
    """
    from app.nodes.coup_agent.decision_nodes import react_node as impl
    return impl(state)


def resolve_node(state: CoupAgentState) -> dict:
    """
    RESOLVE: Forced completion (reveal card, exchange cards).

    Routes internally based on resolution_type (REVEAL_CARD, EXCHANGE_CARDS).
    """
    from app.nodes.coup_agent.decision_nodes import resolve_node as impl
    return impl(state)


# =============================================
# Workflow Class
# =============================================
class CoupAgentWorkflow:
    """
    Internal LangGraph workflow for Coup agent decisions.
    
    This is an INTERNAL SERVICE - NOT exposed via REST endpoint.
    All decisions are asynchronous (populate pending state, resolved at phase end).

    Three stable entry points routed by decision_type:
        - SELECT_ACTION: Pick an action + target for Phase 1
        - REACT: Voluntary response (challenge/block/pass) for Phase 2
        - RESOLVE: Forced completion (reveal/exchange) for Phase 2
    
    Usage:
        # From Phase 1 handler - deciding pending action
        result = coup_agent_wf.select_action(agent_state)
        agent.set_pending_action(result["chosen_action"], result["chosen_target"])
        
        # From ReactionWorkflow - deciding reaction
        result = coup_agent_wf.decide_reaction(agent_state, action_to_react_to)
        
        # From Phase 2 handler - resolving card selection
        result = coup_agent_wf.resolve_cards(agent_state)
    """

    def __init__(self):
        # Build the graph
        self.workflow = StateGraph(CoupAgentState)

        # Add nodes
        self.workflow.add_node(CoupNode.SELECT_ACTION, select_action_node)
        self.workflow.add_node(CoupNode.REACT, react_node)
        self.workflow.add_node(CoupNode.RESOLVE, resolve_node)

        # Entry point: conditional routing based on decision_type
        self.workflow.set_conditional_entry_point(
            entry_router,
            {
                CoupNode.SELECT_ACTION: CoupNode.SELECT_ACTION,
                CoupNode.REACT: CoupNode.REACT,
                CoupNode.RESOLVE: CoupNode.RESOLVE,
            }
        )

        # All nodes terminate to END (single-step decisions)
        self.workflow.add_edge(CoupNode.SELECT_ACTION, END)
        self.workflow.add_edge(CoupNode.REACT, END)
        self.workflow.add_edge(CoupNode.RESOLVE, END)

        # Compile
        self.app = self.workflow.compile()

    def run(self, initial_state: dict, thread_id: str = "default") -> dict:
        """Synchronous invocation of the workflow."""
        return self.app.invoke(initial_state, {"configurable": {"thread_id": thread_id}})

    async def arun(self, initial_state: dict, thread_id: str = "default") -> dict:
        """Asynchronous invocation of the workflow."""
        return await self.app.ainvoke(initial_state, {"configurable": {"thread_id": thread_id}})
    
    # =============================================
    # Convenience Methods for Internal Callers
    # =============================================
    
    def select_action(self, agent_state: dict, thread_id: str = "default") -> dict:
        """
        Run the SELECT_ACTION decision node.
        
        Used during Phase 1 when an agent needs to decide their pending action.
        
        Args:
            agent_state: The agent's CoupAgentState/HourlyCoupAgentState
            thread_id: Thread identifier (typically "{game_id}:{agent_id}")
        
        Returns:
            Dict with chosen_action, chosen_target, claimed_role, reasoning
        """
        state = {**agent_state, "decision_type": DecisionType.ACTION}
        return self.run(state, thread_id)
    
    def decide_reaction(
        self,
        agent_state: dict,
        reaction_type: str,
        thread_id: str = "default"
    ) -> dict:
        """
        Run the REACT decision node.
        
        Used during Phase 2 when an agent needs to decide on a reaction.
        
        Args:
            agent_state: The agent's state including pending_reaction context
            reaction_type: "challenge", "challenge_block", or "block"
            thread_id: Thread identifier
        
        Returns:
            Dict with chosen_reaction, reasoning
        """
        from app.constants import ReactionType
        state = {
            **agent_state,
            "decision_type": DecisionType.REACT,
            "reaction_type": ReactionType(reaction_type),
        }
        return self.run(state, thread_id)
    
    def resolve_cards(
        self,
        agent_state: dict,
        resolution_type: str,
        thread_id: str = "default"
    ) -> dict:
        """
        Run the RESOLVE decision node.
        
        Used during Phase 2 for card selections (reveal or exchange).
        
        Args:
            agent_state: The agent's state including available cards
            resolution_type: "reveal_card" or "exchange_cards"
            thread_id: Thread identifier
        
        Returns:
            Dict with chosen_reveal or chosen_exchange
        """
        from app.constants import ResolutionType
        state = {
            **agent_state,
            "decision_type": DecisionType.RESOLVE,
            "resolution_type": ResolutionType(resolution_type),
        }
        return self.run(state, thread_id)

