"""
Medication Safety API — Module 2

Consumer-facing endpoints for building a personal medication list and running
the Phase-1 safety check over it. Reuses the platform's existing JWT auth and
audit log; it does not introduce a second user system.

Every route is scoped to the calling user's own list. Unlike Module 1, there is
no admin override — a medication list is personal data, and an admin has no
business reading one from these endpoints.
"""

import os
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from .. import limiter
from ..database import db
from ..errors import FileValidationError, NotFoundError, VALIDATION_ERROR, RECORD_NOT_FOUND
from ..repositories.audit_repository import AuditRepository
from ..repositories.medication_repository import MedicationRepository
from ..services.drug_data_service import DrugDataService
from ..services.medication_safety_service import MedicationSafetyService

bp = Blueprint('medications', __name__)

MAX_MEDICATIONS_PER_USER = 50


def _serialise(med) -> dict:
    concept = med.concept
    return {
        "id": str(med.id),
        "display_name": med.display_name,
        "rxcui": med.rxcui,
        "units_per_dose": float(med.units_per_dose or 1),
        "doses_per_day": float(med.doses_per_day or 1),
        "schedule_note": med.schedule_note,
        "entry_source": med.entry_source,
        "notes": med.notes,
        "is_active": med.is_active,
        "created_at": (med.created_at.isoformat() + 'Z') if med.created_at else None,
        "ingredients": [
            {
                "name": i.ingredient_name,
                "key": i.ingredient_key,
                "strength_mg": i.strength_mg,
                "strength_display": (
                    f"{i.strength_amount:g} {i.strength_unit}"
                    if i.strength_amount and i.strength_unit else None
                ),
            }
            for i in (concept.ingredients if concept else [])
        ],
    }


# ---------------------------------------------------------------------------
# Product search
# ---------------------------------------------------------------------------

@bp.get('/search')
@jwt_required()
@limiter.limit("60 per minute")
def search():
    """Autocomplete medication names against RxNorm."""
    term = request.args.get('q', '', type=str)
    limit = min(max(request.args.get('limit', 15, type=int), 1), 30)

    results = DrugDataService(db.session).search_products(term, limit=limit)
    return jsonify({
        "query": term,
        "results": results,
        "source": "RxNorm (US National Library of Medicine)",
    }), 200


@bp.get('/concept/<rxcui>')
@jwt_required()
def concept(rxcui):
    """Ingredient breakdown for one product, so the UI can show what's inside."""
    concept = DrugDataService(db.session).get_concept(rxcui)
    if concept is None:
        raise NotFoundError(RECORD_NOT_FOUND, f"No RxNorm concept found for {rxcui}")

    return jsonify({
        "rxcui": concept.rxcui,
        "name": concept.name,
        "tty": concept.tty,
        "is_branded": concept.is_branded,
        "source": "RxNorm (US National Library of Medicine)",
        "ingredients": [
            {
                "name": i.ingredient_name,
                "key": i.ingredient_key,
                "rxcui": i.ingredient_rxcui,
                "strength_mg": i.strength_mg,
                "strength_display": (
                    f"{i.strength_amount:g} {i.strength_unit}"
                    if i.strength_amount and i.strength_unit else None
                ),
            }
            for i in concept.ingredients
        ],
    }), 200


# ---------------------------------------------------------------------------
# Medication list CRUD
# ---------------------------------------------------------------------------

@bp.get('')
@jwt_required()
def list_medications():
    repo = MedicationRepository(db.session)
    meds = repo.list_for_user(get_jwt_identity())
    return jsonify({
        "medications": [_serialise(m) for m in meds],
        "count": len(meds),
    }), 200


