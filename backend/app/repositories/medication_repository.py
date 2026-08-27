"""Persistence for a user's medication list (Module 2).

Follows the same shape as `VerificationRepository`: UUID coercion at the
boundary, user-scoped reads so one account can never see another's list.
"""

import uuid
from typing import List, Optional

from ..database import db
from ..models import UserMedication


class MedicationRepository:
    def __init__(self, db_session=None):
        self.session = db_session or db.session

    @staticmethod
    def _uuid(value) -> Optional[uuid.UUID]:
        try:
            return uuid.UUID(str(value))
        except (ValueError, TypeError, AttributeError):
            return None

    def list_for_user(self, user_id, include_inactive: bool = False) -> List[UserMedication]:
        user_uuid = self._uuid(user_id)
        if user_uuid is None:
            return []
        query = self.session.query(UserMedication).filter_by(user_id=user_uuid)
        if not include_inactive:
            query = query.filter_by(is_active=True)
        return query.order_by(UserMedication.created_at.asc()).all()

    def get_for_user(self, medication_id, user_id) -> Optional[UserMedication]:
        med_uuid, user_uuid = self._uuid(medication_id), self._uuid(user_id)
        if med_uuid is None or user_uuid is None:
            return None
        return (
            self.session.query(UserMedication)
            .filter_by(id=med_uuid, user_id=user_uuid)
            .first()
        )

    def create(self, user_id, **fields) -> Optional[UserMedication]:
        user_uuid = self._uuid(user_id)
        if user_uuid is None:
            return None
        med = UserMedication(user_id=user_uuid, **fields)
        self.session.add(med)
        self.session.commit()
        return med

    def update(self, medication: UserMedication, **fields) -> UserMedication:
        for key, value in fields.items():
            if value is not None and hasattr(medication, key):
                setattr(medication, key, value)
        self.session.commit()
        return medication

    def deactivate(self, medication: UserMedication) -> UserMedication:
        """Soft-delete.

        Kept rather than hard-deleted so an earlier `SafetyCheck` that cited
        this entry still resolves when someone re-opens that result.
        """
        medication.is_active = False
        self.session.commit()
        return medication

    def count_active(self, user_id) -> int:
        user_uuid = self._uuid(user_id)
        if user_uuid is None:
            return 0
        return (
            self.session.query(UserMedication)
            .filter_by(user_id=user_uuid, is_active=True)
            .count()
        )
