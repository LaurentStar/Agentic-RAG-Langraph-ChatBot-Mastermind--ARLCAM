"""
Action Resolution Service.

Handles resolving game actions, challenges, blocks, and influence loss.
"""

from typing import List, Optional, Tuple

from app.constants import (
    ACTION_COSTS,
    ACTION_ROLES,
    BLOCK_ROLES,
    CardType,
    PlayerStatus,
    ReactionType,
    ResolutionOutcome,
    ToBeInitiated,
)
from app.extensions import db
from app.models.game_models import ActionResult, TurnResult
from app.models.postgres_sql_db_models import (
    GameSession,
    Player,
    Reaction,
    ToBeInitiatedUpgradeDetails,
    TurnResultORM,
)
from app.services.deck_service import DeckService


class ActionResolutionService:
    """Service for resolving game actions."""
    
    @staticmethod
    def resolve_turn(session_id: str) -> TurnResult:
        """
        Resolve all pending actions for a turn.
        
        This is the main entry point called during LOCKOUT2 phase.
        Resolution order:
        1. Process challenges first (may cancel actions)
        2. Process blocks (may prevent action effects)
        3. Apply remaining action effects
        
        Args:
            session_id: Session to resolve
        
        Returns:
            Complete turn result
        """
        session = GameSession.query.filter_by(session_id=session_id).first()
        if not session:
            raise ValueError(f"Session '{session_id}' not found")
        
        players = Player.query.filter_by(session_id=session_id).all()
        players_by_name = {p.display_name: p for p in players}
        action_results = []
        players_eliminated = []
        
        # Get all reactions for this turn
        reactions = Reaction.query.filter_by(
            session_id=session_id,
            turn_number=session.turn_number,
            is_resolved=False
        ).all()
        
        # Group reactions by actor
        reactions_by_actor = {}
        for reaction in reactions:
            if reaction.actor_display_name not in reactions_by_actor:
                reactions_by_actor[reaction.actor_display_name] = []
            reactions_by_actor[reaction.actor_display_name].append(reaction)
        
        # Process each player's pending action
        for player in players:
            if not player.is_alive:
                continue
            
            if not player.to_be_initiated:
                continue
            
            for action in player.to_be_initiated:
                if action == ToBeInitiated.NO_EVENT:
                    continue
                
                # Get reactions to this action
                action_reactions = reactions_by_actor.get(player.display_name, [])
                
                result = ActionResolutionService._resolve_action_with_reactions(
                    session=session,
                    actor=player,
                    action=action,
                    target_name=player.target_display_name,
                    players_by_name=players_by_name,
                    reactions=action_reactions
                )
                action_results.append(result)
        
        # Mark all reactions as resolved
        for reaction in reactions:
            reaction.is_resolved = True
        
        # Update eliminated players
        for player in players:
            card_count = len(player.card_types or [])
            was_alive = PlayerStatus.ALIVE in (player.player_statuses or [])
            
            if card_count == 0 and was_alive:
                # Player just lost their last card
                player.player_statuses = [PlayerStatus.DEAD]
                players_eliminated.append(player.display_name)
        
        db.session.commit()
        
        # Build summary
        summary_parts = [r.description for r in action_results]
        if players_eliminated:
            summary_parts.append(f"💀 Eliminated: {', '.join(players_eliminated)}")
        
        turn_result = TurnResult(
            session_id=session_id,
            turn_number=session.turn_number,
            action_results=action_results,
            players_eliminated=players_eliminated,
            summary="; ".join(summary_parts) if summary_parts else "No actions this turn."
        )
        
        # Store result in database for history
        ActionResolutionService._store_turn_result(session_id, session.turn_number, turn_result)
        
        return turn_result
    
    @staticmethod
    def _resolve_action_with_reactions(
        session: GameSession,
        actor: Player,
        action: ToBeInitiated,
        target_name: Optional[str],
        players_by_name: dict,
        reactions: List[Reaction]
    ) -> ActionResult:
        """Resolve a single action considering all reactions."""
        
        target = players_by_name.get(target_name) if target_name else None
        
        # Get upgrade details if any
        upgrade = ToBeInitiatedUpgradeDetails.query.filter_by(
            display_name=actor.display_name
        ).first()
        
        # Check for insufficient coins
        cost = ACTION_COSTS.get(action, 0)
        if actor.coins < cost:
            return ActionResult(
                actor=actor.display_name,
                action=action,
                target=target_name,
                outcome=ResolutionOutcome.FAILED,
                cards_revealed=[],
                coins_transferred=0,
                description=f"{actor.display_name}'s {action.value} failed (insufficient coins)"
            )
        
        # Separate challenges and blocks
        challenges = [r for r in reactions if r.reaction_type == ReactionType.CHALLENGE]
        blocks = [r for r in reactions if r.reaction_type == ReactionType.BLOCK]
        
        # Process challenges first
        if challenges:
            challenge = challenges[0]  # First challenger
            challenger = players_by_name.get(challenge.reactor_display_name)
            
            if challenger:
                challenge_result = ActionResolutionService._resolve_challenge(
                    session=session,
                    actor=actor,
                    action=action,
                    challenger=challenger,
                    players_by_name=players_by_name
                )
                
                if challenge_result[0]:  # Challenge succeeded (actor was bluffing)
                    return ActionResult(
                        actor=actor.display_name,
                        action=action,
                        target=target_name,
                        outcome=ResolutionOutcome.CHALLENGED_LOST,
                        cards_revealed=challenge_result[1],
                        coins_transferred=0,
                        description=f"{actor.display_name}'s {action.value} was challenged by {challenger.display_name} - bluff caught! (revealed {', '.join(challenge_result[1])})"
                    )
                else:
                    # Challenge failed - challenger loses influence
                    return ActionResult(
                        actor=actor.display_name,
                        action=action,
                        target=target_name,
                        outcome=ResolutionOutcome.CHALLENGED_WON,
                        cards_revealed=challenge_result[1],
                        coins_transferred=0,
                        description=f"{actor.display_name}'s {action.value} was challenged by {challenger.display_name} - challenge failed! ({challenger.display_name} revealed {', '.join(challenge_result[1])})"
                    )
        
        # Process blocks (if action wasn't challenged)
        if blocks and action in BLOCK_ROLES:
            block = blocks[0]  # First blocker
            blocker = players_by_name.get(block.reactor_display_name)
            
            if blocker:
                # Check if there's a counter-challenge to the block
                block_challenges = [r for r in reactions 
                                   if r.reaction_type == ReactionType.CHALLENGE 
                                   and r.actor_display_name == blocker.display_name]
                
                if block_challenges:
                    # Actor challenged the block
                    block_role = CardType(block.block_with_role.lower()) if block.block_with_role else None
                    
                    if block_role and block_role in (blocker.card_types or []):
                        # Blocker has the card - block succeeds, actor loses influence
                        revealed = ActionResolutionService._player_loses_influence(actor, session.session_id)
                        return ActionResult(
                            actor=actor.display_name,
                            action=action,
                            target=target_name,
                            outcome=ResolutionOutcome.BLOCKED,
                            cards_revealed=revealed,
                            coins_transferred=0,
                            description=f"{actor.display_name}'s {action.value} was blocked by {blocker.display_name} (challenged and proved {block.block_with_role})"
                        )
                    else:
                        # Blocker was bluffing - block fails
                        revealed = ActionResolutionService._player_loses_influence(blocker, session.session_id)
                        # Continue to apply action effects below
                else:
                    # Block not challenged - it succeeds
                    # Deduct coins if action had a cost (assassination)
                    if action == ToBeInitiated.ACT_ASSASSINATION:
                        actor.coins -= 3
                    
                    return ActionResult(
                        actor=actor.display_name,
                        action=action,
                        target=target_name,
                        outcome=ResolutionOutcome.BLOCKED,
                        cards_revealed=[],
                        coins_transferred=0,
                        description=f"{actor.display_name}'s {action.value} was blocked by {blocker.display_name} (claimed {block.block_with_role})"
                    )
        
        # No successful challenge or block - apply action effects
        return ActionResolutionService._apply_action_effects(
            session=session,
            actor=actor,
            action=action,
            target=target,
            upgrade=upgrade
        )
    
    @staticmethod
    def _resolve_challenge(
        session: GameSession,
        actor: Player,
        action: ToBeInitiated,
        challenger: Player,
        players_by_name: dict
    ) -> Tuple[bool, List[str]]:
        """
        Resolve a challenge to an action.
        
        Args:
            session: Game session
            actor: Player whose action was challenged
            action: The action that was challenged
            challenger: Player making the challenge
            players_by_name: All players by name
        
        Returns:
            Tuple of (challenge_succeeded, cards_revealed)
        """
        required_role = ACTION_ROLES.get(action)
        
        if required_role is None:
            # Action can't be challenged (income, foreign aid, coup)
            return False, []
        
        actor_cards = actor.card_types or []
        
        if required_role in actor_cards:
            # Actor has the card - challenge fails
            # Challenger loses influence
            revealed = ActionResolutionService._player_loses_influence(challenger, session.session_id)
            
            # Actor shows card and gets a new one
            ActionResolutionService._swap_revealed_card(actor, required_role, session.session_id)
            
            return False, revealed
        else:
            # Actor was bluffing - challenge succeeds
            # Actor loses influence
            revealed = ActionResolutionService._player_loses_influence(actor, session.session_id)
            return True, revealed
    
    @staticmethod
    def _player_loses_influence(player: Player, session_id: str) -> List[str]:
        """
        Make a player lose one influence (reveal a card).
        
        Returns list of revealed card names.
        """
        if not player.card_types:
            return []
        
        # Remove first card (in real game, player chooses)
        lost_card = player.card_types[0]
        player.card_types = player.card_types[1:]
        
        # Add to session's revealed cards
        session = GameSession.query.filter_by(session_id=session_id).first()
        if session:
            revealed = list(session.revealed_cards or [])
            revealed.append(lost_card)
            session.revealed_cards = revealed
        
        return [lost_card.value]
    
    @staticmethod
    def _swap_revealed_card(player: Player, revealed_card: CardType, session_id: str):
        """
        Swap a revealed card for a new one from the deck.
        
        Used when a player proves they have a card during a challenge.
        """
        # Remove the revealed card
        cards = list(player.card_types or [])
        if revealed_card in cards:
            cards.remove(revealed_card)
        
        # Draw a new card
        new_card = DeckService.draw_card(session_id)
        if new_card:
            cards.append(new_card)
        
        # Return the revealed card to deck
        DeckService.return_card(session_id, revealed_card)
        
        player.card_types = cards
    
    @staticmethod
    def _apply_action_effects(
        session: GameSession,
        actor: Player,
        action: ToBeInitiated,
        target: Optional[Player],
        upgrade: Optional[ToBeInitiatedUpgradeDetails]
    ) -> ActionResult:
        """Apply the effects of a successful action."""
        
        outcome = ResolutionOutcome.SUCCESS
        coins_transferred = 0
        cards_revealed = []
        description = ""
        
        if action == ToBeInitiated.ACT_INCOME:
            actor.coins += 1
            description = f"{actor.display_name} took income (+1 coin)"
        
        elif action == ToBeInitiated.ACT_FOREIGN_AID:
            actor.coins += 2
            description = f"{actor.display_name} took foreign aid (+2 coins)"
        
        elif action == ToBeInitiated.ACT_TAX:
            actor.coins += 3
            description = f"{actor.display_name} collected tax (+3 coins)"
        
        elif action == ToBeInitiated.ACT_STEAL:
            if target:
                steal_amount = min(2, target.coins)
                target.coins -= steal_amount
                actor.coins += steal_amount
                coins_transferred = steal_amount
                description = f"{actor.display_name} stole {steal_amount} coins from {target.display_name}"
            else:
                outcome = ResolutionOutcome.FAILED
                description = f"{actor.display_name}'s steal failed (no target)"
        
        elif action == ToBeInitiated.ACT_ASSASSINATION:
            actor.coins -= 3
            if target and target.card_types:
                # Determine which card to remove
                target_card = target.card_types[0]
                if upgrade and upgrade.assassination_priority:
                    priority = upgrade.assassination_priority
                    if priority in target.card_types:
                        target_card = priority
                
                revealed = ActionResolutionService._player_loses_influence(target, session.session_id)
                cards_revealed = revealed
                description = f"{actor.display_name} assassinated {target.display_name} (revealed {', '.join(revealed)})"
            else:
                outcome = ResolutionOutcome.FAILED
                description = f"{actor.display_name}'s assassination failed (no valid target)"
        
        elif action == ToBeInitiated.ACT_COUP:
            actor.coins -= 7
            if target and target.card_types:
                revealed = ActionResolutionService._player_loses_influence(target, session.session_id)
                cards_revealed = revealed
                description = f"{actor.display_name} couped {target.display_name} (revealed {', '.join(revealed)})"
            else:
                outcome = ResolutionOutcome.FAILED
                description = f"{actor.display_name}'s coup failed (no valid target)"
        
        elif action == ToBeInitiated.ACT_SWAP_INFLUENCE:
            # Draw 2 cards, return 2 cards
            new_cards = []
            for _ in range(2):
                card = DeckService.draw_card(session.session_id)
                if card:
                    new_cards.append(card)
            
            # For now, just add new cards (player should choose which to keep)
            # In full implementation, this would be a separate card selection phase
            current_cards = list(actor.card_types or [])
            actor.card_types = current_cards + new_cards
            
            description = f"{actor.display_name} swapped influence (drew {len(new_cards)} cards)"
            
            if upgrade and upgrade.trigger_identity_crisis and target:
                # Also swap target's cards
                target_new = []
                for _ in range(2):
                    card = DeckService.draw_card(session.session_id)
                    if card:
                        target_new.append(card)
                target_current = list(target.card_types or [])
                target.card_types = target_current + target_new
                description += f" and triggered identity crisis on {target.display_name}"
        
        return ActionResult(
            actor=actor.display_name,
            action=action,
            target=target.display_name if target else None,
            outcome=outcome,
            cards_revealed=cards_revealed,
            coins_transferred=coins_transferred,
            description=description
        )
    
    @staticmethod
    def _store_turn_result(session_id: str, turn_number: int, result: TurnResult):
        """Store turn result in database for history."""
        turn_result_orm = TurnResultORM(
            session_id=session_id,
            turn_number=turn_number,
            results_json={
                'action_results': [
                    {
                        'actor': ar.actor,
                        'action': ar.action.value,
                        'target': ar.target,
                        'outcome': ar.outcome.value,
                        'cards_revealed': ar.cards_revealed,
                        'coins_transferred': ar.coins_transferred,
                        'description': ar.description
                    }
                    for ar in result.action_results
                ]
            },
            summary=result.summary,
            players_eliminated=result.players_eliminated
        )
        db.session.add(turn_result_orm)


# Singleton instance
action_resolution_service = ActionResolutionService()
