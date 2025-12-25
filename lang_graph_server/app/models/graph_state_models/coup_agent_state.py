"""
State and enums for a single Coup agent's view of the game.

This state is agent-local: it contains the agent's private hand plus the
public table information needed to decide an action or reaction. A separate
referee/game-engine should construct this state view and apply the results.
"""

from typing import Dict, List, Optional, TypedDict

from app.constants import (
    AgentModulator,
    CoupAction,
    DecisionType,
    InfluenceCard,
    ReactionType,
    ResolutionType,
)


AgentModulators = Dict[
    AgentModulator,
    float,
]
"""Tunable knobs that adjust how the agent plays. Values are expected in roughly [0, 1]."""


class AgentProfile(TypedDict, total=False):
    """
    Base agent attributes akin to the generic agent graph state definitions.
    """

    agent_name: str
    agent_play_style: str
    agent_personality: str
    agent_modulators: AgentModulators


class PublicEvent(TypedDict, total=False):
    """
    A public log entry of what happened on the table.

    This keeps a lightweight history that agents can reason over.
    """

    actor: str
    action: CoupAction
    target: Optional[str]
    succeeded: Optional[bool]
    challenged_by: Optional[str]
    blocked_by: Optional[str]


class CoupAgentState(TypedDict, total=False):
    """
    Agent-local view of the game.

    Fields:
        me: agent identifier.
        coins: agent's current coins.
        hand: hidden influence cards (face down).
        revealed: influence cards the agent has lost (face up).
        players_alive: all players still in the game.
        public_events: ordered list of table events.
        pending_reaction: if the agent must respond to a block/challenge.
        rng_seed: optional deterministic seed for testing.

        agent_profile: playstyle and modulator knobs.

        Decision Routing (set by game server):
            decision_type: top-level routing (ACTION/REACT/RESOLVE).
            reaction_type: sub-type when decision_type=REACT.
            resolution_type: sub-type when decision_type=RESOLVE.

        Decision Outputs (set by agent):
            chosen_action: the action this agent proposed (for ACTION decisions).
            chosen_reaction: response action (CHALLENGE/BLOCK/PASS for REACT).
            chosen_reveal: which card to reveal (for RESOLVE.REVEAL_CARD).
            chosen_exchange: which cards to keep (for RESOLVE.EXCHANGE_CARDS).

        Guardrails:
            must_act: if True, agent must return an action (no pass).
            may_pass: if True, agent may explicitly choose PASS.
            forced_targets: optional list of allowed targets (e.g., mandatory coup target).
    """

    # Agent identity
    me: str
    coins: int
    hand: List[InfluenceCard]
    revealed: List[InfluenceCard]
    players_alive: List[str]
    public_events: List[PublicEvent]

    # Context for reactions (the event agent is responding to)
    pending_reaction: Optional[PublicEvent]

    # Utilities
    rng_seed: Optional[int]

    # Agent configuration
    agent_profile: AgentProfile

    # =============================================
    # Decision Routing (set by game server)
    # =============================================
    decision_type: DecisionType
    reaction_type: Optional[ReactionType]      # Set when decision_type=REACT
    resolution_type: Optional[ResolutionType]  # Set when decision_type=RESOLVE

    # =============================================
    # Decision Outputs (set by agent graph)
    # =============================================
    chosen_action: Optional[PublicEvent]            # For ACTION decisions
    chosen_reaction: Optional[CoupAction]           # For REACT (CHALLENGE, BLOCK, PASS)
    chosen_reveal: Optional[InfluenceCard]          # For RESOLVE.REVEAL_CARD
    chosen_exchange: Optional[List[InfluenceCard]]  # For RESOLVE.EXCHANGE_CARDS

    # =============================================
    # Guardrails (set by the game engine/referee)
    # =============================================
    must_act: Optional[bool]
    may_pass: Optional[bool]
    forced_targets: Optional[List[str]]

