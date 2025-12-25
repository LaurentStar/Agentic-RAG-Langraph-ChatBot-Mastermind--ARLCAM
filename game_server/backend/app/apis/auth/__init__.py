"""
Authentication API.

Handles login, token refresh, and OAuth2 authentication.
"""

from app.apis.auth.auth_ns import auth_ns
from app.apis.auth.oauth_ns import oauth_ns

__all__ = ["auth_ns", "oauth_ns"]

