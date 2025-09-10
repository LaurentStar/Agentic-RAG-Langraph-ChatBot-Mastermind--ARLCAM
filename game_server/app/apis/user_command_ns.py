
from flask import jsonify,  make_response, request
from flask_restx import Api, Resource, fields, Namespace

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.attributes import flag_modified

from app.models.postgres_sql_db_models.player import Player, ToBeInitiatedUpgradeDetails
from app.constants import SocialMediaPlatform, CardType, PlayerStatus, SpecialAbilityCost, ToBeInitiated
from app.extensions import db
from app.extensions import api
from app.models.rest_api_models.user_command_models import (
    register_player_payload_rest_api_model, retrieve_player_profile_parser, 
    assassinate_payload_rest_api_model, coup_payload_rest_api_model,
    player_query_payload_rest_api_model, generic_payload_rest_api_model,
    generic_target_not_required_payload_rest_api_model, 
    player_data_response_marshal)

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

class Coup(Resource):
    @user_commands_ns.expect(coup_payload_rest_api_model)
    def post(self):
        '''perform an unblockable coup against another player'''
        payload_data = request.get_json()

        if not isinstance(payload_data, dict):
            return False
        
        caudillo_display_name = payload_data.get('caudillo_display_name')
        deposed_influencer_display_name = payload_data.get('deposed_influencer_display_name')
        caudillo_coins = None; status_code = None; response = None
        message = [] 

        try:
            # ---------------------- Get caudillo and deposed_influence profiles ---------------------- #
            caudillo_profile = db.session.execute(db.select(Player).where(Player.display_name == caudillo_display_name)).scalar_one_or_none()
            deposed_influencer_profile = db.session.execute(db.select(Player).where(Player.display_name == deposed_influencer_display_name)).scalar_one_or_none()
        
            
            # ---------------------- Check if assassin can afford action and the profiles exist---------------------- #
            if caudillo_profile and deposed_influencer_profile and caudillo_profile.coins >= SpecialAbilityCost.COUP:   
                caudillo_profile.target_display_name = deposed_influencer_profile.display_name
                caudillo_profile.to_be_initiated.append(ToBeInitiated.ACT_ASSASSINATION)

                # ---------------------- Update Tables ---------------------- #
                db.session.add(caudillo_profile)
                db.session.commit()

                # ---------------------- Output Response ---------------------- #
                status_code = 200
                status = 'success'         
                message.append(f"Player '{deposed_influencer_profile.display_name}' is marked for coup.")
            else:
                status = 'denied'
                status_code = 403
                if caudillo_profile.coins >= SpecialAbilityCost.COUP:
                    message.append(f"Inssufficent funds")
                if deposed_influencer_profile.display_name:
                    message.append(f"Coup target does not exist ")    
        except Exception as e:
            print('error',e)

        return make_response(jsonify(response), status_code)

class ForeignAid(Resource):
    @user_commands_ns.expect(player_query_payload_rest_api_model)
    def post(self):
        '''Request foreigh aid and takes two coins from the bank'''
        payload_data = request.get_json()

        if not isinstance(payload_data, dict):
            return False
        
        recipient_display_name = payload_data.get('display_name')
        message = []; response = None

        try:
            # ---------------------- Get recipient profiles ---------------------- #
            recipient_profile = db.session.execute(db.select(Player).where(Player.display_name == recipient_display_name )).scalar_one_or_none()
             
            # ---------------------- Check if recipient profile exist---------------------- #
            if recipient_profile:   
                recipient_profile.to_be_initiated.append(ToBeInitiated.ACT_ASSASSINATION)

                # ---------------------- Update Tables ---------------------- #
                db.session.add(recipient_profile)
                flag_modified(recipient_profile, "to_be_initiated")
                db.session.commit()

                # ---------------------- Output Response ---------------------- #
                status_code = 200
                status = 'success'         
                message.append(f"Player '{recipient_profile.display_name}' is marked for coup.")
   
        except Exception as e:
            status_code = 500
            print('error',e)

        return make_response(jsonify(response), status_code)

