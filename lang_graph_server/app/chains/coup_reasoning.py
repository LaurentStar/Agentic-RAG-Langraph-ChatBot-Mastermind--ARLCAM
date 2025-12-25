"""
LLM chains for Coup agent strategic reasoning.

These chains provide LLM-based decision making that can be blended
with heuristics based on agent modulators.
"""

from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain_openai import ChatOpenAI

from app.extensions import LoadedPromptTemplates
from app.models.structured_output_models.coup_decision_so import (
    ActionDecisionSO,
    ExchangeDecisionSO,
    ReactionDecisionSO,
    RevealDecisionSO,
)


class CoupReasoningChains:
    """
    LLM chains for strategic Coup decisions.

    Each chain takes game context and returns a structured decision.
    """

    @staticmethod
    def _get_llm(temperature: float = 0.3) -> ChatOpenAI:
        """Get LLM instance. Using slightly higher temperature for creative bluffing."""
        return ChatOpenAI(model="gpt-4o", temperature=temperature, verbose=True)

    @staticmethod
    def action_selection_chain() -> RunnableSequence:
        """
        Chain for SELECT_ACTION decisions.

        Input variables:
            - me: agent name
            - coins: current coins
            - hand: cards in hand
            - players_alive: active players
            - public_events: game history
            - agent_personality: personality description
            - agent_play_style: play style description
            - legal_actions: list of currently legal actions
        """
        prompt_template = LoadedPromptTemplates.markdown_prompt_templates.get(
            'coup_action_selection.md',
            _DEFAULT_ACTION_PROMPT
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_template)
        ])
        llm = CoupReasoningChains._get_llm(temperature=0.4)
        structured_llm = llm.with_structured_output(ActionDecisionSO)
        return prompt | structured_llm

    @staticmethod
    def reaction_decision_chain() -> RunnableSequence:
        """
        Chain for REACT decisions (challenge/block/pass).

        Input variables:
            - me: agent name
            - hand: cards in hand
            - pending_event: the action/block being responded to
            - actor: who took the action
            - claimed_role: what role they're claiming
            - agent_personality: personality description
            - reaction_options: available reactions
        """
        prompt_template = LoadedPromptTemplates.markdown_prompt_templates.get(
            'coup_reaction_decision.md',
            _DEFAULT_REACTION_PROMPT
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_template)
        ])
        llm = CoupReasoningChains._get_llm(temperature=0.3)
        structured_llm = llm.with_structured_output(ReactionDecisionSO)
        return prompt | structured_llm

    @staticmethod
    def bluff_reasoning_chain() -> RunnableSequence:
        """
        Chain specifically for bluff-heavy decisions.

        Used when the agent is considering a risky bluff or detecting opponent bluffs.

        Input variables:
            - me: agent name
            - hand: cards in hand (what we actually have)
            - target_role: role we're considering claiming
            - opponent_history: relevant actions by opponent
            - agent_bluff_confidence: how confident we are in bluffing
        """
        prompt_template = LoadedPromptTemplates.markdown_prompt_templates.get(
            'coup_bluff_reasoning.md',
            _DEFAULT_BLUFF_PROMPT
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_template)
        ])
        llm = CoupReasoningChains._get_llm(temperature=0.5)  # Higher temp for creative bluffs
        structured_llm = llm.with_structured_output(ActionDecisionSO)
        return prompt | structured_llm

    @staticmethod
    def reveal_selection_chain() -> RunnableSequence:
        """
        Chain for RESOLVE.REVEAL_CARD decisions.

        Input variables:
            - me: agent name
            - hand: cards to choose from
            - game_context: why we're revealing (challenge loss, assassination, coup)
            - remaining_players: who's still alive
        """
        prompt_template = LoadedPromptTemplates.markdown_prompt_templates.get(
            'coup_reveal_selection.md',
            _DEFAULT_REVEAL_PROMPT
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_template)
        ])
        llm = CoupReasoningChains._get_llm(temperature=0.1)  # Low temp - straightforward decision
        structured_llm = llm.with_structured_output(RevealDecisionSO)
        return prompt | structured_llm

    @staticmethod
    def exchange_selection_chain() -> RunnableSequence:
        """
        Chain for RESOLVE.EXCHANGE_CARDS decisions.

        Input variables:
            - me: agent name
            - available_cards: hand + 2 drawn cards
            - num_to_keep: how many to keep (1 or 2)
            - game_context: current game state for strategic selection
        """
        prompt_template = LoadedPromptTemplates.markdown_prompt_templates.get(
            'coup_exchange_selection.md',
            _DEFAULT_EXCHANGE_PROMPT
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_template)
        ])
        llm = CoupReasoningChains._get_llm(temperature=0.2)
        structured_llm = llm.with_structured_output(ExchangeDecisionSO)
        return prompt | structured_llm

    # =============================================
    # Class-level chain instances (lazy loaded)
    # =============================================
    _action_chain: Optional[RunnableSequence] = None
    _reaction_chain: Optional[RunnableSequence] = None
    _bluff_chain: Optional[RunnableSequence] = None
    _reveal_chain: Optional[RunnableSequence] = None
    _exchange_chain: Optional[RunnableSequence] = None

    @classmethod
    def get_action_chain(cls) -> RunnableSequence:
        if cls._action_chain is None:
            cls._action_chain = cls.action_selection_chain()
        return cls._action_chain

    @classmethod
    def get_reaction_chain(cls) -> RunnableSequence:
        if cls._reaction_chain is None:
            cls._reaction_chain = cls.reaction_decision_chain()
        return cls._reaction_chain

    @classmethod
    def get_bluff_chain(cls) -> RunnableSequence:
        if cls._bluff_chain is None:
            cls._bluff_chain = cls.bluff_reasoning_chain()
        return cls._bluff_chain

    @classmethod
    def get_reveal_chain(cls) -> RunnableSequence:
        if cls._reveal_chain is None:
            cls._reveal_chain = cls.reveal_selection_chain()
        return cls._reveal_chain

    @classmethod
    def get_exchange_chain(cls) -> RunnableSequence:
        if cls._exchange_chain is None:
            cls._exchange_chain = cls.exchange_selection_chain()
        return cls._exchange_chain


