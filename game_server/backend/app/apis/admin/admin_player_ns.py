"""
Admin Player Namespace.

Privileged player management operations.
"""

from flask import request
from flask_restx import Namespace, Resource

from app.constants import GamePrivilege, PlayerType, SocialMediaPlatform
from app.models.rest_api_models.player_models import create_player_models
from app.services.auth_service import admin_required, privilege_required
from app.services.player_service import PlayerService

admin_player_ns = Namespace('admin-players', description='Admin player management')

# Create models
models = create_player_models(admin_player_ns)


def _player_to_dict(player):
    """Convert Player object to response dict."""
    return {
        'display_name': player.display_name,
        'social_media_platform_display_name': player.social_media_platform_display_name,
        'social_media_platform': player.social_media_platform.value if player.social_media_platform else None,
        'player_type': player.player_type.value if player.player_type else None,
        'session_id': player.session_id,
        'coins': player.coins,
        'is_alive': player.is_alive,
        'game_privileges': [p.value for p in (player.game_privileges or [])]
    }


@admin_player_ns.route('')
class AdminPlayerList(Resource):
    """Admin player list endpoint."""
    
    @admin_player_ns.doc(params={
        'player_type': 'Filter by player type',
        'session_id': 'Filter by session',
        'is_alive': 'Filter by alive status'
    })
    @admin_player_ns.response(200, 'Success', models['player_list_response'])
    @admin_required
    def get(self):
        """List all players with full details (admin only)."""
        player_type = request.args.get('player_type')
        session_id = request.args.get('session_id')
        is_alive = request.args.get('is_alive')
        
        # Parse filters
        pt = PlayerType(player_type) if player_type else None
        alive = is_alive.lower() == 'true' if is_alive else None
        
        players = PlayerService.list_players(
            player_type=pt,
            session_id=session_id,
            is_alive=alive
        )
        
        return {
            'players': [_player_to_dict(p) for p in players],
            'total': len(players)
        }, 200


@admin_player_ns.route('/register/llm-agent')
class LLMAgentRegister(Resource):
    """LLM agent registration endpoint."""
    
    @admin_player_ns.expect(models['register_llm_request'])
    @admin_player_ns.response(201, 'Created', models['player_response'])
    @admin_player_ns.response(400, 'Bad request', models['error_response'])
    @privilege_required(GamePrivilege.MANAGE_CONFIG)
    def post(self):
        """Register a new LLM agent with profile (admin or MANAGE_CONFIG)."""
        data = request.get_json()
        
        try:
            platform = SocialMediaPlatform(data.get('social_media_platform', 'default'))
            
            player = PlayerService.register_llm_agent(
                display_name=data['display_name'],
                password=data['password'],
                social_media_platform_display_name=data.get('social_media_platform_display_name', data['display_name']),
                social_media_platform=platform,
                personality_type=data.get('personality_type', 'balanced'),
                modulators=data.get('modulators')
            )
            
            return _player_to_dict(player), 201
            
        except ValueError as e:
            return {'error': str(e)}, 400
        except KeyError as e:
            return {'error': f'Missing required field: {e}'}, 400


@admin_player_ns.route('/register/admin')
class AdminRegister(Resource):
    """Admin registration endpoint."""
    
    @admin_player_ns.expect(models['register_request'])
    @admin_player_ns.response(201, 'Created', models['player_response'])
    @admin_player_ns.response(400, 'Bad request', models['error_response'])
    @admin_required
    def post(self):
        """Register a new admin player (admin only)."""
        data = request.get_json()
        
        try:
            platform = SocialMediaPlatform(data.get('social_media_platform', 'default'))
            privileges = [GamePrivilege(p) for p in data.get('game_privileges', [])]
            
            player = PlayerService.register_player(
                display_name=data['display_name'],
                password=data['password'],
                social_media_platform_display_name=data.get('social_media_platform_display_name', data['display_name']),
                social_media_platform=platform,
                player_type=PlayerType.ADMIN,
                game_privileges=privileges
            )
            
            return _player_to_dict(player), 201
            
        except ValueError as e:
            return {'error': str(e)}, 400
        except KeyError as e:
            return {'error': f'Missing required field: {e}'}, 400


@admin_player_ns.route('/<string:display_name>')
@admin_player_ns.param('display_name', 'Player display name')
class AdminPlayerResource(Resource):
    """Admin player resource endpoint."""
    
    @admin_player_ns.expect(models['player_update_request'])
    @admin_player_ns.response(200, 'Success', models['player_response'])
    @admin_player_ns.response(404, 'Not found', models['error_response'])
    @admin_required
    def put(self, display_name):
        """Update any player's profile (admin only)."""
        data = request.get_json()
        
        try:
            # Parse privileges if provided
            if 'game_privileges' in data:
                data['game_privileges'] = [GamePrivilege(p) for p in data['game_privileges']]
            
            # Parse platform if provided
            if 'social_media_platform' in data:
                data['social_media_platform'] = SocialMediaPlatform(data['social_media_platform'])
            
            player = PlayerService.update_player(display_name, **data)
            return _player_to_dict(player), 200
            
        except ValueError as e:
            return {'error': str(e)}, 404
    
    @admin_player_ns.response(204, 'Deleted')
    @admin_player_ns.response(404, 'Not found', models['error_response'])
    @privilege_required(GamePrivilege.KICK_PLAYER)
    def delete(self, display_name):
        """Delete a player (admin or KICK_PLAYER)."""
        deleted = PlayerService.delete_player(display_name)
        
        if not deleted:
            return {'error': 'Player not found'}, 404
        
        return '', 204

