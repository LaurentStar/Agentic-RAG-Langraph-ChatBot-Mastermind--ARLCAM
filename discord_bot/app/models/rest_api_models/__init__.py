"""
REST API Models.

Flask-RESTX models for request/response validation.
"""

from app.models.rest_api_models.health_models import register_health_models
from app.models.rest_api_models.broadcast_models import register_broadcast_models
from app.models.rest_api_models.admin_models import register_admin_models

__all__ = [
    'register_health_models',
    'register_broadcast_models',
    'register_admin_models'
]
