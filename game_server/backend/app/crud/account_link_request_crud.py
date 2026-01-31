"""
Account Link Request CRUD Operations.

Data access layer for account_link_request table.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from app.crud.base import BaseCRUD
from app.models.postgres_sql_db_models import AccountLinkRequest


class AccountLinkRequestCRUD(BaseCRUD[AccountLinkRequest]):
    """CRUD operations for AccountLinkRequest."""
    
    model = AccountLinkRequest
    
    @classmethod
    def get_pending_for_user(cls, user_id: UUID) -> List[AccountLinkRequest]:
        """Get pending link requests for a user."""
        return cls.model.query.filter_by(user_id=user_id).filter(
            AccountLinkRequest.completed_at.is_(None)
        ).all()
    
    @classmethod
    def get_by_token_primary(cls, token: str) -> Optional[AccountLinkRequest]:
        """Get request by primary token."""
        return cls.model.query.filter_by(token_primary=token).first()
    
    @classmethod
    def get_by_token_secondary(cls, token: str) -> Optional[AccountLinkRequest]:
        """Get request by secondary token."""
        return cls.model.query.filter_by(token_secondary=token).first()
    
    @classmethod
    def confirm_primary(cls, request_id: UUID) -> Optional[AccountLinkRequest]:
        """Mark primary email as confirmed."""
        return cls.update(request_id, primary_confirmed=True)
    
    @classmethod
    def confirm_secondary(cls, request_id: UUID) -> Optional[AccountLinkRequest]:
        """Mark secondary email as confirmed."""
        return cls.update(request_id, secondary_confirmed=True)
    
    @classmethod
    def mark_complete(cls, request_id: UUID) -> Optional[AccountLinkRequest]:
        """Mark request as complete."""
        return cls.update(request_id, completed_at=datetime.now(timezone.utc))
    
    @classmethod
    def get_expired(cls) -> List[AccountLinkRequest]:
        """Get all expired but not completed requests."""
        now = datetime.now(timezone.utc)
        return cls.model.query.filter(
            AccountLinkRequest.expires_at < now,
            AccountLinkRequest.completed_at.is_(None)
        ).all()
