import os
from flask import Flask
from config import Config

# Create the Flask app instance here
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)  # Load configuration from the Config class

    # Ensure upload folder exists
    UPLOAD_FOLDER = app.config['UPLOAD_FOLDER']
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # Ensure logs folder exists
    log_folder = os.path.join(os.getcwd(), app.config['LOG_FOLDER'])
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)

    return app
