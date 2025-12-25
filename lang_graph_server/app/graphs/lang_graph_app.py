class LangGraphApp():
    """
    Central registry for all LangGraph workflows.
    
    Workflows are initialized at app startup and accessible globally.
    All workflows that require checkpointing use the shared langgraph_checkpointer.
    
    Workflows:
        - coup_agent_wf: Internal action/reaction decision logic (no longer REST-exposed)
        - chat_reasoning_wf: Chat message analysis and response generation
        - broadcast_commentary_wf: Optional commentary on game broadcasts
        - event_router_wf: Main entry point for all incoming events
        - reaction_wf: Phase 2 reaction decision workflow
    """
    def init_app(self):
        # ---------------------- Load All Graph States ---------------------- #
        from app.graphs.workflows.coup_agent_workflow import CoupAgentWorkflow
        from app.graphs.workflows.chat_reasoning_workflow import ChatReasoningWorkflow
        from app.graphs.workflows.event_router_workflow import EventRouterWorkflow
        from app.graphs.workflows.broadcast_commentary_workflow import BroadcastCommentaryWorkflow
        from app.graphs.workflows.reaction_workflow import ReactionWorkflow
        from app.extensions import langgraph_checkpointer

        # Get the shared checkpointer for all workflows
        checkpointer = langgraph_checkpointer.get_checkpointer()

        # ---------------------- Initialize entire lang graph app ---------------------- #
        
        # CoupAgentWorkflow - Internal service for action/reaction logic
        # No longer exposed via REST endpoint, called internally by other workflows
        self.__class__.coup_agent_wf = CoupAgentWorkflow()
        
        # ChatReasoningWorkflow - Analyzes incoming chat and generates responses
        self.__class__.chat_reasoning_wf = ChatReasoningWorkflow()
        
        # BroadcastCommentaryWorkflow - Generates optional commentary on game broadcasts
        self.__class__.broadcast_commentary_wf = BroadcastCommentaryWorkflow()
        
        # ReactionWorkflow - Phase 2 reaction decision making
        # Used when agents need to decide challenges, blocks, etc.
        self.__class__.reaction_wf = ReactionWorkflow(checkpointer=checkpointer)
        
        # EventRouterWorkflow - Main entry point for all incoming events
        # Uses checkpointing for conversation persistence
        self.__class__.event_router_wf = EventRouterWorkflow(checkpointer=checkpointer)

    # Class-level attributes (declared None, initialized in init_app)
    coup_agent_wf = None
    chat_reasoning_wf = None
    broadcast_commentary_wf = None
    event_router_wf = None
    reaction_wf = None
