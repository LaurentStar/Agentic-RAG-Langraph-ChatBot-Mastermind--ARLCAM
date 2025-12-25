"""
Chat Reasoning Workflow for Coup LLM Agents.

LangGraph workflow that processes incoming chat messages and generates responses.

Flow:
    Analyze Message → Decide Response → [Generate Response] → [Decide Action Update] → END

The workflow conditionally skips generation if the decision is to not respond.
"""

from typing import Literal

from langgraph.graph import END, StateGraph

from app.models.graph_state_models.chat_reasoning_state import ChatReasoningState


# =============================================
# Node Names
# =============================================
class ChatNode:
    """Node names for the chat reasoning workflow."""
    ANALYZE = "analyze_message"
    DECIDE = "decide_response"
    GENERATE = "generate_response"
    ACTION_UPDATE = "decide_action_update"


# =============================================
# Conditional Router
# =============================================
def should_generate_router(state: ChatReasoningState) -> Literal["generate_response", "end"]:
    """
    Route based on response decision.
    
    If should_respond is True, go to generation.
    Otherwise, skip to end.
    """
    decision = state.get("response_decision", {})
    
    if decision.get("should_respond", False):
        return ChatNode.GENERATE
    return "end"


def should_update_action_router(state: ChatReasoningState) -> Literal["decide_action_update", "end"]:
    """
    Route to action update node only if we generated a response.
    """
    response = state.get("generated_response")
    
    if response:
        return ChatNode.ACTION_UPDATE
    return "end"


# =============================================
# Node Wrappers
# =============================================
def analyze_message_node(state: ChatReasoningState) -> dict:
    """Wrapper for analyze message node."""
    from app.nodes.coup_agent.chat_nodes import analyze_message_node as impl
    return impl(state)


def decide_response_node(state: ChatReasoningState) -> dict:
    """Wrapper for decide response node."""
    from app.nodes.coup_agent.chat_nodes import decide_response_node as impl
    return impl(state)


def generate_response_node(state: ChatReasoningState) -> dict:
    """Wrapper for generate response node."""
    from app.nodes.coup_agent.chat_nodes import generate_response_node as impl
    return impl(state)


def decide_action_update_node(state: ChatReasoningState) -> dict:
    """Wrapper for decide action update node."""
    from app.nodes.coup_agent.chat_nodes import decide_action_update_node as impl
    return impl(state)


# =============================================
# Workflow Class
# =============================================
class ChatReasoningWorkflow:
    """
    LangGraph workflow for processing chat messages.
    
    Architecture:
        ANALYZE → DECIDE → (conditional) → GENERATE → ACTION_UPDATE → END
                           ↓
                          END (if not responding)
    """
    
    def __init__(self):
        # Build the graph
        self.workflow = StateGraph(ChatReasoningState)
        
        # Add nodes
        self.workflow.add_node(ChatNode.ANALYZE, analyze_message_node)
        self.workflow.add_node(ChatNode.DECIDE, decide_response_node)
        self.workflow.add_node(ChatNode.GENERATE, generate_response_node)
        self.workflow.add_node(ChatNode.ACTION_UPDATE, decide_action_update_node)
        
        # Set entry point
        self.workflow.set_entry_point(ChatNode.ANALYZE)
        
        # Add edges
        self.workflow.add_edge(ChatNode.ANALYZE, ChatNode.DECIDE)
        
        # Conditional: decide whether to generate
        self.workflow.add_conditional_edges(
            ChatNode.DECIDE,
            should_generate_router,
            {
                ChatNode.GENERATE: ChatNode.GENERATE,
                "end": END,
            }
        )
        
        # Conditional: decide whether to update action
        self.workflow.add_conditional_edges(
            ChatNode.GENERATE,
            should_update_action_router,
            {
                ChatNode.ACTION_UPDATE: ChatNode.ACTION_UPDATE,
                "end": END,
            }
        )
        
        # Action update goes to end
        self.workflow.add_edge(ChatNode.ACTION_UPDATE, END)
        
        # Compile
        self.app = self.workflow.compile()
    
    def run(self, initial_state: dict, thread_id: str = "default") -> dict:
        """
        Synchronous invocation of the workflow.
        
        Args:
            initial_state: ChatReasoningState dict
            thread_id: Thread identifier for state persistence
            
        Returns:
            Final state with response decision and optional response
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