# =============================================
# Default Prompts (fallback if files not loaded)
# =============================================

_DEFAULT_ACTION_PROMPT = """You are an AI playing the card game Coup. It is your turn to take an action.

Player: {me}
Your coins: {coins}
Your hand (SECRET - only you know): {hand}
Players still alive: {players_alive}

Recent game events:
{public_events}

Your personality: {agent_personality}
Your play style: {agent_play_style}

Legal actions you can take:
{legal_actions}

Choose the best action based on your hand, the game state, and your personality.
Consider:
- Do you have the card for the action, or are you bluffing?
- What is the risk of being challenged?
- What will advance your position in the game?

Respond with your chosen action, target (if needed), and brief reasoning."""

_DEFAULT_REACTION_PROMPT = """You are an AI playing Coup. Another player has taken an action and you must decide how to respond.

Player: {me}
Your hand (SECRET): {hand}

The action being taken:
Actor: {actor}
Action: {pending_event}
Claimed role: {claimed_role}

Your personality: {agent_personality}

Your options:
{reaction_options}

Consider:
- Do you hold a card that would let them be bluffing?
- What is the risk if you challenge and are wrong?
- Would blocking be better than challenging?

Respond with your reaction choice and reasoning."""

_DEFAULT_BLUFF_PROMPT = """You are an AI playing Coup, considering a bluff.

Player: {me}
Your actual hand: {hand}
Role you're considering claiming: {target_role}

Opponent history (relevant actions):
{opponent_history}

Your bluff confidence level: {agent_bluff_confidence}

Analyze:
1. How likely are opponents to challenge this bluff?
2. What evidence suggests they might have the card you're claiming?
3. Is the reward worth the risk?

Make a decision about whether to bluff and explain your reasoning."""

_DEFAULT_REVEAL_PROMPT = """You must reveal (lose) one of your influence cards.

Player: {me}
Your hand: {hand}
Why you're revealing: {game_context}
Remaining players: {remaining_players}

Choose which card to reveal. Consider:
- Which card is most valuable for your remaining strategy?
- What cards might help you in the endgame?

Select the card you're willing to lose."""

_DEFAULT_EXCHANGE_PROMPT = """You used the Ambassador ability and must choose which cards to keep.

Player: {me}
Available cards (your hand + 2 drawn): {available_cards}
Number to keep: {num_to_keep}

Current game state: {game_context}

Choose the best cards to keep for your strategy. Consider:
- What roles will be most useful?
- What bluffs might you want to make?
- What defensive options do you need?

Select the cards to keep."""

