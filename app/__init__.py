from flask import Flask
from .config import load_config
from .db import init_db
from .routes import bp as routes_bp
import os


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")

    # Load configuration
    load_config(app)

    # Ensure data directories exist
    os.makedirs(app.config["IMAGE_DIR"], exist_ok=True)
    os.makedirs(app.config["DB_DIR"], exist_ok=True)

    # Serve images directly from filesystem path under /
    # Use a simple rule in front server or ensure paths are within project dir

    # Initialize database
    init_db(app)

    # Register routes
    app.register_blueprint(routes_bp)

    return app 