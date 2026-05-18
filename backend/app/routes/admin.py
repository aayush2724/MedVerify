from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, jwt_required
from sqlalchemy import func

from ..database import db
from ..models import AuditLog, VerificationRecord
from .. import settings as runtime_settings

bp = Blueprint("admin", __name__)


def require_admin():
    claims = get_jwt()
    if claims.get("role") != "admin":
        from ..errors import AuthError, FORBIDDEN

        raise AuthError(FORBIDDEN, "Admin privileges are required", status_code=403)


@bp.get("/audit-logs")
@jwt_required()
def audit_logs():
    require_admin()
    limit = min(request.args.get("limit", 100, type=int), 500)
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return jsonify([
        {
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": str(log.resource_id) if log.resource_id else None,
            "ip_address": log.ip_address,
            "confidence_threshold_used": log.confidence_threshold_used,
            "model_version": log.model_version,
            "details": log.details or {},
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ])


@bp.get("/records")
@jwt_required()
def records():
    require_admin()
    limit = min(request.args.get("limit", 100, type=int), 500)
    rows = VerificationRecord.query.order_by(VerificationRecord.submitted_at.desc()).limit(limit).all()
    return jsonify([
        {
            "id": str(row.id),
            "user_id": str(row.user_id) if row.user_id else None,
            "filename": row.original_filename,
            "status": row.status,
            "confidence": row.confidence,
            "confidence_threshold_used": row.confidence_threshold_used,
            "model_version": row.model_version,
            "processing_time_ms": row.processing_time_ms,
            "submitted_at": row.submitted_at.isoformat(),
        }
        for row in rows
    ])


@bp.get("/stats")
@jwt_required()
def stats():
    require_admin()
    total = db.session.query(func.count(VerificationRecord.id)).scalar()
    by_status = {
        status: db.session.query(func.count(VerificationRecord.id)).filter_by(status=status).scalar()
        for status in ("GENUINE", "SUSPICIOUS", "FAKE", "ERROR", "PENDING")
    }
    return jsonify({"total_verifications": total, "by_status": by_status})


@bp.get("/thresholds")
@jwt_required()
def get_thresholds():
    require_admin()
    thresholds = runtime_settings.get_thresholds()
    return jsonify({
        "genuine": thresholds["genuine"],
        "suspicious": thresholds["suspicious"],
        "description": {
            "genuine": f"Confidence >= {thresholds['genuine']} → GENUINE",
            "suspicious": f"Confidence >= {thresholds['suspicious']} → SUSPICIOUS, else FAKE",
        }
    })


@bp.put("/thresholds")
@jwt_required()
def update_thresholds():
    require_admin()
    data = request.get_json(silent=True) or {}
    genuine = data.get("genuine")
    suspicious = data.get("suspicious")

    if genuine is None or suspicious is None:
        from ..errors import FileValidationError, VALIDATION_ERROR
        raise FileValidationError(VALIDATION_ERROR, "Both 'genuine' and 'suspicious' thresholds are required")

    try:
        genuine = float(genuine)
        suspicious = float(suspicious)
    except (TypeError, ValueError):
        from ..errors import FileValidationError, VALIDATION_ERROR
        raise FileValidationError(VALIDATION_ERROR, "Thresholds must be numbers between 0 and 1")

    if not (0 < suspicious < genuine <= 1):
        from ..errors import FileValidationError, VALIDATION_ERROR
        raise FileValidationError(
            VALIDATION_ERROR,
            "Thresholds must satisfy: 0 < suspicious < genuine ≤ 1"
        )

    updated = runtime_settings.set_thresholds(genuine, suspicious)

    from ml.classifier import CertificateClassifier
    if CertificateClassifier._instance is not None:
        CertificateClassifier._instance.thresholds = updated

    return jsonify({
        "genuine": updated["genuine"],
        "suspicious": updated["suspicious"],
        "message": "Thresholds updated successfully"
    })
