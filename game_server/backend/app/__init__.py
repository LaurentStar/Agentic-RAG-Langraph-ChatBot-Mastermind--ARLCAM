"""
Game Server Application Factory.

Creates and configures the Flask application with all extensions,
namespaces, and database models.
"""

import os

from flask import Flask
from flask_apscheduler import APScheduler

from app.extensions import api, db, cors
from app.lifecycle import create_default_admin_if_enabled

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
    admin_flags_ns,
    # Account
    link_ns,
    identity_ns,
    # Users
    user_ns,
    # Profiles
    profile_ns,
    # Game
    actions_ns,
    chat_ns,
    reactions_ns,
    state_ns,
    game_session_ns,
    # Players (DEPRECATED)
    player_ns,
    # System
    health_ns,
    # Ops (Developer)
    status_ns,
    jobs_ns,
    connections_ns,
)

# Import all models (required for db.create_all() to work)
from app.models.postgres_sql_db_models import (
    AccountFlag,
    AccountLinkRequest,
    AgentProfile,
    BroadcastDestination,
    ChatBotEndpoint,
    ChatMessage,
    GameServerLog,
    GameSession,
    OAuthIdentity,
    PlayerGameState,
    PlayerProfile,
    Reaction,
    ToBeInitiatedUpgradeDetails,
    TurnResultORM,
    UserAccount,
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
    
    # CORS (allow frontend origins with credentials for HTTP-only cookies)
    cors.init_app(app, origins=[
        "http://localhost:4001",
        "http://127.0.0.1:4001"
    ], supports_credentials=True)
    
    # REST API
    # api is declared in extensions.py (with authorizations for Swagger UI)
    api.init_app(
        app,
        version='1.0',
        title='Game Server API',
        description='APIs for managing Coup game sessions, players, and gameplay'
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
    api.add_namespace(admin_flags_ns, path='/admin/flags')
    
    # Account domain
    api.add_namespace(link_ns, path='/account/link')
    api.add_namespace(identity_ns, path='/account/identities')
    
    # Users domain
    api.add_namespace(user_ns, path='/users')
    
    # Profiles domain
    api.add_namespace(profile_ns, path='/profiles')
    
    # Game domain
    api.add_namespace(game_session_ns, path='/game/sessions')
    api.add_namespace(actions_ns, path='/game/actions')
    api.add_namespace(chat_ns, path='/game/chat')
    api.add_namespace(reactions_ns, path='/game/reactions')
    api.add_namespace(state_ns, path='/game/state')
    
    # Players domain (DEPRECATED - use /users and /profiles)
    api.add_namespace(player_ns, path='/players')
    
    # System domain
    api.add_namespace(health_ns, path='/health')
    
    # Ops domain (Developer)
    api.add_namespace(status_ns, path='/ops/status')
    api.add_namespace(jobs_ns, path='/ops/jobs')
    api.add_namespace(connections_ns, path='/ops/connections')
    
    # =============================================
    # LOCAL DEVELOPMENT (conditional)
    # =============================================
    if os.getenv("ENVIRONMENT", "local") == "local":
        from app.apis.local.proxy import slack_proxy_ns
        
        # Register proxy routes
        api.add_namespace(slack_proxy_ns, path='/local/proxy/slack')
        
        # Start ngrok tunnel only in the worker process (not the reloader)
        # When debug=True, Flask spawns 2 processes. WERKZEUG_RUN_MAIN is only
        # set in the worker process. When debug=False, there's no reloader,
        # so we also start ngrok in that case.
        # Check if debug mode is enabled via environment variable
        # (app.debug is not set yet during create_app - it's set by app.run())
        debug_mode = os.getenv("GAME_SERVER_DEBUG", "False").lower() == "true"
        is_worker_process = os.getenv("WERKZEUG_RUN_MAIN") == "true"
        
        if is_worker_process or not debug_mode:
            from app.lifecycle.ngrok_tunnel import start_tunnel
            
            port = int(os.getenv("GAME_SERVER_PORT", "4000"))
            public_url = start_tunnel(port)
            if public_url:
                app.logger.info(f"Local development mode enabled")
                app.logger.info(f"Public URL: {public_url}")
                app.logger.info(f"Slack events: {public_url}/local/proxy/slack/events")
                app.logger.info(f"Slack commands: {public_url}/local/proxy/slack/commands")
    
    # ---------------------- Create Database Tables ---------------------- #
    with app.app_context():
        # Create all tables for the db_players bind
        db.create_all(bind_key='db_players')
        
        # Create default admin if enabled
        create_default_admin_if_enabled(app)
    
    return app
