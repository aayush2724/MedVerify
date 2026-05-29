import os
from flask import Blueprint, request, jsonify, current_app, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from ..database import db
from ..validators.file_validator import FileValidator
from ..services.verification_service import VerificationService
from ..repositories.audit_repository import AuditRepository
from ..errors import FileValidationError, RECORD_NOT_FOUND, UNAUTHORIZED

bp = Blueprint('certificates', __name__)

def get_verification_service():
    return VerificationService(
        db.session, 
        current_app.config['MODEL_PATH'],
        current_app.config['MODEL_VERSION']
    )

@bp.route('/verify', methods=['POST'])
@jwt_required()
def verify():
    if 'certificate' not in request.files:
        raise FileValidationError("MISSING_FILE", "No file part in the request")
        
    file = request.files['certificate']
    if file.filename == '':
        raise FileValidationError("EMPTY_FILENAME", "No selected file")

    user_id = get_jwt_identity()
    ip_address = request.remote_addr
    
    temp_path = None
    try:
        temp_path = FileValidator.save_temp(file, current_app.config['UPLOAD_FOLDER'])
        service = get_verification_service()
        record = service.verify(
            temp_path, 
            file.filename, 
            user_id=user_id, 
            ip_address=ip_address
        )
        
        response = {
            "record_id": str(record.id),
            "status": record.status,
            "confidence_score": record.confidence,
            "verdict_label": "Likely Genuine" if record.status == 'GENUINE' else "Suspicious/Fake",
            "reasons": record.reasons,
            "extracted_info": record.extracted_fields,
            "image_forensics": {
                "text_score": record.text_score,
                "image_score": record.image_score,
                "ml_features": record.ml_features
            },
            "processing_time_ms": record.processing_time_ms,
            "warnings": None
        }
        
        return jsonify(response), 200
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

@bp.route('/verify-async', methods=['POST'])
@jwt_required()
def verify_async():
    if 'certificate' not in request.files:
        raise FileValidationError("MISSING_FILE", "No file part in the request")
        
    file = request.files['certificate']
    if file.filename == '':
        raise FileValidationError("EMPTY_FILENAME", "No selected file")

    user_id = get_jwt_identity()
    ip_address = request.remote_addr
    
    temp_path = FileValidator.save_temp(file, current_app.config['UPLOAD_FOLDER'])
    
    from ..tasks.verification_tasks import verify_certificate_task
    task = verify_certificate_task.delay(
        temp_path, 
        file.filename, 
        user_id=user_id, 
        ip_address=ip_address
    )
    
    return jsonify({
        "task_id": task.id,
        "status": "QUEUED"
    }), 202

@bp.route('/verify-async/<task_id>/status', methods=['GET'])
@jwt_required()
def get_task_status(task_id):
    from celery.result import AsyncResult
    celery_app = current_app.extensions.get('celery')
    if not celery_app:
        return jsonify({"error": "Celery not initialized"}), 500
        
    result = AsyncResult(task_id, app=celery_app)
    
    if result.state == 'PENDING':
        response = {"status": "QUEUED"}
    elif result.state == 'STARTED':
        response = {"status": "PROCESSING"}
    elif result.state == 'SUCCESS':
        response = {"status": "DONE", "record_id": result.result}
    elif result.state == 'FAILURE':
        response = {"status": "ERROR", "error": str(result.info)}
    else:
        response = {"status": result.state}
        
    return jsonify(response), 200

@bp.route('', methods=['GET'])
@jwt_required()
def list_records():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    service = get_verification_service()
    records = service.list_records(
        user_id=None,
        limit=limit,
        offset=(page-1)*limit
    )
    return jsonify([{"id": str(r.id), "filename": r.original_filename, "status": r.status, "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None} for r in records]), 200

@bp.route('/<record_id>', methods=['GET'])
@jwt_required()
def get_record(record_id):
    claims = get_jwt()
    is_admin = claims.get('role') == 'admin'
    user_id = get_jwt_identity()
    current_app.logger.info(f"DIAGNOSTIC: get_record ID: {record_id}, role: {claims.get('role')}, is_admin: {is_admin}, user_id: {user_id}")
    service = get_verification_service()
    record = service.get_record(record_id, user_id=None)
    return jsonify({
        "id": str(record.id),
        "status": record.status,
        "confidence_score": record.confidence,
        "reasons": record.reasons,
        "extracted_info": record.extracted_fields,
        "image_forensics": {
            "text_score": record.text_score,
            "image_score": record.image_score,
            "ml_features": record.ml_features,
        },
        "processing_time_ms": record.processing_time_ms,
        "model_version": record.model_version,
        "filename": record.original_filename,
    }), 200

@bp.route('/stats', methods=['GET'])
@jwt_required()
def get_stats():
    service = get_verification_service()
    return jsonify(service.get_dashboard_stats()), 200

@bp.route('/<record_id>/export', methods=['GET'])
@jwt_required()
def export_record(record_id):
    service = get_verification_service()
    record = service.get_record(record_id, user_id=None)
    return jsonify({
        "report_id": str(record.id),
        "status": record.status,
        "confidence_score": record.confidence,
        "verdict_label": "Likely Genuine" if record.status == "GENUINE" else "Suspicious/Fake",
        "reasons": record.reasons,
        "extracted_info": record.extracted_fields,
        "image_forensics": {
            "text_score": record.text_score,
            "image_score": record.image_score,
            "ela_score": record.ml_features.get("ela_score") if record.ml_features else None,
            "noise_inconsistency_score": record.ml_features.get("noise_inconsistency_score") if record.ml_features else None,
            "copy_move_detected": record.ml_features.get("copy_move_detected") if record.ml_features else None,
            "font_consistency_score": record.ml_features.get("font_consistency_score") if record.ml_features else None,
        },
        "processing_time_ms": record.processing_time_ms,
        "model_version": record.model_version,
        "filename": record.original_filename,
        "submitted_at": record.submitted_at.isoformat() if record.submitted_at else None,
    }), 200
