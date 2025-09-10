

from pathlib import Path
from app.extensions import api, markdown_prompts, lang_graph_app
from flask import Flask, Blueprint, render_template, render_template_string, request, redirect, url_for



# ---------------------- Name Spaces ----------------------#
from app.apis.llm_notify_ns import user_commands_ns

def create_app(test_config=None):

    #--------------#
    # LOAD PROMPTS # !!! Must be loaded first
    #--------------#
    script_dir = Path(__file__).parent
    file_path = script_dir / "prompts" / "tone_extractor_prompt.md"
    with open(file_path, "r", encoding="utf-8") as f:
        markdown_prompts[file_path.name] = f.read()


    #-------------------#
    #  CREATE FLASK APP #
    #-------------------#
    app = Flask(__name__, instance_relative_config=True)


    #-----------#
    # REST APIs #
    #-----------# 
    api.init_app(app,
                 version='1.0', 
                 title='Lang Graph API', 
                 description='APIs to use to interact with llm agents') 
    
    
    # ---------------------- Building Namespaces ---------------------- #
    api.add_namespace(user_commands_ns)
     



    #----------------#
    # LANG GRAPH APP #
    #----------------# 
    lang_graph_app.init_app()


    #-------------------------------------#
    # Creating the lang graph application #
    #-------------------------------------#
    return app

