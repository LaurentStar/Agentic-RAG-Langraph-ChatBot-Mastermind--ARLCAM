"""
Discord Bot Flask Application.

Flask-RESTX application factory for Discord bot REST APIs.
"""

# ---------------------- Standard Library ---------------------- #
import os
import logging

# ---------------------- Flask ---------------------- #
from flask import Flask
from flask_cors import CORS

# ---------------------- Extensions ---------------------- #
from app.extensions import api, db, bot

# ---------------------- Namespaces ---------------------- #
from app.apis.health_ns import health_ns
from app.apis.broadcast_ns import broadcast_ns
from app.apis.admin_ns import admin_ns

# ---------------------- Models ---------------------- #
from app.database.db_models import DiscordBotLog, TokenCache

# ---------------------- Services ---------------------- #
from app.services.token_cache_service import TokenCacheService


logger = logging.getLogger("discord_bot")


def create_app(bot_loop=None):
    """
    Flask application factory.
    
    Creates and configures the Flask app with all namespaces
    and extensions initialized.
    
    Args:
        bot_loop: The bot's asyncio event loop
    
    Returns:
        Tuple of (Flask application, Discord bot)
    """
    
    #-------------------#
    # CREATE FLASK APP  #
    #-------------------#
    app = Flask(__name__)
    app.config['RESTX_MASK_SWAGGER'] = False
    
    
    #-------------------#
    # DISCORD BOT       #
    #-------------------#
    # bot is declared in extensions.py
    # Store reference for use in endpoints
    app.bot_instance = bot
    app.bot_loop = bot_loop
    
    
    #-------------------#
    # DATABASE          #
    #-------------------#
    # db is declared in extensions.py
    db_url = os.getenv("SQLALCHEMY_DATABASE_URI")
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
        logger.warning("SQLALCHEMY_DATABASE_URI not set - database features disabled")
    
    
    #-------------------#
    # JWT CONFIG        #
    #-------------------#
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-secret-change-me')
    
    
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
        title='Discord Bot API',
        version='1.0',
        description='REST APIs for Discord bot operations',
        doc='/docs'
    )
    
    
    #-------------------#
    # NAMESPACES        #
    #-------------------#
    api.add_namespace(health_ns, path='/health')
    api.add_namespace(broadcast_ns, path='/broadcast')
    api.add_namespace(admin_ns, path='/admin')
    
    
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
    logger.info("Discord Bot Flask app created")
    logger.info("  Swagger UI: /docs")
    logger.info("  Health: /health")
    logger.info("  Broadcast: /broadcast")
    logger.info("  Admin: /admin")
    
    return app, bot
