"""
Coup Event Router API Namespace.

Unified endpoint for all incoming events to the Coup LLM agents.
This file handles ONLY routing - all business logic is in coup_event_service.py.

Event Types:
    - chat_message: Player chat from any platform
    - game_state_update: Game state changed
    - player_action_change: Another player changed their pending action
    - supervisor_instruction: Admin command
    - profile_sync: Sync agent profile from DB
    - broadcast_results: End-of-hour game results
"""

from flask import request
from flask_restx import Namespace, Resource

from app.models.rest_api_models.coup_event_models import register_coup_event_models
from app.services.coup_event_service import CoupEventService


# =============================================
# Namespace Definition
# =============================================
coup_event_ns = Namespace(
    'coup-events',
    description='Unified event intake for Coup LLM agents. Routes events to appropriate workflows based on event_type.'
)

# Register models with namespace
models = register_coup_event_models(coup_event_ns)


# =============================================
# Resources
# =============================================

@coup_event_ns.route('/event')
class CoupEventRouter(Resource):
    """Unified event intake endpoint."""
    
    @coup_event_ns.expect(models['incoming_event'], validate=True)
    @coup_event_ns.response(200, 'Event processed', models['event_response'])
    @coup_event_ns.response(400, 'Invalid event')
    def post(self):
        """
        Process an incoming event.
        
        Routes to appropriate handler based on event_type.
        Events can target a specific agent or broadcast to all agents in a game.
        """
        event = request.get_json()
        
        if not event:
            return {'success': False, 'error': 'No event data provided'}, 400
        
        result = CoupEventService.process_event(event)
        
        return result, 200 if result.get('success') else 400


@coup_event_ns.route('/agents/<string:game_id>')
class GameAgents(Resource):
    """List agents in a game."""
    
    @coup_event_ns.response(200, 'Success', models['game_agents'])
    def get(self, game_id: str):
        """Get all LLM agents registered for a game."""
        return CoupEventService.get_game_agents(game_id)
    
    @coup_event_ns.response(200, 'Success', models['cleanup_agents_response'])
    def delete(self, game_id: str):
        """
        Remove all agents for a game (cleanup).
        
        Called when a game session ends to free memory.
        """
        result = CoupEventService.cleanup_game_agents(game_id)
        return result, 200


@coup_event_ns.route('/agents/<string:game_id>/register')
class RegisterAgents(Resource):
    """Register LLM agents for a game session."""
    
    @coup_event_ns.expect(models['register_agents_request'], validate=True)
    @coup_event_ns.response(200, 'Agents registered', models['register_agents_response'])
    @coup_event_ns.response(400, 'Invalid request')
    def post(self, game_id: str):
        """
        Register LLM agents for a game session.
        
        Called by game_server when a session starts or LLM agents join.
        This creates agent instances in the in-memory registry so they
        can process events.
        """
        data = request.get_json()
        
        if not data or 'agents' not in data:
            return {'success': False, 'error': 'No agents provided'}, 400
        
        result = CoupEventService.register_agents(game_id, data['agents'])
        return result, 200


@coup_event_ns.route('/agents/<string:game_id>/<string:agent_id>/stats')
class AgentStats(Resource):
    """Get detailed stats for a specific agent."""
    
    @coup_event_ns.response(200, 'Success', models['agent_stats'])
    @coup_event_ns.response(404, 'Agent not found')
    def get(self, game_id: str, agent_id: str):
        """Get detailed statistics for an agent."""
        result = CoupEventService.get_agent_stats(game_id, agent_id)
        
        if not result:
            return {'error': f'Agent {agent_id} not found in game {game_id}'}, 404
        
        return result


@coup_event_ns.route('/registry/stats')
class RegistryStats(Resource):
    """Get registry-wide statistics."""
    
    @coup_event_ns.response(200, 'Success', models['registry_stats'])
    def get(self):
        """Get statistics about all registered agents across all games."""
        return CoupEventService.get_registry_stats()


