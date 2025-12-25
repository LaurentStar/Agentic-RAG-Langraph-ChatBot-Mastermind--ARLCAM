"""
Broadcast Namespace.

Receives chat broadcasts from game_server and routes to Discord.
Migrated from broadcast_server.py.
"""

import logging

from flask import current_app, request
from flask_restx import Namespace, Resource

from app.services.broadcast_service import BroadcastService
from app.services.logging_service import LoggingService
from app.models.rest_api_models.broadcast_models import register_broadcast_models

logger = logging.getLogger(__name__)

broadcast_ns = Namespace('broadcast', description='Game server broadcast operations')

# Register models with namespace
models = register_broadcast_models(broadcast_ns)


@broadcast_ns.route('')
class BroadcastReceive(Resource):
    """Receive and route broadcasts from game_server."""
    
    @broadcast_ns.expect(models['broadcast_request'])
    @broadcast_ns.response(200, 'Broadcast received', models['broadcast_response'])
    @broadcast_ns.response(404, 'Channel not found', models['broadcast_error'])
    @broadcast_ns.response(503, 'Bot not ready', models['broadcast_error'])
    def post(self):
        """
        Receive chat broadcast from game_server.
        
        Routes messages to the correct Discord channel based on session_id.
        Uses the GameChat cog's channel registry for routing.
        """
        bot = getattr(current_app, 'bot_instance', None)
        loop = getattr(current_app, 'bot_loop', None)
        
        if not bot:
            logger.error("Bot instance not set")
            return {"error": "Bot not initialized"}, 503
        
        if not bot.is_ready():
            logger.error("Bot not ready")
            return {"error": "Bot not ready"}, 503
        
        data = request.json or {}
        messages = data.get('messages', [])
        session_id = data.get('session_id', 'unknown')
        
        if not messages:
            logger.debug(f"No messages in broadcast for session {session_id}")
            return {"status": "no_messages", "session_id": session_id}, 200
        
        logger.info(f"Received broadcast with {len(messages)} messages for session {session_id}")
        
        # Route to Discord
        success, error = BroadcastService.post_to_discord_sync(
            bot, loop, session_id, messages
        )
        
        # Log the broadcast
        try:
            LoggingService.log_broadcast(
                session_id=session_id,
                message_count=len(messages),
                success=success,
                error=error
            )
        except Exception as e:
            logger.warning(f"Failed to log broadcast: {e}")
        
        if success:
            return {
                "status": "received",
                "session_id": session_id,
                "message_count": len(messages)
            }, 200
        else:
            return {
                "error": error or "Failed to post to Discord",
                "session_id": session_id,
                "hint": "No channel registered for this session?"
            }, 404
