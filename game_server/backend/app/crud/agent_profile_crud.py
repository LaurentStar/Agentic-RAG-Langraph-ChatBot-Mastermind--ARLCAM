"""
Agent Profile CRUD Operations.

Data access layer for agent_profile table.
"""

from typing import Dict, Optional
from uuid import UUID

from app.crud.base import BaseCRUD
from app.models.postgres_sql_db_models import AgentProfile


class AgentProfileCRUD(BaseCRUD[AgentProfile]):
    """CRUD operations for AgentProfile."""
    
    model = AgentProfile
    
    @classmethod
    def get_by_user_id(cls, user_id: UUID) -> Optional[AgentProfile]:
        """Get agent profile by user_id."""
        return cls.get_by_id(user_id)
    
    @classmethod
    def create_for_user(
        cls,
        user_id: UUID,
        personality_type: str = 'balanced',
        model_name: str = 'gpt-4',
        **modulators
    ) -> AgentProfile:
        """Create an agent profile for a user."""
        return cls.create(
            user_id=user_id,
            personality_type=personality_type,
            model_name=model_name,
            **modulators
        )
    
    @classmethod
    def update_modulators(cls, user_id: UUID, modulators: Dict[str, float]) -> Optional[AgentProfile]:
        """Update agent modulators."""
        profile = cls.get_by_user_id(user_id)
        if profile:
            valid_modulators = [
                'aggression', 'bluff_confidence', 'challenge_tendency',
                'block_tendency', 'risk_tolerance', 'llm_reliance'
            ]
            updates = {k: v for k, v in modulators.items() if k in valid_modulators}
            return cls.update(user_id, **updates)
        return None
    
    @classmethod
    def update_model(cls, user_id: UUID, model_name: str, temperature: float = 0.7) -> Optional[AgentProfile]:
        """Update LLM model configuration."""
        return cls.update(user_id, model_name=model_name, temperature=temperature)
