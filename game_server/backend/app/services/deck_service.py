"""
Deck Service.

Handles card deck management, dealing, shuffling, and returns.
"""

import random
from typing import Dict, List, Optional

from app.constants import CardType
from app.extensions import db
from app.models.postgres_sql_db_models import GameSession, Player


class DeckService:
    """Service for managing the card deck."""
    
    # Standard Coup deck: 3 copies of each card (15 total)
    FULL_DECK = (
        [CardType.DUKE] * 3 +
        [CardType.ASSASSIN] * 3 +
        [CardType.CAPTAIN] * 3 +
        [CardType.AMBASSADOR] * 3 +
        [CardType.CONTESSA] * 3
    )
    
    @staticmethod
    def initialize_deck(session_id: str) -> List[CardType]:
        """
        Create and shuffle a new deck for a session.
        
        Args:
            session_id: Session to initialize deck for
        
        Returns:
            Shuffled deck
        """
        session = GameSession.query.filter_by(session_id=session_id).first()
        if not session:
            raise ValueError(f"Session '{session_id}' not found")
        
        deck = list(DeckService.FULL_DECK)
        random.shuffle(deck)
        
        session.deck_state = deck
        db.session.commit()
        
        return deck
    
    @staticmethod
    def deal_cards(session_id: str) -> Dict[str, List[CardType]]:
        """
        Deal 2 cards to each player in the session.
        
        Args:
            session_id: Session to deal cards for
        
        Returns:
            Mapping of player display_name to their cards
        """
        session = GameSession.query.filter_by(session_id=session_id).first()
        if not session:
            raise ValueError(f"Session '{session_id}' not found")
        
        players = Player.query.filter_by(session_id=session_id).all()
        if not players:
            raise ValueError("No players in session")
        
        # Initialize deck if empty
        deck = list(session.deck_state or [])
        if not deck:
            deck = list(DeckService.FULL_DECK)
            random.shuffle(deck)
        
        # Check if enough cards
        if len(deck) < len(players) * 2:
            raise ValueError("Not enough cards in deck")
        
        # Deal 2 cards to each player
        dealt = {}
        for player in players:
            cards = [deck.pop(), deck.pop()]
            player.card_types = cards
            dealt[player.display_name] = cards
        
        session.deck_state = deck
        db.session.commit()
        
        return dealt
    
    @staticmethod
    def draw_cards(session_id: str, count: int) -> List[CardType]:
        """
        Draw cards from the deck.
        
        Args:
            session_id: Session to draw from
            count: Number of cards to draw
        
        Returns:
            List of drawn cards
        """
        session = GameSession.query.filter_by(session_id=session_id).first()
        if not session:
            raise ValueError(f"Session '{session_id}' not found")
        
        deck = list(session.deck_state or [])
        if len(deck) < count:
            raise ValueError(f"Not enough cards in deck (have {len(deck)}, need {count})")
        
        drawn = [deck.pop() for _ in range(count)]
        
        session.deck_state = deck
        db.session.commit()
        
        return drawn
    
    @staticmethod
    def draw_card(session_id: str) -> Optional[CardType]:
        """
        Draw a single card from the deck.
        
        Args:
            session_id: Session to draw from
        
        Returns:
            Drawn card, or None if deck is empty
        """
        session = GameSession.query.filter_by(session_id=session_id).first()
        if not session:
            return None
        
        deck = list(session.deck_state or [])
        if not deck:
            return None
        
        card = deck.pop()
        session.deck_state = deck
        db.session.commit()
        
        return card
    
    @staticmethod
    def return_cards(session_id: str, cards: List[CardType], shuffle: bool = True) -> None:
        """
        Return cards to the deck.
        
        Args:
            session_id: Session to return cards to
            cards: Cards to return
            shuffle: Whether to shuffle after returning
        """
        session = GameSession.query.filter_by(session_id=session_id).first()
        if not session:
            raise ValueError(f"Session '{session_id}' not found")
        
        deck = list(session.deck_state or [])
        deck.extend(cards)
        
        if shuffle:
            random.shuffle(deck)
        
        session.deck_state = deck
        db.session.commit()
    
    @staticmethod
    def return_card(session_id: str, card: CardType, shuffle: bool = True) -> None:
        """
        Return a single card to the deck.
        
        Args:
            session_id: Session to return card to
            card: Card to return
            shuffle: Whether to shuffle after returning
        """
        DeckService.return_cards(session_id, [card], shuffle)
    
    @staticmethod
    def reveal_card(session_id: str, player_display_name: str, card: CardType) -> None:
        """
        Reveal a card (player loses influence).
        
        Args:
            session_id: Session
            player_display_name: Player revealing card
            card: Card to reveal
        """
        session = GameSession.query.filter_by(session_id=session_id).first()
        player = Player.query.filter_by(display_name=player_display_name).first()
        
        if not session or not player:
            raise ValueError("Session or player not found")
        
        # Remove card from player's hand
        cards = list(player.card_types or [])
        if card not in cards:
            raise ValueError(f"Player does not have card {card.value}")
        
        cards.remove(card)
        player.card_types = cards
        
        # Add to revealed cards
        revealed = list(session.revealed_cards or [])
        revealed.append(card)
        session.revealed_cards = revealed
        
        # Update player status if dead
        from app.constants import PlayerStatus
        if not cards:
            statuses = list(player.player_statuses or [])
            if PlayerStatus.ALIVE in statuses:
                statuses.remove(PlayerStatus.ALIVE)
            if PlayerStatus.DEAD not in statuses:
                statuses.append(PlayerStatus.DEAD)
            player.player_statuses = statuses
        
        db.session.commit()
    
    @staticmethod
    def swap_cards(
        session_id: str,
        player_display_name: str,
        cards_to_return: List[CardType],
        cards_to_keep: List[CardType]
    ) -> None:
        """
        Swap cards (Ambassador ability).
        
        Args:
            session_id: Session
            player_display_name: Player swapping
            cards_to_return: Cards to put back in deck
            cards_to_keep: Cards to keep in hand
        """
        session = GameSession.query.filter_by(session_id=session_id).first()
        player = Player.query.filter_by(display_name=player_display_name).first()
        
        if not session or not player:
            raise ValueError("Session or player not found")
        
        # Update player's hand
        player.card_types = cards_to_keep
        
        # Return cards to deck
        DeckService.return_cards(session_id, cards_to_return, shuffle=True)
    
    @staticmethod
    def get_deck_size(session_id: str) -> int:
        """Get the number of cards remaining in the deck."""
        session = GameSession.query.filter_by(session_id=session_id).first()
        if not session:
            return 0
        return len(session.deck_state or [])


# Singleton instance
deck_service = DeckService()

