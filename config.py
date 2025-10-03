import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Config:
    # Configuration de base
    DEBUG = os.getenv('DEBUG', 'False') == 'True'
    ENV = os.getenv('ENV', 'production')
    SECRET_KEY = os.getenv('SECRET_KEY')
    
    # Configuration base de données
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 20,
        'max_overflow': 0
    }
    
    # Validation des variables d'environnement
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("❌ DATABASE_URL n'est pas défini dans le fichier .env.")

    if not SECRET_KEY:
        SECRET_KEY = os.urandom(32).hex()
        print("⚠️ SECRET_KEY généré temporairement. Définissez-le dans votre fichier .env pour la production.")

    # Configuration des sessions
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = True
    SESSION_USE_SIGNER = True
    SESSION_FILE_DIR = os.path.join(os.getcwd(), 'flask_session')
    SESSION_FILE_THRESHOLD = 100
    SESSION_FILE_MODE = 0o600
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)  # 2 heures d'inactivité
    
    # Configuration des cookies
    SESSION_COOKIE_SECURE = ENV == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_NAME = 'bizzio_session'
    
    # Configuration de sécurité
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 heure
    
    # Configuration des uploads
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    
    # Configuration de l'application
    ITEMS_PER_PAGE = 20
    DEFAULT_LOCALE = 'fr_FR'
    TIMEZONE = 'Africa/Douala'
    
    # Configuration PDF
    PDF_FONT_PATH = os.path.join(os.getcwd(), 'app', 'static', 'fonts')
    
    # Configuration des logs
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.path.join(os.getcwd(), 'logs', 'bizzio.log')
    
    @staticmethod
    def init_app(app):
        """Initialiser l'application avec la configuration"""
        # Créer les dossiers nécessaires
        os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(os.path.dirname(app.config['LOG_FILE']), exist_ok=True)

class DevelopmentConfig(Config):
    DEBUG = True
    ENV = 'development'
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    DEBUG = False
    ENV = 'production'
    SESSION_COOKIE_SECURE = True
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 20,
        'max_overflow': 10,
        'pool_size': 20
    }

class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# Dictionnaire des configurations
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}