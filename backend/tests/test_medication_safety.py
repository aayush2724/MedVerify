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


@pytest.fixture(autouse=True)
def offline_interactions(monkeypatch):
    """Keep the interaction rule off the network by default.

    RULE-INT-01 fetches an openFDA label per ingredient, so without this every
    test with two ingredients would make live calls and the suite would depend
    on openFDA being reachable. Returning None models "no label found", which
    the rule reports as a RULE-GAP-04 coverage gap. Tests that exercise
    interactions install their own label text with `_stub_interactions`.
    """
    monkeypatch.setattr(
        DrugDataService, "fetch_interaction_sections", lambda self, name: None
    )


def _stub_interactions(monkeypatch, sections_by_ingredient):
    """Serve fixed openFDA label prose in place of the network.

    Keys are normalised ingredient keys, so a stub for "warfarin" also serves
    the RxNorm name "warfarin sodium". A key absent from the mapping models
    "no label found", so gap behaviour stays testable.
    """
    def _fetch(self, ingredient_name):
        sections = sections_by_ingredient.get(normalise_ingredient_key(ingredient_name))
        if sections is None:
            return None
        return {
            "source": "openFDA drug label",
            "label_id": f"set-{normalise_ingredient_key(ingredient_name)}",
            "url": "https://dailymed.example.test/label",
            "brand_name": None,
            "generic_name": ingredient_name,
            "sections": sections,
            "retrieved_at": "2026-01-01T00:00:00+00:00",
        }

    monkeypatch.setattr(DrugDataService, "fetch_interaction_sections", _fetch)


def _section(name, text):
    return {"section": name, "text": text}


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
        assert stored.rule_engine_version == "rules-v2"

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
# RULE-INT-01 — drug-drug interactions read from openFDA label text (Phase 2)
# ---------------------------------------------------------------------------

