"""
Authentication API Models.

Flask-RESTX models for authentication endpoints.
"""

from flask_restx import fields


def create_auth_models(api):
    """Create and return auth-related API models."""
    
    login_request = api.model('LoginRequest', {
        'display_name': fields.String(required=True, description='Player display name'),
        'password': fields.String(required=True, description='Player password')
    })
    
    login_response = api.model('LoginResponse', {
        'access_token': fields.String(description='JWT access token'),
        'refresh_token': fields.String(description='JWT refresh token'),
        'player_type': fields.String(description='Type of player'),
        'display_name': fields.String(description='Player display name'),
        'expires_in': fields.Integer(description='Token expiry in seconds')
    })
    
    refresh_request = api.model('RefreshRequest', {
        'refresh_token': fields.String(required=True, description='JWT refresh token')
    })
    
    refresh_response = api.model('RefreshResponse', {
        'access_token': fields.String(description='New JWT access token'),
        'expires_in': fields.Integer(description='Token expiry in seconds')
    })
    
    error_response = api.model('ErrorResponse', {
        'error': fields.String(description='Error message')
    })
    
    return {
        'login_request': login_request,
        'login_response': login_response,
        'refresh_request': refresh_request,
        'refresh_response': refresh_response,
        'error_response': error_response
    }

