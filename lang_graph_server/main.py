from dotenv import load_dotenv; load_dotenv('.env')
from app import create_app
import os


app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get("LANG_GRAPH_PORT", 5000))
    debug = bool("True" == os.environ.get("LANG_GRAPH_DEBUG", "False").capitalize())
    app.run(port=port, debug=debug)  