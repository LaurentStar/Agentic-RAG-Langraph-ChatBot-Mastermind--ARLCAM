"""
Agents module for Coup LLM players.

This module contains:
- BaseCoupAgent: Base class with shared functionality for all Coup agents
- AgentRegistry: Manager for multiple agent instances per game

Global agent_registry instance is declared in app/extensions.py

Note: Uses lazy imports to avoid circular dependencies.
Import directly from submodules when needed:
    from app.agents.base_coup_agent import BaseCoupAgent
    from app.agents.agent_registry import AgentRegistry
"""

__all__ = ["BaseCoupAgent", "AgentRegistry"]


def __getattr__(name):
    """Lazy import to avoid circular dependencies."""
    if name == "BaseCoupAgent":
        from app.agents.base_coup_agent import BaseCoupAgent
        return BaseCoupAgent
    elif name == "AgentRegistry":
        from app.agents.agent_registry import AgentRegistry
        return AgentRegistry
    
    raise AttributeError(f"module 'app.agents' has no attribute '{name}'")
