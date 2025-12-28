"""
Slack Bot APIs.

Flask-RESTX namespaces for REST endpoints.
"""

from app.apis.health_ns import health_ns
from app.apis.broadcast_ns import broadcast_ns
from app.apis.admin_ns import admin_ns

__all__ = ['health_ns', 'broadcast_ns', 'admin_ns']
