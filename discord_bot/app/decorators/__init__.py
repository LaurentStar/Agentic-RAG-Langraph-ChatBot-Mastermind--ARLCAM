"""
Discord Bot Decorators.

Reusable decorators for Discord slash commands.
"""

from app.decorators.auth import requires_linked_account

__all__ = ['requires_linked_account']

