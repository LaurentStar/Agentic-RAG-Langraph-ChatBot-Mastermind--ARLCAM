"""
Admin Session Namespace.

Privileged session management operations.
"""

from flask import request
from flask_restx import Namespace, Resource

from app.constants import GamePrivilege, SocialMediaPlatform
from app.models.rest_api_models.session_models import create_session_models
from app.services.auth_service import privilege_required
from app.services.session_service import SessionService

admin_session_ns = Namespace('admin-sessions', description='Admin session management')

# Create models
models = create_session_models(admin_session_ns)


@admin_session_ns.route('')
class AdminSessionList(Resource):
    """Admin session creation endpoint."""
    
    @admin_session_ns.expect(models['create_session_request'])
    @admin_session_ns.response(201, 'Created', models['session_response'])
    @admin_session_ns.response(400, 'Bad request', models['error_response'])
    @privilege_required(GamePrivilege.START_GAME)
    def post(self):
        """Create a new game session (admin or START_GAME privilege)."""
        data = request.get_json()
        
        try:
            session = SessionService.create_session(
                session_name=data['session_name'],
                max_players=data.get('max_players', 6),
                turn_limit=data.get('turn_limit', 10),
                upgrades_enabled=data.get('upgrades_enabled', True),
                # Phase durations (numbered sequentially)
                phase1_action_duration=data.get('phase1_action_duration', 50),
                phase2_lockout_duration=data.get('phase2_lockout_duration', 10),
                phase3_reaction_duration=data.get('phase3_reaction_duration', 20),
                phase4_lockout_duration=data.get('phase4_lockout_duration', 10),
                phase5_broadcast_duration=data.get('phase5_broadcast_duration', 1),
                phase6_ending_duration=data.get('phase6_ending_duration', 5)
            )
            
            return SessionService.session_to_dict(session), 201
            
        except ValueError as e:
            return {'message': str(e)}, 400
        except KeyError as e:
            return {'message': f'Missing required field: {e}'}, 400


@admin_session_ns.route('/<string:session_id>')
@admin_session_ns.param('session_id', 'Session UUID')
class AdminSessionResource(Resource):
    """Admin session resource endpoint."""
    
    @admin_session_ns.expect(models['create_session_request'])
    @admin_session_ns.response(200, 'Success', models['session_response'])
    @admin_session_ns.response(400, 'Bad request', models['error_response'])
    @admin_session_ns.response(404, 'Not found', models['error_response'])
    @privilege_required(GamePrivilege.MANAGE_CONFIG)
    def put(self, session_id):
        """Update session configuration (admin or MANAGE_CONFIG privilege)."""
        data = request.get_json()
        
        try:
            session = SessionService.update_session(
                session_id=session_id,
                session_name=data.get('session_name'),
                max_players=data.get('max_players'),
                turn_limit=data.get('turn_limit'),
                upgrades_enabled=data.get('upgrades_enabled'),
                # Phase durations (numbered sequentially)
                phase1_action_duration=data.get('phase1_action_duration'),
                phase2_lockout_duration=data.get('phase2_lockout_duration'),
                phase3_reaction_duration=data.get('phase3_reaction_duration'),
                phase4_lockout_duration=data.get('phase4_lockout_duration'),
                phase5_broadcast_duration=data.get('phase5_broadcast_duration'),
                phase6_ending_duration=data.get('phase6_ending_duration')
            )
            
            return SessionService.session_to_dict(session), 200
            
        except ValueError as e:
            return {'message': str(e)}, 400


@admin_session_ns.route('/<string:session_id>/start')
@admin_session_ns.param('session_id', 'Session UUID')
class AdminSessionStart(Resource):
    """Session start endpoint."""
    
    @admin_session_ns.response(200, 'Success', models['session_response'])
    @admin_session_ns.response(400, 'Bad request', models['error_response'])
    @privilege_required(GamePrivilege.START_GAME)
    def post(self, session_id):
        """Start a game session (admin or START_GAME privilege)."""
        try:
            session = SessionService.start_session(session_id)
            return SessionService.session_to_dict(session), 200
        except ValueError as e:
            return {'message': str(e)}, 400


