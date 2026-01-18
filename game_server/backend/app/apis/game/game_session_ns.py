"""
Game Session Namespace.

Player-facing session interactions (join, leave, list).
"""

from flask import g, request
from flask_restx import Namespace, Resource

from app.constants import SessionStatus
from app.models.rest_api_models.session_models import create_session_models
from app.services.auth_service import jwt_required
from app.services.session_service import SessionService

game_session_ns = Namespace('game-sessions', description='Game session interactions')

# Create models
models = create_session_models(game_session_ns)


@game_session_ns.route('')
class GameSessionList(Resource):
    """Session list endpoint."""
    
    @game_session_ns.doc(params={
        'status': 'Filter by status (waiting, active, completed, cancelled)',
        'is_game_started': 'Filter by started status'
    })
    @game_session_ns.response(200, 'Success', models['session_list_response'])
    @jwt_required
    def get(self):
        """List all joinable sessions."""
        status_str = request.args.get('status')
        is_started = request.args.get('is_game_started')
        
        status = SessionStatus(status_str) if status_str else None
        started = is_started.lower() == 'true' if is_started else None
        
        sessions = SessionService.list_sessions(status=status, is_game_started=started)
        
        return {
            'sessions': [SessionService.session_to_dict(s, include_broadcasts=False) for s in sessions],
            'total': len(sessions)
        }, 200


@game_session_ns.route('/<string:session_id>')
@game_session_ns.param('session_id', 'Session UUID')
class GameSessionResource(Resource):
    """Session resource endpoint."""
    
    @game_session_ns.response(200, 'Success', models['session_response'])
    @game_session_ns.response(404, 'Not found', models['error_response'])
    @jwt_required
    def get(self, session_id):
        """Get session by ID."""
        session = SessionService.get_session(session_id)
        
        if not session:
            return {'message': 'Session not found'}, 404
        
        return SessionService.session_to_dict(session, include_broadcasts=False), 200


@game_session_ns.route('/<string:session_id>/join')
@game_session_ns.param('session_id', 'Session UUID')
class GameSessionJoin(Resource):
    """Session join endpoint."""
    
    @game_session_ns.expect(models['join_session_request'])
    @game_session_ns.response(200, 'Success', models['success_response'])
    @game_session_ns.response(400, 'Bad request', models['error_response'])
    @jwt_required
    def post(self, session_id):
        """Join a game session."""
        data = request.get_json() or {}
        player_name = data.get('player_display_name', g.current_player_name)
        
        try:
            SessionService.join_session(session_id, player_name)
            return {'message': f'Joined session {session_id}'}, 200
        except ValueError as e:
            return {'message': str(e)}, 400


@game_session_ns.route('/<string:session_id>/leave')
@game_session_ns.param('session_id', 'Session UUID')
class GameSessionLeave(Resource):
    """Session leave endpoint."""
    
    @game_session_ns.response(200, 'Success', models['success_response'])
    @game_session_ns.response(400, 'Bad request', models['error_response'])
    @jwt_required
    def post(self, session_id):
        """Leave a game session."""
        try:
            SessionService.leave_session(g.current_player_name)
            return {'message': f'Left session {session_id}'}, 200
        except ValueError as e:
            return {'message': str(e)}, 400


@game_session_ns.route('/<string:session_id>/request-rematch')
@game_session_ns.param('session_id', 'Session UUID')
class GameSessionRematch(Resource):
    """Session rematch request endpoint."""
    
    @game_session_ns.response(200, 'Success', models['session_response'])
    @game_session_ns.response(400, 'Bad request', models['error_response'])
    @game_session_ns.response(404, 'Not found', models['error_response'])
    @jwt_required
    def post(self, session_id):
        """
        Request a rematch for a completed game.
        
        Only available during the ENDING phase.
        All current players are kept in the session.
        Maximum of 3 rematches allowed per session.
        """
        try:
            session = SessionService.rematch_session(session_id)
            return SessionService.session_to_dict(session), 200
        except ValueError as e:
            return {'message': str(e)}, 400


@game_session_ns.route('/<string:session_id>/status')
@game_session_ns.param('session_id', 'Session UUID')
class GameSessionStatus(Resource):
    """Session status endpoint."""
    
    @game_session_ns.response(200, 'Success')
    @game_session_ns.response(404, 'Not found', models['error_response'])
    @jwt_required
    def get(self, session_id):
        """
        Get game session status.
        
        Returns:
        - is_ongoing: Whether game is currently active
        - remaining_turns: Turns left (null if unlimited)
        - player_count: Total players in session
        - players_alive/dead: Count and names
        - current_phase: Current game phase
        - time_remaining_seconds: Seconds until phase ends
        """
        result = SessionService.get_session_status(session_id, include_broadcasts=False)
        
        if 'error' in result:
            return result, 404
        
        return result, 200


# ---------------------- Platform Channel Endpoints ---------------------- #

@game_session_ns.route('/discord-channels')
class DiscordChannelSessions(Resource):
    """Discord channel session bindings endpoint."""
    
    @game_session_ns.doc(description='Get all sessions with Discord channel bindings')
    @game_session_ns.response(200, 'Success')
    def get(self):
        """
        Get all sessions with Discord channel bindings.
        
        Used by Discord bot on startup to populate channel registry.
        No authentication required for bot startup sync.
        
        Returns:
        - channels: List of {session_id, discord_channel_id, session_name, is_active}
        """
        channels = SessionService.get_discord_channel_sessions()
        return {'channels': channels}, 200


@game_session_ns.route('/slack-channels')
class SlackChannelSessions(Resource):
    """Slack channel session bindings endpoint."""
    
    @game_session_ns.doc(description='Get all sessions with Slack channel bindings')
    @game_session_ns.response(200, 'Success')
    def get(self):
        """
        Get all sessions with Slack channel bindings.
        
        Used by Slack bot on startup to populate channel registry.
        No authentication required for bot startup sync.
        
        Returns:
        - channels: List of {session_id, slack_channel_id, session_name, is_active}
        """
        channels = SessionService.get_slack_channel_sessions()
        return {'channels': channels}, 200

