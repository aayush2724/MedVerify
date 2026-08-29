import uuid
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func
from .database import db

JSONType = db.JSON().with_variant(postgresql.JSONB, "postgresql")

class User(db.Model):
    __tablename__ = 'users'
    __table_args__ = (
        db.Index('ix_users_email', 'email'),
        db.Index('ix_users_role', 'role'),
    )
    
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('admin', 'verifier', 'viewer', name='user_roles'), nullable=False, default='viewer')
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    last_login = db.Column(db.DateTime(timezone=True), nullable=True)
    name = db.Column(db.String(255), nullable=True)
    avatar = db.Column(db.String(500), nullable=True)

    def __repr__(self):
        return f'<User {self.email}>'

class Permission(db.Model):
    __tablename__ = 'permissions'
    
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<Permission {self.name}>'

class UserPermission(db.Model):
    __tablename__ = 'user_permissions'
    
    user_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    permission_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True)
    granted_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

class VerificationRecord(db.Model):
    __tablename__ = 'verification_records'
    __table_args__ = (
        db.CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_verification_confidence_range"),
        db.CheckConstraint("processing_time_ms IS NULL OR processing_time_ms >= 0", name="ck_verification_processing_time_nonnegative"),
        db.Index('ix_verification_records_submitted_at', 'submitted_at'),
        db.Index('ix_verification_records_status', 'status'),
        db.Index('ix_verification_records_user_id', 'user_id'),
        db.Index('ix_verification_records_user_status', 'user_id', 'status'),
    )
    
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    extracted_text = db.Column(db.Text, nullable=True) # Max 5000 chars logic can be enforced in application layer or via check constraint
    status = db.Column(db.Enum('GENUINE', 'SUSPICIOUS', 'FAKE', 'PENDING', 'ERROR', name='verification_status'), nullable=False, default='PENDING')
    confidence = db.Column(db.Float, nullable=True)
    confidence_threshold_used = db.Column(db.Float, nullable=True)
    reasons = db.Column(JSONType, nullable=True) # Array of strings
    extracted_fields = db.Column(JSONType, nullable=True) # Doctor name, hospital, etc.
    text_score = db.Column(db.Float, nullable=True)
    image_score = db.Column(db.Float, nullable=True)
    ml_features = db.Column(JSONType, nullable=True) # Full feature vector
    feature_extraction_metadata = db.Column(JSONType, nullable=True)
    model_version = db.Column(db.String(50), nullable=True)
    processing_time_ms = db.Column(db.Integer, nullable=True)
    submitted_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f'<VerificationRecord {self.id} - {self.status}>'

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    __table_args__ = (
        db.Index('ix_audit_logs_created_at', 'created_at'),
        db.Index('ix_audit_logs_user_id', 'user_id'),
        db.Index('ix_audit_logs_resource', 'resource_type', 'resource_id'),
    )
    
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(100), nullable=False) # e.g. 'UPLOAD', 'VERIFY'
    resource_type = db.Column(db.String(50), nullable=True)
    resource_id = db.Column(db.UUID(as_uuid=True), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    confidence_threshold_used = db.Column(db.Float, nullable=True)
    model_version = db.Column(db.String(50), nullable=True)
    details = db.Column(JSONType, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f'<AuditLog {self.action} by {self.user_id}>'

class BatchJob(db.Model):
    __tablename__ = 'batch_jobs'
    __table_args__ = (
        db.CheckConstraint("total_files >= 0", name="ck_batch_jobs_total_files_nonnegative"),
        db.CheckConstraint("processed_files >= 0", name="ck_batch_jobs_processed_files_nonnegative"),
        db.CheckConstraint("processed_files <= total_files", name="ck_batch_jobs_progress_bounds"),
        db.Index('ix_batch_jobs_created_at', 'created_at'),
        db.Index('ix_batch_jobs_status', 'status'),
        db.Index('ix_batch_jobs_user_id', 'user_id'),
    )
    
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.Enum('QUEUED', 'PROCESSING', 'DONE', 'FAILED', name='batch_status'), nullable=False, default='QUEUED')
    total_files = db.Column(db.Integer, nullable=False, default=0)
    processed_files = db.Column(db.Integer, nullable=False, default=0)
    results = db.Column(JSONType, nullable=True) # List of {filename, record_id, status}
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f'<BatchJob {self.id} - {self.status}>'


# ---------------------------------------------------------------------------
# Module 2 — Medication Safety Check
#
# Consumer-facing, informational-only. Every safety finding produced from these
# tables must carry a citation back to a public data source (RxNorm / openFDA /
# DailyMed) plus a consult-a-professional caveat. No table here stores a
# clinical verdict — only observed facts and the sourced rule that fired.
# ---------------------------------------------------------------------------

class DrugConcept(db.Model):
    """Cached RxNorm concept (a product the user can add to their list).

    Populated from RxNav so autocomplete and ingredient breakdown never hit the
    network on the hot path.
    """
    __tablename__ = 'drug_concepts'
    __table_args__ = (
        db.Index('ix_drug_concepts_name', 'name'),
        db.Index('ix_drug_concepts_refreshed_at', 'refreshed_at'),
    )

    rxcui = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(500), nullable=False)
    tty = db.Column(db.String(20), nullable=True)          # SBD, SCD, BPCK, IN...
    synonym = db.Column(db.String(500), nullable=True)
    is_branded = db.Column(db.Boolean, nullable=False, default=False)
    payload = db.Column(JSONType, nullable=True)           # raw RxNav response
    source = db.Column(db.String(50), nullable=False, default='RxNorm')
    refreshed_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    ingredients = db.relationship(
        'DrugIngredient', back_populates='concept',
        cascade='all, delete-orphan', lazy='selectin',
    )

    def __repr__(self):
        return f'<DrugConcept {self.rxcui} {self.name[:40]}>'


