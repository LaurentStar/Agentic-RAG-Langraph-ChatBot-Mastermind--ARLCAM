"""
Authentication Namespace.

Handles user login, token refresh, and authentication.
"""

import os
from uuid import UUID

from flask import make_response, request
from flask_restx import Namespace, Resource

from app.models.rest_api_models.auth_models import create_auth_models
from app.services.auth_service import AuthService
from app.crud import UserAccountCRUD

auth_ns = Namespace('auth', description='Authentication operations')

# Create models
models = create_auth_models(auth_ns)


@auth_ns.route('/login')
class Login(Resource):
    """Login endpoint."""
    
    @auth_ns.expect(models['login_request'])
    @auth_ns.response(200, 'Success', models['user_info'])
    @auth_ns.response(401, 'Invalid credentials', models['error_response'])
    def post(self):
        """
        Authenticate and receive user info.
        
        Tokens are set as HTTP-only cookies for browser clients.
        For service-to-service calls, use /auth/oauth/token-by-provider.
        """
        data = request.get_json()
        
        user_name = data.get('user_name')
        password = data.get('password')
        
        if not user_name or not password:
            return {'error': 'Missing user_name or password'}, 400
        
        user = AuthService.authenticate(user_name, password)
        
        if not user:
            return {'error': 'Invalid credentials'}, 401
        
        access_token = AuthService.create_access_token(user)
        refresh_token = AuthService.create_refresh_token(user)
        
        # Create response with user info only (no tokens in body)
        response_data = {
            'user_id': str(user.user_id),
            'user_name': user.user_name,
            'display_name': user.display_name,
            'player_type': user.player_type.value,
        }
        response = make_response(response_data, 200)
        
        # Set HTTP-only cookies
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


@auth_ns.route('/session')
class Session(Resource):
    """Session validation endpoint."""
    
    @auth_ns.response(200, 'Authenticated', models['user_info'])
    @auth_ns.response(401, 'Not authenticated', models['error_response'])
    def get(self):
        """
        Get current session info from cookie.
        
        Used by frontend to validate session on app mount.
        Returns user info if cookie contains valid JWT.
        """
        token = request.cookies.get('access_token')
        if not token:
            return {'error': 'Not authenticated'}, 401
        
        user = AuthService.get_user_from_token(token)
        if not user:
            return {'error': 'Invalid or expired session'}, 401
        
        return {
            'user_id': str(user.user_id),
            'user_name': user.user_name,
            'display_name': user.display_name,
            'player_type': user.player_type.value,
        }, 200


@auth_ns.route('/logout')
class Logout(Resource):
    """Logout endpoint."""
    
    @auth_ns.response(200, 'Logged out', models['logout_response'])
    def post(self):
        """
        Clear authentication cookies.
        
        Clears both access_token and refresh_token cookies.
        """
        response = make_response({'message': 'Logged out successfully'}, 200)
        
        # Clear cookies by setting them to expire immediately
        response.set_cookie('access_token', '', expires=0, path='/')
        response.set_cookie('refresh_token', '', expires=0, path='/auth')
        
        return response


@auth_ns.route('/refresh')
class Refresh(Resource):
    """Token refresh endpoint."""
    
    @auth_ns.expect(models['refresh_request'], validate=False)  # Optional body
    @auth_ns.response(200, 'Success', models['refresh_response'])
    @auth_ns.response(401, 'Invalid token', models['error_response'])
    def post(self):
        """
        Refresh an expired access token.
        
        Accepts refresh_token from:
        1. Cookie (browser clients) - preferred
        2. JSON body (service clients) - backward compatible
        """
        # Try cookie first, then JSON body
        refresh_token = request.cookies.get('refresh_token')
        from_cookie = refresh_token is not None
        
        if not refresh_token:
            data = request.get_json() or {}
            refresh_token = data.get('refresh_token')
        
        if not refresh_token:
            return {'error': 'Missing refresh_token'}, 400
        
        is_valid, payload, error = AuthService.verify_token(refresh_token, token_type='refresh')
        
        if not is_valid:
            return {'error': error}, 401
        
        # Get user and create new access token
        user_id = payload.get('sub')
        
        try:
            user = UserAccountCRUD.get_by_id(UUID(user_id))
        except (ValueError, TypeError):
            return {'error': 'Invalid user ID in token'}, 401
        
        if not user:
            return {'error': 'User not found'}, 401
        
        if not user.is_active:
            return {'error': 'Account is not active'}, 401
        
        access_token = AuthService.create_access_token(user)
        
        # If request came from browser (has cookie), set new access_token cookie
        if from_cookie:
            is_production = os.getenv('ENVIRONMENT', 'local') != 'local'
            response = make_response({
                'expires_in': AuthService.JWT_EXPIRY_HOURS * 3600
            }, 200)
            response.set_cookie(
                'access_token',
                access_token,
                httponly=True,
                secure=is_production,
                samesite='Lax',
                max_age=AuthService.JWT_EXPIRY_HOURS * 3600,
                path='/'
            )
            return response
        
        # Backward compatible: return token in body for service clients
        return {
            'access_token': access_token,
            'expires_in': AuthService.JWT_EXPIRY_HOURS * 3600
        }, 200
