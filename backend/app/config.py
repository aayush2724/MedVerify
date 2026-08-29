import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

class BaseConfig:
    # `db.create_all()` on boot is a development convenience. Production runs
    # `alembic upgrade head` from the entrypoint instead, so the schema has one
    # owner and a migration cannot be silently undone by a model import.
    AUTO_CREATE_TABLES = True

    # Security
    SECRET_KEY = os.environ.get("SECRET_KEY")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)

    # Database — PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'medverify_dev.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {}

    # File uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}
    ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "application/pdf"}

    # ML
    MODEL_PATH = os.environ.get("MODEL_PATH", os.path.join(BASE_DIR, "ml/models/classifier.pkl"))
    MODEL_VERSION = os.environ.get("MODEL_VERSION", "v1.0.0")
    CONFIDENCE_THRESHOLD_GENUINE = 0.75
    CONFIDENCE_THRESHOLD_SUSPICIOUS = 0.45

    # Celery / Redis (async jobs)
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL)
    JWT_BLOCKLIST_REDIS_URL = os.environ.get("JWT_BLOCKLIST_REDIS_URL", REDIS_URL)
    JWT_BLOCKLIST_REQUIRED = os.environ.get("JWT_BLOCKLIST_REQUIRED", "").lower() in {"1", "true", "yes"}

    # Rate limiting
    RATELIMIT_DEFAULT = "100 per hour"
    RATELIMIT_UPLOAD = "20 per hour"

    # CORS
    CORS_ORIGINS = os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:5175,http://127.0.0.1:5175",
    ).split(",")

class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-do-not-use-in-prod")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    RATELIMIT_STORAGE_URI = "memory://"

class ProductionConfig(BaseConfig):
    DEBUG = False
    AUTO_CREATE_TABLES = False
    # In-memory rate limiting is per-process. With several gunicorn workers each
    # would keep its own counters, so the effective limit becomes N times what
    # was configured and resets on every worker recycle. Redis makes the limit
    # mean what it says across the whole deployment.
    RATELIMIT_STORAGE_URI = os.environ.get(
        "RATELIMIT_STORAGE_URI", BaseConfig.REDIS_URL
    )
    JWT_BLOCKLIST_REQUIRED = os.environ.get("JWT_BLOCKLIST_REQUIRED", "true").lower() in {"1", "true", "yes"}

class TestingConfig(BaseConfig):
    TESTING = True
    SECRET_KEY = "test-secret"
    JWT_SECRET_KEY = SECRET_KEY
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    CELERY_TASK_ALWAYS_EAGER = True  # run tasks synchronously in tests


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
