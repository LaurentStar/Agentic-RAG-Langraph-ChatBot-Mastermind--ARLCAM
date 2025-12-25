"""
Chat Reasoning Nodes for Coup LLM Agents.

Nodes for the chat reasoning workflow:
1. analyze_message_node - Analyze incoming message intent and relevance
2. decide_response_node - Decide whether to respond
3. generate_response_node - Generate the actual response
4. decide_action_update_node - Decide if pending action should change

Analysis Mode:
- Controlled by AgentModulator.LLM_RELIANCE
- 0.0-0.3: Pure heuristics (fast, cheap)
- 0.3-0.7: Blended (heuristics + LLM validation)
- 0.7-1.0: LLM primary (more nuanced, expensive)
"""

from typing import Any, Dict, Optional, Tuple

from app.constants import AgentModulator, CoupAction, MessageTargetType, SocialMediaPlatform
from app.models.graph_state_models.chat_reasoning_state import (
    ChatReasoningState,
    MessageAnalysis,
    ResponseDecision,
    GeneratedResponse,
    ActionUpdateDecision,
)
from app.services.platform_response_router import (
    PlatformResponseRouter,
    get_platform_config,
)


# =============================================
# Analysis Mode Thresholds
# =============================================
LLM_RELIANCE_THRESHOLD_LOW = 0.3   # Below this: pure heuristics
LLM_RELIANCE_THRESHOLD_HIGH = 0.7  # Above this: LLM primary


# =============================================
# Analyze Message Node
# =============================================

def analyze_message_node(state: ChatReasoningState) -> Dict[str, Any]:
    """
    Analyze the incoming message to understand intent and relevance.
    
    Analysis mode is controlled by AgentModulator.LLM_RELIANCE:
    - Low (< 0.3): Pure heuristics (fast, cheap)
    - Medium (0.3-0.7): Blended analysis
    - High (> 0.7): LLM primary with heuristic fallback
    
    Returns:
        Dict with message_analysis and analysis_source
    """
    # Get LLM reliance setting from agent profile
    agent_profile = state.get("agent_profile", {})
    modulators = agent_profile.get("agent_modulators", {})
    llm_reliance = modulators.get(AgentModulator.LLM_RELIANCE, 0.3)
    
    # Always run heuristics (fast baseline)
    heuristic_analysis = _run_heuristic_analysis(state)
    
    # Determine analysis mode based on LLM_RELIANCE
    if llm_reliance < LLM_RELIANCE_THRESHOLD_LOW:
        # Pure heuristics mode
        return {
            "message_analysis": heuristic_analysis,
            "analysis_source": "heuristic",
        }
    
    # Try LLM analysis for medium/high reliance
    llm_analysis = None
    try:
        llm_analysis = _run_llm_analysis(state)
    except Exception as e:
        # LLM failed - fall back to heuristics
        pass
    
    if llm_analysis is None:
        # LLM unavailable or failed
        return {
            "message_analysis": heuristic_analysis,
            "analysis_source": "heuristic_fallback",
        }
    
    if llm_reliance >= LLM_RELIANCE_THRESHOLD_HIGH:
        # LLM primary mode - use LLM with heuristic validation
        final_analysis = _blend_analysis(llm_analysis, heuristic_analysis, llm_weight=0.8)
        return {
            "message_analysis": final_analysis,
            "analysis_source": "llm_primary",
        }
    
    # Blended mode - weight by llm_reliance
    llm_weight = (llm_reliance - LLM_RELIANCE_THRESHOLD_LOW) / (LLM_RELIANCE_THRESHOLD_HIGH - LLM_RELIANCE_THRESHOLD_LOW)
    final_analysis = _blend_analysis(llm_analysis, heuristic_analysis, llm_weight=llm_weight)
    return {
        "message_analysis": final_analysis,
        "analysis_source": "blended",
    }


