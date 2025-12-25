"""
Broadcast Commentary State Model.

State for the broadcast commentary workflow that generates optional
agent reactions to end-of-hour game results.

Triggers for commentary:
- Agent was eliminated
- Agent's action succeeded/failed
- Agent successfully bluffed or was caught bluffing
- Dramatic game state (final 2 players, big swing)
- Another player's interesting fate

Commentary should be in-character and respect message limits.
"""

from typing import Dict, List, Optional, TypedDict

from app.constants import (
    CoupAction,
    InfluenceCard,
    MessageTargetType,
    SocialMediaPlatform,
)


class GameResult(TypedDict, total=False):
    """A single game result from the broadcast."""
    
    actor: str              # Who took the action
    action: str             # What action (assassinate, steal, etc.)
    target: Optional[str]   # Target of action
    succeeded: bool         # Did action succeed
    blocked_by: Optional[str]   # Who blocked (if blocked)
    challenged_by: Optional[str]  # Who challenged (if challenged)
    challenge_succeeded: bool     # Did challenge succeed
    
    # Elimination info
    eliminated_player: Optional[str]  # Who got eliminated
    eliminated_card: Optional[str]    # What card they lost
    
    # Special outcomes
    bluff_caught: bool      # Was a bluff caught
    bluff_succeeded: bool   # Did a bluff work


class ResultAnalysis(TypedDict, total=False):
    """Analysis of how results affect the agent."""
    
    # Impact on this agent
    agent_was_actor: bool       # Agent took an action
    agent_was_target: bool      # Agent was targeted
    agent_was_eliminated: bool  # Agent lost
    agent_action_succeeded: bool  # Agent's action worked
    agent_bluff_caught: bool    # Agent's bluff was caught
    agent_bluff_succeeded: bool # Agent's bluff worked
    
    # Dramatic events
    is_dramatic: bool           # Something notable happened
    drama_reason: str           # Why it's dramatic
    drama_score: float          # 0.0 to 1.0 - how dramatic
    
    # Affected relationships
    players_to_mention: List[str]  # Players worth commenting on
    
    # Commentary opportunity
    has_commentary_opportunity: bool  # Should agent comment
    commentary_type: str  # "victory", "defeat", "taunt", "sympathy", "observation", "none"


class CommentaryDecision(TypedDict, total=False):
    """Decision about whether and how to comment."""
    
    should_comment: bool
    priority: str  # "high", "medium", "low", "none"
    reason: str    # Why commenting or not
    
    # If should_comment is True
    commentary_angle: str  # "celebrate", "mourn", "taunt", "analyze", "deflect"
    target_audience: str   # "everyone", "specific_player", "self_reflection"
    emotional_tone: str    # "triumphant", "bitter", "amused", "shocked", "indifferent"


class GeneratedCommentary(TypedDict, total=False):
    """Generated commentary response."""
    
    content: str
    tone: str           # "smug", "gracious", "bitter", "playful", "analytical"
    mentions: List[str] # Players mentioned in commentary
    
    # Strategy
    strategic_intent: str  # "intimidate", "build_alliance", "misdirect", "neutral"
    reveals_info: bool     # Does this reveal strategic info
    
    # Metadata
    confidence: float      # How confident agent is


class BroadcastCommentaryState(TypedDict, total=False):
    """
    State for the broadcast commentary workflow.
    
    Tracks game results and generates appropriate agent commentary.
    """
    
    # =============================================
    # Agent Identity & Context
    # =============================================
    agent_id: str
    game_id: str
    agent_name: str
    agent_personality: str
    agent_play_style: str
    
    # =============================================
    # Broadcast Results
    # =============================================
    results: List[GameResult]
    result_count: int
    
    # Game state after resolution
    players_remaining: List[str]
    is_game_over: bool
    winner: Optional[str]
    
    # =============================================
    # Agent's Game State (post-resolution)
    # =============================================
    coins: int
    hand: List[InfluenceCard]
    revealed: List[InfluenceCard]
    is_alive: bool
    was_eliminated_this_round: bool
    
    # =============================================
    # Message Limits
    # =============================================
    can_comment: bool
    messages_remaining: int
    
    # =============================================
    # Workflow Outputs (filled by nodes)
    # =============================================
    
    # Analysis node output
    result_analysis: Optional[ResultAnalysis]
    
    # Decision node output
    commentary_decision: Optional[CommentaryDecision]
    
    # Generation node output
    generated_commentary: Optional[GeneratedCommentary]
    
    # =============================================
    # Final Output
    # =============================================
    final_commentary: Optional[str]  # The actual commentary to send (or None)
    response_platform: SocialMediaPlatform


def create_broadcast_commentary_state(
    agent,  # BaseCoupAgent
    results: List[Dict],
    players_remaining: List[str],
    is_game_over: bool = False,
    winner: Optional[str] = None,
) -> BroadcastCommentaryState:
    """
    Create a broadcast commentary state from agent and game results.
    
    Args:
        agent: The BaseCoupAgent processing this broadcast
        results: List of game results from the broadcast
        players_remaining: Players still alive after resolution
        is_game_over: Whether the game has ended
        winner: Winner if game is over
        
    Returns:
        Initialized BroadcastCommentaryState
    """
    from app.services.message_counter_service import MessageCounterService
    
    # Check if agent can send a mixed message (commentary goes to all)
    can_comment = agent.can_send_message(MessageTargetType.MIXED)
    messages_remaining = MessageCounterService.get_remaining(
        agent.state, MessageTargetType.MIXED
    )
    
    # Check if agent was eliminated this round
    was_eliminated = False
    for result in results:
        if result.get("eliminated_player") == agent.agent_id:
            was_eliminated = True
            break
    
    return BroadcastCommentaryState(
        # Identity
        agent_id=agent.agent_id,
        game_id=agent.game_id,
        agent_name=agent.name,
        agent_personality=agent.personality,
        agent_play_style=agent.play_style,
        
        # Results
        results=[GameResult(**r) for r in results],
        result_count=len(results),
        players_remaining=players_remaining,
        is_game_over=is_game_over,
        winner=winner,
        
        # Agent state
        coins=agent.get_coins(),
        hand=agent.get_hand(),
        revealed=agent.get_revealed(),
        is_alive=agent.is_alive(),
        was_eliminated_this_round=was_eliminated,
        
        # Limits
        can_comment=can_comment,
        messages_remaining=messages_remaining,
        
        # Outputs (to be filled)
        result_analysis=None,
        commentary_decision=None,
        generated_commentary=None,
        final_commentary=None,
        response_platform=SocialMediaPlatform.DEFUALT,
    )