class Steal(Resource):
    @user_commands_ns.expect(generic_payload_rest_api_model)
    def post(self):
        '''Steal from another player'''
        payload_data = request.get_json()

        if not isinstance(payload_data, dict):
            return False
        
        player_display_name = payload_data.get('player_display_name')
        target_display_name = payload_data.get('target_display_name')
        player_upgrade = payload_data.get('player_upgrade')
        message = []; response = None


        try:
            # ---------------------- Get player and target profiles ---------------------- #
            player_profile = db.session.execute(db.select(Player).where(Player.display_name == player_display_name)).scalar_one_or_none()
            target_profile = db.session.execute(db.select(Player).where(Player.display_name == target_display_name )).scalar_one_or_none()
            player_to_be_initiated_upgrade_details = db.session.execute(db.select(ToBeInitiatedUpgradeDetails).where(ToBeInitiatedUpgradeDetails.display_name == player_display_name)).scalar_one_or_none()

            special_ability_total_cost = (SpecialAbilityCost.STEAL + (SpecialAbilityCost.STEAL_UPGRADE if player_upgrade else 0))

            # ---------------------- Check if recipient profile exist---------------------- #
            if player_profile and target_profile:   
                target_profile.to_be_initiated.append(ToBeInitiated.ACT_STEAL)

                # ---------------------- Check if player can afford action ---------------------- #
                if player_profile.coins >= special_ability_total_cost:   
                    player_profile.target_display_name = target_profile.display_name
                    player_profile.to_be_initiated.append(ToBeInitiated.ACT_STEAL)
                    
                    if player_upgrade:
                        if player_to_be_initiated_upgrade_details:
                            player_to_be_initiated_upgrade_details.kleptomania_steal = True # kleptomania means to have a mental disorder, being unable to resist not stealing and theivefy.
                        else:
                            player_to_be_initiated_upgrade_details = ToBeInitiatedUpgradeDetails(            
                                display_name = payload_data.get('player_display_name'),
                                kleptomania_steal = True
                            )
                            
                    # ---------------------- Update Tables ---------------------- #
                    db.session.add(player_profile)
                    db.session.add(player_to_be_initiated_upgrade_details)
                    flag_modified(player_profile, "to_be_initiated")
                    db.session.commit()

                    # ---------------------- Output Response ---------------------- #
                    status_code = 200
                    status = 'success'         
                    message.append(f"Player '{target_profile.display_name}' is marked to be stolen from.")
            else:
                status = 'denied'
                status_code = 403
                if player_profile.coins >= special_ability_total_cost:
                    message.append(f"Inssufficent funds")
                if target_profile.display_name:
                    message.append(f"Robbery target does not exist.")

        except Exception as e:
            status = 'error'
            status_code = 500
            message.append(f"Having an internal server error, please try again later.")
            print('error',e)



        response = {
            'status': status,
            'message': message,
            'player data' : {
                'display_name': player_profile.display_name,
                'social_media_platform_display_name': player_profile.social_media_platform_display_name,
                'social_media_platform': player_profile.social_media_platform,
                'card_types': player_profile.card_types,
                'coins': player_profile.coins,
                'player_statuses': player_profile.player_statuses
        }}    
        return make_response(jsonify(response), status_code)

class Block(Resource):
    @user_commands_ns.expect(generic_payload_rest_api_model)
    def post(self):
        '''Block another player action'''
        payload_data = request.get_json()

        if not isinstance(payload_data, dict):
            return False
        
        player_display_name = payload_data.get('player_display_name')
        target_display_name = payload_data.get('target_display_name')
        message = []; response = None


        try:
            # ---------------------- Get player and target profiles ---------------------- #
            player_profile = db.session.execute(db.select(Player).where(Player.display_name == player_display_name)).scalar_one_or_none()
            target_profile = db.session.execute(db.select(Player).where(Player.display_name == target_display_name )).scalar_one_or_none()

            # ---------------------- Check if recipient profile exist---------------------- #
            if player_profile and target_profile:   
                player_profile.target_display_name = target_profile.display_name
                player_profile.to_be_initiated.append(ToBeInitiated.ACT_BLOCK)
                
                # ---------------------- Update Tables ---------------------- #
                db.session.add(player_profile)
                flag_modified(player_profile, "to_be_initiated")
                db.session.commit()

                # ---------------------- Output Response ---------------------- #
                status_code = 200
                status = 'success'         
                message.append(f"Player '{target_profile.display_name}' is marked to be blocked.")
            else:
                status = 'denied'
                status_code = 403
                if target_profile.display_name:
                    message.append(f"Robbery target does not exist.")

        except Exception as e:
            status = 'error'
            status_code = 500
            message.append(f"Having an internal server error, please try again later.")
            print('error',e)



        response = {
            'status': status,
            'message': message,
            'player data' : {
                'display_name': player_profile.display_name,
                'social_media_platform_display_name': player_profile.social_media_platform_display_name,
                'social_media_platform': player_profile.social_media_platform,
                'card_types': player_profile.card_types,
                'coins': player_profile.coins,
                'player_statuses': player_profile.player_statuses
        }}    
        return make_response(jsonify(response), status_code)
 
