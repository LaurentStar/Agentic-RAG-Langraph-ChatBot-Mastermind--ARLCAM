"""
REST API Models.

Flask-RESTX models for API request/response serialization.
"""

from app.models.rest_api_models.health_models import create_health_models
from app.models.rest_api_models.broadcast_models import create_broadcast_models
from app.models.rest_api_models.admin_models import create_admin_models

__all__ = [
    'create_health_models',
    'create_broadcast_models',
    'create_admin_models'
]
