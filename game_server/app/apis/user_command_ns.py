
from flask import jsonify,  make_response, request
from flask_restx import Api, Resource, fields, Namespace

from sqlalchemy.exc import IntegrityError
from app.models.postgres_sql_db_models.player import Player
from app.constants import SocailMediaPlatform, CardType, PlayerStatus
from app.extensions import db
from app.extensions import api
from app.models.rest_api_models.user_command_models import (
    register_player_payload_rest_api_model, retrieve_player_profile_parser, player_data_response_marshal)

# ---------------------- Name Spaces ---------------------- #
user_commands_ns = Namespace('user-commands', description='Command requested by users and bots')


# ---------------------- Resources ---------------------- #
class RegisterPlayer(Resource):
    @user_commands_ns.expect(register_player_payload_rest_api_model, validate=True)
    def post(self):
        '''Registers a player or bot into an existing game'''
        # display_name:str
        # social_media_platform_display_name:str
        # social_media_platform:SocailMediaPlatform
        # card_types:CardType
        payload_data = request.get_json()

        if not isinstance(payload_data, dict):
            return False

        try:
            player = Player (            
                display_name = payload_data.get('display_name'),
                social_media_platform_display_name = payload_data.get('social_media_platform_display_name'),
                social_media_platform = SocailMediaPlatform(payload_data.get('social_media_platform')),
                card_types = [CardType(card) for card in payload_data.get('card_types')],
                player_statuses = [PlayerStatus(player_status) for player_status in payload_data.get('player_statuses')]
            )
            db.session.add(player)
            db.session.commit()
            response = {
                "status": "success",
                "message": f'New player  registered.'
            }
            status_code = 200

        except ValueError as e:
            print(f"Error: {e}")
            response = {
                "status": "Failure",
                "message": f'{e}'
            }
            status_code = 500    
        except IntegrityError as e:
            print(f"Error: {e}")
            db.session.rollback()  # Rollback the transaction to clear the error state
            response = {
                "status": "Failure",
                "message": f'{e}'
            }
            status_code = 500
    
        return make_response(jsonify(response), status_code)
    
class RetrievePlayerProfile(Resource): 
    @user_commands_ns.expect(retrieve_player_profile_parser)
    def get(self):
        '''Gather player details based on display name query'''
        args = retrieve_player_profile_parser.parse_args()
        display_name = args.get('display_name')
        player = db.session.execute(db.select(Player).where(Player.display_name == display_name)).scalar_one_or_none()
        
        if player:
            print(f'Player: {display_name} found.')
            status_code = 200
            response = {
                'status': 'success',
                'message': f"Player Information for '{display_name}' found in player registery.",
                'player data' : {
                    'display_name': player.display_name,
                    'social_media_platform_display_name': player.social_media_platform_display_name,
                    'social_media_platform': player.social_media_platform,
                    'card_types': player.card_types,
                    'player_statuses': player.player_statuses 
            }}      
        else:
            print(f'Player: {display_name} not found.')
            status_code = 404
            response = {
                'status': 'failure',
                'message': f"Player Information for '{display_name}' not found in player registery.",
                'player data' : None
            }

        return make_response(jsonify(response), status_code)

# ---------------------- Building Resources ---------------------- #
user_commands_ns.add_resource(RegisterPlayer, '/register-player')
user_commands_ns.add_resource(RetrievePlayerProfile, '/retrieve-player-profile')

