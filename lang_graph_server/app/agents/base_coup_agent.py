"""
Base Coup Agent.

Shared functionality for all Coup LLM agents in the hourly game.

Each agent:
- Has a unique identity (agent_id)
- Belongs to a game (game_id)
- Has a profile loaded from PostgreSQL (personality, modulators)
- Maintains isolated state (message counters, pending action, etc.)
"""

from datetime import datetime
from typing import Dict, List, Optional

from app.constants import (
    AgentModulator,
    CoupAction,
    GamePhase,
    InfluenceCard,
    MessageTargetType,
    SocialMediaPlatform,
    UpgradeType,
)
from app.models.graph_state_models.coup_agent_state import AgentProfile
from app.models.graph_state_models.hourly_coup_state import (
    HourlyCoupAgentState,
    UpgradeDecision,
    VisiblePendingAction,
    create_initial_hourly_state,
    reset_hourly_counters,
)
from app.models.graph_state_models.game_phase_state import (
    PendingReaction,
    PendingCardSelection,
    VisiblePendingReaction,
)
from app.services.message_counter_service import MessageCounterService
from app.services.upgrade_decision_service import UpgradeDecisionService


class BaseCoupAgent:
    """
    Base class for all Coup LLM agents.
    
    Provides shared functionality:
    - State management
    - Message limit tracking
    - Pending action management
    - Profile/modulator access
    
    Concrete agents can extend this with specialized behavior.
    """
    
    # Default modulators - can be overridden by subclasses or DB config
    default_modulators: Dict[AgentModulator, float] = {
        AgentModulator.AGGRESSION: 0.5,
        AgentModulator.BLUFF_CONFIDENCE: 0.3,
        AgentModulator.CHALLENGE_TENDENCY: 0.3,
        AgentModulator.BLOCK_TENDENCY: 0.5,
        AgentModulator.RISK_TOLERANCE: 0.5,
    }
    
    def __init__(
        self,
        agent_id: str,
        game_id: str,
        profile: Optional[AgentProfile] = None,
        initial_coins: int = 2,
        initial_hand: Optional[List[InfluenceCard]] = None,
        players_alive: Optional[List[str]] = None,
    ):
        """
        Initialize a Coup agent.
        
        Args:
            agent_id: Unique identifier for this agent (e.g., "jball", "agent_2")
            game_id: ID of the game this agent is playing in
            profile: Agent profile from PostgreSQL (personality, modulators)
            initial_coins: Starting coins (default 2)
            initial_hand: Starting influence cards
            players_alive: List of all players in the game
        """
        self.agent_id = agent_id
        self.game_id = game_id
        
        # Game server client for HTTP API calls
        self._game_server_client = None
        
        # Profile - can be loaded/synced from PostgreSQL
        self.profile: AgentProfile = profile or AgentProfile(
            agent_name=agent_id,
            agent_play_style="balanced",
            agent_personality="neutral",
            agent_modulators=self.default_modulators.copy(),
        )
        
        # Initialize state
        self.state: HourlyCoupAgentState = create_initial_hourly_state(
            agent_id=agent_id,
            game_id=game_id,
            coins=initial_coins,
            hand=initial_hand,
            players_alive=players_alive,
        )
        
        # Set profile in state
        self.state["agent_profile"] = self.profile
    
    # =============================================
    # Profile & Modulator Access
    # =============================================
    
    @property
    def name(self) -> str:
        """Get agent display name."""
        return self.profile.get("agent_name", self.agent_id)
    
    @property
    def play_style(self) -> str:
        """Get agent play style description."""
        return self.profile.get("agent_play_style", "balanced")
    
    @property
    def personality(self) -> str:
        """Get agent personality for chat responses."""
        return self.profile.get("agent_personality", "neutral")
    
    def get_modulator(self, modulator: AgentModulator) -> float:
        """Get a specific modulator value (0.0 to 1.0)."""
        modulators = self.profile.get("agent_modulators", {})
        return modulators.get(modulator, self.default_modulators.get(modulator, 0.5))
    
    def update_profile(self, profile: AgentProfile) -> None:
        """
        Update agent profile (typically from PostgreSQL sync).
        
        Args:
            profile: New profile data
        """
        self.profile = profile
        self.state["agent_profile"] = profile
    
    # =============================================
    # Message Tracking
    # =============================================
    
    def can_send_message(self, target_type: MessageTargetType) -> bool:
        """Check if agent can send a message to the given target type."""
        return MessageCounterService.can_send_message(self.state, target_type)
    
    def increment_message_count(self, target_type: MessageTargetType) -> bool:
        """
        Increment message counter for a target type.
        
        Returns:
            True if successful, False if limit reached
        """
        self.state, success = MessageCounterService.increment_count(self.state, target_type)
        return success
    
    def get_message_stats(self) -> dict:
        """Get all message counts, limits, and remaining."""
        return MessageCounterService.get_all_counts(self.state)
    
    # =============================================
    # Pending Action Management
    # =============================================
    
    def get_pending_action(self) -> Optional[Dict]:
        """Get current pending action for this hour."""
        return self.state.get("pending_action")
    
    def get_pending_upgrade(self) -> Optional[UpgradeDecision]:
        """Get upgrade decision for pending action."""
        return self.state.get("pending_upgrade")
    
    def is_action_locked(self) -> bool:
        """Check if actions are locked (final 10 minutes of hour)."""
        return self.state.get("action_locked", False)
    
    def update_pending_action(
        self,
        action: CoupAction,
        target: Optional[str] = None,
        upgrade: bool = False,
        upgrade_type: Optional[UpgradeType] = None,
    ) -> bool:
        """
        Update the agent's pending action for this hour.
        
        Args:
            action: The action to take
            target: Target player (for targeted actions)
            upgrade: Whether to upgrade the action
            upgrade_type: Type of upgrade (if upgrading)
            
        Returns:
            True if successful, False if locked
        """
        if self.is_action_locked():
            return False
        
        # Build pending action
        self.state["pending_action"] = {
            "actor": self.agent_id,
            "action": action,
            "target": target,
            "succeeded": None,
            "challenged_by": None,
            "blocked_by": None,
        }
        
        # Build upgrade decision if applicable
        if upgrade and upgrade_type:
            self.state["pending_upgrade"] = UpgradeDecision(
                action=action,
                upgrade=True,
                upgrade_type=upgrade_type,
                total_cost=self._calculate_upgrade_cost(action, upgrade_type),
            )
        else:
            self.state["pending_upgrade"] = None
        
        return True
    
    def _calculate_upgrade_cost(self, action: CoupAction, upgrade_type: UpgradeType) -> int:
        """Calculate total cost for an upgraded action."""
        return UpgradeDecisionService.get_total_cost(action, upgraded=True)
    
    def lock_action(self) -> None:
        """Lock actions (called at 10-minute mark)."""
        self.state["action_locked"] = True
    
    def unlock_action(self) -> None:
        """Unlock actions (called at hour start)."""
        self.state["action_locked"] = False
    
    # =============================================
    # Visible Pending Actions (from other players)
    # =============================================
    
    def get_visible_pending_actions(self) -> List[VisiblePendingAction]:
        """Get pending actions visible to this agent."""
        return self.state.get("visible_pending_actions", [])
    
    def update_visible_pending_actions(self, actions: List[VisiblePendingAction]) -> None:
        """
        Update visible pending actions (from PostgreSQL query).
        
        Note: This should be called periodically to sync with DB.
        """
        self.state["visible_pending_actions"] = actions
    
    # =============================================
    # Phase Management (Two-Phase Hourly Coup)
    # =============================================
    
    def get_phase(self) -> GamePhase:
        """Get the current game phase."""
        return self.state.get("current_phase", GamePhase.PHASE1_ACTIONS)
    
    def set_phase(self, phase: GamePhase) -> None:
        """
        Set the current game phase.
        
        Automatically handles phase-specific state updates:
        - LOCKOUT1: Locks actions
        - PHASE2_REACTIONS: Unlocks reactions
        - LOCKOUT2: Locks reactions
        - PHASE1_ACTIONS: Resets for new hour
        """
        previous_phase = self.get_phase()
        self.state["current_phase"] = phase
        
        # Phase-specific state updates
        if phase == GamePhase.LOCKOUT1:
            self.lock_action()
        elif phase == GamePhase.PHASE2_REACTIONS:
            self.unlock_reactions()
        elif phase == GamePhase.LOCKOUT2:
            self.lock_reactions()
        elif phase == GamePhase.PHASE1_ACTIONS and previous_phase == GamePhase.BROADCAST:
            self.reset_for_new_hour()
    
    def is_in_action_phase(self) -> bool:
        """Check if we're in Phase 1 (action selection)."""
        return self.get_phase() == GamePhase.PHASE1_ACTIONS
    
    def is_in_reaction_phase(self) -> bool:
        """Check if we're in Phase 2 (reaction selection)."""
        return self.get_phase() == GamePhase.PHASE2_REACTIONS
    
    def is_in_lockout(self) -> bool:
        """Check if we're in a lockout period (no changes allowed)."""
        phase = self.get_phase()
        return phase in (GamePhase.LOCKOUT1, GamePhase.LOCKOUT2, GamePhase.BROADCAST)
    
    # =============================================
    # Phase 2: Pending Reactions
    # =============================================
    
    def get_pending_reactions(self) -> List[PendingReaction]:
        """Get all pending reactions for Phase 2."""
        return self.state.get("pending_reactions", [])
    
    def add_pending_reaction(self, reaction: PendingReaction) -> bool:
        """
        Add a pending reaction for Phase 2.
        
        Returns:
            True if successful, False if reactions are locked
        """
        if self.are_reactions_locked():
            return False
        
        reactions = self.state.get("pending_reactions", [])
        reactions.append(reaction)
        self.state["pending_reactions"] = reactions
        return True
    
    def update_pending_reactions(self, reactions: List[PendingReaction]) -> bool:
        """
        Replace all pending reactions.
        
        Returns:
            True if successful, False if reactions are locked
        """
        if self.are_reactions_locked():
            return False
        
        self.state["pending_reactions"] = reactions
        return True
    
    def clear_pending_reactions(self) -> None:
        """Clear all pending reactions."""
        self.state["pending_reactions"] = []
    
    def are_reactions_locked(self) -> bool:
        """Check if reactions are locked (Lockout 2)."""
        return self.state.get("reactions_locked", False)
    
    def lock_reactions(self) -> None:
        """Lock reactions (called at Lockout 2 start)."""
        self.state["reactions_locked"] = True
    
    def unlock_reactions(self) -> None:
        """Unlock reactions (called at Phase 2 start)."""
        self.state["reactions_locked"] = False
    
    # =============================================
    # Phase 2: Actions Requiring Reaction
    # =============================================
    
    def get_actions_requiring_reaction(self) -> List[Dict]:
        """Get actions from Phase 1 that need this agent's reaction."""
        return self.state.get("actions_requiring_my_reaction", [])
    
    def set_actions_requiring_reaction(self, actions: List[Dict]) -> None:
        """Set actions requiring reaction (sent by game server at Phase 2 start)."""
        self.state["actions_requiring_my_reaction"] = actions
    
    # =============================================
    # Phase 2: Visible Pending Reactions
    # =============================================
    
    def get_visible_pending_reactions(self) -> List[VisiblePendingReaction]:
        """Get pending reactions visible from other players."""
        return self.state.get("visible_pending_reactions", [])
    
    def update_visible_pending_reactions(self, reactions: List[VisiblePendingReaction]) -> None:
        """Update visible pending reactions (from game server)."""
        self.state["visible_pending_reactions"] = reactions
    
    # =============================================
    # Phase 2: Card Selection (Ambassador/Reveal)
    # =============================================
    
    def get_pending_card_selection(self) -> Optional[PendingCardSelection]:
        """Get pending card selection (Ambassador exchange or reveal)."""
        return self.state.get("pending_card_selection")
    
    def set_pending_card_selection(self, selection: PendingCardSelection) -> None:
        """Set pending card selection."""
        self.state["pending_card_selection"] = selection
    
    def clear_pending_card_selection(self) -> None:
        """Clear pending card selection."""
        self.state["pending_card_selection"] = None
    
    def finalize_card_selection(self, selected_cards: List[InfluenceCard]) -> bool:
        """
        Finalize the card selection.
        
        Returns:
            True if successful, False if no pending selection or locked
        """
        selection = self.get_pending_card_selection()
        if not selection or self.are_reactions_locked():
            return False
        
        selection["selected_cards"] = selected_cards
        selection["is_finalized"] = True
        self.state["pending_card_selection"] = selection
        return True
    
    # =============================================
    # Hour/Turn Management
    # =============================================
    
    def reset_for_new_hour(self) -> None:
        """Reset state for a new hourly turn."""
        self.state = reset_hourly_counters(self.state)
    
    def update_minutes_remaining(self, minutes: int) -> None:
        """Update time remaining in current hour."""
        self.state["minutes_remaining"] = minutes
        
        # Auto-lock at 10 minute mark
        if minutes <= 10:
            self.lock_action()
    
    # =============================================
    # Platform Context
    # =============================================
    
    def set_current_platform(self, platform: SocialMediaPlatform) -> None:
        """Set the platform of the current event being processed."""
        self.state["current_event_platform"] = platform
    
    def update_player_platforms(self, platforms: Dict[str, SocialMediaPlatform]) -> None:
        """Update the mapping of players to their platforms."""
        self.state["player_platforms"] = platforms
    
    # =============================================
    # State Access
    # =============================================
    
    def get_state(self) -> HourlyCoupAgentState:
        """Get the full agent state."""
        return self.state
    
    def get_coins(self) -> int:
        """Get current coin count."""
        return self.state.get("coins", 0)
    
    def get_hand(self) -> List[InfluenceCard]:
        """Get current hand (face-down cards)."""
        return self.state.get("hand", [])
    
    def get_revealed(self) -> List[InfluenceCard]:
        """Get revealed cards (lost influence)."""
        return self.state.get("revealed", [])
    
    def is_alive(self) -> bool:
        """Check if agent is still in the game (has at least 1 unrevealed card)."""
        return len(self.get_hand()) > 0
    
    # =============================================
    # Checkpointer Thread Access
    # =============================================
    
    def get_thread_id(self) -> str:
        """
        Get this agent's LangGraph checkpointer thread ID.
        
        Thread ID is used to store/retrieve conversation history
        from the PostgreSQL-backed checkpointer.
        
        Format: "{game_id}:{agent_id}"
        
        Returns:
            Thread ID string for this agent
        """
        return f"{self.game_id}:{self.agent_id}"
    
    def get_conversation_history(self) -> List[Dict]:
        """
        Get this agent's conversation history from the checkpointer.
        
        Returns:
            List of conversation messages, or empty list if not available
        """
        from app.extensions import lang_graph_app
        
        try:
            return lang_graph_app.event_router_wf.get_conversation_history(
                self.get_thread_id()
            )
        except Exception:
            return []
    
    # =============================================
    # Game Server Integration
    # =============================================
    
    def configure_game_server_client(self, password: str) -> None:
        """
        Configure the game server client for this agent.
        
        Uses the factory from extensions.py which is initialized in __init__.py.
        
        Args:
            password: Agent's password for authentication
        """
        from app.extensions import game_server_client_factory
        
        self._game_server_client = game_server_client_factory.create_client(
            agent_id=self.agent_id,
            password=password
        )
    
    def get_game_server_client(self):
        """
        Get the configured game server client.
        
        Returns:
            GameServerClient for this agent, or None if not configured
        """
        if self._game_server_client is None:
            # Try to get from factory cache
            from app.extensions import game_server_client_factory
            self._game_server_client = game_server_client_factory.get_client(self.agent_id)
        
        return self._game_server_client
    
    def submit_action_to_server(
        self,
        session_id: str,
        action: CoupAction,
        target: Optional[str] = None,
        claimed_role: Optional[str] = None,
        upgrade: bool = False
    ) -> dict:
        """
        Submit pending action to the game server.
        
        This sends the action via HTTP to the game server API.
        
        Args:
            session_id: Game session ID
            action: Action to take
            target: Target player (for targeted actions)
            claimed_role: Role claimed for action
            upgrade: Whether to use upgrade
        
        Returns:
            Response from game server
        """
        client = self.get_game_server_client()
        
        result = client.set_action(
            session_id=session_id,
            action=action,
            target_display_name=target,
            claimed_role=claimed_role,
            upgrade_enabled=upgrade
        )
        
        # Update local state if successful
        if "error" not in result:
            self.update_pending_action(action, target, upgrade)
        
        return result
    
    def submit_reaction_to_server(
        self,
        session_id: str,
        target_player: str,
        reaction_type: str,
        block_with_role: Optional[str] = None
    ) -> dict:
        """
        Submit reaction to the game server.
        
        Args:
            session_id: Game session ID
            target_player: Player whose action to react to
            reaction_type: 'challenge', 'block', or 'pass'
            block_with_role: Role claimed for blocking
        
        Returns:
            Response from game server
        """
        from app.constants import ReactionType
        
        client = self.get_game_server_client()
        
        try:
            rt = ReactionType(reaction_type)
        except ValueError:
            return {"error": f"Invalid reaction type: {reaction_type}"}
        
        return client.set_reaction(
            session_id=session_id,
            target_player=target_player,
            reaction_type=rt,
            block_with_role=block_with_role
        )
    
    def fetch_game_state_from_server(self, session_id: str) -> dict:
        """
        Fetch current game state from the game server.
        
        Returns:
            Game state including players, coins, phase, etc.
        """
        client = self.get_game_server_client()
        return client.get_game_state(session_id)
    
    def fetch_pending_actions_from_server(self, session_id: str) -> dict:
        """
        Fetch visible pending actions from the game server.
        
        Returns:
            Dict with pending_actions, current_phase, phase_end_time
        """
        client = self.get_game_server_client()
        return client.get_pending_actions(session_id)
    
    def fetch_reactions_from_server(self, session_id: str) -> dict:
        """
        Fetch pending reactions from the game server.
        
        Returns:
            Dict with pending_reactions and actions_requiring_reaction
        """
        client = self.get_game_server_client()
        return client.get_pending_reactions(session_id)

