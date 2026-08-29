"""
Combined Pipeline API — Module 2, Phase 3

One upload, both modules: the document is checked for tampering *and* the
medications printed on it are checked for duplicates, cumulative dose and
label-documented interactions.

Scoping matches the module each half belongs to. Module 1 lets an admin read
any verification record; Module 2 never lets anyone read another person's
medication data. A combined report contains both, so the stricter rule wins —
these endpoints are caller-scoped with no admin override.
"""

import os
import uuid

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from .. import limiter
from ..database import db
from ..errors import FileValidationError, NotFoundError, RECORD_NOT_FOUND
from ..models import SafetyCheck, VerificationRecord
from ..services.medication_safety_service import CONSULT_CAVEAT
from ..services.prescription_pipeline_service import PrescriptionPipelineService
from ..timefmt import iso_utc
from ..validators.file_validator import FileValidator
from .certificates import get_verification_service

bp = Blueprint('pipeline', __name__)


def _as_uuid(value):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


@bp.post('/analyse')
@jwt_required()
@limiter.limit("20 per hour")
def analyse():
    """Verify a prescription and check the medications written on it.

    The upload is kept on disk when the run succeeds so the report can show the
    source document later — the same retention rule the certificate
    verification route uses.
    """
    if 'document' not in request.files:
        raise FileValidationError("MISSING_FILE", "No document supplied")

    file = request.files['document']
    if not file.filename:
        raise FileValidationError("EMPTY_FILENAME", "No selected file")

    temp_path, success = None, False
    try:
        temp_path = FileValidator.save_temp(file, current_app.config['UPLOAD_FOLDER'])
        service = PrescriptionPipelineService(db.session, get_verification_service())
        result = service.analyse(
            temp_path,
            file.filename,
            user_id=get_jwt_identity(),
            ip_address=request.remote_addr,
        )
        success = True
        return jsonify(result), 200
    finally:
        if not success and temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@bp.get('/<record_id>')
@jwt_required()
def get_combined_report(record_id):
    """Re-read a stored combined report by its verification record id.

    Both halves are re-read from their own tables rather than from a cached
    copy, so a report opened months later shows the same data that was audited.
    """
    record_uuid, user_uuid = _as_uuid(record_id), _as_uuid(get_jwt_identity())
    if record_uuid is None or user_uuid is None:
        raise NotFoundError(RECORD_NOT_FOUND, "No combined report found for this document")

    check = (
        db.session.query(SafetyCheck)
        .filter_by(verification_record_id=record_uuid, user_id=user_uuid)
        .order_by(SafetyCheck.created_at.desc())
        .first()
    )
    if check is None:
        raise NotFoundError(RECORD_NOT_FOUND, "No combined report found for this document")

    record = db.session.get(VerificationRecord, check.verification_record_id)
    if record is None:
        raise NotFoundError(
            RECORD_NOT_FOUND, "The source document for this report is no longer on file"
        )

    return jsonify({
        "pipeline_version": check.rule_engine_version,
        "document": {
            "record_id": str(record.id),
            "original_filename": record.original_filename,
            "status": record.status,
            "verdict_label": (
                "Likely Genuine" if record.status == 'GENUINE' else "Suspicious/Fake"
            ),
            "confidence_score": record.confidence,
            "reasons": record.reasons,
            "extracted_info": record.extracted_fields,
            "text_score": record.text_score,
            "image_score": record.image_score,
            "submitted_at": iso_utc(record.submitted_at),
        },
        "medications_detected": check.medication_snapshot,
        "safety": {
            "check_id": str(check.id),
            "source": check.source,
            "medications_checked": check.medication_snapshot,
            "findings": check.findings,
            "severity_summary": check.severity_summary,
            "highest_severity": check.highest_severity,
            "sources_used": check.sources_used,
            "rule_engine_version": check.rule_engine_version,
            "processing_time_ms": check.processing_time_ms,
            "disclaimer": CONSULT_CAVEAT,
            "created_at": iso_utc(check.created_at),
        },
        "reading_caveat": (
            "The medications in this report were read from the document by OCR and "
            "were not confirmed by hand. Check them against the original before "
            "relying on the findings."
        ),
    }), 200
