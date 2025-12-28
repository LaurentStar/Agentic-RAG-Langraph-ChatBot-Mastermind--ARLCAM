"""
Slack Proxy Namespace.

Routes Slack traffic to the local slack_bot server.
Only registered when ENVIRONMENT=local.
"""

from flask import request, Response
from flask_restx import Namespace, Resource

from app.services.local.proxy.slack_proxy_service import SlackProxyService


# =============================================
# NAMESPACE DEFINITION
# =============================================

slack_proxy_ns = Namespace(
    "slack_proxy",
    description="Proxy Slack traffic to local slack_bot (local development only)"
)


# =============================================
# ROUTES
# =============================================

@slack_proxy_ns.route("/events")
class SlackEventsProxy(Resource):
    """Proxy Slack events to slack_bot."""
    
    @slack_proxy_ns.doc(
        description="Forward Slack events to local slack_bot",
        responses={
            200: "Event processed",
            502: "Slack bot not reachable",
            504: "Slack bot timeout"
        }
    )
    def post(self):
        """Proxy Slack event to slack_bot."""
        body = request.get_data()
        headers = dict(request.headers)
        content_type = request.content_type or "application/json"
        
        status, response_body, response_headers = SlackProxyService.proxy_events(
            body, headers, content_type
        )
        
        return Response(
            response_body,
            status=status,
            headers={"Content-Type": response_headers.get("Content-Type", "application/json")}
        )


@slack_proxy_ns.route("/commands")
class SlackCommandsProxy(Resource):
    """Proxy Slack slash commands to slack_bot."""
    
    @slack_proxy_ns.doc(
        description="Forward Slack slash commands to local slack_bot",
        responses={
            200: "Command processed",
            502: "Slack bot not reachable",
            504: "Slack bot timeout"
        }
    )
    def post(self):
        """Proxy Slack command to slack_bot."""
        body = request.get_data()
        headers = dict(request.headers)
        content_type = request.content_type or "application/x-www-form-urlencoded"
        
        status, response_body, response_headers = SlackProxyService.proxy_commands(
            body, headers, content_type
        )
        
        return Response(
            response_body,
            status=status,
            headers={"Content-Type": response_headers.get("Content-Type", "application/json")}
        )


@slack_proxy_ns.route("/interactions")
class SlackInteractionsProxy(Resource):
    """Proxy Slack interactions to slack_bot."""
    
    @slack_proxy_ns.doc(
        description="Forward Slack interactions to local slack_bot",
        responses={
            200: "Interaction processed",
            502: "Slack bot not reachable",
            504: "Slack bot timeout"
        }
    )
    def post(self):
        """Proxy Slack interaction to slack_bot."""
        body = request.get_data()
        headers = dict(request.headers)
        content_type = request.content_type or "application/x-www-form-urlencoded"
        
        status, response_body, response_headers = SlackProxyService.proxy_interactions(
            body, headers, content_type
        )
        
        return Response(
            response_body,
            status=status,
            headers={"Content-Type": response_headers.get("Content-Type", "application/json")}
        )


@slack_proxy_ns.route("/options")
class SlackOptionsProxy(Resource):
    """Proxy Slack options requests to slack_bot."""
    
    @slack_proxy_ns.doc(
        description="Forward Slack options (dynamic select menus) to local slack_bot",
        responses={
            200: "Options returned",
            502: "Slack bot not reachable",
            504: "Slack bot timeout"
        }
    )
    def post(self):
        """Proxy Slack options request to slack_bot."""
        body = request.get_data()
        headers = dict(request.headers)
        content_type = request.content_type or "application/x-www-form-urlencoded"
        
        status, response_body, response_headers = SlackProxyService.proxy_options(
            body, headers, content_type
        )
        
        return Response(
            response_body,
            status=status,
            headers={"Content-Type": response_headers.get("Content-Type", "application/json")}
        )

