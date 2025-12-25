"""
Message Counter Service.

Tracks and enforces messaging limits for LLM agents in hourly Coup games.

Limits per hourly turn:
- To LLM agents only: 30 messages
- To humans only: 150 messages  
- To mixed (both): 30 messages
- Total potential: 210 messages

The counter is per-agent and resets at the start of each hourly turn.
"""

from typing import Tuple

from app.constants import MESSAGE_LIMITS, MessageTargetType
from app.models.graph_state_models.hourly_coup_state import HourlyCoupAgentState


class MessageCounterService:
    """
    Service to track and enforce message limits for LLM agents.
    
    Each agent has their own counters tracked in their HourlyCoupAgentState.
    This service provides methods to check limits and increment counters.
    """
    
    @staticmethod
    def get_limit(target_type: MessageTargetType) -> int:
        """Get the message limit for a target type."""
        return MESSAGE_LIMITS.get(target_type, 0)
    
    @staticmethod
    def get_current_count(state: HourlyCoupAgentState, target_type: MessageTargetType) -> int:
        """Get the current message count for a target type."""
        if target_type == MessageTargetType.LLM_ONLY:
            return state.get("llm_messages_sent", 0)
        elif target_type == MessageTargetType.HUMAN_ONLY:
            return state.get("human_messages_sent", 0)
        elif target_type == MessageTargetType.MIXED:
            return state.get("mixed_messages_sent", 0)
        return 0
    
    @staticmethod
    def get_remaining(state: HourlyCoupAgentState, target_type: MessageTargetType) -> int:
        """Get remaining messages allowed for a target type."""
        limit = MessageCounterService.get_limit(target_type)
        current = MessageCounterService.get_current_count(state, target_type)
        return max(0, limit - current)
    
    @staticmethod
    def can_send_message(state: HourlyCoupAgentState, target_type: MessageTargetType) -> bool:
        """
        Check if the agent can send a message to the given target type.
        
        Args:
            state: Agent's current hourly state
            target_type: Who the message is being sent to
            
        Returns:
            True if agent has remaining quota for this target type
        """
        return MessageCounterService.get_remaining(state, target_type) > 0
    
    @staticmethod
    def increment_count(
        state: HourlyCoupAgentState, 
        target_type: MessageTargetType
    ) -> Tuple[HourlyCoupAgentState, bool]:
        """
        Increment the message counter for a target type.
        
        Args:
            state: Agent's current hourly state
            target_type: Who the message was sent to
            
        Returns:
            Tuple of (updated_state, success)
            success is False if limit was already reached
        """
        if not MessageCounterService.can_send_message(state, target_type):
            return state, False
        
        if target_type == MessageTargetType.LLM_ONLY:
            state["llm_messages_sent"] = state.get("llm_messages_sent", 0) + 1
        elif target_type == MessageTargetType.HUMAN_ONLY:
            state["human_messages_sent"] = state.get("human_messages_sent", 0) + 1
        elif target_type == MessageTargetType.MIXED:
            state["mixed_messages_sent"] = state.get("mixed_messages_sent", 0) + 1
            
        return state, True
    
    @staticmethod
    def determine_target_type(
        recipients: list,
        is_recipient_llm_map: dict
    ) -> MessageTargetType:
        """
        Determine the message target type based on recipients.
        
        Args:
            recipients: List of recipient player IDs
            is_recipient_llm_map: Dict mapping player_id -> bool (True if LLM)
            
        Returns:
            MessageTargetType based on recipient composition
        """
        if not recipients:
            return MessageTargetType.MIXED
        
        has_llm = False
        has_human = False
        
        for recipient in recipients:
            if is_recipient_llm_map.get(recipient, False):
                has_llm = True
            else:
                has_human = True
        
        if has_llm and has_human:
            return MessageTargetType.MIXED
        elif has_llm:
            return MessageTargetType.LLM_ONLY
        else:
            return MessageTargetType.HUMAN_ONLY
    
    @staticmethod
    def get_all_counts(state: HourlyCoupAgentState) -> dict:
        """Get all message counts and limits for reporting."""
        return {
            MessageTargetType.LLM_ONLY: {
                "sent": state.get("llm_messages_sent", 0),
                "limit": MESSAGE_LIMITS[MessageTargetType.LLM_ONLY],
                "remaining": MessageCounterService.get_remaining(state, MessageTargetType.LLM_ONLY),
            },
            MessageTargetType.HUMAN_ONLY: {
                "sent": state.get("human_messages_sent", 0),
                "limit": MESSAGE_LIMITS[MessageTargetType.HUMAN_ONLY],
                "remaining": MessageCounterService.get_remaining(state, MessageTargetType.HUMAN_ONLY),
            },
            MessageTargetType.MIXED: {
                "sent": state.get("mixed_messages_sent", 0),
                "limit": MESSAGE_LIMITS[MessageTargetType.MIXED],
                "remaining": MessageCounterService.get_remaining(state, MessageTargetType.MIXED),
            },
        }
    
    @staticmethod
    def get_total_sent(state: HourlyCoupAgentState) -> int:
        """Get total messages sent across all target types."""
        return (
            state.get("llm_messages_sent", 0) +
            state.get("human_messages_sent", 0) +
            state.get("mixed_messages_sent", 0)
        )
    
    @staticmethod
    def get_total_remaining(state: HourlyCoupAgentState) -> int:
        """Get total remaining messages across all target types."""
        return (
            MessageCounterService.get_remaining(state, MessageTargetType.LLM_ONLY) +
            MessageCounterService.get_remaining(state, MessageTargetType.HUMAN_ONLY) +
            MessageCounterService.get_remaining(state, MessageTargetType.MIXED)
        )

