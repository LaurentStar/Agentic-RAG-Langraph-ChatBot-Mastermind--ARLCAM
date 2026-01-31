"""
Player API Models.

Flask-RESTX models for player endpoints.
"""

from flask_restx import fields


def create_player_models(api):
    """Create and return player-related API models."""
    
    register_request = api.model('RegisterRequest', {
        'user_name': fields.String(required=True, description='Unique login identifier'),
        'display_name': fields.String(required=True, description='Unique public display name'),
        'password': fields.String(required=True, description='Account password'),
        'email': fields.String(description='Optional email address'),
        'social_media_platform_display_name': fields.String(description='Username on platform (defaults to display_name)'),
        'platform': fields.String(description='Platform (discord, slack, default, etc.)', default='default'),
        'player_type': fields.String(description='Player type: human, llm_agent, or admin', default='human'),
        # Admin-specific
        'bootstrap_secret': fields.String(description='Secret key for first admin registration (from ADMIN_BOOTSTRAP_SECRET env var)'),
        'game_privileges': fields.List(fields.String, description='List of privileges for admin'),
        # LLM Agent-specific
        'personality_type': fields.String(description='LLM agent personality style', default='balanced'),
        'modulators': fields.Raw(description='LLM agent modulator values: {aggression, bluff_confidence, challenge_tendency, block_tendency, risk_tolerance, llm_reliance, model_name, temperature}')
    })
    
    register_llm_request = api.model('RegisterLLMRequest', {
        'user_name': fields.String(required=True, description='Unique login identifier'),
        'display_name': fields.String(required=True, description='Unique agent display name'),
        'password': fields.String(required=True, description='API key or password'),
        'social_media_platform_display_name': fields.String(required=True, description='Bot username'),
        'platform': fields.String(required=True, description='Platform (discord, slack, default, etc.)'),
        'personality_type': fields.String(description='Personality style', default='balanced'),
        'modulators': fields.Raw(description='Modulator values dict')
    })
    
    # User account response (identity + account info)
    user_account_response = api.model('UserAccountResponse', {
        'user_id': fields.String(description='Unique user UUID'),
        'user_name': fields.String(description='Login identifier'),
        'display_name': fields.String(description='Public display name'),
        'email': fields.String(description='Email address (if set)'),
        'email_verified': fields.Boolean(description='Email verification status'),
        'player_type': fields.String(description='Type of player'),
        'account_status': fields.String(description='Account status (active, suspended, banned)'),
        'social_media_platforms': fields.List(fields.String, description='All platforms registered on'),
        'preferred_social_media_platform': fields.String(description='Preferred platform'),
        'game_privileges': fields.List(fields.String, description='Player privileges'),
        'created_at': fields.String(description='Account creation timestamp'),
    })
    
    # Player profile response (stats + preferences)
    player_profile_response = api.model('PlayerProfileResponse', {
        'user_id': fields.String(description='User UUID'),
        'avatar_url': fields.String(description='Avatar URL'),
        'bio': fields.String(description='Player bio'),
        'games_played': fields.Integer(description='Total games played'),
        'games_won': fields.Integer(description='Total games won'),
        'games_lost': fields.Integer(description='Total games lost'),
        'win_rate': fields.Float(description='Win rate percentage'),
        'rank': fields.String(description='Player rank'),
        'elo': fields.Integer(description='ELO rating'),
        'level': fields.Integer(description='Player level'),
        'xp': fields.Integer(description='Experience points'),
    })
    
    # Combined player response (account + current game state)
    player_response = api.model('PlayerResponse', {
        'user_id': fields.String(description='Unique user UUID'),
        'user_name': fields.String(description='Login identifier'),
        'display_name': fields.String(description='Public display name'),
        'social_media_platform_display_name': fields.String(description='Username on platform'),
        'social_media_platforms': fields.List(fields.String, description='All platforms registered on'),
        'preferred_social_media_platform': fields.String(description='Preferred platform'),
        'player_type': fields.String(description='Type of player'),
        'session_id': fields.String(description='Current game session (if in game)'),
        'coins': fields.Integer(description='Current coin count (if in game)'),
        'is_alive': fields.Boolean(description='Whether player is alive (if in game)'),
        'game_privileges': fields.List(fields.String, description='Player privileges')
    })
    
    # Player stats response
    player_stats_response = api.model('PlayerStatsResponse', {
        'games_played': fields.Integer(description='Total games played'),
        'games_won': fields.Integer(description='Total games won'),
        'games_lost': fields.Integer(description='Total games lost'),
        'games_abandoned': fields.Integer(description='Games abandoned'),
        'win_rate': fields.Float(description='Win rate percentage'),
        'rank': fields.String(description='Current rank'),
        'elo': fields.Integer(description='ELO rating'),
        'level': fields.Integer(description='Player level'),
        'xp': fields.Integer(description='Experience points'),
    })
    
    player_update_request = api.model('PlayerUpdateRequest', {
        'display_name': fields.String(description='New display name'),
        'social_media_platform_display_name': fields.String(description='New platform username'),
        'preferred_social_media_platform': fields.String(description='Set preferred platform'),
        'avatar_url': fields.String(description='New avatar URL'),
        'bio': fields.String(description='New bio text'),
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
        'user_account_response': user_account_response,
        'player_profile_response': player_profile_response,
        'player_response': player_response,
        'player_stats_response': player_stats_response,
        'player_update_request': player_update_request,
        'player_list_response': player_list_response,
        'error_response': error_response
    }
