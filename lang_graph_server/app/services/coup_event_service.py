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

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from app.constants import EventType, MessageTargetType, SocialMediaPlatform
from app.extensions import agent_registry, lang_graph_app

logger = logging.getLogger(__name__)


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
        
        # Log incoming event
        game_id = event.get("game_id", "unknown")
        sender_id = event.get("sender_id", "unknown")
        event_type = event.get("event_type", "chat_message")
        payload = event.get("payload", {})
        content_preview = str(payload.get("content", ""))[:50]
        
        logger.info(
            f"[CHAT-FLOW] LangGraph received: game_id={game_id} "
            f"sender_id={sender_id} event_type={event_type} "
            f"content=\"{content_preview}...\""
        )
        
        # Build initial state for workflow
        initial_state = {
            "event_type": event_type,
            "source_platform": event.get("source_platform", "defualt"),
            "sender_id": sender_id,
            "sender_is_llm": event.get("sender_is_llm", False),
            "game_id": game_id,
            "timestamp": event.get("timestamp"),
            "payload": payload,
            "target_agent_id": event.get("target_agent_id"),
            "broadcast_to_all_agents": event.get("broadcast_to_all_agents", False),
        }
        
        logger.debug(f"[CHAT-FLOW] Workflow initial_state: {initial_state}")
        
        # Run through EventRouterWorkflow
        try:
            result = lang_graph_app.event_router_wf.run(initial_state)
            
            # Log workflow result
            handler_responses = result.get("handler_responses", [])
            agents_responded = len(handler_responses)
            logger.info(
                f"[CHAT-FLOW] Workflow complete: game_id={game_id} "
                f"handlers_invoked={agents_responded} "
                f"processing_complete={result.get('processing_complete', False)}"
            )
            
            # Log each agent's response decision
            for resp in handler_responses:
                agent_id = resp.get("agent_id", "unknown")
                should_respond = resp.get("should_respond", False)
                reason = resp.get("reason", "no reason given")
                logger.info(
                    f"[CHAT-FLOW] Agent decision: agent={agent_id} "
                    f"should_respond={should_respond} reason=\"{reason}\""
                )
            
            # Extract final response from workflow result
            final_response = result.get("final_response", {})
            if final_response:
                return final_response
            
            # Fallback if no final_response
            return {
                "success": result.get("processing_complete", False),
                "event_type": event_type,
                "handler_responses": handler_responses,
                "error": result.get("error"),
            }
            
        except Exception as e:
            logger.error(
                f"[CHAT-FLOW] Workflow error: game_id={game_id} error={e}"
            )
            return {
                "success": False,
                "event_type": event_type,
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
    
    # =============================================
    # Agent Registration
    # =============================================
    
    @staticmethod
    def register_agents(game_id: str, agent_configs: List[Dict]) -> dict:
        """
        Register LLM agents for a game session.
        
        Called by game_server when a session starts or LLM agents join.
        Creates agent instances in the in-memory registry.
        
        Args:
            game_id: Game session ID
            agent_configs: List of agent configuration dicts
            
        Returns:
            Registration result dict
        """
        from app.services.profile_sync_service import ProfileSyncService
        
        logger.info(
            f"[AGENT-REG] Registering {len(agent_configs)} agents for game {game_id}"
        )
        
        results = []
        
        for config in agent_configs:
            agent_id = config.get('agent_id')
            
            if not agent_id:
                results.append({
                    'agent_id': None,
                    'success': False,
                    'error': 'agent_id is required',
                })
                continue
            
            try:
                # Build agent profile
                play_style = config.get('play_style', 'balanced')
                personality = config.get('personality', 'friendly')
                
                profile = ProfileSyncService.build_agent_profile(
                    display_name=agent_id,
                    play_style=play_style,
                    personality=personality,
                )
                
                # Register agent
                agent = agent_registry.register_agent(
                    game_id=game_id,
                    agent_id=agent_id,
                    profile=profile,
                    initial_coins=config.get('coins', 2),
                    players_alive=config.get('players_alive', []),
                )
                
                logger.info(
                    f"[AGENT-REG] Registered agent: game={game_id} "
                    f"agent={agent_id} play_style={play_style}"
                )
                
                results.append({
                    'agent_id': agent_id,
                    'success': True,
                })
                
            except Exception as e:
                logger.error(
                    f"[AGENT-REG] Failed to register agent {agent_id}: {e}"
                )
                results.append({
                    'agent_id': agent_id,
                    'success': False,
                    'error': str(e),
                })
        
        successful = sum(1 for r in results if r.get('success'))
        
        logger.info(
            f"[AGENT-REG] Registration complete: game={game_id} "
            f"registered={successful}/{len(agent_configs)}"
        )
        
        return {
            'game_id': game_id,
            'agents_registered': successful,
            'agents': results,
        }
    
    @staticmethod
    def cleanup_game_agents(game_id: str) -> dict:
        """
        Remove all agents for a game session.
        
        Called when a game session ends to free memory.
        
        Args:
            game_id: Game session ID
            
        Returns:
            Cleanup result dict
        """
        logger.info(f"[AGENT-REG] Cleaning up agents for game {game_id}")
        
        agents_removed = agent_registry.cleanup_game(game_id)
        
        logger.info(
            f"[AGENT-REG] Cleanup complete: game={game_id} removed={agents_removed}"
        )
        
        return {
            'game_id': game_id,
            'agents_removed': agents_removed,
            'success': True,
        }
    

