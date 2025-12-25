# ---------------------- Standard Library ----------------------#
from pathlib import Path
import os

# ---------------------- Custom ----------------------#
from app.utils.loader import LoadPrompts
from app.constants import PromptFileExtension, AllowedUploadFileTypes

# ---------------------- Custom ----------------------#
from app.extensions import api, lang_graph_app
from app.extensions import LoadedPromptTemplates, LoadedLLMs
from app.extensions import db_connection, agent_registry, langgraph_checkpointer
from app.extensions import game_server_client_factory

# ---------------------- Flask Rest APIs Name Spaces ----------------------#
from app.apis.notifications import infrastructure_ns
from app.apis.coup_event_ns import coup_event_ns 

# ---------------------- External Modeules ----------------------#
from flask import Flask
from flask_cors import CORS
from langchain_openai import ChatOpenAI


def create_app(test_config=None):
    #--------------#
    # LOAD PROMPTS # !!! Must be loaded first
    #--------------#
    script_dir = Path(__file__).parent
    folder_path = script_dir / "prompts"
    LoadedPromptTemplates.markdown_prompt_templates = LoadPrompts.load_prompt_templates(folder_path, PromptFileExtension.MARKDOWN)

    
    #----------------------#
    # LOAD LLMS EXPLICITLY #
    #----------------------#
    # ---------------------- gpt 4.0  ---------------------- #
    api_key = os.environ.get("OPENAI_API_KEY")
    endpoint = os.environ.get("DEFAULT", None)
    model_name = os.environ.get("OPENAI_API_MODEL")
    LoadedLLMs.gpt_llm = ChatOpenAI(base_url=endpoint, api_key=api_key, model_name=model_name, temperature=0.1)



    #-------------------#
    #  CREATE FLASK APP #
    #-------------------#
    app = Flask(__name__, instance_relative_config=True)
    app.config['UPLOAD_EXTENSIONS'] = [member.value for member in AllowedUploadFileTypes]
    # CORS(app, orgins=["url1, url2, url3"])

    #-----------#
    # REST APIs #
    #-----------# 
    api.init_app(app,
                 version='1.0', 
                 title='Lang Graph API', 
                 description='APIs to use to interact with llm agents') 
    
    
    # ---------------------- Building Namespaces ---------------------- #
    api.add_namespace(infrastructure_ns)
    api.add_namespace(coup_event_ns)
     

    #--------------------#
    # DATABASE CONNECTION #
    #--------------------#
    # Initialize PostgreSQL connection to game server database
    # db_connection is declared in extensions.py
    # This provides read-only access for LLM agents to query:
    # - Pending game events
    # - Player profiles
    # - Game state
    try:
        db_connection.init_app()
        if db_connection.test_connection():
            print("PostgreSQL connection established successfully")
        else:
            print("Warning: PostgreSQL connection test failed - database features may not work")
    except Exception as e:
        print(f"Warning: Failed to initialize database connection: {e}")
        print("LLM agents will operate without direct database access")
    
    #----------------#
    # AGENT REGISTRY #
    #----------------#
    # agent_registry is declared in extensions.py
    # No initialization needed - it's ready to use
    # Agents are registered dynamically when games start
    print(f"Agent registry initialized: {agent_registry.get_stats()}")

    #-----------------------#
    # LANGGRAPH CHECKPOINTER #
    #-----------------------#
    # langgraph_checkpointer is declared in extensions.py
    # Uses PostgresSaver for persistent conversation history
    # Falls back to MemorySaver if PostgreSQL unavailable
    try:
        langgraph_checkpointer.init_app(use_postgres=True)
        print(f"LangGraph checkpointer initialized: {langgraph_checkpointer.get_status()}")
    except Exception as e:
        print(f"Warning: Checkpointer initialization failed: {e}")
        langgraph_checkpointer.init_app(use_postgres=False)

    #------------------------------#
    # GAME SERVER CLIENT FACTORY   #
    #------------------------------#
    # game_server_client_factory is declared in extensions.py
    # Creates per-agent HTTP clients for game server API calls
    game_server_url = os.environ.get("GAME_SERVER_URL", "http://localhost:5000")
    game_server_client_factory.init_app(base_url=game_server_url)
    print(f"Game server client factory initialized: {game_server_client_factory.get_status()}")

    #----------------#
    # LANG GRAPH APP #
    #----------------#
    # Must be initialized AFTER checkpointer since workflows use it
    lang_graph_app.init_app()


    return app

