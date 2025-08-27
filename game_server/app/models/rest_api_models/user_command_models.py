from app.extensions import api
from flask_restx import fields, reqparse
from app.constants import SocailMediaPlatform, CardType, PlayerStatus

#---------------------------#
# JSON PAYLOAD INPUT MODELS #
#---------------------------#
register_player_payload_rest_api_model = api.model('RegisterPlayerPayload', {
    'display_name': fields.String(required=True, description='Display name within the game'),
    'social_media_platform_display_name': fields.String(required=True, description='Display name on social media platform where player registered from'),
    'social_media_platform': fields.String(required=True, enum=[social.value for social in SocailMediaPlatform], description='The social media platform'),
    'card_types': fields.List(fields.String(required=True, enum=[card.value for card in CardType], description='List of card types in player possession'), required=True),
    'player_statuses': fields.List(fields.String(required=True, enum=[player_status.value for player_status in PlayerStatus], description='The statuses effecting the player.'), required=True)
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