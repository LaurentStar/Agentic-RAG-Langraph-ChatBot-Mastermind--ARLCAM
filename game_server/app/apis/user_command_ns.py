
from flask import jsonify,  make_response, request
from flask_restx import Api, Resource, fields, Namespace

from sqlalchemy.exc import IntegrityError
from app.models.postgres_sql_db_models.player import Player, ToBeInitiatedUpgradeDetails
from app.constants import SocialMediaPlatform, CardType, PlayerStatus, SpecialAbilityCost, ToBeInitiated
from app.extensions import db
from app.extensions import api
from app.models.rest_api_models.user_command_models import (
    register_player_payload_rest_api_model, retrieve_player_profile_parser, 
    assassinate_payload_rest_api_model, player_data_response_marshal)

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
                social_media_platform = SocialMediaPlatform(payload_data.get('social_media_platform')),
                card_types = [CardType(card) for card in payload_data.get('card_types')],
                player_statuses = [PlayerStatus(player_status) for player_status in payload_data.get('player_statuses')],
                coins = payload_data.get('coins'),
                target_display_name = None,
                to_be_initiated = [ToBeInitiated.NO_EVENT]
            )
            db.session.add(player)
            db.session.commit()
            response = {
                "status": "success",
                "message": f'New player {player.display_name} registered.'
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

class Assassinate(Resource):

    @user_commands_ns.expect(assassinate_payload_rest_api_model)
    def post(self):
        '''assassinate a player and remove 1 of their influencer cards'''
        payload_data = request.get_json()

        if not isinstance(payload_data, dict):
            return False
    
       
        assassin_display_name = payload_data.get('assassin_display_name')
        assassin_priority = payload_data.get('assassin_priority')
        assassin_priority_upgrade = payload_data.get('assassin_priority_upgrade')
        target_display_name = payload_data.get('target_display_name')
        assassinate_coins = None; status_code = None; response = None; special_ability_total_cost = None
        message = [] 
        

        try:
            # ---------------------- Get assassin and target profiles ---------------------- #
            assassin_profile = db.session.execute(db.select(Player).where(Player.display_name == assassin_display_name)).scalar_one_or_none()
            assassin_to_be_initiated_upgrade_details = db.session.execute(db.select(ToBeInitiatedUpgradeDetails).where(ToBeInitiatedUpgradeDetails.display_name == assassin_display_name)).scalar_one_or_none()
            target_profile = db.session.execute(db.select(Player).where(Player.display_name == target_display_name)).scalar_one_or_none()
            
            special_ability_total_cost = (SpecialAbilityCost.ASSASSINATE + (SpecialAbilityCost.ASSASSINATE_UPGRADE if assassin_priority_upgrade else 0))
            
            # ---------------------- Check if assassin can afford action ---------------------- #
            if assassin_profile.coins >= special_ability_total_cost and target_profile.display_name:   
                assassin_profile.target_display_name = target_profile.display_name
                assassin_profile.to_be_initiated.append(ToBeInitiated.ACT_ASSASSINATION)
                
                if assassin_priority_upgrade:
                    if assassin_to_be_initiated_upgrade_details:
                        assassin_to_be_initiated_upgrade_details.assassination_priority = CardType(assassin_priority )
                    else:
                        assassin_to_be_initiated_upgrade_details = ToBeInitiatedUpgradeDetails(            
                            display_name = payload_data.get('assassin_display_name'),
                            assassination_priority = CardType(payload_data.get('assassin_priority')),
                        )

                # ---------------------- Update Tables ---------------------- #
                db.session.add(assassin_profile)
                db.session.add(assassin_to_be_initiated_upgrade_details)
                db.session.commit()

                # ---------------------- Output Response ---------------------- #
                status_code = 200
                status = 'success'         
                message.append(f"Player '{target_profile.display_name}' is marked for assassination: Priority card is: {assassin_priority or 'None'}")

            else:
                status = 'denied'
                status_code = 403
                if assassin_profile.coins >= special_ability_total_cost:
                    message.append(f"Inssufficent funds")
                if target_profile.display_name:
                    message.append(f"Assassination target does not exist ")


            response = {
                'status': status,
                'message': message,
                'player data' : {
                    'display_name': assassin_profile.display_name,
                    'social_media_platform_display_name': assassin_profile.social_media_platform_display_name,
                    'social_media_platform': assassin_profile.social_media_platform,
                    'card_types': assassin_profile.card_types,
                    'coins': assassin_profile.coins,
                    'player_statuses': assassin_profile.player_statuses
            }}      

        except Exception as e:
            print('error',e)

        return make_response(jsonify(response), status_code)

# ---------------------- Building Resources ---------------------- #
user_commands_ns.add_resource(RegisterPlayer, '/register-player')
user_commands_ns.add_resource(RetrievePlayerProfile, '/retrieve-player-profile')
user_commands_ns.add_resource(Assassinate, '/assissinate-target')

