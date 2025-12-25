"""
Slack Bot Application.

A Slack bot that integrates with the game server for cross-platform chat.
Uses Slack Bolt for event handling and Flask for the broadcast endpoint.

Features:
- Forwards game channel messages to game_server
- Receives broadcast pushes from game_server
- Posts formatted messages to Slack channel
"""

import os
import logging
from typing import Optional

import httpx
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("slack_bot")

# =============================================
# Configuration
# =============================================

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
GAME_SERVER_URL = os.environ.get("GAME_SERVER_URL", "http://localhost:5000")
GAME_SESSION_ID = os.environ.get("GAME_SESSION_ID", "")
GAME_CHANNEL_ID = os.environ.get("SLACK_GAME_CHANNEL", "")
BROADCAST_PORT = int(os.environ.get("SLACK_BROADCAST_PORT", "3002"))

# Validate required config
if not SLACK_BOT_TOKEN:
    logger.warning("SLACK_BOT_TOKEN not set - Slack features will not work")
if not SLACK_SIGNING_SECRET:
    logger.warning("SLACK_SIGNING_SECRET not set - Slack events will not verify")

# =============================================
# Slack Bolt App
# =============================================

slack_app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET,
    # Ignore missing token/secret for development
    token_verification_enabled=bool(SLACK_BOT_TOKEN)
)

# =============================================
# Flask App for Broadcast Endpoint
# =============================================

flask_app = Flask(__name__)
handler = SlackRequestHandler(slack_app)

# User cache to avoid repeated API calls
_user_cache = {}


def get_user_name(client, user_id: str) -> str:
    """
    Get user's display name from Slack API.
    
    Caches results to avoid repeated API calls.
    """
    if user_id in _user_cache:
        return _user_cache[user_id]
    
    try:
        result = client.users_info(user=user_id)
        if result["ok"]:
            user = result["user"]
            name = user.get("real_name") or user.get("display_name") or user.get("name", user_id)
            _user_cache[user_id] = name
            return name
    except Exception as e:
        logger.warning(f"Failed to get user info for {user_id}: {e}")
    
    return user_id


def send_to_game_server(sender: str, content: str) -> bool:
    """
    Send a message to the game server chat queue.
    
    Args:
        sender: Sender's display name
        content: Message content
    
    Returns:
        True if successful
    """
    if not GAME_SESSION_ID:
        logger.warning("GAME_SESSION_ID not configured")
        return False
    
    url = f"{GAME_SERVER_URL}/game/chat/{GAME_SESSION_ID}/send"
    payload = {
        "sender": sender,
        "platform": "slack",
        "content": content
    }
    
    try:
        response = httpx.post(url, json=payload, timeout=10.0)
        if response.status_code == 201:
            logger.debug(f"Message from {sender} sent to game server")
            return True
        else:
            logger.warning(f"Failed to send message: {response.status_code} - {response.text}")
            return False
    except httpx.HTTPError as e:
        logger.error(f"Failed to connect to game server: {e}")
        return False


# =============================================
# Slack Event Handlers
# =============================================

@slack_app.message("")
def handle_message(message, say, client):
    """
    Handle incoming messages from Slack channels.
    
    Forwards messages from the game channel to the game server.
    """
    # Only process messages from the game channel
    channel = message.get("channel", "")
    if channel != GAME_CHANNEL_ID:
        return
    
    # Ignore bot messages
    if message.get("bot_id"):
        return
    
    # Ignore message subtypes (edits, deletes, etc.)
    if message.get("subtype"):
        return
    
    # Get sender info
    user_id = message.get("user", "")
    sender = get_user_name(client, user_id)
    content = message.get("text", "")
    
    if not content.strip():
        return
    
    # Send to game server
    logger.info(f"Forwarding message from {sender} to game server")
    send_to_game_server(sender, content)


