
from flask_restx import Api, Resource, fields, Namespace




# ---------------------- Name Spaces ---------------------- #
user_commands_ns = Namespace('user-commands', description='Command requested by users and bots')


# ---------------------- Resources ---------------------- #
class RegisterUsers(Resource):
    def post(self, display_name:str, social_media_platform_display_name:str, social_media_platform:str, card_types:str):
        '''Registers a user or bot into an existing game'''
    
    
# ---------------------- Building Resources ---------------------- #
user_commands_ns.add_resource(RegisterUsers, '/register-user')


