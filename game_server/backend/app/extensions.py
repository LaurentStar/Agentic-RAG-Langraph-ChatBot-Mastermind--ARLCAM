"""
Game Server Extensions.

Shared extensions that are initialized once and used across the application.
Follows the Flask extension pattern - declare here, initialize in create_app().
"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_restx import Api


#=======================#
# SQL ALCHEMY EXTENSION #
#=======================#
class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


#=====================#
# RESTX API EXTENSION #
#=====================#
api = Api()
