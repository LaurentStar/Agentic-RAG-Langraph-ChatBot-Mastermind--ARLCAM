"""
Health Check Namespace.

Provides liveness and readiness endpoints for infrastructure monitoring.
"""

from flask_restx import Namespace, Resource

from app.extensions import db

health_ns = Namespace('health', description='Health check endpoints')


@health_ns.route('/liveness')
class Liveness(Resource):
    """Liveness probe endpoint."""
    
    def get(self):
        """Basic alive check - returns 200 if server is running."""
        return {'status': 'alive'}, 200


@health_ns.route('/readiness')
class Readiness(Resource):
    """Readiness probe endpoint."""
    
    def get(self):
        """Check if all dependencies are ready."""
        checks = {
            'database': False,
            'status': 'not_ready'
        }
        
        # Check database connection
        try:
            db.session.execute(db.text('SELECT 1'))
            checks['database'] = True
        except Exception as e:
            checks['database_error'] = str(e)
        
        # Determine overall status
        if all([checks['database']]):
            checks['status'] = 'ready'
            return checks, 200
        else:
            checks['status'] = 'not_ready'
            return checks, 503

