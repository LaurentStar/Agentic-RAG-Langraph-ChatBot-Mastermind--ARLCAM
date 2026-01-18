"""
Status Namespace.

API endpoints for system status and metrics.
This file handles ONLY routing - all business logic is in OpsStatusService.
"""

from flask_restx import Namespace, Resource

from app.services.auth_service import ops_key_required
from app.services.ops import OpsStatusService


status_ns = Namespace('status', description='System status and metrics')


@status_ns.route('')
class Status(Resource):
    """System status endpoint."""
    
    @ops_key_required
    def get(self):
        """
        Get full system status.
        
        Returns version, uptime, environment, and Python version.
        """
        return OpsStatusService.get_status(), 200


@status_ns.route('/summary')
class StatusSummary(Resource):
    """Quick summary with counts."""
    
    @ops_key_required
    def get(self):
        """
        Get quick summary with counts.
        
        Returns session, player, and job counts.
        """
        return OpsStatusService.get_summary(), 200