@slack_app.command("/gamechat")
def handle_gamechat_command(ack, respond, command):
    """
    Handle /gamechat slash command.
    
    Usage:
        /gamechat status - Show configuration
        /gamechat session <id> - Set session ID (admin)
    """
    ack()
    
    text = command.get("text", "").strip()
    args = text.split()
    
    if not args or args[0] == "status":
        respond({
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "🎮 Game Chat Status"}
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Game Server:*\n{GAME_SERVER_URL}"},
                        {"type": "mrkdwn", "text": f"*Session ID:*\n{GAME_SESSION_ID or '(not set)'}"},
                        {"type": "mrkdwn", "text": f"*Game Channel:*\n<#{GAME_CHANNEL_ID}>" if GAME_CHANNEL_ID else "*(not set)*"}
                    ]
                }
            ]
        })
    else:
        respond({
            "response_type": "ephemeral",
            "text": f"Unknown subcommand: {args[0]}. Use `/gamechat status`."
        })


# =============================================
# Flask Routes
# =============================================

@flask_app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "service": "slack_bot",
        "slack_configured": bool(SLACK_BOT_TOKEN),
        "session_id": GAME_SESSION_ID or None,
        "game_channel": GAME_CHANNEL_ID or None
    }), 200


@flask_app.route('/api/broadcast', methods=['POST'])
def receive_broadcast():
    """
    Receive chat broadcast from game_server.
    
    Expected payload:
    {
        "session_id": "...",
        "broadcast_time": "...",
        "message_count": N,
        "messages": [
            {"sender": "...", "platform": "...", "content": "...", "timestamp": "..."},
            ...
        ]
    }
    """
    if not SLACK_BOT_TOKEN:
        return jsonify({"error": "Slack not configured"}), 503
    
    if not GAME_CHANNEL_ID:
        return jsonify({"error": "Game channel not configured"}), 503
    
    data = request.json or {}
    messages = data.get('messages', [])
    session_id = data.get('session_id', 'unknown')
    
    if not messages:
        logger.debug(f"No messages in broadcast for session {session_id}")
        return jsonify({"status": "no_messages"}), 200
    
    logger.info(f"Received broadcast with {len(messages)} messages for session {session_id}")
    
    # Build Slack blocks
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "📢 Game Chat Update", "emoji": True}
        },
        {"type": "divider"}
    ]
    
    for msg in messages:
        # Platform indicator
        if msg.get('platform') == 'discord':
            icon = ":video_game:"
        elif msg.get('platform') == 'slack':
            icon = ":slack:"
        else:
            icon = ":speech_balloon:"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{icon} *{msg.get('sender', 'Unknown')}*: {msg.get('content', '')}"
            }
        })
    
    # Post to Slack channel
    try:
        slack_app.client.chat_postMessage(
            channel=GAME_CHANNEL_ID,
            blocks=blocks,
            text=f"Game Chat Update: {len(messages)} new messages"  # Fallback text
        )
        logger.info(f"Posted broadcast with {len(messages)} messages to Slack")
        return jsonify({
            "status": "received",
            "message_count": len(messages)
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to post to Slack: {e}")
        return jsonify({"error": str(e)}), 500


@flask_app.route('/slack/events', methods=['POST'])
def slack_events():
    """Handle Slack events (including URL verification)."""
    return handler.handle(request)


@flask_app.route('/slack/interactions', methods=['POST'])
def slack_interactions():
    """Handle Slack interactive components."""
    return handler.handle(request)


# =============================================
# Main Entry Point
# =============================================

if __name__ == "__main__":
    logger.info("Starting Slack bot...")
    logger.info(f"  Game Server URL: {GAME_SERVER_URL}")
    logger.info(f"  Session ID: {GAME_SESSION_ID or '(not set)'}")
    logger.info(f"  Game Channel: {GAME_CHANNEL_ID or '(not set)'}")
    logger.info(f"  Broadcast Port: {BROADCAST_PORT}")
    
    # Run Flask app (handles both broadcast endpoint and Slack events)
    flask_app.run(
        host='0.0.0.0',
        port=BROADCAST_PORT,
        debug=os.environ.get("DEBUG", "").lower() == "true"
    )

