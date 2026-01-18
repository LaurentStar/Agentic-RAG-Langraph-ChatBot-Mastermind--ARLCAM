"""
Operations Connections Service.

Provides health checks for database and external service connections.
"""

import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import httpx


class OpsConnectionsService:
    """Service for connection health checks."""
    
    # External services to check (read from env vars)
    EXTERNAL_SERVICES = {
        "lang_graph_server": "LANG_GRAPH_SERVER_URL",
        "discord_bot": "DISCORD_BOT_URL",
        "slack_bot": "SLACK_BOT_URL",
    }
    
    @classmethod
    def get_all_connections(cls) -> Dict[str, Any]:
        """
        Check all connections (database and external services).
        
        Returns:
            Dict with postgres and external_services health
        """
        return {
            "postgres": cls.check_postgres(),
            "external_services": cls.check_external_services(),
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
        }
    
    @classmethod
    def check_postgres(cls) -> Dict[str, Any]:
        """
        Check PostgreSQL database connection.
        
        Returns:
            Dict with status, latency, and connection pool info
        """
        from app.extensions import db
        
        result = {
            "status": "disconnected",
            "latency_ms": None,
        }
        
        try:
            start = time.perf_counter()
            db.session.execute(db.text('SELECT 1'))
            end = time.perf_counter()
            
            result["status"] = "connected"
            result["latency_ms"] = round((end - start) * 1000, 2)
            
            # Try to get pool info if available
            engine = db.engine
            if hasattr(engine, 'pool'):
                pool = engine.pool
                result["pool_size"] = pool.size()
                result["pool_checked_out"] = pool.checkedout()
                result["pool_overflow"] = pool.overflow()
            
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
        
        return result
    
    @classmethod
    def check_external_services(cls) -> Dict[str, Dict[str, Any]]:
        """
        Check all configured external services.
        
        Returns:
            Dict mapping service name to health status
        """
        results = {}
        
        for service_name, env_var in cls.EXTERNAL_SERVICES.items():
            url = os.getenv(env_var)
            
            if not url:
                results[service_name] = {
                    "status": "not_configured",
                    "env_var": env_var
                }
                continue
            
            results[service_name] = cls._check_service(url, service_name)
        
        return results
    
    @classmethod
    def check_service(cls, service_name: str) -> Optional[Dict[str, Any]]:
        """
        Check a specific external service.
        
        Args:
            service_name: Name of the service to check
        
        Returns:
            Health status dict or None if service not configured
        """
        if service_name not in cls.EXTERNAL_SERVICES:
            return {"status": "unknown_service"}
        
        env_var = cls.EXTERNAL_SERVICES[service_name]
        url = os.getenv(env_var)
        
        if not url:
            return {
                "status": "not_configured",
                "env_var": env_var
            }
        
        return cls._check_service(url, service_name)
    
    @classmethod
    def _check_service(cls, base_url: str, service_name: str) -> Dict[str, Any]:
        """
        Check if a service is reachable.
        
        Args:
            base_url: Base URL of the service
            service_name: Name for logging
        
        Returns:
            Dict with status, latency, and any error
        """
        # Try common health endpoints
        health_paths = ["/health/liveness", "/health", "/"]
        
        result = {
            "url": base_url,
            "status": "unreachable",
            "latency_ms": None,
        }
        
        for path in health_paths:
            try:
                url = base_url.rstrip('/') + path
                start = time.perf_counter()
                
                response = httpx.get(url, timeout=5.0)
                
                end = time.perf_counter()
                
                if response.status_code < 500:
                    result["status"] = "reachable"
                    result["latency_ms"] = round((end - start) * 1000, 2)
                    result["health_endpoint"] = path
                    return result
                    
            except httpx.ConnectError:
                result["error"] = "Connection refused"
            except httpx.TimeoutException:
                result["error"] = "Connection timeout"
            except Exception as e:
                result["error"] = str(e)
        
        return result

