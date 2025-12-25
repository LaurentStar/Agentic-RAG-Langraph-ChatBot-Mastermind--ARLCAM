"""
Event Router State Model.

State for the event classification and routing workflow.
Tracks incoming events, classification results, and handler outputs.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

from app.constants import EventType, SocialMediaPlatform


class EventClassification(TypedDict):
    """Result of event classification."""
    event_type: EventType
    confidence: float  # 0.0 to 1.0
    requires_llm_processing: bool  # True if needs LLM workflow
    handler_name: str  # Which handler to invoke


class EventRouterState(TypedDict):
    """
    State for the event router workflow.
    
    Tracks:
    - Incoming event data
    - Classification result
    - Target agent info
    - Handler response
    - Conversation context (for checkpointing)
    """
    
    # =============================================
    # Event Input
    # =============================================
    event_type: str  # Raw event type string from request
    source_platform: SocialMediaPlatform
    sender_id: str
    sender_is_llm: bool
    game_id: str
    timestamp: str
    payload: Dict[str, Any]
    
    # Target routing
    target_agent_id: Optional[str]
    broadcast_to_all_agents: bool
    
    # =============================================
    # Classification Output
    # =============================================
    classification: Optional[EventClassification]
    classified_event_type: Optional[EventType]
    
    # =============================================
    # Processing Context
    # =============================================
    agent_ids_to_process: List[str]  # Resolved list of agents
    current_agent_id: Optional[str]  # Currently processing agent
    
    # =============================================
    # Handler Output
    # =============================================
    handler_responses: List[Dict[str, Any]]  # Response from each agent
    final_response: Optional[Dict[str, Any]]
    
    # =============================================
    # Conversation History (for checkpointing)
    # =============================================
    # These fields enable conversation continuity across events
    conversation_messages: List[Dict[str, Any]]  # Recent messages for context
    last_event_timestamp: Optional[str]
    events_processed_this_hour: int
    
    # =============================================
    # Error Handling
    # =============================================
    error: Optional[str]
    processing_complete: bool

