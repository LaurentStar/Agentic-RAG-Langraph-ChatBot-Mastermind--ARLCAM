"""
Decision Blender Service - Combines heuristic and LLM reasoning based on agent modulators.

The blender determines when to use pure heuristics, when to consult the LLM,
and how to weight their recommendations.

Key principles:
    1. Forced plays bypass LLM entirely (e.g., must coup at 10+ coins)
    2. Safe plays lean toward heuristics (less token cost)
    3. Bluff-heavy decisions lean toward LLM (needs nuanced reasoning)
    4. Modulators control the blend ratio
"""

from typing import Any, Dict, List, Optional, Tuple

from app.constants import (
    ACTION_TO_ROLE,
    AgentModulator,
    CoupAction,
    InfluenceCard,
)
from app.models.decision_models.blended_decision import BlendedDecision
from app.models.graph_state_models.coup_agent_state import AgentProfile, CoupAgentState, PublicEvent
from app.services.coup_heuristics import (
    select_action_heuristic,
)


class DecisionBlenderService:
    """
    Blends heuristic and LLM decisions based on agent modulators.

    The blender uses modulators to determine:
        - Whether to even call the LLM (expensive operations)
        - How to weight heuristic vs LLM recommendations
        - When to override one with the other
    """

    # Thresholds for LLM consultation
    LLM_THRESHOLD_BLUFF = 0.4
    LLM_THRESHOLD_CHALLENGE = 0.5
    LLM_THRESHOLD_RISK = 0.6

    @staticmethod
    def should_use_llm(
        state: CoupAgentState,
        decision_context: str = "action"
    ) -> Tuple[bool, str]:
        """
        Determine if LLM should be consulted for this decision.

        Args:
            state: Current game state
            decision_context: "action", "react", or "resolve"

        Returns:
            (should_use, reason)
        """
        agent_profile = state.get("agent_profile", {})
        modulators = agent_profile.get("agent_modulators", {})
        coins = state.get("coins", 0)
        hand = state.get("hand", [])

        # ========== FORCED PLAYS: Never use LLM ==========
        if coins >= 10 and decision_context == "action":
            return False, "Forced coup at 10+ coins - no decision needed"

        if decision_context == "resolve" and len(hand) == 1:
            return False, "Only one card to reveal - no decision needed"

        # ========== OBVIOUS SAFE PLAYS: Prefer heuristics ==========
        bluff_confidence = modulators.get(AgentModulator.BLUFF_CONFIDENCE, 0.3)
        if bluff_confidence < 0.3 and decision_context == "action":
            return False, "Low bluff confidence - use safe heuristic plays"

        # ========== BLUFF-HEAVY CONTEXTS: Use LLM ==========
        if bluff_confidence > DecisionBlenderService.LLM_THRESHOLD_BLUFF:
            return True, f"High bluff confidence ({bluff_confidence:.2f}) - LLM for nuanced bluffing"

        # ========== CHALLENGE DECISIONS: Often need LLM ==========
        challenge_tendency = modulators.get(AgentModulator.CHALLENGE_TENDENCY, 0.3)
        if decision_context == "react" and challenge_tendency > DecisionBlenderService.LLM_THRESHOLD_CHALLENGE:
            return True, f"High challenge tendency ({challenge_tendency:.2f}) - LLM for challenge analysis"

        # ========== RISKY SITUATIONS: Consult LLM ==========
        risk_tolerance = modulators.get(AgentModulator.RISK_TOLERANCE, 0.5)
        if risk_tolerance > DecisionBlenderService.LLM_THRESHOLD_RISK:
            return True, f"High risk tolerance ({risk_tolerance:.2f}) - LLM for risky play analysis"

        return False, "Default to heuristics for efficiency"

    @staticmethod
    def blend_action_decision(
        state: CoupAgentState,
        heuristic_result: Tuple[CoupAction, Optional[str], Optional[InfluenceCard], str],
        llm_result: Optional[Dict[str, Any]] = None,
    ) -> BlendedDecision:
        """
        Blend heuristic and LLM action decisions.
        """
        h_action, h_target, h_role, h_reasoning = heuristic_result

        if llm_result is None:
            return BlendedDecision(
                action=h_action,
                target=h_target,
                claimed_role=h_role,
                reasoning=h_reasoning,
                confidence=0.7,
                source="heuristic"
            )

        agent_profile = state.get("agent_profile", {})
        modulators = agent_profile.get("agent_modulators", {})
        hand = state.get("hand", [])

        l_action = llm_result.get("action")
        l_target = llm_result.get("target")
        l_role = llm_result.get("claimed_role")
        l_reasoning = llm_result.get("reasoning", "")
        l_confidence = llm_result.get("confidence", 0.5)

        # ========== AGREEMENT: Both recommend same action ==========
        if h_action == l_action:
            return BlendedDecision(
                action=h_action,
                target=l_target or h_target,
                claimed_role=l_role or h_role,
                reasoning=f"[Agreed] {l_reasoning}",
                confidence=min(1.0, l_confidence + 0.2),
                source="blended"
            )

        # ========== DISAGREEMENT: Weight by modulators ==========
        bluff_confidence = modulators.get(AgentModulator.BLUFF_CONFIDENCE, 0.3)
        risk_tolerance = modulators.get(AgentModulator.RISK_TOLERANCE, 0.5)

        llm_weight = (bluff_confidence + risk_tolerance) / 2

        is_llm_bluff = l_role and l_role not in hand
        is_heuristic_safe = h_role is None or h_role in hand

        if is_llm_bluff and bluff_confidence > 0.5:
            return BlendedDecision(
                action=l_action,
                target=l_target,
                claimed_role=l_role,
                reasoning=f"[LLM Bluff] {l_reasoning}",
                confidence=l_confidence,
                source="llm"
            )

        if is_heuristic_safe and is_llm_bluff and risk_tolerance < 0.5:
            return BlendedDecision(
                action=h_action,
                target=h_target,
                claimed_role=h_role,
                reasoning=f"[Safe Choice] {h_reasoning}",
                confidence=0.8,
                source="heuristic"
            )

        if llm_weight > 0.5:
            return BlendedDecision(
                action=l_action,
                target=l_target,
                claimed_role=l_role,
                reasoning=f"[LLM Preferred] {l_reasoning}",
                confidence=l_confidence,
                source="llm"
            )
        else:
            return BlendedDecision(
                action=h_action,
                target=h_target,
                claimed_role=h_role,
                reasoning=f"[Heuristic Preferred] {h_reasoning}",
                confidence=0.7,
                source="heuristic"
            )

    @staticmethod
    def blend_reaction_decision(
        state: CoupAgentState,
        heuristic_result: Tuple[bool, str],
        llm_result: Optional[Dict[str, Any]] = None,
        reaction_type: str = "challenge"
    ) -> BlendedDecision:
        """
        Blend heuristic and LLM reaction decisions.
        """
        h_should_react, h_reasoning = heuristic_result

        if llm_result is None:
            reaction = CoupAction.CHALLENGE if h_should_react and reaction_type == "challenge" else CoupAction.PASS
            return BlendedDecision(
                action=reaction,
                reasoning=h_reasoning,
                confidence=0.6,
                source="heuristic"
            )

        l_reaction = llm_result.get("reaction")
        l_role = llm_result.get("claimed_role")
        l_reasoning = llm_result.get("reasoning", "")
        l_confidence = llm_result.get("confidence", 0.5)

        if l_confidence > 0.7:
            return BlendedDecision(
                action=l_reaction,
                claimed_role=l_role,
                reasoning=f"[LLM High Confidence] {l_reasoning}",
                confidence=l_confidence,
                source="llm"
            )

        h_reaction = CoupAction.CHALLENGE if h_should_react and reaction_type == "challenge" else CoupAction.PASS
        return BlendedDecision(
            action=h_reaction,
            reasoning=f"[Heuristic Safe] {h_reasoning}",
            confidence=0.6,
            source="heuristic"
        )


