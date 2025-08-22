# ---------------------- Flask ----------------------#
from flask import Flask, Blueprint, render_template, render_template_string, request, redirect, url_for
from flask_restx import Api, Resource, fields, Namespace
from flask_apscheduler import APScheduler


# ---------------------- Misc ----------------------#
from app.extensions import db
from app.models.player import User


# ---------------------- Name Spaces ----------------------#
from app.apis.user_command_ns import user_commands_ns


# ---------------------- Blue Prints ----------------------#
# from apis.test_api import test_bp


# ---------------------- Other ----------------------#
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text



def create_app(test_config=None):
    #-------------------#
    #  CREATE FLASK APP #
    #-------------------#
    app = Flask(__name__, instance_relative_config=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql+psycopg://postgres:mysecretpassword@localhost:5432/postgres"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    
    #---------------#
    # JOB SCHEDULER #
    #---------------#
    # Configure APScheduler
    class Config:
        SCHEDULER_API_ENABLED = True

    app.config.from_object(Config())

    scheduler = APScheduler()

    # Define a simple job function
    def scheduled_job():
        print("This job runs every 5 seconds!")

    scheduler.init_app(app)
    scheduler.start()
    scheduler.add_job(id='my_scheduled_job', func=scheduled_job, trigger='interval', seconds=5)


    #-----------#
    # REST APIs #
    #-----------# 
    api = Api(app, 
        version='1.0', 
        title='Game Server API', 
        description='APIs to use LLM and acts as controllers for the game')
    # ---------------------- Name Spaces ---------------------- #
    user_commands_ns = Namespace('user_commands', description='Command requested by users')

    # ---------------------- Resources ---------------------- #
    class CommandRegisterUsers(Resource):
        def get(self):
            return 'Hi'

    # # ---------------------- Building Namespaces & Resources ---------------------- #
    api.add_namespace(user_commands_ns)
    user_commands_ns.add_resource(CommandRegisterUsers, '/register-user')


    #----------------------------------#
    # POSTGRES SQL DATABASE CONNECTION #
    #----------------------------------# 

    db.init_app(app)


    with app.app_context():
        db.create_all()



    # ---------------------- SAMPLE POSTGRES SQL USE CASE ---------------------- #
    @app.route("/users")
    def user_list():
        users = db.session.execute(db.select(User).order_by(User.username)).scalars()
        

        for user in users.all():
            print(isinstance(user, User))

        # return render_template("user/list.html", users=users)
        return render_template_string(f"""
                    {users}
                    """)

    @app.route("/users/create2", methods=["GET", "POST"])
    def user_create2():

        user = User(
            username='Laure',
            email='email@123.com',
        )
        db.session.add(user)
        db.session.commit()
        return 'NEW USER CREATED'



    return app




# #----------------------------------------------------#
# # FLASK APP | REST API | POSTGRES SQL INITIALIZATION #
# #----------------------------------------------------#
# app = Flask(__name__)


# # URI FORMAT:  'postgresql+psycopg://<user>:<password>@<host>:<port>/<database_name>'
# # user = postgres
# # password = mysecretpassword
# # host = localhost
# # port = 5432
# # database name = postgres"
# app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql+psycopg://postgres:mysecretpassword@localhost:5432/postgres"
# app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# api = Api(app, 
#           version='1.0', 
#           title='Game Server API', 
#           description='APIs to use LLM and acts as controllers for the game',)



# ns = api.namespace('todos', description='TODO operations')

# todo = api.model('Todo', {
#     'id': fields.Integer(readonly=True, description='The task unique identifier'),
#     'task': fields.String(required=True, description='The task details')
# })


# #---------------#
# # JOB SCHEDULER #
# #---------------#
# # Configure APScheduler
# class Config:
#     SCHEDULER_API_ENABLED = True

# app.config.from_object(Config())

# scheduler = APScheduler()

# # Define a simple job function
# def scheduled_job():
#     print("This job runs every 5 seconds!")



# #-----------#
# # REST APIs #
# #-----------# 
# # ---------------------- Name Spaces ---------------------- #
# user_commands_ns = Namespace('user_commands', description='Command requested by users')

# # ---------------------- Resources ---------------------- #
# class CommandRegisterUsers(Resource):
#     def get(self):
#         return 'Hi'

# # # ---------------------- Building Namespaces & Resources ---------------------- #
# api.add_namespace(user_commands_ns)
# user_commands_ns.add_resource(CommandRegisterUsers, '/register-user')



# #----------------------------------#
# # POSTGRES SQL DATABASE CONNECTION #
# #----------------------------------# 
# # class Base(DeclarativeBase):
# #   pass

# # db = SQLAlchemy(model_class=Base)
# db.init_app(app)


# # class User(db.Model):
# #     id: Mapped[int] = mapped_column(primary_key=True)
# #     username: Mapped[str] = mapped_column(unique=True)
# #     email: Mapped[str]



# with app.app_context():
#     db.create_all()



# # ---------------------- SAMPLE POSTGRES SQL USE CASE ---------------------- #
# @app.route("/users")
# def user_list():
#     users = db.session.execute(db.select(User).order_by(User.username)).scalars()
    

#     for user in users.all():
#         print(isinstance(user, User))

#     # return render_template("user/list.html", users=users)
#     return render_template_string(f"""
#                 {users}
#                 """)

# @app.route("/users/create2", methods=["GET", "POST"])
# def user_create2():

#     user = User(
#         username='Laure',
#         email='email@123.com',
#     )
#     db.session.add(user)
#     db.session.commit()
#     return 'NEW USER CREATED'




# @app.route("/users/create", methods=["GET", "POST"])
# def user_create():
#     if request.method == "POST":
#         user = User(
#             username=request.form["username"],
#             email=request.form["email"],
#         )
#         db.session.add(user)
#         db.session.commit()
#         return redirect(url_for("user_detail", id=user.id))

#     return render_template("user/create.html")

# @app.route("/user/<int:id>")
# def user_detail(id):
#     user = db.get_or_404(User, id)
#     return render_template("user/detail.html", user=user)

# @app.route("/user/<int:id>/delete", methods=["GET", "POST"])
# def user_delete(id):
#     user = db.get_or_404(User, id)

#     if request.method == "POST":
#         db.session.delete(user)
#         db.session.commit()
#         return redirect(url_for("user_list"))