import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-me'
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'sqlite:///gdm_database.db'
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MODEL_PATH = os.environ.get('MODEL_PATH', './model')
    RISK_THRESHOLD_LOW = float(os.environ.get('RISK_THRESHOLD_LOW', '0.33'))
    RISK_THRESHOLD_HIGH = float(os.environ.get('RISK_THRESHOLD_HIGH', '0.66'))
    MODEL_VERSION = os.environ.get('MODEL_VERSION', '1.0.0')
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = os.environ.get('SESSION_COOKIE_HTTPONLY', 'True').lower() == 'true'
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
    ITEMS_PER_PAGE = int(os.environ.get('ITEMS_PER_PAGE', '20'))
    MAX_UPLOAD_SIZE = int(os.environ.get('MAX_UPLOAD_SIZE', '16777216'))

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False
    WTF_CSRF_ENABLED = False  # TEMPORARY - disable CSRF for testing

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True

class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}