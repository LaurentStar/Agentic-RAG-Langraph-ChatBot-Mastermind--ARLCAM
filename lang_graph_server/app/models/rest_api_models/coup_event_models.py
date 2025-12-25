"""
REST API models for Coup Event Router.

Flask-RESTX models for request/response validation and documentation.
"""

from flask_restx import fields

from app.constants import EventType, SocialMediaPlatform


def register_coup_event_models(namespace):
    """
    Register all Coup event models with a Flask-RESTX namespace.
    
    Args:
        namespace: The Flask-RESTX namespace to register models with
        
    Returns:
        Dict of registered models
    """
    
    # Incoming event model
    incoming_event_model = namespace.model('IncomingEvent', {
        'event_type': fields.String(
            required=True,
            enum=[e.value for e in EventType],
            description='Type of event'
        ),
        'source_platform': fields.String(
            required=True,
            enum=[p.value for p in SocialMediaPlatform],
            description='Platform the event originated from'
        ),
        'sender_id': fields.String(required=True, description='Player/sender identifier'),
        'sender_is_llm': fields.Boolean(required=False, default=False, description='True if sender is an LLM agent'),
        'game_id': fields.String(required=True, description='Game identifier'),
        'target_agent_id': fields.String(required=False, description='Specific agent to process this event'),
        'broadcast_to_all_agents': fields.Boolean(required=False, default=False, description='Send to all agents in game'),
        'payload': fields.Raw(required=True, description='Event-specific data'),
    })

    # Single agent response model
    event_response_model = namespace.model('EventResponse', {
        'success': fields.Boolean(description='Whether event was processed successfully'),
        'event_type': fields.String(description='Type of event that was processed'),
        'agent_id': fields.String(description='Agent that processed the event'),
        'response': fields.Raw(description='Agent response (if any)'),
        'error': fields.String(description='Error message if failed'),
    })

    # Multi-agent response model (for broadcasts)
    broadcast_response_model = namespace.model('BroadcastResponse', {
        'success': fields.Boolean(description='Whether broadcast was processed'),
        'event_type': fields.String(description='Type of event'),
        'agent_responses': fields.List(
            fields.Nested(event_response_model), 
            description='Responses from each agent'
        ),
    })

    # Agent info model (for listing agents)
    agent_info_model = namespace.model('AgentInfo', {
        'agent_id': fields.String(description='Agent identifier'),
        'name': fields.String(description='Agent display name'),
        'coins': fields.Integer(description='Current coin count'),
        'hand_count': fields.Integer(description='Number of cards in hand'),
        'is_alive': fields.Boolean(description='Whether agent is still in game'),
        'action_locked': fields.Boolean(description='Whether actions are locked'),
        'message_stats': fields.Raw(description='Message count statistics'),
    })

    # Game agents list model
    game_agents_model = namespace.model('GameAgents', {
        'game_id': fields.String(description='Game identifier'),
        'agent_count': fields.Integer(description='Number of agents in game'),
        'agents': fields.List(fields.Nested(agent_info_model), description='List of agents'),
    })

    # Agent detailed stats model
    agent_stats_model = namespace.model('AgentStats', {
        'agent_id': fields.String(description='Agent identifier'),
        'game_id': fields.String(description='Game identifier'),
        'name': fields.String(description='Agent display name'),
        'play_style': fields.String(description='Agent play style'),
        'personality': fields.String(description='Agent personality'),
        'coins': fields.Integer(description='Current coin count'),
        'hand_count': fields.Integer(description='Number of cards in hand'),
        'revealed_count': fields.Integer(description='Number of revealed cards'),
        'is_alive': fields.Boolean(description='Whether agent is still in game'),
        'action_locked': fields.Boolean(description='Whether actions are locked'),
        'pending_action': fields.Raw(description='Current pending action'),
        'pending_upgrade': fields.Raw(description='Pending upgrade decision'),
        'message_stats': fields.Raw(description='Message count statistics'),
        'minutes_remaining': fields.Integer(description='Minutes remaining in hour'),
    })

    # Registry stats model
    registry_stats_model = namespace.model('RegistryStats', {
        'total_games': fields.Integer(description='Total number of active games'),
        'total_agents': fields.Integer(description='Total number of registered agents'),
        'games': fields.Raw(description='Per-game statistics'),
    })

    return {
        'incoming_event': incoming_event_model,
        'event_response': event_response_model,
        'broadcast_response': broadcast_response_model,
        'agent_info': agent_info_model,
        'game_agents': game_agents_model,
        'agent_stats': agent_stats_model,
        'registry_stats': registry_stats_model,
    }