class SwapInfluence(Resource):
    @user_commands_ns.expect(generic_target_not_required_payload_rest_api_model)
    def post(self):
        '''Player swaps their cards or potentially another player along with their'''
        payload_data = request.get_json()

        if not isinstance(payload_data, dict):
            return False
        
        player_display_name = payload_data.get('player_display_name')
        target_display_name = payload_data.get('target_display_name')
        player_upgrade = payload_data.get('player_upgrade')
        message = []; response = None; status = None; status_code = None


        try:
            # ---------------------- Get player and target profiles ---------------------- #
            player_profile = db.session.execute(db.select(Player).where(Player.display_name == player_display_name)).scalar_one_or_none()
            target_profile = db.session.execute(db.select(Player).where(Player.display_name == target_display_name )).scalar_one_or_none()
            player_to_be_initiated_upgrade_details = db.session.execute(db.select(ToBeInitiatedUpgradeDetails).where(ToBeInitiatedUpgradeDetails.display_name == player_display_name)).scalar_one_or_none()

            special_ability_total_cost = (SpecialAbilityCost.SWAP_INFLUENCE + (SpecialAbilityCost.SWAP_INFLUENCE_UPGRADE if player_upgrade else 0))

            # ---------------------- Check ift player profile exist and can afford the action---------------------- #
            if player_profile and player_profile.coins >= special_ability_total_cost:

                player_profile.target_display_name = target_profile.display_name
                player_profile.to_be_initiated.append(ToBeInitiated.ACT_SWAP_INFLUENCE)
                
                if player_upgrade:
                    if player_to_be_initiated_upgrade_details:
                        player_to_be_initiated_upgrade_details.trigger_identity_crisis = True # This swaps the target cards along with the player causing a mild identity crisis
                    else:
                        player_to_be_initiated_upgrade_details = ToBeInitiatedUpgradeDetails(            
                            display_name = payload_data.get('player_display_name'),
                            trigger_identity_crisis = True
                        )
                        
                # ---------------------- Update Tables ---------------------- #
                db.session.add(player_profile)
                db.session.add(player_to_be_initiated_upgrade_details)
                flag_modified(player_profile, "to_be_initiated")
                db.session.commit()

                # ---------------------- Output Response ---------------------- #
                status_code = 200
                status = 'success'         
                message.append(f"Player '{player_profile.display_name}' is marked to have their deck swapped. {target_profile.display_name} will also have their deck swapped.")
            else:
                status = 'denied'
                status_code = 403
                if player_profile.coins < special_ability_total_cost:
                    message.append(f"Inssufficent funds")
                if not target_profile.display_name and player_upgrade:
                    message.append(f" Identity crisis target does not exist.")
        except Exception as e:
            status = 'error'
            status_code = 500
            message.append(f"Having an internal server error, please try again later.")
            print('error',e)

        response = {
            'status': status,
            'message': message,
            'player data' : {
                'display_name': player_profile.display_name,
                'social_media_platform_display_name': player_profile.social_media_platform_display_name,
                'social_media_platform': player_profile.social_media_platform,
                'card_types': player_profile.card_types,
                'coins': player_profile.coins,
                'player_statuses': player_profile.player_statuses
        }}    
        return make_response(jsonify(response), status_code)

 
# ---------------------- Building Resources ---------------------- #
user_commands_ns.add_resource(RegisterPlayer, '/register-player')
user_commands_ns.add_resource(RetrievePlayerProfile, '/retrieve-player-profile')
user_commands_ns.add_resource(Assassinate, '/assissinate-target')
user_commands_ns.add_resource(Coup, '/perform-coup')
user_commands_ns.add_resource(ForeignAid, '/request-foreign-aid')
user_commands_ns.add_resource(Steal, '/steal-from-target')
user_commands_ns.add_resource(Block, '/block-target')
user_commands_ns.add_resource(SwapInfluence, '/swap-influence')