class TestInteractions:
    """The rule's claim is "this label says X", never "these drugs interact".

    Every assertion here is about whether the tool faithfully reports label
    text and labels its own confidence, because that is the only claim it is
    entitled to make once RxNav's interaction API went away.
    """

    def _warfarin_and(self, user, other_name, other_mg=200.0):
        w = _product("1", "Warfarin 5 MG", [("warfarin sodium", 5.0)])
        o = _product("2", f"{other_name} {other_mg:g} MG", [(other_name, other_mg)])
        _add(user, w, "Warfarin 5 MG")
        _add(user, o, f"{other_name} {other_mg:g} MG")

    def test_label_naming_the_other_drug_outright_is_flagged(self, app, user, monkeypatch):
        self._warfarin_and(user, "aspirin", 81.0)
        _stub_interactions(monkeypatch, {
            "warfarin": [_section(
                "drug_interactions",
                "Bleeding risk is increased. Do not take with aspirin unless directed by a doctor.",
            )],
            "aspirin": [_section("warnings", "Take with food to reduce stomach upset.")],
        })

        result = MedicationSafetyService(db.session).run_check(str(user.id), persist=False)
        hits = [f for f in result["findings"] if f["rule_id"] == "RULE-INT-01"]

        assert len(hits) == 1
        assert hits[0]["evidence"]["match_type"] == "ingredient"
        assert hits[0]["evidence"]["matched_term"] == "aspirin"
        assert sorted(hits[0]["evidence"]["ingredient_keys"]) == ["aspirin", "warfarin"]

    def test_do_not_take_wording_escalates_to_high(self, app, user, monkeypatch):
        self._warfarin_and(user, "aspirin", 81.0)
        _stub_interactions(monkeypatch, {
            "warfarin": [_section(
                "drug_interactions", "Do not take with aspirin."
            )],
            "aspirin": [_section("warnings", "Take with food.")],
        })

        result = MedicationSafetyService(db.session).run_check(str(user.id), persist=False)
        hit = [f for f in result["findings"] if f["rule_id"] == "RULE-INT-01"][0]

        assert hit["severity"] == "high"
        assert hit["evidence"]["contraindication_wording"] is True
        assert result["highest_severity"] == "high"

    def test_general_caution_stays_moderate(self, app, user, monkeypatch):
        self._warfarin_and(user, "aspirin", 81.0)
        _stub_interactions(monkeypatch, {
            "warfarin": [_section(
                "drug_interactions",
                "Tell your doctor if you are taking aspirin, as monitoring may be needed.",
            )],
            "aspirin": [_section("warnings", "Take with food.")],
        })

        result = MedicationSafetyService(db.session).run_check(str(user.id), persist=False)
        hit = [f for f in result["findings"] if f["rule_id"] == "RULE-INT-01"][0]

        assert hit["severity"] == "moderate"
        assert hit["evidence"]["contraindication_wording"] is False

    def test_class_mention_is_flagged_and_named_as_a_class(self, app, user, monkeypatch):
        """A label saying "NSAIDs" must still catch ibuprofen — and say it did so by class."""
        self._warfarin_and(user, "ibuprofen", 200.0)
        _stub_interactions(monkeypatch, {
            "warfarin": [_section(
                "ask_a_doctor_or_pharmacist_before_use",
                "Ask a doctor or pharmacist before use if you are taking an NSAID.",
            )],
            "ibuprofen": [_section("warnings", "Take with food.")],
        })

        result = MedicationSafetyService(db.session).run_check(str(user.id), persist=False)
        hit = [f for f in result["findings"] if f["rule_id"] == "RULE-INT-01"][0]

        assert hit["evidence"]["match_type"] == "class"
        assert hit["evidence"]["matched_term"] == "nsaid"
        assert "class" in hit["message"].lower()

    def test_composition_sentence_is_not_reported_as_an_interaction(self, app, user, monkeypatch):
        """A combination product reciting its own contents is not a warning.

        Without this guard, RULE-DUP-01's territory (shared ingredients) would
        be double-reported as an interaction between the two ingredients.
        """
        a = _product("1", "NightCold", [("acetaminophen", 325.0), ("diphenhydramine", 25.0)])
        _add(user, a, "NightCold")
        _stub_interactions(monkeypatch, {
            "acetaminophen": [_section(
                "warnings",
                "Each caplet contains acetaminophen 325 mg and diphenhydramine 25 mg.",
            )],
            "diphenhydramine": [_section(
                "warnings",
                "This product contains diphenhydramine and acetaminophen.",
            )],
        })

        result = MedicationSafetyService(db.session).run_check(str(user.id), persist=False)
        assert not [f for f in result["findings"] if f["rule_id"] == "RULE-INT-01"]

    def test_a_pair_is_reported_once_even_when_both_labels_warn(self, app, user, monkeypatch):
        self._warfarin_and(user, "aspirin", 81.0)
        _stub_interactions(monkeypatch, {
            "warfarin": [_section("drug_interactions", "Increased bleeding risk with aspirin.")],
            "aspirin": [_section("drug_interactions", "Increased bleeding risk with warfarin.")],
        })

        result = MedicationSafetyService(db.session).run_check(str(user.id), persist=False)
        hits = [f for f in result["findings"] if f["rule_id"] == "RULE-INT-01"]

        assert len(hits) == 1
        assert hits[0]["evidence"]["mention_count"] == 2

    def test_silent_labels_produce_no_interaction_and_no_gap(self, app, user, monkeypatch):
        self._warfarin_and(user, "aspirin", 81.0)
        _stub_interactions(monkeypatch, {
            "warfarin": [_section("drug_interactions", "No clinically significant issues noted.")],
            "aspirin": [_section("drug_interactions", "No clinically significant issues noted.")],
        })

        result = MedicationSafetyService(db.session).run_check(str(user.id), persist=False)
        rule_ids = {f["rule_id"] for f in result["findings"]}

        assert "RULE-INT-01" not in rule_ids
        assert "RULE-GAP-04" not in rule_ids, "a label that was read is not a coverage gap"

    def test_unreadable_label_is_reported_as_a_gap(self, app, user, monkeypatch):
        """Silence about an ingredient we could not check must never look clean."""
        self._warfarin_and(user, "aspirin", 81.0)
        _stub_interactions(monkeypatch, {
            "warfarin": [_section("drug_interactions", "Nothing of note.")],
            # aspirin absent -> no label found
        })

        result = MedicationSafetyService(db.session).run_check(str(user.id), persist=False)
        gaps = [f for f in result["findings"] if f["rule_id"] == "RULE-GAP-04"]

        assert len(gaps) == 1
        assert gaps[0]["severity"] == "info"
        assert "aspirin" in gaps[0]["evidence"]["no_label_found"]

    def test_label_without_interaction_text_is_a_distinct_gap(self, app, user, monkeypatch):
        self._warfarin_and(user, "aspirin", 81.0)
        _stub_interactions(monkeypatch, {
            "warfarin": [_section("drug_interactions", "Nothing of note.")],
            "aspirin": [],   # label exists, publishes no interaction prose
        })

        result = MedicationSafetyService(db.session).run_check(str(user.id), persist=False)
        gaps = [f for f in result["findings"] if f["rule_id"] == "RULE-GAP-04"][0]

        assert "aspirin" in gaps["evidence"]["label_without_interaction_text"]
        assert gaps["evidence"]["no_label_found"] == []

    def test_single_ingredient_has_no_pair_so_no_interaction_gap(self, app, user):
        a = _product("1", "Tylenol 500 MG", [("acetaminophen", 500.0)])
        _add(user, a, "Tylenol 500 MG")

        result = MedicationSafetyService(db.session).run_check(str(user.id), persist=False)
        rule_ids = {f["rule_id"] for f in result["findings"]}

        assert "RULE-INT-01" not in rule_ids
        assert "RULE-GAP-04" not in rule_ids

    def test_finding_quotes_the_label_verbatim_and_cites_the_section(self, app, user, monkeypatch):
        sentence = "Do not take with aspirin without asking a doctor."
        self._warfarin_and(user, "aspirin", 81.0)
        _stub_interactions(monkeypatch, {
            "warfarin": [_section("drug_interactions", sentence)],
            "aspirin": [_section("warnings", "Take with food.")],
        })

        result = MedicationSafetyService(db.session).run_check(str(user.id), persist=False)
        hit = [f for f in result["findings"] if f["rule_id"] == "RULE-INT-01"][0]
        citation = hit["citations"][0]

        assert citation["source"] == "openFDA drug label"
        assert citation["excerpt"] == sentence
        assert citation["section"] == "drug_interactions"
        assert sentence in hit["message"]

    def test_finding_disclaims_a_clinical_severity_grade(self, app, user, monkeypatch):
        """The severity is derived from label wording; the finding has to say so."""
        self._warfarin_and(user, "aspirin", 81.0)
        _stub_interactions(monkeypatch, {
            "warfarin": [_section("drug_interactions", "Do not take with aspirin.")],
            "aspirin": [_section("warnings", "Take with food.")],
        })

        result = MedicationSafetyService(db.session).run_check(str(user.id), persist=False)
        hit = [f for f in result["findings"] if f["rule_id"] == "RULE-INT-01"][0]

        assert "not a clinical severity rating" in hit["message"]
        assert hit["caveat"] == CONSULT_CAVEAT

    def test_ingredient_cap_is_reported_rather_than_applied_silently(self, app, user, monkeypatch):
        from app.services.medication_safety_service import MAX_INTERACTION_INGREDIENTS

        over = MAX_INTERACTION_INGREDIENTS + 1
        ingredients = [(f"drug{i:02d}", 10.0) for i in range(1, over + 1)]
        a = _product("1", "Polypharmacy Pack", ingredients)
        _add(user, a, "Polypharmacy Pack")
        _stub_interactions(monkeypatch, {})

        result = MedicationSafetyService(db.session).run_check(str(user.id), persist=False)
        capped = [f for f in result["findings"] if f["rule_id"] == "RULE-GAP-05"]

        assert len(capped) == 1
        assert capped[0]["evidence"]["not_scanned"] == [f"drug{over:02d}"]


