"""
Authentication Service.

JWT token validation for admin API endpoints.
Uses the same JWT secret as game_server for cross-service authentication.
"""

import os
import logging
from functools import wraps
from typing import Optional, Dict, Any, Tuple

import jwt
from flask import request, g

logger = logging.getLogger(__name__)


class AuthService:
    """
    Service for JWT-based authentication.
    
    Validates JWT tokens issued by game_server to authenticate
    admin users for Slack bot management operations.
    """
    
    # JWT configuration
    JWT_ALGORITHM = "HS256"
    
    @staticmethod
    def get_jwt_secret() -> str:
        """Get JWT secret at runtime to ensure env vars are loaded."""
        return os.getenv("JWT_SECRET_KEY", "dev-secret-change-me-in-production")
    
    @staticmethod
    def validate_token(token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Validate a JWT token.
        
        Args:
            token: JWT token string
        
        Returns:
            Tuple of (is_valid, payload, error_message)
        """
        if not token:
            return False, None, "No token provided"
        
        try:
            payload = jwt.decode(
                token,
                AuthService.get_jwt_secret(),
                algorithms=[AuthService.JWT_ALGORITHM]
            )
            
            return True, payload, None
            
        except jwt.ExpiredSignatureError:
            return False, None, "Token expired"
        except jwt.InvalidTokenError as e:
            return False, None, f"Invalid token: {str(e)}"
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return False, None, "Token validation failed"
    
    @staticmethod
    def is_admin(payload: Dict[str, Any]) -> bool:
        """
        Check if the token payload indicates admin privileges.
        
        Args:
            payload: Decoded JWT payload
        
        Returns:
            True if user is admin
        """
        # Check for player_type (game_server token structure)
        if payload.get("player_type") == "admin":
            return True
        
        # Check for admin flag
        if payload.get("is_admin"):
            return True
        
        roles = payload.get("roles", [])
        if "admin" in roles:
            return True
        
        # Check for specific admin claim
        if payload.get("admin"):
            return True
        
        return False
    
    @staticmethod
    def get_user_id(payload: Dict[str, Any]) -> Optional[str]:
        """
        Extract user ID from token payload.
        
        Args:
            payload: Decoded JWT payload
        
        Returns:
            User ID or None
        """
        return payload.get("sub") or payload.get("user_id") or payload.get("display_name")


def jwt_required(f):
    """
    Decorator for endpoints that require JWT authentication.
    
    Extracts token from Authorization header, validates it,
    and stores payload in Flask's g object.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Extract token from header
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            return {"error": "Authorization header required"}, 401
        
        # Expected format: "Bearer <token>"
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return {"error": "Invalid authorization header format"}, 401
        
        token = parts[1]
        
        # Validate token
        is_valid, payload, error = AuthService.validate_token(token)
        
        if not is_valid:
            return {"error": error}, 401
        
        # Store payload in Flask g object
        g.jwt_payload = payload
        g.user_id = AuthService.get_user_id(payload)
        
        return f(*args, **kwargs)
    
    return decorated


def admin_required(f):
    """
    Decorator for endpoints that require admin privileges.
    
    Must be used after @jwt_required.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        payload = getattr(g, 'jwt_payload', None)
        
        if not payload:
            return {"error": "Authentication required"}, 401
        
        if not AuthService.is_admin(payload):
            return {"error": "Admin privileges required"}, 403
        
        return f(*args, **kwargs)
    
    return decorated
