"""
Account Flag CRUD Operations.

Data access layer for account_flag table.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from app.crud.base import BaseCRUD
from app.models.postgres_sql_db_models import AccountFlag


class AccountFlagCRUD(BaseCRUD[AccountFlag]):
    """CRUD operations for AccountFlag."""
    
    model = AccountFlag
    
    @classmethod
    def get_by_user_id(cls, user_id: UUID) -> List[AccountFlag]:
        """Get all flags for a user."""
        return cls.model.query.filter_by(user_id=user_id).all()
    
    @classmethod
    def get_pending(cls) -> List[AccountFlag]:
        """Get all pending flags awaiting review."""
        return cls.model.query.filter_by(status='pending').order_by(
            AccountFlag.created_at.desc()
        ).all()
    
    @classmethod
    def get_by_status(cls, status: str) -> List[AccountFlag]:
        """Get flags by status."""
        return cls.model.query.filter_by(status=status).all()
    
    @classmethod
    def get_by_type(cls, flag_type: str) -> List[AccountFlag]:
        """Get flags by type."""
        return cls.model.query.filter_by(flag_type=flag_type).all()
    
    @classmethod
    def mark_reviewed(
        cls,
        flag_id: int,
        reviewed_by: str,
        status: str = 'reviewed',
        notes: Optional[str] = None
    ) -> Optional[AccountFlag]:
        """Mark a flag as reviewed."""
        return cls.update(
            flag_id,
            status=status,
            reviewed_by=reviewed_by,
            review_notes=notes,
            reviewed_at=datetime.now(timezone.utc)
        )
    
    @classmethod
    def dismiss(cls, flag_id: int, reviewed_by: str) -> Optional[AccountFlag]:
        """Dismiss a flag."""
        return cls.mark_reviewed(flag_id, reviewed_by, status='dismissed')
