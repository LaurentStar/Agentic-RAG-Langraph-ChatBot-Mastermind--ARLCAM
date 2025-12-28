"""
Account Link API Namespace.

Endpoints for explicit account linking via email confirmation.
"""

import logging
from flask import request, render_template, make_response
from flask_restx import Namespace, Resource

from app.models.rest_api_models.account_models import create_link_models
from app.services.account_link_service import AccountLinkService
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

# Create namespace
link_ns = Namespace(
    'account-link',
    description='Account linking operations'
)

# Create models
models = create_link_models(link_ns)


# =============================================
# JWT Authentication Decorators
# =============================================

def jwt_required(f):
    """Decorator to require JWT authentication."""
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return {'error': 'Missing or invalid Authorization header'}, 401
        
        token = auth_header.split(' ')[1]
        payload = AuthService.verify_access_token(token)
        
        if not payload:
            return {'error': 'Invalid or expired token'}, 401
        
        # Add player info to request context
        request.player_name = payload.get('sub')
        request.player_type = payload.get('player_type')
        
        return f(*args, **kwargs)
    
    wrapper.__name__ = f.__name__
    wrapper.__doc__ = f.__doc__
    return wrapper


# =============================================
# Endpoints
# =============================================

@link_ns.route('')
class LinkAccount(Resource):
    """Initiate or list account link requests."""
    
    @link_ns.doc(security='Bearer')
    @link_ns.expect(models['initiate_request'])
    @link_ns.response(201, 'Link request created', models['request_response'])
    @link_ns.response(400, 'Bad request', models['error_response'])
    @link_ns.response(401, 'Unauthorized', models['error_response'])
    @jwt_required
    def post(self):
        """
        Initiate a new account link request.
        
        This will send confirmation emails to both your primary email
        and the target provider email. Both must be confirmed within 24 hours.
        """
        data = request.get_json() or {}
        
        target_provider = data.get('target_provider')
        target_email = data.get('target_email')
        primary_email = data.get('primary_email')
        
        if not target_provider or not target_email:
            return {'error': 'target_provider and target_email are required'}, 400
        
        link_request, error = AccountLinkService.initiate_link(
            player_display_name=request.player_name,
            target_provider=target_provider,
            target_email=target_email,
            primary_email=primary_email
        )
        
        if error:
            return {'error': error}, 400
        
        return link_request.to_dict(), 201
    
    @link_ns.doc(security='Bearer')
    @link_ns.response(200, 'Success', models['status_response'])
    @link_ns.response(401, 'Unauthorized', models['error_response'])
    @jwt_required
    def get(self):
        """
        Get pending link requests for the authenticated user.
        """
        pending = AccountLinkService.get_pending_requests(request.player_name)
        
        return {
            'pending_requests': [req.to_dict() for req in pending]
        }, 200


@link_ns.route('/confirm/<string:token>')
class ConfirmLink(Resource):
    """Confirm a link request token."""
    
    @link_ns.response(200, 'Token confirmed')
    @link_ns.response(400, 'Invalid token', models['error_response'])
    def get(self, token: str):
        """
        Confirm an email link for account linking.
        
        This endpoint is called when a user clicks the confirmation
        link in their email. Returns an HTML page with the result.
        """
        link_request, error = AccountLinkService.confirm_token(token)
        
        if error and not link_request:
            # Render error page
            html = render_template(
                'link_confirm_error.html',
                error=error
            )
            response = make_response(html)
            response.headers['Content-Type'] = 'text/html'
            return response
        
        # Render success page
        html = render_template(
            'link_confirm_success.html',
            link_request=link_request,
            message=error  # error here is just a status message like "already confirmed"
        )
        response = make_response(html)
        response.headers['Content-Type'] = 'text/html'
        return response


@link_ns.route('/cancel')
class CancelLink(Resource):
    """Cancel a pending link request."""
    
    @link_ns.doc(security='Bearer')
    @link_ns.expect(models['cancel_request'])
    @link_ns.response(200, 'Request cancelled')
    @link_ns.response(400, 'Bad request', models['error_response'])
    @link_ns.response(401, 'Unauthorized', models['error_response'])
    @jwt_required
    def post(self):
        """
        Cancel a pending link request.
        """
        data = request.get_json() or {}
        request_id = data.get('request_id')
        
        if not request_id:
            return {'error': 'request_id is required'}, 400
        
        success, error = AccountLinkService.cancel_request(
            request_id=request_id,
            player_display_name=request.player_name
        )
        
        if not success:
            return {'error': error}, 400
        
        return {'message': 'Link request cancelled'}, 200

