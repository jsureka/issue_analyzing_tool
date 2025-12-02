import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration."""
    # Flask
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    PORT = int(os.getenv('PORT', 5000))
    
    # Concurrency
    MAX_WORKERS = int(os.getenv('POOL_PROCESSOR_MAX_WORKERS', 4))
    
    # Database
    DB_PATH = os.getenv('DB_PATH', 'issues.db')
    
    # GitHub App
    APP_ID = os.getenv('APP_ID')
    PRIVATE_KEY_PATH = os.getenv('PRIVATE_KEY_PATH', 'private-key.pem')
    WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')
    
    # Models
    DUPLICATE_BR_MODEL_PATH = os.getenv('DUPLICATE_BR_MODEL_PATH', 'models/duplicate_detection')
    SEVERITY_PREDICTION_MODEL_PATH = os.getenv('SEVERITY_PREDICTION_MODEL_PATH', 'models/severity_prediction')
    BUGLOCALIZATION_MODEL_PATH = os.getenv('BUGLOCALIZATION_MODEL_PATH', 'microsoft/unixcoder-base')
    
    # Neo4j
    NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'password')
    
    # LLM (Phase 2)
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    LLM_MODEL_NAME = os.getenv('LLM_MODEL_NAME', 'gemini-2.5-flash')
    LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', 0.2))
    
    # Paths
    # Use a fixed path for repos instead of tempdir for persistence if needed, 
    # or keep tempdir but make it configurable.
    REPO_STORAGE_PATH = os.getenv('REPO_STORAGE_PATH', os.path.join(os.getcwd(), 'insight_repos'))

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
