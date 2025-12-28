"""
Admin API Models.

Flask-RESTX models for admin endpoints.
"""

from flask_restx import fields


def register_admin_models(api):
    """
    Register admin-related models with the API.
    
    Args:
        api: Flask-RESTX Api or Namespace instance
    
    Returns:
        Dict of registered models
    """
    command_option = api.model('CommandOption', {
        'type': fields.Integer(
            required=True,
            description='Option type (3=string, 4=int, etc.)',
            example=3
        ),
        'name': fields.String(
            required=True,
            description='Option name',
            example='player_name'
        ),
        'description': fields.String(
            required=True,
            description='Option description',
            example='Name of the player'
        ),
        'required': fields.Boolean(
            description='Whether option is required',
            example=True
        ),
        'choices': fields.List(
            fields.Raw,
            description='Option choices'
        )
    })
    
    command_request = api.model('CommandRequest', {
        'name': fields.String(
            required=True,
            description='Command name (1-32 chars, lowercase)',
            example='challenge'
        ),
        'description': fields.String(
            required=True,
            description='Command description (1-100 chars)',
            example='Challenge another player\'s claim'
        ),
        'options': fields.List(
            fields.Nested(command_option),
            description='Command options'
        ),
        'guild_id': fields.String(
            description='Guild ID for guild-specific command (optional)',
            example='123456789012345678'
        )
    })
    
    command_response = api.model('CommandResponse', {
        'id': fields.String(
            description='Discord command ID',
            example='123456789012345678'
        ),
        'name': fields.String(
            description='Command name',
            example='challenge'
        ),
        'description': fields.String(
            description='Command description',
            example='Challenge another player\'s claim'
        ),
        'application_id': fields.String(
            description='Application ID',
            example='123456789012345678'
        ),
        'guild_id': fields.String(
            description='Guild ID if guild-specific',
            example='123456789012345678'
        )
    })
    
    command_list_response = api.model('CommandListResponse', {
        'commands': fields.List(
            fields.Nested(command_response),
            description='List of registered commands'
        ),
        'count': fields.Integer(
            description='Number of commands',
            example=5
        )
    })
    
    admin_error = api.model('AdminError', {
        'error': fields.String(
            description='Error message',
            example='Unauthorized'
        )
    })
    
    # Sync status models
    pending_command = api.model('PendingCommand', {
        'name': fields.String(
            description='Command name',
            example='game_session-create'
        ),
        'status': fields.String(
            description='Sync status (new, changed)',
            example='changed'
        ),
        'changes': fields.List(
            fields.String,
            description='List of changes detected'
        ),
        'remote_id': fields.String(
            description='Discord command ID if exists',
            example='123456789012345678'
        ),
        'reason': fields.String(
            description='Reason for pending status',
            example='New command not yet registered'
        )
    })
    
    orphaned_command = api.model('OrphanedCommand', {
        'name': fields.String(
            description='Command name',
            example='old-command'
        ),
        'remote_id': fields.String(
            description='Discord command ID',
            example='123456789012345678'
        )
    })
    
    sync_status_response = api.model('SyncStatusResponse', {
        'last_checked': fields.String(
            description='ISO timestamp of last sync check',
            example='2024-12-24T10:00:00Z'
        ),
        'guild_id': fields.String(
            description='Guild ID used for sync',
            example='856227000259575819'
        ),
        'pending_sync': fields.List(
            fields.Nested(pending_command),
            description='Commands pending sync'
        ),
        'up_to_date': fields.List(
            fields.String,
            description='Command names that are up to date'
        ),
        'orphaned': fields.List(
            fields.Nested(orphaned_command),
            description='Orphaned commands on Discord not in local cogs'
        )
    })
    
    sync_request = api.model('SyncRequest', {
        'commands': fields.List(
            fields.String,
            required=True,
            description='List of command names to sync',
            example=['game_session-create', 'game_session-list']
        ),
        'action': fields.String(
            description='Action to perform: "sync" (delete+register) or "delete" (only delete)',
            example='sync'
        )
    })
    
    sync_response = api.model('SyncResponse', {
        'successful': fields.List(
            fields.String,
            description='Commands synced successfully'
        ),
        'failed': fields.List(
            fields.String,
            description='Commands that failed to sync'
        ),
        'message': fields.String(
            description='Summary message',
            example='Synced 2 commands, 1 failed'
        )
    })
    
    orphan_delete_request = api.model('OrphanDeleteRequest', {
        'commands': fields.List(
            fields.String,
            description='List of orphaned command names to delete (ignored if delete_all=true)',
            example=['old-command', 'unused-command']
        ),
        'delete_all': fields.Boolean(
            description='If true, delete ALL orphaned commands',
            example=False
        )
    })
    
    orphan_delete_response = api.model('OrphanDeleteResponse', {
        'successful': fields.List(
            fields.String,
            description='Commands deleted successfully'
        ),
        'failed': fields.List(
            fields.String,
            description='Commands that failed to delete'
        ),
        'message': fields.String(
            description='Summary message',
            example='Deleted 5 orphaned commands'
        )
    })
    
    return {
        'command_option': command_option,
        'command_request': command_request,
        'command_response': command_response,
        'command_list_response': command_list_response,
        'admin_error': admin_error,
        'pending_command': pending_command,
        'orphaned_command': orphaned_command,
        'sync_status_response': sync_status_response,
        'sync_request': sync_request,
        'sync_response': sync_response,
        'orphan_delete_request': orphan_delete_request,
        'orphan_delete_response': orphan_delete_response
    }

