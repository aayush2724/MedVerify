import os
from flask import Blueprint, request, jsonify, current_app, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from ..database import db
from ..timefmt import iso_utc
from ..validators.file_validator import FileValidator
from ..services.verification_service import VerificationService
from ..repositories.audit_repository import AuditRepository
from ..errors import FileValidationError, RECORD_NOT_FOUND, UNAUTHORIZED

bp = Blueprint('certificates', __name__)

def _is_admin():
    return get_jwt().get('role') == 'admin'

def _record_scope_user_id():
    return None if _is_admin() else get_jwt_identity()

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
    success = False
    try:
        temp_path = FileValidator.save_temp(file, current_app.config['UPLOAD_FOLDER'])
        service = get_verification_service()
        record = service.verify(
            temp_path, 
            file.filename, 
            user_id=user_id, 
            ip_address=ip_address
        )
        success = True
        
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
        if not success and temp_path and os.path.exists(temp_path):
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
    page = max(1, request.args.get('page', 1, type=int))
    limit = min(max(1, request.args.get('limit', 20, type=int)), 100)
    service = get_verification_service()
    records = service.list_records(
        user_id=_record_scope_user_id(),
        limit=limit,
        offset=(page-1)*limit
    )
    return jsonify([{"id": str(r.id), "filename": r.original_filename, "status": r.status, "submitted_at": iso_utc(r.submitted_at)} for r in records]), 200

@bp.route('/<record_id>', methods=['GET'])
@jwt_required()
def get_record(record_id):
    service = get_verification_service()
    record = service.get_record(record_id, user_id=_record_scope_user_id())
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

@bp.route('/<record_id>/file', methods=['GET'])
def get_certificate_file(record_id):
    # Authenticate via header or query string token to support native browser tags
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    else:
        token = request.args.get("token")
        
    if not token:
        from ..errors import AuthError, UNAUTHORIZED
        raise AuthError(UNAUTHORIZED, "Missing authorization token")
        
    from flask_jwt_extended import decode_token
    from .auth import is_token_revoked
    try:
        decoded_token = decode_token(token)
    except Exception as e:
        from ..errors import AuthError, UNAUTHORIZED
        raise AuthError(UNAUTHORIZED, f"Invalid or expired token: {str(e)}")

    if is_token_revoked(decoded_token):
        from ..errors import AuthError, UNAUTHORIZED
        raise AuthError(UNAUTHORIZED, "Token has been revoked")
        
    service = get_verification_service()
    user_id = decoded_token.get("sub")
    is_admin = decoded_token.get("role") == "admin"
    record = service.get_record(record_id, user_id=None if is_admin else user_id)
    
    upload_dir = current_app.config['UPLOAD_FOLDER']
    file_path = os.path.join(upload_dir, record.filename)
    
    if not os.path.exists(file_path):
        # Generate a premium dynamic placeholder card matching the requested format if file isn't on disk (seeded data)
        ext = record.original_filename.rsplit('.', 1)[1].lower() if '.' in record.original_filename else ''
        file_ext = 'pdf' if ext == 'pdf' else 'png'
        
        placeholder_path = os.path.join(upload_dir, f"placeholder_{record_id}.{file_ext}")
        if not os.path.exists(placeholder_path):
            from PIL import Image, ImageDraw, ImageFont
            # Create a premium high-resolution certificate card
            img = Image.new('RGB', (1000, 700), color='#ffffff')
            d = ImageDraw.Draw(img)
            
            # Draw sophisticated background gradients or frames
            d.rectangle([(20, 20), (980, 680)], outline='#7c5cbf', width=6)
            d.rectangle([(35, 35), (965, 665)], outline='#e8e0f0', width=2)
            
            # Header
            d.text((100, 80), "MEDVERIFY SECURE LEDGER", fill='#7c5cbf')
            d.text((100, 110), "Digital Cryptographic Audit Evidence", fill='#938f99')
            
            # Body metadata
            d.text((100, 220), "DOCUMENT INFORMATION", fill='#7c5cbf')
            d.text((100, 260), f"File Name: {record.original_filename}", fill='#1c1b1f')
            d.text((100, 300), f"Record Reference: {record.id}", fill='#1c1b1f')
            d.text((100, 340), f"Audit Timestamp: {record.submitted_at.isoformat() if record.submitted_at else 'N/A'}", fill='#1c1b1f')
            
            # Verdict Badge
            status_colors = {'GENUINE': '#15803d', 'SUSPICIOUS': '#b45309', 'FAKE': '#b91c1c'}
            color = status_colors.get(record.status, '#7c5cbf')
            d.rectangle([(100, 420), (450, 480)], fill=color)
            d.text((120, 435), f"STATUS: {record.status}", fill='#ffffff')
            
            # Confidence Scoring match
            conf = int((record.confidence or 0) * 100)
            d.text((100, 520), f"Authenticity Index Match: {conf}% Confidence", fill='#1c1b1f')
            d.text((100, 560), "Authorized by MedVerify Automated Classifier", fill='#938f99')
            
            if file_ext == 'pdf':
                img.save(placeholder_path, "PDF")
            else:
                img.save(placeholder_path, "PNG")
        file_path = placeholder_path

    # Extract format
    ext = record.original_filename.rsplit('.', 1)[1].lower() if '.' in record.original_filename else ''
    ext_to_mime = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'pdf': 'application/pdf'}
    mime_type = ext_to_mime.get(ext, 'application/octet-stream')
    
    return send_file(file_path, mimetype=mime_type)


@bp.route('/stats', methods=['GET'])
@jwt_required()
def get_stats():
    service = get_verification_service()
    return jsonify(service.get_dashboard_stats(user_id=_record_scope_user_id())), 200

@bp.route('/<record_id>/export', methods=['GET'])
@jwt_required()
def export_record(record_id):
    service = get_verification_service()
    record = service.get_record(record_id, user_id=_record_scope_user_id())
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
        "submitted_at": iso_utc(record.submitted_at),
    }), 200
