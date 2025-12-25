"""
Reaction Service.

Handles creating, retrieving, and managing player reactions to actions.
"""

from typing import List, Optional, Dict, Any

from app.constants import ReactionType, ToBeInitiated, BLOCK_ROLES, CardType
from app.extensions import db
from app.models.postgres_sql_db_models import GameSession, Player, Reaction


class ReactionService:
    """Service for managing player reactions."""
    
    @staticmethod
    def create_reaction(
        session_id: str,
        reactor_display_name: str,
        actor_display_name: str,
        target_action: ToBeInitiated,
        reaction_type: ReactionType,
        block_with_role: Optional[str] = None
    ) -> Reaction:
        """
        Create a new reaction to a pending action.
        
        Args:
            session_id: Game session ID
            reactor_display_name: Player making the reaction
            actor_display_name: Player whose action is being reacted to
            target_action: The action being reacted to
            reaction_type: Type of reaction (challenge, block, pass)
            block_with_role: Role claimed for blocking (if blocking)
        
        Returns:
            Created Reaction object
        
        Raises:
            ValueError: If reaction is invalid
        """
        session = GameSession.query.filter_by(session_id=session_id).first()
        if not session:
            raise ValueError("Session not found")
        
        # Validate block role if blocking
        if reaction_type == ReactionType.BLOCK:
            if not block_with_role:
                raise ValueError("Must specify role when blocking")
            
            # Check if the role can block this action
            valid_blockers = BLOCK_ROLES.get(target_action, [])
            try:
                claimed_card = CardType(block_with_role.lower())
                if claimed_card not in valid_blockers:
                    raise ValueError(f"{block_with_role} cannot block {target_action.value}")
            except ValueError:
                raise ValueError(f"Invalid role: {block_with_role}")
        
        # Check for existing reaction from this player to this action
        existing = Reaction.query.filter_by(
            session_id=session_id,
            turn_number=session.turn_number,
            reactor_display_name=reactor_display_name,
            actor_display_name=actor_display_name,
            target_action=target_action,
            is_resolved=False
        ).first()
        
        if existing:
            # Update existing reaction
            existing.reaction_type = reaction_type
            existing.block_with_role = block_with_role
            db.session.commit()
            return existing
        
        # Create new reaction
        reaction = Reaction(
            session_id=session_id,
            turn_number=session.turn_number,
            reactor_display_name=reactor_display_name,
            actor_display_name=actor_display_name,
            target_action=target_action,
            reaction_type=reaction_type,
            block_with_role=block_with_role,
            is_locked=False,
            is_resolved=False
        )
        
        db.session.add(reaction)
        db.session.commit()
        return reaction
    
    @staticmethod
    def get_reactions_for_action(
        session_id: str,
        turn_number: int,
        actor_display_name: str,
        target_action: ToBeInitiated
    ) -> List[Reaction]:
        """Get all reactions to a specific action."""
        return Reaction.query.filter_by(
            session_id=session_id,
            turn_number=turn_number,
            actor_display_name=actor_display_name,
            target_action=target_action,
            is_resolved=False
        ).all()
    
    @staticmethod
    def get_reactions_by_reactor(
        session_id: str,
        turn_number: int,
        reactor_display_name: str
    ) -> List[Reaction]:
        """Get all reactions made by a specific player this turn."""
        return Reaction.query.filter_by(
            session_id=session_id,
            turn_number=turn_number,
            reactor_display_name=reactor_display_name,
            is_resolved=False
        ).all()
    
    @staticmethod
    def get_all_reactions_for_turn(session_id: str, turn_number: int) -> List[Reaction]:
        """Get all reactions for a turn."""
        return Reaction.query.filter_by(
            session_id=session_id,
            turn_number=turn_number,
            is_resolved=False
        ).all()
    
    @staticmethod
    def lock_reactions_for_turn(session_id: str, turn_number: int) -> int:
        """
        Lock all reactions for a turn (during LOCKOUT2).
        
        Returns:
            Number of reactions locked
        """
        reactions = Reaction.query.filter_by(
            session_id=session_id,
            turn_number=turn_number,
            is_locked=False
        ).all()
        
        for reaction in reactions:
            reaction.is_locked = True
        
        db.session.commit()
        return len(reactions)
    
    @staticmethod
    def mark_reactions_resolved(session_id: str, turn_number: int) -> int:
        """
        Mark all reactions for a turn as resolved.
        
        Returns:
            Number of reactions marked
        """
        reactions = Reaction.query.filter_by(
            session_id=session_id,
            turn_number=turn_number,
            is_resolved=False
        ).all()
        
        for reaction in reactions:
            reaction.is_resolved = True
        
        db.session.commit()
        return len(reactions)
    
    @staticmethod
    def get_actions_requiring_reaction(session_id: str) -> List[Dict[str, Any]]:
        """
        Get all pending actions that can be reacted to.
        
        Returns list of actions with their details.
        """
        session = GameSession.query.filter_by(session_id=session_id).first()
        if not session:
            return []
        
        players = Player.query.filter_by(session_id=session_id).all()
        actions = []
        
        for player in players:
            if not player.is_alive:
                continue
            
            if not player.to_be_initiated:
                continue
            
            for action in player.to_be_initiated:
                if action == ToBeInitiated.NO_EVENT:
                    continue
                
                # Check if action is reactable
                is_challengeable = action in [
                    ToBeInitiated.ACT_TAX,
                    ToBeInitiated.ACT_ASSASSINATION,
                    ToBeInitiated.ACT_STEAL,
                    ToBeInitiated.ACT_SWAP_INFLUENCE,
                ]
                is_blockable = action in BLOCK_ROLES
                
                if is_challengeable or is_blockable:
                    actions.append({
                        'actor_display_name': player.display_name,
                        'action': action.value,
                        'target_display_name': player.target_display_name,
                        'is_challengeable': is_challengeable,
                        'is_blockable': is_blockable,
                        'valid_block_roles': [r.value for r in BLOCK_ROLES.get(action, [])]
                    })
        
        return actions
    
    @staticmethod
    def has_challenge(session_id: str, turn_number: int, actor_display_name: str) -> bool:
        """Check if an actor's action has been challenged."""
        challenge = Reaction.query.filter_by(
            session_id=session_id,
            turn_number=turn_number,
            actor_display_name=actor_display_name,
            reaction_type=ReactionType.CHALLENGE,
            is_resolved=False
        ).first()
        return challenge is not None
    
    @staticmethod
    def get_blocks(
        session_id: str,
        turn_number: int,
        actor_display_name: str
    ) -> List[Reaction]:
        """Get all block reactions to an actor's action."""
        return Reaction.query.filter_by(
            session_id=session_id,
            turn_number=turn_number,
            actor_display_name=actor_display_name,
            reaction_type=ReactionType.BLOCK,
            is_resolved=False
        ).all()


# Singleton instance
reaction_service = ReactionService()

