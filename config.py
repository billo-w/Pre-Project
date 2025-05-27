import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.getenv('SQLALCHEMY_ECHO', 'False').lower() in ('true', '1', 't')
    WTF_CSRF_ENABLED = True
    # Add other default configs here

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:' # Use in-memory SQLite for tests
    WTF_CSRF_ENABLED = False # Disable CSRF checks in tests for simplicity

class ProductionConfig(Config):
    # Production configs are mostly driven by the app.yaml envs
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    # Add other production-specific settings if needed

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}