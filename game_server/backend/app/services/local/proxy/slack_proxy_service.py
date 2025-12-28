"""
Slack Proxy Service.

Forwards Slack requests to the local slack_bot server.
Only used when ENVIRONMENT=local.
"""

import os
import logging
from typing import Tuple, Dict, Any

import httpx

logger = logging.getLogger("game_server")


class SlackProxyService:
    """
    Service for proxying Slack requests to the local slack_bot.
    
    Forwards:
    - Events (message events, app mentions, etc.)
    - Commands (slash commands)
    - Interactions (buttons, modals, shortcuts)
    - Options (dynamic select menu options)
    """
    
    # =============================================
    # CONFIGURATION
    # =============================================
    
    @staticmethod
    def get_slack_bot_url() -> str:
        """Get the local Slack bot URL from environment."""
        return os.getenv("SLACK_BOT_LOCAL_URL", "http://localhost:3002")
    
    # =============================================
    # PROXY METHODS
    # =============================================
    
    @classmethod
    def proxy_request(
        cls,
        endpoint: str,
        body: bytes,
        headers: Dict[str, str],
        content_type: str = "application/json"
    ) -> Tuple[int, bytes, Dict[str, str]]:
        """
        Proxy a request to the slack_bot.
        
        Args:
            endpoint: Target endpoint on slack_bot (e.g., "/slack/events")
            body: Raw request body
            headers: Request headers to forward
            content_type: Content-Type header
        
        Returns:
            Tuple of (status_code, response_body, response_headers)
        """
        base_url = cls.get_slack_bot_url()
        target_url = f"{base_url}{endpoint}"
        
        # Filter headers to forward
        forward_headers = cls._filter_headers(headers, content_type)
        
        logger.debug(f"Proxying to {target_url}")
        
        try:
            response = httpx.post(
                target_url,
                content=body,
                headers=forward_headers,
                timeout=30.0
            )
            
            # Extract response headers to return
            response_headers = dict(response.headers)
            
            logger.debug(f"Proxy response: {response.status_code}")
            
            return response.status_code, response.content, response_headers
            
        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to slack_bot at {base_url}: {e}")
            error_body = b'{"error": "Slack bot not reachable"}'
            return 502, error_body, {"Content-Type": "application/json"}
            
        except httpx.TimeoutException as e:
            logger.error(f"Timeout proxying to slack_bot: {e}")
            error_body = b'{"error": "Slack bot timeout"}'
            return 504, error_body, {"Content-Type": "application/json"}
            
        except Exception as e:
            logger.error(f"Proxy error: {e}")
            error_body = b'{"error": "Proxy error"}'
            return 500, error_body, {"Content-Type": "application/json"}
    
    @classmethod
    def proxy_events(cls, body: bytes, headers: Dict[str, str], content_type: str) -> Tuple[int, bytes, Dict[str, str]]:
        """Proxy Slack events to slack_bot."""
        return cls.proxy_request("/slack/events", body, headers, content_type)
    
    @classmethod
    def proxy_commands(cls, body: bytes, headers: Dict[str, str], content_type: str) -> Tuple[int, bytes, Dict[str, str]]:
        """Proxy Slack slash commands to slack_bot."""
        return cls.proxy_request("/slack/commands", body, headers, content_type)
    
    @classmethod
    def proxy_interactions(cls, body: bytes, headers: Dict[str, str], content_type: str) -> Tuple[int, bytes, Dict[str, str]]:
        """Proxy Slack interactions to slack_bot."""
        return cls.proxy_request("/slack/interactions", body, headers, content_type)
    
    @classmethod
    def proxy_options(cls, body: bytes, headers: Dict[str, str], content_type: str) -> Tuple[int, bytes, Dict[str, str]]:
        """Proxy Slack options requests to slack_bot."""
        return cls.proxy_request("/slack/options", body, headers, content_type)
    
    # =============================================
    # HELPERS
    # =============================================
    
    @staticmethod
    def _filter_headers(headers: Dict[str, str], content_type: str) -> Dict[str, str]:
        """
        Filter headers to forward to slack_bot.
        
        Includes Slack-specific headers needed for signature verification.
        """
        forward_headers = {
            "Content-Type": content_type
        }
        
        # Slack signature headers (required for verification)
        slack_headers = [
            "X-Slack-Signature",
            "X-Slack-Request-Timestamp",
            "X-Slack-Retry-Num",
            "X-Slack-Retry-Reason"
        ]
        
        for header in slack_headers:
            if header in headers:
                forward_headers[header] = headers[header]
            # Also check lowercase versions
            elif header.lower() in headers:
                forward_headers[header] = headers[header.lower()]
        
        return forward_headers

