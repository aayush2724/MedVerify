import os
from celery import Celery
from flask import current_app
from ..database import db
from ..services.verification_service import VerificationService

def make_celery(app):
    celery = Celery(
        app.import_name,
        broker=app.config["CELERY_BROKER_URL"],
        backend=app.config["CELERY_RESULT_BACKEND"]
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

# The celery instance will be attached to the app in __init__.py
# Here we define the tasks

from celery import shared_task

@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def verify_certificate_task(self, filepath, original_filename, user_id, ip_address):
    """
    Background task wrapping VerificationService.verify().
    """
    try:
        try:
            # We need the app context to use the service
            from flask import current_app
            service = VerificationService(
                db.session,
                current_app.config['MODEL_PATH'],
                current_app.config['MODEL_VERSION']
            )
            
            record = service.verify(
                filepath,
                original_filename,
                user_id=user_id,
                ip_address=ip_address
            )
            
            return str(record.id)

        except Exception as exc:
            # If it's a transient error, retry
            try:
                self.retry(exc=exc)
            except Exception:
                # If retries exhausted or non-retryable error
                raise exc
    finally:
        # ALWAYS cleanup temp file
        if os.path.exists(filepath):
            os.remove(filepath)
