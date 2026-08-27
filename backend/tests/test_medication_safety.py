"""
Module 2 — Medication Safety Check tests.

The rule engine is exercised against an in-memory database with stubbed drug
data, so the suite is deterministic and never depends on RxNav or openFDA being
reachable. Network behaviour of the client itself is covered separately by the
parsing tests, which use recorded response shapes.
"""

import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app import create_app
from app.config import TestingConfig
from app.database import db
from app.models import DrugConcept, DrugIngredient, IngredientLimit, User, UserMedication
from app.services.drug_data_service import DrugDataService, normalise_ingredient_key
from app.services.medication_safety_service import (
    CONSULT_CAVEAT,
    MedicationSafetyService,
)


@pytest.fixture()
def app():
    application = create_app(TestingConfig)
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def user(app):
    u = User(email=f"consumer-{uuid.uuid4().hex[:6]}@test.local",
             password_hash="x", role="viewer")
    db.session.add(u)
    db.session.commit()
    return u


def _product(rxcui, name, ingredients):
    """Seed a cached product so no network call is needed."""
    concept = DrugConcept(rxcui=rxcui, name=name, tty="SBD", is_branded=True)
    for ing_name, mg in ingredients:
        concept.ingredients.append(DrugIngredient(
            rxcui=rxcui,
            ingredient_name=ing_name,
            ingredient_key=normalise_ingredient_key(ing_name),
            strength_amount=mg, strength_unit="MG" if mg else None, strength_mg=mg,
        ))
    db.session.add(concept)
    db.session.commit()
    return concept


def _set_limit(key, name, max_mg, source="FDA OTC monograph (test)", url=None):
    """Upsert a limit.

    `create_app` seeds the real curated table, so a test that wants a specific
    value has to overwrite the seeded row rather than insert alongside it.
    """
    row = db.session.query(IngredientLimit).filter_by(ingredient_key=key).first()
    if row is None:
        row = IngredientLimit(ingredient_key=key)
        db.session.add(row)
    row.ingredient_name = name
    row.max_daily_mg = max_mg
    row.source_name = source
    row.source_url = url
    db.session.commit()
    return row


def _clear_limit(key):
    row = db.session.query(IngredientLimit).filter_by(ingredient_key=key).first()
    if row is not None:
        db.session.delete(row)
        db.session.commit()


def _add(user, concept, name, units=1, per_day=1):
    med = UserMedication(
        user_id=user.id, rxcui=concept.rxcui if concept else None,
        display_name=name, units_per_dose=units, doses_per_day=per_day,
        entry_source="search" if concept else "manual",
    )
    db.session.add(med)
    db.session.commit()
    return med


# ---------------------------------------------------------------------------
# RULE-DUP-01 — duplicate active ingredient
# ---------------------------------------------------------------------------

class TestDuplicateIngredient:
    def test_duplicate_across_two_products_is_flagged(self, app, user):
        a = _product("1", "Tylenol 325 MG", [("acetaminophen", 325.0)])
        b = _product("2", "NightCold 325/25", [("acetaminophen", 325.0), ("diphenhydramine", 25.0)])
        _add(user, a, "Tylenol 325 MG", 1, 3)
        _add(user, b, "NightCold 325/25", 1, 1)

        result = MedicationSafetyService(db.session).run_check(str(user.id), persist=False)
        dup = [f for f in result["findings"] if f["rule_id"] == "RULE-DUP-01"]

        assert len(dup) == 1
        assert dup[0]["ingredient"] == "acetaminophen"
        assert len(dup[0]["products"]) == 2

    def test_single_product_does_not_flag_duplicate(self, app, user):
        a = _product("1", "Tylenol 325 MG", [("acetaminophen", 325.0)])
        _add(user, a, "Tylenol 325 MG", 1, 3)

        result = MedicationSafetyService(db.session).run_check(str(user.id), persist=False)
        assert not [f for f in result["findings"] if f["rule_id"] == "RULE-DUP-01"]

    def test_salt_form_matches_base_ingredient(self, app, user):
        """A duplicate hidden behind a salt name must still be caught."""
        a = _product("1", "Allergy 25 MG", [("diphenhydramine hydrochloride", 25.0)])
        b = _product("2", "SleepAid 25 MG", [("diphenhydramine", 25.0)])
        _add(user, a, "Allergy 25 MG")
        _add(user, b, "SleepAid 25 MG")

        result = MedicationSafetyService(db.session).run_check(str(user.id), persist=False)
        assert [f for f in result["findings"] if f["rule_id"] == "RULE-DUP-01"]


