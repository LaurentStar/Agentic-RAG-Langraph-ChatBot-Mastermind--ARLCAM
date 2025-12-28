from dotenv import load_dotenv; load_dotenv()
from app import create_app
import os


app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get("GAME_SERVER_PORT", 5000))
    debug = bool("True" == os.environ.get("GAME_SERVER_DEBUG", "False").capitalize())
    app.run(port=port, debug=debug)  