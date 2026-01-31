"""
Agent Profile ORM Model.

SQLAlchemy model for LLM agent configuration and modulators.
"""

import uuid
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class AgentProfile(db.Model):
    """
    Agent profile table ORM model for LLM agents.
    
    Stores personality configuration and modulators for AI players.
    One-to-one relationship with UserAccount (only for LLM_AGENT type users).
    """
    
    __bind_key__ = 'db_players'
    __tablename__ = 'gs_agent_profile_table_orm'
    
    # ---------------------- Identity (FK to UserAccount) ---------------------- #
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gs_user_account_table_orm.user_id", ondelete="CASCADE"),
        primary_key=True
    )
    
    # ---------------------- Personality ---------------------- #
    personality_type: Mapped[str] = mapped_column(String(50), default="balanced")
    # Types: balanced, aggressive, defensive, chaotic, analytical
    
    # ---------------------- Modulators (0.0 - 1.0) ---------------------- #
    aggression: Mapped[float] = mapped_column(default=0.5)
    bluff_confidence: Mapped[float] = mapped_column(default=0.5)
    challenge_tendency: Mapped[float] = mapped_column(default=0.5)
    block_tendency: Mapped[float] = mapped_column(default=0.5)
    risk_tolerance: Mapped[float] = mapped_column(default=0.5)
    llm_reliance: Mapped[float] = mapped_column(default=0.5)
    
    # ---------------------- LLM Configuration ---------------------- #
    model_name: Mapped[str] = mapped_column(String(100), default="gpt-4")
    temperature: Mapped[float] = mapped_column(default=0.7)
    
    # ---------------------- Relationships ---------------------- #
    user = relationship("UserAccount", back_populates="agent_profile")
    
    # ---------------------- Helper Methods ---------------------- #
    def get_modulators_dict(self) -> dict:
        """Return modulators as a dictionary for easy access."""
        return {
            "aggression": self.aggression,
            "bluff_confidence": self.bluff_confidence,
            "challenge_tendency": self.challenge_tendency,
            "block_tendency": self.block_tendency,
            "risk_tolerance": self.risk_tolerance,
            "llm_reliance": self.llm_reliance,
        }
    
    def __repr__(self):
        return f"<AgentProfile user={self.user_id} type={self.personality_type}>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'user_id': str(self.user_id),
            'personality_type': self.personality_type,
            'modulators': self.get_modulators_dict(),
            'model_name': self.model_name,
            'temperature': self.temperature,
        }
