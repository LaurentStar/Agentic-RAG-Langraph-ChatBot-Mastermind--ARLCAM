"""
Account Link Service.

Service for explicit account linking via email confirmation.
Users can request to link OAuth identities from different providers,
and both email addresses must be confirmed to complete the link.
"""

import os
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, List, Dict, Any
from urllib.parse import urlencode

from app.extensions import db
from app.models.postgres_sql_db_models import AccountLinkRequest, OAuthIdentity, UserAccount
from app.crud import UserAccountCRUD

logger = logging.getLogger(__name__)


class AccountLinkService:
    """
    Service for managing explicit account linking.
    
    Flow:
    1. User initiates link request with target provider/email
    2. System generates two confirmation tokens
    3. Emails sent to both primary and target email addresses
    4. User clicks both confirmation links
    5. When both confirmed, OAuth identity is linked
    """
    
    # Base URL for confirmation links (can be overridden by env)
    BASE_URL = os.getenv("GAME_SERVER_BASE_URL", "http://localhost:4000")
    
    # Token expiry duration
    TOKEN_EXPIRY_HOURS = 24
    
    # =============================================
    # Initiate Link Request
    # =============================================
    
    @classmethod
    def initiate_link(
        cls,
        player_display_name: str,
        target_provider: str,
        target_email: str,
        primary_email: Optional[str] = None
    ) -> Tuple[Optional[AccountLinkRequest], Optional[str]]:
        """
        Initiate an account link request.
        
        Args:
            player_display_name: Display name of the player initiating the link
            target_provider: Provider to link ("discord", "google", "slack")
            target_email: Email address for the target provider account
            primary_email: Player's current primary email (optional, fetched if not provided)
        
        Returns:
            Tuple of (link_request, error_message)
        """
        # Validate provider
        valid_providers = {"discord", "google", "slack"}
        if target_provider not in valid_providers:
            return None, f"Invalid provider. Must be one of: {valid_providers}"
        
        # Get the user
        user = UserAccountCRUD.get_by_display_name(player_display_name)
        if not user:
            return None, f"Player {player_display_name} not found"
        
        # Get primary email from existing OAuth identities
        if not primary_email:
            primary_identity = OAuthIdentity.query.filter_by(
                user_id=user.user_id,
                deleted_at=None
            ).first()
            
            if primary_identity and primary_identity.provider_email:
                primary_email = primary_identity.provider_email
            else:
                return None, "No primary email found. Please provide one."
        
        # Check if target provider is already linked
        existing_identity = OAuthIdentity.query.filter_by(
            player_display_name=player_display_name,
            provider=target_provider,
            deleted_at=None
        ).first()
        
        if existing_identity:
            return None, f"Provider {target_provider} is already linked to your account"
        
        # Check if there's already a pending request for this target
        pending_request = AccountLinkRequest.query.filter_by(
            player_display_name=player_display_name,
            target_provider=target_provider,
            completed_at=None
        ).filter(
            AccountLinkRequest.expires_at > datetime.now(timezone.utc)
        ).first()
        
        if pending_request:
            return None, "There's already a pending link request for this provider"
        
        # Generate confirmation tokens
        token_primary = secrets.token_urlsafe(32)
        token_secondary = secrets.token_urlsafe(32)
        
        # Create link request
        link_request = AccountLinkRequest(
            player_display_name=player_display_name,
            target_provider=target_provider,
            target_email=target_email,
            token_primary=token_primary,
            token_secondary=token_secondary,
            primary_confirmed=False,
            secondary_confirmed=False,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=cls.TOKEN_EXPIRY_HOURS)
        )
        
        db.session.add(link_request)
        db.session.commit()
        
        # Generate confirmation URLs
        primary_url = cls._generate_confirm_url(token_primary)
        secondary_url = cls._generate_confirm_url(token_secondary)
        
        # Send emails (in production, this would use an email service)
        cls._send_confirmation_email(
            email=primary_email,
            player_name=player_display_name,
            target_provider=target_provider,
            confirm_url=primary_url,
            is_primary=True
        )
        
        cls._send_confirmation_email(
            email=target_email,
            player_name=player_display_name,
            target_provider=target_provider,
            confirm_url=secondary_url,
            is_primary=False
        )
        
        logger.info(
            f"Link request created: {player_display_name} -> {target_provider} "
            f"(emails: {primary_email}, {target_email})"
        )
        
        return link_request, None
    
    # =============================================
    # Confirm Token
    # =============================================
    
    @classmethod
    def confirm_token(cls, token: str) -> Tuple[Optional[AccountLinkRequest], Optional[str]]:
        """
        Confirm a link request token.
        
        Args:
            token: The confirmation token
        
        Returns:
            Tuple of (link_request, error_message)
        """
        # Find the link request by token
        link_request = AccountLinkRequest.query.filter(
            (AccountLinkRequest.token_primary == token) |
            (AccountLinkRequest.token_secondary == token)
        ).first()
        
        if not link_request:
            return None, "Invalid or expired confirmation token"
        
        # Check if expired
        if link_request.is_expired:
            return None, "This confirmation link has expired"
        
        # Check if already completed
        if link_request.completed_at:
            return None, "This link request has already been completed"
        
        # Determine which token was confirmed
        if token == link_request.token_primary:
            if link_request.primary_confirmed:
                return link_request, "Primary email already confirmed"
            link_request.primary_confirmed = True
            logger.info(f"Primary email confirmed for link request {link_request.id}")
        else:
            if link_request.secondary_confirmed:
                return link_request, "Secondary email already confirmed"
            link_request.secondary_confirmed = True
            logger.info(f"Secondary email confirmed for link request {link_request.id}")
        
        db.session.commit()
        
        # Check if both confirmed - complete the link
        if link_request.is_complete:
            return cls._complete_link(link_request)
        
        return link_request, None
    
    # =============================================
    # Complete Link
    # =============================================
    
    @classmethod
    def _complete_link(
        cls,
        link_request: AccountLinkRequest
    ) -> Tuple[Optional[AccountLinkRequest], Optional[str]]:
        """
        Complete the account link after both emails are confirmed.
        
        This creates a placeholder OAuthIdentity that will be fully
        populated when the user logs in via that provider.
        
        Args:
            link_request: The confirmed link request
        
        Returns:
            Tuple of (link_request, error_message)
        """
        # Check if already completed
        if link_request.completed_at:
            return link_request, "Link already completed"
        
        # Mark as completed
        link_request.completed_at = datetime.now(timezone.utc)
        
        # Note: We don't create the OAuthIdentity here because we don't have
        # the provider_user_id yet. The actual OAuth identity will be created
        # when the user logs in via the target provider and the email matches.
        
        db.session.commit()
        
        # Send success email
        cls._send_success_email(
            email=link_request.target_email,
            player_name=link_request.player_display_name,
            target_provider=link_request.target_provider
        )
        
        logger.info(
            f"Link request completed: {link_request.player_display_name} "
            f"-> {link_request.target_provider}"
        )
        
        return link_request, None
    
    # =============================================
    # Status and Retrieval
    # =============================================
    
    @classmethod
    def get_pending_requests(cls, player_display_name: str) -> List[AccountLinkRequest]:
        """
        Get pending link requests for a player.
        
        Args:
            player_display_name: Display name of the player
        
        Returns:
            List of pending AccountLinkRequest objects
        """
        return AccountLinkRequest.query.filter_by(
            player_display_name=player_display_name,
            completed_at=None
        ).filter(
            AccountLinkRequest.expires_at > datetime.now(timezone.utc)
        ).order_by(AccountLinkRequest.created_at.desc()).all()
    
    @classmethod
    def get_request_by_id(cls, request_id: str) -> Optional[AccountLinkRequest]:
        """
        Get a link request by ID.
        
        Args:
            request_id: The request UUID
        
        Returns:
            AccountLinkRequest or None
        """
        return db.session.get(AccountLinkRequest, request_id)
    
    @classmethod
    def cancel_request(cls, request_id: str, player_display_name: str) -> Tuple[bool, Optional[str]]:
        """
        Cancel a pending link request.
        
        Args:
            request_id: The request UUID
            player_display_name: Display name of the player (for authorization)
        
        Returns:
            Tuple of (success, error_message)
        """
        link_request = db.session.get(AccountLinkRequest, request_id)
        
        if not link_request:
            return False, "Link request not found"
        
        if link_request.player_display_name != player_display_name:
            return False, "Not authorized to cancel this request"
        
        if link_request.completed_at:
            return False, "Cannot cancel a completed request"
        
        # Delete the request
        db.session.delete(link_request)
        db.session.commit()
        
        logger.info(f"Link request {request_id} cancelled by {player_display_name}")
        
        return True, None
    
    # =============================================
    # Helper Methods
    # =============================================
    
    @classmethod
    def _generate_confirm_url(cls, token: str) -> str:
        """Generate the confirmation URL for a token."""
        return f"{cls.BASE_URL}/account/link/confirm/{token}"
    
    @classmethod
    def _send_confirmation_email(
        cls,
        email: str,
        player_name: str,
        target_provider: str,
        confirm_url: str,
        is_primary: bool
    ) -> None:
        """
        Send confirmation email.
        
        In production, this would use an email service.
        For now, we log the email content.
        
        Args:
            email: Recipient email address
            player_name: Player's display name
            target_provider: Provider being linked
            confirm_url: URL to confirm
            is_primary: Whether this is the primary (existing) email
        """
        email_type = "primary" if is_primary else "target"
        
        # In production: use SendGrid, SES, etc.
        # For now, just log it
        logger.info(
            f"[EMAIL] Confirmation ({email_type}) to {email}:\n"
            f"  Player: {player_name}\n"
            f"  Linking: {target_provider}\n"
            f"  Confirm URL: {confirm_url}"
        )
        
        # TODO: Implement actual email sending
        # Example with SendGrid:
        # message = Mail(
        #     from_email='noreply@yourgame.com',
        #     to_emails=email,
        #     subject=f'Confirm account link - {target_provider}',
        #     html_content=render_template(
        #         'link_confirm_email.html',
        #         player_name=player_name,
        #         target_provider=target_provider,
        #         confirm_url=confirm_url
        #     )
        # )
        # sg.send(message)
    
    @classmethod
    def _send_success_email(
        cls,
        email: str,
        player_name: str,
        target_provider: str
    ) -> None:
        """
        Send success email after link is complete.
        
        Args:
            email: Recipient email address
            player_name: Player's display name
            target_provider: Provider that was linked
        """
        # In production: use email service
        logger.info(
            f"[EMAIL] Link success to {email}:\n"
            f"  Player: {player_name}\n"
            f"  Linked: {target_provider}"
        )
    
    # =============================================
    # Cleanup
    # =============================================
    
    @classmethod
    def cleanup_expired_requests(cls) -> int:
        """
        Clean up expired link requests.
        
        Returns:
            Number of deleted requests
        """
        expired = AccountLinkRequest.query.filter(
            AccountLinkRequest.expires_at < datetime.now(timezone.utc),
            AccountLinkRequest.completed_at.is_(None)
        ).all()
        
        count = len(expired)
        
        for request in expired:
            db.session.delete(request)
        
        if count > 0:
            db.session.commit()
            logger.info(f"Cleaned up {count} expired link requests")
        
        return count

