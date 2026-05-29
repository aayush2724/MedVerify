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

flask_app = create_app()
celery_app = flask_app.extensions["celery"]
