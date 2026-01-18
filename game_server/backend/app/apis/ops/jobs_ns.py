"""
Jobs Namespace.

API endpoints for scheduled job introspection.
This file handles ONLY routing - all business logic is in OpsJobsService.
"""

from flask_restx import Namespace, Resource

from app.services.auth_service import ops_key_required
from app.services.ops import OpsJobsService


jobs_ns = Namespace('jobs', description='Scheduled job introspection')


@jobs_ns.route('')
class Jobs(Resource):
    """List all scheduled jobs."""
    
    @ops_key_required
    def get(self):
        """
        Get all scheduled jobs.
        
        Returns job list with types, triggers, and next run times.
        """
        return OpsJobsService.get_all_jobs(), 200


@jobs_ns.route('/<string:job_id>')
@jobs_ns.param('job_id', 'The job ID')
class JobById(Resource):
    """Get a specific job by ID."""
    
    @ops_key_required
    def get(self, job_id):
        """
        Get a specific job by ID.
        
        Returns job details or 404 if not found.
        """
        job = OpsJobsService.get_job_by_id(job_id)
        
        if not job:
            return {'error': f'Job not found: {job_id}'}, 404
        
        return job, 200


@jobs_ns.route('/session/<string:session_id>')
@jobs_ns.param('session_id', 'The game session ID')
class JobsBySession(Resource):
    """Get all jobs for a session."""
    
    @ops_key_required
    def get(self, session_id):
        """
        Get all jobs for a specific session.
        
        Returns list of jobs associated with the session.
        """
        jobs = OpsJobsService.get_jobs_by_session(session_id)
        
        return {
            'session_id': session_id,
            'job_count': len(jobs),
            'jobs': jobs
        }, 200

