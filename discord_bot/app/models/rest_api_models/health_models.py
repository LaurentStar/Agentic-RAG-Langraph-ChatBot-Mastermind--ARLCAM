"""
Health API Models.

Flask-RESTX models for health check endpoints.
"""

from flask_restx import fields


def register_health_models(api):
    """
    Register health-related models with the API.
    
    Args:
        api: Flask-RESTX Api or Namespace instance
    
    Returns:
        Dict of registered models
    """
    health_response = api.model('HealthResponse', {
        'status': fields.String(
            description='Health status',
            example='ok'
        ),
        'service': fields.String(
            description='Service name',
            example='discord_bot'
        )
    })
    
    readiness_check = api.model('ReadinessCheck', {
        'bot_connected': fields.Boolean(description='Bot instance exists'),
        'bot_ready': fields.Boolean(description='Bot is ready'),
        'database': fields.Boolean(description='Database connection OK'),
        'cogs_loaded': fields.Boolean(description='Required cogs loaded')
    })
    
    readiness_response = api.model('ReadinessResponse', {
        'ready': fields.Boolean(description='Overall readiness status'),
        'checks': fields.Nested(
            readiness_check, 
            description='Individual check results'
        ),
        'details': fields.Raw(description='Detailed check information')
    })
    
    return {
        'health_response': health_response,
        'readiness_check': readiness_check,
        'readiness_response': readiness_response
    }