@admin_session_ns.route('/<string:session_id>/end')
@admin_session_ns.param('session_id', 'Session UUID')
class AdminSessionEnd(Resource):
    """Session end endpoint."""
    
    @admin_session_ns.response(200, 'Success', models['session_response'])
    @admin_session_ns.response(400, 'Bad request', models['error_response'])
    @privilege_required(GamePrivilege.END_GAME)
    def post(self, session_id):
        """End a game session (admin or END_GAME privilege)."""
        try:
            session = SessionService.end_session(session_id)
            return SessionService.session_to_dict(session), 200
        except ValueError as e:
            return {'message': str(e)}, 400


@admin_session_ns.route('/<string:session_id>/restart')
@admin_session_ns.param('session_id', 'Session UUID')
class AdminSessionRestart(Resource):
    """Session restart endpoint."""
    
    @admin_session_ns.response(200, 'Success', models['session_response'])
    @admin_session_ns.response(400, 'Bad request', models['error_response'])
    @admin_session_ns.response(404, 'Not found', models['error_response'])
    @privilege_required(GamePrivilege.START_GAME)
    def post(self, session_id):
        """
        Restart a game session (admin or START_GAME privilege).
        
        This resets the session to WAITING status, clears all players
        (they must rejoin), and resets the rematch count to 0.
        """
        try:
            session = SessionService.restart_session(session_id)
            return SessionService.session_to_dict(session), 200
        except ValueError as e:
            return {'message': str(e)}, 400


@admin_session_ns.route('/<string:session_id>/status')
@admin_session_ns.param('session_id', 'Session UUID')
class AdminSessionStatus(Resource):
    """Admin session status endpoint."""
    
    @admin_session_ns.response(200, 'Success')
    @admin_session_ns.response(404, 'Not found', models['error_response'])
    @privilege_required(GamePrivilege.MANAGE_CONFIG)
    def get(self, session_id):
        """
        Get detailed game session status (admin version).
        
        Returns all status info plus broadcast destinations.
        """
        result = SessionService.get_session_status(session_id, include_broadcasts=True)
        
        if 'error' in result:
            return result, 404
        
        return result, 200


@admin_session_ns.route('/<string:session_id>/broadcasts')
@admin_session_ns.param('session_id', 'Session UUID')
class AdminBroadcastList(Resource):
    """Broadcast destinations management endpoint."""
    
    @admin_session_ns.response(200, 'Success')
    @privilege_required(GamePrivilege.MANAGE_BROADCASTS)
    def get(self, session_id):
        """Get all broadcast destinations for a session."""
        destinations = SessionService.get_broadcast_destinations(session_id)
        
        return {
            'destinations': [
                {
                    'id': d.id,
                    'platform': d.platform.value if d.platform else None,
                    'channel_id': d.channel_id,
                    'channel_name': d.channel_name,
                    'webhook_url': d.webhook_url
                }
                for d in destinations
            ]
        }, 200
    
    @admin_session_ns.expect(models['add_broadcast_request'])
    @admin_session_ns.response(201, 'Created', models['broadcast_destination'])
    @admin_session_ns.response(400, 'Bad request', models['error_response'])
    @privilege_required(GamePrivilege.MANAGE_BROADCASTS)
    def post(self, session_id):
        """Add a broadcast destination."""
        data = request.get_json()
        
        try:
            destination = SessionService.add_broadcast_destination(
                session_id=session_id,
                platform=SocialMediaPlatform(data['platform']),
                channel_id=data['channel_id'],
                channel_name=data['channel_name'],
                webhook_url=data.get('webhook_url')
            )
            
            return {
                'id': destination.id,
                'platform': destination.platform.value,
                'channel_id': destination.channel_id,
                'channel_name': destination.channel_name,
                'webhook_url': destination.webhook_url
            }, 201
            
        except ValueError as e:
            return {'message': str(e)}, 400
        except KeyError as e:
            return {'message': f'Missing required field: {e}'}, 400


