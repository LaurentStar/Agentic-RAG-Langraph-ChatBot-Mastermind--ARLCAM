from flask import Blueprint
from flask_restx import Api, Resource, fields, Namespace


#-----------------------------#
# Create a blueprint instance #
#-----------------------------#
test_bp = Blueprint('test_bp', __name__, url_prefix='/products')
api = Api(test_bp, 
          version='1.0', 
          title='test', 
          description='Commands that can be requested by a user')




# ---------------------- Name Spaces ---------------------- #
test_ns = Namespace('utests', description='Command requested by users')


# ---------------------- Resources ---------------------- #
class CommandRegisterUsers(Resource):
    def post(self):
        return 'Hi'
    

# ---------------------- Building Namespaces & Resources ---------------------- #
api.add_namespace(test_ns)
test_ns.add_resource(CommandRegisterUsers, '/test-stufff')

