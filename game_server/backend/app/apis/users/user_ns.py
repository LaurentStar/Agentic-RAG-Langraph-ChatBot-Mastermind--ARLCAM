"""
User Namespace.

User account registration and management.
"""

import os
from uuid import UUID

from flask import g, make_response, request
from flask_restx import Namespace, Resource

from app.constants import GamePrivilege, PlayerType, SocialMediaPlatform
from app.models.rest_api_models.player_models import create_player_models
from app.services.auth_service import AuthService, jwt_required
from app.services.user_account_service import UserAccountService

user_ns = Namespace('users', description='User account management')

# Create models (reusing player models for now)
models = create_player_models(user_ns)

# Bootstrap secret for first admin creation (from env var)
BOOTSTRAP_SECRET = os.environ.get('ADMIN_BOOTSTRAP_SECRET', 'change-me-in-production')


def _user_to_dict(user, include_private=False):
    """Convert UserAccount to response dict."""
    result = {
        'user_id': str(user.user_id),
        'user_name': user.user_name,
        'display_name': user.display_name,
        'social_media_platform_display_name': user.social_media_platform_display_name,
        'social_media_platforms': [p.value for p in (user.social_media_platforms or [])],
        'preferred_social_media_platform': user.preferred_social_media_platform.value if user.preferred_social_media_platform else None,
        'player_type': user.player_type.value if user.player_type else None,
    }
    
    if include_private:
        result['email'] = user.email
        result['email_verified'] = user.email_verified
        result['account_status'] = user.account_status
        result['game_privileges'] = [p.value for p in (user.game_privileges or [])]
        result['created_at'] = user.created_at.isoformat() if user.created_at else None
    
    return result


@user_ns.route('')
class UserRegister(Resource):
    """User registration endpoint."""
    
    @user_ns.expect(models['register_request'])
    @user_ns.response(201, 'Created', models['user_account_response'])
    @user_ns.response(400, 'Bad request', models['error_response'])
    @user_ns.response(403, 'Forbidden', models['error_response'])
    def post(self):
        """
        Register a new user account.
        
        Creates an account and sets HTTP-only authentication cookies.
        
        User types:
        - **human** (default): No special requirements
        - **llm_agent**: Optional modulators and personality_type
        - **admin**: Requires bootstrap_secret for first admin
        
        For admin registration, provide:
        ```json
        {
            "user_name": "admin_login",
            "display_name": "Admin Display Name",
            "player_type": "admin",
            "bootstrap_secret": "your-secret-from-env"
        }
        ```
        """
        data = request.get_json()
        
        try:
            platform = SocialMediaPlatform(data.get('platform', 'default'))
            player_type_str = data.get('player_type', 'human').lower()
            
            # Parse player type
            try:
                player_type = PlayerType(player_type_str)
            except ValueError:
                return {'error': f"Invalid player_type: {player_type_str}. Must be: human, llm_agent, or admin"}, 400
            
            # Get identity fields
            user_name = data.get('user_name')
            display_name = data.get('display_name')
            password = data.get('password')
            email = data.get('email')
            
            if not user_name:
                return {'error': 'Missing required field: user_name'}, 400
            if not display_name:
                return {'error': 'Missing required field: display_name'}, 400
            if not password:
                return {'error': 'Missing required field: password'}, 400
            
            # Handle different player types
            if player_type == PlayerType.ADMIN:
                # Admin registration requires bootstrap secret
                bootstrap_secret = data.get('bootstrap_secret')
                
                if bootstrap_secret != BOOTSTRAP_SECRET:
                    return {'error': 'Invalid or missing bootstrap_secret for admin registration'}, 403
                
                # Create admin with all privileges
                privileges = [GamePrivilege(p) for p in data.get('game_privileges', [])]
                if not privileges:
                    # Default: give all privileges to bootstrapped admin
                    privileges = list(GamePrivilege)
                
                user = UserAccountService.register(
                    user_name=user_name,
                    display_name=display_name,
                    password=password,
                    email=email,
                    platform_display_name=data.get('social_media_platform_display_name', display_name),
                    platform=platform,
                    player_type=PlayerType.ADMIN,
                    game_privileges=privileges
                )
                
            elif player_type == PlayerType.LLM_AGENT:
                # LLM agent registration with optional profile
                user = UserAccountService.register_agent(
                    user_name=user_name,
                    display_name=display_name,
                    password=password,
                    platform=platform,
                    personality_type=data.get('personality_type', 'balanced'),
                    modulators=data.get('modulators')
                )
                
            else:
                # Human player registration (default)
                user = UserAccountService.register(
                    user_name=user_name,
                    display_name=display_name,
                    password=password,
                    email=email,
                    platform_display_name=data.get('social_media_platform_display_name', display_name),
                    platform=platform,
                    player_type=PlayerType.HUMAN,
                    game_privileges=[]
                )
            
            # Create tokens for immediate login
            access_token = AuthService.create_access_token(user)
            refresh_token = AuthService.create_refresh_token(user)
            
            # Build response with user info (no tokens in body)
            response_data = _user_to_dict(user, include_private=True)
            response = make_response(response_data, 201)
            
            # Set HTTP-only cookies (same pattern as /auth/login)
            is_production = os.getenv('ENVIRONMENT', 'local') != 'local'
            
            response.set_cookie(
                'access_token',
                access_token,
                httponly=True,
                secure=is_production,
                samesite='Lax',
                max_age=AuthService.JWT_EXPIRY_HOURS * 3600,
                path='/'
            )
            response.set_cookie(
                'refresh_token',
                refresh_token,
                httponly=True,
                secure=is_production,
                samesite='Lax',
                max_age=AuthService.JWT_REFRESH_EXPIRY_DAYS * 86400,
                path='/auth'  # Only sent to /auth/* endpoints
            )
            
            return response
            
        except ValueError as e:
            return {'error': str(e)}, 400
        except KeyError as e:
            return {'error': f'Missing required field: {e}'}, 400


