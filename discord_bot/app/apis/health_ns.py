"""
Health Namespace.

Health and readiness check endpoints.
"""

from flask import current_app
from flask_restx import Namespace, Resource

from app.services.health_service import HealthService
from app.models.rest_api_models.health_models import register_health_models

health_ns = Namespace('health', description='Health and readiness checks')

# Register models with namespace
models = register_health_models(health_ns)


@health_ns.route('')
class Health(Resource):
    """Basic health check (liveness probe)."""
    
    @health_ns.response(200, 'OK', models['health_response'])
    def get(self):
        """
        Liveness probe.
        
        Returns OK if the server is running.
        Use for Kubernetes liveness probes.
        """
        return HealthService.check_health(), 200


@health_ns.route('/ready')
class Ready(Resource):
    """Readiness check."""
    
    @health_ns.response(200, 'Ready', models['readiness_response'])
    @health_ns.response(503, 'Not Ready', models['readiness_response'])
    def get(self):
        """
        Readiness probe.
        
        Checks if the bot is fully operational:
        - Bot connected to Discord
        - Bot is ready (logged in, caches populated)
        - Database connection working
        - Required cogs loaded
        
        Use for Kubernetes readiness probes.
        """
        bot = getattr(current_app, 'bot_instance', None)
        result = HealthService.check_readiness(bot, current_app)
        status = 200 if result['ready'] else 503
        
        return result, status
