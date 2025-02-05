# config.py

import os

class Config:
    """Base configuration class"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')
    DEBUG = os.getenv('DEBUG', 'True') == 'True'
    SERVER_HOST = os.getenv('SERVER_HOST', 'localhost')
    SERVER_PORT = int(os.getenv('SERVER_PORT', 5000))
    VIDEO_ALLOWED_COUNT = int(os.getenv('VIDEO_ALLOWED_COUNT', 4))
    LOG_FOLDER = os.getenv('LOG_FOLDER', 'logs/')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads/')
    TEMPLATES_FOLDER = os.getenv('TEMPLATES_FOLDER', 'templates')
    STATIC_FOLDER = os.getenv('STATIC_FOLDER', 'static')
    LIVE_CCTV_IPS = os.getenv('LIVE_CCTV_IPS', '').split(',')
    LIVE_CCTV_FILES = os.getenv('LIVE_CCTV_FILES', '').split(',') 
    # DEFAULT_USERNAME = os.getenv('DEFAULT_USERNAME', 'admin@')
    # DEFAULT_PASSWORD = os.getenv('DEFAULT_PASSWORD', 'admin123')

    # MySQL Database Configuration
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'mysql+mysqlconnector://username:password@localhost/database_name')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
