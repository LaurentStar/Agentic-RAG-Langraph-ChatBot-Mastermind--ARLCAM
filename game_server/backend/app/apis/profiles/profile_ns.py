"""
Profile Namespace.

Player game profiles and statistics.
"""

from uuid import UUID

from flask import g, request
from flask_restx import Namespace, Resource

from app.models.rest_api_models.player_models import create_player_models
from app.services.auth_service import jwt_required
from app.services.profile_service import ProfileService

profile_ns = Namespace('profiles', description='Player game profiles and statistics')

# Create models (reusing player models for now)
models = create_player_models(profile_ns)


def _profile_to_dict(profile):
    """Convert PlayerProfile to response dict."""
    return {
        'user_id': str(profile.user_id),
        'avatar_url': profile.avatar_url,
        'bio': profile.bio,
        'games_played': profile.games_played,
        'games_won': profile.games_won,
        'games_lost': profile.games_lost,
        'games_abandoned': profile.games_abandoned,
        'win_rate': round(profile.win_rate, 2),
        'rank': profile.rank,
        'elo': profile.elo,
        'level': profile.level,
        'xp': profile.xp,
    }


@profile_ns.route('/me')
class ProfileMe(Resource):
    """Current user's profile endpoint."""
    
    @profile_ns.response(200, 'Success', models['player_profile_response'])
    @profile_ns.response(404, 'Not found', models['error_response'])
    @jwt_required
    def get(self):
        """Get current user's game profile and statistics."""
        user_id = UUID(g.current_user_id)
        profile = ProfileService.get_by_user_id(user_id)
        
        if not profile:
            return {'error': 'Profile not found'}, 404
        
        return _profile_to_dict(profile), 200
    
    @profile_ns.expect(models['player_update_request'])
    @profile_ns.response(200, 'Success', models['player_profile_response'])
    @profile_ns.response(400, 'Bad request', models['error_response'])
    @profile_ns.response(404, 'Not found', models['error_response'])
    @jwt_required
    def put(self):
        """Update current user's profile (avatar, bio)."""
        data = request.get_json()
        user_id = UUID(g.current_user_id)
        
        try:
            profile = ProfileService.update_profile(
                user_id=user_id,
                avatar_url=data.get('avatar_url'),
                bio=data.get('bio')
            )
            
            return _profile_to_dict(profile), 200
            
        except ValueError as e:
            return {'error': str(e)}, 400


@profile_ns.route('/<string:identifier>')
@profile_ns.param('identifier', 'User name or display name')
class ProfileResource(Resource):
    """Public profile endpoint."""
    
    @profile_ns.response(200, 'Success', models['player_profile_response'])
    @profile_ns.response(404, 'Not found', models['error_response'])
    @jwt_required
    def get(self, identifier):
        """Get player's public game profile and statistics."""
        profile = ProfileService.get_by_identifier(identifier)
        
        if not profile:
            return {'error': 'Profile not found'}, 404
        
        return _profile_to_dict(profile), 200
