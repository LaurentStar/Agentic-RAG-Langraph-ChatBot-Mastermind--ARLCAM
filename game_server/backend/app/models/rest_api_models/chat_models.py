"""
Chat API Models.

Flask-RESTX models for chat endpoints.
"""

from flask_restx import fields


def create_chat_models(api):
    """Create and return chat-related API models."""
    
    send_message_request = api.model('SendChatMessageRequest', {
        'content': fields.String(required=True, description='Message content (max 2000 chars)'),
        'sender': fields.String(description='Sender name (optional, defaults to authenticated player)'),
        'platform': fields.String(description='Source platform (optional, defaults to "default")')
    })
    
    message_response = api.model('ChatMessageResponse', {
        'id': fields.Integer(description='Message ID'),
        'sender': fields.String(description='Sender display name'),
        'platform': fields.String(description='Source platform'),
        'content': fields.String(description='Message content'),
        'timestamp': fields.String(description='Creation timestamp')
    })
    
    messages_list_response = api.model('ChatMessagesListResponse', {
        'session_id': fields.String(description='Session ID'),
        'message_count': fields.Integer(description='Number of pending messages'),
        'messages': fields.List(fields.Nested(message_response))
    })
    
    register_bot_request = api.model('RegisterBotEndpointRequest', {
        'platform': fields.String(required=True, description='Platform (discord, slack, etc.)'),
        'endpoint_url': fields.String(required=True, description='URL to receive broadcast POSTs')
    })
    
    bot_endpoint_response = api.model('BotEndpointResponse', {
        'id': fields.Integer(description='Endpoint ID'),
        'platform': fields.String(description='Platform'),
        'endpoint_url': fields.String(description='Endpoint URL'),
        'is_active': fields.Boolean(description='Whether endpoint is active'),
        'last_broadcast_at': fields.String(description='Last broadcast timestamp')
    })
    
    endpoints_list_response = api.model('EndpointsListResponse', {
        'session_id': fields.String(description='Session ID'),
        'endpoint_count': fields.Integer(description='Number of endpoints'),
        'endpoints': fields.List(fields.Nested(bot_endpoint_response))
    })
    
    broadcast_result_response = api.model('BroadcastResultResponse', {
        'message_count': fields.Integer(description='Messages broadcast'),
        'endpoint_count': fields.Integer(description='Endpoints notified'),
        'cleared': fields.Integer(description='Messages cleared'),
        'results': fields.List(fields.Raw, description='Per-endpoint results')
    })
    
    schedule_response = api.model('ScheduleResponse', {
        'status': fields.String(description='Schedule status'),
        'session_id': fields.String(description='Session ID'),
        'job_id': fields.String(description='Scheduler job ID'),
        'interval_minutes': fields.Integer(description='Broadcast interval')
    })
    
    error_response = api.model('ChatErrorResponse', {
        'error': fields.String(description='Error message')
    })
    
    # Route message request - for LLM agents to send immediate responses
    route_message_request = api.model('RouteMessageRequest', {
        'platform': fields.String(required=True, description='Target platform (discord, slack)'),
        'sender': fields.String(required=True, description='Sender display name'),
        'content': fields.String(required=True, description='Message content')
    })
    
    route_message_response = api.model('RouteMessageResponse', {
        'status': fields.String(description='Route status'),
        'session_id': fields.String(description='Session ID'),
        'platform': fields.String(description='Target platform'),
        'endpoint_url': fields.String(description='Endpoint URL used')
    })
    
    return {
        'send_message_request': send_message_request,
        'message_response': message_response,
        'messages_list_response': messages_list_response,
        'register_bot_request': register_bot_request,
        'bot_endpoint_response': bot_endpoint_response,
        'endpoints_list_response': endpoints_list_response,
        'broadcast_result_response': broadcast_result_response,
        'schedule_response': schedule_response,
        'error_response': error_response,
        'route_message_request': route_message_request,
        'route_message_response': route_message_response,
    }

