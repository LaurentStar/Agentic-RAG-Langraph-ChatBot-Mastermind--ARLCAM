"""
Admin API Namespace.

Admin operations for the Slack bot.
"""

from flask import current_app
from flask_restx import Namespace, Resource

from app.services import TokenCacheService, jwt_required, admin_required
from app.models.rest_api_models import create_admin_models

admin_ns = Namespace('admin', description='Admin operations')

# Create models
models = create_admin_models(admin_ns)


@admin_ns.route('/bot-info')
class BotInfo(Resource):
    """Bot information endpoint."""
    
    @admin_ns.doc('get_bot_info', security='Bearer')
    @admin_ns.marshal_with(models['bot_info_response'])
    @admin_ns.response(401, 'Unauthorized', models['error_response'])
    @jwt_required
    @admin_required
    def get(self):
        """
        Get bot information.
        
        Returns the bot's connection status and identity.
        Requires admin privileges.
        """
        slack_bot = getattr(current_app, 'slack_bot', None)
        if not slack_bot:
            return {'connected': False}
        
        return slack_bot.get_bot_info()


@admin_ns.route('/token-cache/stats')
class TokenCacheStats(Resource):
    """Token cache statistics endpoint."""
    
    @admin_ns.doc('get_token_cache_stats', security='Bearer')
    @admin_ns.marshal_with(models['token_cache_stats'])
    @admin_ns.response(401, 'Unauthorized', models['error_response'])
    @admin_ns.response(403, 'Forbidden', models['error_response'])
    @jwt_required
    @admin_required
    def get(self):
        """
        Get token cache statistics.
        
        Returns counts of cached, valid, and expired tokens.
        Requires admin privileges.
        """
        return TokenCacheService.get_cache_stats()


@admin_ns.route('/token-cache/cleanup')
class TokenCacheCleanup(Resource):
    """Token cache cleanup endpoint."""
    
    @admin_ns.doc('cleanup_token_cache', security='Bearer')
    @admin_ns.marshal_with(models['cleanup_response'])
    @admin_ns.response(401, 'Unauthorized', models['error_response'])
    @admin_ns.response(403, 'Forbidden', models['error_response'])
    @jwt_required
    @admin_required
    def post(self):
        """
        Clean up expired token cache entries.
        
        Removes all expired tokens from the database.
        Requires admin privileges.
        """
        deleted = TokenCacheService.cleanup_expired()
        return {
            'deleted': deleted,
            'message': f'Cleaned up {deleted} expired entries'
        }
