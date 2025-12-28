"""
OAuth Namespace.

OAuth2 authentication endpoints for Discord, Google, and Slack.
"""

import asyncio
import logging
import secrets
from functools import wraps

from flask import make_response, redirect, request, render_template, session, url_for
from flask_restx import Namespace, Resource


def html_response(template, status=200, **kwargs):
    """Render template and return as HTML response (not JSON)."""
    html = render_template(template, **kwargs)
    response = make_response(html, status)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response

from app.services.oauth_service import OAuthService

logger = logging.getLogger(__name__)

oauth_ns = Namespace('oauth', description='OAuth2 authentication')


def run_async(coro):
    """Run async function in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# =============================================
# Login Page
# =============================================

@oauth_ns.route('/login')
class OAuthLogin(Resource):
    """OAuth login page."""
    
    @oauth_ns.doc(responses={200: 'Login page HTML'})
    def get(self):
        """
        Render login page with OAuth buttons.
        
        Returns HTML page with Discord, Google, and Slack login options.
        """
        return html_response('login.html')


# =============================================
# Discord OAuth
# =============================================

@oauth_ns.route('/discord')
class DiscordAuth(Resource):
    """Discord OAuth2 authorization."""
    
    @oauth_ns.doc(responses={302: 'Redirect to Discord'})
    def get(self):
        """
        Redirect to Discord authorization page.
        
        Initiates Discord OAuth2 flow.
        """
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        session['oauth_state'] = state
        
        auth_url = OAuthService.get_discord_auth_url(state=state)
        logger.info(f"Redirecting to Discord OAuth: {auth_url}")
        
        return redirect(auth_url)


@oauth_ns.route('/discord/callback')
class DiscordCallback(Resource):
    """Discord OAuth2 callback."""
    
    @oauth_ns.doc(responses={
        200: 'Success - returns JWT tokens',
        400: 'Invalid request',
        401: 'Authentication failed'
    })
    def get(self):
        """
        Handle Discord OAuth2 callback.
        
        Exchanges authorization code for access token,
        creates/retrieves player, and returns JWT tokens.
        """
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        if error:
            logger.warning(f"Discord OAuth error: {error}")
            return html_response('auth_error.html', status=401, error=error)
        
        if not code:
            return html_response('auth_error.html', status=400, error="No authorization code provided")
        
        # Verify state (CSRF protection)
        # stored_state = session.pop('oauth_state', None)
        # if state != stored_state:
        #     return render_template('auth_error.html', error="Invalid state parameter"), 400
        
        # Handle callback (async)
        player, oauth_token, error_msg = run_async(
            OAuthService.handle_discord_callback(code)
        )
        
        if error_msg:
            logger.error(f"Discord OAuth callback error: {error_msg}")
            return html_response('auth_error.html', status=401, error=error_msg)
        
        # Generate JWT tokens
        access_token, refresh_token = OAuthService.create_tokens_for_player(player)
        
        logger.info(f"Discord OAuth success: {player.display_name}")
        
        return html_response(
            'auth_success.html',
            provider='Discord',
            display_name=player.display_name,
            access_token=access_token,
            refresh_token=refresh_token
        )


# =============================================
# Google OAuth
# =============================================

@oauth_ns.route('/google')
class GoogleAuth(Resource):
    """Google OAuth2 authorization."""
    
    @oauth_ns.doc(responses={302: 'Redirect to Google'})
    def get(self):
        """
        Redirect to Google authorization page.
        
        Initiates Google OAuth2 flow.
        """
        state = secrets.token_urlsafe(32)
        session['oauth_state'] = state
        
        auth_url = OAuthService.get_google_auth_url(state=state)
        logger.info(f"Redirecting to Google OAuth: {auth_url}")
        
        return redirect(auth_url)


@oauth_ns.route('/google/callback')
class GoogleCallback(Resource):
    """Google OAuth2 callback."""
    
    @oauth_ns.doc(responses={
        200: 'Success - returns JWT tokens',
        400: 'Invalid request',
        401: 'Authentication failed'
    })
    def get(self):
        """
        Handle Google OAuth2 callback.
        
        Exchanges authorization code for access token,
        creates/retrieves player, and returns JWT tokens.
        """
        code = request.args.get('code')
        error = request.args.get('error')
        
        if error:
            logger.warning(f"Google OAuth error: {error}")
            return html_response('auth_error.html', status=401, error=error)
        
        if not code:
            return html_response('auth_error.html', status=400, error="No authorization code provided")
        
        # Handle callback (async)
        player, oauth_token, error_msg = run_async(
            OAuthService.handle_google_callback(code)
        )
        
        if error_msg:
            logger.error(f"Google OAuth callback error: {error_msg}")
            return html_response('auth_error.html', status=401, error=error_msg)
        
        # Generate JWT tokens
        access_token, refresh_token = OAuthService.create_tokens_for_player(player)
        
        logger.info(f"Google OAuth success: {player.display_name}")
        
        return html_response(
            'auth_success.html',
            provider='Google',
            display_name=player.display_name,
            access_token=access_token,
            refresh_token=refresh_token
        )


# =============================================
# Slack OAuth
# =============================================

@oauth_ns.route('/slack')
class SlackAuth(Resource):
    """Slack OAuth2 authorization."""
    
    @oauth_ns.doc(responses={302: 'Redirect to Slack'})
    def get(self):
        """
        Redirect to Slack authorization page.
        
        Initiates Slack OAuth2 flow.
        """
        state = secrets.token_urlsafe(32)
        session['oauth_state'] = state
        
        auth_url = OAuthService.get_slack_auth_url(state=state)
        logger.info(f"Redirecting to Slack OAuth: {auth_url}")
        
        return redirect(auth_url)


@oauth_ns.route('/slack/callback')
class SlackCallback(Resource):
    """Slack OAuth2 callback."""
    
    @oauth_ns.doc(responses={
        200: 'Success - returns JWT tokens',
        400: 'Invalid request',
        401: 'Authentication failed'
    })
    def get(self):
        """
        Handle Slack OAuth2 callback.
        
        Exchanges authorization code for access token,
        creates/retrieves player, and returns JWT tokens.
        """
        code = request.args.get('code')
        error = request.args.get('error')
        
        if error:
            logger.warning(f"Slack OAuth error: {error}")
            return html_response('auth_error.html', status=401, error=error)
        
        if not code:
            return html_response('auth_error.html', status=400, error="No authorization code provided")
        
        # Handle callback (async)
        player, oauth_token, error_msg = run_async(
            OAuthService.handle_slack_callback(code)
        )
        
        if error_msg:
            logger.error(f"Slack OAuth callback error: {error_msg}")
            return html_response('auth_error.html', status=401, error=error_msg)
        
        # Generate JWT tokens
        access_token, refresh_token = OAuthService.create_tokens_for_player(player)
        
        logger.info(f"Slack OAuth success: {player.display_name}")
        
        return html_response(
            'auth_success.html',
            provider='Slack',
            display_name=player.display_name,
            access_token=access_token,
            refresh_token=refresh_token
        )


# =============================================
# Token by Provider (for Discord Bot integration)
# =============================================

@oauth_ns.route('/token-by-provider')
class TokenByProvider(Resource):
    """Get JWT token for a linked OAuth account."""
    
    @oauth_ns.doc(
        responses={
            200: 'Success - returns JWT tokens',
            400: 'Bad request - missing parameters',
            404: 'Account not linked'
        },
        params={
            'provider': 'OAuth provider (discord, google, slack)',
            'provider_user_id': 'User ID from the provider'
        }
    )
    def post(self):
        """
        Get JWT tokens for a user who has already linked their account.
        
        Used by Discord/Slack bots to get tokens for users who have
        previously completed the OAuth flow.
        
        Request body:
        {
            "provider": "discord",
            "provider_user_id": "123456789012345678"
        }
        
        Returns JWT access and refresh tokens if account is linked.
        Returns 404 if no linked account found.
        """
        data = request.get_json() or {}
        
        provider = data.get('provider')
        provider_user_id = data.get('provider_user_id')
        
        if not provider:
            return {"error": "Missing 'provider' parameter"}, 400
        
        if not provider_user_id:
            return {"error": "Missing 'provider_user_id' parameter"}, 400
        
        if provider not in ('discord', 'google', 'slack'):
            return {"error": "Invalid provider. Must be: discord, google, slack"}, 400
        
        # Look up the linked account
        player, error = OAuthService.get_player_by_provider(provider, str(provider_user_id))
        
        if error:
            logger.warning(f"Token lookup failed: {provider}:{provider_user_id} - {error}")
            return {"error": error}, 404
        
        # Generate JWT tokens
        access_token, refresh_token = OAuthService.create_tokens_for_player(player)
        
        logger.info(f"Token issued for {provider}:{provider_user_id} -> {player.display_name}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "player_display_name": player.display_name,
            "player_type": player.player_type.value if player.player_type else "human"
        }, 200

