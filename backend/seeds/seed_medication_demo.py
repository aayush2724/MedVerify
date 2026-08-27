"""
Demo seed for Module 2 — Medication Safety Check.

Builds a consumer account whose medication list reproduces the single most
common real-world consumer medication harm: acetaminophen taken knowingly in one
product and unknowingly in a second combination product, pushing the daily total
past the labeled maximum.

Usage:
    MEDVERIFY_DEMO_PASSWORD=... python seeds/seed_medication_demo.py

Re-runnable: the demo user's list is rebuilt from scratch each time.
"""

import os
import sys

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '../..')))

from flask_bcrypt import Bcrypt

from app import create_app
from app.database import db
from app.models import User, UserMedication
from app.services.drug_data_service import DrugDataService

DEMO_EMAIL = os.environ.get("MEDVERIFY_DEMO_EMAIL", "patient@medverify.dev")

# Three products, each at an ordinary label dose, that together cross the
# 4,000 mg acetaminophen ceiling. The point of the demo is that no single line
# looks wrong — the harm only appears once the list is added up, and only one of
# the three products has "acetaminophen" anywhere in the name a patient reads.
DEMO_LIST = [
    # (rxcui, units per dose, doses per day, when)
    ("1738139", 2, 3, "for headaches"),           # acetaminophen 325 MG [Tylenol]  -> 1,950 mg
    ("1092189", 2, 1, "to help me sleep"),        # acetaminophen 500 / diphenhydramine 25 -> 1,000 mg
    ("1049640", 1, 4, "after my surgery"),        # acetaminophen 325 / oxycodone 5 [Percocet] -> 1,300 mg
]                                                 # combined: 4,250 mg vs 4,000 mg labeled max


def seed():
    password = os.environ.get("MEDVERIFY_DEMO_PASSWORD")
    if not password:
        raise RuntimeError(
            "Set MEDVERIFY_DEMO_PASSWORD before seeding the demo patient account."
        )

    app = create_app()
    bcrypt = Bcrypt(app)

    with app.app_context():
        user = User.query.filter_by(email=DEMO_EMAIL).first()
        if user is None:
            user = User(
                email=DEMO_EMAIL,
                password_hash=bcrypt.generate_password_hash(password).decode('utf-8'),
                role='viewer',
                name='Demo Patient',
            )
            db.session.add(user)
            db.session.commit()
            print(f"Created demo patient: {DEMO_EMAIL}")
        else:
            user.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
            db.session.commit()
            print(f"Reusing demo patient: {DEMO_EMAIL}")

        UserMedication.query.filter_by(user_id=user.id).delete()
        db.session.commit()

        drug_data = DrugDataService(db.session)
        for rxcui, units, per_day, note in DEMO_LIST:
            concept = drug_data.get_concept(rxcui)
            if concept is None:
                print(f"  ! Could not resolve RxCUI {rxcui} — skipping "
                      f"(RxNav may be unreachable)")
                continue
            db.session.add(UserMedication(
                user_id=user.id, rxcui=concept.rxcui, display_name=concept.name,
                units_per_dose=units, doses_per_day=per_day,
                schedule_note=note, entry_source='search',
            ))
            ingredients = ", ".join(
                f"{i.ingredient_name} {i.strength_amount:g}{i.strength_unit}"
                for i in concept.ingredients if i.strength_amount
            )
            print(f"  + {concept.name[:60]}")
            print(f"      {units} x {per_day}/day — {ingredients}")

        db.session.commit()
        print(f"\nDemo list ready. Sign in as {DEMO_EMAIL} and open Medication Safety.")


if __name__ == '__main__':
    seed()
