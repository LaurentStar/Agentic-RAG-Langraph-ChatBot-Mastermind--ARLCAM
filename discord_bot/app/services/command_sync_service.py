"""
Command Sync Service.

Handles automatic synchronization of Discord slash commands between
local cog definitions and Discord's registered commands.
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from discord import app_commands
from discord.ext import commands

from app.services.command_registration_service import CommandRegistrationService

logger = logging.getLogger("discord_bot")

# Path to temp directory for sync status
# Go up from services/ to app/, then into temp/
TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp")
SYNC_STATUS_FILE = os.path.join(TEMP_DIR, "command_sync_status.json")


class CommandSyncService:
    """
    Service for synchronizing local slash commands with Discord.
    
    Features:
    - Extract command definitions from loaded cogs
    - Compare with Discord-registered commands
    - Detect new, changed, and orphaned commands
    - Auto-register new commands on startup
    - Flag changed commands for manual sync via API
    """
    
    @staticmethod
    def _normalize_option(option: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize an option dict for consistent comparison.
        
        Discord's API may omit fields or represent them differently.
        This ensures both local and remote options have the same structure.
        
        Args:
            option: Option dict (from local or Discord)
            
        Returns:
            Normalized option dict
        """
        return {
            "name": option.get("name", ""),
            "description": option.get("description", ""),
            "type": option.get("type", 3),  # Default to STRING type
            "required": bool(option.get("required", False)),  # Normalize to bool, default False
        }
    
    @staticmethod
    def _normalize_options(options: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize a list of options for consistent comparison.
        
        Args:
            options: List of option dicts
            
        Returns:
            List of normalized option dicts (sorted by name for consistent hashing)
        """
        normalized = [
            CommandSyncService._normalize_option(opt) 
            for opt in options
        ]
        # Sort by name for consistent hash computation
        return sorted(normalized, key=lambda x: x["name"])
    
    @staticmethod
    def _serialize_option(param: app_commands.Parameter) -> Dict[str, Any]:
        """
        Serialize a command parameter/option to a dict.
        
        Args:
            param: discord.py Parameter object
            
        Returns:
            Dictionary representation of the option
        """
        option_data = {
            "name": param.name,
            "description": param.description,
            "type": param.type.value,
            "required": bool(param.required),  # Ensure boolean
        }
        
        # Add choices if present
        if hasattr(param, 'choices') and param.choices:
            option_data["choices"] = [
                {"name": c.name, "value": c.value}
                for c in param.choices
            ]
        
        return option_data
    
    @staticmethod
    def _compute_hash(command_data: Dict[str, Any]) -> str:
        """
        Compute a hash of command definition for change detection.
        
        Normalizes options before hashing to ensure consistent comparison
        between local definitions and Discord's API response.
        
        Args:
            command_data: Command definition dict
            
        Returns:
            MD5 hash string
        """
        # Normalize for consistent hashing
        normalized = {
            "name": command_data.get("name", ""),
            "description": command_data.get("description", ""),
            "type": command_data.get("type", 1),
            "options": CommandSyncService._normalize_options(
                command_data.get("options", [])
            ),
        }
        
        # Include permissions if present
        if command_data.get("default_member_permissions"):
            normalized["default_member_permissions"] = command_data["default_member_permissions"]
        
        # Create a stable string representation
        hash_input = json.dumps(normalized, sort_keys=True)
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]
    
    @staticmethod
    def _serialize_command(cmd: app_commands.Command) -> Dict[str, Any]:
        """
        Serialize a discord.py app command to a dict.
        
        Args:
            cmd: discord.py Command object
            
        Returns:
            Dictionary representation suitable for Discord API
        """
        command_data = {
            "name": cmd.name,
            "description": cmd.description,
            "type": 1,  # CHAT_INPUT
            "options": [],
        }
        
        # Serialize parameters
        for param in cmd.parameters:
            command_data["options"].append(
                CommandSyncService._serialize_option(param)
            )
        
        # Add default_member_permissions if set
        if cmd.default_permissions is not None:
            command_data["default_member_permissions"] = str(cmd.default_permissions.value)
        
        return command_data
    
    @staticmethod
    def extract_local_commands(bot: commands.Bot) -> Dict[str, Dict[str, Any]]:
        """
        Extract all slash command definitions from loaded cogs.
        
        Args:
            bot: The Discord bot instance
            
        Returns:
            Dict mapping command names to their definitions
        """
        local_commands = {}
        
        for cog in bot.cogs.values():
            # Get app commands from cog
            if hasattr(cog, 'walk_app_commands'):
                for cmd in cog.walk_app_commands():
                    if isinstance(cmd, app_commands.Command):
                        cmd_data = CommandSyncService._serialize_command(cmd)
                        cmd_data["hash"] = CommandSyncService._compute_hash(cmd_data)
                        cmd_data["cog"] = cog.__class__.__name__
                        local_commands[cmd.name] = cmd_data
        
        # Also check bot's tree for directly registered commands
        for cmd in bot.tree.get_commands():
            if cmd.name not in local_commands:
                cmd_data = CommandSyncService._serialize_command(cmd)
                cmd_data["hash"] = CommandSyncService._compute_hash(cmd_data)
                cmd_data["cog"] = "global"
                local_commands[cmd.name] = cmd_data
        
        logger.info(f"Extracted {len(local_commands)} local commands")
        return local_commands
    
    @staticmethod
    def fetch_discord_commands(guild_id: Optional[str] = None) -> Tuple[Dict[str, Dict[str, Any]], Optional[str]]:
        """
        Fetch registered commands from Discord API.
        
        Args:
            guild_id: Guild ID for guild-specific commands
            
        Returns:
            Tuple of (commands_dict, error_message)
        """
        commands_list, error = CommandRegistrationService.list_commands(guild_id)
        
        if error:
            return {}, error
        
        discord_commands = {}
        for cmd in commands_list:
            cmd_name = cmd.get("name")
            if cmd_name:
                # Compute hash from Discord's command data
                hash_data = {
                    "name": cmd.get("name"),
                    "description": cmd.get("description"),
                    "type": cmd.get("type", 1),
                    "options": cmd.get("options", []),
                }
                if cmd.get("default_member_permissions"):
                    hash_data["default_member_permissions"] = cmd["default_member_permissions"]
                
                discord_commands[cmd_name] = {
                    "id": cmd.get("id"),
                    "name": cmd_name,
                    "description": cmd.get("description"),
                    "options": cmd.get("options", []),
                    "hash": CommandSyncService._compute_hash(hash_data),
                }
        
        logger.info(f"Fetched {len(discord_commands)} commands from Discord")
        return discord_commands, None
    
    @staticmethod
    def compare_commands(
        local: Dict[str, Dict[str, Any]],
        remote: Dict[str, Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Compare local and remote command definitions.
        
        Args:
            local: Local command definitions
            remote: Discord-registered commands
            
        Returns:
            Dict with keys: new, changed, unchanged, orphaned
        """
        result = {
            "new": [],
            "changed": [],
            "unchanged": [],
            "orphaned": [],
        }
        
        local_names = set(local.keys())
        remote_names = set(remote.keys())
        
        # New commands (in local, not in remote)
        for name in local_names - remote_names:
            result["new"].append({
                "name": name,
                "local": local[name],
            })
        
        # Orphaned commands (in remote, not in local)
        for name in remote_names - local_names:
            result["orphaned"].append({
                "name": name,
                "remote": remote[name],
            })
        
        # Check for changes in existing commands
        for name in local_names & remote_names:
            local_hash = local[name].get("hash", "")
            remote_hash = remote[name].get("hash", "")
            
            if local_hash != remote_hash:
                # Detect what changed
                changes = CommandSyncService._detect_changes(local[name], remote[name])
                result["changed"].append({
                    "name": name,
                    "local": local[name],
                    "remote": remote[name],
                    "local_hash": local_hash,
                    "remote_hash": remote_hash,
                    "changes": changes,
                })
            else:
                result["unchanged"].append({
                    "name": name,
                })
        
        return result
    
    @staticmethod
    def _detect_changes(local: Dict[str, Any], remote: Dict[str, Any]) -> List[str]:
        """
        Detect specific changes between local and remote command.
        
        Args:
            local: Local command definition
            remote: Remote command definition
            
        Returns:
            List of change descriptions
        """
        changes = []
        
        # Check description
        if local.get("description") != remote.get("description"):
            changes.append("description changed")
        
        # Normalize options for comparison
        local_options = {
            o["name"]: CommandSyncService._normalize_option(o) 
            for o in local.get("options", [])
        }
        remote_options = {
            o["name"]: CommandSyncService._normalize_option(o) 
            for o in remote.get("options", [])
        }
        
        for opt_name in set(local_options.keys()) - set(remote_options.keys()):
            changes.append(f"added option: {opt_name}")
        
        for opt_name in set(remote_options.keys()) - set(local_options.keys()):
            changes.append(f"removed option: {opt_name}")
        
        for opt_name in set(local_options.keys()) & set(remote_options.keys()):
            local_opt = local_options[opt_name]
            remote_opt = remote_options[opt_name]
            
            if local_opt["description"] != remote_opt["description"]:
                changes.append(f"option '{opt_name}' description changed")
            if local_opt["type"] != remote_opt["type"]:
                changes.append(f"option '{opt_name}' type changed")
            if local_opt["required"] != remote_opt["required"]:
                changes.append(f"option '{opt_name}' required changed")
        
        return changes if changes else ["hash mismatch (internal changes)"]
    
    @staticmethod
    def save_sync_status(
        status: Dict[str, Any],
        guild_id: Optional[str] = None
    ) -> None:
        """
        Save sync status to temp JSON file.
        
        Args:
            status: Sync status dict
            guild_id: Guild ID used for sync
        """
        # Ensure temp directory exists
        os.makedirs(TEMP_DIR, exist_ok=True)
        
        data = {
            "last_checked": datetime.now(timezone.utc).isoformat(),
            "guild_id": guild_id,
            "commands": {},
        }
        
        # Save command statuses
        for cmd in status.get("new", []):
            data["commands"][cmd["name"]] = {
                "status": "new",
                "local_hash": cmd["local"].get("hash"),
                "cog": cmd["local"].get("cog"),
            }
        
        for cmd in status.get("changed", []):
            data["commands"][cmd["name"]] = {
                "status": "changed",
                "local_hash": cmd.get("local_hash"),
                "remote_hash": cmd.get("remote_hash"),
                "remote_id": cmd["remote"].get("id"),
                "changes": cmd.get("changes", []),
            }
        
        for cmd in status.get("unchanged", []):
            data["commands"][cmd["name"]] = {
                "status": "unchanged",
            }
        
        for cmd in status.get("orphaned", []):
            data["commands"][cmd["name"]] = {
                "status": "orphaned",
                "remote_id": cmd["remote"].get("id"),
            }
        
        with open(SYNC_STATUS_FILE, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved sync status to {SYNC_STATUS_FILE}")
    
    @staticmethod
    def load_sync_status() -> Optional[Dict[str, Any]]:
        """
        Load sync status from temp JSON file.
        
        Returns:
            Sync status dict or None if file doesn't exist
        """
        if not os.path.exists(SYNC_STATUS_FILE):
            return None
        
        try:
            with open(SYNC_STATUS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load sync status: {e}")
            return None
    
    @staticmethod
    async def auto_sync(
        bot: commands.Bot,
        guild_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform automatic sync on startup.
        
        - Extracts local commands from cogs
        - Compares with Discord
        - Auto-registers NEW commands
        - Flags CHANGED commands for manual sync
        
        Args:
            bot: Discord bot instance
            guild_id: Guild ID for guild-specific commands
            
        Returns:
            Sync result summary
        """
        logger.info(f"Starting auto-sync for guild: {guild_id or 'global'}")
        
        # Extract local commands
        local_commands = CommandSyncService.extract_local_commands(bot)
        
        if not local_commands:
            logger.warning("No local commands found in cogs")
            return {"status": "no_commands"}
        
        # Fetch Discord commands
        discord_commands, error = CommandSyncService.fetch_discord_commands(guild_id)
        
        if error:
            logger.error(f"Failed to fetch Discord commands: {error}")
            return {"status": "error", "error": error}
        
        # Compare
        comparison = CommandSyncService.compare_commands(local_commands, discord_commands)
        
        # Save status
        CommandSyncService.save_sync_status(comparison, guild_id)
        
        # Auto-register NEW commands
        registered = []
        for cmd in comparison["new"]:
            cmd_data = cmd["local"].copy()
            # Remove internal fields
            cmd_data.pop("hash", None)
            cmd_data.pop("cog", None)
            
            result, err = CommandRegistrationService.register_command(cmd_data, guild_id)
            if err:
                logger.error(f"Failed to register {cmd['name']}: {err}")
            else:
                registered.append(cmd["name"])
                logger.info(f"Auto-registered command: {cmd['name']}")
        
        # Log summary
        summary = {
            "status": "success",
            "guild_id": guild_id,
            "new_registered": registered,
            "pending_changes": [c["name"] for c in comparison["changed"]],
            "orphaned": [c["name"] for c in comparison["orphaned"]],
            "unchanged": len(comparison["unchanged"]),
        }
        
        logger.info(f"Auto-sync complete: {len(registered)} registered, "
                   f"{len(comparison['changed'])} pending, "
                   f"{len(comparison['orphaned'])} orphaned")
        
        return summary
    
    @staticmethod
    def get_sync_status_summary() -> Dict[str, Any]:
        """
        Get a summary of current sync status for API response.
        
        Returns:
            Summary dict with pending_sync, up_to_date, orphaned
        """
        status = CommandSyncService.load_sync_status()
        
        if not status:
            return {
                "status": "no_sync_data",
                "message": "No sync has been performed yet. Restart the bot to trigger auto-sync.",
            }
        
        result = {
            "last_checked": status.get("last_checked"),
            "guild_id": status.get("guild_id"),
            "pending_sync": [],
            "up_to_date": [],
            "orphaned": [],
        }
        
        for name, cmd_status in status.get("commands", {}).items():
            if cmd_status["status"] == "new":
                result["pending_sync"].append({
                    "name": name,
                    "status": "new",
                    "reason": "New command not yet registered",
                })
            elif cmd_status["status"] == "changed":
                result["pending_sync"].append({
                    "name": name,
                    "status": "changed",
                    "changes": cmd_status.get("changes", []),
                    "remote_id": cmd_status.get("remote_id"),
                })
            elif cmd_status["status"] == "orphaned":
                result["orphaned"].append({
                    "name": name,
                    "remote_id": cmd_status.get("remote_id"),
                })
            else:
                result["up_to_date"].append(name)
        
        return result
    
    @staticmethod
    def sync_commands(
        command_names: List[str],
        guild_id: Optional[str] = None,
        action: str = "sync",
        local_commands: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Tuple[List[str], List[str]]:
        """
        Sync specified commands (delete and re-register).
        
        Args:
            command_names: List of command names to sync
            guild_id: Guild ID for guild-specific commands
            action: "sync" to re-register, "delete" to only delete
            local_commands: Local command definitions (if available)
            
        Returns:
            Tuple of (successful, failed) command names
        """
        status = CommandSyncService.load_sync_status()
        if not status:
            return [], command_names
        
        successful = []
        failed = []
        
        for name in command_names:
            cmd_info = status.get("commands", {}).get(name)
            
            if not cmd_info:
                logger.warning(f"Command {name} not found in sync status")
                failed.append(name)
                continue
            
            # Delete existing command if it has a remote_id
            remote_id = cmd_info.get("remote_id")
            if remote_id:
                success, error = CommandRegistrationService.delete_command(remote_id, guild_id)
                if not success:
                    logger.error(f"Failed to delete {name}: {error}")
                    failed.append(name)
                    continue
                logger.info(f"Deleted command: {name}")
            
            # Re-register if action is sync and we have local definition
            if action == "sync" and local_commands and name in local_commands:
                cmd_data = local_commands[name].copy()
                cmd_data.pop("hash", None)
                cmd_data.pop("cog", None)
                
                result, error = CommandRegistrationService.register_command(cmd_data, guild_id)
                if error:
                    logger.error(f"Failed to re-register {name}: {error}")
                    failed.append(name)
                    continue
                logger.info(f"Re-registered command: {name}")
            
            successful.append(name)
        
        return successful, failed
    
    @staticmethod
    def refresh_sync_status(
        bot: "commands.Bot",
        guild_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Refresh the sync status JSON by re-comparing local and remote commands.
        
        Call this after any sync operation to ensure the status file is accurate.
        
        Args:
            bot: Discord bot instance
            guild_id: Guild ID for guild-specific commands
            
        Returns:
            Updated comparison result
        """
        # Extract current local commands
        local_commands = CommandSyncService.extract_local_commands(bot)
        
        # Fetch current Discord commands
        discord_commands, error = CommandSyncService.fetch_discord_commands(guild_id)
        
        if error:
            logger.error(f"Failed to refresh sync status: {error}")
            return {"error": error}
        
        # Compare and save
        comparison = CommandSyncService.compare_commands(local_commands, discord_commands)
        CommandSyncService.save_sync_status(comparison, guild_id)
        
        logger.info("Sync status refreshed")
        return comparison
    
    @staticmethod
    def delete_orphaned_commands(
        command_names: List[str],
        guild_id: Optional[str] = None,
        delete_all: bool = False
    ) -> Tuple[List[str], List[str]]:
        """
        Delete orphaned commands from Discord.
        
        Args:
            command_names: Specific command names to delete (ignored if delete_all=True)
            guild_id: Guild ID for guild-specific commands
            delete_all: If True, delete ALL orphaned commands
            
        Returns:
            Tuple of (successful, failed) command names
        """
        status = CommandSyncService.load_sync_status()
        if not status:
            logger.warning("No sync status available")
            return [], command_names
        
        # Get list of orphaned commands
        orphaned = {}
        for name, cmd_info in status.get("commands", {}).items():
            if cmd_info.get("status") == "orphaned":
                orphaned[name] = cmd_info
        
        if not orphaned:
            logger.info("No orphaned commands found")
            return [], []
        
        # Determine which commands to delete
        if delete_all:
            to_delete = list(orphaned.keys())
        else:
            # Only delete specified commands that are actually orphaned
            to_delete = [name for name in command_names if name in orphaned]
            
            # Log warnings for non-orphaned commands
            for name in command_names:
                if name not in orphaned:
                    logger.warning(f"Command '{name}' is not orphaned, skipping")
        
        successful = []
        failed = []
        
        for name in to_delete:
            cmd_info = orphaned[name]
            remote_id = cmd_info.get("remote_id")
            
            if not remote_id:
                logger.warning(f"No remote_id for orphaned command '{name}'")
                failed.append(name)
                continue
            
            success, error = CommandRegistrationService.delete_command(remote_id, guild_id)
            
            if success:
                successful.append(name)
                logger.info(f"Deleted orphaned command: {name}")
            else:
                failed.append(name)
                logger.error(f"Failed to delete orphaned command '{name}': {error}")
        
        return successful, failed