class TestInteractionScanning:
    """Unit-level checks on the text scanner behind RULE-INT-01."""

    def _target(self, key, name=None):
        return {"ingredient_key": key, "ingredient_name": name or key}

    def test_word_boundaries_prevent_substring_false_positives(self):
        sections = [_section("drug_interactions", "Contains no codeineberry extract.")]
        assert MedicationSafetyService._scan_sections(sections, self._target("codeine")) == []

    def test_longest_class_term_wins(self):
        sections = [_section(
            "drug_interactions",
            "Avoid use with a central nervous system depressant of any kind.",
        )]
        hits = MedicationSafetyService._scan_sections(sections, self._target("oxycodone"))
        assert hits[0]["matched_term"] == "central nervous system depressant"

    def test_contraindication_is_scoped_to_the_matching_sentence(self):
        """Strong wording elsewhere on a label must not escalate an unrelated sentence."""
        sections = [_section(
            "warnings",
            "Do not use if you are allergic to this product. "
            "Tell your doctor if you take warfarin.",
        )]
        hits = MedicationSafetyService._scan_sections(sections, self._target("warfarin"))
        assert len(hits) == 1
        assert hits[0]["contraindication"] is False

    def test_excerpt_is_capped(self):
        from app.services.medication_safety_service import MAX_EXCERPT_CHARS

        sections = [_section("drug_interactions", "warfarin " + ("x" * 900) + ".")]
        hits = MedicationSafetyService._scan_sections(sections, self._target("warfarin"))
        assert len(hits[0]["sentence"]) == MAX_EXCERPT_CHARS


