"""
Game Server Log Model.

SQLAlchemy ORM model for persistent logging of game server events.
Used for debugging chat flow, LangGraph communication, and errors.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Text, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class GameServerLog(db.Model):
    """
    Game Server Log Table.
    
    Stores chat flow events, LangGraph push results, and errors.
    Useful for debugging message flow from Discord → Game Server → LangGraph.
    """
    __tablename__ = 'gs_server_logs_table_orm'
    __bind_key__ = 'db_players'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Log classification
    log_type: Mapped[str] = mapped_column(
        String(30), 
        nullable=False, 
        index=True,
        comment="Type: chat_flow, langgraph_push, error, system"
    )
    
    # Context identifiers
    session_id: Mapped[Optional[str]] = mapped_column(
        String(100), 
        nullable=True, 
        index=True,
        comment="Game session ID"
    )
    sender_id: Mapped[Optional[str]] = mapped_column(
        String(100), 
        nullable=True,
        comment="Sender display name"
    )
    platform: Mapped[Optional[str]] = mapped_column(
        String(20), 
        nullable=True,
        comment="Source platform: discord, slack, etc."
    )
    
    # Log content
    content: Mapped[Optional[str]] = mapped_column(
        Text, 
        nullable=True,
        comment="Log message or content preview"
    )
    
    # Additional metadata
    extra_data: Mapped[Optional[dict]] = mapped_column(
        JSON, 
        nullable=True,
        comment="Additional context as JSON"
    )
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True
    )
    
    def __repr__(self):
        return f"<GameServerLog {self.id} {self.log_type} session={self.session_id}>"
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'log_type': self.log_type,
            'session_id': self.session_id,
            'sender_id': self.sender_id,
            'platform': self.platform,
            'content': self.content,
            'extra_data': self.extra_data,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

