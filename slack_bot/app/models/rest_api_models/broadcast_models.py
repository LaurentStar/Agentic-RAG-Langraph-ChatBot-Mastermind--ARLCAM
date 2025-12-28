"""
Broadcast API Models.

Flask-RESTX models for broadcast endpoints.
"""

from flask_restx import fields


def create_broadcast_models(api):
    """Create and return broadcast-related models."""
    
    message_model = api.model('BroadcastMessage', {
        'sender': fields.String(required=True, description='Sender display name'),
        'content': fields.String(required=True, description='Message content'),
        'platform': fields.String(description='Source platform', example='discord')
    })
    
    broadcast_request = api.model('BroadcastRequest', {
        'session_id': fields.String(required=True, description='Game session ID'),
        'channel_id': fields.String(required=True, description='Target Slack channel ID'),
        'messages': fields.List(fields.Nested(message_model), required=True, description='Messages to broadcast')
    })
    
    single_message_request = api.model('SingleMessageRequest', {
        'channel_id': fields.String(required=True, description='Target Slack channel ID'),
        'sender': fields.String(required=True, description='Sender display name'),
        'content': fields.String(required=True, description='Message content'),
        'platform': fields.String(description='Source platform', default='unknown')
    })
    
    broadcast_response = api.model('BroadcastResponse', {
        'success': fields.Boolean(description='Whether broadcast succeeded'),
        'message': fields.String(description='Status message'),
        'message_count': fields.Integer(description='Number of messages broadcast')
    })
    
    error_response = api.model('BroadcastError', {
        'error': fields.String(description='Error message')
    })
    
    return {
        'message_model': message_model,
        'broadcast_request': broadcast_request,
        'single_message_request': single_message_request,
        'broadcast_response': broadcast_response,
        'error_response': error_response
    }
