import os
import logging
from flask import Flask
from flask_cors import CORS
from celery import Celery, Task
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt

from .database import db
from .config import DevelopmentConfig

limiter = Limiter(key_func=get_remote_address)
jwt = JWTManager()
bcrypt = Bcrypt()

def _seed_default_users(app):
    """Create optional development users from environment-provided credentials."""
    from .models import User
    seed_users = [
        ("admin@medverify.dev", os.environ.get("MEDVERIFY_SEED_ADMIN_PASSWORD"), "admin"),
        ("verifier@medverify.dev", os.environ.get("MEDVERIFY_SEED_VERIFIER_PASSWORD"), "verifier"),
        ("viewer@medverify.dev", os.environ.get("MEDVERIFY_SEED_VIEWER_PASSWORD"), "viewer"),
    ]
    if not any(password for _, password, _ in seed_users):
        app.logger.info('Default user seeding skipped; no seed passwords configured.')
        return

    try:
        for email, password, role in seed_users:
            if password and not User.query.filter_by(email=email).first():
                db.session.add(User(
                    email=email,
                    password_hash=bcrypt.generate_password_hash(password).decode('utf-8'),
                    role=role,
                ))
            
        db.session.commit()
        app.logger.info('Default users verified/created.')
    except Exception as e:
        db.session.rollback()
        app.logger.warning(f'Could not seed default users: {e}')

def _seed_ingredient_limits(app):
    """Load the curated maximum-daily-dose table used by Module 2.

    Idempotent and re-runnable: rows are upserted by ingredient key so editing
    `app/data/ingredient_limits.py` and restarting is enough to publish a
    corrected limit. Without this table the safety engine reports "no published
    limit on file" rather than guessing, so a failure here degrades the feature
    instead of producing wrong numbers.
    """
    from .models import IngredientLimit
    from .data.ingredient_limits import INGREDIENT_LIMITS

    try:
        existing = {row.ingredient_key: row for row in IngredientLimit.query.all()}
        for entry in INGREDIENT_LIMITS:
            row = existing.get(entry["ingredient_key"])
            if row is None:
                db.session.add(IngredientLimit(**entry))
            else:
                for field, value in entry.items():
                    setattr(row, field, value)
        db.session.commit()
        app.logger.info("Ingredient dose limits seeded (%d entries).", len(INGREDIENT_LIMITS))
    except Exception as e:
        db.session.rollback()
        app.logger.warning("Could not seed ingredient limits: %s", e)


def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.conf.update(
        broker_url=app.config["CELERY_BROKER_URL"],
        result_backend=app.config["CELERY_RESULT_BACKEND"],
        task_always_eager=app.config.get("CELERY_TASK_ALWAYS_EAGER", False),
        task_eager_propagates=app.config.get("CELERY_TASK_EAGER_PROPAGATES", False),
    )
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app

def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config_class)
    if not app.config.get("DEBUG") and not app.config.get("SECRET_KEY"):
        raise ValueError("No SECRET_KEY set for Flask application")

    # Initialize Extensions
    db.init_app(app)
    bcrypt.init_app(app)
    CORS(app, origins=app.config["CORS_ORIGINS"])
    celery_init_app(app)
    limiter.init_app(app)
    jwt.init_app(app)

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        from .routes.auth import is_token_revoked
        return is_token_revoked(jwt_payload)
    
    # Ensure upload directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Global Error Handlers
    from .errors import register_error_handlers
    register_error_handlers(app)

    # Blueprints
    from .routes.certificates import bp as certificates_bp
    from .routes.auth import bp as auth_bp
    from .routes.admin import bp as admin_bp
    from .routes.medications import bp as medications_bp
    from .routes.pipeline import bp as pipeline_bp
    from .routes.health import bp as health_bp

    app.register_blueprint(certificates_bp, url_prefix='/api/certificates')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(medications_bp, url_prefix='/api/medications')
    app.register_blueprint(pipeline_bp, url_prefix='/api/pipeline')
    app.register_blueprint(health_bp, url_prefix='/api/health')

    # Initialize database tables and seed reference data
    with app.app_context():
        # Alembic owns the schema in production; create_all() there would race
        # the migration and could resurrect a table a migration had dropped.
        # In development and tests it is the fastest way to a working database.
        if app.config.get("AUTO_CREATE_TABLES", True):
            db.create_all()
        _seed_default_users(app)
        _seed_ingredient_limits(app)

    return app
