"""
Player Game State CRUD Operations.

Data access layer for player_game_state table.
"""

from typing import List, Optional, Tuple
from uuid import UUID

from app.crud.base import BaseCRUD
from app.models.postgres_sql_db_models import PlayerGameState, UserAccount
from app.constants import CardType, PlayerStatus, ToBeInitiated
from app.extensions import db


class PlayerGameStateCRUD(BaseCRUD[PlayerGameState]):
    """CRUD operations for PlayerGameState."""
    
    model = PlayerGameState
    
    # =============================================
    # Custom Query Methods
    # =============================================
    
    @classmethod
    def get_by_session(cls, session_id: str) -> List[PlayerGameState]:
        """
        Get all game states for a session.
        
        Args:
            session_id: Game session ID
        
        Returns:
            List of PlayerGameState for all players in session
        """
        return cls.model.query.filter_by(session_id=session_id).all()
    
    @classmethod
    def get_by_user_and_session(cls, user_id: UUID, session_id: str) -> Optional[PlayerGameState]:
        """
        Get game state for a specific user in a session.
        
        Args:
            user_id: User account UUID
            session_id: Game session ID
        
        Returns:
            PlayerGameState or None
        """
        return cls.model.query.filter_by(
            user_id=user_id,
            session_id=session_id
        ).first()
    
    @classmethod
    def get_active_for_user(cls, user_id: UUID) -> Optional[PlayerGameState]:
        """
        Get user's active game state (in a session).
        
        Args:
            user_id: User account UUID
        
        Returns:
            Active PlayerGameState or None
        """
        return cls.model.query.filter(
            cls.model.user_id == user_id,
            cls.model.session_id.isnot(None)
        ).first()
    
    @classmethod
    def get_alive_players(cls, session_id: str) -> List[PlayerGameState]:
        """
        Get all alive players in a session.
        
        Args:
            session_id: Game session ID
        
        Returns:
            List of alive PlayerGameState
        """
        all_states = cls.get_by_session(session_id)
        return [s for s in all_states if s.is_alive]
    
    @classmethod
    def get_with_pending_actions(cls, session_id: str) -> List[PlayerGameState]:
        """
        Get players with pending actions in a session.
        
        Args:
            session_id: Game session ID
        
        Returns:
            List of PlayerGameState with pending actions
        """
        all_states = cls.get_by_session(session_id)
        return [s for s in all_states if s.has_pending_action]
    
    # =============================================
    # Display Name Lookups (via UserAccount join)
    # =============================================
    
    @classmethod
    def get_by_display_name(cls, display_name: str) -> Optional[PlayerGameState]:
        """
        Get active game state by user's display name.
        
        This joins with UserAccount to look up by display_name,
        returning the active game state (where session_id is not null).
        
        Args:
            display_name: User's display name
        
        Returns:
            Active PlayerGameState or None
        """
        return cls.model.query.join(
            UserAccount, cls.model.user_id == UserAccount.user_id
        ).filter(
            UserAccount.display_name == display_name,
            cls.model.session_id.isnot(None)
        ).first()
    
    @classmethod
    def get_by_display_name_and_session(
        cls,
        display_name: str,
        session_id: str
    ) -> Optional[PlayerGameState]:
        """
        Get game state for a user in a specific session by display name.
        
        Args:
            display_name: User's display name
            session_id: Game session ID
        
        Returns:
            PlayerGameState or None
        """
        return cls.model.query.join(
            UserAccount, cls.model.user_id == UserAccount.user_id
        ).filter(
            UserAccount.display_name == display_name,
            cls.model.session_id == session_id
        ).first()
    
    @classmethod
    def get_user_and_state_by_display_name(
        cls,
        display_name: str
    ) -> Optional[Tuple[UserAccount, PlayerGameState]]:
        """
        Get both UserAccount and active PlayerGameState by display name.
        
        Useful when you need both user info and game state.
        
        Args:
            display_name: User's display name
        
        Returns:
            Tuple of (UserAccount, PlayerGameState) or None
        """
        result = db.session.query(UserAccount, cls.model).join(
            cls.model, cls.model.user_id == UserAccount.user_id
        ).filter(
            UserAccount.display_name == display_name,
            cls.model.session_id.isnot(None)
        ).first()
        return result
    
    @classmethod
    def get_session_with_users(cls, session_id: str) -> List[Tuple[UserAccount, 'PlayerGameState']]:
        """
        Get all players in a session with their user accounts.
        
        Returns list of (UserAccount, PlayerGameState) tuples.
        
        Args:
            session_id: Game session ID
        
        Returns:
            List of (UserAccount, PlayerGameState) tuples
        """
        return db.session.query(UserAccount, cls.model).join(
            cls.model, cls.model.user_id == UserAccount.user_id
        ).filter(
            cls.model.session_id == session_id
        ).all()
    
    # =============================================
    # Game State Creation
    # =============================================
    
    @classmethod
    def create_for_session(
        cls,
        user_id: UUID,
        session_id: str,
        starting_coins: int = 2
    ) -> PlayerGameState:
        """
        Create a new game state when player joins session.
        
        Args:
            user_id: User account UUID
            session_id: Game session ID
            starting_coins: Initial coin count
        
        Returns:
            Created PlayerGameState
        """
        return cls.create(
            user_id=user_id,
            session_id=session_id,
            coins=starting_coins,
            player_statuses=[PlayerStatus.ALIVE]
        )
    
    # =============================================
    # Game State Updates
    # =============================================
    
    @classmethod
    def set_cards(cls, game_state_id: UUID, cards: List[CardType]) -> Optional[PlayerGameState]:
        """Set player's cards."""
        return cls.update(game_state_id, card_types=cards)
    
    @classmethod
    def add_card(cls, game_state_id: UUID, card: CardType) -> Optional[PlayerGameState]:
        """Add a card to player's hand."""
        state = cls.get_by_id(game_state_id)
        if state:
            cards = list(state.card_types or [])
            cards.append(card)
            return cls.update(game_state_id, card_types=cards)
        return None
    
    @classmethod
    def remove_card(cls, game_state_id: UUID, card: CardType) -> Optional[PlayerGameState]:
        """Remove a card from player's hand."""
        state = cls.get_by_id(game_state_id)
        if state:
            cards = list(state.card_types or [])
            if card in cards:
                cards.remove(card)
                return cls.update(game_state_id, card_types=cards)
        return state
    
    @classmethod
    def update_coins(cls, game_state_id: UUID, coins: int) -> Optional[PlayerGameState]:
        """Set player's coin count."""
        return cls.update(game_state_id, coins=coins)
    
    @classmethod
    def add_coins(cls, game_state_id: UUID, amount: int) -> Optional[PlayerGameState]:
        """Add coins to player."""
        state = cls.get_by_id(game_state_id)
        if state:
            return cls.update(game_state_id, coins=state.coins + amount)
        return None
    
    @classmethod
    def remove_coins(cls, game_state_id: UUID, amount: int) -> Optional[PlayerGameState]:
        """Remove coins from player (minimum 0)."""
        state = cls.get_by_id(game_state_id)
        if state:
            new_coins = max(0, state.coins - amount)
            return cls.update(game_state_id, coins=new_coins)
        return None
    
    @classmethod
    def set_pending_action(
        cls,
        game_state_id: UUID,
        action: ToBeInitiated,
        target_display_name: Optional[str] = None
    ) -> Optional[PlayerGameState]:
        """Set a pending action for the player."""
        state = cls.get_by_id(game_state_id)
        if state:
            actions = list(state.to_be_initiated or [])
            if action not in actions:
                actions.append(action)
            state.to_be_initiated = actions
            state.target_display_name = target_display_name
            db.session.commit()
        return state
    
    @classmethod
    def clear_pending_actions(cls, game_state_id: UUID) -> Optional[PlayerGameState]:
        """Clear all pending actions."""
        return cls.update(
            game_state_id,
            to_be_initiated=[],
            target_display_name=None
        )
    
    @classmethod
    def eliminate_player(cls, game_state_id: UUID) -> Optional[PlayerGameState]:
        """Mark player as eliminated (dead)."""
        state = cls.get_by_id(game_state_id)
        if state:
            statuses = list(state.player_statuses or [])
            if PlayerStatus.ALIVE in statuses:
                statuses.remove(PlayerStatus.ALIVE)
            if PlayerStatus.DEAD not in statuses:
                statuses.append(PlayerStatus.DEAD)
            return cls.update(game_state_id, player_statuses=statuses)
        return None
    
    @classmethod
    def leave_session(cls, game_state_id: UUID) -> Optional[PlayerGameState]:
        """Remove player from session (clear session_id)."""
        return cls.update(game_state_id, session_id=None)
    
    # =============================================
    # Bulk Operations
    # =============================================
    
    @classmethod
    def clear_all_pending_actions_in_session(cls, session_id: str) -> int:
        """
        Clear pending actions for all players in a session.
        
        Returns:
            Number of players updated
        """
        states = cls.get_by_session(session_id)
        count = 0
        for state in states:
            if state.has_pending_action:
                state.to_be_initiated = []
                state.target_display_name = None
                count += 1
        db.session.commit()
        return count
    
    @classmethod
    def reset_for_new_game(cls, session_id: str, starting_coins: int = 2) -> int:
        """
        Reset all player states for a new game (rematch).
        
        Returns:
            Number of players reset
        """
        states = cls.get_by_session(session_id)
        for state in states:
            state.coins = starting_coins
            state.debt = 0
            state.card_types = []
            state.player_statuses = [PlayerStatus.ALIVE]
            state.to_be_initiated = []
            state.target_display_name = None
        db.session.commit()
        return len(states)
