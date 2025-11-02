from app.extensions import api
from flask_restx import fields, reqparse
from app.constants import SocialMediaPlatform
from werkzeug.datastructures import FileStorage

#---------------------------#
# JSON PAYLOAD INPUT MODELS #
#---------------------------#
notify_llm_payload_rest_api_model = api.model('NotifyLLMPayload', {
    'message': fields.String(required=True, description='message from public chat or email'),
    'message_meta_social_media_platform': fields.String(required=True, enum=[social.name for social in SocialMediaPlatform], description='The social media platform'),
})


#---------------------------#
# FILE INPUT MODELS GENERIC #
#---------------------------#
upload_parser = api.parser()
upload_parser.add_argument('file', location='files', type=FileStorage, required=True, help='generic file uploaded')
upload_parser.add_argument('custom_json_field', location='form', type=str, required=True, choices=[social.name for social in SocialMediaPlatform], help="extra field in form")