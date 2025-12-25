"""
Game Server Application Factory.

Creates and configures the Flask application with all extensions,
namespaces, and database models.
"""

import os

from flask import Flask
from flask_apscheduler import APScheduler

from app.extensions import api, db

# Get the directory where this __init__.py file is located
APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Import all namespaces from organized structure
from app.apis import (
    # Auth
    auth_ns,
    oauth_ns,
    # Admin
    admin_session_ns,
    admin_player_ns,
    # Game
    actions_ns,
    chat_ns,
    reactions_ns,
    state_ns,
    game_session_ns,
    # Players
    player_ns,
    # System
    health_ns,
)

# Import all models (required for db.create_all() to work)
from app.models.postgres_sql_db_models import (
    AgentProfile,
    BroadcastDestination,
    ChatBotEndpoint,
    ChatMessage,
    GameSession,
    OAuthIdentity,
    Player,
    Reaction,
    ToBeInitiatedUpgradeDetails,
    TurnResultORM,
)

# Scheduler instance (declared here, initialized in create_app)
scheduler = APScheduler()


def create_app(test_config=None):
    """Create and configure the Flask application."""
    
    # ---------------------- Create Flask App ---------------------- #
    # Configure template and static folder paths relative to app directory
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=os.path.join(APP_DIR, 'templates'),
        static_folder=os.path.join(APP_DIR, 'static'),
        static_url_path='/static'
    )
    
    # ---------------------- Configuration ---------------------- #
    # Database connection - uses postgres user from Docker container
    db_uri = "postgresql+psycopg://postgres:mysecretpassword@localhost:5432/postgres"
    app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config['SQLALCHEMY_BINDS'] = {
        'db_players': db_uri,  # Use same database for all tables
    }
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {'connect_timeout': 10}
    }
    
    # JWT Configuration
    app.config['JWT_SECRET_KEY'] = "dev-secret-change-me-in-production"
    
    # Session Configuration (for OAuth state)
    app.config['SECRET_KEY'] = "dev-session-secret-change-me"
    
    # APScheduler Configuration
    app.config['SCHEDULER_API_ENABLED'] = True
    
    # Override with test config if provided
    if test_config:
        app.config.update(test_config)
    
    # ---------------------- Initialize Extensions ---------------------- #
    
    # Database
    db.init_app(app)
    
    # REST API
    # JWT Bearer token authorization for Swagger UI
    authorizations = {
        'Bearer': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization',
            'description': 'JWT token. Format: "Bearer {token}"'
        }
    }
    
    api.init_app(
        app,
        version='1.0',
        title='Game Server API',
        description='APIs for managing Coup game sessions, players, and gameplay',
        authorizations=authorizations,
        security='Bearer'
    )
    
    # Scheduler
    scheduler.init_app(app)
    scheduler.start()
    
    # ---------------------- Register Namespaces ---------------------- #
    
    # Auth domain
    api.add_namespace(auth_ns, path='/auth')
    api.add_namespace(oauth_ns, path='/auth/oauth')
    
    # Admin domain
    api.add_namespace(admin_session_ns, path='/admin/sessions')
    api.add_namespace(admin_player_ns, path='/admin/players')
    
    # Game domain
    api.add_namespace(game_session_ns, path='/game/sessions')
    api.add_namespace(actions_ns, path='/game/actions')
    api.add_namespace(chat_ns, path='/game/chat')
    api.add_namespace(reactions_ns, path='/game/reactions')
    api.add_namespace(state_ns, path='/game/state')
    
    # Players domain
    api.add_namespace(player_ns, path='/players')
    
    # System domain
    api.add_namespace(health_ns, path='/health')
    
    # ---------------------- Create Database Tables ---------------------- #
    with app.app_context():
        # Create all tables for the db_players bind
        db.create_all(bind_key='db_players')
    
    return app
