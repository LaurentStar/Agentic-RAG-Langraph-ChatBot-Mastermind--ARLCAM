"""
Ngrok Tunnel for Local Development.

Starts ngrok tunnel when ENVIRONMENT=local.
Only used for local development - not loaded in dev/qa/prod.
"""

import atexit
import logging
import os
import signal
import sys
import time
from typing import Optional

logger = logging.getLogger("game_server")

# =============================================
# MODULE STATE
# =============================================

_tunnel = None


# =============================================
# PRIVATE HELPERS
# =============================================

def _kill_existing_ngrok() -> None:
    """
    Kill any existing ngrok process before starting.
    
    Prevents "endpoint already online" error when restarting
    after an unclean shutdown left an orphan ngrok process.
    """
    # NOTE: Inline import is intentional - pyngrok is optional (local-dev only)
    try:
        from pyngrok import ngrok
        ngrok.kill()
        # Wait for ngrok servers to recognize the disconnect
        time.sleep(5)
        logger.debug("Killed existing ngrok process (if any)")
    except Exception:
        pass  # No existing process or pyngrok not installed


def _signal_handler(signum, frame):
    """Handle shutdown signals (SIGINT, SIGTERM)."""
    logger.info(f"Received signal {signum}, stopping ngrok...")
    stop_tunnel()
    sys.exit(0)


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
    
    # Kill any orphan ngrok process from previous session
    _kill_existing_ngrok()
    
    try:
        # NOTE: Inline import is intentional - pyngrok is optional (local-dev only)
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
        
        # Register signal handlers for graceful shutdown (only on main thread)
        try:
            signal.signal(signal.SIGINT, _signal_handler)
            signal.signal(signal.SIGTERM, _signal_handler)
        except ValueError:
            pass  # Not on main thread, skip signal registration
        
        # Register cleanup on normal exit
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

