"""
Celery Worker Entry Point
Run with: celery -A celery_worker.celery_app worker --loglevel=info
"""
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import create_app
from app.config import DevelopmentConfig, config_by_name

# The worker must honour FLASK_ENV exactly as the web process does. A bare
# `create_app()` defaults to DevelopmentConfig, which in production would run
# the worker with the dev secret key and — because DevelopmentConfig sets
# CELERY_TASK_ALWAYS_EAGER — execute tasks inline instead of consuming the
# queue, leaving jobs to pile up unprocessed.
env = os.environ.get("FLASK_ENV", "development")
flask_app = create_app(config_by_name.get(env, DevelopmentConfig))
celery_app = flask_app.extensions["celery"]