class DrugIngredient(db.Model):
    """One active ingredient of a cached product, with its per-unit strength.

    Strength comes from the RxNorm SCDC concept (e.g. "acetaminophen 325 MG"),
    normalised to milligrams where the unit allows it.
    """
    __tablename__ = 'drug_ingredients'
    __table_args__ = (
        db.UniqueConstraint('rxcui', 'ingredient_rxcui', name='uq_drug_ingredient_pair'),
        db.Index('ix_drug_ingredients_ingredient_key', 'ingredient_key'),
    )

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rxcui = db.Column(db.String(20), db.ForeignKey('drug_concepts.rxcui', ondelete='CASCADE'), nullable=False)
    ingredient_rxcui = db.Column(db.String(20), nullable=True)
    ingredient_name = db.Column(db.String(255), nullable=False)
    ingredient_key = db.Column(db.String(255), nullable=False)   # lower-cased match key
    strength_amount = db.Column(db.Float, nullable=True)
    strength_unit = db.Column(db.String(20), nullable=True)
    strength_mg = db.Column(db.Float, nullable=True)             # normalised, None if not mass-based
    source = db.Column(db.String(50), nullable=False, default='RxNorm')

    concept = db.relationship('DrugConcept', back_populates='ingredients')

    def __repr__(self):
        return f'<DrugIngredient {self.ingredient_name} {self.strength_mg}mg>'


class IngredientLimit(db.Model):
    """Labeled maximum daily dose for a single active ingredient.

    Deliberately a curated, human-auditable table rather than a model
    prediction — the spec forbids an ML-derived safety verdict. Each row cites
    the label or monograph it came from so a finding can be traced after the
    fact. `label_excerpt` holds verbatim text pulled from the openFDA label.
    """
    __tablename__ = 'ingredient_limits'
    __table_args__ = (
        db.CheckConstraint('max_daily_mg IS NULL OR max_daily_mg > 0', name='ck_ingredient_limit_positive'),
        db.Index('ix_ingredient_limits_key', 'ingredient_key'),
    )

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ingredient_key = db.Column(db.String(255), unique=True, nullable=False)
    ingredient_name = db.Column(db.String(255), nullable=False)
    max_daily_mg = db.Column(db.Float, nullable=True)
    audience = db.Column(db.String(50), nullable=False, default='adult')   # adult | adolescent | child
    source_name = db.Column(db.String(255), nullable=False)                # e.g. "FDA OTC Monograph"
    source_url = db.Column(db.String(500), nullable=True)
    source_label_id = db.Column(db.String(100), nullable=True)             # openFDA/DailyMed set id
    label_excerpt = db.Column(db.Text, nullable=True)
    caution_note = db.Column(db.Text, nullable=True)
    refreshed_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    def citation(self) -> dict:
        return {
            "source": self.source_name,
            "url": self.source_url,
            "label_id": self.source_label_id,
            "excerpt": self.label_excerpt,
            "retrieved_at": self.refreshed_at.isoformat() if self.refreshed_at else None,
        }

    def __repr__(self):
        return f'<IngredientLimit {self.ingredient_name} max={self.max_daily_mg}mg>'


