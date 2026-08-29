"""
Module 2, Phase 3 — combined prescription pipeline tests.

Both halves of the pipeline are stubbed at their boundaries so the suite stays
deterministic and offline: the forensics half is replaced with a fake that
returns a fixed verification record, and RxNorm/openFDA lookups are replaced
with fixtures. What is exercised for real is the part Phase 3 actually adds —
reading medications off prescription text, and carrying the provenance of that
reading through to the result.
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
from app.models import (
    DrugConcept,
    DrugIngredient,
    IngredientLimit,
    SafetyCheck,
    User,
    UserMedication,
    VerificationRecord,
)
from app.services.drug_data_service import DrugDataService, normalise_ingredient_key
from app.services.prescription_pipeline_service import (
    MAX_DETECTED_MEDICATIONS,
    PrescriptionPipelineService,
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
    u = User(email=f"patient-{uuid.uuid4().hex[:6]}@test.local",
             password_hash="x", role="viewer")
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """No RxNorm, no openFDA. Individual tests opt back in with a stub."""
    monkeypatch.setattr(DrugDataService, "search_products", lambda self, term, limit=15: [])
    monkeypatch.setattr(DrugDataService, "get_concept", lambda self, rxcui, **kw: None)
    monkeypatch.setattr(DrugDataService, "fetch_interaction_sections", lambda self, name: None)
    monkeypatch.setattr(DrugDataService, "fetch_label_excerpt", lambda self, name: None)


class _FakeVerification:
    """Stands in for Module 1, returning a fixed record with known OCR text.

    Phase 3's contract with Module 1 is narrow — run the pipeline, hand back a
    record whose `extracted_text` holds what was read. Faking exactly that keeps
    these tests about the new behaviour rather than about ELA scores.
    """

    def __init__(self, text, status="GENUINE", confidence=0.9):
        self.text, self.status, self.confidence = text, status, confidence
        self.calls = 0

    def verify(self, filepath, original_filename, user_id=None, ip_address=None):
        self.calls += 1
        record = VerificationRecord(
            user_id=uuid.UUID(str(user_id)) if user_id else None,
            filename=os.path.basename(filepath),
            original_filename=original_filename,
            extracted_text=self.text,
            status=self.status,
            confidence=self.confidence,
            reasons=["stubbed"],
            extracted_fields={"hospital_name": "Test Hospital"},
            text_score=0.8,
            image_score=0.9,
            processing_time_ms=10,
        )
        db.session.add(record)
        db.session.commit()
        return record


def _service(text, **kwargs):
    return PrescriptionPipelineService(db.session, _FakeVerification(text, **kwargs))


def _seed_product(rxcui, name, ingredients):
    concept = DrugConcept(rxcui=rxcui, name=name, tty="SBD", is_branded=True)
    for ing_name, mg in ingredients:
        concept.ingredients.append(DrugIngredient(
            rxcui=rxcui, ingredient_name=ing_name,
            ingredient_key=normalise_ingredient_key(ing_name),
            strength_amount=mg, strength_unit="MG", strength_mg=mg,
        ))
    db.session.add(concept)
    db.session.commit()
    return concept


def _resolve_to(monkeypatch, concept):
    """Make every RxNorm resolution land on one seeded product."""
    monkeypatch.setattr(
        DrugDataService, "search_products",
        lambda self, term, limit=15: [{"rxcui": concept.rxcui, "name": concept.name}],
    )
    monkeypatch.setattr(
        DrugDataService, "get_concept", lambda self, rxcui, **kw: concept,
    )


# ---------------------------------------------------------------------------
# Reading medications off a prescription
# ---------------------------------------------------------------------------

class TestMedicationDetection:
    def test_known_ingredient_is_matched_without_a_network_call(self, app):
        """The curated tables are the first pass, so common drugs cost nothing."""
        found = _service("").detect_medications("Tab. Acetaminophen 500mg 1-0-1")

        assert len(found) == 1
        assert found[0].match_confidence == "high"
        assert found[0].strength_mg == 500.0

    def test_numeric_sig_is_read_as_units_and_frequency(self, app):
        found = _service("").detect_medications("Tab. Ibuprofen 400mg 1-0-1")[0]

        assert found.units_per_dose == 1.0
        assert found.doses_per_day == 2.0
        assert found.frequency_source == "parsed"
        assert found.schedule_note == "1-0-1"

    def test_numeric_sig_counts_only_the_non_zero_slots(self, app):
        found = _service("").detect_medications("Tab. Ibuprofen 400mg 2-2-2")[0]

        assert found.units_per_dose == 2.0
        assert found.doses_per_day == 3.0

    @pytest.mark.parametrize("sig,expected", [
        ("once daily", 1.0),
        ("twice daily", 2.0),
        ("BD", 2.0),
        ("three times a day", 3.0),
        ("TDS", 3.0),
        ("QID", 4.0),
        ("q8h", 3.0),
        ("at bedtime", 1.0),
    ])
    def test_written_frequencies_are_parsed(self, app, sig, expected):
        found = _service("").detect_medications(f"Tab. Ibuprofen 400mg {sig}")[0]

        assert found.doses_per_day == expected
        assert found.frequency_source == "parsed"

    def test_unit_count_is_read_from_the_line(self, app):
        found = _service("").detect_medications("Ibuprofen 200mg - 2 tablets twice daily")[0]

        assert found.units_per_dose == 2.0
        assert found.units_source == "parsed"
        assert found.doses_per_day == 2.0

    def test_missing_frequency_is_marked_assumed_not_stated(self, app):
        """An assumption must never be presented as something the page said."""
        found = _service("").detect_medications("Tab. Ibuprofen 400mg")[0]

        assert found.doses_per_day == 1.0
        assert found.frequency_source == "assumed"
        assert found.schedule_note is None

    def test_page_furniture_is_not_read_as_a_medication(self, app):
        text = "\n".join([
            "Dr. A. Sharma, MBBS",
            "Patient Name: Redacted",
            "Date: 01/02/2026",
            "Hospital: Test Hospital",
            "Registration No: 12345",
            "Tab. Ibuprofen 400mg 1-0-1",
        ])
        found = _service("").detect_medications(text)

        assert [f.display_name.lower() for f in found] == ["ibuprofen"]

    def test_the_same_ingredient_on_two_lines_is_not_double_counted(self, app):
        text = "Tab. Ibuprofen 400mg 1-0-1\nCap. Ibuprofen 200mg once daily"
        assert len(_service("").detect_medications(text)) == 1

    def test_detection_stops_at_the_cap(self, app):
        # Distinct alphabetic names: a digit inside the name would truncate
        # every candidate to the same stem and collapse them into one entry.
        lines = [f"Tab. Zeta{chr(ord('a') + i)}ine {100 + i}mg 1-0-1"
                 for i in range(MAX_DETECTED_MEDICATIONS + 8)]
        found = _service("").detect_medications("\n".join(lines))

        assert len(found) == MAX_DETECTED_MEDICATIONS

    def test_empty_text_detects_nothing(self, app):
        assert _service("").detect_medications("") == []
        assert _service("").detect_medications("   \n  ") == []

    def test_form_prefix_is_stripped_from_the_candidate_name(self):
        assert PrescriptionPipelineService._candidate_name("Tab. Dolo 650mg 1-0-1") == "Dolo"
        assert PrescriptionPipelineService._candidate_name("Syp. Ambroxol 30mg") == "Ambroxol"

    def test_unresolvable_line_is_kept_rather_than_dropped(self, app):
        """Dropping it would shrink the list and make the check look cleaner."""
        found = _service("").detect_medications("Tab. Zzyzxine 250mg 1-0-1")

        assert len(found) == 1
        assert found[0].rxcui is None
        assert found[0].as_dict()["matched_product"] is False


# ---------------------------------------------------------------------------
# Resolution accuracy — regressions found by running a real prescription
# ---------------------------------------------------------------------------

class TestResolutionAccuracy:
    def test_list_number_is_not_read_as_a_quantity(self, app):
        """"4. Tab. Aspirin" is the fourth item, not four tablets.

        OCR routinely drops the period after the list number, leaving "4 Tab"
        for the units regex to find. Caught on a real scan, where it quadrupled
        the daily total for every item numbered above one.
        """
        found = _service("").detect_medications("4. Tab. Aspirin 75mg once daily")[0]

        assert found.units_per_dose == 1.0
        assert found.units_source == "assumed"
        assert found.doses_per_day == 1.0

    @pytest.mark.parametrize("line", [
        "1. Tab. Ibuprofen 400mg 1-0-1",
        "2) Tab. Ibuprofen 400mg 1-0-1",
        "(3) Tab. Ibuprofen 400mg 1-0-1",
    ])
    def test_list_markers_in_several_styles_are_stripped(self, app, line):
        found = _service("").detect_medications(line)[0]
        assert found.units_per_dose == 1.0
        assert found.doses_per_day == 2.0

    def test_rxnorm_is_queried_with_the_term_from_the_page(self, app, monkeypatch):
        """The curated display name carries a gloss RxNorm cannot match.

        The limit table stores "Acetaminophen (paracetamol)". Searching that
        verbatim returns nothing, so the drug silently failed to resolve and was
        reported as uncheckable even though it was read perfectly.
        """
        queries = []

        def _spy(self, term, limit=15):
            queries.append(term)
            return []

        monkeypatch.setattr(DrugDataService, "search_products", _spy)
        _service("").detect_medications("Tab. Acetaminophen 500mg 1-0-1")

        assert queries, "expected an RxNorm lookup"
        assert all("(" not in q for q in queries), queries
        assert any(q.lower().startswith("acetaminophen") for q in queries)

    def test_unpunctuated_list_number_is_still_not_a_quantity(self, app):
        """OCR drops the period. A real scan produced "4 Tab Aspirin 75mg"."""
        found = _service("").detect_medications("4 Tab Aspirin 75mg once daily")[0]

        assert found.units_per_dose == 1.0
        # Flagged assumed, not parsed: stripping a bare number is a judgement
        # call, and the report has to show it as an assumption.
        assert found.units_source == "assumed"

    def test_a_pack_does_not_win_over_a_single_product(self, app, monkeypatch):
        """A GPCK bundles several drugs; resolving to one imports all of them.

        On a real run, "Acetaminophen 500mg" resolved to a pack and put
        chlorpheniramine and phenylephrine into the findings for a prescription
        that contained neither.
        """
        pack = _seed_product("9", "Cold Pack", [
            ("acetaminophen", 500.0), ("chlorpheniramine", 2.0), ("phenylephrine", 5.0),
        ])
        plain = _seed_product("8", "acetaminophen 500 MG Oral Tablet", [("acetaminophen", 500.0)])

        monkeypatch.setattr(
            DrugDataService, "search_products",
            # Worst case again: RxNorm ranks the pack first.
            lambda self, term, limit=15: [
                {"rxcui": "9", "name": pack.name, "tty": "GPCK"},
                {"rxcui": "8", "name": plain.name, "tty": "SCD"},
            ],
        )
        monkeypatch.setattr(
            DrugDataService, "get_concept",
            lambda self, rxcui, **kw: {"8": plain, "9": pack}.get(rxcui),
        )

        found = _service("").detect_medications("Tab. Acetaminophen 500mg 1-0-1")[0]

        assert found.rxcui == "8"

    def test_combination_product_does_not_win_over_the_plain_one(self, app, monkeypatch):
        """A search for aspirin must not resolve to an aspirin/oxycodone product.

        Every extra ingredient in a wrongly chosen combination product is then
        reported as a drug the patient is taking — on a real run this put
        oxycodone in the findings for a prescription that had none.
        """
        plain = _seed_product("1", "Aspirin 81 MG", [("aspirin", 81.0)])
        combo = _seed_product("2", "Aspirin / Oxycodone", [("aspirin", 325.0), ("oxycodone", 5.0)])

        monkeypatch.setattr(
            DrugDataService, "search_products",
            # Deliberately worst case: the combination product ranks first.
            lambda self, term, limit=15: [
                {"rxcui": "2", "name": combo.name},
                {"rxcui": "1", "name": plain.name},
            ],
        )
        monkeypatch.setattr(
            DrugDataService, "get_concept",
            lambda self, rxcui, **kw: {"1": plain, "2": combo}.get(rxcui),
        )

        found = _service("").detect_medications("Tab. Aspirin 75mg once daily")[0]

        assert found.rxcui == "1"
        assert found.resolved_name == "Aspirin 81 MG"

    def test_a_combination_product_is_still_used_when_it_is_the_only_match(self, app, monkeypatch):
        """Preferring the plainest product must not mean rejecting the only one."""
        combo = _seed_product("2", "Aspirin / Oxycodone", [("aspirin", 325.0), ("oxycodone", 5.0)])

        monkeypatch.setattr(
            DrugDataService, "search_products",
            lambda self, term, limit=15: [{"rxcui": "2", "name": combo.name}],
        )
        monkeypatch.setattr(DrugDataService, "get_concept", lambda self, rxcui, **kw: combo)

        found = _service("").detect_medications("Tab. Aspirin 75mg once daily")[0]

        assert found.rxcui == "2"
        assert found.resolution_status == "resolved"


# ---------------------------------------------------------------------------
# The combined run
# ---------------------------------------------------------------------------

class TestCombinedPipeline:
    def test_document_and_safety_halves_both_come_back(self, app, user, monkeypatch):
        concept = _seed_product("1", "Ibuprofen 400 MG", [("ibuprofen", 400.0)])
        _resolve_to(monkeypatch, concept)

        result = _service("Tab. Ibuprofen 400mg 1-0-1").analyse(
            "/tmp/scan.png", "scan.png", str(user.id),
        )

        assert result["document"]["status"] == "GENUINE"
        assert result["document"]["verdict_label"] == "Likely Genuine"
        assert result["safety"]["source"] == "prescription"
        assert len(result["medications_detected"]) == 1

    def test_ocr_runs_once_for_both_modules(self, app, user, monkeypatch):
        """The single shared OCR pass is the whole point of Phase 3."""
        concept = _seed_product("1", "Ibuprofen 400 MG", [("ibuprofen", 400.0)])
        _resolve_to(monkeypatch, concept)

        verification = _FakeVerification("Tab. Ibuprofen 400mg 1-0-1")
        service = PrescriptionPipelineService(db.session, verification)
        service.analyse("/tmp/scan.png", "scan.png", str(user.id))

        assert verification.calls == 1

    def test_the_dose_rule_fires_on_a_list_read_off_the_page(self, app, user, monkeypatch):
        """The same cited rules run whether the list was typed or scanned."""
        concept = _seed_product("1", "Ibuprofen 400 MG", [("ibuprofen", 400.0)])
        _resolve_to(monkeypatch, concept)
        row = db.session.query(IngredientLimit).filter_by(ingredient_key="ibuprofen").first()
        row.max_daily_mg = 1200.0
        db.session.commit()

        # 400 mg x 1 unit x 4 doses = 1600 mg against a 1200 mg labeled maximum
        result = _service("Tab. Ibuprofen 400mg QID").analyse(
            "/tmp/scan.png", "scan.png", str(user.id),
        )
        dose = [f for f in result["safety"]["findings"] if f["rule_id"] == "RULE-DOSE-01"]

        assert len(dose) == 1
        assert dose[0]["severity"] == "high"
        assert dose[0]["evidence"]["combined_daily_mg"] == 1600.0

    def test_result_is_stamped_as_read_by_ocr_and_unconfirmed(self, app, user, monkeypatch):
        concept = _seed_product("1", "Ibuprofen 400 MG", [("ibuprofen", 400.0)])
        _resolve_to(monkeypatch, concept)

        result = _service("Tab. Ibuprofen 400mg 1-0-1").analyse(
            "/tmp/scan.png", "scan.png", str(user.id),
        )
        provenance = result["safety"]["provenance"]

        assert provenance["medications_read_by"] == "OCR"
        assert provenance["confirmed_by_user"] is False
        assert "not been confirmed" in result["reading_caveat"]

    def test_assumed_frequency_is_called_out_in_the_caveat(self, app, user, monkeypatch):
        """An understated daily total has to say why it might be understated."""
        concept = _seed_product("1", "Ibuprofen 400 MG", [("ibuprofen", 400.0)])
        _resolve_to(monkeypatch, concept)

        result = _service("Tab. Ibuprofen 400mg").analyse(
            "/tmp/scan.png", "scan.png", str(user.id),
        )

        assert "once a day was assumed" in result["reading_caveat"]
        assert "too low" in result["reading_caveat"]

    def test_a_document_with_no_medications_says_so(self, app, user):
        result = _service("Fit to fly certificate. Nothing was prescribed.").analyse(
            "/tmp/cert.png", "cert.png", str(user.id),
        )

        assert result["medications_detected"] == []
        assert "No medications could be read" in result["reading_caveat"]
        assert result["document"]["status"] == "GENUINE"

    def test_forensics_verdict_survives_an_empty_medication_list(self, app, user):
        """A fake certificate is still a fake certificate with nothing to check."""
        result = _service("Nothing here.", status="FAKE", confidence=0.1).analyse(
            "/tmp/cert.png", "cert.png", str(user.id),
        )

        assert result["document"]["status"] == "FAKE"
        assert result["document"]["verdict_label"] == "Suspicious/Fake"

    def test_check_is_persisted_and_linked_to_the_document(self, app, user, monkeypatch):
        concept = _seed_product("1", "Ibuprofen 400 MG", [("ibuprofen", 400.0)])
        _resolve_to(monkeypatch, concept)

        result = _service("Tab. Ibuprofen 400mg 1-0-1").analyse(
            "/tmp/scan.png", "scan.png", str(user.id),
        )

        stored = db.session.get(SafetyCheck, uuid.UUID(result["safety"]["check_id"]))
        assert stored is not None
        assert stored.source == "prescription"
        assert str(stored.verification_record_id) == result["document"]["record_id"]

    def test_scanned_medications_are_not_added_to_the_saved_list(self, app, user, monkeypatch):
        """An OCR guess must never silently become the user's real list."""
        concept = _seed_product("1", "Ibuprofen 400 MG", [("ibuprofen", 400.0)])
        _resolve_to(monkeypatch, concept)

        _service("Tab. Ibuprofen 400mg 1-0-1").analyse(
            "/tmp/scan.png", "scan.png", str(user.id),
        )

        assert db.session.query(UserMedication).filter_by(user_id=user.id).count() == 0

    def test_every_finding_still_carries_a_citation_and_caveat(self, app, user, monkeypatch):
        from app.services.medication_safety_service import CONSULT_CAVEAT

        concept = _seed_product("1", "Ibuprofen 400 MG", [("ibuprofen", 400.0)])
        _resolve_to(monkeypatch, concept)

        result = _service("Tab. Ibuprofen 400mg QID\nTab. Zzyzxine 250mg 1-0-1").analyse(
            "/tmp/scan.png", "scan.png", str(user.id),
        )

        assert result["safety"]["findings"], "expected findings to assert against"
        for finding in result["safety"]["findings"]:
            assert finding["citations"]
            assert any(c.get("source") for c in finding["citations"])
            assert finding["caveat"] == CONSULT_CAVEAT
