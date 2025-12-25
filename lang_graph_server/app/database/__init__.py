"""
Database module for LangGraph server.

Provides read-only access to the game server's PostgreSQL database
for querying player data, pending actions, and agent profiles.

Global db_connection instance is declared in app/extensions.py
"""

from app.database.connection import DatabaseConnection
from app.database.models import (
    Base,
    Player,
    UpgradeDetails,
    # Enums
    CardType,
    PlayerStatus,
    ToBeInitiated,
    SocialMediaPlatform,
    # Legacy aliases
    PlayerModel,
    UpgradeDetailsModel,
)

__all__ = [
    "DatabaseConnection",
    "Base",
    "Player",
    "UpgradeDetails",
    "CardType",
    "PlayerStatus",
    "ToBeInitiated",
    "SocialMediaPlatform",
    # Legacy
    "PlayerModel",
    "UpgradeDetailsModel",
]
