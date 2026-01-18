"""
Session API Models.

Flask-RESTX models for game session endpoints.
"""

from flask_restx import fields


def create_session_models(api):
    """Create and return session-related API models."""
    
    create_session_request = api.model('CreateSessionRequest', {
        'session_name': fields.String(required=True, description='Session name'),
        'max_players': fields.Integer(description='Max players', default=6),
        'turn_limit': fields.Integer(description='Max turns (0 = unlimited)', default=10),
        'upgrades_enabled': fields.Boolean(description='Allow upgrades', default=True),
        # Phase durations in minutes (numbered sequentially)
        'phase1_action_duration': fields.Integer(description='Phase 1 (actions) duration in minutes', default=50),
        'phase2_lockout_duration': fields.Integer(description='Phase 2 (lockout) duration in minutes', default=10),
        'phase3_reaction_duration': fields.Integer(description='Phase 3 (reactions) duration in minutes', default=20),
        'phase4_lockout_duration': fields.Integer(description='Phase 4 (lockout) duration in minutes', default=10),
        'phase5_broadcast_duration': fields.Integer(description='Phase 5 (broadcast) duration in minutes', default=1),
        'phase6_ending_duration': fields.Integer(description='Phase 6 (ending/rematch) duration in minutes', default=5)
    })
    
    broadcast_destination = api.model('BroadcastDestination', {
        'id': fields.Integer(description='Destination ID'),
        'platform': fields.String(description='Platform'),
        'channel_id': fields.String(description='Channel ID'),
        'channel_name': fields.String(description='Channel name'),
        'webhook_url': fields.String(description='Webhook URL')
    })
    
    session_response = api.model('SessionResponse', {
        'session_id': fields.String(description='Session UUID'),
        'session_name': fields.String(description='Session name'),
        'current_phase': fields.String(description='Current game phase'),
        'phase_end_time': fields.DateTime(description='When current phase ends'),
        'turn_number': fields.Integer(description='Current turn'),
        'turn_limit': fields.Integer(description='Max turns'),
        'max_players': fields.Integer(description='Max players'),
        'player_count': fields.Integer(description='Current player count'),
        'upgrades_enabled': fields.Boolean(description='Upgrades allowed'),
        'is_game_started': fields.Boolean(description='Game has started'),
        'status': fields.String(description='Session status'),
        'created_at': fields.DateTime(description='Creation time'),
        'broadcast_destinations': fields.List(fields.Nested(broadcast_destination)),
        # Phase durations (numbered sequentially)
        'phase1_action_duration': fields.Integer(description='Phase 1 (actions) duration in minutes'),
        'phase2_lockout_duration': fields.Integer(description='Phase 2 (lockout) duration in minutes'),
        'phase3_reaction_duration': fields.Integer(description='Phase 3 (reactions) duration in minutes'),
        'phase4_lockout_duration': fields.Integer(description='Phase 4 (lockout) duration in minutes'),
        'phase5_broadcast_duration': fields.Integer(description='Phase 5 (broadcast) duration in minutes'),
        'phase6_ending_duration': fields.Integer(description='Phase 6 (ending/rematch) duration in minutes'),
        # Rematch tracking
        'rematch_count': fields.Integer(description='Number of rematches played'),
        'winners': fields.List(fields.String, description='Winner display names')
    })
    
    session_list_response = api.model('SessionListResponse', {
        'sessions': fields.List(fields.Nested(session_response)),
        'total': fields.Integer(description='Total session count')
    })
    
    add_broadcast_request = api.model('AddBroadcastRequest', {
        'platform': fields.String(required=True, description='Platform'),
        'channel_id': fields.String(required=True, description='Channel ID'),
        'channel_name': fields.String(required=True, description='Channel name'),
        'webhook_url': fields.String(description='Optional webhook URL')
    })
    
    join_session_request = api.model('JoinSessionRequest', {
        'player_display_name': fields.String(description='Player to join (defaults to authenticated user)')
    })
    
    error_response = api.model('SessionErrorResponse', {
        'message': fields.String(description='Error message')
    })
    
    success_response = api.model('SessionSuccessResponse', {
        'message': fields.String(description='Success message')
    })
    
    # Platform channel binding models
    discord_channel_binding = api.model('DiscordChannelBinding', {
        'channel_id': fields.String(required=True, description='Discord channel ID')
    })
    
    slack_channel_binding = api.model('SlackChannelBinding', {
        'channel_id': fields.String(required=True, description='Slack channel ID')
    })
    
    channel_binding_response = api.model('ChannelBindingResponse', {
        'message': fields.String(description='Result message'),
        'session_id': fields.String(description='Session UUID'),
        'discord_channel_id': fields.String(description='Bound Discord channel ID'),
        'slack_channel_id': fields.String(description='Bound Slack channel ID')
    })
    
    return {
        'create_session_request': create_session_request,
        'broadcast_destination': broadcast_destination,
        'session_response': session_response,
        'session_list_response': session_list_response,
        'add_broadcast_request': add_broadcast_request,
        'join_session_request': join_session_request,
        'error_response': error_response,
        'success_response': success_response,
        'discord_channel_binding': discord_channel_binding,
        'slack_channel_binding': slack_channel_binding,
        'channel_binding_response': channel_binding_response
    }

