"""
Agent Profile ORM Model.

SQLAlchemy model for LLM agent configuration and modulators.
"""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class AgentProfile(db.Model):
    """Agent profile table ORM model for LLM agents."""
    
    __bind_key__ = 'db_players'
    __tablename__ = 'agent_profile_table_orm'
    
    # ---------------------- Identity ---------------------- #
    display_name: Mapped[str] = mapped_column(
        ForeignKey("player_table_orm.display_name"),
        primary_key=True
    )
    
    # ---------------------- Personality ---------------------- #
    personality_type: Mapped[str] = mapped_column(String, default="balanced")
    
    # ---------------------- Modulators (0.0 - 1.0) ---------------------- #
    aggression: Mapped[float] = mapped_column(default=0.5)
    bluff_confidence: Mapped[float] = mapped_column(default=0.5)
    challenge_tendency: Mapped[float] = mapped_column(default=0.5)
    block_tendency: Mapped[float] = mapped_column(default=0.5)
    risk_tolerance: Mapped[float] = mapped_column(default=0.5)
    llm_reliance: Mapped[float] = mapped_column(default=0.5)
    
    # ---------------------- LLM Configuration ---------------------- #
    model_name: Mapped[str] = mapped_column(String, default="gpt-4")
    temperature: Mapped[float] = mapped_column(default=0.7)
    
    # ---------------------- Relationships ---------------------- #
    player = relationship("Player", back_populates="agent_profile")
    
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

