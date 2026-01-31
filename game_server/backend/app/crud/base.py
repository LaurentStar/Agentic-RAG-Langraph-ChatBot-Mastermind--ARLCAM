"""
Base CRUD Class.

Provides common CRUD operations that all table-specific CRUD classes inherit.
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.extensions import db

# Type variable for the model class
ModelType = TypeVar("ModelType", bound=db.Model)


class BaseCRUD(Generic[ModelType]):
    """
    Base class for CRUD operations.
    
    Provides standard create, read, update, delete operations.
    Subclasses can add table-specific query methods.
    
    Usage:
        class UserAccountCRUD(BaseCRUD[UserAccount]):
            model = UserAccount
            
            @classmethod
            def get_by_user_name(cls, user_name: str) -> Optional[UserAccount]:
                return cls.model.query.filter_by(user_name=user_name).first()
    """
    
    model: Type[ModelType]
    
    @classmethod
    def get_by_id(cls, id: Any) -> Optional[ModelType]:
        """
        Get a record by its primary key.
        
        Args:
            id: Primary key value (UUID, int, or string)
        
        Returns:
            Model instance or None if not found
        """
        return cls.model.query.get(id)
    
    @classmethod
    def get_all(cls, limit: Optional[int] = None, offset: int = 0) -> List[ModelType]:
        """
        Get all records, with optional pagination.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
        
        Returns:
            List of model instances
        """
        query = cls.model.query.offset(offset)
        if limit:
            query = query.limit(limit)
        return query.all()
    
    @classmethod
    def get_by_filters(cls, **filters) -> List[ModelType]:
        """
        Get records matching filter criteria.
        
        Args:
            **filters: Column=value pairs to filter by
        
        Returns:
            List of matching model instances
        """
        return cls.model.query.filter_by(**filters).all()
    
    @classmethod
    def get_first_by_filters(cls, **filters) -> Optional[ModelType]:
        """
        Get first record matching filter criteria.
        
        Args:
            **filters: Column=value pairs to filter by
        
        Returns:
            First matching model instance or None
        """
        return cls.model.query.filter_by(**filters).first()
    
    @classmethod
    def create(cls, **data) -> ModelType:
        """
        Create a new record.
        
        Args:
            **data: Column=value pairs for the new record
        
        Returns:
            Created model instance
        """
        instance = cls.model(**data)
        db.session.add(instance)
        db.session.commit()
        return instance
    
    @classmethod
    def create_no_commit(cls, **data) -> ModelType:
        """
        Create a new record without committing.
        
        Useful when you need to create multiple related records
        and commit them together.
        
        Args:
            **data: Column=value pairs for the new record
        
        Returns:
            Created model instance (not yet committed)
        """
        instance = cls.model(**data)
        db.session.add(instance)
        return instance
    
    @classmethod
    def update(cls, id: Any, **data) -> Optional[ModelType]:
        """
        Update a record by its primary key.
        
        Args:
            id: Primary key value
            **data: Column=value pairs to update
        
        Returns:
            Updated model instance or None if not found
        """
        instance = cls.get_by_id(id)
        if instance is None:
            return None
        
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        
        db.session.commit()
        return instance
    
    @classmethod
    def update_no_commit(cls, instance: ModelType, **data) -> ModelType:
        """
        Update a record instance without committing.
        
        Args:
            instance: Model instance to update
            **data: Column=value pairs to update
        
        Returns:
            Updated model instance (not yet committed)
        """
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        return instance
    
    @classmethod
    def delete(cls, id: Any) -> bool:
        """
        Delete a record by its primary key.
        
        Args:
            id: Primary key value
        
        Returns:
            True if deleted, False if not found
        """
        instance = cls.get_by_id(id)
        if instance is None:
            return False
        
        db.session.delete(instance)
        db.session.commit()
        return True
    
    @classmethod
    def delete_instance(cls, instance: ModelType) -> None:
        """
        Delete a specific model instance.
        
        Args:
            instance: Model instance to delete
        """
        db.session.delete(instance)
        db.session.commit()
    
    @classmethod
    def count(cls, **filters) -> int:
        """
        Count records matching filter criteria.
        
        Args:
            **filters: Column=value pairs to filter by
        
        Returns:
            Number of matching records
        """
        if filters:
            return cls.model.query.filter_by(**filters).count()
        return cls.model.query.count()
    
    @classmethod
    def exists(cls, **filters) -> bool:
        """
        Check if any records match filter criteria.
        
        Args:
            **filters: Column=value pairs to filter by
        
        Returns:
            True if at least one matching record exists
        """
        return cls.model.query.filter_by(**filters).first() is not None
    
    @classmethod
    def commit(cls) -> None:
        """Commit the current transaction."""
        db.session.commit()
    
    @classmethod
    def rollback(cls) -> None:
        """Rollback the current transaction."""
        db.session.rollback()
