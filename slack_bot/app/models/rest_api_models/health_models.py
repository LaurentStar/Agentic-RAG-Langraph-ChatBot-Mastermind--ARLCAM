"""
Health API Models.

Flask-RESTX models for health check endpoints.
"""

from flask_restx import fields


def create_health_models(api):
    """Create and return health-related models."""
    
    health_response = api.model('HealthResponse', {
        'status': fields.String(description='Health status', example='ok'),
        'service': fields.String(description='Service name', example='slack_bot')
    })
    
    readiness_response = api.model('ReadinessResponse', {
        'ready': fields.Boolean(description='Overall readiness status'),
        'checks': fields.Raw(description='Individual check results'),
        'details': fields.Raw(description='Detailed check information')
    })
    
    return {
        'health_response': health_response,
        'readiness_response': readiness_response
    }
