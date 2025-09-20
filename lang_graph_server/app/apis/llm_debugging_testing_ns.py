
from flask import jsonify,  make_response, request
from flask_restx import Api, Resource, fields, Namespace

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.attributes import flag_modified

# from app.models.postgres_sql_db_models.player import Player, ToBeInitiatedUpgradeDetails
# from app.constants import SocialMediaPlatform, CardType, PlayerStatus, SpecialAbilityCost, ToBeInitiated
# from app.extensions import db
from app.extensions import api
from app.extensions import lang_graph_app
from app.models.rest_api_models.test_models import (
    test )

# ---------------------- Name Spaces ---------------------- #
debug_test_ns = Namespace('debug-text', description='Update that will be given to all llms players (chat messages, player action, updates from master agent). T')


# ---------------------- Resources ---------------------- #
class TestPrompts(Resource):
    @debug_test_ns .expect(test, validate=True)
    def post(self):
        '''Test AgentJBallGraphState agent workflow'''

        payload_data = request.get_json()

        if not isinstance(payload_data, dict):
            return False
        

        llm_response = lang_graph_app.jball_agent_app.invoke(input={"message":  payload_data.get('message', 'message not found')})

        return f"{llm_response}"
        


    

 
# ---------------------- Building Resources ---------------------- #
debug_test_ns.add_resource(TestPrompts, '/test-notify-llm')
