"""
Chat Service.

Business logic for processing chat messages through the chat reasoning workflow.

This service:
1. Prepares chat reasoning state from incoming events
2. Runs the chat reasoning workflow
3. Updates agent state with results
4. Returns formatted response
"""

from typing import Dict, Optional, Any

from app.agents.base_coup_agent import BaseCoupAgent
from app.constants import MessageTargetType, SocialMediaPlatform
from app.extensions import lang_graph_app
from app.models.graph_state_models.chat_reasoning_state import (
    ChatReasoningState,
    ChatMessage,
    create_chat_reasoning_state,
)
from app.services.message_counter_service import MessageCounterService


class ChatService:
    """
    Service for processing chat messages through the reasoning workflow.
    """
    
    @staticmethod
    def process_chat_message(
        agent: BaseCoupAgent,
        event: dict,
    ) -> Dict[str, Any]:
        """
        Process an incoming chat message for an agent.
        
        Args:
            agent: The agent processing the message
            event: The incoming event dict
            
        Returns:
            Dict with processing result including any response
        """
        payload = event.get("payload", {})
        sender_id = event.get("sender_id", "unknown")
        sender_is_llm = event.get("sender_is_llm", False)
        source_platform = SocialMediaPlatform(event.get("source_platform", "defualt"))
        
        # Determine target type
        if sender_is_llm:
            target_type = MessageTargetType.LLM_ONLY
        else:
            target_type = MessageTargetType.HUMAN_ONLY
        
        # Check message limit first
        if not agent.can_send_message(target_type):
            return {
                "action": "limit_reached",
                "responded": False,
                "message": f"Message limit reached for {target_type.value}",
                "stats": agent.get_message_stats(),
            }
        
        # Build incoming message
        incoming_message = ChatMessage(
            sender_id=sender_id,
            sender_is_llm=sender_is_llm,
            platform=source_platform,
            content=payload.get("content", ""),
            timestamp=event.get("timestamp"),
            game_id=agent.game_id,
        )
        
        # Get recent chat history from agent state
        recent_history = agent.state.get("chat_history", [])[-10:]  # Last 10 messages
        
        # Create workflow state
        workflow_state = create_chat_reasoning_state(
            agent=agent,
            incoming_message=incoming_message,
            sender_id=sender_id,
            sender_is_llm=sender_is_llm,
            source_platform=source_platform,
            recent_history=recent_history,
        )
        
        # Run workflow
        workflow = lang_graph_app.chat_reasoning_wf
        thread_id = f"{agent.game_id}_{agent.agent_id}"
        
        try:
            result = workflow.run(workflow_state, thread_id=thread_id)
        except Exception as e:
            return {
                "action": "workflow_error",
                "responded": False,
                "error": str(e),
            }
        
        # Process result
        return ChatService._process_workflow_result(agent, result, incoming_message, target_type)
    
    @staticmethod
    def _process_workflow_result(
        agent: BaseCoupAgent,
        result: ChatReasoningState,
        incoming_message: ChatMessage,
        target_type: MessageTargetType,
    ) -> Dict[str, Any]:
        """Process the workflow result and update agent state."""
        
        response_decision = result.get("response_decision", {})
        generated_response = result.get("generated_response")
        final_response = result.get("final_response")
        action_update = result.get("action_update_decision", {})
        
        # Add incoming message to chat history
        chat_history = agent.state.get("chat_history", [])
        chat_history.append(incoming_message)
        agent.state["chat_history"] = chat_history[-50:]  # Keep last 50
        
        # If we generated a response, increment counter and add to history
        if final_response and response_decision.get("should_respond"):
            # Increment message counter
            success = agent.increment_message_count(target_type)
            
            if success:
                # Add our response to chat history
                our_response = ChatMessage(
                    sender_id=agent.agent_id,
                    sender_is_llm=True,
                    platform=result.get("response_platform", SocialMediaPlatform.DEFUALT),
                    content=final_response,
                    game_id=agent.game_id,
                )
                agent.state["chat_history"].append(our_response)
            else:
                # Counter increment failed (race condition)
                final_response = None
        
        # Handle action update if needed
        action_updated = False
        if action_update.get("should_update") and not agent.is_action_locked():
            new_action = action_update.get("new_action")
            new_target = action_update.get("new_target")
            
            if new_action:
                agent.update_pending_action(
                    action=new_action,
                    target=new_target,
                    upgrade=action_update.get("new_upgrade", False),
                    upgrade_type=action_update.get("new_upgrade_type"),
                )
                action_updated = True
        
        # Build response
        return {
            "action": "processed",
            "responded": bool(final_response),
            "response": final_response,
            "response_platform": str(result.get("response_platform", "discord")),
            "analysis": {
                "intent": result.get("message_analysis", {}).get("intent"),
                "relevance": result.get("message_analysis", {}).get("relevance_score"),
                "threat_level": result.get("message_analysis", {}).get("threat_level"),
            },
            "decision": {
                "should_respond": response_decision.get("should_respond"),
                "priority": response_decision.get("response_priority"),
                "reason": response_decision.get("reason"),
            },
            "action_updated": action_updated,
            "message_stats": agent.get_message_stats(),
        }
    
    @staticmethod
    def get_chat_stats(agent: BaseCoupAgent) -> Dict[str, Any]:
        """Get chat statistics for an agent."""
        return {
            "agent_id": agent.agent_id,
            "message_stats": agent.get_message_stats(),
            "chat_history_count": len(agent.state.get("chat_history", [])),
            "can_message_llm": agent.can_send_message(MessageTargetType.LLM_ONLY),
            "can_message_human": agent.can_send_message(MessageTargetType.HUMAN_ONLY),
            "can_message_mixed": agent.can_send_message(MessageTargetType.MIXED),
        }

