# from flask_sqlalchemy import SQLAlchemy
# from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from flask_restx import Api
from app.graphs.graph import LangGraphApp
from langchain_openai import ChatOpenAI



#=========#
# PROMPTS #
#=========#
markdown_prompts = {}



#=======================#
# SQL ALCHEMY EXTENSION #
#=======================#
# class Base(DeclarativeBase):
#   pass

# db = SQLAlchemy(model_class=Base)


#=====================#
# RESTX API EXTENSION #
#=====================#
api = Api()


#=====================================#
# LANG GRAPH APP + WORKFLOWS + GRAPHS #
#=====================================#
lang_graph_app = LangGraphApp()



#==========================#
# LLM MODEL INITIALIZATION #
#==========================#
# llm = ChatOpenAI(model="gpt-4o-mini")






