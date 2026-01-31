"""
Game Server Extensions.

Shared extensions that are initialized once and used across the application.
Follows the Flask extension pattern - declare here, initialize in create_app().
"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_restx import Api
from flask_cors import CORS


#=======================#
# SQL ALCHEMY EXTENSION #
#=======================#
class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


#=====================#
# RESTX API EXTENSION #
#=====================#
# Authorization options for Swagger UI
# Note: authorizations must be passed at Api() declaration for Swagger UI button to appear
authorizations = {
    'Bearer': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization',
        'description': 'JWT token. Format: "Bearer {token}"'
    },
    'CoupOpsKey': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Coup-Ops-Key',
        'description': 'Developer operations API key for /ops/* endpoints'
    },
    'CoupServiceKey': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Coup-Service-Key',
        'description': 'Service-to-service API key for bot integrations'
    }
}

api = Api(
    authorizations=authorizations,
    security='Bearer'
)


#================#
# CORS EXTENSION #
#================#
# Configured in create_app() with allowed origins
cors = CORS()