# ---------------------------------------------------------------------------
# RULE-DOSE-01 — cumulative daily dose
# ---------------------------------------------------------------------------

class TestCumulativeDose:
    @pytest.fixture(autouse=True)
    def limit(self, app):
        _set_limit("acetaminophen", "Acetaminophen", 4000.0,
                   url="https://example.test/monograph")

    def test_exceeding_labeled_max_is_high_severity(self, app, user):
        a = _product("1", "Tylenol 325 MG", [("acetaminophen", 325.0)])
        b = _product("2", "Percocet 325 MG", [("acetaminophen", 325.0), ("oxycodone", 5.0)])
        _add(user, a, "Tylenol 325 MG", units=2, per_day=4)     # 2600 mg
        _add(user, b, "Percocet 325 MG", units=2, per_day=4)    # 2600 mg -> 5200 total

        result = MedicationSafetyService(db.session).run_check(str(user.id), persist=False)
        dose = [f for f in result["findings"] if f["rule_id"] == "RULE-DOSE-01"]

        assert len(dose) == 1
        assert dose[0]["severity"] == "high"
        assert dose[0]["evidence"]["combined_daily_mg"] == 5200.0
        assert dose[0]["evidence"]["labeled_max_daily_mg"] == 4000.0
        assert result["highest_severity"] == "high"

    def test_approaching_limit_is_moderate_not_high(self, app, user):
        a = _product("1", "Tylenol 500 MG", [("acetaminophen", 500.0)])
        _add(user, a, "Tylenol 500 MG", units=1, per_day=7)   # 3500 mg = 87.5% of 4000

        result = MedicationSafetyService(db.session).run_check(str(user.id), persist=False)
        dose = [f for f in result["findings"] if f["rule_id"] == "RULE-DOSE-01"]

        assert len(dose) == 1
        assert dose[0]["severity"] == "moderate"

    def test_comfortably_under_limit_produces_no_dose_finding(self, app, user):
        a = _product("1", "Tylenol 500 MG", [("acetaminophen", 500.0)])
        _add(user, a, "Tylenol 500 MG", units=1, per_day=2)   # 1000 mg

        result = MedicationSafetyService(db.session).run_check(str(user.id), persist=False)
        assert not [f for f in result["findings"] if f["rule_id"] == "RULE-DOSE-01"]

    def test_dose_maths_accounts_for_units_and_frequency(self, app, user):
        a = _product("1", "Tylenol 500 MG", [("acetaminophen", 500.0)])
        _add(user, a, "Tylenol 500 MG", units=2, per_day=4)   # 500*2*4 = 4000

        result = MedicationSafetyService(db.session).run_check(str(user.id), persist=False)
        dose = [f for f in result["findings"] if f["rule_id"] == "RULE-DOSE-01"][0]
        assert dose["evidence"]["combined_daily_mg"] == 4000.0
        assert dose["severity"] == "high"   # at the limit counts as reaching it


# ---------------------------------------------------------------------------
# RULE-GAP — coverage gaps must be stated, never silent
# ---------------------------------------------------------------------------

class TestCoverageGaps:
    def test_unmatched_entry_is_reported_not_ignored(self, app, user):
        _add(user, None, "Some herbal thing from the market")

        result = MedicationSafetyService(db.session).run_check(str(user.id), persist=False)
        gaps = [f for f in result["findings"] if f["rule_id"] == "RULE-GAP-01"]
        assert len(gaps) == 1
        assert gaps[0]["severity"] == "info"

    def test_ingredient_without_known_limit_is_reported(self, app, user):
        _clear_limit("obscurine")
        a = _product("1", "Mystery 10 MG", [("obscurine", 10.0)])
        _add(user, a, "Mystery 10 MG")

        result = MedicationSafetyService(db.session).run_check(str(user.id), persist=False)
        gaps = [f for f in result["findings"] if f["rule_id"] == "RULE-GAP-03"]
        assert len(gaps) == 1
        assert "no labeled daily maximum on file" in gaps[0]["message"].lower()

    def test_non_mass_strength_is_reported_as_uncalculated(self, app, user):
        a = _product("1", "Cough Syrup", [("guaifenesin", None)])
        _add(user, a, "Cough Syrup")

        result = MedicationSafetyService(db.session).run_check(str(user.id), persist=False)
        assert [f for f in result["findings"] if f["rule_id"] == "RULE-GAP-02"]

    def test_empty_list_yields_no_findings_and_no_severity(self, app, user):
        result = MedicationSafetyService(db.session).run_check(str(user.id), persist=False)
        assert result["findings"] == []
        assert result["highest_severity"] == "none"


