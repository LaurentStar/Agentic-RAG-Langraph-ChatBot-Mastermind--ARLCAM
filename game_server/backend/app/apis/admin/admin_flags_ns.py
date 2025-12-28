"""
Admin Account Flags Namespace.

Admin-only endpoints for reviewing account flags.
"""

import logging
from flask import request
from flask_restx import Namespace, Resource, fields

from app.services.account_flag_service import AccountFlagService
from app.services.auth_service import admin_required

logger = logging.getLogger(__name__)

# Create namespace
admin_flags_ns = Namespace(
    'admin-flags',
    description='Account flag management (admin only)'
)


# =============================================
# API Models
# =============================================

flag_model = admin_flags_ns.model('AccountFlag', {
    'id': fields.Integer(description='Flag ID'),
    'player_display_name': fields.String(description='Flagged player'),
    'flag_type': fields.String(description='Flag type (similar_username, suspicious_linking, etc.)'),
    'related_player': fields.String(description='Related player (if applicable)'),
    'details': fields.Raw(description='Additional context as JSON'),
    'status': fields.String(description='Flag status (pending, reviewed, dismissed, actioned)'),
    'reviewed_by': fields.String(description='Admin who reviewed'),
    'review_notes': fields.String(description='Review notes'),
    'created_at': fields.String(description='When flag was created'),
    'reviewed_at': fields.String(description='When flag was reviewed')
})

flags_list_response = admin_flags_ns.model('FlagsListResponse', {
    'flags': fields.List(fields.Nested(flag_model), description='List of flags'),
    'total': fields.Integer(description='Total count'),
    'limit': fields.Integer(description='Query limit'),
    'offset': fields.Integer(description='Query offset')
})

flag_stats_response = admin_flags_ns.model('FlagStatsResponse', {
    'pending': fields.Integer(description='Pending flags'),
    'reviewed': fields.Integer(description='Reviewed flags'),
    'dismissed': fields.Integer(description='Dismissed flags'),
    'actioned': fields.Integer(description='Actioned flags'),
    'total': fields.Integer(description='Total flags')
})

review_request = admin_flags_ns.model('ReviewFlagRequest', {
    'action': fields.String(
        required=True,
        description='Review action (reviewed, dismissed, actioned)',
        enum=['reviewed', 'dismissed', 'actioned']
    ),
    'notes': fields.String(
        required=False,
        description='Optional review notes'
    )
})

review_response = admin_flags_ns.model('ReviewFlagResponse', {
    'message': fields.String(description='Result message'),
    'flag': fields.Nested(flag_model)
})

error_response = admin_flags_ns.model('FlagErrorResponse', {
    'error': fields.String(description='Error message')
})


# =============================================
# Endpoints
# =============================================

@admin_flags_ns.route('')
class FlagsList(Resource):
    """List account flags."""
    
    @admin_flags_ns.doc(
        security='Bearer',
        params={
            'status': 'Filter by status (pending, reviewed, dismissed, actioned)',
            'limit': 'Maximum results (default 50)',
            'offset': 'Skip N results (default 0)'
        }
    )
    @admin_flags_ns.response(200, 'Success', flags_list_response)
    @admin_required
    def get(self):
        """
        List account flags with optional status filter.
        
        Default shows pending flags. Set status=all to see all.
        """
        status = request.args.get('status', 'pending')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        if status == 'all':
            # Get all flags with pagination
            from app.models.postgres_sql_db_models import AccountFlag
            from app.extensions import db
            
            query = AccountFlag.query.order_by(AccountFlag.created_at.desc())
            total = query.count()
            flags = query.offset(offset).limit(limit).all()
        else:
            flags, total = AccountFlagService.get_flags_by_status(
                status=status,
                limit=limit,
                offset=offset
            )
        
        return {
            'flags': [f.to_dict() for f in flags],
            'total': total,
            'limit': limit,
            'offset': offset
        }, 200


@admin_flags_ns.route('/stats')
class FlagsStats(Resource):
    """Get flag statistics."""
    
    @admin_flags_ns.doc(security='Bearer')
    @admin_flags_ns.response(200, 'Success', flag_stats_response)
    @admin_required
    def get(self):
        """Get statistics about account flags."""
        return AccountFlagService.get_flag_stats(), 200


@admin_flags_ns.route('/<int:flag_id>')
@admin_flags_ns.param('flag_id', 'The flag ID')
class FlagResource(Resource):
    """Single flag operations."""
    
    @admin_flags_ns.doc(security='Bearer')
    @admin_flags_ns.response(200, 'Success', flag_model)
    @admin_flags_ns.response(404, 'Not found', error_response)
    @admin_required
    def get(self, flag_id: int):
        """Get details of a specific flag."""
        flag = AccountFlagService.get_flag_by_id(flag_id)
        
        if not flag:
            return {'error': f'Flag {flag_id} not found'}, 404
        
        return flag.to_dict(), 200
    
    @admin_flags_ns.doc(security='Bearer')
    @admin_flags_ns.expect(review_request)
    @admin_flags_ns.response(200, 'Success', review_response)
    @admin_flags_ns.response(400, 'Bad request', error_response)
    @admin_flags_ns.response(404, 'Not found', error_response)
    @admin_required
    def patch(self, flag_id: int):
        """
        Review a flag.
        
        Set the flag's status to reviewed, dismissed, or actioned.
        """
        data = request.get_json() or {}
        
        action = data.get('action')
        notes = data.get('notes')
        
        if not action:
            return {'error': 'action is required'}, 400
        
        # Get admin name from request context
        admin_name = getattr(request, 'player_name', 'unknown')
        
        flag, error = AccountFlagService.review_flag(
            flag_id=flag_id,
            action=action,
            admin_name=admin_name,
            notes=notes
        )
        
        if error:
            status_code = 404 if 'not found' in error.lower() else 400
            return {'error': error}, status_code
        
        return {
            'message': f'Flag {flag_id} marked as {action}',
            'flag': flag.to_dict()
        }, 200


@admin_flags_ns.route('/player/<string:display_name>')
@admin_flags_ns.param('display_name', 'Player display name')
class PlayerFlags(Resource):
    """Get flags for a specific player."""
    
    @admin_flags_ns.doc(security='Bearer')
    @admin_flags_ns.response(200, 'Success', flags_list_response)
    @admin_required
    def get(self, display_name: str):
        """Get all flags for a specific player."""
        flags = AccountFlagService.get_flags_for_player(display_name)
        
        return {
            'flags': [f.to_dict() for f in flags],
            'total': len(flags),
            'limit': None,
            'offset': 0
        }, 200