@admin_session_ns.route('/<string:session_id>/broadcasts/<int:destination_id>')
@admin_session_ns.param('session_id', 'Session UUID')
@admin_session_ns.param('destination_id', 'Broadcast destination ID')
class AdminBroadcastResource(Resource):
    """Broadcast destination resource endpoint."""
    
    @admin_session_ns.response(204, 'Deleted')
    @admin_session_ns.response(404, 'Not found', models['error_response'])
    @privilege_required(GamePrivilege.MANAGE_BROADCASTS)
    def delete(self, session_id, destination_id):
        """Remove a broadcast destination."""
        if SessionService.remove_broadcast_destination(destination_id):
            return '', 204
        return {'message': 'Broadcast destination not found'}, 404


# ---------------------- Platform Channel Bindings ---------------------- #

@admin_session_ns.route('/<string:session_id>/discord-channel')
@admin_session_ns.param('session_id', 'Session UUID')
class AdminDiscordChannel(Resource):
    """Discord channel binding endpoint."""
    
    @admin_session_ns.expect(models['discord_channel_binding'])
    @admin_session_ns.response(200, 'Success')
    @admin_session_ns.response(400, 'Bad request', models['error_response'])
    @admin_session_ns.response(404, 'Not found', models['error_response'])
    @privilege_required(GamePrivilege.MANAGE_CONFIG)
    def post(self, session_id):
        """
        Bind a Discord channel to a game session.
        
        This allows the Discord bot to route messages from this channel
        to the specified game session.
        """
        data = request.get_json()
        
        if not data or 'channel_id' not in data:
            return {'message': 'channel_id is required'}, 400
        
        try:
            session = SessionService.bind_discord_channel(session_id, data['channel_id'])
            return {
                'message': f"Discord channel {data['channel_id']} bound to session {session_id}",
                'session_id': session.session_id,
                'discord_channel_id': session.discord_channel_id
            }, 200
        except ValueError as e:
            return {'message': str(e)}, 404
    
    @admin_session_ns.response(200, 'Success')
    @admin_session_ns.response(404, 'Not found', models['error_response'])
    @privilege_required(GamePrivilege.MANAGE_CONFIG)
    def delete(self, session_id):
        """
        Unbind Discord channel from a game session.
        """
        try:
            session = SessionService.unbind_discord_channel(session_id)
            return {
                'message': f"Discord channel unbound from session {session_id}",
                'session_id': session.session_id
            }, 200
        except ValueError as e:
            return {'message': str(e)}, 404


@admin_session_ns.route('/<string:session_id>/slack-channel')
@admin_session_ns.param('session_id', 'Session UUID')
class AdminSlackChannel(Resource):
    """Slack channel binding endpoint."""
    
    @admin_session_ns.expect(models['slack_channel_binding'])
    @admin_session_ns.response(200, 'Success')
    @admin_session_ns.response(400, 'Bad request', models['error_response'])
    @admin_session_ns.response(404, 'Not found', models['error_response'])
    @privilege_required(GamePrivilege.MANAGE_CONFIG)
    def post(self, session_id):
        """
        Bind a Slack channel to a game session.
        
        This allows the Slack bot to route messages from this channel
        to the specified game session.
        """
        data = request.get_json()
        
        if not data or 'channel_id' not in data:
            return {'message': 'channel_id is required'}, 400
        
        try:
            session = SessionService.bind_slack_channel(session_id, data['channel_id'])
            return {
                'message': f"Slack channel {data['channel_id']} bound to session {session_id}",
                'session_id': session.session_id,
                'slack_channel_id': session.slack_channel_id
            }, 200
        except ValueError as e:
            return {'message': str(e)}, 404
    
    @admin_session_ns.response(200, 'Success')
    @admin_session_ns.response(404, 'Not found', models['error_response'])
    @privilege_required(GamePrivilege.MANAGE_CONFIG)
    def delete(self, session_id):
        """
        Unbind Slack channel from a game session.
        """
        try:
            session = SessionService.unbind_slack_channel(session_id)
            return {
                'message': f"Slack channel unbound from session {session_id}",
                'session_id': session.session_id
            }, 200
        except ValueError as e:
            return {'message': str(e)}, 404

