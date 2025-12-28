"""
Slack Bot Flask Application.

Flask-RESTX application factory for Slack bot REST APIs.
"""

# ---------------------- Standard Library ---------------------- #
import os
import logging

# ---------------------- Flask ---------------------- #
from flask import Flask
from flask_cors import CORS

# ---------------------- Extensions ---------------------- #
from app.extensions import api, db, slack_bot

# ---------------------- Namespaces ---------------------- #
from app.apis.health_ns import health_ns
from app.apis.broadcast_ns import broadcast_ns
from app.apis.admin_ns import admin_ns

# ---------------------- Models ---------------------- #
from app.database.db_models import SlackBotLog, TokenCache

# ---------------------- Services ---------------------- #
from app.services.token_cache_service import TokenCacheService


logger = logging.getLogger("slack_bot")


def create_app():
    """
    Flask application factory.
    
    Creates and configures the Flask app with all namespaces
    and extensions initialized.
    
    Returns:
        Tuple of (Flask application, Slack bot)
    """
    
    #-------------------#
    # CREATE FLASK APP  #
    #-------------------#
    app = Flask(__name__)
    app.config['RESTX_MASK_SWAGGER'] = False
    
    
    #-------------------#
    # SLACK BOT         #
    #-------------------#
    # slack_bot is declared in extensions.py
    # Store reference for use in endpoints
    app.slack_bot = slack_bot
    
    
    #-------------------#
    # DATABASE          #
    #-------------------#
    # db is declared in extensions.py
    db_url = os.getenv("SLACK_BOT_DATABASE_URL")
    if db_url:
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_size': 5,
            'pool_recycle': 300,
            'pool_pre_ping': True
        }
        db.init_app(app)
        logger.info("SQLAlchemy database initialized")
    else:
        logger.warning("SLACK_BOT_DATABASE_URL not set - database features disabled")
    
    
    #-------------------#
    # JWT CONFIG        #
    #-------------------#
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-secret-change-me-in-production')
    
    
    #-------------------#
    # CORS              #
    #-------------------#
    CORS(app)
    
    
    #-------------------#
    # REST API          #
    #-------------------#
    # api is declared in extensions.py (with authorizations for Swagger UI)
    api.init_app(
        app,
        title='Slack Bot API',
        version='1.0',
        description='REST APIs for Slack bot operations',
        doc='/docs'
    )
    
    
    #-------------------#
    # NAMESPACES        #
    #-------------------#
    api.add_namespace(health_ns, path='/health')
    api.add_namespace(broadcast_ns, path='/broadcast')
    api.add_namespace(admin_ns, path='/admin')
    
    
    #-------------------#
    # SLACK EVENTS      #
    #-------------------#
    # Register Slack Bolt routes with Flask
    slack_bot.register_flask_routes(app)
    
    
    #-------------------#
    # DATABASE TABLES   #
    #-------------------#
    if db_url:
        with app.app_context():
            db.create_all()
            logger.info("Database tables verified/created")
        
        # Initialize TokenCacheService with app for context access
        TokenCacheService.init_app(app)
    
    
    #-------------------#
    # STARTUP LOG       #
    #-------------------#
    logger.info("Slack Bot Flask app created")
    logger.info("  Swagger UI: /docs")
    logger.info("  Health: /health")
    logger.info("  Broadcast: /broadcast")
    logger.info("  Admin: /admin")
    logger.info("  Slack Events: /slack/events")
    
    return app, slack_bot
