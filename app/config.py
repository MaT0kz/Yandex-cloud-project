import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration class."""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-prod'
    FLASK_APP = os.environ.get('FLASK_APP') or 'app.py'
    
    # Database settings - support both PostgreSQL and SQLite
    DATABASE_URL = os.environ.get('DATABASE_URL') or None
    
    # PostgreSQL settings (Managed Service)
    DB_HOST = os.environ.get('DB_HOST') or 'localhost'
    DB_PORT = os.environ.get('DB_PORT') or '5432'
    DB_NAME = os.environ.get('DB_NAME') or 'news_db'
    DB_USER = os.environ.get('DB_USER') or 'news_user'
    DB_PASSWORD = os.environ.get('DB_PASSWORD') or 'password'
    
    @staticmethod
    def get_db_url():
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            return database_url
        return f"postgresql://{Config.DB_USER}:{Config.DB_PASSWORD}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}"
    
    # Yandex Object Storage settings
    YANDEX_ACCESS_KEY_ID = os.environ.get('YANDEX_ACCESS_KEY_ID') or ''
    YANDEX_SECRET_ACCESS_KEY = os.environ.get('YANDEX_SECRET_ACCESS_KEY') or ''
    YANDEX_BUCKET_NAME = os.environ.get('YANDEX_BUCKET_NAME') or 'news-site-storage'
    YANDEX_ENDPOINT_URL = os.environ.get('YANDEX_ENDPOINT_URL') or 'https://storage.yandexcloud.net'
    YANDEX_REGION = os.environ.get('YANDEX_REGION') or 'ru-central1'
    
    # Yandex Message Queue settings
    YANDEX_SQS_ENDPOINT_URL = os.environ.get('YANDEX_SQS_ENDPOINT_URL') or 'https://message-queue.api.cloud.yandex.net'
    YANDEX_SQS_QUEUE_URL = os.environ.get('YANDEX_SQS_QUEUE_URL') or ''
    
    # Static files URL
    STATIC_FILES_URL = os.environ.get('STATIC_FILES_URL') or '/static/uploads'


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = Config.get_db_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = Config.get_db_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
