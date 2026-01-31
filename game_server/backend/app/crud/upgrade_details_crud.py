"""
Upgrade Details CRUD Operations.

Data access layer for to_be_initiated_upgrade_details table.
"""

from typing import Optional
from uuid import UUID

from app.crud.base import BaseCRUD
from app.models.postgres_sql_db_models import ToBeInitiatedUpgradeDetails
from app.constants import CardType


class UpgradeDetailsCRUD(BaseCRUD[ToBeInitiatedUpgradeDetails]):
    """CRUD operations for ToBeInitiatedUpgradeDetails."""
    
    model = ToBeInitiatedUpgradeDetails
    
    @classmethod
    def get_by_game_state(cls, game_state_id: UUID) -> Optional[ToBeInitiatedUpgradeDetails]:
        """Get upgrade details for a game state."""
        return cls.get_by_id(game_state_id)
    
    @classmethod
    def create_for_game_state(cls, game_state_id: UUID, **kwargs) -> ToBeInitiatedUpgradeDetails:
        """Create upgrade details for a game state."""
        return cls.create(game_state_id=game_state_id, **kwargs)
    
    @classmethod
    def set_assassination_priority(cls, game_state_id: UUID, card: CardType) -> Optional[ToBeInitiatedUpgradeDetails]:
        """Set assassination priority card."""
        details = cls.get_by_game_state(game_state_id)
        if details:
            return cls.update(game_state_id, assassination_priority=card)
        return cls.create_for_game_state(game_state_id, assassination_priority=card)
    
    @classmethod
    def set_kleptomania(cls, game_state_id: UUID, enabled: bool = True) -> Optional[ToBeInitiatedUpgradeDetails]:
        """Enable/disable kleptomania steal."""
        details = cls.get_by_game_state(game_state_id)
        if details:
            return cls.update(game_state_id, kleptomania_steal=enabled)
        return cls.create_for_game_state(game_state_id, kleptomania_steal=enabled)
    
    @classmethod
    def clear_all(cls, game_state_id: UUID) -> Optional[ToBeInitiatedUpgradeDetails]:
        """Reset all upgrade options."""
        return cls.update(
            game_state_id,
            assassination_priority=None,
            kleptomania_steal=False,
            trigger_identity_crisis=False,
            identify_as_tax_liability=False,
            tax_debt=0
        )
