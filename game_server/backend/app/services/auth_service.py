"""
Authentication Service.

Handles JWT token generation, validation, and password hashing.
"""

import os
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Optional, Tuple

import bcrypt
import jwt
from flask import current_app, g, request

from app.constants import PlayerType
from app.models.postgres_sql_db_models import Player


class AuthService:
    """Service for authentication and authorization."""
    
    # JWT Configuration
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRY_HOURS = 24
    JWT_REFRESH_EXPIRY_DAYS = 7
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(
            password.encode('utf-8'),
            password_hash.encode('utf-8')
        )
    
    @classmethod
    def create_access_token(cls, player: Player) -> str:
        """Create a JWT access token for a player."""
        secret_key = current_app.config.get('JWT_SECRET_KEY', 'dev-secret-change-me')
        
        payload = {
            'sub': player.display_name,
            'player_type': player.player_type.value,
            'privileges': [p.value for p in (player.game_privileges or [])],
            'iat': datetime.now(timezone.utc),
            'exp': datetime.now(timezone.utc) + timedelta(hours=cls.JWT_EXPIRY_HOURS),
            'type': 'access'
        }
        
        return jwt.encode(payload, secret_key, algorithm=cls.JWT_ALGORITHM)
    
    @classmethod
    def create_refresh_token(cls, player: Player) -> str:
        """Create a JWT refresh token for a player."""
        secret_key = current_app.config.get('JWT_SECRET_KEY', 'dev-secret-change-me')
        
        payload = {
            'sub': player.display_name,
            'iat': datetime.now(timezone.utc),
            'exp': datetime.now(timezone.utc) + timedelta(days=cls.JWT_REFRESH_EXPIRY_DAYS),
            'type': 'refresh'
        }
        
        return jwt.encode(payload, secret_key, algorithm=cls.JWT_ALGORITHM)
    
    @classmethod
    def verify_token(cls, token: str, token_type: str = 'access') -> Tuple[bool, Optional[dict], Optional[str]]:
        """
        Verify a JWT token.
        
        Returns:
            Tuple of (is_valid, payload, error_message)
        """
        secret_key = current_app.config.get('JWT_SECRET_KEY', 'dev-secret-change-me')
        
        try:
            payload = jwt.decode(token, secret_key, algorithms=[cls.JWT_ALGORITHM])
            
            if payload.get('type') != token_type:
                return False, None, f"Invalid token type. Expected {token_type}."
            
            return True, payload, None
            
        except jwt.ExpiredSignatureError:
            return False, None, "Token has expired."
        except jwt.InvalidTokenError as e:
            return False, None, f"Invalid token: {str(e)}"
    
    @classmethod
    def get_current_player_name(cls) -> Optional[str]:
        """Get the current player's display name from the request context."""
        return getattr(g, 'current_player_name', None)
    
    @classmethod
    def get_current_player_type(cls) -> Optional[PlayerType]:
        """Get the current player's type from the request context."""
        player_type = getattr(g, 'current_player_type', None)
        if player_type:
            return PlayerType(player_type)
        return None


def jwt_required(f):
    """Decorator to require JWT authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return {'error': 'Missing or invalid Authorization header'}, 401
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        is_valid, payload, error = AuthService.verify_token(token)
        
        if not is_valid:
            return {'error': error}, 401
        
        # Store player info in request context
        g.current_player_name = payload.get('sub')
        g.current_player_type = payload.get('player_type')
        g.current_player_privileges = payload.get('privileges', [])
        
        return f(*args, **kwargs)
    
    return decorated


def admin_required(f):
    """Decorator to require admin privileges."""
    @wraps(f)
    @jwt_required
    def decorated(*args, **kwargs):
        if g.current_player_type != PlayerType.ADMIN.value:
            return {'error': 'Admin privileges required'}, 403
        return f(*args, **kwargs)
    
    return decorated


def privilege_required(privilege: str):
    """Decorator factory to require a specific privilege."""
    def decorator(f):
        @wraps(f)
        @jwt_required
        def decorated(*args, **kwargs):
            # Admins have all privileges
            if g.current_player_type == PlayerType.ADMIN.value:
                return f(*args, **kwargs)
            
            # Check for specific privilege
            if privilege not in g.current_player_privileges:
                return {'error': f'Missing required privilege: {privilege}'}, 403
            
            return f(*args, **kwargs)
        
        return decorated
    return decorator


# =============================================
# Service-to-Service Authentication
# =============================================

# API key for trusted services (Discord bot, Slack bot, etc.)
SERVICE_API_KEY = os.getenv("SERVICE_API_KEY", "dev-service-key")


def service_key_required(f):
    """
    Decorator to require valid Coup-Service-Key header.
    
    Used for service-to-service communication (e.g., Discord bot -> Game Server).
    This authenticates the calling service, not the end user.
    User identity should be provided in the request payload for moderation tracking.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('Coup-Service-Key')
        
        if not api_key or api_key != SERVICE_API_KEY:
            return {'error': 'Invalid or missing service key'}, 401
        
        return f(*args, **kwargs)
    
    return decorated


# =============================================
# Developer Operations Authentication
# =============================================

# API key for developers (human operators, not machines)
OPS_API_KEY = os.getenv("OPS_API_KEY", "dev-ops-key")


def ops_key_required(f):
    """
    Decorator to require valid Coup-Ops-Key header.
    
    Used for developer operations (debugging, monitoring, introspection).
    This authenticates human developers, not automated services.
    
    Different from service_key_required:
    - Coup-Service-Key: Machine-to-machine (bots calling APIs)
    - Coup-Ops-Key: Human-to-machine (developers debugging)
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('Coup-Ops-Key')
        
        if not api_key or api_key != OPS_API_KEY:
            return {'error': 'Invalid or missing ops key'}, 401
        
        return f(*args, **kwargs)
    
    return decorated

