"""
Admin API Models.

Flask-RESTX models for admin endpoints.
"""

from flask_restx import fields


def create_admin_models(api):
    """Create and return admin-related models."""
    
    token_cache_stats = api.model('TokenCacheStats', {
        'total_cached': fields.Integer(description='Total cached tokens'),
        'valid_tokens': fields.Integer(description='Valid (non-expired) tokens'),
        'expired_tokens': fields.Integer(description='Expired tokens')
    })
    
    cleanup_response = api.model('CleanupResponse', {
        'deleted': fields.Integer(description='Number of entries deleted'),
        'message': fields.String(description='Status message')
    })
    
    bot_info_response = api.model('BotInfoResponse', {
        'connected': fields.Boolean(description='Whether bot is connected'),
        'user': fields.String(description='Bot username'),
        'user_id': fields.String(description='Bot user ID'),
        'team': fields.String(description='Workspace name'),
        'team_id': fields.String(description='Workspace ID')
    })
    
    error_response = api.model('AdminError', {
        'error': fields.String(description='Error message')
    })
    
    return {
        'token_cache_stats': token_cache_stats,
        'cleanup_response': cleanup_response,
        'bot_info_response': bot_info_response,
        'error_response': error_response
    }
