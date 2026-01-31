"""
OAuth Identity CRUD Operations.

Data access layer for oauth_identity table.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from app.crud.base import BaseCRUD
from app.models.postgres_sql_db_models import OAuthIdentity
from app.extensions import db


class OAuthIdentityCRUD(BaseCRUD[OAuthIdentity]):
    """CRUD operations for OAuthIdentity."""
    
    model = OAuthIdentity
    
    @classmethod
    def get_by_provider_user_id(cls, provider: str, provider_user_id: str) -> Optional[OAuthIdentity]:
        """
        Get OAuth identity by provider and provider user ID.
        
        Args:
            provider: OAuth provider (discord, google, slack)
            provider_user_id: User ID from the provider
        
        Returns:
            OAuthIdentity or None
        """
        return cls.model.query.filter_by(
            provider=provider,
            provider_user_id=provider_user_id,
            deleted_at=None
        ).first()
    
    @classmethod
    def get_by_user_id(cls, user_id: UUID) -> List[OAuthIdentity]:
        """Get all OAuth identities for a user."""
        return cls.model.query.filter_by(user_id=user_id).all()
    
    @classmethod
    def get_active_by_user_id(cls, user_id: UUID) -> List[OAuthIdentity]:
        """Get active (not deleted) OAuth identities for a user."""
        return cls.model.query.filter_by(user_id=user_id, deleted_at=None).all()
    
    @classmethod
    def get_by_user_and_provider(cls, user_id: UUID, provider: str) -> Optional[OAuthIdentity]:
        """Get OAuth identity for a specific user and provider."""
        return cls.model.query.filter_by(
            user_id=user_id,
            provider=provider,
            deleted_at=None
        ).first()
    
    @classmethod
    def update_last_login(cls, identity_id: int) -> Optional[OAuthIdentity]:
        """Update last login timestamp."""
        return cls.update(identity_id, last_login_at=datetime.now(timezone.utc))
    
    @classmethod
    def soft_delete(cls, identity_id: int) -> Optional[OAuthIdentity]:
        """Soft delete an identity (7-day grace period)."""
        return cls.update(identity_id, deleted_at=datetime.now(timezone.utc))
    
    @classmethod
    def restore(cls, identity_id: int) -> Optional[OAuthIdentity]:
        """Restore a soft-deleted identity."""
        return cls.update(identity_id, deleted_at=None)
    
    @classmethod
    def count_active_for_user(cls, user_id: UUID) -> int:
        """Count active identities for a user."""
        return cls.count(user_id=user_id, deleted_at=None)
