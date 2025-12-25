"""
Reaction Workflow for Phase 2 Decision Making.

This LangGraph workflow handles the reaction phase of hourly Coup,
where agents decide how to react to actions from Phase 1.

Flow:
    1. Analyze Actions -> Assess threat, bluff likelihood, block options
    2. Decide Reactions -> Challenge, block, or pass for each action
    3. Set Specific Reactions -> Create reactions targeting specific actions
    4. Set Conditional Reactions -> Create rule-based reactions
    5. Update DB -> Persist reactions to PostgreSQL
    6. Maybe Chat -> Optionally generate chat about reactions
    7. Generate Chat -> If chatting, create the message

```
                    ┌──────────────────┐
                    │  Analyze Actions │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ Decide Reactions │
                    └────────┬─────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
    ┌───────▼───────┐ ┌──────▼──────┐  ┌──────▼──────┐
    │ Set Specific  │ │    Pass     │  │Set Conditional│
    │  Reactions    │ │             │  │  Reactions  │
    └───────┬───────┘ └──────┬──────┘  └──────┬──────┘
            │                │                │
            └────────────────┼────────────────┘
                             │
                    ┌────────▼─────────┐
                    │    Update DB     │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  Decide Chat?    │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  Generate Chat   │ (if should_chat)
                    └────────┬─────────┘
                             │
                            END
```
"""

from typing import Any, Dict, Literal

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.nodes.coup_agent.reaction_nodes import (
    ReactionWorkflowState,
    analyze_actions_node,
    decide_reactions_node,
    set_specific_reactions_node,
    set_conditional_reactions_node,
    update_db_node,
    decide_chat_about_reactions_node,
    generate_reaction_chat_node,
)


# =============================================
# Node Names
# =============================================

class ReactionNode:
    """Node names for the reaction workflow."""
    ANALYZE = "analyze_actions"
    DECIDE = "decide_reactions"
    SET_SPECIFIC = "set_specific_reactions"
    SET_CONDITIONAL = "set_conditional_reactions"
    UPDATE_DB = "update_db"
    DECIDE_CHAT = "decide_chat"
    GENERATE_CHAT = "generate_chat"


# =============================================
# Router Functions
# =============================================

def should_generate_chat_router(
    state: ReactionWorkflowState
) -> Literal["generate_chat", "__end__"]:
    """
    Route based on whether agent should chat about reactions.
    """
    if state.get("should_chat_about_reactions", False):
        return ReactionNode.GENERATE_CHAT
    return END


# =============================================
# Workflow Class
# =============================================

class ReactionWorkflow:
    """
    LangGraph workflow for Phase 2 reaction decisions.
    
    Agents use this workflow to analyze incoming actions and
    set their pending reactions (challenges, blocks, passes).
    
    The workflow is triggered by REACTION_REQUIRED events from
    the game server at the start of Phase 2.
    
    Args:
        checkpointer: Optional checkpointer for conversation persistence
    """
    
    def __init__(self, checkpointer: BaseCheckpointSaver = None):
        self.checkpointer = checkpointer
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile(checkpointer=checkpointer)
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph state graph."""
        workflow = StateGraph(ReactionWorkflowState)
        
        # Add nodes
        workflow.add_node(ReactionNode.ANALYZE, analyze_actions_node)
        workflow.add_node(ReactionNode.DECIDE, decide_reactions_node)
        workflow.add_node(ReactionNode.SET_SPECIFIC, set_specific_reactions_node)
        workflow.add_node(ReactionNode.SET_CONDITIONAL, set_conditional_reactions_node)
        workflow.add_node(ReactionNode.UPDATE_DB, update_db_node)
        workflow.add_node(ReactionNode.DECIDE_CHAT, decide_chat_about_reactions_node)
        workflow.add_node(ReactionNode.GENERATE_CHAT, generate_reaction_chat_node)
        
        # Set entry point
        workflow.set_entry_point(ReactionNode.ANALYZE)
        
        # Linear flow: Analyze -> Decide -> Set Specific -> Set Conditional -> Update DB
        workflow.add_edge(ReactionNode.ANALYZE, ReactionNode.DECIDE)
        workflow.add_edge(ReactionNode.DECIDE, ReactionNode.SET_SPECIFIC)
        workflow.add_edge(ReactionNode.SET_SPECIFIC, ReactionNode.SET_CONDITIONAL)
        workflow.add_edge(ReactionNode.SET_CONDITIONAL, ReactionNode.UPDATE_DB)
        workflow.add_edge(ReactionNode.UPDATE_DB, ReactionNode.DECIDE_CHAT)
        
        # Conditional: Decide Chat -> Generate Chat OR End
        workflow.add_conditional_edges(
            ReactionNode.DECIDE_CHAT,
            should_generate_chat_router,
            {
                ReactionNode.GENERATE_CHAT: ReactionNode.GENERATE_CHAT,
                END: END,
            }
        )
        
        # Generate Chat -> End
        workflow.add_edge(ReactionNode.GENERATE_CHAT, END)
        
        return workflow
    
    def run(
        self,
        initial_state: Dict[str, Any],
        thread_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Run the reaction workflow.
        
        Args:
            initial_state: ReactionWorkflowState with agent context and
                          actions_requiring_my_reaction populated
            thread_id: Thread ID for checkpointing (format: "{game_id}:{agent_id}")
        
        Returns:
            Final state with pending_reactions and optional reaction_chat_content
        """
        config = {"configurable": {"thread_id": thread_id}}
        return self.app.invoke(initial_state, config)
    
    async def arun(
        self,
        initial_state: Dict[str, Any],
        thread_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Run the reaction workflow asynchronously.
        
        Args:
            initial_state: ReactionWorkflowState with agent context
            thread_id: Thread ID for checkpointing
        
        Returns:
            Final state with pending_reactions and optional reaction_chat_content
        """
        config = {"configurable": {"thread_id": thread_id}}
        return await self.app.ainvoke(initial_state, config)


# =============================================
# Factory Function
# =============================================

def create_reaction_workflow_state(
    agent_state: Dict[str, Any],
    actions_requiring_reaction: list,
) -> ReactionWorkflowState:
    """
    Create a ReactionWorkflowState from an agent's HourlyCoupAgentState.
    
    Args:
        agent_state: The agent's current HourlyCoupAgentState
        actions_requiring_reaction: List of ActionRequiringReaction from game server
    
    Returns:
        ReactionWorkflowState ready for the workflow
    """
    return ReactionWorkflowState(
        # Copy agent state
        **agent_state,
        
        # Add actions to react to
        actions_requiring_my_reaction=actions_requiring_reaction,
        
        # Initialize workflow fields
        analyzed_actions=[],
        reaction_decisions=[],
        new_pending_reactions=[],
        should_chat_about_reactions=False,
        reaction_chat_content=None,
        reactions_updated_in_db=False,
    )

