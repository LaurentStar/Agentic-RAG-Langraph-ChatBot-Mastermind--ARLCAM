from app.extensions import api
from flask_restx import fields, reqparse
from app.constants import SocialMediaPlatform

#---------------------------#
# JSON PAYLOAD INPUT MODELS #
#---------------------------#
notify_llm_payload_rest_api_model = api.model('NotifyLLMPayload', {
    'chat_message': fields.String(required=True, description='message from public chat or email'),
    'social_media_platform': fields.String(required=True, enum=[social.value for social in SocialMediaPlatform], description='The social media platform'),
})
