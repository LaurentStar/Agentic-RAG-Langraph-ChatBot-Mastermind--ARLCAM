
from flask import jsonify,  make_response, request
from flask_restx import Api, Resource, fields, Namespace

# from sqlalchemy.exc import IntegrityError
# from sqlalchemy.orm.attributes import flag_modified
import requests

# from app.models.postgres_sql_db_models.player import Player, ToBeInitiatedUpgradeDetails
# from app.constants import SocialMediaPlatform, CardType, PlayerStatus, SpecialAbilityCost, ToBeInitiated
# from app.extensions import db
from app.extensions import api
from app.extensions import lang_graph_app
from app.models.rest_api_models.llm_notification_models import (
    notify_llm_payload_rest_api_model)

# ---------------------- Name Spaces ---------------------- #
llm_notifications_ns = Namespace('llm-notifcations', description='Update that will be given to all llms players (chat messages, player action, updates from servers or supervisor agent). T')


# ---------------------- Resources ---------------------- #
class NotifyLLMs(Resource):
    @llm_notifications_ns.expect(notify_llm_payload_rest_api_model, validate=True)
    def post(self):
        '''Notify all llm about an message or email'''

        payload_data = request.get_json()

        if not isinstance(payload_data, dict):
            return False
        
        try:
            status = 'Success'
            status_code = 200
            
            # ---------------------- Invoke all llms ---------------------- #
            llm_jbal_response = lang_graph_app.jball_agent_app.invoke(input={"message":  payload_data.get('message', 'message not found')})
            # llm2
            # llm3

            message = "all agents have been notified"


        except ValueError as e:
            status = 'Failure'
            status_code = 500  
            message = f'{e}'



        response = {
            "status": status,
            "message": message
        }
        
        return make_response(jsonify(response), status_code)
        


    

 
# ---------------------- Building Resources ---------------------- #
llm_notifications_ns.add_resource(NotifyLLMs, '/test-tone-extract')
