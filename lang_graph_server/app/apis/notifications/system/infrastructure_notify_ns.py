"""
Infrastructure Health and Readiness Endpoints.

Kubernetes-style probes for container orchestration:
- /health (liveness): Is the process alive?
- /ready (readiness): Is the service ready to accept traffic?

This file handles ONLY routing - all business logic is in infrastructure_service.py.
"""

from flask import jsonify, make_response
from flask_restx import Namespace, Resource

from app.services.infrastructure_service import InfrastructureService


#-------------#
# Name Spaces #
#-------------#
infrastructure_ns = Namespace(
    "infrastructure",
    description="Infrastructure health and readiness checks for container orchestration",
)


#-----------#
# Resources #
#-----------#
class HealthCheck(Resource):
    def get(self):
        """
        Basic liveness probe.
        
        Returns 200 if the server process is running.
        Kubernetes will restart the pod if this fails.
        """
        payload = InfrastructureService.get_health()
        return make_response(jsonify(payload), 200)


class ReadinessCheck(Resource):
    def get(self):
        """
        Readiness probe with dependency checks.
        
        Returns 200 if all critical dependencies are available.
        Returns 503 if any critical dependency fails.
        Kubernetes will remove pod from load balancer if this fails.
        """
        payload, status_code = InfrastructureService.get_readiness()
        return make_response(jsonify(payload), status_code)


class GameServerConnectivityCheck(Resource):
    def get(self):
        """
        Test connectivity to game_server.
        
        Attempts to reach game_server's health endpoint.
        Returns connection status and response time.
        """
        import time
        import httpx
        from app.extensions import game_server_client_factory
        
        result = {
            "game_server_url": game_server_client_factory._base_url,
            "connection": False,
            "game_server_status": None,
            "response_time_ms": None,
            "error": None
        }
        
        try:
            start = time.time()
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{game_server_client_factory._base_url}/health/liveness")
                result["response_time_ms"] = round((time.time() - start) * 1000, 2)
                
                if response.status_code == 200:
                    result["connection"] = True
                    result["game_server_status"] = response.json()
                else:
                    result["error"] = f"HTTP {response.status_code}"
                    
        except httpx.ConnectError as e:
            result["error"] = f"Connection refused: {e}"
        except httpx.TimeoutException:
            result["error"] = "Connection timeout"
        except Exception as e:
            result["error"] = str(e)
        
        status_code = 200 if result["connection"] else 503
        return make_response(jsonify(result), status_code)


# ---------------------- Building Resources ---------------------- #
infrastructure_ns.add_resource(HealthCheck, "/health")
infrastructure_ns.add_resource(ReadinessCheck, "/ready")
infrastructure_ns.add_resource(GameServerConnectivityCheck, "/game-server-check")
