from app.extensions import api
from flask_restx import fields, reqparse
from app.constants import SocialMediaPlatform, CardType, PlayerStatus

#---------------------------#
# JSON PAYLOAD INPUT MODELS #
#---------------------------#
register_player_payload_rest_api_model = api.model('RegisterPlayerPayload', {
    'display_name': fields.String(required=True, description='Display name within the game'),
    'social_media_platform_display_name': fields.String(required=True, description='Display name on social media platform where player registered from'),
    'social_media_platform': fields.String(required=True, enum=[social.value for social in SocialMediaPlatform], description='The social media platform'),
    'card_types': fields.List(fields.String(required=True, enum=[card.value for card in CardType], description='List of card types in player possession'), required=True),
    'player_statuses': fields.List(fields.String(required=True, enum=[player_status.value for player_status in PlayerStatus], description='The statuses effecting the player.'), required=True),
    'coins' : fields.Integer(required=True, description='Number of coins to start with'),
})

assassinate_payload_rest_api_model = api.model('AssassinatePayload', {
    'assassin_display_name': fields.String(required=True, description='The name of the player initiating the assassination'),
    'assassin_priority': fields.String(required=False, enum=[card.value for card in CardType], description='For 2 extra coins the assasin can remove a specific card if it exist in the hand of the target'),
    'assassin_priority_upgrade': fields.Boolean(required=False, description='For 2 extra coins the assasin can remove a specific card if it exist in the hand of the target'),
    'target_display_name': fields.String(required=True, description='The name of player targeted for assassination'),
})

coup_payload_rest_api_model = api.model('CoupPayload', {
    'caudillo_display_name': fields.String(required=True, description='The name of the player initiating the coup. Caudillo A Spanish term for a military-political leader, historically used in Spain and Latin America for strongmen who came to power, often by force.'),
    'deposed_influencer_display_name': fields.String(required=True, description='The name of player targeted for coup. One of thier influencer cards will be deposed'),
})

# model for most generic actions
generic_payload_rest_api_model = api.model('GenericPayload', {
    'player_display_name': fields.String(required=True, description='The name of the player initiating the action.'),
    'player_upgrade' : fields.Boolean(required=False, description='Flag to mark player action as upgraded'),
    'target_display_name': fields.String(required=True, description='The name of player targeted for action.'),
})

# generic model, without target required
generic_target_not_required_payload_rest_api_model = api.model('GenericTargetNotRequiredPayload', {
    'player_display_name': fields.String(required=True, description='The name of the player initiating the action.'),
    'player_upgrade' : fields.Boolean(required=False, description='Flag to mark player action as upgraded'),
    'target_display_name': fields.String(required=False, description='The name of player targeted for action.'),
})



player_query_payload_rest_api_model = api.model('PlayerPayload', {
    'display_name': fields.String(required=True, description='The name of the player. This is a primary key in the database. It is used for a few apis generically'),
})


#---------------------------------------------#
# JSON RESPONSE OUTPUT MODELS FOR MARSHALLING #
#---------------------------------------------#
player_data_response_marshal = api.model('PlayerDataResponse', {
    'status': fields.String(required=True),
    'status code': fields.Integer(required=True),
    'message': fields.String(required=True),
    'player data' : fields.Nested(register_player_payload_rest_api_model, required=True)
})


#---------------------------------#
# Query Parameter Input Arguments #
#---------------------------------#
retrieve_player_profile_parser = reqparse.RequestParser()
retrieve_player_profile_parser.add_argument('display_name', type=str, help='Player unique display name in game server', location='args', required=True)