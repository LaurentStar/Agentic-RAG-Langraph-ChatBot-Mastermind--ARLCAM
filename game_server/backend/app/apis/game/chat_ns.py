"""
Chat Namespace.

API endpoints for cross-platform game chat.
This file handles ONLY routing - all business logic is in chat_service.py.
"""

from flask import g, request
from flask_restx import Namespace, Resource

from app.models.rest_api_models.chat_models import create_chat_models
from app.services.auth_service import jwt_required, admin_required
from app.services.chat_service import ChatService
from app.services.chat_broadcast_service import ChatBroadcastService
from app.services.chat_routing_service import ChatRoutingService


chat_ns = Namespace('chat', description='Cross-platform game chat operations')

# Create models from models folder
models = create_chat_models(chat_ns)


# =============================================
# Endpoints
# =============================================

@chat_ns.route('/<string:session_id>/send')
@chat_ns.param('session_id', 'Game session ID')
class ChatSend(Resource):
    """Send a chat message."""
    
    @chat_ns.expect(models['send_message_request'])
    @chat_ns.response(201, 'Message queued', models['message_response'])
    @chat_ns.response(400, 'Bad request', models['error_response'])
    @jwt_required
    def post(self, session_id):
        """Queue a chat message for broadcast."""
        data = request.get_json() or {}
        
        # Use provided sender or fall back to authenticated player
        sender = data.get('sender') or g.current_player_name
        platform_str = data.get('platform', 'default')
        content = data.get('content', '')
        
        result, error = ChatService.send_message(
            session_id=session_id,
            sender_display_name=sender,
            platform_str=platform_str,
            content=content
        )
        
        if error:
            return {'error': error}, 400
        
        return result, 201


@chat_ns.route('/<string:session_id>/messages')
@chat_ns.param('session_id', 'Game session ID')
class ChatMessages(Resource):
    """View pending chat messages."""
    
    @chat_ns.response(200, 'Success', models['messages_list_response'])
    @jwt_required
    def get(self, session_id):
        """Get all pending messages for a session."""
        result = ChatService.get_messages_response(session_id)
        return result, 200


@chat_ns.route('/<string:session_id>/register-bot')
@chat_ns.param('session_id', 'Game session ID')
class ChatRegisterBot(Resource):
    """Register a bot endpoint for broadcasts."""
    
    @chat_ns.expect(models['register_bot_request'])
    @chat_ns.response(201, 'Endpoint registered', models['bot_endpoint_response'])
    @chat_ns.response(400, 'Bad request', models['error_response'])
    @admin_required
    def post(self, session_id):
        """Register a bot endpoint to receive chat broadcasts."""
        data = request.get_json() or {}
        
        platform_str = data.get('platform', '')
        endpoint_url = data.get('endpoint_url', '')
        
        result, error = ChatService.register_endpoint(
            session_id=session_id,
            platform_str=platform_str,
            endpoint_url=endpoint_url
        )
        
        if error:
            return {'error': error}, 400
        
        return result, 201


@chat_ns.route('/<string:session_id>/endpoints')
@chat_ns.param('session_id', 'Game session ID')
class ChatEndpoints(Resource):
    """List registered bot endpoints."""
    
    @chat_ns.response(200, 'Success', models['endpoints_list_response'])
    @admin_required
    def get(self, session_id):
        """Get all registered bot endpoints for a session."""
        result = ChatService.get_endpoints_response(session_id)
        return result, 200


@chat_ns.route('/<string:session_id>/broadcast')
@chat_ns.param('session_id', 'Game session ID')
class ChatBroadcast(Resource):
    """Manually trigger a chat broadcast."""
    
    @chat_ns.response(200, 'Broadcast complete', models['broadcast_result_response'])
    @admin_required
    def post(self, session_id):
        """Trigger an immediate chat broadcast."""
        result = ChatBroadcastService.trigger_immediate_broadcast(session_id)
        return result, 200


@chat_ns.route('/<string:session_id>/schedule')
@chat_ns.param('session_id', 'Game session ID')
class ChatSchedule(Resource):
    """Manage broadcast scheduling."""
    
    @chat_ns.doc(params={'interval': 'Broadcast interval in minutes (default: 5)'})
    @chat_ns.response(200, 'Scheduled', models['schedule_response'])
    @admin_required
    def post(self, session_id):
        """Start scheduled broadcasts for a session."""
        interval = request.args.get('interval', 5, type=int)
        
        job_id = ChatBroadcastService.schedule_broadcast(session_id, interval)
        
        return {
            'status': 'scheduled',
            'session_id': session_id,
            'job_id': job_id,
            'interval_minutes': interval
        }, 200
    
    @chat_ns.response(200, 'Cancelled')
    @admin_required
    def delete(self, session_id):
        """Stop scheduled broadcasts for a session."""
        cancelled = ChatBroadcastService.cancel_broadcast(session_id)
        
        return {
            'status': 'cancelled' if cancelled else 'not_found',
            'session_id': session_id
        }, 200


@chat_ns.route('/<string:session_id>/route')
@chat_ns.param('session_id', 'Game session ID')
class ChatRoute(Resource):
    """Route LLM agent message to platform immediately."""
    
    @chat_ns.expect(models['route_message_request'])
    @chat_ns.response(200, 'Message routed', models['route_message_response'])
    @chat_ns.response(404, 'No endpoint for platform', models['error_response'])
    @chat_ns.response(400, 'Bad request', models['error_response'])
    def post(self, session_id):
        """
        Route a message immediately to the target platform.
        
        Used by LLM agents to send responses directly to Discord/Slack
        without waiting for the scheduled broadcast.
        """
        data = request.get_json() or {}
        
        result, error = ChatRoutingService.route_message(
            session_id=session_id,
            platform=data.get('platform'),
            sender=data.get('sender'),
            content=data.get('content')
        )
        
        if error:
            # Determine appropriate status code
            if 'No active endpoint' in error:
                return {'error': error}, 404
            return {'error': error}, 400
        
        return result, 200