# ---------------------------------------------------------------------------
# Non-negotiable constraints
# ---------------------------------------------------------------------------

class TestSafetyConstraints:
    def test_every_finding_carries_a_citation_and_a_caveat(self, app, user):
        _set_limit("acetaminophen", "Acetaminophen", 4000.0)
        a = _product("1", "Tylenol 500 MG", [("acetaminophen", 500.0)])
        b = _product("2", "Combo 500 MG", [("acetaminophen", 500.0)])
        _add(user, a, "Tylenol 500 MG", 2, 4)
        _add(user, b, "Combo 500 MG", 2, 4)
        _add(user, None, "Unmatched item")

        result = MedicationSafetyService(db.session).run_check(str(user.id), persist=False)

        assert result["findings"], "expected findings to assert against"
        for finding in result["findings"]:
            assert finding["citations"], f"{finding['rule_id']} has no citation"
            assert any(c.get("source") for c in finding["citations"])
            assert finding["caveat"] == CONSULT_CAVEAT

    def test_finding_builder_rejects_an_uncited_claim(self):
        """The guard, not just convention, is what enforces the constraint."""
        with pytest.raises(ValueError, match="no source citation"):
            MedicationSafetyService._finding(
                rule_id="RULE-TEST", severity="high", title="t", message="m",
                ingredient=None, products=[], evidence={}, citations=[],
            )

    def test_result_never_claims_a_personalised_safe_verdict(self, app, user):
        a = _product("1", "Tylenol 500 MG", [("acetaminophen", 500.0)])
        _add(user, a, "Tylenol 500 MG", 1, 1)

        result = MedicationSafetyService(db.session).run_check(str(user.id), persist=False)
        blob = " ".join(f["message"] for f in result["findings"]).lower()
        for phrase in ("is safe for you", "safe to take", "you can safely"):
            assert phrase not in blob

    def test_check_is_persisted_with_its_sources(self, app, user):
        _set_limit("acetaminophen", "Acetaminophen", 4000.0)
        a = _product("1", "Tylenol 500 MG", [("acetaminophen", 500.0)])
        b = _product("2", "Combo 500 MG", [("acetaminophen", 500.0)])
        _add(user, a, "Tylenol 500 MG", 2, 4)
        _add(user, b, "Combo 500 MG", 2, 4)

        service = MedicationSafetyService(db.session)
        result = service.run_check(str(user.id), persist=True)

        assert result["check_id"]
        stored = service.get_check(result["check_id"], str(user.id))
        assert stored is not None
        assert stored.sources_used
        assert stored.rule_engine_version == "rules-v1"

    def test_one_user_cannot_read_another_users_check(self, app, user):
        other = User(email=f"other-{uuid.uuid4().hex[:6]}@test.local",
                     password_hash="x", role="viewer")
        db.session.add(other)
        db.session.commit()

        a = _product("1", "Tylenol 500 MG", [("acetaminophen", 500.0)])
        _add(user, a, "Tylenol 500 MG")
        service = MedicationSafetyService(db.session)
        result = service.run_check(str(user.id), persist=True)

        assert service.get_check(result["check_id"], str(other.id)) is None


# ---------------------------------------------------------------------------
# Drug data parsing
# ---------------------------------------------------------------------------

class TestDrugDataParsing:
    @pytest.mark.parametrize("name,expected_mg", [
        ("acetaminophen 325 MG", 325.0),
        ("levothyroxine sodium 0.025 MG", 0.025),
        ("cyanocobalamin 100 MCG", 0.1),
        ("magnesium 1 G", 1000.0),
    ])
    def test_strength_normalised_to_mg(self, name, expected_mg):
        assert DrugDataService._parse_strength(name)["mg"] == pytest.approx(expected_mg)

    def test_non_mass_units_do_not_produce_a_mg_value(self):
        """A volume cannot be compared against a mg limit, so it must stay None."""
        assert DrugDataService._parse_strength("guaifenesin 100 ML")["mg"] is None

    def test_unparseable_name_returns_none(self):
        assert DrugDataService._parse_strength("something with no strength") is None

    @pytest.mark.parametrize("raw,expected", [
        ("Acetaminophen", "acetaminophen"),
        ("diphenhydramine hydrochloride", "diphenhydramine"),
        ("  Naproxen   Sodium ", "naproxen"),
    ])
    def test_ingredient_key_normalisation(self, raw, expected):
        assert normalise_ingredient_key(raw) == expected
