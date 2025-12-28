"""
Proxy namespaces for local development.

Routes external traffic to local services.
"""
from app.apis.local.proxy.slack_proxy_ns import slack_proxy_ns

__all__ = ["slack_proxy_ns"]

