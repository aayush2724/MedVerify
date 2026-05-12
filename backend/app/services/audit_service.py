import logging
from app.errors import DatabaseError

logger = logging.getLogger(__name__)

class AuditService:
    def __init__(self, db):
        self.db = db

    def log_verification(self, filename, extracted_text, result):
        try:
            record_id = self.db.save_result(filename, extracted_text, result)
            return record_id
        except Exception as exc:
            logger.exception("Audit logging failed")
            raise DatabaseError(f"Failed to persist audit trail: {exc}")

    def get_history(self, limit=100):
        return self.db.get_all_records(limit=limit)

    def get_details(self, record_id):
        return self.db.get_record(record_id)
