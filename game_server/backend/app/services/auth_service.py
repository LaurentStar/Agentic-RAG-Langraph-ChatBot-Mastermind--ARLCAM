"""
Authentication Service.

Handles JWT token generation, validation, and password hashing.
"""

import os
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Optional, Tuple, Union
from uuid import UUID

import bcrypt
import jwt
from flask import current_app, g, request

from app.constants import PlayerType
from app.models.postgres_sql_db_models import UserAccount
from app.crud import UserAccountCRUD


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
    def authenticate(cls, user_name: str, password: str) -> Optional[UserAccount]:
        """
        Authenticate a user with username and password.
        
        Args:
            user_name: Login username
            password: Plain text password
        
        Returns:
            UserAccount if authentication successful, None otherwise
        """
        user = UserAccountCRUD.get_by_user_name(user_name)
        if not user or not user.password_hash:
            return None
        
        if not user.is_active:
            return None  # Account suspended/banned/deactivated
        
        if cls.verify_password(password, user.password_hash):
            # Update last login time
            UserAccountCRUD.update_last_login(user.user_id)
            return user
        
        return None
    
    @classmethod
    def create_access_token(cls, user: UserAccount) -> str:
        """
        Create a JWT access token for a user.
        
        Token includes:
        - sub: user_id (UUID) - immutable identifier
        - user_name: login identifier
        - display_name: public display name
        - player_type: human/llm_agent/admin
        - privileges: list of game privileges
        - token_version: for session invalidation
        """
        secret_key = current_app.config.get('JWT_SECRET_KEY', 'dev-secret-change-me')
        
        payload = {
            'sub': str(user.user_id),
            'user_name': user.user_name,
            'display_name': user.display_name,
            'player_type': user.player_type.value,
            'privileges': [p.value for p in (user.game_privileges or [])],
            'token_version': user.token_version,
            'iat': datetime.now(timezone.utc),
            'exp': datetime.now(timezone.utc) + timedelta(hours=cls.JWT_EXPIRY_HOURS),
            'type': 'access'
        }
        
        return jwt.encode(payload, secret_key, algorithm=cls.JWT_ALGORITHM)
    
    @classmethod
    def create_refresh_token(cls, user: UserAccount) -> str:
        """Create a JWT refresh token for a user."""
        secret_key = current_app.config.get('JWT_SECRET_KEY', 'dev-secret-change-me')
        
        payload = {
            'sub': str(user.user_id),
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
    def verify_access_token(cls, token: str) -> Optional[dict]:
        """
        Verify an access token and return the payload.
        
        Returns:
            Token payload dict if valid, None otherwise
        """
        is_valid, payload, _ = cls.verify_token(token, 'access')
        return payload if is_valid else None
    
    @classmethod
    def get_user_from_token(cls, token: str) -> Optional[UserAccount]:
        """
        Get user account from an access token.
        
        Returns:
            UserAccount if token is valid and user exists, None otherwise
        """
        payload = cls.verify_access_token(token)
        if not payload:
            return None
        
        user_id = payload.get('sub')
        if not user_id:
            return None
        
        try:
            return UserAccountCRUD.get_by_id(UUID(user_id))
        except (ValueError, TypeError):
            return None
    
    @classmethod
    def get_current_user_id(cls) -> Optional[UUID]:
        """Get the current user's UUID from the request context."""
        user_id_str = getattr(g, 'current_user_id', None)
        if user_id_str:
            try:
                return UUID(user_id_str)
            except (ValueError, TypeError):
                return None
        return None
    
    @classmethod
    def get_current_user_name(cls) -> Optional[str]:
        """Get the current user's username from the request context."""
        return getattr(g, 'current_user_name', None)
    
    @classmethod
    def get_current_display_name(cls) -> Optional[str]:
        """Get the current user's display name from the request context."""
        return getattr(g, 'current_display_name', None)
    
    @classmethod
    def get_current_player_type(cls) -> Optional[PlayerType]:
        """Get the current player's type from the request context."""
        player_type = getattr(g, 'current_player_type', None)
        if player_type:
            return PlayerType(player_type)
        return None
    
    # Legacy compatibility - will be deprecated
    @classmethod
    def get_current_player_name(cls) -> Optional[str]:
        """Legacy: Get display name. Use get_current_display_name instead."""
        return cls.get_current_display_name()


def jwt_required(f):
    """
    Decorator to require JWT authentication.
    
    Checks for token in order:
    1. Cookie 'access_token' (browser clients)
    2. Authorization header 'Bearer <token>' (service clients)
    
    Also validates token_version to support session invalidation.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # 1. Check cookie first (browser requests)
        token = request.cookies.get('access_token')
        
        # 2. Fall back to Authorization header (API/service calls)
        if not token:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
        
        if not token:
            return {'error': 'Missing authentication'}, 401
        
        is_valid, payload, error = AuthService.verify_token(token)
        
        if not is_valid:
            return {'error': error}, 401
        
        # Validate token version (for session invalidation)
        token_version = payload.get('token_version')
        if token_version is not None:
            user_id = payload.get('sub')
            try:
                user = UserAccountCRUD.get_by_id(UUID(user_id))
                if user and user.token_version != token_version:
                    return {'error': 'Session invalidated. Please log in again.'}, 401
            except (ValueError, TypeError):
                pass  # Let it proceed, user lookup will fail later if needed
        
        # Store user info in request context
        g.current_user_id = payload.get('sub')
        g.current_user_name = payload.get('user_name')
        g.current_display_name = payload.get('display_name')
        g.current_player_type = payload.get('player_type')
        g.current_player_privileges = payload.get('privileges', [])
        
        # Legacy compatibility
        g.current_player_name = payload.get('display_name')
        
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
