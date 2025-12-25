"""
Broadcast API Models.

Flask-RESTX models for broadcast endpoints.
"""

from flask_restx import fields


def register_broadcast_models(api):
    """
    Register broadcast-related models with the API.
    
    Args:
        api: Flask-RESTX Api or Namespace instance
    
    Returns:
        Dict of registered models
    """
    broadcast_message = api.model('BroadcastMessage', {
        'sender': fields.String(
            description='Sender display name',
            example='Player1'
        ),
        'platform': fields.String(
            description='Source platform',
            example='discord'
        ),
        'content': fields.String(
            description='Message content',
            example='Hello everyone!'
        ),
        'timestamp': fields.String(
            description='Message timestamp',
            example='2024-01-15T10:30:00Z'
        )
    })
    
    broadcast_request = api.model('BroadcastRequest', {
        'session_id': fields.String(
            required=True,
            description='Game session ID',
            example='session-123'
        ),
        'broadcast_time': fields.String(
            description='Broadcast timestamp',
            example='2024-01-15T10:30:00Z'
        ),
        'message_count': fields.Integer(
            description='Number of messages',
            example=3
        ),
        'messages': fields.List(
            fields.Nested(broadcast_message),
            description='Messages to broadcast'
        )
    })
    
    broadcast_response = api.model('BroadcastResponse', {
        'status': fields.String(
            description='Result status',
            example='received'
        ),
        'session_id': fields.String(
            description='Session ID',
            example='session-123'
        ),
        'message_count': fields.Integer(
            description='Messages processed',
            example=3
        )
    })
    
    broadcast_error = api.model('BroadcastError', {
        'error': fields.String(
            description='Error message',
            example='No channel registered for session'
        ),
        'session_id': fields.String(
            description='Session ID',
            example='session-123'
        ),
        'hint': fields.String(
            description='Helpful hint',
            example='Register a channel first'
        )
    })
    
    return {
        'broadcast_message': broadcast_message,
        'broadcast_request': broadcast_request,
        'broadcast_response': broadcast_response,
        'broadcast_error': broadcast_error
    }

