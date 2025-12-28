"""
Health API Namespace.

Health and readiness check endpoints.
"""

from flask import current_app
from flask_restx import Namespace, Resource

from app.services import HealthService
from app.models.rest_api_models import create_health_models

health_ns = Namespace('health', description='Health check operations')

# Create models
models = create_health_models(health_ns)


@health_ns.route('')
@health_ns.route('/')
class Health(Resource):
    """Health check endpoint."""
    
    @health_ns.doc('health_check')
    @health_ns.marshal_with(models['health_response'])
    def get(self):
        """
        Basic health check (liveness probe).
        
        Returns 200 if the service is running.
        """
        return HealthService.check_health()


@health_ns.route('/ready')
class Ready(Resource):
    """Readiness check endpoint."""
    
    @health_ns.doc('readiness_check')
    @health_ns.marshal_with(models['readiness_response'])
    def get(self):
        """
        Full readiness check.
        
        Checks bot connection, database, and listener registration.
        Returns 200 if all checks pass, 503 if any fail.
        """
        slack_bot = getattr(current_app, 'slack_bot', None)
        result = HealthService.check_readiness(slack_bot, current_app)
        
        if not result.get('ready'):
            return result, 503
        
        return result
