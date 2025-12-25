"""
Player Namespace.

Self-service player registration and profile management.
"""

import os
from flask import g, request
from flask_restx import Namespace, Resource

from app.constants import GamePrivilege, PlayerType, SocialMediaPlatform
from app.models.rest_api_models.player_models import create_player_models
from app.services.auth_service import jwt_required
from app.services.player_service import PlayerService

player_ns = Namespace('players', description='Player self-service operations')

# Create models
models = create_player_models(player_ns)

# Bootstrap secret for first admin creation (from env var)
BOOTSTRAP_SECRET = os.environ.get('ADMIN_BOOTSTRAP_SECRET', 'change-me-in-production')


def _player_to_dict(player, include_private=False):
    """Convert Player object to response dict."""
    result = {
        'display_name': player.display_name,
        'social_media_platform_display_name': player.social_media_platform_display_name,
        'social_media_platform': player.social_media_platform.value if player.social_media_platform else None,
        'player_type': player.player_type.value if player.player_type else None,
        'session_id': player.session_id,
        'coins': player.coins,
        'is_alive': player.is_alive,
    }
    
    if include_private:
        result['game_privileges'] = [p.value for p in (player.game_privileges or [])]
    
    return result


@player_ns.route('/register')
class PlayerRegister(Resource):
    """Player registration endpoint."""
    
    @player_ns.expect(models['register_request'])
    @player_ns.response(201, 'Created', models['player_response'])
    @player_ns.response(400, 'Bad request', models['error_response'])
    @player_ns.response(403, 'Forbidden', models['error_response'])
    def post(self):
        """
        Register a new player (human, llm_agent, or admin).
        
        Player types:
        - **human** (default): No special requirements
        - **llm_agent**: Optional modulators and personality_type
        - **admin**: Requires bootstrap_secret for first admin, or existing admin auth
        
        For admin registration without auth, provide:
        ```json
        {
            "player_type": "admin",
            "bootstrap_secret": "your-secret-from-env"
        }
        ```
        """
        data = request.get_json()
        
        try:
            platform = SocialMediaPlatform(data.get('social_media_platform', 'default'))
            player_type_str = data.get('player_type', 'human').lower()
            
            # Parse player type
            try:
                player_type = PlayerType(player_type_str)
            except ValueError:
                return {'error': f"Invalid player_type: {player_type_str}. Must be: human, llm_agent, or admin"}, 400
            
            # Handle different player types
            if player_type == PlayerType.ADMIN:
                # Admin registration requires bootstrap secret OR existing admin auth
                bootstrap_secret = data.get('bootstrap_secret')
                
                if bootstrap_secret != BOOTSTRAP_SECRET:
                    return {'error': 'Invalid or missing bootstrap_secret for admin registration'}, 403
                
                # Create admin with all privileges
                privileges = [GamePrivilege(p) for p in data.get('game_privileges', [])]
                if not privileges:
                    # Default: give all privileges to bootstrapped admin
                    privileges = list(GamePrivilege)
                
                player = PlayerService.register_player(
                    display_name=data['display_name'],
                    password=data['password'],
                    social_media_platform_display_name=data.get('social_media_platform_display_name', data['display_name']),
                    social_media_platform=platform,
                    player_type=PlayerType.ADMIN,
                    game_privileges=privileges
                )
                
            elif player_type == PlayerType.LLM_AGENT:
                # LLM agent registration with optional profile
                player = PlayerService.register_llm_agent(
                    display_name=data['display_name'],
                    password=data['password'],
                    social_media_platform_display_name=data.get('social_media_platform_display_name', data['display_name']),
                    social_media_platform=platform,
                    personality_type=data.get('personality_type', 'balanced'),
                    modulators=data.get('modulators')
                )
                
            else:
                # Human player registration (default)
                player = PlayerService.register_player(
                    display_name=data['display_name'],
                    password=data['password'],
                    social_media_platform_display_name=data.get('social_media_platform_display_name', data['display_name']),
                    social_media_platform=platform,
                    player_type=PlayerType.HUMAN,
                    game_privileges=[]
                )
            
            return _player_to_dict(player, include_private=True), 201
            
        except ValueError as e:
            return {'error': str(e)}, 400
        except KeyError as e:
            return {'error': f'Missing required field: {e}'}, 400


@player_ns.route('/me')
class PlayerMe(Resource):
    """Current player profile endpoint."""
    
    @player_ns.response(200, 'Success', models['player_response'])
    @player_ns.response(404, 'Not found', models['error_response'])
    @jwt_required
    def get(self):
        """Get current player's profile."""
        player = PlayerService.get_player(g.current_player_name)
        
        if not player:
            return {'error': 'Player not found'}, 404
        
        return _player_to_dict(player, include_private=True), 200
    
    @player_ns.expect(models['player_update_request'])
    @player_ns.response(200, 'Success', models['player_response'])
    @player_ns.response(404, 'Not found', models['error_response'])
    @jwt_required
    def put(self):
        """Update current player's profile."""
        data = request.get_json()
        
        try:
            # Parse platform if provided
            if 'social_media_platform' in data:
                data['social_media_platform'] = SocialMediaPlatform(data['social_media_platform'])
            
            # Only allow updating certain fields for self-service
            allowed_fields = ['social_media_platform_display_name', 'social_media_platform', 'password']
            filtered_data = {k: v for k, v in data.items() if k in allowed_fields}
            
            player = PlayerService.update_player(g.current_player_name, **filtered_data)
            return _player_to_dict(player, include_private=True), 200
            
        except ValueError as e:
            return {'error': str(e)}, 400


@player_ns.route('/<string:display_name>')
@player_ns.param('display_name', 'Player display name')
class PlayerResource(Resource):
    """Public player profile endpoint."""
    
    @player_ns.response(200, 'Success', models['player_response'])
    @player_ns.response(404, 'Not found', models['error_response'])
    @jwt_required
    def get(self, display_name):
        """Get player's public profile by display name."""
        player = PlayerService.get_player(display_name)
        
        if not player:
            return {'error': 'Player not found'}, 404
        
        # Return public info only
        return _player_to_dict(player, include_private=False), 200

