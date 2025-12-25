"""
Broadcast Commentary Nodes.

LangGraph nodes for analyzing game results and generating
optional agent commentary at the end of each hour.

Nodes:
1. analyze_results_node - Analyze how results affect the agent
2. decide_commentary_node - Decide whether to comment
3. generate_commentary_node - Generate in-character commentary
"""

from typing import Any, Dict

from app.constants import MessageTargetType
from app.models.graph_state_models.broadcast_commentary_state import (
    BroadcastCommentaryState,
    ResultAnalysis,
    CommentaryDecision,
    GeneratedCommentary,
)


# =============================================
# Analyze Results Node
# =============================================
def analyze_results_node(state: BroadcastCommentaryState) -> Dict[str, Any]:
    """
    Analyze game results and determine impact on agent.
    
    Identifies:
    - Whether agent was directly involved
    - Dramatic events worth commenting on
    - Opportunities for strategic commentary
    """
    agent_id = state.get("agent_id")
    results = state.get("results", [])
    players_remaining = state.get("players_remaining", [])
    is_game_over = state.get("is_game_over", False)
    was_eliminated = state.get("was_eliminated_this_round", False)
    
    # Track agent involvement
    agent_was_actor = False
    agent_was_target = False
    agent_action_succeeded = False
    agent_bluff_caught = False
    agent_bluff_succeeded = False
    
    # Track drama
    drama_score = 0.0
    drama_reasons = []
    players_to_mention = []
    
    for result in results:
        actor = result.get("actor")
        target = result.get("target")
        succeeded = result.get("succeeded", False)
        eliminated = result.get("eliminated_player")
        bluff_caught = result.get("bluff_caught", False)
        bluff_succeeded = result.get("bluff_succeeded", False)
        
        # Check agent involvement
        if actor == agent_id:
            agent_was_actor = True
            agent_action_succeeded = succeeded
            if bluff_caught:
                agent_bluff_caught = True
            if bluff_succeeded:
                agent_bluff_succeeded = True
        
        if target == agent_id:
            agent_was_target = True
        
        # Track eliminated players (dramatic!)
        if eliminated:
            drama_score += 0.3
            if eliminated == agent_id:
                drama_score += 0.5
                drama_reasons.append(f"{agent_id} was eliminated!")
            else:
                players_to_mention.append(eliminated)
                drama_reasons.append(f"{eliminated} was eliminated")
        
        # Track bluffs (dramatic!)
        if bluff_caught:
            drama_score += 0.2
            drama_reasons.append("A bluff was caught")
        if bluff_succeeded:
            drama_score += 0.15
            drama_reasons.append("A bluff succeeded")
        
        # Track actors and targets for potential mentions
        if actor and actor != agent_id and actor not in players_to_mention:
            players_to_mention.append(actor)
    
    # Game end is very dramatic
    if is_game_over:
        drama_score += 0.5
        drama_reasons.append("Game has ended!")
    
    # Final 2-3 players is dramatic
    if len(players_remaining) <= 3:
        drama_score += 0.2
        drama_reasons.append(f"Only {len(players_remaining)} players left")
    
    # Cap drama score
    drama_score = min(drama_score, 1.0)
    is_dramatic = drama_score >= 0.3
    
    # Determine commentary opportunity
    has_opportunity = False
    commentary_type = "none"
    
    if was_eliminated:
        has_opportunity = True
        commentary_type = "defeat"
    elif agent_was_actor and agent_action_succeeded:
        has_opportunity = True
        commentary_type = "victory"
    elif agent_was_target and not was_eliminated:
        has_opportunity = True
        commentary_type = "survival"
    elif agent_bluff_succeeded:
        has_opportunity = True
        commentary_type = "taunt"  # Can't reveal we bluffed, but can gloat
    elif is_dramatic:
        has_opportunity = True
        commentary_type = "observation"
    
    analysis = ResultAnalysis(
        agent_was_actor=agent_was_actor,
        agent_was_target=agent_was_target,
        agent_was_eliminated=was_eliminated,
        agent_action_succeeded=agent_action_succeeded,
        agent_bluff_caught=agent_bluff_caught,
        agent_bluff_succeeded=agent_bluff_succeeded,
        is_dramatic=is_dramatic,
        drama_reason="; ".join(drama_reasons) if drama_reasons else "Nothing notable",
        drama_score=drama_score,
        players_to_mention=players_to_mention[:3],  # Limit mentions
        has_commentary_opportunity=has_opportunity,
        commentary_type=commentary_type,
    )
    
    return {"result_analysis": analysis}


