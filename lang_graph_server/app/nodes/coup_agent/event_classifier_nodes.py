"""
Event Classifier Nodes.

LangGraph nodes for classifying and routing incoming events
to the appropriate handler workflows.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from app.constants import EventType, GamePhase, SocialMediaPlatform, MessageTargetType
from app.extensions import agent_registry
from app.models.graph_state_models.event_router_state import (
    EventRouterState,
    EventClassification,
)
from app.models.graph_state_models.game_phase_state import (
    ActionRequiringReaction,
    PhaseTransitionInfo,
)
from app.services.platform_response_router import PlatformResponseRouter

logger = logging.getLogger(__name__)


# =============================================
# Classification Node
# =============================================
def classify_event_node(state: EventRouterState) -> Dict[str, Any]:
    """
    Classify the incoming event and determine routing.
    
    This node:
    1. Validates the event type
    2. Determines if LLM processing is needed
    3. Sets the handler name for routing
    """
    event_type_str = state.get("event_type", "")
    game_id = state.get("game_id", "unknown")
    
    logger.info(f"[CHAT-FLOW] classify_event_node: game={game_id} event_type={event_type_str}")
    
    # Try to parse event type
    try:
        event_type = EventType(event_type_str)
    except ValueError:
        logger.error(f"[CHAT-FLOW] Unknown event type: {event_type_str}")
        return {
            "error": f"Unknown event type: {event_type_str}",
            "classification": None,
            "classified_event_type": None,
            "processing_complete": True,
        }
    
    # Determine classification based on event type
    classification = _classify_event_type(event_type)
    
    logger.info(
        f"[CHAT-FLOW] Event classified: type={event_type.value} "
        f"handler={classification.get('handler_name')} "
        f"requires_llm={classification.get('requires_llm_processing')}"
    )
    
    return {
        "classification": classification,
        "classified_event_type": event_type,
        "error": None,
    }


def _classify_event_type(event_type: EventType) -> EventClassification:
    """
    Classify an event type and return routing information.
    
    Events that require LLM processing:
    - CHAT_MESSAGE: Needs analysis, response generation
    - BROADCAST_RESULTS: May generate commentary
    - REACTION_REQUIRED: May need LLM to decide reactions
    
    Events that are direct state updates:
    - GAME_STATE_UPDATE: Direct state mutation
    - PLAYER_ACTION_CHANGE: Direct state mutation
    - SUPERVISOR_INSTRUCTION: Direct command execution
    - PROFILE_SYNC: Direct profile update
    - PHASE_TRANSITION: Update phase, may reset state
    - REACTIONS_VISIBLE: Update visible reactions
    - CARD_SELECTION_REQUIRED: Update selection requirements
    """
    llm_events = {
        EventType.CHAT_MESSAGE,
        EventType.BROADCAST_RESULTS,
        EventType.REACTION_REQUIRED,  # May involve LLM decision making
    }
    
    handler_mapping = {
        EventType.CHAT_MESSAGE: "handle_chat_message",
        EventType.GAME_STATE_UPDATE: "handle_game_state_update",
        EventType.PLAYER_ACTION_CHANGE: "handle_player_action_change",
        EventType.SUPERVISOR_INSTRUCTION: "handle_supervisor_instruction",
        EventType.PROFILE_SYNC: "handle_profile_sync",
        EventType.BROADCAST_RESULTS: "handle_broadcast_results",
        # Phase 2 event handlers
        EventType.PHASE_TRANSITION: "handle_phase_transition",
        EventType.REACTION_REQUIRED: "handle_reaction_required",
        EventType.REACTIONS_VISIBLE: "handle_reactions_visible",
        EventType.CARD_SELECTION_REQUIRED: "handle_card_selection_required",
    }
    
    return EventClassification(
        event_type=event_type,
        confidence=1.0,  # Direct classification, always confident
        requires_llm_processing=event_type in llm_events,
        handler_name=handler_mapping.get(event_type, "handle_unknown"),
    )


# =============================================
# Agent Resolution Node
# =============================================
def resolve_target_agents_node(state: EventRouterState) -> Dict[str, Any]:
    """
    Resolve which agents should process this event.
    
    Logic:
    - If target_agent_id is set: single agent
    - If broadcast_to_all_agents: all agents in game
    - Default: all agents in game
    """
    game_id = state.get("game_id")
    target_agent_id = state.get("target_agent_id")
    broadcast = state.get("broadcast_to_all_agents", False)
    
    logger.info(
        f"[CHAT-FLOW] resolve_target_agents_node: game={game_id} "
        f"target_agent={target_agent_id} broadcast={broadcast}"
    )
    
    if not game_id:
        logger.error("[CHAT-FLOW] No game_id provided!")
        return {
            "error": "No game_id provided",
            "agent_ids_to_process": [],
            "processing_complete": True,
        }
    
    # Resolve agent IDs
    if target_agent_id and not broadcast:
        # Single agent target
        agent = agent_registry.get_agent(game_id, target_agent_id)
        if agent:
            agent_ids = [target_agent_id]
            logger.info(f"[CHAT-FLOW] Single agent target resolved: {agent_ids}")
        else:
            logger.warning(
                f"[CHAT-FLOW] Agent {target_agent_id} not found in game {game_id}. "
                f"Registry stats: {agent_registry.get_stats()}"
            )
            return {
                "error": f"Agent {target_agent_id} not found in game {game_id}",
                "agent_ids_to_process": [],
                "processing_complete": True,
            }
    else:
        # Broadcast to all agents
        agent_ids = agent_registry.get_agent_ids_in_game(game_id)
        
        if not agent_ids:
            logger.warning(
                f"[CHAT-FLOW] No agents found for game {game_id}. "
                f"Registry stats: {agent_registry.get_stats()}"
            )
            return {
                "error": f"No agents found for game {game_id}",
                "agent_ids_to_process": [],
                "processing_complete": True,
            }
        
        logger.info(f"[CHAT-FLOW] Broadcast to agents: {agent_ids}")
    
    return {
        "agent_ids_to_process": agent_ids,
        "error": None,
    }


# =============================================
# Chat Message Handler Node
# =============================================
def handle_chat_message_node(state: EventRouterState) -> Dict[str, Any]:
    """
    Handle chat message events using the chat reasoning workflow.
    
    This node invokes the ChatReasoningWorkflow for each target agent.
    """
    from app.services.chat_service import ChatService
    
    game_id = state.get("game_id")
    agent_ids = state.get("agent_ids_to_process", [])
    payload = state.get("payload", {})
    sender_id = state.get("sender_id")
    content = payload.get("content", "")[:50]
    
    logger.info(
        f"[CHAT-FLOW] handle_chat_message_node: game={game_id} "
        f"sender={sender_id} agents={agent_ids} content=\"{content}...\""
    )
    
    # Build event dict for chat service
    event = {
        "event_type": state.get("event_type"),
        "source_platform": state.get("source_platform"),
        "sender_id": sender_id,
        "sender_is_llm": state.get("sender_is_llm", False),
        "game_id": game_id,
        "timestamp": state.get("timestamp"),
        "payload": payload,
    }
    
    responses = []
    conversation_messages = state.get("conversation_messages", [])
    
    if not agent_ids:
        logger.warning(f"[CHAT-FLOW] No agents to process for game {game_id}")
    
    for agent_id in agent_ids:
        agent = agent_registry.get_agent(game_id, agent_id)
        if agent:
            logger.debug(f"[CHAT-FLOW] Processing for agent: {agent_id}")
            # Set platform context
            source_platform = state.get("source_platform", SocialMediaPlatform.DEFUALT)
            if isinstance(source_platform, str):
                try:
                    source_platform = SocialMediaPlatform(source_platform)
                except ValueError:
                    source_platform = SocialMediaPlatform.DEFUALT
            agent.set_current_platform(source_platform)
            
            # Process through chat service
            try:
                response = ChatService.process_chat_message(agent, event)
                
                # Log response summary
                responded = response.get("responded", False)
                response_content = response.get("response", "")
                logger.info(
                    f"[CHAT-FLOW] Agent {agent_id} result: responded={responded} "
                    f"response=\"{str(response_content)[:50] if response_content else 'None'}...\""
                )
                
                responses.append({
                    "agent_id": agent_id,
                    "success": "error" not in response,
                    "response": response,
                })
                
                # Add to conversation history for checkpointing
                if payload.get("message"):
                    conversation_messages.append({
                        "role": "user" if not state.get("sender_is_llm") else "assistant",
                        "content": payload.get("message"),
                        "sender_id": state.get("sender_id"),
                        "timestamp": state.get("timestamp"),
                        "platform": str(source_platform.value) if hasattr(source_platform, 'value') else str(source_platform),
                    })
                
                # Add agent response to conversation history
                if response.get("response_text"):
                    conversation_messages.append({
                        "role": "assistant",
                        "content": response.get("response_text"),
                        "sender_id": agent_id,
                        "timestamp": datetime.now().isoformat(),
                        "platform": str(source_platform.value) if hasattr(source_platform, 'value') else str(source_platform),
                    })
                    
            except Exception as e:
                logger.error(f"[CHAT-FLOW] Error processing agent {agent_id}: {e}", exc_info=True)
                responses.append({
                    "agent_id": agent_id,
                    "success": False,
                    "error": str(e),
                })
        else:
            logger.warning(f"[CHAT-FLOW] Agent {agent_id} not found in registry for game {game_id}")
    
    # Trim conversation history to last 50 messages for checkpointing
    if len(conversation_messages) > 50:
        conversation_messages = conversation_messages[-50:]
    
    logger.info(
        f"[CHAT-FLOW] handle_chat_message_node complete: "
        f"processed={len(responses)} agents"
    )
    
    return {
        "handler_responses": responses,
        "conversation_messages": conversation_messages,
        "events_processed_this_hour": state.get("events_processed_this_hour", 0) + 1,
        "last_event_timestamp": state.get("timestamp"),
    }


# =============================================
# Game State Update Handler Node
# =============================================
def handle_game_state_update_node(state: EventRouterState) -> Dict[str, Any]:
    """
    Handle game state update events.
    
    Updates agent's view of the game state.
    """
    game_id = state.get("game_id")
    agent_ids = state.get("agent_ids_to_process", [])
    payload = state.get("payload", {})
    
    responses = []
    
    for agent_id in agent_ids:
        agent = agent_registry.get_agent(game_id, agent_id)
        if agent:
            try:
                # Update agent state from payload
                if "coins" in payload:
                    agent.state["coins"] = payload["coins"]
                if "hand" in payload:
                    agent.state["hand"] = payload["hand"]
                if "revealed" in payload:
                    agent.state["revealed"] = payload["revealed"]
                if "players_alive" in payload:
                    agent.state["players_alive"] = payload["players_alive"]
                if "minutes_remaining" in payload:
                    agent.update_minutes_remaining(payload["minutes_remaining"])
                
                responses.append({
                    "agent_id": agent_id,
                    "success": True,
                    "action": "state_updated",
                    "coins": agent.get_coins(),
                    "hand_count": len(agent.get_hand()),
                })
            except Exception as e:
                responses.append({
                    "agent_id": agent_id,
                    "success": False,
                    "error": str(e),
                })
    
    return {
        "handler_responses": responses,
        "events_processed_this_hour": state.get("events_processed_this_hour", 0) + 1,
    }


# =============================================
# Player Action Change Handler Node
# =============================================
def handle_player_action_change_node(state: EventRouterState) -> Dict[str, Any]:
    """
    Handle player action change notifications.
    
    Updates agent's visible pending actions.
    """
    game_id = state.get("game_id")
    agent_ids = state.get("agent_ids_to_process", [])
    payload = state.get("payload", {})
    visible_actions = payload.get("visible_pending_actions", [])
    
    responses = []
    
    for agent_id in agent_ids:
        agent = agent_registry.get_agent(game_id, agent_id)
        if agent:
            try:
                agent.update_visible_pending_actions(visible_actions)
                responses.append({
                    "agent_id": agent_id,
                    "success": True,
                    "action": "visible_actions_updated",
                    "action_count": len(visible_actions),
                })
            except Exception as e:
                responses.append({
                    "agent_id": agent_id,
                    "success": False,
                    "error": str(e),
                })
    
    return {
        "handler_responses": responses,
    }


# =============================================
# Supervisor Instruction Handler Node
# =============================================
def handle_supervisor_instruction_node(state: EventRouterState) -> Dict[str, Any]:
    """
    Handle supervisor/admin instructions.
    
    Special commands for controlling agent behavior.
    """
    game_id = state.get("game_id")
    agent_ids = state.get("agent_ids_to_process", [])
    payload = state.get("payload", {})
    instruction = payload.get("instruction", "")
    
    responses = []
    
    for agent_id in agent_ids:
        agent = agent_registry.get_agent(game_id, agent_id)
        if agent:
            try:
                if instruction == "lock_action":
                    agent.lock_action()
                    responses.append({
                        "agent_id": agent_id,
                        "success": True,
                        "action": "action_locked",
                    })
                elif instruction == "unlock_action":
                    agent.unlock_action()
                    responses.append({
                        "agent_id": agent_id,
                        "success": True,
                        "action": "action_unlocked",
                    })
                elif instruction == "reset_hour":
                    agent.reset_for_new_hour()
                    responses.append({
                        "agent_id": agent_id,
                        "success": True,
                        "action": "hour_reset",
                    })
                else:
                    responses.append({
                        "agent_id": agent_id,
                        "success": True,
                        "action": "unknown_instruction",
                        "instruction": instruction,
                    })
            except Exception as e:
                responses.append({
                    "agent_id": agent_id,
                    "success": False,
                    "error": str(e),
                })
    
    return {
        "handler_responses": responses,
    }


# =============================================
# Profile Sync Handler Node
# =============================================
def handle_profile_sync_node(state: EventRouterState) -> Dict[str, Any]:
    """
    Handle profile sync from PostgreSQL.
    
    Updates agent's personality and modulators.
    """
    game_id = state.get("game_id")
    agent_ids = state.get("agent_ids_to_process", [])
    payload = state.get("payload", {})
    profile = payload.get("profile", {})
    
    responses = []
    
    for agent_id in agent_ids:
        agent = agent_registry.get_agent(game_id, agent_id)
        if agent:
            try:
                if profile:
                    agent.update_profile(profile)
                    responses.append({
                        "agent_id": agent_id,
                        "success": True,
                        "action": "profile_synced",
                        "agent_name": agent.name,
                        "play_style": agent.play_style,
                    })
                else:
                    responses.append({
                        "agent_id": agent_id,
                        "success": True,
                        "action": "no_profile_provided",
                    })
            except Exception as e:
                responses.append({
                    "agent_id": agent_id,
                    "success": False,
                    "error": str(e),
                })
    
    return {
        "handler_responses": responses,
    }


# =============================================
# Broadcast Results Handler Node
# =============================================
def handle_broadcast_results_node(state: EventRouterState) -> Dict[str, Any]:
    """
    Handle end-of-hour broadcast results.
    
    Runs the BroadcastCommentaryWorkflow for each agent to generate
    optional in-character commentary on game results.
    """
    from app.extensions import lang_graph_app
    from app.models.graph_state_models.broadcast_commentary_state import (
        create_broadcast_commentary_state,
    )
    
    game_id = state.get("game_id")
    agent_ids = state.get("agent_ids_to_process", [])
    payload = state.get("payload", {})
    results = payload.get("results", [])
    players_remaining = payload.get("players_remaining", [])
    is_game_over = payload.get("is_game_over", False)
    winner = payload.get("winner")
    
    responses = []
    conversation_messages = state.get("conversation_messages", [])
    
    for agent_id in agent_ids:
        agent = agent_registry.get_agent(game_id, agent_id)
        if agent:
            try:
                # Create broadcast commentary state
                commentary_state = create_broadcast_commentary_state(
                    agent=agent,
                    results=results,
                    players_remaining=players_remaining,
                    is_game_over=is_game_over,
                    winner=winner,
                )
                
                # Run broadcast commentary workflow
                workflow_result = lang_graph_app.broadcast_commentary_wf.run(
                    commentary_state,
                    thread_id=f"{game_id}:{agent_id}:broadcast",
                )
                
                # Extract results
                raw_commentary = workflow_result.get("final_commentary")
                decision = workflow_result.get("commentary_decision", {})
                analysis = workflow_result.get("result_analysis", {})
                
                # Format commentary for target platform
                final_commentary = raw_commentary
                formatted_response = None
                source_platform = state.get("source_platform", SocialMediaPlatform.DEFUALT)
                if isinstance(source_platform, str):
                    try:
                        source_platform = SocialMediaPlatform(source_platform)
                    except ValueError:
                        source_platform = SocialMediaPlatform.DEFUALT
                
                if raw_commentary:
                    platform_router = PlatformResponseRouter()
                    # For broadcast, we might want to mention specific players
                    affected_players = [r.get("target") for r in results if r.get("target")]
                    formatted = platform_router.route_response(
                        content=raw_commentary,
                        source_platform=source_platform,
                        mentions=affected_players[:3],  # Limit mentions
                    )
                    final_commentary = formatted.content
                    formatted_response = {
                        "content": formatted.content,
                        "platform": formatted.platform.value,
                        "was_truncated": formatted.was_truncated,
                        "mentions": formatted.mentions,
                    }
                
                response = {
                    "agent_id": agent_id,
                    "success": True,
                    "action": "broadcast_processed",
                    "result_count": len(results),
                    "agent_affected": analysis.get("agent_was_actor") or analysis.get("agent_was_target"),
                    "agent_eliminated": analysis.get("agent_was_eliminated", False),
                    "commented": decision.get("should_comment", False),
                    "commentary": final_commentary,
                    "formatted_response": formatted_response,
                    "target_platform": source_platform.value,
                }
                responses.append(response)
                
                # Add broadcast and commentary to conversation history
                conversation_messages.append({
                    "role": "system",
                    "content": f"Game broadcast: {len(results)} actions resolved",
                    "timestamp": state.get("timestamp"),
                    "results_summary": [
                        f"{r.get('actor')} -> {r.get('action')} -> {r.get('target')}"
                        for r in results[:5]
                    ],
                })
                
                if final_commentary:
                    conversation_messages.append({
                        "role": "assistant",
                        "content": final_commentary,
                        "sender_id": agent_id,
                        "timestamp": datetime.now().isoformat(),
                        "type": "broadcast_commentary",
                    })
                    
                    # Increment message count for commentary
                    agent.increment_message_count(MessageTargetType.MIXED)
                
            except Exception as e:
                responses.append({
                    "agent_id": agent_id,
                    "success": False,
                    "error": str(e),
                })
    
    return {
        "handler_responses": responses,
        "conversation_messages": conversation_messages,
        "events_processed_this_hour": state.get("events_processed_this_hour", 0) + 1,
    }


# =============================================
# Phase Transition Handler Node
# =============================================
def handle_phase_transition_node(state: EventRouterState) -> Dict[str, Any]:
    """
    Handle game phase transition events.
    
    Updates agent's current phase and resets appropriate state.
    
    Phase transitions:
    - PHASE1_ACTIONS -> LOCKOUT1: Lock pending actions
    - LOCKOUT1 -> PHASE2_REACTIONS: Populate actions_requiring_my_reaction
    - PHASE2_REACTIONS -> LOCKOUT2: Lock pending reactions
    - LOCKOUT2 -> BROADCAST: Wait for results
    - BROADCAST -> PHASE1_ACTIONS: Reset for new hour
    """
    game_id = state.get("game_id")
    agent_ids = state.get("agent_ids_to_process", [])
    payload = state.get("payload", {})
    
    new_phase_str = payload.get("new_phase", "")
    previous_phase_str = payload.get("previous_phase", "")
    actions_to_react = payload.get("actions_to_react_to", [])
    phase_duration = payload.get("phase_duration_minutes", 0)
    
    # Parse phases
    try:
        new_phase = GamePhase(new_phase_str)
    except ValueError:
        return {
            "handler_responses": [{
                "success": False,
                "error": f"Unknown phase: {new_phase_str}",
            }],
        }
    
    responses = []
    
    for agent_id in agent_ids:
        agent = agent_registry.get_agent(game_id, agent_id)
        if agent:
            try:
                # Update agent's current phase
                previous_phase = agent.state.get("current_phase")
                agent.state["current_phase"] = new_phase
                
                # Phase-specific state updates
                if new_phase == GamePhase.LOCKOUT1:
                    # Lock actions at end of Phase 1
                    agent.state["action_locked"] = True
                    
                elif new_phase == GamePhase.PHASE2_REACTIONS:
                    # Entering Phase 2: populate actions requiring reaction
                    # Filter to actions that affect this agent
                    my_actions = [
                        a for a in actions_to_react
                        if a.get("affects_me", False) or a.get("target_id") == agent_id
                    ]
                    agent.state["actions_requiring_my_reaction"] = my_actions
                    agent.state["reactions_locked"] = False
                    
                elif new_phase == GamePhase.LOCKOUT2:
                    # Lock reactions at end of Phase 2
                    agent.state["reactions_locked"] = True
                    
                elif new_phase == GamePhase.PHASE1_ACTIONS:
                    # New hour starting: reset everything
                    from app.models.graph_state_models.hourly_coup_state import reset_hourly_counters
                    reset_hourly_counters(agent.state)
                
                responses.append({
                    "agent_id": agent_id,
                    "success": True,
                    "action": "phase_transitioned",
                    "previous_phase": previous_phase.value if previous_phase else None,
                    "new_phase": new_phase.value,
                    "actions_to_react_count": len(agent.state.get("actions_requiring_my_reaction", [])),
                })
                
            except Exception as e:
                responses.append({
                    "agent_id": agent_id,
                    "success": False,
                    "error": str(e),
                })
    
    return {
        "handler_responses": responses,
        "events_processed_this_hour": state.get("events_processed_this_hour", 0) + 1,
    }


# =============================================
# Reaction Required Handler Node
# =============================================
def handle_reaction_required_node(state: EventRouterState) -> Dict[str, Any]:
    """
    Handle reaction required events.
    
    Triggers the ReactionWorkflow for each agent to decide
    how to react to incoming actions.
    
    This is called at the start of Phase 2 when agents need
    to set their pending reactions.
    """
    from app.extensions import lang_graph_app
    from app.graphs.workflows.reaction_workflow import create_reaction_workflow_state
    
    game_id = state.get("game_id")
    agent_ids = state.get("agent_ids_to_process", [])
    payload = state.get("payload", {})
    actions_requiring_reaction = payload.get("actions", [])
    
    responses = []
    
    for agent_id in agent_ids:
        agent = agent_registry.get_agent(game_id, agent_id)
        if agent:
            try:
                # Check if agent is in Phase 2
                current_phase = agent.state.get("current_phase")
                if current_phase != GamePhase.PHASE2_REACTIONS:
                    responses.append({
                        "agent_id": agent_id,
                        "success": False,
                        "error": f"Cannot process reactions in phase {current_phase}",
                    })
                    continue
                
                # Filter actions that affect this agent
                my_actions = [
                    a for a in actions_requiring_reaction
                    if a.get("target_id") == agent_id
                    or a.get("affects_me", False)
                    or "challenge" in a.get("reaction_options", [])
                ]
                
                if not my_actions:
                    responses.append({
                        "agent_id": agent_id,
                        "success": True,
                        "action": "no_reactions_needed",
                        "reactions_set": 0,
                    })
                    continue
                
                # Create reaction workflow state
                reaction_state = create_reaction_workflow_state(
                    agent_state=agent.state,
                    actions_requiring_reaction=my_actions,
                )
                
                # Run the reaction workflow
                workflow_result = lang_graph_app.reaction_wf.run(
                    reaction_state,
                    thread_id=f"{game_id}:{agent_id}",
                )
                
                # Update agent state with new reactions
                new_reactions = workflow_result.get("new_pending_reactions", [])
                agent.state["pending_reactions"] = new_reactions
                
                # Handle any generated chat
                reaction_chat = workflow_result.get("reaction_chat_content")
                
                responses.append({
                    "agent_id": agent_id,
                    "success": True,
                    "action": "reactions_processed",
                    "reactions_set": len(new_reactions),
                    "chat_generated": bool(reaction_chat),
                    "reaction_chat": reaction_chat,
                })
                
            except Exception as e:
                responses.append({
                    "agent_id": agent_id,
                    "success": False,
                    "error": str(e),
                })
    
    return {
        "handler_responses": responses,
        "events_processed_this_hour": state.get("events_processed_this_hour", 0) + 1,
    }


# =============================================
# Reactions Visible Handler Node
# =============================================
def handle_reactions_visible_node(state: EventRouterState) -> Dict[str, Any]:
    """
    Handle reactions visibility updates.
    
    During Phase 2, all pending reactions are visible to all players.
    This handler updates each agent's view of other players' reactions.
    """
    game_id = state.get("game_id")
    agent_ids = state.get("agent_ids_to_process", [])
    payload = state.get("payload", {})
    visible_reactions = payload.get("visible_pending_reactions", [])
    
    responses = []
    
    for agent_id in agent_ids:
        agent = agent_registry.get_agent(game_id, agent_id)
        if agent:
            try:
                # Filter out the agent's own reactions (they already know those)
                other_reactions = [
                    r for r in visible_reactions
                    if r.get("player_id") != agent_id
                ]
                
                # Update agent's visible reactions
                agent.state["visible_pending_reactions"] = other_reactions
                
                responses.append({
                    "agent_id": agent_id,
                    "success": True,
                    "action": "reactions_visibility_updated",
                    "visible_reactions_count": len(other_reactions),
                })
                
            except Exception as e:
                responses.append({
                    "agent_id": agent_id,
                    "success": False,
                    "error": str(e),
                })
    
    return {
        "handler_responses": responses,
    }


# =============================================
# Card Selection Required Handler Node
# =============================================
def handle_card_selection_required_node(state: EventRouterState) -> Dict[str, Any]:
    """
    Handle card selection required events.
    
    Triggered when an agent needs to select cards for:
    - Ambassador exchange: Choose which cards to keep
    - Challenge resolution: Choose which card to reveal
    """
    from app.models.graph_state_models.game_phase_state import PendingCardSelection
    
    game_id = state.get("game_id")
    agent_ids = state.get("agent_ids_to_process", [])
    payload = state.get("payload", {})
    
    selection_type = payload.get("selection_type", "")  # "exchange" or "reveal"
    triggered_by_action_id = payload.get("triggered_by_action_id", "")
    available_cards = payload.get("available_cards", [])
    num_required = payload.get("num_required", 1)
    
    responses = []
    
    for agent_id in agent_ids:
        agent = agent_registry.get_agent(game_id, agent_id)
        if agent:
            try:
                # Create pending card selection
                pending_selection = PendingCardSelection(
                    selection_id=f"{game_id}:{agent_id}:{triggered_by_action_id}",
                    selection_type=selection_type,
                    triggered_by_action_id=triggered_by_action_id,
                    available_cards=available_cards,
                    selected_cards=[],  # Agent will fill this in
                    num_required=num_required,
                    is_finalized=False,
                )
                
                # Update agent state
                agent.state["pending_card_selection"] = pending_selection
                
                # Auto-select if only one valid option
                if len(available_cards) == num_required:
                    pending_selection["selected_cards"] = available_cards
                    pending_selection["is_finalized"] = True
                    agent.state["pending_card_selection"] = pending_selection
                    
                    responses.append({
                        "agent_id": agent_id,
                        "success": True,
                        "action": "card_selection_auto_finalized",
                        "selection_type": selection_type,
                        "selected_cards": available_cards,
                    })
                else:
                    # Agent needs to make a decision
                    # For now, use heuristic selection
                    selected = _select_cards_heuristic(
                        available_cards,
                        num_required,
                        selection_type,
                        agent.state.get("hand", []),
                    )
                    
                    pending_selection["selected_cards"] = selected
                    pending_selection["is_finalized"] = True
                    agent.state["pending_card_selection"] = pending_selection
                    
                    responses.append({
                        "agent_id": agent_id,
                        "success": True,
                        "action": "card_selection_heuristic",
                        "selection_type": selection_type,
                        "available_count": len(available_cards),
                        "selected_cards": selected,
                    })
                
            except Exception as e:
                responses.append({
                    "agent_id": agent_id,
                    "success": False,
                    "error": str(e),
                })
    
    return {
        "handler_responses": responses,
    }


def _select_cards_heuristic(
    available_cards: List[str],
    num_required: int,
    selection_type: str,
    current_hand: List[str],
) -> List[str]:
    """
    Heuristic card selection.
    
    For exchange: Prefer to keep diverse roles
    For reveal: Prefer to reveal less valuable cards
    """
    from app.constants import InfluenceCard
    
    # Card value ranking (higher = more valuable to keep)
    CARD_VALUE = {
        InfluenceCard.DUKE.value: 5,         # Strong economy
        InfluenceCard.ASSASSIN.value: 4,     # Offensive power
        InfluenceCard.CAPTAIN.value: 3,      # Versatile
        InfluenceCard.AMBASSADOR.value: 2,   # Situational
        InfluenceCard.CONTESSA.value: 1,     # Defensive only
    }
    
    if selection_type == "exchange":
        # For exchange: keep the highest value cards
        sorted_cards = sorted(
            available_cards,
            key=lambda c: CARD_VALUE.get(c, 0),
            reverse=True
        )
        return sorted_cards[:num_required]
    
    elif selection_type == "reveal":
        # For reveal: reveal the lowest value cards
        sorted_cards = sorted(
            available_cards,
            key=lambda c: CARD_VALUE.get(c, 0)
        )
        return sorted_cards[:num_required]
    
    # Default: return first N cards
    return available_cards[:num_required]


# =============================================
# Finalize Response Node
# =============================================
def finalize_response_node(state: EventRouterState) -> Dict[str, Any]:
    """
    Finalize the response from all handlers.
    
    Aggregates responses and prepares final output.
    Includes platform routing information for each response.
    """
    responses = state.get("handler_responses", [])
    event_type = state.get("classified_event_type")
    source_platform = state.get("source_platform", SocialMediaPlatform.DEFUALT)
    game_id = state.get("game_id", "unknown")
    
    logger.info(
        f"[CHAT-FLOW] finalize_response_node: game={game_id} "
        f"response_count={len(responses)}"
    )
    
    if isinstance(source_platform, str):
        try:
            source_platform = SocialMediaPlatform(source_platform)
        except ValueError:
            source_platform = SocialMediaPlatform.DEFUALT
    
    # Build final response
    if len(responses) == 1:
        final_response = {
            "success": responses[0].get("success", False),
            "event_type": event_type.value if event_type else None,
            "source_platform": source_platform.value,
            "target_platform": responses[0].get("target_platform", source_platform.value),
            **responses[0],
        }
    else:
        final_response = {
            "success": all(r.get("success", False) for r in responses),
            "event_type": event_type.value if event_type else None,
            "source_platform": source_platform.value,
            "agent_responses": responses,
        }
    
    # Log summary of agent responses
    for resp in responses:
        agent_id = resp.get("agent_id", "unknown")
        inner_resp = resp.get("response", {})
        responded = inner_resp.get("responded", False) if isinstance(inner_resp, dict) else False
        response_text = inner_resp.get("response", "") if isinstance(inner_resp, dict) else ""
        logger.info(
            f"[CHAT-FLOW] Final: agent={agent_id} responded={responded} "
            f"text=\"{str(response_text)[:50] if response_text else 'None'}...\""
        )
    
    return {
        "final_response": final_response,
        "processing_complete": True,
    }

