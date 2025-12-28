"""
OAuth Identity API Namespace.

Endpoints for managing linked OAuth identities.
"""

import logging
from datetime import datetime, timezone, timedelta
from flask import request
from flask_restx import Namespace, Resource

from app.extensions import db
from app.models.postgres_sql_db_models import OAuthIdentity
from app.models.rest_api_models.account_models import create_identity_models
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

# Create namespace
identity_ns = Namespace(
    'account-identities',
    description='OAuth identity management'
)

# Create models
models = create_identity_models(identity_ns)


# =============================================
# JWT Authentication Decorator
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
        
        request.player_name = payload.get('sub')
        request.player_type = payload.get('player_type')
        
        return f(*args, **kwargs)
    
    wrapper.__name__ = f.__name__
    wrapper.__doc__ = f.__doc__
    return wrapper


# =============================================
# Constants
# =============================================

GRACE_PERIOD_DAYS = 7


# =============================================
# Endpoints
# =============================================

@identity_ns.route('')
class IdentitiesList(Resource):
    """List linked OAuth identities."""
    
    @identity_ns.doc(security='Bearer')
    @identity_ns.response(200, 'Success', models['identities_response'])
    @identity_ns.response(401, 'Unauthorized', models['error_response'])
    @jwt_required
    def get(self):
        """
        List all OAuth identities linked to your account.
        
        Includes both active and soft-deleted identities.
        """
        identities = OAuthIdentity.query.filter_by(
            player_display_name=request.player_name
        ).order_by(OAuthIdentity.created_at.desc()).all()
        
        return {
            'identities': [identity.to_dict(include_deleted=True) for identity in identities],
            'count': len(identities)
        }, 200


@identity_ns.route('/<string:provider>')
class IdentityByProvider(Resource):
    """Manage a specific OAuth identity by provider."""
    
    @identity_ns.doc(security='Bearer')
    @identity_ns.response(200, 'Identity deleted', models['delete_response'])
    @identity_ns.response(400, 'Bad request', models['error_response'])
    @identity_ns.response(401, 'Unauthorized', models['error_response'])
    @identity_ns.response(404, 'Not found', models['error_response'])
    @jwt_required
    def delete(self, provider: str):
        """
        Request deletion of an OAuth identity.
        
        This is a soft delete with a 7-day grace period.
        You can restore the identity during this period.
        
        Note: You cannot delete your last remaining identity.
        """
        # Validate provider
        valid_providers = {'discord', 'google', 'slack'}
        if provider not in valid_providers:
            return {'error': f'Invalid provider. Must be one of: {valid_providers}'}, 400
        
        # Find the identity
        identity = OAuthIdentity.query.filter_by(
            player_display_name=request.player_name,
            provider=provider,
            deleted_at=None  # Only active identities
        ).first()
        
        if not identity:
            return {'error': f'No active {provider} identity found'}, 404
        
        # Check if this is the last identity
        active_count = OAuthIdentity.query.filter_by(
            player_display_name=request.player_name,
            deleted_at=None
        ).count()
        
        if active_count <= 1:
            return {
                'error': 'Cannot delete your last OAuth identity. '
                         'Link another provider first.'
            }, 400
        
        # Soft delete
        now = datetime.now(timezone.utc)
        identity.deleted_at = now
        db.session.commit()
        
        can_restore_until = now + timedelta(days=GRACE_PERIOD_DAYS)
        
        logger.info(
            f"Identity soft-deleted: {request.player_name} - {provider} "
            f"(can restore until {can_restore_until})"
        )
        
        return {
            'message': f'{provider} identity scheduled for deletion',
            'deleted_at': now.isoformat(),
            'can_restore_until': can_restore_until.isoformat()
        }, 200


@identity_ns.route('/<string:provider>/restore')
class RestoreIdentity(Resource):
    """Restore a soft-deleted OAuth identity."""
    
    @identity_ns.doc(security='Bearer')
    @identity_ns.response(200, 'Identity restored', models['restore_response'])
    @identity_ns.response(400, 'Bad request', models['error_response'])
    @identity_ns.response(401, 'Unauthorized', models['error_response'])
    @identity_ns.response(404, 'Not found', models['error_response'])
    @jwt_required
    def post(self, provider: str):
        """
        Restore a soft-deleted OAuth identity.
        
        Only works during the 7-day grace period after deletion.
        """
        # Validate provider
        valid_providers = {'discord', 'google', 'slack'}
        if provider not in valid_providers:
            return {'error': f'Invalid provider. Must be one of: {valid_providers}'}, 400
        
        # Find soft-deleted identity
        identity = OAuthIdentity.query.filter_by(
            player_display_name=request.player_name,
            provider=provider
        ).filter(
            OAuthIdentity.deleted_at.isnot(None)
        ).first()
        
        if not identity:
            return {'error': f'No deleted {provider} identity found'}, 404
        
        # Check if within grace period
        grace_deadline = identity.deleted_at + timedelta(days=GRACE_PERIOD_DAYS)
        if datetime.now(timezone.utc) > grace_deadline:
            return {
                'error': f'Grace period expired. Identity was permanently deleted.'
            }, 400
        
        # Restore
        identity.deleted_at = None
        db.session.commit()
        
        logger.info(f"Identity restored: {request.player_name} - {provider}")
        
        return {
            'message': f'{provider} identity restored',
            'identity': identity.to_dict()
        }, 200


# =============================================
# Cleanup Service (called by scheduler)
# =============================================

def cleanup_expired_deletions() -> int:
    """
    Permanently delete identities past their grace period.
    
    This should be called by a scheduled job.
    
    Returns:
        Number of identities permanently deleted
    """
    grace_cutoff = datetime.now(timezone.utc) - timedelta(days=GRACE_PERIOD_DAYS)
    
    expired = OAuthIdentity.query.filter(
        OAuthIdentity.deleted_at.isnot(None),
        OAuthIdentity.deleted_at < grace_cutoff
    ).all()
    
    count = len(expired)
    
    for identity in expired:
        logger.info(
            f"Permanently deleting identity: {identity.provider}:{identity.provider_user_id} "
            f"(player: {identity.player_display_name})"
        )
        db.session.delete(identity)
    
    if count > 0:
        db.session.commit()
        logger.info(f"Permanently deleted {count} expired OAuth identities")
    
    return count

