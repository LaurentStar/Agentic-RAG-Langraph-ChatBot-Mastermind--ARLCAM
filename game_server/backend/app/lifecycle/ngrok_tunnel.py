"""
Ngrok Tunnel for Local Development.

Starts ngrok tunnel when ENVIRONMENT=local.
Only used for local development - not loaded in dev/qa/prod.
"""

import os
import logging
import atexit
from typing import Optional

logger = logging.getLogger("game_server")

# =============================================
# MODULE STATE
# =============================================

_tunnel = None


# =============================================
# PUBLIC FUNCTIONS
# =============================================

def start_tunnel(port: int) -> Optional[str]:
    """
    Start ngrok tunnel using static domain.
    
    Args:
        port: Local port to tunnel to
    
    Returns:
        Public URL if successful, None otherwise
    """
    global _tunnel
    
    try:
        from pyngrok import ngrok, conf
        
        auth_token = os.getenv("NGROK_AUTH_TOKEN")
        domain = os.getenv("NGROK_DEV_DOMAIN")
        
        if not auth_token:
            logger.warning("NGROK_AUTH_TOKEN not set - tunnel disabled")
            return None
        
        # Configure ngrok
        conf.get_default().auth_token = auth_token
        
        # Start tunnel with static domain if available
        if domain:
            logger.info(f"Starting ngrok tunnel with static domain: {domain}")
            _tunnel = ngrok.connect(port, bind_tls=True, hostname=domain)
        else:
            logger.info(f"Starting ngrok tunnel (dynamic URL)")
            _tunnel = ngrok.connect(port, bind_tls=True)
        
        public_url = _tunnel.public_url
        logger.info(f"Ngrok tunnel active: {public_url}")
        
        # Register cleanup on exit
        atexit.register(stop_tunnel)
        
        return public_url
        
    except ImportError:
        logger.warning("pyngrok not installed - ngrok tunnel disabled")
        logger.info("Install with: pip install pyngrok")
        return None
        
    except Exception as e:
        logger.error(f"Failed to start ngrok tunnel: {e}")
        return None


def stop_tunnel() -> None:
    """Stop ngrok tunnel if running."""
    global _tunnel
    
    if _tunnel is None:
        return
    
    try:
        from pyngrok import ngrok
        
        logger.info("Stopping ngrok tunnel...")
        ngrok.disconnect(_tunnel.public_url)
        ngrok.kill()
        logger.info("Ngrok tunnel stopped")
        
    except Exception as e:
        logger.warning(f"Error stopping ngrok tunnel: {e}")
        
    finally:
        _tunnel = None


def get_tunnel_url() -> Optional[str]:
    """Get the current tunnel URL if active."""
    global _tunnel
    return _tunnel.public_url if _tunnel else None

