"""
Account API Models.

Flask-RESTX models for account linking and identity management endpoints.
"""

from flask_restx import fields


def create_identity_models(api):
    """Create and return identity-related API models."""
    
    identity_model = api.model('OAuthIdentity', {
        'id': fields.Integer(description='Identity ID'),
        'provider': fields.String(description='OAuth provider (discord, google, slack)'),
        'provider_username': fields.String(description='Username from provider'),
        'provider_email': fields.String(description='Email from provider'),
        'created_at': fields.String(description='When identity was linked'),
        'last_login_at': fields.String(description='Last login via this identity'),
        'is_active': fields.Boolean(description='Whether identity is active'),
        'deleted_at': fields.String(description='When identity was soft-deleted (if applicable)')
    })
    
    identities_response = api.model('IdentitiesResponse', {
        'identities': fields.List(
            fields.Nested(identity_model),
            description='List of linked OAuth identities'
        ),
        'count': fields.Integer(description='Number of identities')
    })
    
    delete_response = api.model('DeleteIdentityResponse', {
        'message': fields.String(description='Result message'),
        'deleted_at': fields.String(description='When the deletion was initiated'),
        'can_restore_until': fields.String(description='Deadline to restore the identity')
    })
    
    restore_response = api.model('RestoreIdentityResponse', {
        'message': fields.String(description='Result message'),
        'identity': fields.Nested(identity_model)
    })
    
    error_response = api.model('IdentityErrorResponse', {
        'error': fields.String(description='Error message')
    })
    
    return {
        'identity': identity_model,
        'identities_response': identities_response,
        'delete_response': delete_response,
        'restore_response': restore_response,
        'error_response': error_response
    }


def create_link_models(api):
    """Create and return account link-related API models."""
    
    link_initiate_request = api.model('LinkInitiateRequest', {
        'target_provider': fields.String(
            required=True,
            description='Provider to link (discord, google, slack)',
            example='discord'
        ),
        'target_email': fields.String(
            required=True,
            description='Email address for the target provider account',
            example='user@example.com'
        ),
        'primary_email': fields.String(
            required=False,
            description='Your current primary email (optional, auto-detected)',
            example='current@example.com'
        )
    })
    
    link_request_response = api.model('LinkRequestResponse', {
        'id': fields.String(description='Link request UUID'),
        'player_display_name': fields.String(description='Player name'),
        'target_provider': fields.String(description='Target provider'),
        'target_email': fields.String(description='Target email'),
        'primary_confirmed': fields.Boolean(description='Primary email confirmed'),
        'secondary_confirmed': fields.Boolean(description='Secondary email confirmed'),
        'is_complete': fields.Boolean(description='Whether link is complete'),
        'is_expired': fields.Boolean(description='Whether request has expired'),
        'expires_at': fields.String(description='Expiry timestamp'),
        'created_at': fields.String(description='Creation timestamp')
    })
    
    link_status_response = api.model('LinkStatusResponse', {
        'pending_requests': fields.List(
            fields.Nested(link_request_response),
            description='List of pending link requests'
        )
    })
    
    link_confirm_response = api.model('LinkConfirmResponse', {
        'message': fields.String(description='Confirmation message'),
        'primary_confirmed': fields.Boolean(description='Primary email confirmed'),
        'secondary_confirmed': fields.Boolean(description='Secondary email confirmed'),
        'is_complete': fields.Boolean(description='Whether link is complete')
    })
    
    link_cancel_request = api.model('LinkCancelRequest', {
        'request_id': fields.String(
            required=True,
            description='UUID of the link request to cancel'
        )
    })
    
    error_response = api.model('LinkErrorResponse', {
        'error': fields.String(description='Error message')
    })
    
    return {
        'initiate_request': link_initiate_request,
        'request_response': link_request_response,
        'status_response': link_status_response,
        'confirm_response': link_confirm_response,
        'cancel_request': link_cancel_request,
        'error_response': error_response
    }

