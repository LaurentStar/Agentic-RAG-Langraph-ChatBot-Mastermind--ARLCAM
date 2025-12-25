"""
Player API Models.

Flask-RESTX models for player endpoints.
"""

from flask_restx import fields


def create_player_models(api):
    """Create and return player-related API models."""
    
    register_request = api.model('RegisterRequest', {
        'display_name': fields.String(required=True, description='Unique player identifier'),
        'password': fields.String(required=True, description='Player password'),
        'social_media_platform_display_name': fields.String(description='Username on platform (defaults to display_name)'),
        'social_media_platform': fields.String(description='Platform (discord, slack, twitter, etc.)', default='default'),
        'player_type': fields.String(description='Player type: human, llm_agent, or admin', default='human'),
        # Admin-specific
        'bootstrap_secret': fields.String(description='Secret key for first admin registration (from ADMIN_BOOTSTRAP_SECRET env var)'),
        'game_privileges': fields.List(fields.String, description='List of privileges for admin'),
        # LLM Agent-specific
        'personality_type': fields.String(description='LLM agent personality style', default='balanced'),
        'modulators': fields.Raw(description='LLM agent modulator values: {aggression, bluff_confidence, challenge_tendency, block_tendency, risk_tolerance, llm_reliance, model_name, temperature}')
    })
    
    register_llm_request = api.model('RegisterLLMRequest', {
        'display_name': fields.String(required=True, description='Unique agent identifier'),
        'password': fields.String(required=True, description='API key or password'),
        'social_media_platform_display_name': fields.String(required=True, description='Bot username'),
        'social_media_platform': fields.String(required=True, description='Platform'),
        'personality_type': fields.String(description='Personality style', default='balanced'),
        'modulators': fields.Raw(description='Modulator values dict')
    })
    
    player_response = api.model('PlayerResponse', {
        'display_name': fields.String(description='Player identifier'),
        'social_media_platform_display_name': fields.String(description='Username on platform'),
        'social_media_platform': fields.String(description='Platform'),
        'player_type': fields.String(description='Type of player'),
        'session_id': fields.String(description='Current game session'),
        'coins': fields.Integer(description='Current coin count'),
        'is_alive': fields.Boolean(description='Whether player is alive'),
        'game_privileges': fields.List(fields.String, description='Player privileges')
    })
    
    player_update_request = api.model('PlayerUpdateRequest', {
        'social_media_platform_display_name': fields.String(description='New username'),
        'social_media_platform': fields.String(description='New platform'),
        'game_privileges': fields.List(fields.String, description='New privileges')
    })
    
    player_list_response = api.model('PlayerListResponse', {
        'players': fields.List(fields.Nested(player_response)),
        'total': fields.Integer(description='Total player count')
    })
    
    error_response = api.model('PlayerErrorResponse', {
        'error': fields.String(description='Error message')
    })
    
    return {
        'register_request': register_request,
        'register_llm_request': register_llm_request,
        'player_response': player_response,
        'player_update_request': player_update_request,
        'player_list_response': player_list_response,
        'error_response': error_response
    }