# ---------------------------------------------------------------------------
# Drug data parsing
# ---------------------------------------------------------------------------

class TestProductSearchOrdering:
    """RxNav returns its concept groups in its own order, not ours."""

    def _response(self):
        # Shape of a real RxNav /drugs.json reply: pack groups arrive first.
        return {"drugGroup": {"conceptGroup": [
            {"tty": "GPCK", "conceptProperties": [
                {"rxcui": f"pk{i}", "name": f"{{1 (acetaminophen 500 MG / ...)}} Pack {i}"}
                for i in range(8)
            ]},
            {"tty": "SCD", "conceptProperties": [
                {"rxcui": "scd1", "name": "acetaminophen 500 MG Oral Tablet"},
            ]},
            {"tty": "SBD", "conceptProperties": [
                {"rxcui": "sbd1", "name": "acetaminophen 500 MG Oral Tablet [Tylenol]"},
            ]},
        ]}}

    def test_single_products_outrank_packs_regardless_of_response_order(self, app, monkeypatch):
        """A pack bundles several drugs; it must not crowd out the plain tablet.

        Consuming the response in RxNav's order let eight packs fill the result
        page, so a plain paracetamol search offered only cold-and-flu bundles —
        and the prescription pipeline then resolved to one, importing drugs the
        patient was not taking.
        """
        svc = DrugDataService(db.session)
        monkeypatch.setattr(
            DrugDataService, "_get_json",
            lambda self, url, params, provider, ttl=None: self and self._response_stub,
        )
        svc._response_stub = self._response()

        results = svc.search_products("acetaminophen", limit=5)

        assert results[0]["tty"] == "SCD"
        assert results[1]["tty"] == "SBD"
        assert [r["tty"] for r in results[:2]] == ["SCD", "SBD"]

    def test_plain_products_outrank_combinations_within_a_term_type(self, app, monkeypatch):
        """RxNav returns combinations first; `limit` then hides the plain drug.

        A consumer searching "acetaminophen" was offered eight oxycodone and
        cold-and-flu combinations and never the plain tablet.
        """
        svc = DrugDataService(db.session)
        response = {"drugGroup": {"conceptGroup": [{"tty": "SCD", "conceptProperties": [
            {"rxcui": "c1", "name": "acetaminophen 500 MG / oxycodone hydrochloride 5 MG Oral Tablet"},
            {"rxcui": "c2", "name": "acetaminophen 500 MG / methionine 250 MG Oral Tablet"},
            {"rxcui": "c3", "name": "acetaminophen 500 MG / chlorpheniramine 2 MG / phenylephrine 5 MG Oral Tablet"},
            {"rxcui": "plain", "name": "acetaminophen 500 MG Oral Tablet"},
        ]}]}}
        monkeypatch.setattr(
            DrugDataService, "_get_json",
            lambda self, url, params, provider, ttl=None: response,
        )

        results = svc.search_products("acetaminophen", limit=2)

        assert results[0]["rxcui"] == "plain", [r["name"] for r in results]

    def test_packs_are_still_offered_once_single_products_run_out(self, app, monkeypatch):
        svc = DrugDataService(db.session)
        monkeypatch.setattr(
            DrugDataService, "_get_json",
            lambda self, url, params, provider, ttl=None: self and self._response_stub,
        )
        svc._response_stub = self._response()

        results = svc.search_products("acetaminophen", limit=5)

        assert len(results) == 5
        assert any(r["tty"] == "GPCK" for r in results), "packs should fill the remainder"


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
