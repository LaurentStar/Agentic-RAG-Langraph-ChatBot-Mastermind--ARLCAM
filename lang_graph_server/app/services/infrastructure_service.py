"""
Infrastructure Service.

Provides health and readiness check logic for the application.
Used by infrastructure endpoints for Kubernetes-style probes.
"""

from datetime import datetime
from typing import Dict, List, Tuple


class InfrastructureService:
    """
    Service for infrastructure health and readiness checks.
    
    Checks are categorized as:
    - Critical: Service cannot function without these
    - Important: Service can function but with reduced capability
    """
    
    CRITICAL_CHECKS = ["database", "event_router_workflow", "checkpointer"]
    
    @staticmethod
    def get_health() -> Dict:
        """
        Get basic liveness status.
        
        Returns:
            Health status dict
        """
        return {
            "status": "ok",
            "service": "lang_graph_server",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    
    @staticmethod
    def get_readiness() -> Tuple[Dict, int]:
        """
        Get readiness status with all dependency checks.
        
        Returns:
            Tuple of (response dict, HTTP status code)
        """
        checks, failed = InfrastructureService._run_all_checks()
        
        # Determine if critical checks failed
        critical_failed = [f for f in failed if f in InfrastructureService.CRITICAL_CHECKS]
        all_ready = len(critical_failed) == 0
        
        response = {
            "status": "ready" if all_ready else "not_ready",
            "service": "lang_graph_server",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        
        if failed:
            response["failed"] = failed
            response["critical_failed"] = critical_failed
        
        status_code = 200 if all_ready else 503
        return response, status_code
    
    @staticmethod
    def _run_all_checks() -> Tuple[Dict[str, bool], List[str]]:
        """
        Run all readiness checks.
        
        Returns:
            Tuple of (checks dict, list of failed check names)
        """
        checks = {}
        failed = []
        
        check_functions = [
            ("database", InfrastructureService._check_database),
            ("event_router_workflow", InfrastructureService._check_event_router_workflow),
            ("checkpointer", InfrastructureService._check_checkpointer),
            ("chat_workflow", InfrastructureService._check_chat_workflow),
            ("broadcast_workflow", InfrastructureService._check_broadcast_workflow),
            ("coup_agent_workflow", InfrastructureService._check_coup_agent_workflow),
            ("agent_registry", InfrastructureService._check_agent_registry),
            ("llm_configured", InfrastructureService._check_llm_configured),
        ]
        
        for name, check_fn in check_functions:
            checks[name] = check_fn()
            if not checks[name]:
                failed.append(name)
        
        return checks, failed
    
    # =============================================
    # Individual Check Methods
    # =============================================
    
    @staticmethod
    def _check_database() -> bool:
        """Check if database connection is available."""
        try:
            from app.extensions import db_connection
            return db_connection.test_connection()
        except Exception:
            return False
    
    @staticmethod
    def _check_event_router_workflow() -> bool:
        """Check if event router workflow is loaded."""
        try:
            from app.extensions import lang_graph_app
            return lang_graph_app.event_router_wf is not None
        except Exception:
            return False
    
    @staticmethod
    def _check_checkpointer() -> bool:
        """Check if LangGraph checkpointer is initialized."""
        try:
            from app.extensions import langgraph_checkpointer
            return langgraph_checkpointer.get_checkpointer() is not None
        except Exception:
            return False
    
    @staticmethod
    def _check_chat_workflow() -> bool:
        """Check if chat reasoning workflow is loaded."""
        try:
            from app.extensions import lang_graph_app
            return lang_graph_app.chat_reasoning_wf is not None
        except Exception:
            return False
    
    @staticmethod
    def _check_broadcast_workflow() -> bool:
        """Check if broadcast commentary workflow is loaded."""
        try:
            from app.extensions import lang_graph_app
            return lang_graph_app.broadcast_commentary_wf is not None
        except Exception:
            return False
    
    @staticmethod
    def _check_coup_agent_workflow() -> bool:
        """Check if coup agent workflow is loaded."""
        try:
            from app.extensions import lang_graph_app
            return lang_graph_app.coup_agent_wf is not None
        except Exception:
            return False
    
    @staticmethod
    def _check_agent_registry() -> bool:
        """Check if agent registry is available."""
        try:
            from app.extensions import agent_registry
            stats = agent_registry.get_stats()
            return stats is not None
        except Exception:
            return False
    
    @staticmethod
    def _check_llm_configured() -> bool:
        """Check if LLM is configured."""
        try:
            from app.extensions import LoadedLLMs
            return LoadedLLMs.gpt_llm is not None
        except Exception:
            return False

