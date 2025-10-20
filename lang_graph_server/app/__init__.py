# ---------------------- Standard Library ----------------------#
from pathlib import Path
import os

# ---------------------- Custom ----------------------#
from app.utils.loader import LoadPrompts
from app.constants import PromptFileExtension, AllowedUploadFileTypes

# ---------------------- Custom ----------------------#
from app.extensions import api, lang_graph_app
from app.extensions import LoadedPromptTemplates, LoadedLLMs

# ---------------------- Flask Rest APIs Name Spaces ----------------------#
from app.apis.llm_notify_ns import llm_notifications_ns
from app.apis.llm_debugging_testing_ns import debug_test_ns 

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
    api.add_namespace(llm_notifications_ns)
    api.add_namespace(debug_test_ns)
     

    #----------------#
    # LANG GRAPH APP #
    #----------------# 
    lang_graph_app.init_app()


    return app