# =============================================
# Decide Commentary Node
# =============================================
def decide_commentary_node(state: BroadcastCommentaryState) -> Dict[str, Any]:
    """
    Decide whether the agent should comment on results.
    
    Considers:
    - Message limits
    - Relevance to agent
    - Strategic value of commenting
    - Agent personality
    """
    can_comment = state.get("can_comment", False)
    messages_remaining = state.get("messages_remaining", 0)
    analysis = state.get("result_analysis")
    agent_personality = state.get("agent_personality", "neutral")
    agent_play_style = state.get("agent_play_style", "balanced")
    
    # Can't comment if no messages remaining
    if not can_comment or messages_remaining <= 0:
        return {
            "commentary_decision": CommentaryDecision(
                should_comment=False,
                priority="none",
                reason="No messages remaining",
            )
        }
    
    # No analysis means nothing to comment on
    if not analysis:
        return {
            "commentary_decision": CommentaryDecision(
                should_comment=False,
                priority="none",
                reason="No analysis available",
            )
        }
    
    # Decide based on analysis
    has_opportunity = analysis.get("has_commentary_opportunity", False)
    commentary_type = analysis.get("commentary_type", "none")
    drama_score = analysis.get("drama_score", 0.0)
    was_eliminated = analysis.get("agent_was_eliminated", False)
    
    # Always comment if eliminated (famous last words!)
    if was_eliminated:
        return {
            "commentary_decision": CommentaryDecision(
                should_comment=True,
                priority="high",
                reason="Agent was eliminated - final words",
                commentary_angle="mourn" if "cautious" in agent_play_style.lower() else "taunt",
                target_audience="everyone",
                emotional_tone="bitter" if drama_score > 0.5 else "gracious",
            )
        }
    
    # High drama events get commentary
    if has_opportunity and drama_score >= 0.5:
        angle = _determine_commentary_angle(commentary_type, agent_personality)
        tone = _determine_emotional_tone(commentary_type, agent_personality, agent_play_style)
        
        return {
            "commentary_decision": CommentaryDecision(
                should_comment=True,
                priority="high",
                reason=f"High drama event: {commentary_type}",
                commentary_angle=angle,
                target_audience="everyone",
                emotional_tone=tone,
            )
        }
    
    # Medium drama - personality dependent
    if has_opportunity and drama_score >= 0.3:
        # Aggressive/chaotic personalities comment more
        should_comment = (
            "aggressive" in agent_play_style.lower() or
            "chaotic" in agent_play_style.lower() or
            "charming" in agent_personality.lower()
        )
        
        if should_comment:
            angle = _determine_commentary_angle(commentary_type, agent_personality)
            tone = _determine_emotional_tone(commentary_type, agent_personality, agent_play_style)
            
            return {
                "commentary_decision": CommentaryDecision(
                    should_comment=True,
                    priority="medium",
                    reason=f"Notable event, personality inclined to comment: {commentary_type}",
                    commentary_angle=angle,
                    target_audience="everyone",
                    emotional_tone=tone,
                )
            }
    
    # Low drama or cautious personality - probably skip
    return {
        "commentary_decision": CommentaryDecision(
            should_comment=False,
            priority="low",
            reason="Event not significant enough to warrant commentary",
        )
    }


def _determine_commentary_angle(commentary_type: str, personality: str) -> str:
    """Determine the angle for commentary based on type and personality."""
    if commentary_type == "victory":
        if "cunning" in personality.lower() or "aggressive" in personality.lower():
            return "taunt"
        return "celebrate"
    elif commentary_type == "defeat":
        return "mourn"
    elif commentary_type == "survival":
        return "deflect"
    elif commentary_type == "taunt":
        return "taunt"
    else:
        return "analyze"


def _determine_emotional_tone(commentary_type: str, personality: str, play_style: str) -> str:
    """Determine emotional tone based on context and personality."""
    if commentary_type == "victory":
        if "aggressive" in play_style.lower():
            return "triumphant"
        if "charming" in personality.lower():
            return "playful"
        return "amused"
    elif commentary_type == "defeat":
        if "aggressive" in play_style.lower():
            return "bitter"
        return "gracious"
    elif commentary_type == "survival":
        return "relieved"
    else:
        if "paranoid" in personality.lower():
            return "suspicious"
        return "analytical"