# Keep backwards compatibility alias
DecisionBlender = DecisionBlenderService


def get_blended_action(state: CoupAgentState) -> BlendedDecision:
    """
    Main entry point for blended action selection.

    Checks if LLM should be used, runs heuristics, optionally consults LLM,
    and blends the results.
    """
    heuristic_result = select_action_heuristic(
        coins=state.get("coins", 0),
        hand=state.get("hand", []),
        players_alive=state.get("players_alive", []),
        forced_targets=state.get("forced_targets"),
        agent_profile=state.get("agent_profile"),
    )

    should_use_llm, reason = DecisionBlenderService.should_use_llm(state, "action")

    llm_result = None
    if should_use_llm:
        try:
            from app.chains.coup_reasoning import CoupReasoningChains

            llm_input = {
                "me": state.get("me", "agent"),
                "coins": state.get("coins", 0),
                "hand": [c.value for c in state.get("hand", [])],
                "players_alive": state.get("players_alive", []),
                "public_events": _format_events(state.get("public_events", [])),
                "agent_personality": state.get("agent_profile", {}).get("agent_personality", ""),
                "agent_play_style": state.get("agent_profile", {}).get("agent_play_style", ""),
                "legal_actions": _get_legal_actions(state),
            }

            chain = CoupReasoningChains.get_action_chain()
            llm_output = chain.invoke(llm_input)
            llm_result = llm_output.model_dump() if hasattr(llm_output, 'model_dump') else llm_output
        except Exception:
            llm_result = None

    return DecisionBlenderService.blend_action_decision(state, heuristic_result, llm_result)


def _format_events(events: List[PublicEvent]) -> str:
    """Format public events for LLM prompt."""
    if not events:
        return "No events yet."

    lines = []
    for event in events[-10:]:
        actor = event.get("actor", "?")
        action = event.get("action", "?")
        target = event.get("target")
        target_str = f" → {target}" if target else ""
        lines.append(f"- {actor}: {action}{target_str}")

    return "\n".join(lines)


def _get_legal_actions(state: CoupAgentState) -> str:
    """Get list of legal actions for current state."""
    coins = state.get("coins", 0)
    actions = []

    actions.append("income (take 1 coin)")
    actions.append("foreign_aid (take 2 coins, can be blocked)")

    if coins >= 7:
        actions.append("coup (7 coins, eliminate one influence)")

    if coins >= 10:
        return "coup (REQUIRED at 10+ coins)"

    actions.append("tax (claim Duke, take 3 coins)")
    actions.append("steal (claim Captain, take 2 coins from target)")
    actions.append("exchange (claim Ambassador, swap cards)")

    if coins >= 3:
        actions.append("assassinate (claim Assassin, 3 coins, eliminate target's influence)")

    return "\n".join(f"- {a}" for a in actions)

