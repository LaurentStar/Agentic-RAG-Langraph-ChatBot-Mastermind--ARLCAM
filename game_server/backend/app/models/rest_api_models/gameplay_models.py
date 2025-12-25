"""
Gameplay API Models.

Flask-RESTX models for gameplay endpoints (actions, reactions, state).
"""

from flask_restx import fields


def create_gameplay_models(api):
    """Create and return gameplay-related API models."""
    
    # Action models
    action_request = api.model('ActionRequest', {
        'action': fields.String(required=True, description='Action type (income, foreign_aid, coup, tax, steal, assassinate, swap)'),
        'target_display_name': fields.String(description='Target player (required for coup, steal, assassinate)'),
        'claimed_role': fields.String(description='Role claimed for action'),
        'upgrade_enabled': fields.Boolean(description='Use upgrade', default=False)
    })
    
    pending_action = api.model('PendingAction', {
        'player_display_name': fields.String(description='Player who set the action'),
        'action': fields.String(description='Action type'),
        'target_display_name': fields.String(description='Target player'),
        'claimed_role': fields.String(description='Claimed role'),
        'is_upgraded': fields.Boolean(description='Whether action is upgraded')
    })
    
    actions_response = api.model('ActionsResponse', {
        'pending_actions': fields.List(fields.Nested(pending_action)),
        'current_phase': fields.String(description='Current game phase'),
        'phase_end_time': fields.DateTime(description='When phase ends')
    })
    
    # Reaction models
    reaction_request = api.model('ReactionRequest', {
        'target_player': fields.String(required=True, description='Player whose action to react to'),
        'reaction_type': fields.String(required=True, description='Reaction type (challenge, block, pass)'),
        'block_with_role': fields.String(description='Role claimed for blocking')
    })
    
    pending_reaction = api.model('PendingReaction', {
        'reactor_display_name': fields.String(description='Player reacting'),
        'target_player': fields.String(description='Player being reacted to'),
        'reaction_type': fields.String(description='Type of reaction'),
        'block_role': fields.String(description='Role claimed for block')
    })
    
    reactions_response = api.model('ReactionsResponse', {
        'pending_reactions': fields.List(fields.Nested(pending_reaction)),
        'actions_requiring_reaction': fields.List(fields.Nested(pending_action))
    })
    
    # Card selection models
    card_select_request = api.model('CardSelectRequest', {
        'cards': fields.List(fields.String, required=True, description='Cards to select/reveal')
    })
    
    # Game state models
    player_state = api.model('PlayerState', {
        'display_name': fields.String(description='Player name'),
        'coins': fields.Integer(description='Coin count'),
        'cards_count': fields.Integer(description='Number of cards (influence)'),
        'is_alive': fields.Boolean(description='Whether player is alive'),
        'pending_action': fields.String(description='Current pending action'),
        'target': fields.String(description='Action target')
    })
    
    game_state_response = api.model('GameStateResponse', {
        'session_id': fields.String(description='Session ID'),
        'current_phase': fields.String(description='Current phase'),
        'phase_end_time': fields.DateTime(description='Phase end time'),
        'turn_number': fields.Integer(description='Current turn'),
        'turn_limit': fields.Integer(description='Max turns'),
        'players': fields.List(fields.Nested(player_state)),
        'revealed_cards': fields.List(fields.String, description='Dead/revealed cards'),
        'my_cards': fields.List(fields.String, description='Your cards (only for authenticated player)')
    })
    
    error_response = api.model('GameplayErrorResponse', {
        'error': fields.String(description='Error message')
    })
    
    success_response = api.model('GameplaySuccessResponse', {
        'message': fields.String(description='Success message')
    })
    
    return {
        'action_request': action_request,
        'pending_action': pending_action,
        'actions_response': actions_response,
        'reaction_request': reaction_request,
        'pending_reaction': pending_reaction,
        'reactions_response': reactions_response,
        'card_select_request': card_select_request,
        'player_state': player_state,
        'game_state_response': game_state_response,
        'error_response': error_response,
        'success_response': success_response
    }