# =============================================
# Generate Commentary Node
# =============================================
def generate_commentary_node(state: BroadcastCommentaryState) -> Dict[str, Any]:
    """
    Generate in-character commentary about the game results.
    
    Uses LLM to generate commentary based on:
    - Agent personality
    - Game context
    - Commentary decision
    """
    decision = state.get("commentary_decision")
    analysis = state.get("result_analysis")
    
    # Skip if decided not to comment
    if not decision or not decision.get("should_comment"):
        return {
            "generated_commentary": None,
            "final_commentary": None,
        }
    
    # Get context
    agent_name = state.get("agent_name", "Agent")
    agent_personality = state.get("agent_personality", "neutral")
    results = state.get("results", [])
    players_remaining = state.get("players_remaining", [])
    is_game_over = state.get("is_game_over", False)
    winner = state.get("winner")
    
    commentary_angle = decision.get("commentary_angle", "analyze")
    emotional_tone = decision.get("emotional_tone", "neutral")
    commentary_type = analysis.get("commentary_type", "observation") if analysis else "observation"
    players_to_mention = analysis.get("players_to_mention", []) if analysis else []
    was_eliminated = analysis.get("agent_was_eliminated", False) if analysis else False
    
    # Build context for LLM
    try:
        commentary = _generate_commentary_with_llm(
            agent_name=agent_name,
            agent_personality=agent_personality,
            commentary_type=commentary_type,
            commentary_angle=commentary_angle,
            emotional_tone=emotional_tone,
            results=results,
            players_to_mention=players_to_mention,
            players_remaining=players_remaining,
            is_game_over=is_game_over,
            winner=winner,
            was_eliminated=was_eliminated,
        )
    except Exception as e:
        # Fallback to template-based commentary
        commentary = _generate_fallback_commentary(
            agent_name=agent_name,
            commentary_type=commentary_type,
            emotional_tone=emotional_tone,
            was_eliminated=was_eliminated,
            is_game_over=is_game_over,
            winner=winner,
        )
    
    generated = GeneratedCommentary(
        content=commentary,
        tone=emotional_tone,
        mentions=players_to_mention,
        strategic_intent="neutral",
        reveals_info=False,
        confidence=0.8,
    )
    
    return {
        "generated_commentary": generated,
        "final_commentary": commentary,
    }


def _generate_commentary_with_llm(
    agent_name: str,
    agent_personality: str,
    commentary_type: str,
    commentary_angle: str,
    emotional_tone: str,
    results: list,
    players_to_mention: list,
    players_remaining: list,
    is_game_over: bool,
    winner: str,
    was_eliminated: bool,
) -> str:
    """Generate commentary using LLM."""
    from app.extensions import LoadedLLMs
    
    llm = LoadedLLMs.gpt_llm
    if not llm:
        raise ValueError("No LLM available")
    
    # Build prompt
    results_summary = []
    for r in results[:5]:  # Limit to first 5 results
        actor = r.get("actor", "Someone")
        action = r.get("action", "did something")
        target = r.get("target", "")
        succeeded = r.get("succeeded", True)
        eliminated = r.get("eliminated_player")
        
        if eliminated:
            results_summary.append(f"- {actor} {action}ed {target}, {eliminated} was eliminated!")
        elif succeeded:
            results_summary.append(f"- {actor} successfully {action}ed {target if target else ''}")
        else:
            results_summary.append(f"- {actor} failed to {action} {target if target else ''}")
    
    results_text = "\n".join(results_summary) if results_summary else "No significant events."
    
    prompt = f"""You are {agent_name}, a player in an online Coup game. Your personality is: {agent_personality}

The hourly results have just been announced:
{results_text}

Players still in the game: {', '.join(players_remaining) if players_remaining else 'Unknown'}
{'The game is OVER! Winner: ' + winner if is_game_over else ''}
{'YOU WERE ELIMINATED THIS ROUND!' if was_eliminated else ''}

Generate a SHORT (1-2 sentences) in-character reaction to these results.
- Commentary type: {commentary_type}
- Angle: {commentary_angle}  
- Tone: {emotional_tone}
- Players you might mention: {', '.join(players_to_mention) if players_to_mention else 'None specifically'}

Stay in character. Be {emotional_tone}. {'This is your final message!' if was_eliminated else ''}
Don't reveal your cards or strategy.

Your reaction:"""

    response = llm.invoke(prompt)
    return response.content.strip()


def _generate_fallback_commentary(
    agent_name: str,
    commentary_type: str,
    emotional_tone: str,
    was_eliminated: bool,
    is_game_over: bool,
    winner: str,
) -> str:
    """Generate template-based fallback commentary."""
    templates = {
        ("victory", "triumphant"): "Ha! Just as I planned. 😏",
        ("victory", "playful"): "Well, that worked out nicely! 🎯",
        ("victory", "amused"): "Interesting turn of events...",
        ("defeat", "bitter"): "This isn't over. Not by a long shot.",
        ("defeat", "gracious"): "Well played, everyone. Until next time.",
        ("survival", "relieved"): "Still here. Still dangerous.",
        ("taunt", "triumphant"): "Did anyone really think that would work? 😂",
        ("observation", "analytical"): "The board has shifted. Adapt or perish.",
        ("observation", "suspicious"): "Something doesn't add up here...",
    }
    
    if was_eliminated:
        return f"You haven't seen the last of {agent_name}. Mark my words."
    
    if is_game_over:
        if winner == agent_name:
            return "Victory! 👑 A masterful performance, if I do say so myself."
        else:
            return f"Congratulations to {winner}. A worthy opponent."
    
    key = (commentary_type, emotional_tone)
    return templates.get(key, "Interesting developments...")

