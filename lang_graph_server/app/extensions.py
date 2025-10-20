# from flask_sqlalchemy import SQLAlchemy
# from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from flask_restx import Api
from app.graphs.lang_graph_app import LangGraphApp
from langchain_openai import ChatOpenAI



#=========#
# PROMPTS #
#=========#
class LoadedPromptTemplates():
    """All loaded prompt templates ready to be used"""
    markdown_prompt_templates = {}
    yaml_prompt_templates = {}
    json_prompt_templates = {}
    xml_prompt_templates = {}
    html_prompt_templates = {}

#================#
# AVAILIBLE LLMs #
#================#
class LoadedLLMs():
    gpt_llm = None
    gemini_llm = None
    bloom_llm = None

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






