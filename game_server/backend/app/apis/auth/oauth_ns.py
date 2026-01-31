"""
OAuth Namespace.

OAuth2 authentication endpoints for Discord, Google, and Slack.
"""

import asyncio
import logging
import os
import secrets

from flask import make_response, redirect, render_template, request, session
from flask_restx import Namespace, Resource

from app.models.rest_api_models.auth_models import create_oauth_models
from app.services.auth_service import AuthService
from app.services.oauth_service import OAuthService

logger = logging.getLogger(__name__)

# Frontend URL for OAuth redirects (with cookie-based auth)
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:4001')

# Namespace and models
oauth_ns = Namespace('oauth', description='OAuth2 authentication')
oauth_models = create_oauth_models(oauth_ns)


# =============================================
# Internal Helpers
# =============================================

def _html_response(template, status=200, **kwargs):
    """Render template and return as HTML response (not JSON)."""
    html = render_template(template, **kwargs)
    response = make_response(html, status)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response


def _create_oauth_success_response(user, provider: str):
    """
    Create response for successful OAuth login.
    
    Sets HTTP-only cookies and redirects to frontend.
    """
    access_token = AuthService.create_access_token(user)
    refresh_token = AuthService.create_refresh_token(user)
    
    # Redirect to frontend callback page
    redirect_url = f"{FRONTEND_URL}/auth/callback?provider={provider}"
    response = make_response(redirect(redirect_url))
    
    # Set HTTP-only cookies (same as login endpoint)
    is_production = os.getenv('ENVIRONMENT', 'local') != 'local'
    
    response.set_cookie(
        'access_token',
        access_token,
        httponly=True,
        secure=is_production,
        samesite='Lax',
        max_age=AuthService.JWT_EXPIRY_HOURS * 3600,
        path='/'
    )
    response.set_cookie(
        'refresh_token',
        refresh_token,
        httponly=True,
        secure=is_production,
        samesite='Lax',
        max_age=AuthService.JWT_REFRESH_EXPIRY_DAYS * 86400,
        path='/auth'
    )
    
    return response


def _run_async(coro):
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
        return _html_response('login.html')


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
        302: 'Success - redirects to frontend with cookies set',
        400: 'Invalid request',
        401: 'Authentication failed'
    })
    def get(self):
        """
        Handle Discord OAuth2 callback.
        
        Exchanges authorization code for access token,
        creates/retrieves user, sets HTTP-only cookies,
        and redirects to frontend.
        """
        code = request.args.get('code')
        error = request.args.get('error')
        
        if error:
            logger.warning(f"Discord OAuth error: {error}")
            return _html_response('auth_error.html', status=401, error=error)
        
        if not code:
            return _html_response('auth_error.html', status=400, error="No authorization code provided")
        
        # Handle callback (async)
        user, oauth_token, error_msg = _run_async(
            OAuthService.handle_discord_callback(code)
        )
        
        if error_msg:
            logger.error(f"Discord OAuth callback error: {error_msg}")
            return _html_response('auth_error.html', status=401, error=error_msg)
        
        logger.info(f"Discord OAuth success: {user.display_name}")
        
        # Set cookies and redirect to frontend
        return _create_oauth_success_response(user, 'discord')


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
        302: 'Success - redirects to frontend with cookies set',
        400: 'Invalid request',
        401: 'Authentication failed'
    })
    def get(self):
        """
        Handle Google OAuth2 callback.
        
        Exchanges authorization code for access token,
        creates/retrieves user, sets HTTP-only cookies,
        and redirects to frontend.
        """
        code = request.args.get('code')
        error = request.args.get('error')
        
        if error:
            logger.warning(f"Google OAuth error: {error}")
            return _html_response('auth_error.html', status=401, error=error)
        
        if not code:
            return _html_response('auth_error.html', status=400, error="No authorization code provided")
        
        # Handle callback (async)
        user, oauth_token, error_msg = _run_async(
            OAuthService.handle_google_callback(code)
        )
        
        if error_msg:
            logger.error(f"Google OAuth callback error: {error_msg}")
            return _html_response('auth_error.html', status=401, error=error_msg)
        
        logger.info(f"Google OAuth success: {user.display_name}")
        
        # Set cookies and redirect to frontend
        return _create_oauth_success_response(user, 'google')


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
        302: 'Success - redirects to frontend with cookies set',
        400: 'Invalid request',
        401: 'Authentication failed'
    })
    def get(self):
        """
        Handle Slack OAuth2 callback.
        
        Exchanges authorization code for access token,
        creates/retrieves user, sets HTTP-only cookies,
        and redirects to frontend.
        """
        code = request.args.get('code')
        error = request.args.get('error')
        
        if error:
            logger.warning(f"Slack OAuth error: {error}")
            return _html_response('auth_error.html', status=401, error=error)
        
        if not code:
            return _html_response('auth_error.html', status=400, error="No authorization code provided")
        
        # Handle callback (async)
        user, oauth_token, error_msg = _run_async(
            OAuthService.handle_slack_callback(code)
        )
        
        if error_msg:
            logger.error(f"Slack OAuth callback error: {error_msg}")
            return _html_response('auth_error.html', status=401, error=error_msg)
        
        logger.info(f"Slack OAuth success: {user.display_name}")
        
        # Set cookies and redirect to frontend
        return _create_oauth_success_response(user, 'slack')


# =============================================
# Token by Provider (for Discord Bot integration)
# =============================================

@oauth_ns.route('/token-by-provider')
class TokenByProvider(Resource):
    """Get JWT token for a linked OAuth account."""
    
    @oauth_ns.expect(oauth_models['token_by_provider_request'])
    @oauth_ns.response(200, 'Success', oauth_models['token_by_provider_response'])
    @oauth_ns.response(400, 'Bad request - missing parameters')
    @oauth_ns.response(404, 'Account not linked')
    def post(self):
        """
        Get JWT tokens for a user who has already linked their account.
        
        Used by Discord/Slack bots to get tokens for users who have
        previously completed the OAuth flow.
        
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
        user, error = OAuthService.get_user_by_provider(provider, str(provider_user_id))
        
        if error:
            logger.warning(f"Token lookup failed: {provider}:{provider_user_id} - {error}")
            return {"error": error}, 404
        
        # Generate JWT tokens
        access_token, refresh_token = OAuthService.create_tokens_for_user(user)
        
        logger.info(f"Token issued for {provider}:{provider_user_id} -> {user.display_name}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "player_display_name": user.display_name,
            "player_type": user.player_type.value if user.player_type else "human"
        }, 200

