"""
Agent Registry.

Manages multiple LLM agent instances across games.

Responsibilities:
- Create and register agent instances
- Route events to the correct agent
- Reset hourly counters for all agents
- Provide access to agents by game_id and agent_id
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional

from app.constants import GamePhase, InfluenceCard, SocialMediaPlatform
from app.models.graph_state_models.coup_agent_state import AgentProfile

if TYPE_CHECKING:
    from app.agents.base_coup_agent import BaseCoupAgent


class AgentRegistry:
    """
    Singleton registry for managing all Coup LLM agent instances.
    
    Structure: {game_id: {agent_id: BaseCoupAgent}}
    
    Usage:
        registry = AgentRegistry()
        agent = registry.register_agent("game_123", agent_config)
        agent = registry.get_agent("game_123", "jball")
    """
    
    _instance: Optional["AgentRegistry"] = None
    
    def __new__(cls) -> "AgentRegistry":
        """Singleton pattern - only one registry instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents: Dict[str, Dict[str, "BaseCoupAgent"]] = {}
            cls._instance._player_is_llm: Dict[str, Dict[str, bool]] = {}
        return cls._instance
    
    # =============================================
    # Agent Registration
    # =============================================
    
    def register_agent(
        self,
        game_id: str,
        agent_id: str,
        profile: Optional[AgentProfile] = None,
        initial_coins: int = 2,
        initial_hand: Optional[List[InfluenceCard]] = None,
        players_alive: Optional[List[str]] = None,
        agent_class: Optional[type] = None,
    ) -> "BaseCoupAgent":
        """
        Register a new agent for a game.
        
        Args:
            game_id: ID of the game
            agent_id: Unique identifier for this agent
            profile: Agent profile (from PostgreSQL)
            initial_coins: Starting coins
            initial_hand: Starting influence cards
            players_alive: All players in the game
            agent_class: Agent class to instantiate (allows custom subclasses)
            
        Returns:
            The created agent instance
        """
        # Lazy import to avoid circular dependency
        from app.agents.base_coup_agent import BaseCoupAgent
        
        if agent_class is None:
            agent_class = BaseCoupAgent
        
        # Initialize game dict if needed
        if game_id not in self._agents:
            self._agents[game_id] = {}
            self._player_is_llm[game_id] = {}
        
        # Check if agent already exists
        if agent_id in self._agents[game_id]:
            return self._agents[game_id][agent_id]
        
        # Create agent
        agent = agent_class(
            agent_id=agent_id,
            game_id=game_id,
            profile=profile,
            initial_coins=initial_coins,
            initial_hand=initial_hand,
            players_alive=players_alive,
        )
        
        # Register
        self._agents[game_id][agent_id] = agent
        self._player_is_llm[game_id][agent_id] = True
        
        return agent
    
    def unregister_agent(self, game_id: str, agent_id: str) -> bool:
        """
        Unregister an agent from a game.
        
        Returns:
            True if agent was found and removed
        """
        if game_id in self._agents and agent_id in self._agents[game_id]:
            del self._agents[game_id][agent_id]
            if agent_id in self._player_is_llm.get(game_id, {}):
                del self._player_is_llm[game_id][agent_id]
            return True
        return False
    
    def register_human_player(self, game_id: str, player_id: str) -> None:
        """
        Register a human player in a game (for LLM tracking purposes).
        
        This doesn't create an agent - just tracks that this player is human.
        """
        if game_id not in self._player_is_llm:
            self._player_is_llm[game_id] = {}
        self._player_is_llm[game_id][player_id] = False
    
    # =============================================
    # Agent Access
    # =============================================
    
    def get_agent(self, game_id: str, agent_id: str) -> Optional["BaseCoupAgent"]:
        """
        Get an agent by game and agent ID.
        
        Returns:
            Agent instance or None if not found
        """
        return self._agents.get(game_id, {}).get(agent_id)
    
    def get_all_agents_in_game(self, game_id: str) -> List["BaseCoupAgent"]:
        """Get all LLM agents in a game."""
        return list(self._agents.get(game_id, {}).values())
    
    def get_agent_ids_in_game(self, game_id: str) -> List[str]:
        """Get all LLM agent IDs in a game."""
        return list(self._agents.get(game_id, {}).keys())
    
    def get_all_games(self) -> List[str]:
        """Get all active game IDs."""
        return list(self._agents.keys())
    
    # =============================================
    # Player Type Tracking
    # =============================================
    
    def is_player_llm(self, game_id: str, player_id: str) -> bool:
        """Check if a player is an LLM agent."""
        return self._player_is_llm.get(game_id, {}).get(player_id, False)
    
    def get_player_is_llm_map(self, game_id: str) -> Dict[str, bool]:
        """Get the full player -> is_llm mapping for a game."""
        return self._player_is_llm.get(game_id, {}).copy()
    
    # =============================================
    # Hourly Reset
    # =============================================
    
    def reset_hourly_counters(self, game_id: str) -> int:
        """
        Reset all agents' hourly counters in a game.
        
        Called at the start of each hourly turn.
        
        Returns:
            Number of agents reset
        """
        agents = self.get_all_agents_in_game(game_id)
        for agent in agents:
            agent.reset_for_new_hour()
        return len(agents)
    
    def lock_all_actions(self, game_id: str) -> int:
        """
        Lock actions for all agents in a game.
        
        Called at Lockout 1 (10 min before Phase 2).
        
        Returns:
            Number of agents locked
        """
        agents = self.get_all_agents_in_game(game_id)
        for agent in agents:
            agent.lock_action()
        return len(agents)
    
    def lock_all_reactions(self, game_id: str) -> int:
        """
        Lock reactions for all agents in a game.
        
        Called at Lockout 2 (10 min before Broadcast).
        
        Returns:
            Number of agents locked
        """
        agents = self.get_all_agents_in_game(game_id)
        for agent in agents:
            agent.lock_reactions()
        return len(agents)
    
    # =============================================
    # Phase Transitions
    # =============================================
    
    def transition_phase(self, game_id: str, new_phase: GamePhase) -> int:
        """
        Transition all agents to a new game phase.
        
        Each agent's set_phase() handles phase-specific state updates:
        - LOCKOUT1: Locks actions
        - PHASE2_REACTIONS: Unlocks reactions, clears old reactions
        - LOCKOUT2: Locks reactions
        - PHASE1_ACTIONS: Full reset for new hour
        
        Args:
            game_id: The game to transition
            new_phase: The new phase to enter
            
        Returns:
            Number of agents transitioned
        """
        agents = self.get_all_agents_in_game(game_id)
        for agent in agents:
            agent.set_phase(new_phase)
        return len(agents)
    
    def get_phase(self, game_id: str) -> Optional[GamePhase]:
        """
        Get the current phase for a game (from first agent).
        
        All agents in a game should be in the same phase.
        
        Returns:
            Current GamePhase or None if no agents
        """
        agents = self.get_all_agents_in_game(game_id)
        if agents:
            return agents[0].get_phase()
        return None
    
    def set_actions_requiring_reaction(
        self,
        game_id: str,
        actions_by_agent: Dict[str, List[Dict]]
    ) -> int:
        """
        Set actions requiring reaction for each agent at Phase 2 start.
        
        Args:
            game_id: The game ID
            actions_by_agent: {agent_id: [list of actions requiring their reaction]}
            
        Returns:
            Number of agents updated
        """
        count = 0
        for agent_id, actions in actions_by_agent.items():
            agent = self.get_agent(game_id, agent_id)
            if agent:
                agent.set_actions_requiring_reaction(actions)
                count += 1
        return count
    
    def update_minutes_remaining(self, game_id: str, minutes: int) -> None:
        """
        Update time remaining for all agents in a game.
        
        Args:
            game_id: Game ID
            minutes: Minutes remaining in the hour
        """
        for agent in self.get_all_agents_in_game(game_id):
            agent.update_minutes_remaining(minutes)
    
    # =============================================
    # Profile Sync
    # =============================================
    
    def sync_agent_profile(
        self, 
        game_id: str, 
        agent_id: str, 
        profile: AgentProfile
    ) -> bool:
        """
        Sync an agent's profile from PostgreSQL.
        
        Returns:
            True if agent was found and updated
        """
        agent = self.get_agent(game_id, agent_id)
        if agent:
            agent.update_profile(profile)
            return True
        return False
    
    # =============================================
    # Game Cleanup
    # =============================================
    
    def cleanup_game(self, game_id: str) -> int:
        """
        Remove all agents for a finished game.
        
        Returns:
            Number of agents removed
        """
        if game_id not in self._agents:
            return 0
        
        count = len(self._agents[game_id])
        del self._agents[game_id]
        
        if game_id in self._player_is_llm:
            del self._player_is_llm[game_id]
        
        return count
    
    # =============================================
    # Stats & Debug
    # =============================================
    
    def get_stats(self) -> dict:
        """Get registry statistics including phase info."""
        return {
            "total_games": len(self._agents),
            "total_agents": sum(len(agents) for agents in self._agents.values()),
            "games": {
                game_id: {
                    "agent_count": len(agents),
                    "agent_ids": list(agents.keys()),
                    "current_phase": self.get_phase(game_id).value if self.get_phase(game_id) else None,
                    "agents_alive": sum(1 for a in agents.values() if a.is_alive()),
                }
                for game_id, agents in self._agents.items()
            },
        }


# Global instance is declared in app/extensions.py
# Access via: from app.extensions import agent_registry
