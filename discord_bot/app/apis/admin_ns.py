"""
Admin Namespace.

Admin operations including slash command registration.
Requires JWT authentication.
"""

import logging

from flask import request
from flask_restx import Namespace, Resource

from flask import current_app

from app.services.auth_service import jwt_required, admin_required
from app.services.command_registration_service import CommandRegistrationService
from app.services.command_sync_service import CommandSyncService
from app.models.rest_api_models.admin_models import register_admin_models

logger = logging.getLogger(__name__)

admin_ns = Namespace('admin', description='Admin operations (JWT required)')

# Register models with namespace
models = register_admin_models(admin_ns)


@admin_ns.route('/commands')
class CommandRegistration(Resource):
    """Register and list Discord slash commands."""
    
    @admin_ns.doc(security='Bearer')
    @admin_ns.expect(models['command_request'])
    @admin_ns.response(201, 'Command registered', models['command_response'])
    @admin_ns.response(400, 'Bad request', models['admin_error'])
    @admin_ns.response(401, 'Unauthorized', models['admin_error'])
    @admin_ns.response(403, 'Forbidden', models['admin_error'])
    @admin_ns.response(429, 'Rate limited', models['admin_error'])
    @jwt_required
    @admin_required
    def post(self):
        """
        Register a new Discord slash command.
        
        Requires admin JWT token.
        
        Note: Discord rate limits apply (200 command updates per day globally).
        Guild-specific commands update instantly, global commands take up to 1 hour.
        """
        data = request.get_json() or {}
        
        # Extract guild_id if provided (for guild-specific command)
        guild_id = data.pop('guild_id', None)
        
        # Register the command
        result, error = CommandRegistrationService.register_command(data, guild_id)
        
        if error:
            if "Rate limited" in error:
                return {"error": error}, 429
            return {"error": error}, 400
        
        logger.info(f"Admin registered command: {data.get('name')}")
        return result, 201
    
    @admin_ns.doc(security='Bearer')
    @admin_ns.param('guild_id', 'Guild ID for guild-specific commands (optional)', _in='query')
    @admin_ns.response(200, 'Success', models['command_list_response'])
    @admin_ns.response(401, 'Unauthorized', models['admin_error'])
    @jwt_required
    def get(self):
        """
        List registered Discord slash commands.
        
        Requires JWT token.
        Pass guild_id query param for guild-specific commands.
        """
        guild_id = request.args.get('guild_id')
        
        commands, error = CommandRegistrationService.list_commands(guild_id)
        
        if error:
            return {"error": error}, 400
        
        return {
            "commands": commands,
            "count": len(commands)
        }, 200


@admin_ns.route('/commands/<string:command_id>')
@admin_ns.param('command_id', 'Discord command ID')
class CommandDelete(Resource):
    """Delete a registered command."""
    
    @admin_ns.doc(security='Bearer')
    @admin_ns.param('guild_id', 'Guild ID for guild-specific commands (optional)', _in='query')
    @admin_ns.response(204, 'Command deleted')
    @admin_ns.response(400, 'Bad request', models['admin_error'])
    @admin_ns.response(401, 'Unauthorized', models['admin_error'])
    @admin_ns.response(403, 'Forbidden', models['admin_error'])
    @jwt_required
    @admin_required
    def delete(self, command_id: str):
        """
        Delete a registered Discord slash command.
        
        Requires admin JWT token.
        Pass guild_id query param for guild-specific commands.
        """
        guild_id = request.args.get('guild_id')
        
        success, error = CommandRegistrationService.delete_command(command_id, guild_id)
        
        if not success:
            return {"error": error}, 400
        
        logger.info(f"Admin deleted command: {command_id}")
        return '', 204


@admin_ns.route('/commands/sync-status')
class CommandSyncStatus(Resource):
    """Get slash command sync status."""
    
    @admin_ns.doc(security='Bearer')
    @admin_ns.response(200, 'Success', models['sync_status_response'])
    @admin_ns.response(401, 'Unauthorized', models['admin_error'])
    @jwt_required
    def get(self):
        """
        Get current slash command sync status.
        
        Returns:
        - pending_sync: Commands that need to be synced (new or changed)
        - up_to_date: Commands that match Discord's registered commands
        - orphaned: Commands on Discord that don't exist in local cogs
        
        Use POST /admin/commands/sync to sync pending commands.
        """
        status = CommandSyncService.get_sync_status_summary()
        return status, 200


@admin_ns.route('/commands/sync')
class CommandSync(Resource):
    """Sync slash commands with Discord."""
    
    @admin_ns.doc(security='Bearer')
    @admin_ns.expect(models['sync_request'])
    @admin_ns.response(200, 'Success', models['sync_response'])
    @admin_ns.response(400, 'Bad request', models['admin_error'])
    @admin_ns.response(401, 'Unauthorized', models['admin_error'])
    @admin_ns.response(403, 'Forbidden', models['admin_error'])
    @jwt_required
    @admin_required
    def post(self):
        """
        Sync specified slash commands with Discord.
        
        Actions:
        - "sync": Delete and re-register the command (for changed commands)
        - "delete": Only delete the command (for orphaned commands)
        
        Note: This uses the TEST_GUILD_ID for guild-specific registration.
        Commands will update instantly for that guild.
        """
        import os
        
        data = request.get_json() or {}
        command_names = data.get('commands', [])
        action = data.get('action', 'sync')
        
        if not command_names:
            return {"error": "No commands specified"}, 400
        
        if action not in ('sync', 'delete'):
            return {"error": "Invalid action. Use 'sync' or 'delete'"}, 400
        
        guild_id = os.getenv('TEST_GUILD_ID')
        if not guild_id:
            return {"error": "TEST_GUILD_ID not configured"}, 400
        
        # Get local commands from bot if we need to re-register
        local_commands = None
        if action == 'sync':
            bot = current_app.bot_instance
            if bot:
                local_commands = CommandSyncService.extract_local_commands(bot)
            else:
                return {"error": "Bot instance not available"}, 500
        
        successful, failed = CommandSyncService.sync_commands(
            command_names,
            guild_id,
            action,
            local_commands
        )
        
        message = f"Synced {len(successful)} commands"
        if failed:
            message += f", {len(failed)} failed"
        
        logger.info(f"Command sync: {message}")
        
        return {
            "successful": successful,
            "failed": failed,
            "message": message
        }, 200