@bp.post('')
@jwt_required()
def add_medication():
    """Add a medication, by RxNorm match or as a free-text entry.

    A free-text entry is accepted deliberately — refusing an unmatched name
    would push people to leave items off their list, and an incomplete list is
    worse for a duplicate check than an unmatched one. It is reported as
    unassessable at check time instead.
    """
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    rxcui = (data.get('rxcui') or '').strip() or None
    display_name = (data.get('display_name') or '').strip()

    if not rxcui and not display_name:
        raise FileValidationError(VALIDATION_ERROR, "Provide either an rxcui or a display_name")

    repo = MedicationRepository(db.session)
    if repo.count_active(user_id) >= MAX_MEDICATIONS_PER_USER:
        raise FileValidationError(
            VALIDATION_ERROR,
            f"A medication list is capped at {MAX_MEDICATIONS_PER_USER} active items",
        )

    units_per_dose = _positive_number(data.get('units_per_dose'), default=1.0, field='units_per_dose')
    doses_per_day = _positive_number(data.get('doses_per_day'), default=1.0, field='doses_per_day')

    entry_source = data.get('entry_source') or ('search' if rxcui else 'manual')
    if entry_source not in ('search', 'manual', 'barcode', 'ocr'):
        raise FileValidationError(VALIDATION_ERROR, f"Unknown entry_source '{entry_source}'")

    resolved_rxcui = None
    if rxcui:
        concept = DrugDataService(db.session).get_concept(rxcui)
        if concept is not None:
            resolved_rxcui = concept.rxcui
            display_name = display_name or concept.name

    med = repo.create(
        user_id,
        rxcui=resolved_rxcui,
        display_name=display_name or rxcui,
        units_per_dose=units_per_dose,
        doses_per_day=doses_per_day,
        schedule_note=(data.get('schedule_note') or None),
        entry_source=entry_source,
        notes=(data.get('notes') or None),
    )
    if med is None:
        raise FileValidationError(VALIDATION_ERROR, "Could not add medication for this user")

    AuditRepository(db.session).log(
        user_id=user_id,
        action='MEDICATION_ADDED',
        resource_type='UserMedication',
        resource_id=med.id,
        ip_address=request.remote_addr,
        details={"rxcui": resolved_rxcui, "entry_source": entry_source,
                 "matched": resolved_rxcui is not None},
    )

    return jsonify(_serialise(med)), 201


@bp.put('/<medication_id>')
@jwt_required()
def update_medication(medication_id):
    user_id = get_jwt_identity()
    repo = MedicationRepository(db.session)
    med = repo.get_for_user(medication_id, user_id)
    if med is None:
        raise NotFoundError(RECORD_NOT_FOUND, "Medication not found on your list")

    data = request.get_json(silent=True) or {}
    updates = {}
    if 'units_per_dose' in data:
        updates['units_per_dose'] = _positive_number(data['units_per_dose'], 1.0, 'units_per_dose')
    if 'doses_per_day' in data:
        updates['doses_per_day'] = _positive_number(data['doses_per_day'], 1.0, 'doses_per_day')
    for field in ('schedule_note', 'notes', 'display_name'):
        if field in data:
            updates[field] = data[field]

    repo.update(med, **updates)
    AuditRepository(db.session).log(
        user_id=user_id, action='MEDICATION_UPDATED',
        resource_type='UserMedication', resource_id=med.id,
        ip_address=request.remote_addr, details={"fields": sorted(updates.keys())},
    )
    return jsonify(_serialise(med)), 200


@bp.delete('/<medication_id>')
@jwt_required()
def remove_medication(medication_id):
    user_id = get_jwt_identity()
    repo = MedicationRepository(db.session)
    med = repo.get_for_user(medication_id, user_id)
    if med is None:
        raise NotFoundError(RECORD_NOT_FOUND, "Medication not found on your list")

    repo.deactivate(med)
    AuditRepository(db.session).log(
        user_id=user_id, action='MEDICATION_REMOVED',
        resource_type='UserMedication', resource_id=med.id,
        ip_address=request.remote_addr, details={"display_name": med.display_name},
    )
    return jsonify({"message": "Removed from your medication list", "id": str(med.id)}), 200


# ---------------------------------------------------------------------------
# Safety check
# ---------------------------------------------------------------------------

@bp.post('/safety-check')
@jwt_required()
@limiter.limit("30 per hour")
def safety_check():
    """Run the Phase-1 rule engine over the caller's active medication list."""
    user_id = get_jwt_identity()
    service = MedicationSafetyService(db.session)
    result = service.run_check(user_id, ip_address=request.remote_addr)
    return jsonify(result), 200


