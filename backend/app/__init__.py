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
    """Create default admin and verifier users if they don't exist."""
    from .models import User
    try:
        if not User.query.filter_by(email='admin@certsentinel.dev').first():
            admin = User(
                email='admin@certsentinel.dev',
                password_hash=bcrypt.generate_password_hash('admin123').decode('utf-8'),
                role='admin'
            )
            db.session.add(admin)
        if not User.query.filter_by(email='verifier@certsentinel.dev').first():
            verifier = User(
                email='verifier@certsentinel.dev',
                password_hash=bcrypt.generate_password_hash('verifier123').decode('utf-8'),
                role='verifier'
            )
            db.session.add(verifier)
        db.session.commit()
        app.logger.info('Default users verified/created.')
    except Exception as e:
        db.session.rollback()
        app.logger.warning(f'Could not seed default users: {e}')

def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config, silent=True, namespace='CELERY')
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
    
    # Ensure upload directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Global Error Handlers
    from .errors import register_error_handlers
    register_error_handlers(app)

    # Blueprints
    from .routes.certificates import bp as certificates_bp
    from .routes.auth import bp as auth_bp
    from .routes.admin import bp as admin_bp
    
    app.register_blueprint(certificates_bp, url_prefix='/api/certificates')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')

    # Initialize database tables and seed default admin user
    with app.app_context():
        db.create_all()
        _seed_default_users(app)

    return app
