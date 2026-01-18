"""
Operations API Namespaces.

Developer-focused endpoints for debugging and monitoring.
These endpoints require Coup-Ops-Key authentication.

Namespaces:
- status_ns: System status, version, uptime, counts
- jobs_ns: Scheduled job introspection
- connections_ns: Database and external service health
"""

from app.apis.ops.status_ns import status_ns
from app.apis.ops.jobs_ns import jobs_ns
from app.apis.ops.connections_ns import connections_ns

__all__ = [
    "status_ns",
    "jobs_ns",
    "connections_ns",
]

