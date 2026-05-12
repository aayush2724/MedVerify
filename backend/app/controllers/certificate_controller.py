import os
import uuid
import logging
from flask import current_app
from werkzeug.utils import secure_filename
from app.tasks.verification_tasks import verify_certificate_task
from app.errors import PreprocessingError

logger = logging.getLogger(__name__)

class CertificateController:
    @staticmethod
    def handle_upload(file):
        """Handle file saving and task triggering."""
        if not file or not file.filename:
            raise PreprocessingError("No file provided", error_code="MISSING_FILE")

        safe_input_name = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4()}_{safe_input_name}"
        upload_dir = current_app.config["UPLOAD_FOLDER"]
        filepath = os.path.join(upload_dir, unique_name)

        # Basic path traversal protection
        if not os.path.abspath(filepath).startswith(os.path.abspath(upload_dir)):
            raise PreprocessingError("Invalid file path", error_code="INVALID_PATH")

        try:
            file.save(filepath)
        except OSError as exc:
            logger.exception("Failed to save file")
            raise PreprocessingError(f"File system error: {exc}")

        # Trigger Celery Task
        task = verify_certificate_task.delay(filepath, unique_name)
        
        return {
            "task_id": task.id,
            "status": "pending",
            "message": "Verification queued"
        }
