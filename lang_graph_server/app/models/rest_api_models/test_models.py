from app.extensions import api
from flask_restx import fields, reqparse


#---------------------------#
# JSON PAYLOAD INPUT MODELS #
#---------------------------#
test = api.model('Test', {
    'message': fields.String(required=True),
})