class UserMedication(db.Model):
    """An entry on one user's personal medication list."""
    __tablename__ = 'user_medications'
    __table_args__ = (
        db.CheckConstraint('doses_per_day IS NULL OR doses_per_day > 0', name='ck_user_med_doses_positive'),
        db.CheckConstraint('units_per_dose IS NULL OR units_per_dose > 0', name='ck_user_med_units_positive'),
        db.Index('ix_user_medications_user_active', 'user_id', 'is_active'),
    )

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    rxcui = db.Column(db.String(20), db.ForeignKey('drug_concepts.rxcui', ondelete='SET NULL'), nullable=True)
    display_name = db.Column(db.String(500), nullable=False)
    units_per_dose = db.Column(db.Float, nullable=False, default=1.0)     # tablets/capsules per dose
    doses_per_day = db.Column(db.Float, nullable=False, default=1.0)
    schedule_note = db.Column(db.String(255), nullable=True)              # "as needed", "morning"...
    entry_source = db.Column(
        db.Enum('search', 'manual', 'barcode', 'ocr', name='medication_entry_source'),
        nullable=False, default='search',
    )
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    concept = db.relationship('DrugConcept', lazy='selectin')

    def __repr__(self):
        return f'<UserMedication {self.display_name} x{self.doses_per_day}/day>'


class SafetyCheck(db.Model):
    """A persisted run of the medication-safety rule engine.

    Stored so a result stays explainable after the fact: the exact medication
    snapshot, the findings, and the data sources each finding cited.
    """
    __tablename__ = 'safety_checks'
    __table_args__ = (
        db.Index('ix_safety_checks_user_created', 'user_id', 'created_at'),
        db.Index('ix_safety_checks_verification_record', 'verification_record_id'),
    )

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # Where the checked list came from. 'list' is the user's own curated list;
    # 'prescription' is a list read off a document by OCR and never confirmed
    # by hand. The two carry very different confidence and must stay
    # distinguishable long after the check was run.
    source = db.Column(
        db.Enum('list', 'prescription', name='safety_check_source'),
        nullable=False, default='list', server_default='list',
    )
    # Set when this check was produced by the Phase 3 combined pipeline, so a
    # report can show the forensics verdict and the safety findings for one
    # document side by side. SET NULL on delete: losing the certificate must
    # not silently delete the safety history attached to it.
    verification_record_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey('verification_records.id', ondelete='SET NULL'),
        nullable=True,
    )

    medication_snapshot = db.Column(JSONType, nullable=False)   # what was checked, verbatim
    findings = db.Column(JSONType, nullable=False)              # list of sourced findings
    severity_summary = db.Column(JSONType, nullable=True)       # {"high": 1, "moderate": 0, ...}
    highest_severity = db.Column(
        db.Enum('none', 'info', 'moderate', 'high', name='safety_severity'),
        nullable=False, default='none',
    )
    sources_used = db.Column(JSONType, nullable=True)           # citations, for the audit trail
    rule_engine_version = db.Column(db.String(50), nullable=False, default='rules-v1')
    processing_time_ms = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f'<SafetyCheck {self.id} {self.highest_severity}>'


class ExternalApiCache(db.Model):
    """Generic response cache for RxNav / openFDA calls.

    Keyed by "<provider>:<request signature>" so every outbound lookup is
    de-duplicated across users and the platform degrades to cached data if an
    upstream API is unreachable.
    """
    __tablename__ = 'external_api_cache'
    __table_args__ = (
        db.Index('ix_external_api_cache_fetched_at', 'fetched_at'),
    )

    cache_key = db.Column(db.String(500), primary_key=True)
    provider = db.Column(db.String(50), nullable=False)
    payload = db.Column(JSONType, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='OK')   # OK | EMPTY | ERROR
    fetched_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f'<ExternalApiCache {self.cache_key[:60]}>'