def _run_heuristic_analysis(state: ChatReasoningState) -> MessageAnalysis:
    """Run fast heuristic-based message analysis."""
    incoming = state.get("incoming_message", {})
    content = incoming.get("content", "").lower()
    agent_name = state.get("agent_name", "").lower()
    agent_id = state.get("agent_id", "").lower()
    
    # Check if message mentions this agent
    mentions_agent = (
        agent_name in content or 
        agent_id in content or
        "@" + agent_id in content
    )
    
    # Detect intent from keywords
    intent = _detect_intent(content)
    
    # Detect mentioned action
    mentioned_action = _detect_action_mention(content)
    
    # Calculate scores
    relevance_score = _calculate_relevance(content, mentions_agent, mentioned_action)
    urgency_score = _calculate_urgency(content, mentions_agent, intent)
    threat_level = _calculate_threat(content, state)
    opportunity_score = _calculate_opportunity(content, state)
    
    # Detect tone
    sender_tone = _detect_tone(content)
    
    # Find mentioned players
    mentioned_players = _find_mentioned_players(content, state.get("players_alive", []))
    
    return MessageAnalysis(
        intent=intent,
        relevance_score=relevance_score,
        urgency_score=urgency_score,
        threat_level=threat_level,
        opportunity_score=opportunity_score,
        mentions_agent=mentions_agent,
        mentions_action=mentioned_action,
        mentioned_players=mentioned_players,
        sender_tone=sender_tone,
    )


def _run_llm_analysis(state: ChatReasoningState) -> Optional[MessageAnalysis]:
    """Run LLM-based message analysis using chat_message_analysis.md prompt."""
    from app.extensions import LoadedLLMs, LoadedPromptTemplates
    
    llm = LoadedLLMs.gpt_llm
    if not llm:
        return None
    
    # Get prompt template
    prompt_template = LoadedPromptTemplates.markdown_prompt_templates.get("chat_message_analysis")
    if not prompt_template:
        return None
    
    # Build context
    incoming = state.get("incoming_message", {})
    sender_is_llm = state.get("sender_is_llm", False)
    sender_type = "LLM Agent" if sender_is_llm else "Human Player"
    
    # Format visible pending actions
    visible_actions = state.get("visible_pending_actions", [])
    visible_actions_str = "\n".join([
        f"- {a.get('player_id')}: {a.get('action')} → {a.get('target', 'N/A')} {'(UPGRADED)' if a.get('is_upgraded') else ''}"
        for a in visible_actions
    ]) or "No visible pending actions"
    
    # Format chat history
    history = state.get("recent_chat_history", [])
    history_str = "\n".join([
        f"[{h.get('sender_id')}]: {h.get('content', '')[:100]}"
        for h in history[-5:]
    ]) or "No recent history"
    
    # Get current phase
    current_phase = state.get("current_phase", "unknown")
    if hasattr(current_phase, 'value'):
        current_phase = current_phase.value
    
    # Format prompt
    prompt = prompt_template.format(
        agent_name=state.get("agent_name", "Agent"),
        agent_personality=state.get("agent_personality", "neutral"),
        agent_play_style=state.get("agent_play_style", "balanced"),
        coins=state.get("coins", 0),
        hand=[c.value if hasattr(c, 'value') else str(c) for c in state.get("hand", [])],
        players_alive=state.get("players_alive", []),
        pending_action=state.get("pending_action"),
        current_phase=current_phase,
        visible_pending_actions=visible_actions_str,
        sender_id=state.get("sender_id", "Unknown"),
        sender_type=sender_type,
        source_platform=state.get("source_platform", "discord"),
        message_content=incoming.get("content", ""),
        chat_history=history_str,
    )
    
    # Invoke LLM
    try:
        result = llm.invoke(prompt)
        content = result.content if hasattr(result, 'content') else str(result)
        
        # Parse JSON response
        return _parse_llm_analysis(content)
    except Exception:
        return None


def _parse_llm_analysis(llm_response: str) -> Optional[MessageAnalysis]:
    """Parse LLM response into MessageAnalysis."""
    import json
    import re
    
    # Try to extract JSON from response
    json_match = re.search(r'\{[^{}]*\}', llm_response, re.DOTALL)
    if not json_match:
        return None
    
    try:
        data = json.loads(json_match.group())
        
        # Map LLM response to MessageAnalysis
        return MessageAnalysis(
            intent=data.get("intent", "unknown"),
            relevance_score=float(data.get("relevance_score", 0.5)),
            urgency_score=float(data.get("urgency_score", 0.5)),
            threat_level=float(data.get("threat_level", 0.0)),
            opportunity_score=float(data.get("opportunity_score", 0.5)),
            mentions_agent=bool(data.get("mentions_you", False)),
            mentions_action=data.get("mentioned_action"),
            mentioned_players=data.get("mentioned_players", []),
            sender_tone=data.get("sender_tone", "neutral"),
        )
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


