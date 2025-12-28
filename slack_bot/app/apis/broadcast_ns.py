"""
Broadcast API Namespace.

Receives chat broadcasts from the game server.
"""

from flask import current_app, request
from flask_restx import Namespace, Resource

from app.services import BroadcastService, LoggingService, jwt_required
from app.models.rest_api_models import create_broadcast_models

broadcast_ns = Namespace('broadcast', description='Broadcast operations')

# Create models
models = create_broadcast_models(broadcast_ns)


@broadcast_ns.route('')
@broadcast_ns.route('/')
class Broadcast(Resource):
    """Broadcast message endpoint."""
    
    @broadcast_ns.doc('post_broadcast', security='Bearer')
    @broadcast_ns.expect(models['broadcast_request'])
    @broadcast_ns.marshal_with(models['broadcast_response'])
    @broadcast_ns.response(400, 'Validation error', models['error_response'])
    @broadcast_ns.response(401, 'Unauthorized', models['error_response'])
    @broadcast_ns.response(500, 'Internal error', models['error_response'])
    @jwt_required
    def post(self):
        """
        Post a broadcast to a Slack channel.
        
        Used by game_server to send batched chat messages.
        Requires JWT authentication.
        """
        data = request.json
        
        # Validate required fields
        session_id = data.get('session_id')
        channel_id = data.get('channel_id')
        messages = data.get('messages', [])
        
        if not session_id:
            return {'error': 'session_id is required'}, 400
        if not channel_id:
            return {'error': 'channel_id is required'}, 400
        
        # Get Slack client
        slack_bot = getattr(current_app, 'slack_bot', None)
        if not slack_bot:
            return {'error': 'Slack bot not initialized'}, 500
        
        # Post broadcast
        success = BroadcastService.post_broadcast(
            slack_client=slack_bot.client,
            channel_id=channel_id,
            messages=messages,
            session_id=session_id
        )
        
        # Log the broadcast
        LoggingService.log_broadcast(
            session_id=session_id,
            message_count=len(messages),
            success=success,
            channel_id=channel_id
        )
        
        if success:
            return {
                'success': True,
                'message': 'Broadcast posted successfully',
                'message_count': len(messages)
            }
        else:
            return {'error': 'Failed to post broadcast'}, 500


@broadcast_ns.route('/message')
class SingleMessage(Resource):
    """Single message endpoint for immediate routing."""
    
    @broadcast_ns.doc('post_single_message', security='Bearer')
    @broadcast_ns.expect(models['single_message_request'])
    @broadcast_ns.marshal_with(models['broadcast_response'])
    @broadcast_ns.response(400, 'Validation error', models['error_response'])
    @broadcast_ns.response(401, 'Unauthorized', models['error_response'])
    @broadcast_ns.response(500, 'Internal error', models['error_response'])
    @jwt_required
    def post(self):
        """
        Post a single message to a Slack channel.
        
        Used for immediate routing of LLM agent responses.
        Requires JWT authentication.
        """
        data = request.json
        
        # Validate required fields
        channel_id = data.get('channel_id')
        sender = data.get('sender')
        content = data.get('content')
        platform = data.get('platform', 'unknown')
        
        if not channel_id:
            return {'error': 'channel_id is required'}, 400
        if not sender:
            return {'error': 'sender is required'}, 400
        if not content:
            return {'error': 'content is required'}, 400
        
        # Get Slack client
        slack_bot = getattr(current_app, 'slack_bot', None)
        if not slack_bot:
            return {'error': 'Slack bot not initialized'}, 500
        
        # Post message
        success = BroadcastService.post_single_message(
            slack_client=slack_bot.client,
            channel_id=channel_id,
            sender=sender,
            content=content,
            platform=platform
        )
        
        if success:
            return {
                'success': True,
                'message': 'Message posted successfully',
                'message_count': 1
            }
        else:
            return {'error': 'Failed to post message'}, 500
