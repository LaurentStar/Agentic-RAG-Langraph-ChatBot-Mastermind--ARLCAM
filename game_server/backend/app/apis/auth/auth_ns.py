"""
Authentication Namespace.

Handles user login, token refresh, and authentication.
"""

from flask import request
from flask_restx import Namespace, Resource

from app.models.rest_api_models.auth_models import create_auth_models
from app.services.auth_service import AuthService
from app.services.player_service import PlayerService

auth_ns = Namespace('auth', description='Authentication operations')

# Create models
models = create_auth_models(auth_ns)


@auth_ns.route('/login')
class Login(Resource):
    """Login endpoint."""
    
    @auth_ns.expect(models['login_request'])
    @auth_ns.response(200, 'Success', models['login_response'])
    @auth_ns.response(401, 'Invalid credentials', models['error_response'])
    def post(self):
        """Authenticate and receive JWT tokens."""
        data = request.get_json()
        
        display_name = data.get('display_name')
        password = data.get('password')
        
        if not display_name or not password:
            return {'error': 'Missing display_name or password'}, 400
        
        player = PlayerService.authenticate(display_name, password)
        
        if not player:
            return {'error': 'Invalid credentials'}, 401
        
        access_token = AuthService.create_access_token(player)
        refresh_token = AuthService.create_refresh_token(player)
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'player_type': player.player_type.value,
            'display_name': player.display_name,
            'expires_in': AuthService.JWT_EXPIRY_HOURS * 3600
        }, 200


@auth_ns.route('/refresh')
class Refresh(Resource):
    """Token refresh endpoint."""
    
    @auth_ns.expect(models['refresh_request'])
    @auth_ns.response(200, 'Success', models['refresh_response'])
    @auth_ns.response(401, 'Invalid token', models['error_response'])
    def post(self):
        """Refresh an expired access token."""
        data = request.get_json()
        
        refresh_token = data.get('refresh_token')
        
        if not refresh_token:
            return {'error': 'Missing refresh_token'}, 400
        
        is_valid, payload, error = AuthService.verify_token(refresh_token, token_type='refresh')
        
        if not is_valid:
            return {'error': error}, 401
        
        # Get player and create new access token
        player = PlayerService.get_player(payload.get('sub'))
        
        if not player:
            return {'error': 'Player not found'}, 401
        
        access_token = AuthService.create_access_token(player)
        
        return {
            'access_token': access_token,
            'expires_in': AuthService.JWT_EXPIRY_HOURS * 3600
        }, 200

