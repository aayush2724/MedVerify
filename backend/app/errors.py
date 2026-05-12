import uuid
from datetime import datetime, timezone
from flask import g, jsonify, request
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, OperationalError
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from werkzeug.exceptions import HTTPException
from flask_limiter.errors import RateLimitExceeded

from .schemas.errors import ErrorResponse
from shared.constants.error_codes import (
    BATCH_LIMIT_EXCEEDED,
    DB_SAVE_FAILED,
    FILE_CORRUPTED,
    FILE_SIZE_EXCEEDED,
    FORBIDDEN,
    INTERNAL_ERROR,
    INVALID_FILE_FORMAT,
    MODEL_INFERENCE_FAILED,
    OCR_EMPTY_RESULT,
    OCR_FAILED,
    PREPROCESSING_FAILED,
    RATE_LIMIT_EXCEEDED,
    RECORD_NOT_FOUND,
    UNAUTHORIZED,
    VALIDATION_ERROR,
)

FILE_TOO_LARGE = FILE_SIZE_EXCEEDED

# Exception Classes
class CertSentinelError(Exception):
    def __init__(self, error_code, message, details=None, status_code=400, retryable=False):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.status_code = status_code
        self.retryable = retryable

class FileValidationError(CertSentinelError):
    def __init__(self, error_code, message, details=None):
        super().__init__(error_code, message, details, status_code=400)

class ProcessingError(CertSentinelError):
    def __init__(self, error_code, message, details=None, retryable=True):
        super().__init__(error_code, message, details, status_code=500, retryable=retryable)

class PreprocessingError(ProcessingError):
    def __init__(self, message, details=None, error_code=PREPROCESSING_FAILED):
        super().__init__(error_code, message, details)

class OCRError(ProcessingError):
    def __init__(self, message, details=None, error_code=OCR_FAILED, retryable=True):
        super().__init__(error_code, message, details, retryable=retryable)

class AnalysisError(ProcessingError):
    def __init__(self, message, details=None, error_code="ANALYSIS_FAILED"):
        super().__init__(error_code, message, details)

class ModelError(ProcessingError):
    def __init__(self, message, details=None, error_code=MODEL_INFERENCE_FAILED):
        super().__init__(error_code, message, details, retryable=False)

class DatabaseError(ProcessingError):
    def __init__(self, message, details=None):
        super().__init__(DB_SAVE_FAILED, message, details)

class AuthError(CertSentinelError):
    def __init__(self, error_code, message, details=None, status_code=401):
        super().__init__(error_code, message, details, status_code)

class NotFoundError(CertSentinelError):
    def __init__(self, error_code, message, details=None):
        super().__init__(error_code, message, details, status_code=404)

# Error Response Builder
def error_response(error_code, message, details=None, status_code=400, request_id=None):
    payload = ErrorResponse(
        error_code=error_code,
        message=message,
        details=details or {},
        timestamp=datetime.now(timezone.utc),
        request_id=request_id or getattr(g, "request_id", None) or str(uuid.uuid4()),
    )
    response = jsonify(payload.model_dump(mode="json"))
    response.status_code = status_code
    return response

# Register Error Handlers
def register_error_handlers(app):
    from . import jwt

    @app.before_request
    def assign_request_id():
        g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    @app.after_request
    def attach_request_id(response):
        response.headers["X-Request-ID"] = getattr(g, "request_id", str(uuid.uuid4()))
        return response

    @app.errorhandler(CertSentinelError)
    def handle_certsentinel_error(e):
        return error_response(e.error_code, e.message, e.details, e.status_code)

    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        return error_response(
            VALIDATION_ERROR,
            "Request validation failed",
            details={"errors": e.errors()},
            status_code=400,
        )

    @app.errorhandler(RateLimitExceeded)
    def handle_rate_limit_error(e):
        response = error_response(
            RATE_LIMIT_EXCEEDED,
            "Too many requests",
            details={"limit": str(e.limit) if e.limit else None},
            status_code=429,
        )
        retry_after = getattr(e, "retry_after", None)
        if retry_after:
            response.headers["Retry-After"] = str(retry_after)
        return response

    @app.errorhandler(400)
    def bad_request(e):
        return error_response(VALIDATION_ERROR, "Bad request", {"error": str(e)}, 400)

    @app.errorhandler(404)
    def not_found(e):
        return error_response(RECORD_NOT_FOUND, "Resource not found", status_code=404)

    @app.errorhandler(405)
    def method_not_allowed(e):
        return error_response("METHOD_NOT_ALLOWED", "Method not allowed", {"error": str(e)}, 405)

    @app.errorhandler(413)
    def request_entity_too_large(e):
        return error_response(FILE_SIZE_EXCEEDED, "File is too large", status_code=413)

    @app.errorhandler(422)
    def unprocessable_entity(e):
        return error_response(VALIDATION_ERROR, "Unprocessable entity", {"error": str(e)}, 422)

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return error_response(RATE_LIMIT_EXCEEDED, "Too many requests", status_code=429)

    @app.errorhandler(500)
    def internal_server_error(e):
        return error_response(INTERNAL_ERROR, "An unexpected error occurred", status_code=500)

    # JWT Errors
    @app.errorhandler(ExpiredSignatureError)
    def handle_expired_token(e):
        return error_response(UNAUTHORIZED, "Token has expired", status_code=401)

    @app.errorhandler(InvalidTokenError)
    def handle_invalid_token(e):
        return error_response(UNAUTHORIZED, "Invalid token", status_code=401)

    # SQLAlchemy Errors
    @app.errorhandler(IntegrityError)
    def handle_integrity_error(e):
        return error_response(DB_SAVE_FAILED, "Database integrity error", status_code=400)

    @app.errorhandler(OperationalError)
    def handle_operational_error(e):
        return error_response(DB_SAVE_FAILED, "Database operational error", status_code=500)

    @jwt.unauthorized_loader
    def handle_missing_jwt(reason):
        return error_response(UNAUTHORIZED, reason, status_code=401)

    @jwt.invalid_token_loader
    def handle_invalid_jwt(reason):
        return error_response(UNAUTHORIZED, reason, status_code=401)

    @jwt.expired_token_loader
    def handle_expired_jwt(jwt_header, jwt_payload):
        return error_response(UNAUTHORIZED, "Token has expired", status_code=401)

    @app.errorhandler(Exception)
    def handle_unexpected_error(e):
        if isinstance(e, HTTPException):
            return error_response(
                getattr(e, "name", "HTTP_ERROR").upper().replace(" ", "_"),
                getattr(e, "description", str(e)),
                status_code=getattr(e, "code", 500) or 500,
            )
        app.logger.exception("Unhandled request failure")
        return error_response(INTERNAL_ERROR, "An unexpected error occurred", status_code=500)
