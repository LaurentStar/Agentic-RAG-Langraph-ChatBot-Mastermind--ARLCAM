"""
Application Startup Tasks.

Functions that run during app initialization.
"""

import os
import logging

from app.constants import PlayerType
from app.crud import UserAccountCRUD
from app.services.user_account_service import UserAccountService

logger = logging.getLogger(__name__)


def create_default_admin_if_enabled(app) -> None:
    """
    Create default admin account on startup if enabled via environment variable.
    
    Environment Variables:
        GS_CREATE_DEFAULT_ADMIN: Set to 'true' to enable
        GS_DEFAULT_ADMIN_USERNAME: Admin username (default: Master_Of_Coup)
        GS_DEFAULT_ADMIN_PASSWORD: Admin password (required if enabled)
    """
    create_admin = os.environ.get('GS_CREATE_DEFAULT_ADMIN', 'false').lower() == 'true'
    
    if not create_admin:
        return
    
    admin_username = os.environ.get('GS_DEFAULT_ADMIN_USERNAME', 'Master_Of_Coup')
    admin_password = os.environ.get('GS_DEFAULT_ADMIN_PASSWORD')
    
    if not admin_password:
        app.logger.error("GS_CREATE_DEFAULT_ADMIN is true but GS_DEFAULT_ADMIN_PASSWORD is not set")
        return
    
    if UserAccountCRUD.user_name_exists(admin_username):
        app.logger.info(f"Default admin '{admin_username}' already exists, skipping creation")
        return
    
    try:
        UserAccountService.register(
            user_name=admin_username,
            display_name=admin_username,
            password=admin_password,
            player_type=PlayerType.ADMIN
        )
        app.logger.info(f"Created default admin account: {admin_username}")
    except Exception as e:
        app.logger.error(f"Failed to create default admin: {e}")
