"""
Session Service.

Handles game session creation, player joining, and session management.
"""

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


class SessionService:
    """Service for game session management."""
    
    @staticmethod
    def create_session(
        session_name: str,
        max_players: int = 6,
        turn_limit: int = 10,
        upgrades_enabled: bool = True,
        # Phase durations in minutes
        phase1_duration: int = 50,
        lockout1_duration: int = 10,
        phase2_duration: int = 20,
        lockout2_duration: int = 10,
        broadcast_duration: int = 1
    ) -> GameSession:
        """
        Create a new game session.
        
        Args:
            session_name: Human-readable name for the session
            max_players: Maximum number of players allowed
            turn_limit: Max turns before game ends (0 = unlimited)
            upgrades_enabled: Whether action upgrades are allowed
            phase1_duration: Duration of Phase 1 (actions) in minutes
            lockout1_duration: Duration of Lockout 1 in minutes
            phase2_duration: Duration of Phase 2 (reactions) in minutes
            lockout2_duration: Duration of Lockout 2 in minutes
            broadcast_duration: Duration of Broadcast phase in minutes
        
        Returns:
            Created GameSession object
        """
        # Calculate total turn duration for reference
        total_duration = (
            phase1_duration + lockout1_duration + 
            phase2_duration + lockout2_duration + broadcast_duration
        )
        
        session = GameSession(
            session_id=str(uuid.uuid4()),
            session_name=session_name,
            max_players=max_players,
            hourly_duration_minutes=total_duration,  # Calculated from phases
            turn_limit=turn_limit,
            upgrades_enabled=upgrades_enabled,
            # Phase durations
            phase1_duration=phase1_duration,
            lockout1_duration=lockout1_duration,
            phase2_duration=phase2_duration,
            lockout2_duration=lockout2_duration,
            broadcast_duration=broadcast_duration,
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
        return session
    
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
        return session
    
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
        # Phase durations
        phase1_duration: Optional[int] = None,
        lockout1_duration: Optional[int] = None,
        phase2_duration: Optional[int] = None,
        lockout2_duration: Optional[int] = None,
        broadcast_duration: Optional[int] = None
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
        if phase1_duration is not None:
            session.phase1_duration = phase1_duration
        if lockout1_duration is not None:
            session.lockout1_duration = lockout1_duration
        if phase2_duration is not None:
            session.phase2_duration = phase2_duration
        if lockout2_duration is not None:
            session.lockout2_duration = lockout2_duration
        if broadcast_duration is not None:
            session.broadcast_duration = broadcast_duration
        
        # Recalculate total duration
        session.hourly_duration_minutes = (
            session.phase1_duration + session.lockout1_duration +
            session.phase2_duration + session.lockout2_duration +
            session.broadcast_duration
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
            # Phase durations
            'phase1_duration': session.phase1_duration,
            'lockout1_duration': session.lockout1_duration,
            'phase2_duration': session.phase2_duration,
            'lockout2_duration': session.lockout2_duration,
            'broadcast_duration': session.broadcast_duration,
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