@bp.get('/safety-checks')
@jwt_required()
def list_safety_checks():
    user_id = get_jwt_identity()
    checks = MedicationSafetyService(db.session).list_checks(user_id)
    return jsonify([
        {
            "id": str(c.id),
            "highest_severity": c.highest_severity,
            "severity_summary": c.severity_summary,
            "medication_count": len(c.medication_snapshot or []),
            "finding_count": len(c.findings or []),
            "rule_engine_version": c.rule_engine_version,
            "created_at": (c.created_at.isoformat() + 'Z') if c.created_at else None,
        }
        for c in checks
    ]), 200


@bp.get('/safety-checks/<check_id>')
@jwt_required()
def get_safety_check(check_id):
    user_id = get_jwt_identity()
    check = MedicationSafetyService(db.session).get_check(check_id, user_id)
    if check is None:
        raise NotFoundError(RECORD_NOT_FOUND, "Safety check not found")

    from ..services.medication_safety_service import CONSULT_CAVEAT
    return jsonify({
        "check_id": str(check.id),
        "medications_checked": check.medication_snapshot,
        "findings": check.findings,
        "severity_summary": check.severity_summary,
        "highest_severity": check.highest_severity,
        "sources_used": check.sources_used,
        "rule_engine_version": check.rule_engine_version,
        "processing_time_ms": check.processing_time_ms,
        "disclaimer": CONSULT_CAVEAT,
        "created_at": (check.created_at.isoformat() + 'Z') if check.created_at else None,
    }), 200


# ---------------------------------------------------------------------------
# Scan a package / label photo
# ---------------------------------------------------------------------------

@bp.post('/scan')
@jwt_required()
@limiter.limit("20 per hour")
def scan_package():
    """OCR a photo of packaging and suggest matching RxNorm products.

    Shares Module 1's OCR engine — the same extraction path Phase 3 will run a
    document through for forensics and safety in one pass. Returns *candidates*
    only; the user still confirms which product is theirs, because an OCR guess
    is not a good enough basis for a dose calculation.
    """
    from ..validators.file_validator import FileValidator

    if 'image' not in request.files:
        raise FileValidationError("MISSING_FILE", "No image supplied")
    file = request.files['image']
    if not file.filename:
        raise FileValidationError("EMPTY_FILENAME", "No selected file")

    temp_path = None
    try:
        temp_path = FileValidator.save_temp(file, current_app.config['UPLOAD_FOLDER'])

        try:
            from preprocessing.document_processor import DocumentProcessor
            from utils.ocr_engine import OCREngine
        except ImportError:
            from ...preprocessing.document_processor import DocumentProcessor
            from ...utils.ocr_engine import OCREngine

        processed = DocumentProcessor().preprocess(temp_path)
        text = OCREngine().extract_text(processed) or ""

        candidates = []
        if text.strip():
            drug_data = DrugDataService(db.session)
            seen = set()
            # Package text is noisy; try the longest alphabetic lines first,
            # since brand and ingredient names sit on their own line.
            lines = sorted(
                {ln.strip() for ln in text.splitlines() if len(ln.strip()) >= 4},
                key=len, reverse=True,
            )[:6]
            for line in lines:
                for hit in drug_data.search_products(line, limit=3):
                    if hit['rxcui'] in seen:
                        continue
                    seen.add(hit['rxcui'])
                    candidates.append({**hit, "matched_text": line})
                if len(candidates) >= 8:
                    break

        AuditRepository(db.session).log(
            user_id=get_jwt_identity(), action='MEDICATION_SCAN',
            resource_type='UserMedication', ip_address=request.remote_addr,
            details={"text_length": len(text), "candidate_count": len(candidates)},
        )

        return jsonify({
            "extracted_text": text[:2000],
            "candidates": candidates[:8],
            "note": (
                "These are possible matches read from the photo. Confirm the exact "
                "product and strength against the package before adding it."
                if candidates else
                "No product could be read from this photo. Try better lighting, or "
                "search for the medication by name instead."
            ),
        }), 200
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


# ---------------------------------------------------------------------------

def _positive_number(value, default: float, field: str) -> float:
    if value is None or value == '':
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise FileValidationError(VALIDATION_ERROR, f"'{field}' must be a number")
    if number <= 0 or number > 100:
        raise FileValidationError(VALIDATION_ERROR, f"'{field}' must be between 0 and 100")
    return number
