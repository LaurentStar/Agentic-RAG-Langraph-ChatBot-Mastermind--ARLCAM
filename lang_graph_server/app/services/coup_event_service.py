"""
Coup Event Service.

Business logic for processing incoming events to Coup LLM agents.

This service delegates event processing to the EventRouterWorkflow,
which provides:
- Event classification and routing
- Checkpointing for conversation context
- Handler node invocation

The workflow-based approach enables:
- Conversation history persistence across events
- Better LLM context for quality responses
- Visual debugging in LangGraph Studio
"""

from datetime import datetime
from typing import Dict, List, Optional, Any

from app.constants import EventType, MessageTargetType, SocialMediaPlatform
from app.extensions import agent_registry, lang_graph_app


class CoupEventService:
    """
    Service for processing Coup game events.
    
    Delegates to EventRouterWorkflow for:
    - Event classification
    - Agent resolution
    - Handler execution
    - Conversation checkpointing
    """
    
    # =============================================
    # Main Event Router (Workflow-based)
    # =============================================
    
    @staticmethod
    def process_event(event: dict) -> dict:
        """
        Process an incoming event through the EventRouterWorkflow.
        
        The workflow handles:
        1. Event classification
        2. Agent resolution
        3. Routing to appropriate handler
        4. Conversation checkpointing
        
        Args:
            event: The incoming event dict
            
        Returns:
            Response dict with processing result
        """
        # Add timestamp if not present
        if 'timestamp' not in event:
            event['timestamp'] = datetime.now().isoformat()
        
        # Build initial state for workflow
        initial_state = {
            "event_type": event.get("event_type", "chat_message"),
            "source_platform": event.get("source_platform", "defualt"),
            "sender_id": event.get("sender_id", ""),
            "sender_is_llm": event.get("sender_is_llm", False),
            "game_id": event.get("game_id", ""),
            "timestamp": event.get("timestamp"),
            "payload": event.get("payload", {}),
            "target_agent_id": event.get("target_agent_id"),
            "broadcast_to_all_agents": event.get("broadcast_to_all_agents", False),
        }
        
        # Run through EventRouterWorkflow
        try:
            result = lang_graph_app.event_router_wf.run(initial_state)
            
            # Extract final response from workflow result
            final_response = result.get("final_response", {})
            if final_response:
                return final_response
            
            # Fallback if no final_response
            return {
                "success": result.get("processing_complete", False),
                "event_type": event.get("event_type"),
                "handler_responses": result.get("handler_responses", []),
                "error": result.get("error"),
            }
            
        except Exception as e:
            return {
                "success": False,
                "event_type": event.get("event_type"),
                "error": f"Workflow execution failed: {str(e)}",
            }
    
    @staticmethod
    def process_event_async(event: dict):
        """
        Async version of process_event.
        
        Use this in async contexts for better performance.
        """
        import asyncio
        
        # Add timestamp if not present
        if 'timestamp' not in event:
            event['timestamp'] = datetime.now().isoformat()
        
        initial_state = {
            "event_type": event.get("event_type", "chat_message"),
            "source_platform": event.get("source_platform", "defualt"),
            "sender_id": event.get("sender_id", ""),
            "sender_is_llm": event.get("sender_is_llm", False),
            "game_id": event.get("game_id", ""),
            "timestamp": event.get("timestamp"),
            "payload": event.get("payload", {}),
            "target_agent_id": event.get("target_agent_id"),
            "broadcast_to_all_agents": event.get("broadcast_to_all_agents", False),
        }
        
        return lang_graph_app.event_router_wf.arun(initial_state)
    
    # =============================================
    # Conversation History Access
    # =============================================
    
    @staticmethod
    def get_conversation_history(game_id: str, agent_id: str = None) -> List[Dict]:
        """
        Get conversation history for a game/agent thread.
        
        Args:
            game_id: The game identifier
            agent_id: Optional agent ID. If None, returns broadcast thread.
            
        Returns:
            List of conversation messages
        """
        thread_id = lang_graph_app.event_router_wf.build_thread_id(
            game_id=game_id,
            agent_id=agent_id,
            broadcast=agent_id is None,
        )
        return lang_graph_app.event_router_wf.get_conversation_history(thread_id)
    
    # =============================================
    # Agent Query Methods
    # =============================================
    
    @staticmethod
    def get_game_agents(game_id: str) -> dict:
        """Get all agents in a game with their basic info."""
        agents = agent_registry.get_all_agents_in_game(game_id)
        
        return {
            'game_id': game_id,
            'agent_count': len(agents),
            'agents': [
                {
                    'agent_id': a.agent_id,
                    'name': a.name,
                    'coins': a.get_coins(),
                    'hand_count': len(a.get_hand()),
                    'is_alive': a.is_alive(),
                    'action_locked': a.is_action_locked(),
                    'message_stats': a.get_message_stats(),
                }
                for a in agents
            ],
        }
    
    @staticmethod
    def get_agent_stats(game_id: str, agent_id: str) -> Optional[dict]:
        """Get detailed stats for a specific agent."""
        agent = agent_registry.get_agent(game_id, agent_id)
        
        if not agent:
            return None
        
        return {
            'agent_id': agent.agent_id,
            'game_id': game_id,
            'name': agent.name,
            'play_style': agent.play_style,
            'personality': agent.personality,
            'coins': agent.get_coins(),
            'hand_count': len(agent.get_hand()),
            'revealed_count': len(agent.get_revealed()),
            'is_alive': agent.is_alive(),
            'action_locked': agent.is_action_locked(),
            'pending_action': agent.get_pending_action(),
            'pending_upgrade': agent.get_pending_upgrade(),
            'message_stats': agent.get_message_stats(),
            'minutes_remaining': agent.state.get('minutes_remaining', 60),
        }
    
    @staticmethod
    def get_registry_stats() -> dict:
        """Get registry-wide statistics."""
        return agent_registry.get_stats()
    