def _blend_analysis(
    llm_analysis: MessageAnalysis,
    heuristic_analysis: MessageAnalysis,
    llm_weight: float = 0.5
) -> MessageAnalysis:
    """
    Blend LLM and heuristic analysis results.
    
    Args:
        llm_analysis: Analysis from LLM
        heuristic_analysis: Analysis from heuristics
        llm_weight: Weight for LLM (0.0-1.0), heuristic gets (1 - llm_weight)
    
    Returns:
        Blended MessageAnalysis
    """
    h_weight = 1.0 - llm_weight
    
    # Blend numeric scores
    blended_relevance = (llm_analysis.get("relevance_score", 0.5) * llm_weight + 
                        heuristic_analysis.get("relevance_score", 0.5) * h_weight)
    blended_urgency = (llm_analysis.get("urgency_score", 0.5) * llm_weight + 
                      heuristic_analysis.get("urgency_score", 0.5) * h_weight)
    blended_threat = (llm_analysis.get("threat_level", 0.0) * llm_weight + 
                     heuristic_analysis.get("threat_level", 0.0) * h_weight)
    blended_opportunity = (llm_analysis.get("opportunity_score", 0.5) * llm_weight + 
                          heuristic_analysis.get("opportunity_score", 0.5) * h_weight)
    
    # For categorical values, prefer LLM if high weight, else heuristic
    intent = llm_analysis.get("intent") if llm_weight > 0.5 else heuristic_analysis.get("intent")
    sender_tone = llm_analysis.get("sender_tone") if llm_weight > 0.5 else heuristic_analysis.get("sender_tone")
    
    # For boolean/list values, use OR logic for safety
    mentions_agent = llm_analysis.get("mentions_agent") or heuristic_analysis.get("mentions_agent")
    mentions_action = llm_analysis.get("mentions_action") or heuristic_analysis.get("mentions_action")
    
    # Merge mentioned players
    llm_players = llm_analysis.get("mentioned_players", [])
    heuristic_players = heuristic_analysis.get("mentioned_players", [])
    mentioned_players = list(set(llm_players + heuristic_players))
    
    return MessageAnalysis(
        intent=intent,
        relevance_score=blended_relevance,
        urgency_score=blended_urgency,
        threat_level=blended_threat,
        opportunity_score=blended_opportunity,
        mentions_agent=mentions_agent,
        mentions_action=mentions_action,
        mentioned_players=mentioned_players,
        sender_tone=sender_tone,
    )


def _detect_intent(content: str) -> str:
    """Detect message intent from content."""
    question_words = ["?", "who", "what", "why", "how", "do you", "are you", "did you"]
    accusation_words = ["liar", "lying", "bluff", "fake", "don't have", "doesn't have"]
    persuasion_words = ["should", "let's", "we could", "trust me", "work together", "alliance"]
    threat_words = ["coup", "assassinate", "target", "next", "watch out", "coming for"]
    
    if any(word in content for word in accusation_words):
        return "accusation"
    if any(word in content for word in threat_words):
        return "threat"
    if any(word in content for word in persuasion_words):
        return "persuasion"
    if any(word in content for word in question_words):
        return "question"
    if any(word in content for word in ["tax", "steal", "foreign aid", "duke", "captain", "assassin"]):
        return "game_talk"
    return "smalltalk"


def _detect_action_mention(content: str) -> str:
    """Detect if a Coup action is mentioned."""
    action_keywords = {
        CoupAction.INCOME: ["income"],
        CoupAction.FOREIGN_AID: ["foreign aid", "foreign_aid"],
        CoupAction.COUP: ["coup"],
        CoupAction.TAX: ["tax", "duke"],
        CoupAction.ASSASSINATE: ["assassinate", "assassin"],
        CoupAction.STEAL: ["steal", "captain"],
        CoupAction.EXCHANGE: ["exchange", "ambassador", "swap"],
    }
    
    for action, keywords in action_keywords.items():
        if any(kw in content for kw in keywords):
            return action
    return None


