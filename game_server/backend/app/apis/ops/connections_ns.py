"""
Connections Namespace.

API endpoints for database and external service health checks.
This file handles ONLY routing - all business logic is in OpsConnectionsService.
"""

from flask_restx import Namespace, Resource

from app.services.auth_service import ops_key_required
from app.services.ops import OpsConnectionsService


connections_ns = Namespace('connections', description='Connection health checks')


@connections_ns.route('')
class Connections(Resource):
    """Check all connections."""
    
    @ops_key_required
    def get(self):
        """
        Check all connections.
        
        Returns health status for database and all external services.
        """
        return OpsConnectionsService.get_all_connections(), 200


@connections_ns.route('/postgres')
class PostgresConnection(Resource):
    """Check PostgreSQL connection."""
    
    @ops_key_required
    def get(self):
        """
        Check PostgreSQL database connection.
        
        Returns status, latency, and connection pool info.
        """
        return OpsConnectionsService.check_postgres(), 200


@connections_ns.route('/services')
class ExternalServices(Resource):
    """Check all external services."""
    
    @ops_key_required
    def get(self):
        """
        Check all external services.
        
        Returns health status for each configured service.
        """
        return OpsConnectionsService.check_external_services(), 200


@connections_ns.route('/services/<string:service_name>')
@connections_ns.param('service_name', 'The service name (lang_graph_server, discord_bot, slack_bot)')
class ExternalServiceByName(Resource):
    """Check a specific external service."""
    
    @ops_key_required
    def get(self, service_name):
        """
        Check a specific external service.
        
        Returns health status for the specified service.
        """
        result = OpsConnectionsService.check_service(service_name)
        
        if result.get('status') == 'unknown_service':
            return {'error': f'Unknown service: {service_name}'}, 404
        
        return result, 200

