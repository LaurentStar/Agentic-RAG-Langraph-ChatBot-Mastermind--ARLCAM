"""
Database utilities and re-exports.

The game server uses Flask-SQLAlchemy for database access.
Connection is managed by `db` from extensions.py.
Models are defined in models/postgres_sql_db_models/.
"""

from app.extensions import db

__all__ = ["db"]

