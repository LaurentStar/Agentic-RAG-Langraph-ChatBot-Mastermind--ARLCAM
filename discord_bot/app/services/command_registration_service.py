"""
Command Registration Service.

Handles registration of Discord slash commands via the Discord API.
Allows admin users to register new commands without restarting the bot.
"""

import os
import logging
from typing import Dict, Any, Optional, List, Tuple

import httpx

logger = logging.getLogger(__name__)


class CommandRegistrationService:
    """
    Service for registering Discord slash commands via HTTP.
    
    Uses Discord's HTTP API to register application commands,
    allowing dynamic command registration without bot restart.
    
    Note: Discord has rate limits on command registration (200/day globally).
    Guild-specific commands update instantly, global commands take up to 1 hour.
    """
    
    DISCORD_API_BASE = "https://discord.com/api/v10"
    BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("TOKEN")
    APPLICATION_ID = os.getenv("DISCORD_APPLICATION_ID")
    
    @staticmethod
    def register_command(
        command_data: Dict[str, Any],
        guild_id: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Register a slash command with Discord.
        
        Args:
            command_data: Command definition dict with:
                - name: Command name (1-32 chars, lowercase)
                - description: Command description (1-100 chars)
                - options: Optional list of command options
                - default_permission: Optional bool
            guild_id: Optional guild ID for guild-specific command.
                     If None, registers globally.
        
        Returns:
            Tuple of (response_data, error_message)
        """
        if not CommandRegistrationService.BOT_TOKEN:
            return None, "DISCORD_BOT_TOKEN not configured"
        
        if not CommandRegistrationService.APPLICATION_ID:
            return None, "DISCORD_APPLICATION_ID not configured"
        
        # Validate command data
        if not command_data.get("name"):
            return None, "Command name is required"
        if not command_data.get("description"):
            return None, "Command description is required"
        
        # Build endpoint URL
        if guild_id:
            url = (
                f"{CommandRegistrationService.DISCORD_API_BASE}"
                f"/applications/{CommandRegistrationService.APPLICATION_ID}"
                f"/guilds/{guild_id}/commands"
            )
        else:
            url = (
                f"{CommandRegistrationService.DISCORD_API_BASE}"
                f"/applications/{CommandRegistrationService.APPLICATION_ID}"
                f"/commands"
            )
        
        headers = {
            "Authorization": f"Bot {CommandRegistrationService.BOT_TOKEN}",
            "Content-Type": "application/json"
        }
        
        try:
            response = httpx.post(
                url,
                json=command_data,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code in (200, 201):
                logger.info(
                    f"Registered command '{command_data['name']}' "
                    f"{'globally' if not guild_id else f'for guild {guild_id}'}"
                )
                return response.json(), None
            elif response.status_code == 429:
                # Rate limited
                retry_after = response.json().get("retry_after", "unknown")
                return None, f"Rate limited. Retry after {retry_after} seconds"
            else:
                error_data = response.json()
                error_msg = error_data.get("message", response.text)
                logger.error(f"Failed to register command: {error_msg}")
                return None, f"Discord API error: {error_msg}"
                
        except httpx.TimeoutException:
            return None, "Request timeout"
        except Exception as e:
            logger.error(f"Command registration error: {e}")
            return None, str(e)
    
    @staticmethod
    def list_commands(
        guild_id: Optional[str] = None
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        """
        List registered commands.
        
        Args:
            guild_id: Optional guild ID for guild-specific commands.
                     If None, lists global commands.
        
        Returns:
            Tuple of (commands_list, error_message)
        """
        if not CommandRegistrationService.BOT_TOKEN:
            return None, "DISCORD_BOT_TOKEN not configured"
        
        if not CommandRegistrationService.APPLICATION_ID:
            return None, "DISCORD_APPLICATION_ID not configured"
        
        # Build endpoint URL
        if guild_id:
            url = (
                f"{CommandRegistrationService.DISCORD_API_BASE}"
                f"/applications/{CommandRegistrationService.APPLICATION_ID}"
                f"/guilds/{guild_id}/commands"
            )
        else:
            url = (
                f"{CommandRegistrationService.DISCORD_API_BASE}"
                f"/applications/{CommandRegistrationService.APPLICATION_ID}"
                f"/commands"
            )
        
        headers = {
            "Authorization": f"Bot {CommandRegistrationService.BOT_TOKEN}"
        }
        
        try:
            response = httpx.get(url, headers=headers, timeout=30.0)
            
            if response.status_code == 200:
                return response.json(), None
            else:
                error_msg = response.json().get("message", response.text)
                return None, f"Discord API error: {error_msg}"
                
        except Exception as e:
            logger.error(f"Error listing commands: {e}")
            return None, str(e)
    
    @staticmethod
    def delete_command(
        command_id: str,
        guild_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Delete a registered command.
        
        Args:
            command_id: Discord command ID to delete
            guild_id: Optional guild ID for guild-specific command
        
        Returns:
            Tuple of (success, error_message)
        """
        if not CommandRegistrationService.BOT_TOKEN:
            return False, "DISCORD_BOT_TOKEN not configured"
        
        if not CommandRegistrationService.APPLICATION_ID:
            return False, "DISCORD_APPLICATION_ID not configured"
        
        # Build endpoint URL
        if guild_id:
            url = (
                f"{CommandRegistrationService.DISCORD_API_BASE}"
                f"/applications/{CommandRegistrationService.APPLICATION_ID}"
                f"/guilds/{guild_id}/commands/{command_id}"
            )
        else:
            url = (
                f"{CommandRegistrationService.DISCORD_API_BASE}"
                f"/applications/{CommandRegistrationService.APPLICATION_ID}"
                f"/commands/{command_id}"
            )
        
        headers = {
            "Authorization": f"Bot {CommandRegistrationService.BOT_TOKEN}"
        }
        
        try:
            response = httpx.delete(url, headers=headers, timeout=30.0)
            
            if response.status_code == 204:
                logger.info(f"Deleted command {command_id}")
                return True, None
            else:
                error_msg = response.json().get("message", response.text)
                return False, f"Discord API error: {error_msg}"
                
        except Exception as e:
            logger.error(f"Error deleting command: {e}")
            return False, str(e)
    
    @staticmethod
    def bulk_overwrite_commands(
        commands: List[Dict[str, Any]],
        guild_id: Optional[str] = None
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        """
        Bulk overwrite all commands at once.
        
        This is more efficient than registering commands individually.
        It replaces ALL existing commands with the provided list.
        
        WARNING: Any commands not in the list will be DELETED.
        
        Args:
            commands: List of command definitions
            guild_id: Optional guild ID for guild-specific commands.
                     If None, overwrites global commands.
        
        Returns:
            Tuple of (registered_commands, error_message)
        """
        if not CommandRegistrationService.BOT_TOKEN:
            return None, "DISCORD_BOT_TOKEN not configured"
        
        if not CommandRegistrationService.APPLICATION_ID:
            return None, "DISCORD_APPLICATION_ID not configured"
        
        # Build endpoint URL (PUT to overwrite all)
        if guild_id:
            url = (
                f"{CommandRegistrationService.DISCORD_API_BASE}"
                f"/applications/{CommandRegistrationService.APPLICATION_ID}"
                f"/guilds/{guild_id}/commands"
            )
        else:
            url = (
                f"{CommandRegistrationService.DISCORD_API_BASE}"
                f"/applications/{CommandRegistrationService.APPLICATION_ID}"
                f"/commands"
            )
        
        headers = {
            "Authorization": f"Bot {CommandRegistrationService.BOT_TOKEN}",
            "Content-Type": "application/json"
        }
        
        try:
            response = httpx.put(
                url,
                json=commands,
                headers=headers,
                timeout=60.0  # Longer timeout for bulk operation
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(
                    f"Bulk overwrote {len(result)} commands "
                    f"{'globally' if not guild_id else f'for guild {guild_id}'}"
                )
                return result, None
            elif response.status_code == 429:
                retry_after = response.json().get("retry_after", "unknown")
                return None, f"Rate limited. Retry after {retry_after} seconds"
            else:
                error_data = response.json()
                error_msg = error_data.get("message", response.text)
                logger.error(f"Failed to bulk overwrite commands: {error_msg}")
                return None, f"Discord API error: {error_msg}"
                
        except httpx.TimeoutException:
            return None, "Request timeout"
        except Exception as e:
            logger.error(f"Bulk overwrite error: {e}")
            return None, str(e)

