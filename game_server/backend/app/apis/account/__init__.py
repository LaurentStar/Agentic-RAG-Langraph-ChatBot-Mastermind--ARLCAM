"""
Account APIs.

Endpoints for managing user accounts:
- link_ns: Account linking across OAuth providers
- identity_ns: OAuth identity management
"""

from app.apis.account.link_ns import link_ns
from app.apis.account.identity_ns import identity_ns

__all__ = [
    "link_ns",
    "identity_ns",
]

