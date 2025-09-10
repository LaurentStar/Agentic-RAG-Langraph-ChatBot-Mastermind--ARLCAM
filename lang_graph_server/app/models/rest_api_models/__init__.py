


from app.extensions import api
from flask import Flask, Blueprint, render_template, render_template_string, request, redirect, url_for


def create_app(test_config=None):
    #-------------------#
    #  CREATE FLASK APP #
    #-------------------#
    app = Flask(__name__, instance_relative_config=True)
    # app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql+psycopg://postgres:mysecretpassword@localhost:5432/postgres"
    # app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # app.config['SQLALCHEMY_BINDS'] = {
    #     'db_players': 'postgresql+psycopg://player_manager:pm_manager1@localhost:5432/player',
    # }
    # app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    #     'connect_args': {'connect_timeout': 10}
    # }


    #-----------#
    # REST APIs #
    #-----------# 
    api.init_app(app,
                 version='1.0', 
                 title='Lang Graph API', 
                 description='APIs to use to interact with llm agents') 
     
    #-------------------------------------#
    # Creating the lang graph application #
    #-------------------------------------#
    return app

