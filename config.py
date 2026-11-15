import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base Configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key-for-dev-only")
    
    # Primary application database URL (mindguard_app restricted role)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", 
        "postgresql+psycopg://mindguard_app:MindGuardApp2026!@localhost:5432/mindguard_db"
    )
    # Migration database URL (used by Alembic / Flask-Migrate with higher schema privileges)
    MIGRATION_DATABASE_URL = os.getenv(
        "MIGRATION_DATABASE_URL",
        "postgresql+psycopg://mindguard_migrator:MindGuardMigrator2026!@localhost:5432/mindguard_db"
    )
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 1800,
    }

    # Fernet encryption key for journal entries
    FERNET_KEY = os.getenv("FERNET_KEY", "")

    # Session & Cookie Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"

    # Flask-Limiter
    RATELIMIT_DEFAULT = "200 per day, 50 per hour"
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_STRATEGY = "fixed-window"


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    DEBUG = False
    TESTING = True
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    # Use direct test connection
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL",
        os.getenv("DATABASE_URL", "postgresql+psycopg://mindguard_app:MindGuardApp2026!@localhost:5432/mindguard_db")
    )
    # Fernet key for testing
    FERNET_KEY = os.getenv("FERNET_KEY", "zn5ZY7pqOZP_aEP8H1px3oLyYY_TTte-tDadH-t35HM=")


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
