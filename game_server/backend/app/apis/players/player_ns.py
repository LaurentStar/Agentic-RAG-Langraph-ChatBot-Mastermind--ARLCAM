"""
Player Namespace.

DEPRECATED: All endpoints have moved to /users and /profiles namespaces.
This namespace only contains 301 redirects for backward compatibility.
"""

from flask_restx import Namespace, Resource

from app.models.rest_api_models.player_models import create_player_models

player_ns = Namespace('players', description='DEPRECATED - use /users and /profiles')

# Create models (still needed for Swagger docs)
models = create_player_models(player_ns)


@player_ns.route('/register')
class PlayerRegister(Resource):
    """DEPRECATED: Player registration endpoint. Use POST /users instead."""
    
    @player_ns.response(301, 'Moved Permanently')
    def post(self):
        """
        DEPRECATED: Use POST /users instead.
        
        This endpoint has been moved. Update your client.
        """
        from flask import make_response
        response = make_response({'error': 'Endpoint moved to POST /users'}, 301)
        response.headers['Location'] = '/users'
        return response


@player_ns.route('/me')
class PlayerMe(Resource):
    """DEPRECATED: Use /users/me instead."""
    
    @player_ns.response(301, 'Moved Permanently')
    def get(self):
        """
        DEPRECATED: Use GET /users/me instead.
        
        This endpoint has been moved. Update your client.
        """
        from flask import make_response
        response = make_response({'error': 'Endpoint moved to GET /users/me'}, 301)
        response.headers['Location'] = '/users/me'
        return response
    
    @player_ns.response(301, 'Moved Permanently')
    def put(self):
        """
        DEPRECATED: Use PUT /users/me instead.
        
        This endpoint has been moved. Update your client.
        """
        from flask import make_response
        response = make_response({'error': 'Endpoint moved to PUT /users/me'}, 301)
        response.headers['Location'] = '/users/me'
        return response


@player_ns.route('/me/stats')
class PlayerStats(Resource):
    """DEPRECATED: Use /profiles/me instead."""
    
    @player_ns.response(301, 'Moved Permanently')
    def get(self):
        """
        DEPRECATED: Use GET /profiles/me instead.
        
        This endpoint has been moved. Update your client.
        """
        from flask import make_response
        response = make_response({'error': 'Endpoint moved to GET /profiles/me'}, 301)
        response.headers['Location'] = '/profiles/me'
        return response


@player_ns.route('/<string:identifier>')
@player_ns.param('identifier', 'User name or display name')
class PlayerResource(Resource):
    """DEPRECATED: Use /users/{id} instead."""
    
    @player_ns.response(301, 'Moved Permanently')
    def get(self, identifier):
        """
        DEPRECATED: Use GET /users/{id} instead.
        
        This endpoint has been moved. Update your client.
        """
        from flask import make_response
        response = make_response({'error': f'Endpoint moved to GET /users/{identifier}'}, 301)
        response.headers['Location'] = f'/users/{identifier}'
        return response


@player_ns.route('/<string:identifier>/stats')
@player_ns.param('identifier', 'User name or display name')
class PlayerStatsPublic(Resource):
    """DEPRECATED: Use /profiles/{id} instead."""
    
    @player_ns.response(301, 'Moved Permanently')
    def get(self, identifier):
        """
        DEPRECATED: Use GET /profiles/{id} instead.
        
        This endpoint has been moved. Update your client.
        """
        from flask import make_response
        response = make_response({'error': f'Endpoint moved to GET /profiles/{identifier}'}, 301)
        response.headers['Location'] = f'/profiles/{identifier}'
        return response
