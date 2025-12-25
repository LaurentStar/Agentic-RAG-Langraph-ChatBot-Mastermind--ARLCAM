# from flask_sqlalchemy import SQLAlchemy
# from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from flask_restx import Api
from langchain_openai import ChatOpenAI

from app.graphs.lang_graph_app import LangGraphApp
from app.database.connection import DatabaseConnection
from app.agents.agent_registry import AgentRegistry
from app.services.checkpointer_factory import CheckpointerFactory
from app.services.game_server_client import GameServerClientFactory

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


#======================================#
# DATABASE CONNECTION (GAME SERVER DB) #
#======================================#
# Declared here, initialized in __init__.py
# Provides read-only access to game server PostgreSQL
db_connection = DatabaseConnection()


#=================#
# AGENT REGISTRY  #
#=================#
# Declared here, initialized in __init__.py
# Manages multiple LLM agent instances per game
agent_registry = AgentRegistry()


#======================================#
# LANGGRAPH CHECKPOINTER               #
#======================================#
# Declared here, initialized in __init__.py
# Provides conversation persistence for LLM agents
# Uses PostgresSaver for persistent storage
# Thread IDs format: "{game_id}:{agent_id}" for agent isolation
langgraph_checkpointer = CheckpointerFactory()


#======================================#
# GAME SERVER CLIENT FACTORY           #
#======================================#
# Declared here, initialized in __init__.py
# Creates per-agent HTTP clients for game server API calls
# Each agent gets its own client with its own JWT auth
game_server_client_factory = GameServerClientFactory()