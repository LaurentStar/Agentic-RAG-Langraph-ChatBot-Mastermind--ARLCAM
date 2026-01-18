"""
Session Service.

Handles game session creation, player joining, and session management.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.constants import (
    CardType,
    GamePhase,
    GamePrivilege,
    PlayerStatus,
    SessionStatus,
    SocialMediaPlatform,
    PHASE_ORDER,
)
from app.extensions import db
from app.models.postgres_sql_db_models import BroadcastDestination, GameSession, Player

logger = logging.getLogger(__name__)


class SessionService:
    """Service for game session management."""
    
    @staticmethod
    def create_session(
        session_name: str,
        max_players: int = 6,
        turn_limit: int = 10,
        upgrades_enabled: bool = True,
        # Phase durations in minutes (numbered sequentially)
        phase1_action_duration: int = 50,
        phase2_lockout_duration: int = 10,
        phase3_reaction_duration: int = 20,
        phase4_lockout_duration: int = 10,
        phase5_broadcast_duration: int = 1,
        phase6_ending_duration: int = 5
    ) -> GameSession:
        """
        Create a new game session.
        
        Args:
            session_name: Human-readable name for the session
            max_players: Maximum number of players allowed
            turn_limit: Max turns before game ends (0 = unlimited)
            upgrades_enabled: Whether action upgrades are allowed
            phase1_action_duration: Duration of Phase 1 (actions) in minutes
            phase2_lockout_duration: Duration of Phase 2 (lockout) in minutes
            phase3_reaction_duration: Duration of Phase 3 (reactions) in minutes
            phase4_lockout_duration: Duration of Phase 4 (lockout) in minutes
            phase5_broadcast_duration: Duration of Phase 5 (broadcast) in minutes
            phase6_ending_duration: Duration of Phase 6 (ending/rematch window) in minutes
        
        Returns:
            Created GameSession object
        """
        # Calculate total turn duration for reference (excluding ending phase)
        total_duration = (
            phase1_action_duration + phase2_lockout_duration + 
            phase3_reaction_duration + phase4_lockout_duration + phase5_broadcast_duration
        )
        
        session = GameSession(
            session_id=str(uuid.uuid4()),
            session_name=session_name,
            max_players=max_players,
            hourly_duration_minutes=total_duration,  # Calculated from phases
            turn_limit=turn_limit,
            upgrades_enabled=upgrades_enabled,
            # Phase durations
            phase1_action_duration=phase1_action_duration,
            phase2_lockout_duration=phase2_lockout_duration,
            phase3_reaction_duration=phase3_reaction_duration,
            phase4_lockout_duration=phase4_lockout_duration,
            phase5_broadcast_duration=phase5_broadcast_duration,
            phase6_ending_duration=phase6_ending_duration,
            # Rematch tracking
            rematch_count=0,
            winners=[],
            # Initial state
            current_phase=GamePhase.PHASE1_ACTIONS,
            status=SessionStatus.WAITING,
            is_game_started=False,
            turn_number=1,
            created_at=datetime.now(timezone.utc),
            deck_state=[],
            revealed_cards=[]
        )
        
        db.session.add(session)
        db.session.commit()
        
        return session
    
    @staticmethod
    def get_session(session_id: str) -> Optional[GameSession]:
        """Get a session by ID."""
        return GameSession.query.filter_by(session_id=session_id).first()
    
    @staticmethod
    def get_session_or_404(session_id: str) -> GameSession:
        """Get a session by ID or raise error."""
        session = SessionService.get_session(session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found")
        return session
    
    @staticmethod
    def list_sessions(
        status: Optional[SessionStatus] = None,
        is_game_started: Optional[bool] = None
    ) -> List[GameSession]:
        """
        List sessions with optional filters.
        
        Args:
            status: Filter by session status
            is_game_started: Filter by whether game has started
        
        Returns:
            List of matching sessions
        """
        query = GameSession.query
        
        if status:
            query = query.filter_by(status=status)
        
        if is_game_started is not None:
            query = query.filter_by(is_game_started=is_game_started)
        
        return query.order_by(GameSession.created_at.desc()).all()
    
    @staticmethod
    def join_session(session_id: str, player_display_name: str) -> Player:
        """
        Add a player to a session.
        
        Args:
            session_id: Session to join
            player_display_name: Player joining
        
        Returns:
            Updated Player object
        
        Raises:
            ValueError: If session is full, started, or player already in session
        """
        session = SessionService.get_session_or_404(session_id)
        player = Player.query.filter_by(display_name=player_display_name).first()
        
        if not player:
            raise ValueError(f"Player '{player_display_name}' not found")
        
        if session.is_game_started:
            raise ValueError("Cannot join a game that has already started")
        
        if session.is_full:
            raise ValueError("Session is full")
        
        if player.session_id and player.session_id != session_id:
            existing_session = GameSession.query.get(player.session_id)
            if existing_session and existing_session.status in (SessionStatus.WAITING, SessionStatus.ACTIVE):
                raise ValueError("Player is already in another session")
        
        player.session_id = session_id
        player.player_statuses = [PlayerStatus.WAITING]
        
        db.session.commit()
        return player
    
    @staticmethod
    def leave_session(player_display_name: str) -> Player:
        """
        Remove a player from their current session.
        
        Args:
            player_display_name: Player leaving
        
        Returns:
            Updated Player object
        """
        player = Player.query.filter_by(display_name=player_display_name).first()
        
        if not player:
            raise ValueError(f"Player '{player_display_name}' not found")
        
        if player.session_id:
            session = SessionService.get_session(player.session_id)
            if session and session.is_game_started:
                raise ValueError("Cannot leave a game that has started")
        
        player.session_id = None
        player.player_statuses = [PlayerStatus.WAITING]
        player.card_types = []
        player.coins = 2
        
        db.session.commit()
        return player
    
    @staticmethod
    def start_session(session_id: str) -> GameSession:
        """
        Start a game session.
        
        This initializes the deck, deals cards, and sets the first phase.
        Also registers LLM agents with the lang_graph_server.
        
        Args:
            session_id: Session to start
        
        Returns:
            Updated GameSession object
        """
        session = SessionService.get_session_or_404(session_id)
        
        if session.is_game_started:
            raise ValueError("Game has already started")
        
        players = Player.query.filter_by(session_id=session_id).all()
        if len(players) < 2:
            raise ValueError("Need at least 2 players to start")
        
        # Initialize deck (3 of each card = 15 total)
        deck = (
            [CardType.DUKE] * 3 +
            [CardType.ASSASSIN] * 3 +
            [CardType.CAPTAIN] * 3 +
            [CardType.AMBASSADOR] * 3 +
            [CardType.CONTESSA] * 3
        )
        
        # Shuffle deck
        import random
        random.shuffle(deck)
        
        # Deal 2 cards to each player
        for player in players:
            player.card_types = [deck.pop(), deck.pop()]
            player.player_statuses = [PlayerStatus.ALIVE]
            player.coins = 2
            player.to_be_initiated = []
        
        # Update session state
        session.deck_state = deck
        session.is_game_started = True
        session.status = SessionStatus.ACTIVE
        session.current_phase = GamePhase.PHASE1_ACTIONS
        session.turn_number = 1
        session.phase_end_time = datetime.now(timezone.utc) + timedelta(
            minutes=session.get_phase_duration(GamePhase.PHASE1_ACTIONS)
        )
        
        db.session.commit()
        
        # Register LLM agents with lang_graph_server
        SessionService._register_llm_agents_with_langgraph(session_id, players)
        
        return session
    
    @staticmethod
    def _register_llm_agents_with_langgraph(session_id: str, players: List[Player]) -> None:
        """
        Register LLM agents with the lang_graph_server.
        
        This is called after a session starts to create agent instances
        in the lang_graph_server's in-memory registry.
        
        Args:
            session_id: Game session ID
            players: List of all players in the session
        """
        from app.services.lang_graph_client import LangGraphClient
        
        # Filter to LLM agents only
        llm_agents = [p for p in players if p.player_type == "llm_agent"]
        
        if not llm_agents:
            logger.info(f"[SESSION] No LLM agents to register for session {session_id}")
            return
        
        # Build agent configs
        agent_configs = [
            {
                "agent_id": agent.display_name,
                "play_style": "balanced",  # Could be stored in player profile
                "personality": "friendly",  # Could be stored in player profile
                "coins": agent.coins,
            }
            for agent in llm_agents
        ]
        
        # Get all player names for context
        players_alive = [p.display_name for p in players if p.is_alive]
        
        logger.info(
            f"[SESSION] Registering {len(llm_agents)} LLM agents for session {session_id}: "
            f"{[a['agent_id'] for a in agent_configs]}"
        )
        
        # Call lang_graph_server
        result = LangGraphClient.register_agents(
            session_id=session_id,
            agents=agent_configs,
            players_alive=players_alive
        )
        
        if result.get("success") is False:
            logger.error(
                f"[SESSION] Failed to register LLM agents: {result.get('error')}"
            )
        else:
            logger.info(
                f"[SESSION] Successfully registered {result.get('agents_registered', 0)} agents"
            )
    
    @staticmethod
    def end_session(session_id: str, status: SessionStatus = SessionStatus.COMPLETED) -> GameSession:
        """
        End a game session.
        
        Args:
            session_id: Session to end
            status: Final status (COMPLETED or CANCELLED)
        
        Returns:
            Updated GameSession object
        """
        session = SessionService.get_session_or_404(session_id)
        
        session.status = status
        session.is_game_started = False
        
        # Clear player session associations
        players = Player.query.filter_by(session_id=session_id).all()
        for player in players:
            player.session_id = None
            player.card_types = []
            player.player_statuses = [PlayerStatus.WAITING]
        
        db.session.commit()
        
        # Cleanup LLM agents from lang_graph_server
        SessionService._cleanup_llm_agents_from_langgraph(session_id)
        
        return session
    
    @staticmethod
    def _cleanup_llm_agents_from_langgraph(session_id: str) -> None:
        """
        Remove LLM agents from lang_graph_server when session ends.
        
        This frees memory in the lang_graph_server.
        
        Args:
            session_id: Game session ID
        """
        from app.services.lang_graph_client import LangGraphClient
        
        logger.info(f"[SESSION] Cleaning up LLM agents for session {session_id}")
        
        result = LangGraphClient.cleanup_agents(session_id)
        
        if result.get("success"):
            logger.info(
                f"[SESSION] Cleaned up {result.get('agents_removed', 0)} agents"
            )
        else:
            logger.warning(
                f"[SESSION] Failed to cleanup agents: {result.get('error')}"
            )
    
    @staticmethod
    def add_broadcast_destination(
        session_id: str,
        platform: SocialMediaPlatform,
        channel_id: str,
        channel_name: str,
        webhook_url: Optional[str] = None
    ) -> BroadcastDestination:
        """
        Add a broadcast destination to a session.
        
        Args:
            session_id: Session to add destination to
            platform: Target platform
            channel_id: Platform-specific channel/thread ID
            channel_name: Human-readable name
            webhook_url: Optional webhook URL for push notifications
        
        Returns:
            Created BroadcastDestination object
        """
        session = SessionService.get_session_or_404(session_id)
        
        destination = BroadcastDestination(
            session_id=session_id,
            platform=platform,
            channel_id=channel_id,
            channel_name=channel_name,
            webhook_url=webhook_url
        )
        
        db.session.add(destination)
        db.session.commit()
        
        return destination
    
    @staticmethod
    def remove_broadcast_destination(destination_id: int) -> bool:
        """
        Remove a broadcast destination.
        
        Returns:
            True if removed, False if not found
        """
        destination = BroadcastDestination.query.get(destination_id)
        if not destination:
            return False
        
        db.session.delete(destination)
        db.session.commit()
        return True
    
    @staticmethod
    def get_broadcast_destinations(session_id: str) -> List[BroadcastDestination]:
        """Get all broadcast destinations for a session."""
        return BroadcastDestination.query.filter_by(session_id=session_id).all()
    
    @staticmethod
    def update_session(
        session_id: str,
        session_name: Optional[str] = None,
        max_players: Optional[int] = None,
        turn_limit: Optional[int] = None,
        upgrades_enabled: Optional[bool] = None,
        # Phase durations (numbered sequentially)
        phase1_action_duration: Optional[int] = None,
        phase2_lockout_duration: Optional[int] = None,
        phase3_reaction_duration: Optional[int] = None,
        phase4_lockout_duration: Optional[int] = None,
        phase5_broadcast_duration: Optional[int] = None,
        phase6_ending_duration: Optional[int] = None
    ) -> GameSession:
        """
        Update session configuration.
        
        Only works on sessions that haven't started.
        
        Returns:
            Updated GameSession object
        """
        session = SessionService.get_session_or_404(session_id)
        
        if session.is_game_started:
            raise ValueError("Cannot modify a game that has started")
        
        if session_name is not None:
            session.session_name = session_name
        if max_players is not None:
            session.max_players = max_players
        if turn_limit is not None:
            session.turn_limit = turn_limit
        if upgrades_enabled is not None:
            session.upgrades_enabled = upgrades_enabled
        
        # Update phase durations
        if phase1_action_duration is not None:
            session.phase1_action_duration = phase1_action_duration
        if phase2_lockout_duration is not None:
            session.phase2_lockout_duration = phase2_lockout_duration
        if phase3_reaction_duration is not None:
            session.phase3_reaction_duration = phase3_reaction_duration
        if phase4_lockout_duration is not None:
            session.phase4_lockout_duration = phase4_lockout_duration
        if phase5_broadcast_duration is not None:
            session.phase5_broadcast_duration = phase5_broadcast_duration
        if phase6_ending_duration is not None:
            session.phase6_ending_duration = phase6_ending_duration
        
        # Recalculate total duration (excluding ending phase)
        session.hourly_duration_minutes = (
            session.phase1_action_duration + session.phase2_lockout_duration +
            session.phase3_reaction_duration + session.phase4_lockout_duration +
            session.phase5_broadcast_duration
        )
        
        db.session.commit()
        return session
    
    @staticmethod
    def session_to_dict(session: GameSession, include_broadcasts: bool = True) -> dict:
        """
        Convert a GameSession to a dictionary for API responses.
        
        Args:
            session: GameSession object
            include_broadcasts: Whether to include broadcast destinations
        
        Returns:
            Dictionary representation
        """
        result = {
            'session_id': session.session_id,
            'session_name': session.session_name,
            'current_phase': session.current_phase.value if session.current_phase else None,
            'phase_end_time': session.phase_end_time.isoformat() if session.phase_end_time else None,
            'turn_number': session.turn_number,
            'turn_limit': session.turn_limit,
            'max_players': session.max_players,
            'player_count': session.players.count() if session.players else 0,
            'upgrades_enabled': session.upgrades_enabled,
            'is_game_started': session.is_game_started,
            'status': session.status.value if session.status else None,
            'created_at': session.created_at.isoformat() if session.created_at else None,
            # Phase durations (numbered sequentially)
            'phase1_action_duration': session.phase1_action_duration,
            'phase2_lockout_duration': session.phase2_lockout_duration,
            'phase3_reaction_duration': session.phase3_reaction_duration,
            'phase4_lockout_duration': session.phase4_lockout_duration,
            'phase5_broadcast_duration': session.phase5_broadcast_duration,
            'phase6_ending_duration': session.phase6_ending_duration,
            # Rematch tracking
            'rematch_count': session.rematch_count,
            'winners': session.winners or [],
        }
        
        if include_broadcasts:
            result['broadcast_destinations'] = [
                {
                    'id': bd.id,
                    'platform': bd.platform.value if bd.platform else None,
                    'channel_id': bd.channel_id,
                    'channel_name': bd.channel_name,
                    'webhook_url': bd.webhook_url
                }
                for bd in (session.broadcast_destinations or [])
            ]
        
        return result
    
    @staticmethod
    def transition_phase(session_id: str) -> GameSession:
        """
        Transition to the next phase.
        
        Returns:
            Updated GameSession object
        """
        session = SessionService.get_session_or_404(session_id)
        
        if not session.is_game_started:
            raise ValueError("Game has not started")
        
        # Find current phase index and move to next
        current_index = PHASE_ORDER.index(session.current_phase)
        next_index = (current_index + 1) % len(PHASE_ORDER)
        next_phase = PHASE_ORDER[next_index]
        
        # If wrapping back to PHASE1, increment turn
        if next_phase == GamePhase.PHASE1_ACTIONS and current_index > 0:
            session.turn_number += 1
            
            # Check turn limit
            if session.turn_limit > 0 and session.turn_number > session.turn_limit:
                session.status = SessionStatus.COMPLETED
                session.is_game_started = False
                db.session.commit()
                return session
        
        session.current_phase = next_phase
        session.phase_end_time = datetime.now(timezone.utc) + timedelta(
            minutes=session.get_phase_duration(next_phase)
        )
        
        db.session.commit()
        return session
    
    @staticmethod
    def get_session_status(session_id: str, include_broadcasts: bool = False) -> dict:
        """
        Get detailed status of a game session.
        
        Args:
            session_id: Session to get status for
            include_broadcasts: Whether to include broadcast destinations
        
        Returns:
            Dictionary with session status details
        """
        session = SessionService.get_session(session_id)
        if not session:
            return {'error': 'Session not found'}
        
        # Get players in session
        players = Player.query.filter_by(session_id=session_id).all()
        
        # Calculate stats
        total_players = len(players)
        players_alive = [p for p in players if p.is_alive]
        players_dead = [p for p in players if not p.is_alive]
        
        # Calculate remaining turns
        remaining_turns = None
        if session.turn_limit and session.turn_limit > 0:
            remaining_turns = max(0, session.turn_limit - session.turn_number)
        
        # Calculate time remaining in current phase
        time_remaining_seconds = None
        if session.phase_end_time:
            now = datetime.now(timezone.utc)
            if session.phase_end_time > now:
                time_remaining_seconds = int((session.phase_end_time - now).total_seconds())
            else:
                time_remaining_seconds = 0
        
        status = {
            'session_id': session.session_id,
            'session_name': session.session_name,
            
            # Game progress
            'is_ongoing': session.is_game_started and session.status == SessionStatus.ACTIVE,
            'status': session.status.value if session.status else None,
            'current_phase': session.current_phase.value if session.current_phase else None,
            'phase_end_time': session.phase_end_time.isoformat() if session.phase_end_time else None,
            'time_remaining_seconds': time_remaining_seconds,
            
            # Turn info
            'turn_number': session.turn_number,
            'turn_limit': session.turn_limit,
            'remaining_turns': remaining_turns,
            
            # Player stats
            'player_count': total_players,
            'max_players': session.max_players,
            'players_alive': len(players_alive),
            'players_dead': len(players_dead),
            'players_alive_names': [p.display_name for p in players_alive],
            'players_dead_names': [p.display_name for p in players_dead],
            
            # Revealed cards
            'revealed_cards_count': len(session.revealed_cards or []),
            'revealed_cards': [c.value for c in (session.revealed_cards or [])],
        }
        
        # Include broadcast destinations if requested (admin only)
        if include_broadcasts:
            destinations = SessionService.get_broadcast_destinations(session_id)
            status['broadcast_destinations'] = [
                {
                    'id': d.id,
                    'platform': d.platform.value if d.platform else None,
                    'channel_id': d.channel_id,
                    'channel_name': d.channel_name,
                    'is_configured': bool(d.webhook_url)
                }
                for d in destinations
            ]
            status['broadcast_count'] = len(destinations)
        
        return status
    
    # ---------------------- Platform Channel Bindings ---------------------- #
    
    @staticmethod
    def bind_discord_channel(session_id: str, channel_id: str) -> GameSession:
        """
        Bind a Discord channel to a game session.
        
        Args:
            session_id: Session to bind
            channel_id: Discord channel ID (as string)
        
        Returns:
            Updated GameSession object
        """
        session = SessionService.get_session_or_404(session_id)
        session.discord_channel_id = channel_id
        db.session.commit()
        return session
    
    @staticmethod
    def unbind_discord_channel(session_id: str) -> GameSession:
        """
        Unbind Discord channel from a game session.
        
        Args:
            session_id: Session to unbind
        
        Returns:
            Updated GameSession object
        """
        session = SessionService.get_session_or_404(session_id)
        session.discord_channel_id = None
        db.session.commit()
        return session
    
    @staticmethod
    def bind_slack_channel(session_id: str, channel_id: str) -> GameSession:
        """
        Bind a Slack channel to a game session.
        
        Args:
            session_id: Session to bind
            channel_id: Slack channel ID
        
        Returns:
            Updated GameSession object
        """
        session = SessionService.get_session_or_404(session_id)
        session.slack_channel_id = channel_id
        db.session.commit()
        return session
    
    @staticmethod
    def unbind_slack_channel(session_id: str) -> GameSession:
        """
        Unbind Slack channel from a game session.
        
        Args:
            session_id: Session to unbind
        
        Returns:
            Updated GameSession object
        """
        session = SessionService.get_session_or_404(session_id)
        session.slack_channel_id = None
        db.session.commit()
        return session
    
    @staticmethod
    def get_discord_channel_sessions() -> List[dict]:
        """
        Get all sessions with Discord channel bindings.
        
        Used by Discord bot on startup to populate channel registry.
        
        Returns:
            List of dicts with session_id, discord_channel_id, session_name
        """
        sessions = GameSession.query.filter(
            GameSession.discord_channel_id.isnot(None)
        ).all()
        
        return [
            {
                'session_id': s.session_id,
                'discord_channel_id': s.discord_channel_id,
                'session_name': s.session_name,
                'is_active': s.is_active
            }
            for s in sessions
        ]
    
    @staticmethod
    def get_slack_channel_sessions() -> List[dict]:
        """
        Get all sessions with Slack channel bindings.
        
        Used by Slack bot on startup to populate channel registry.
        
        Returns:
            List of dicts with session_id, slack_channel_id, session_name
        """
        sessions = GameSession.query.filter(
            GameSession.slack_channel_id.isnot(None)
        ).all()
        
        return [
            {
                'session_id': s.session_id,
                'slack_channel_id': s.slack_channel_id,
                'session_name': s.session_name,
                'is_active': s.is_active
            }
            for s in sessions
        ]
    
    @staticmethod
    def get_session_by_discord_channel(channel_id: str) -> Optional[GameSession]:
        """
        Find session by Discord channel ID.
        
        Args:
            channel_id: Discord channel ID
        
        Returns:
            GameSession if found, None otherwise
        """
        return GameSession.query.filter_by(discord_channel_id=channel_id).first()
    
    @staticmethod
    def get_session_by_slack_channel(channel_id: str) -> Optional[GameSession]:
        """
        Find session by Slack channel ID.
        
        Args:
            channel_id: Slack channel ID
        
        Returns:
            GameSession if found, None otherwise
        """
        return GameSession.query.filter_by(slack_channel_id=channel_id).first()
    
    # ---------------------- Winner Calculation ---------------------- #
    
    @staticmethod
    def calculate_winners(session_id: str) -> List[str]:
        """
        Calculate winners for a game session.
        
        Winners are determined by:
        1. Players with the most cards alive
        2. If tied, players with the most coins
        
        Args:
            session_id: Session to calculate winners for
        
        Returns:
            List of winner display names
        """
        session = SessionService.get_session_or_404(session_id)
        players = Player.query.filter_by(session_id=session_id).all()
        
        if not players:
            return []
        
        # Get alive players
        alive_players = [p for p in players if p.is_alive]
        
        # If only one player alive, they're the winner
        if len(alive_players) == 1:
            return [alive_players[0].display_name]
        
        # If no players alive (shouldn't happen), return empty
        if len(alive_players) == 0:
            return []
        
        # Calculate scores: (card_count, coins, display_name)
        player_scores = []
        for player in alive_players:
            card_count = len(player.card_types or [])
            coins = player.coins or 0
            player_scores.append((card_count, coins, player.display_name))
        
        # Sort by card count (desc), then coins (desc)
        player_scores.sort(key=lambda x: (x[0], x[1]), reverse=True)
        
        # Get the highest score
        max_cards = player_scores[0][0]
        max_coins = player_scores[0][1]
        
        # Find all players with the same top score
        winners = [
            name for cards, coins, name in player_scores
            if cards == max_cards and coins == max_coins
        ]
        
        return winners
    
    # ---------------------- Session Restart & Rematch ---------------------- #
    
    @staticmethod
    def transition_to_ending(session_id: str) -> GameSession:
        """
        Transition a session to the ENDING phase.
        
        This happens when a game ends (turn limit reached or only one player alive).
        Players can request rematch during this phase.
        
        Args:
            session_id: Session to transition
        
        Returns:
            Updated GameSession object
        """
        session = SessionService.get_session_or_404(session_id)
        
        # Calculate and store winners
        winners = SessionService.calculate_winners(session_id)
        session.winners = winners
        
        # Transition to ENDING phase
        session.current_phase = GamePhase.ENDING
        session.phase_end_time = datetime.now(timezone.utc) + timedelta(
            minutes=session.get_phase_duration(GamePhase.ENDING)
        )
        session.is_game_started = False  # Game is no longer "in progress"
        
        db.session.commit()
        
        logger.info(
            f"[SESSION] Session {session_id} transitioned to ENDING phase. "
            f"Winners: {winners}"
        )
        
        return session
    
    @staticmethod
    def restart_session(session_id: str) -> GameSession:
        """
        Restart a game session (admin only).
        
        This reverts the session to WAITING status, clears all players,
        and resets the rematch count. Players must rejoin.
        
        Args:
            session_id: Session to restart
        
        Returns:
            Updated GameSession object
        """
        session = SessionService.get_session_or_404(session_id)
        
        # Clear player session associations
        players = Player.query.filter_by(session_id=session_id).all()
        for player in players:
            player.session_id = None
            player.card_types = []
            player.player_statuses = [PlayerStatus.WAITING]
            player.coins = 2
            player.to_be_initiated = []
            player.target_display_name = None
        
        # Reset session state
        session.status = SessionStatus.WAITING
        session.is_game_started = False
        session.current_phase = GamePhase.PHASE1_ACTIONS
        session.phase_end_time = None
        session.turn_number = 1
        session.deck_state = []
        session.revealed_cards = []
        session.rematch_count = 0  # Reset rematch count on admin restart
        session.winners = []
        
        db.session.commit()
        
        # Cleanup LLM agents from lang_graph_server
        SessionService._cleanup_llm_agents_from_langgraph(session_id)
        
        logger.info(f"[SESSION] Session {session_id} restarted by admin. Players cleared.")
        
        return session
    
    @staticmethod
    def rematch_session(session_id: str) -> GameSession:
        """
        Request a rematch for a game session.
        
        This is player-initiated and only available during the ENDING phase.
        The session reverts to WAITING but keeps all current players.
        Rematch count is incremented (max 3 before forced completion).
        
        Args:
            session_id: Session to rematch
        
        Returns:
            Updated GameSession object
        
        Raises:
            ValueError: If not in ENDING phase or max rematches reached
        """
        session = SessionService.get_session_or_404(session_id)
        
        # Check if in ENDING phase
        if session.current_phase != GamePhase.ENDING:
            raise ValueError("Rematch can only be requested during ENDING phase")
        
        # Check rematch limit
        if session.rematch_count >= 3:
            raise ValueError("Maximum rematch limit (3) reached. Session will be completed.")
        
        # Cancel the ending phase job to prevent auto-completion
        from app.jobs.ending_phase_job import EndingPhaseJob
        EndingPhaseJob.cancel(session_id)
        
        # Get current players (keep them in the session)
        players = Player.query.filter_by(session_id=session_id).all()
        
        # Reset player states but keep them in the session
        for player in players:
            player.card_types = []
            player.player_statuses = [PlayerStatus.WAITING]
            player.coins = 2
            player.to_be_initiated = []
            player.target_display_name = None
        
        # Reset session state but keep players and increment rematch count
        session.status = SessionStatus.WAITING
        session.is_game_started = False
        session.current_phase = GamePhase.PHASE1_ACTIONS
        session.phase_end_time = None
        session.turn_number = 1
        session.deck_state = []
        session.revealed_cards = []
        session.rematch_count += 1
        session.winners = []
        
        db.session.commit()
        
        logger.info(
            f"[SESSION] Session {session_id} rematch requested. "
            f"Rematch #{session.rematch_count}, {len(players)} players retained."
        )
        
        return session
    
    @staticmethod
    def complete_session_from_ending(session_id: str) -> GameSession:
        """
        Complete a session from the ENDING phase.
        
        Called when the ENDING phase timer expires without a rematch request.
        Transitions the session to COMPLETED and clears players.
        
        Args:
            session_id: Session to complete
        
        Returns:
            Updated GameSession object
        """
        session = SessionService.get_session_or_404(session_id)
        
        if session.current_phase != GamePhase.ENDING:
            raise ValueError("Session is not in ENDING phase")
        
        # Clear player session associations
        players = Player.query.filter_by(session_id=session_id).all()
        for player in players:
            player.session_id = None
            player.card_types = []
            player.player_statuses = [PlayerStatus.WAITING]
        
        # Mark as completed
        session.status = SessionStatus.COMPLETED
        session.phase_end_time = None
        
        db.session.commit()
        
        # Cleanup LLM agents from lang_graph_server
        SessionService._cleanup_llm_agents_from_langgraph(session_id)
        
        logger.info(
            f"[SESSION] Session {session_id} completed from ENDING phase. "
            f"Winners: {session.winners}"
        )
        
        return session