def _calculate_relevance(content: str, mentions_agent: bool, mentioned_action) -> float:
    """Calculate how relevant the message is to the agent."""
    score = 0.3  # Base relevance
    
    if mentions_agent:
        score += 0.4
    if mentioned_action:
        score += 0.2
    if len(content) > 50:  # Longer messages likely more substantive
        score += 0.1
    
    return min(1.0, score)


def _calculate_urgency(content: str, mentions_agent: bool, intent: str) -> float:
    """Calculate how urgently agent should respond."""
    score = 0.2  # Base urgency
    
    if mentions_agent:
        score += 0.3
    if intent in ["accusation", "threat"]:
        score += 0.3
    if intent == "question":
        score += 0.2
    if "?" in content:
        score += 0.1
    
    return min(1.0, score)


def _calculate_threat(content: str, state: ChatReasoningState) -> float:
    """Calculate threat level of the message."""
    score = 0.0
    
    threat_words = ["coup", "assassinate", "target", "kill", "eliminate", "coming for"]
    agent_name = state.get("agent_name", "").lower()
    
    for word in threat_words:
        if word in content.lower():
            score += 0.2
    
    # Higher threat if agent is mentioned with threat words
    if agent_name in content.lower() and score > 0:
        score += 0.3
    
    return min(1.0, score)


def _calculate_opportunity(content: str, state: ChatReasoningState) -> float:
    """Calculate opportunity score (chance to manipulate/persuade)."""
    score = 0.2  # Base opportunity
    
    opportunity_words = ["alliance", "together", "trust", "help", "team up"]
    if any(word in content.lower() for word in opportunity_words):
        score += 0.3
    
    # Questions are opportunities to shape perception
    if "?" in content:
        score += 0.2
    
    return min(1.0, score)


def _detect_tone(content: str) -> str:
    """Detect the sender's tone."""
    hostile_words = ["liar", "hate", "stupid", "idiot", "kill"]
    friendly_words = ["friend", "ally", "together", "help", "thanks", "haha", "lol"]
    suspicious_words = ["really", "sure about that", "doubt", "suspicious", "hmm"]
    
    if any(word in content.lower() for word in hostile_words):
        return "hostile"
    if any(word in content.lower() for word in friendly_words):
        return "friendly"
    if any(word in content.lower() for word in suspicious_words):
        return "suspicious"
    return "neutral"


def _find_mentioned_players(content: str, players_alive: list) -> list:
    """Find which players are mentioned in the message."""
    mentioned = []
    content_lower = content.lower()
    for player in players_alive:
        if player.lower() in content_lower:
            mentioned.append(player)
    return mentioned


# =============================================
# Decide Response Node
# =============================================

def decide_response_node(state: ChatReasoningState) -> Dict[str, Any]:
    """
    Decide whether the agent should respond to the message.
    
    Considers:
    - Message relevance and urgency
    - Message limits
    - Strategic value of responding
    - Agent personality
    """
    analysis = state.get("message_analysis", {})
    can_respond = state.get("can_respond", False)
    messages_remaining = state.get("messages_remaining", 0)
    play_style = state.get("agent_play_style", "balanced")
    
    # ========== Check Hard Limits ==========
    
    if not can_respond:
        return {
            "response_decision": ResponseDecision(
                should_respond=False,
                response_priority="none",
                reason="Message limit reached",
                skip_reason="limit_reached",
            )
        }
    
    # ========== Calculate Response Priority ==========
    
    relevance = analysis.get("relevance_score", 0)
    urgency = analysis.get("urgency_score", 0)
    threat = analysis.get("threat_level", 0)
    opportunity = analysis.get("opportunity_score", 0)
    mentions_agent = analysis.get("mentions_agent", False)
    
    # Combine factors
    priority_score = (
        relevance * 0.3 +
        urgency * 0.3 +
        threat * 0.2 +
        opportunity * 0.2
    )
    
    # Adjust for play style
    if "quiet" in play_style.lower() or "passive" in play_style.lower():
        priority_score *= 0.7  # Less likely to respond
    elif "aggressive" in play_style.lower() or "chatty" in play_style.lower():
        priority_score *= 1.3  # More likely to respond
    
    # ========== Make Decision ==========
    
    # Always respond if directly mentioned
    if mentions_agent and can_respond:
        return {
            "response_decision": ResponseDecision(
                should_respond=True,
                response_priority="high",
                reason="Directly mentioned - should respond",
            )
        }
    
    # High priority threshold
    if priority_score > 0.6:
        return {
            "response_decision": ResponseDecision(
                should_respond=True,
                response_priority="high",
                reason=f"High priority score ({priority_score:.2f})",
            )
        }
    
    # Medium priority - respond if plenty of messages left
    if priority_score > 0.4 and messages_remaining > 10:
        return {
            "response_decision": ResponseDecision(
                should_respond=True,
                response_priority="medium",
                reason=f"Medium priority, messages available",
            )
        }
    
    # Low priority - only respond if very high message budget
    if priority_score > 0.25 and messages_remaining > 50:
        return {
            "response_decision": ResponseDecision(
                should_respond=True,
                response_priority="low",
                reason="Low priority but high message budget",
            )
        }
    
    # Default: don't respond
    return {
        "response_decision": ResponseDecision(
            should_respond=False,
            response_priority="none",
            reason="Not relevant enough to spend message budget",
            skip_reason="not_relevant",
        )
    }