@user_ns.route('/me')
class UserMe(Resource):
    """Current user account endpoint."""
    
    @user_ns.response(200, 'Success', models['user_account_response'])
    @user_ns.response(404, 'Not found', models['error_response'])
    @jwt_required
    def get(self):
        """Get current user's account info."""
        user_id = UUID(g.current_user_id)
        user = UserAccountService.get_by_id(user_id)
        
        if not user:
            return {'error': 'User not found'}, 404
        
        return _user_to_dict(user, include_private=True), 200
    
    @user_ns.expect(models['player_update_request'])
    @user_ns.response(200, 'Success', models['user_account_response'])
    @user_ns.response(400, 'Bad request', models['error_response'])
    @user_ns.response(404, 'Not found', models['error_response'])
    @jwt_required
    def put(self):
        """Update current user's account info."""
        data = request.get_json()
        user_id = UUID(g.current_user_id)
        
        try:
            # Parse platform if provided
            preferred_platform = None
            if 'preferred_social_media_platform' in data:
                preferred_platform = SocialMediaPlatform(data['preferred_social_media_platform'])
            
            user = UserAccountService.update_profile(
                user_id=user_id,
                display_name=data.get('display_name'),
                email=data.get('email'),
                preferred_platform=preferred_platform
            )
            
            return _user_to_dict(user, include_private=True), 200
            
        except ValueError as e:
            return {'error': str(e)}, 400


@user_ns.route('/<string:identifier>')
@user_ns.param('identifier', 'User name or display name')
class UserResource(Resource):
    """Public user info endpoint."""
    
    @user_ns.response(200, 'Success', models['user_account_response'])
    @user_ns.response(404, 'Not found', models['error_response'])
    @jwt_required
    def get(self, identifier):
        """Get user's public info by user_name or display_name."""
        # Try user_name first, then display_name
        user = UserAccountService.get_by_user_name(identifier)
        if not user:
            user = UserAccountService.get_by_display_name(identifier)
        
        if not user:
            return {'error': 'User not found'}, 404
        
        # Return public info only (no private fields)
        return _user_to_dict(user, include_private=False), 200
