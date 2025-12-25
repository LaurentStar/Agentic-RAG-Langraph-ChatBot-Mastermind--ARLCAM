"""
Reactions Namespace.

Handles setting and viewing pending reactions.
"""

from flask import g, request
from flask_restx import Namespace, Resource

from app.models.rest_api_models.gameplay_models import create_gameplay_models
from app.services.auth_service import jwt_required
from app.services.gameplay_service import GameplayService

reactions_ns = Namespace('game-reactions', description='Game reaction operations')

# Create models
models = create_gameplay_models(reactions_ns)


@reactions_ns.route('/<string:session_id>')
@reactions_ns.param('session_id', 'Session UUID')
class SessionReactions(Resource):
    """Session reactions endpoint."""
    
    @reactions_ns.response(200, 'Success', models['reactions_response'])
    @jwt_required
    def get(self, session_id):
        """Get pending reactions and actions requiring reaction."""
        result = GameplayService.get_pending_reactions(session_id)
        
        if 'error' in result:
            return result, 404
        
        return result, 200
    
    @reactions_ns.expect(models['reaction_request'])
    @reactions_ns.response(200, 'Success', models['success_response'])
    @reactions_ns.response(400, 'Bad request', models['error_response'])
    @jwt_required
    def post(self, session_id):
        """Set reaction to another player's action."""
        session, player, error, code = GameplayService.get_session_and_player(
            session_id, g.current_player_name
        )
        if error:
            return error, code
        
        data = request.get_json()
        
        return GameplayService.set_reaction(
            session=session,
            player=player,
            reaction_type_str=data.get('reaction_type'),
            target_player=data.get('target_player'),
            block_with_role=data.get('block_with_role')
        )


@reactions_ns.route('/<string:session_id>/cards')
@reactions_ns.param('session_id', 'Session UUID')
class CardSelection(Resource):
    """Card selection endpoint."""
    
    @reactions_ns.expect(models['card_select_request'])
    @reactions_ns.response(200, 'Success', models['success_response'])
    @reactions_ns.response(400, 'Bad request', models['error_response'])
    @jwt_required
    def post(self, session_id):
        """Select cards for reveal or exchange."""
        session, player, error, code = GameplayService.get_session_and_player(
            session_id, g.current_player_name
        )
        if error:
            return error, code
        
        data = request.get_json()
        
        return GameplayService.select_cards(
            session=session,
            player=player,
            cards=data.get('cards', [])
        )