# =============================================
# Generate Response Node
# =============================================

def generate_response_node(state: ChatReasoningState) -> Dict[str, Any]:
    """
    Generate the actual chat response.
    
    Uses LLM with agent personality and game context to craft response.
    Falls back to heuristic responses if LLM unavailable.
    Formats response for the target platform.
    """
    decision = state.get("response_decision", {})
    
    # Skip if not responding
    if not decision.get("should_respond", False):
        return {
            "generated_response": None,
            "final_response": None,
            "formatted_response": None,
        }
    
    analysis = state.get("message_analysis", {})
    incoming = state.get("incoming_message", {})
    
    # Get platform info
    source_platform = state.get("source_platform", SocialMediaPlatform.DEFUALT)
    if isinstance(source_platform, str):
        try:
            source_platform = SocialMediaPlatform(source_platform)
        except ValueError:
            source_platform = SocialMediaPlatform.DEFUALT
    
    # Try LLM generation
    response = None
    try:
        response = _generate_llm_response(state)
    except Exception:
        pass  # Fall back to heuristic
    
    # Heuristic fallback
    if not response:
        response = _generate_heuristic_response(state)
    
    # Format for target platform
    platform_router = PlatformResponseRouter()
    mentioned_players = analysis.get("mentioned_players", [])
    sender_id = state.get("sender_id")
    
    # Include sender in mentions if replying directly
    mentions = list(set([sender_id] + mentioned_players)) if sender_id else mentioned_players
    
    formatted = platform_router.route_response(
        content=response.get("content", ""),
        source_platform=source_platform,
        mentions=mentions,
        thread_id=state.get("thread_id"),
        reply_to=state.get("reply_to_message_id"),
    )
    
    # Update response with platform-formatted content
    response["content"] = formatted.content
    response["target_platform"] = formatted.platform.value
    response["was_truncated"] = formatted.was_truncated
    
    return {
        "generated_response": response,
        "final_response": formatted.content,
        "formatted_response": {
            "content": formatted.content,
            "platform": formatted.platform.value,
            "was_truncated": formatted.was_truncated,
            "mentions": formatted.mentions,
            "metadata": formatted.metadata,
        },
    }


