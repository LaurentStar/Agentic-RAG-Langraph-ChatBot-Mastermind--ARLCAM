"""
State Namespace.

Handles game state retrieval.
"""

from flask import g
from flask_restx import Namespace, Resource

from app.models.rest_api_models.gameplay_models import create_gameplay_models
from app.services.auth_service import jwt_required
from app.services.gameplay_service import GameplayService

state_ns = Namespace('game-state', description='Game state operations')

# Create models
models = create_gameplay_models(state_ns)


@state_ns.route('/<string:session_id>')
@state_ns.param('session_id', 'Session UUID')
class GameState(Resource):
    """Game state endpoint."""
    
    @state_ns.response(200, 'Success', models['game_state_response'])
    @jwt_required
    def get(self, session_id):
        """Get current game state."""
        result = GameplayService.get_game_state(session_id, g.current_player_name)
        
        if 'error' in result:
            return result, 404
        
        return result, 200

