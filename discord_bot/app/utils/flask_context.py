"""
Flask Context Utilities.

Provides decorators for database access from outside Flask's request cycle.

WHY THIS EXISTS:
Discord bot commands run in an async context, completely separate from
Flask's request/response cycle. Flask-SQLAlchemy requires an "app context"
to access the database. These utilities bridge that gap.

USAGE:
    from app.utils import requires_flask_db
    
    class MyService:
        _app: Flask = None  # Set via init_app()
        
        @classmethod
        @requires_flask_db
        def get_something(cls):
            return db.session.query(...)  # Works!
"""

import logging
from functools import wraps
from typing import Callable, TypeVar

logger = logging.getLogger("discord_bot")

T = TypeVar('T')

# Reference to Flask app (set by service that uses this)
_flask_app = None


def set_flask_app(app) -> None:
    """
    Set the Flask app reference for context creation.
    
    Called during app initialization.
    """
    global _flask_app
    _flask_app = app


def get_flask_app():
    """Get the Flask app reference."""
    return _flask_app


def requires_flask_db(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator: Wraps method with Flask app context for database access.
    
    Use on any method that:
    - Calls db.session (Flask-SQLAlchemy)
    - Runs outside Flask's request cycle (e.g., Discord commands)
    
    Example:
        @classmethod
        @requires_flask_db
        def get_user(cls, user_id: str):
            return db.session.get(User, user_id)
    
    The decorator:
    1. Checks if Flask app is initialized
    2. Wraps the call in app.app_context()
    3. Returns None if app not initialized (graceful failure)
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> T:
        # Try to get app from the class (if it has _app attribute)
        app = None
        if args and hasattr(args[0], '_app'):
            app = args[0]._app
        
        # Fallback to global
        if app is None:
            app = _flask_app
        
        if app is None:
            logger.warning(
                f"{func.__qualname__}: Flask app not initialized. "
                "Database operation skipped."
            )
            return None
        
        with app.app_context():
            return func(*args, **kwargs)
    
    return wrapper

