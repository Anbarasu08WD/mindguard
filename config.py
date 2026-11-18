
import os
from datetime import timedelta
from dotenv import load_dotenv

# Load local .env for development.
# Vercel uses its configured Environment Variables.
load_dotenv()


def _normalize_db_url(url):
    """Make provider URLs work with SQLAlchemy 2 + psycopg 3.

    Neon, Supabase and Vercel Postgres often hand out postgres:// or postgresql://
    URLs, which SQLAlchemy would try to open with psycopg2 (not installed).
    """
    if not url:
        return url
    url = url.strip()
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def _env_db(name, default=None):
    return _normalize_db_url(os.getenv(name, default))


class Config:
    """Base application configuration."""

    # Application security
    SECRET_KEY = os.getenv("SECRET_KEY")

    # Primary database connection (restricted application role)
    SQLALCHEMY_DATABASE_URI = _env_db("DATABASE_URL")

    # Separate migration connection (privileged migration role)
    MIGRATION_DATABASE_URL = _env_db("MIGRATION_DATABASE_URL")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Conservative connection pool settings for serverless deployment.
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_size": 2,
        "max_overflow": 0,
        "pool_recycle": 300,
        # Required when the database sits behind a transaction pooler
        # (PgBouncer, Neon pooled host, Supabase pooler): no server-side prepared statements.
        "connect_args": {"prepare_threshold": None},
    }

    # Preserve the existing key to decrypt previously encrypted journal entries.
    FERNET_KEY = os.getenv("FERNET_KEY", "")

    # Session and cookie security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False

    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = False

    # Flask-Limiter
    RATELIMIT_DEFAULT = "200 per day, 50 per hour"
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_STRATEGY = "fixed-window"


class DevelopmentConfig(Config):
    """Local development configuration."""

    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Automated testing configuration."""

    DEBUG = False
    TESTING = True

    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False

    SQLALCHEMY_DATABASE_URI = _env_db("TEST_DATABASE_URL", os.getenv("DATABASE_URL"))

    FERNET_KEY = os.getenv("FERNET_KEY", "")


class ProductionConfig(Config):
    """Production configuration for Vercel."""

    DEBUG = False
    TESTING = False

    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True

    # Production must use explicitly configured environment variables.
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = _env_db("DATABASE_URL")
    MIGRATION_DATABASE_URL = _env_db("MIGRATION_DATABASE_URL")
    FERNET_KEY = os.getenv("FERNET_KEY", "")


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