def _generate_llm_response(state: ChatReasoningState) -> GeneratedResponse:
    """Generate response using LLM."""
    from app.extensions import LoadedLLMs, LoadedPromptTemplates
    
    llm = LoadedLLMs.gpt_llm
    if not llm:
        return None
    
    # Get prompt template
    prompt_template = LoadedPromptTemplates.markdown_prompt_templates.get("chat_response_generation")
    if not prompt_template:
        return None
    
    # Format prompt
    incoming = state.get("incoming_message", {})
    analysis = state.get("message_analysis", {})
    
    # Format visible actions
    visible_actions = state.get("visible_pending_actions", [])
    visible_actions_str = "\n".join([
        f"- {a.get('player_id')}: {a.get('action')} -> {a.get('target', 'N/A')} {'(UPGRADED)' if a.get('is_upgraded') else ''}"
        for a in visible_actions
    ]) or "No visible pending actions"
    
    # Format chat history
    history = state.get("recent_chat_history", [])
    history_str = "\n".join([
        f"[{h.get('sender_id')}]: {h.get('content', '')[:100]}"
        for h in history[-5:]  # Last 5 messages
    ]) or "No recent history"
    
    prompt = prompt_template.format(
        agent_name=state.get("agent_name", "Agent"),
        agent_personality=state.get("agent_personality", "neutral"),
        agent_play_style=state.get("agent_play_style", "balanced"),
        coins=state.get("coins", 0),
        hand=[c.value if hasattr(c, 'value') else str(c) for c in state.get("hand", [])],
        revealed=[c.value if hasattr(c, 'value') else str(c) for c in state.get("revealed", [])],
        players_alive=state.get("players_alive", []),
        pending_action=state.get("pending_action"),
        visible_pending_actions=visible_actions_str,
        sender_id=state.get("sender_id", "Unknown"),
        message_content=incoming.get("content", ""),
        intent=analysis.get("intent", "unknown"),
        relevance_score=analysis.get("relevance_score", 0),
        threat_level=analysis.get("threat_level", 0),
        sender_tone=analysis.get("sender_tone", "neutral"),
        chat_history=history_str,
        source_platform=state.get("source_platform", "discord"),
    )
    
    # Invoke LLM
    result = llm.invoke(prompt)
    content = result.content if hasattr(result, 'content') else str(result)
    
    return GeneratedResponse(
        content=content,
        tone="neutral",  # Could be extracted from LLM response
        strategy="adaptive",
        bluffing=False,
        confidence=0.7,
    )


def _generate_heuristic_response(state: ChatReasoningState) -> GeneratedResponse:
    """Generate a heuristic-based response when LLM unavailable."""
    analysis = state.get("message_analysis", {})
    incoming = state.get("incoming_message", {})
    agent_name = state.get("agent_name", "Agent")
    intent = analysis.get("intent", "smalltalk")
    sender_id = state.get("sender_id", "someone")
    
    # Generate based on intent
    if intent == "accusation":
        responses = [
            f"Me? I don't know what you're talking about, {sender_id}.",
            "Interesting accusation. Got any proof?",
            "I think you're barking up the wrong tree here.",
        ]
    elif intent == "threat":
        responses = [
            "Noted. We'll see how that works out.",
            "Threatening me? Bold move.",
            "I'd reconsider that if I were you.",
        ]
    elif intent == "question":
        responses = [
            "Hmm, that's a good question.",
            "I could tell you, but where's the fun in that?",
            "Why do you want to know?",
        ]
    elif intent == "persuasion":
        responses = [
            "I'll think about it.",
            "What's in it for me?",
            "Interesting proposal...",
        ]
    else:
        responses = [
            "Indeed.",
            "Interesting point.",
            "I see.",
        ]
    
    import random
    content = random.choice(responses)
    
    return GeneratedResponse(
        content=content,
        tone="neutral",
        strategy="vague",
        bluffing=False,
        confidence=0.5,
    )


# =============================================
# Decide Action Update Node
# =============================================

def decide_action_update_node(state: ChatReasoningState) -> Dict[str, Any]:
    """
    Decide if the conversation should cause the agent to update their pending action.
    
    Considers:
    - Threats revealed in conversation
    - Alliance opportunities
    - New information about other players
    """
    analysis = state.get("message_analysis", {})
    action_locked = state.get("action_locked", False)
    
    # Can't update if locked
    if action_locked:
        return {
            "action_update_decision": ActionUpdateDecision(
                should_update=False,
                reason="Actions are locked (final 10 minutes)",
            )
        }
    
    threat_level = analysis.get("threat_level", 0)
    mentioned_action = analysis.get("mentions_action")
    
    # High threat might warrant changing target
    if threat_level > 0.7:
        return {
            "action_update_decision": ActionUpdateDecision(
                should_update=True,
                reason="High threat detected - consider defensive action",
                new_action=None,  # To be determined by action selection
                new_target=state.get("sender_id"),  # Target the threatener
            )
        }
    
    # Default: don't update based on chat alone
    return {
        "action_update_decision": ActionUpdateDecision(
            should_update=False,
            reason="No compelling reason to change pending action",
        )
    }

