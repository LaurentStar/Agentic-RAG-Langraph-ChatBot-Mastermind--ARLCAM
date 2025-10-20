
from flask import jsonify,  make_response, request
from flask_restx import Api, Resource, fields, Namespace
from app.extensions import api, lang_graph_app
from app.models.rest_api_models.llm_notification_models import (
    notify_llm_payload_rest_api_model
)

#-------------# 
# Name Spaces # 
#-------------#
llm_notifications_ns = Namespace('llm-notifcations', description='Update that will be given to all llms players (chat messages, player action, updates from servers or supervisor agent). T')


#-----------# 
# Resources # 
#-----------#
class NotifyLLMs(Resource):
    @llm_notifications_ns.expect(notify_llm_payload_rest_api_model, validate=True)
    def post(self):
        '''Notify all llm about an message or email'''

        payload_data = request.get_json()
        status = None
        status_code = None
        message = None
        response = None

        # ---------------------- Sanity Check ---------------------- #
        if not isinstance(payload_data, dict):
            status_code = 400
            status = "rejected"
            message = "This endpoint only accepts json payloads. No other formats allowed! thank you!" 
            response = {"status": status, "messgae": message}
            return make_response(jsonify(response), status_code)
        
        try:
            status = 'success'
            status_code = 200
            message = "all agents have been notified"

            # ---------------------- Invoke all llms ---------------------- #
            llm_jbal_response = lang_graph_app.jball_agent_wf.run(initial_state=payload_data)
            # llm2
            # llm3

        except ValueError as e:
            status = 'Failure'
            status_code = 500  
            message = f"A extremely serious critical event has happened....Please don't call the programmer at 1am in the morning. just roll back \n Error: {e}"

        response = { "status": status, "message": message}
        
        return make_response(jsonify(response), status_code)
        


    

 
# ---------------------- Building Resources ---------------------- #
llm_notifications_ns.add_resource(NotifyLLMs, '/test-tone-extract')
