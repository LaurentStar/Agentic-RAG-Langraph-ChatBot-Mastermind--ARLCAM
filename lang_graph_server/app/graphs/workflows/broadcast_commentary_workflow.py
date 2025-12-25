"""
Broadcast Commentary Workflow.

LangGraph workflow for generating optional agent commentary
on end-of-hour game results.

Flow:
    ANALYZE_RESULTS → DECIDE_COMMENTARY → (conditional) → GENERATE → END
                                              ↓
                                             END (if not commenting)

Commentary triggers:
- Agent was eliminated (final words!)
- Agent's action succeeded/failed
- Dramatic game events (eliminations, final players)
"""

from typing import Literal

from langgraph.graph import END, StateGraph

from app.models.graph_state_models.broadcast_commentary_state import (
    BroadcastCommentaryState,
)


# =============================================
# Node Names
# =============================================
class BroadcastNode:
    """Node names for the broadcast commentary workflow."""
    ANALYZE = "analyze_results"
    DECIDE = "decide_commentary"
    GENERATE = "generate_commentary"


# =============================================
# Node Wrappers (lazy imports)
# =============================================
def analyze_results_node(state: BroadcastCommentaryState) -> dict:
    """Wrapper for analyze results node."""
    from app.nodes.coup_agent.broadcast_commentary_nodes import analyze_results_node as impl
    return impl(state)


def decide_commentary_node(state: BroadcastCommentaryState) -> dict:
    """Wrapper for decide commentary node."""
    from app.nodes.coup_agent.broadcast_commentary_nodes import decide_commentary_node as impl
    return impl(state)


def generate_commentary_node(state: BroadcastCommentaryState) -> dict:
    """Wrapper for generate commentary node."""
    from app.nodes.coup_agent.broadcast_commentary_nodes import generate_commentary_node as impl
    return impl(state)


# =============================================
# Conditional Router
# =============================================
def should_generate_router(state: BroadcastCommentaryState) -> Literal["generate_commentary", "end"]:
    """
    Route based on commentary decision.
    
    If should_comment is True, go to generation.
    Otherwise, skip to end.
    """
    decision = state.get("commentary_decision", {})
    
    if decision.get("should_comment", False):
        return BroadcastNode.GENERATE
    return "end"


# =============================================
# Workflow Class
# =============================================
class BroadcastCommentaryWorkflow:
    """
    LangGraph workflow for generating broadcast commentary.
    
    Architecture:
        ANALYZE → DECIDE → (conditional) → GENERATE → END
                              ↓
                             END (if not commenting)
    """
    
    def __init__(self):
        # Build the graph
        self.workflow = StateGraph(BroadcastCommentaryState)
        
        # Add nodes
        self.workflow.add_node(BroadcastNode.ANALYZE, analyze_results_node)
        self.workflow.add_node(BroadcastNode.DECIDE, decide_commentary_node)
        self.workflow.add_node(BroadcastNode.GENERATE, generate_commentary_node)
        
        # Set entry point
        self.workflow.set_entry_point(BroadcastNode.ANALYZE)
        
        # Add edges
        self.workflow.add_edge(BroadcastNode.ANALYZE, BroadcastNode.DECIDE)
        
        # Conditional: decide whether to generate
        self.workflow.add_conditional_edges(
            BroadcastNode.DECIDE,
            should_generate_router,
            {
                BroadcastNode.GENERATE: BroadcastNode.GENERATE,
                "end": END,
            }
        )
        
        # Generate goes to end
        self.workflow.add_edge(BroadcastNode.GENERATE, END)
        
        # Compile
        self.app = self.workflow.compile()
    
    def run(self, initial_state: dict, thread_id: str = "default") -> dict:
        """
        Synchronous invocation of the workflow.
        
        Args:
            initial_state: BroadcastCommentaryState dict
            thread_id: Thread identifier for state persistence
            
        Returns:
            Final state with commentary decision and optional commentary
        """
        return self.app.invoke(initial_state, {"configurable": {"thread_id": thread_id}})
    
    async def arun(self, initial_state: dict, thread_id: str = "default") -> dict:
        """Asynchronous invocation of the workflow."""
        return await self.app.ainvoke(initial_state, {"configurable": {"thread_id": thread_id}})
    
    def get_graph_image(self):
        """Get a visual representation of the workflow graph."""
        try:
            return self.app.get_graph().draw_mermaid()
        except Exception:
            return None


