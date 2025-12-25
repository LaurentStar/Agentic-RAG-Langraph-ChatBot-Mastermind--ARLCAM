"""
Actions Namespace.

Handles setting and viewing pending actions.
"""

from flask import g, request
from flask_restx import Namespace, Resource

from app.models.rest_api_models.gameplay_models import create_gameplay_models
from app.services.auth_service import jwt_required
from app.services.gameplay_service import GameplayService

actions_ns = Namespace('game-actions', description='Game action operations')

# Create models
models = create_gameplay_models(actions_ns)


@actions_ns.route('/<string:session_id>')
@actions_ns.param('session_id', 'Session UUID')
class SessionActions(Resource):
    """Session actions endpoint."""
    
    @actions_ns.response(200, 'Success', models['actions_response'])
    @jwt_required
    def get(self, session_id):
        """Get all visible pending actions."""
        result = GameplayService.get_pending_actions(session_id)
        
        if 'error' in result:
            return result, 404
        
        return result, 200
    
    @actions_ns.expect(models['action_request'])
    @actions_ns.response(200, 'Success', models['success_response'])
    @actions_ns.response(400, 'Bad request', models['error_response'])
    @jwt_required
    def post(self, session_id):
        """Set or update pending action."""
        session, player, error, code = GameplayService.get_session_and_player(
            session_id, g.current_player_name
        )
        if error:
            return error, code
        
        data = request.get_json()
        
        return GameplayService.set_action(
            session=session,
            player=player,
            action_str=data.get('action'),
            target_display_name=data.get('target_display_name'),
            claimed_role=data.get('claimed_role'),
            upgrade_enabled=data.get('upgrade_enabled', False)
        )

