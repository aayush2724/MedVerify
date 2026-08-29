"""
Prescription Pipeline — Module 2, Phase 3

Runs one uploaded document through *both* modules in a single pass:

    upload -> preprocess -> OCR -> [ Module 1 forensics ]
                                \\-> [ medication extraction -> Module 2 rules ]

The OCR happens once. `VerificationService.verify()` already preprocesses the
image, reads the text and stores it on the verification record, so the safety
half reads that same text rather than paying for a second extraction. That
shared step is the whole point of Phase 3.

WHAT THIS PIPELINE IS ALLOWED TO CLAIM
--------------------------------------
The medication list here was *read off a photograph*, not typed by the person
taking the drugs. That is a materially weaker input than the curated list
Module 2 normally checks, and the design refuses to hide the difference:

* Every result is stamped `source: "prescription"` and carries a `provenance`
  block naming the document it came from and how the list was read.
* Each detected medication reports its own `match_confidence` and whether the
  dosing was `parsed` from the page or `assumed` by default. A frequency the
  page never stated is never presented as though it did.
* A line that cannot be resolved to a known product is still passed to the rule
  engine, which reports it through RULE-GAP-01. Dropping it would shrink the
  list silently and make the check look cleaner than it was.
* Nothing is written to the user's saved medication list. A guess made by OCR
  must not quietly become the list every future check runs against.

The rule engine itself is unchanged — the same named, cited rules run over this
list as over a hand-entered one.
"""

import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..data.interaction_classes import INGREDIENT_CLASSES
from ..models import DrugConcept, DrugIngredient, IngredientLimit
from ..repositories.audit_repository import AuditRepository
from .drug_data_service import DrugDataService, normalise_ingredient_key
from .medication_safety_service import MedicationSafetyService

logger = logging.getLogger(__name__)

PIPELINE_VERSION = "pipeline-v1"

# Bounds on one document. A prescription has a handful of lines; anything past
# these caps is noise or a scanning artefact, and each RxNorm lookup is a
# network call.
MAX_DETECTED_MEDICATIONS = 15
MAX_RXNORM_LOOKUPS = 10
MIN_LINE_LENGTH = 3

# "650 mg", "0.5 G", "5ml"
_STRENGTH_RE = re.compile(
    r"(?P<amount>\d+(?:\.\d+)?)\s*(?P<unit>mg|mcg|ug|g|gm|ml|iu|units?)\b",
    re.IGNORECASE,
)

_UNIT_TO_MG = {"MG": 1.0, "G": 1000.0, "GM": 1000.0, "MCG": 0.001, "UG": 0.001}

# Preference order when RxNorm offers several products for one line. Clinical
# drug concepts first, packs last: a pack is a bundle of several products, and
# resolving to one imports every drug in the bundle into the safety check as
# though the patient were taking all of them.
_TTY_RANK = {"SCD": 0, "SBD": 1, "BPCK": 2, "GPCK": 2}

# The "1-0-1" convention: one unit in the morning, none at midday, one at
# night. Widely used on handwritten and printed prescriptions in South Asia,
# which is exactly the document population Module 1 was built for.
_NUMERIC_SIG_RE = re.compile(r"\b(\d)\s*[-–—]\s*(\d)\s*[-–—]\s*(\d)\b")

# Ordered most-specific first: "daily" also appears inside "twice daily", so a
# looser pattern must never be tested before a tighter one.
_FREQUENCY_PATTERNS = (
    (re.compile(r"\b(four\s+times\s+(a\s+)?day|4\s*times\s+(a\s+)?day|qid|qds|q\.?i\.?d\.?|q6h)\b", re.I), 4.0),
    (re.compile(r"\b(three\s+times\s+(a\s+)?day|3\s*times\s+(a\s+)?day|thrice\s+daily|tds|tid|t\.?i\.?d\.?|q8h)\b", re.I), 3.0),
    (re.compile(r"\b(twice\s+(a\s+)?day|two\s+times\s+(a\s+)?day|twice\s+daily|bid|bds|bd|b\.?i\.?d\.?|q12h)\b", re.I), 2.0),
    (re.compile(r"\b(once\s+(a\s+)?day|once\s+daily|every\s+day|one\s+time\s+(a\s+)?day|daily|od|qd|q\.?d\.?|hs|nocte|mane|at\s+bedtime|at\s+night)\b", re.I), 1.0),
)

_UNITS_RE = re.compile(
    r"\b(?P<count>\d+(?:\.\d+)?)\s*(tab|tabs|tablet|tablets|cap|caps|capsule|"
    r"capsules|pill|pills|puff|puffs|spray|sprays|drop|drops)\b",
    re.IGNORECASE,
)

# Lines that are page furniture rather than a prescribed item. Matching one of
# these skips the line before any network lookup is spent on it.
_NON_MEDICATION_RE = re.compile(
    r"^\s*(dr\.?|doctor|patient|name|age|sex|date|address|hospital|clinic|"
    r"reg(istration)?\.?\s*(no|number)|signature|diagnosis|advice|follow[\s-]?up|"
    r"tel|phone|email|www\.|http)\b",
    re.IGNORECASE,
)

# A leading "1." or "2)" numbers the item on the page; it is not a quantity.
# Stripped before dose parsing, because "4. Tab. Aspirin" otherwise reads as
# four tablets per dose.
#
# The second branch handles the punctuation being missing entirely, which OCR
# does routinely — a real scan produced "4 Tab Aspirin 75mg once daily". A bare
# leading number followed by a dosage form is genuinely ambiguous ("2 Tab X"
# could mean two tablets), but on a prescription it is overwhelmingly an item
# number, and the far more common way to write a quantity is after the drug
# name ("X 2 tabs BD"), which this does not touch. Because it is a judgement
# call, units stay flagged `assumed` rather than `parsed`, so the report shows
# "(assumed)" instead of presenting the number as something the page stated.
_FORM_WORDS = (
    r"tabs?|tablets?|caps?|capsules?|syp|syrup|susp|suspension|inj|injection|"
    r"oint|ointment|cream|drops?|sol|solution"
)
_LIST_MARKER_RE = re.compile(
    r"^\s*\(?\d{1,2}\s*"
    rf"(?:[.)\]]\s+|(?=(?:{_FORM_WORDS})\b))",
    re.IGNORECASE,
)

# Dosage-form prefixes a prescription puts before the drug name ("Tab. Dolo").
# Stripped so the name that reaches RxNorm is the drug, not the form.
_FORM_PREFIX_RE = re.compile(
    r"^\s*(tab|tabs|tablet|cap|caps|capsule|syp|syrup|susp|suspension|inj|"
    r"injection|oint|ointment|cream|drops?|sol|solution)\.?\s+",
    re.IGNORECASE,
)


@dataclass
class DetectedMedication:
    """One medication line read off a document.

    Shaped to satisfy everything `MedicationSafetyService` reads from a
    `UserMedication` — `id`, `rxcui`, `display_name`, `units_per_dose`,
    `doses_per_day`, `schedule_note`, `entry_source`, `concept` — without being
    one. Deliberately not an ORM object: an unsaved `UserMedication` risks
    being flushed into the user's real medication list by an unrelated commit,
    and an OCR guess must never become saved data on its own.
    """

    display_name: str
    line: str
    rxcui: Optional[str] = None
    concept: Optional[DrugConcept] = None
    units_per_dose: float = 1.0
    doses_per_day: float = 1.0
    schedule_note: Optional[str] = None
    entry_source: str = "ocr"
    matched_term: Optional[str] = None
    strength_text: Optional[str] = None
    strength_mg: Optional[float] = None
    frequency_source: str = "assumed"
    units_source: str = "assumed"
    # How confident we are that we read the *name* right. Separate from
    # `resolution_status`, which is about whether that name could be matched to
    # a product. Recognising "acetaminophen" from the curated table is certain
    # even when RxNorm has no branded product to offer for it.
    match_confidence: str = "low"
    # resolved | not_found | not_attempted. "not_attempted" means the per-
    # document lookup budget ran out, which is a different thing from "we
    # looked and found nothing" and is reported as such.
    resolution_status: str = "not_attempted"
    resolved_name: Optional[str] = None
    # Ingredients in the matched product that the page did not name. Non-empty
    # means the rules are running over more drugs than were prescribed.
    extra_ingredients: List[str] = field(default_factory=list)
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "line": self.line,
            "display_name": self.display_name,
            "matched_term": self.matched_term,
            "rxcui": self.rxcui,
            "resolved_name": self.resolved_name,
            "strength_text": self.strength_text,
            "strength_mg": self.strength_mg,
            "units_per_dose": self.units_per_dose,
            "doses_per_day": self.doses_per_day,
            "schedule_note": self.schedule_note,
            "frequency_source": self.frequency_source,
            "units_source": self.units_source,
            "match_confidence": self.match_confidence,
            "resolution_status": self.resolution_status,
            "extra_ingredients": self.extra_ingredients,
            "matched_product": self.resolved_name is not None,
        }


class PrescriptionPipelineService:
    """Forensics + medication safety over a single uploaded document."""

    def __init__(self, db_session, verification_service):
        self.session = db_session
        self.verification = verification_service
        self.drug_data = DrugDataService(db_session)
        self.safety = MedicationSafetyService(db_session)
        self.audit = AuditRepository(db_session)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def analyse(self, filepath: str, original_filename: str, user_id: str,
                ip_address: str = None, persist: bool = True) -> Dict[str, Any]:
        """Verify a document and check the medications printed on it.

        The forensics half runs first because it owns the OCR step; the safety
        half then reads the text it already produced.
        """
        start = time.time()

        record = self.verification.verify(
            filepath, original_filename, user_id=user_id, ip_address=ip_address,
        )
        text = record.extracted_text or ""

        detected = self.detect_medications(text)
        safety = self.safety.run_check_on(
            detected,
            user_id,
            ip_address=ip_address,
            persist=persist,
            source="prescription",
            verification_record_id=record.id,
            audit_action="PRESCRIPTION_PIPELINE_CHECK",
            provenance={
                "verification_record_id": str(record.id),
                "original_filename": original_filename,
                "document_status": record.status,
                "document_confidence": record.confidence,
                "pipeline_version": PIPELINE_VERSION,
                "medications_read_by": "OCR",
                "confirmed_by_user": False,
            },
        )

        elapsed_ms = int((time.time() - start) * 1000)
        self.audit.log(
            user_id=user_id,
            action='PRESCRIPTION_PIPELINE',
            resource_type='VerificationRecord',
            resource_id=record.id,
            ip_address=ip_address,
            model_version=PIPELINE_VERSION,
            details={
                "document_status": record.status,
                "medications_detected": len(detected),
                "medications_resolved": sum(1 for d in detected if d.rxcui),
                "highest_severity": safety["highest_severity"],
                "processing_time_ms": elapsed_ms,
            },
        )

        return {
            "pipeline_version": PIPELINE_VERSION,
            "processing_time_ms": elapsed_ms,
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
                "processing_time_ms": record.processing_time_ms,
            },
            "medications_detected": [d.as_dict() for d in detected],
            "safety": safety,
            "reading_caveat": self._reading_caveat(detected),
        }

    @staticmethod
    def _reading_caveat(detected: List["DetectedMedication"]) -> str:
        """State plainly how the checked list was obtained.

        This travels inside the result, next to the findings, for the same
        reason the medical caveat does: a screenshot of the findings alone must
        not read as a check of a confirmed list.
        """
        if not detected:
            return (
                "No medications could be read from this document, so no medication "
                "safety check was performed. The document verification result above "
                "still applies. If this is a prescription, enter the medications by "
                "hand to have them checked."
            )

        assumed = sum(1 for d in detected if d.frequency_source == "assumed")
        unresolved = sum(1 for d in detected if not d.rxcui)

        caveat = (
            f"These {len(detected)} medication(s) were read from the document by OCR "
            f"and have not been confirmed by anyone. Check every name, strength and "
            f"frequency against the original before relying on the findings below."
        )
        if assumed:
            caveat += (
                f" {assumed} of them state no frequency on the page, so once a day "
                f"was assumed — if the real frequency is higher, the daily totals "
                f"shown are too low."
            )
        if unresolved:
            caveat += (
                f" {unresolved} could not be matched to a known product and were "
                f"reported as unchecked rather than dropped."
            )

        unlooked = sum(1 for d in detected if d.resolution_status == "not_attempted")
        if unlooked:
            caveat += (
                f" {unlooked} of them were past this document's lookup limit and were "
                f"never looked up at all, so nothing about them has been checked."
            )

        widened = [d for d in detected if d.extra_ingredients]
        if widened:
            names = ", ".join(sorted({d.display_name for d in widened}))
            caveat += (
                f" For {names}, the closest product on file is a combination containing "
                f"ingredients this document did not name, so some findings below may "
                f"concern a drug that is not actually on this prescription. Check the "
                f"matched product against what was dispensed."
            )
        return caveat

    # ------------------------------------------------------------------
    # Medication extraction
    # ------------------------------------------------------------------

    def detect_medications(self, text: str) -> List[DetectedMedication]:
        """Read candidate medications out of OCR'd prescription text.

        Two passes, cheapest first. A line naming an ingredient already known
        to the platform is matched locally with no network call; only lines
        that look like a prescribed item but match nothing locally are sent to
        RxNorm.
        """
        if not (text or "").strip():
            return []

        lexicon = self._lexicon()
        pattern = self._lexicon_pattern(lexicon)

        detected: List[DetectedMedication] = []
        seen_keys: set = set()
        lookups = 0

        for raw_line in text.splitlines():
            if len(detected) >= MAX_DETECTED_MEDICATIONS:
                break

            line = _LIST_MARKER_RE.sub("", " ".join(raw_line.split()))
            if len(line) < MIN_LINE_LENGTH or _NON_MEDICATION_RE.match(line):
                continue

            strength = self._parse_strength(line)
            local = pattern.search(line) if pattern else None

            if local:
                key = normalise_ingredient_key(local.group(1))
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                name = lexicon.get(key, local.group(1))
                confidence = "high"
            elif strength:
                # Looks like a prescribed item (it carries a strength) but names
                # nothing known locally — worth an RxNorm lookup if budget allows.
                name = self._candidate_name(line)
                if not name:
                    continue
                key = normalise_ingredient_key(name)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                confidence = "medium"
            else:
                continue

            med = DetectedMedication(
                display_name=name,
                line=line,
                matched_term=local.group(1) if local else name,
                match_confidence=confidence,
                strength_text=strength["text"] if strength else None,
                strength_mg=strength["mg"] if strength else None,
            )
            self._apply_dosing(med, line)

            # Resolution is budgeted; detection is not. A line we cannot afford
            # to look up is still reported — as unresolved — because dropping
            # it would quietly shorten the list the rules then run over.
            if lookups < MAX_RXNORM_LOOKUPS:
                lookups += 1
                self._resolve(med, strength)

            detected.append(med)

        return detected

    # ------------------------------------------------------------------
    # Lexicon
    # ------------------------------------------------------------------

    def _lexicon(self) -> Dict[str, str]:
        """Ingredient names the platform already knows, keyed for matching.

        Drawn from the curated limit table, the interaction class table, and
        every ingredient cached from a previous RxNorm lookup — so the lexicon
        grows as the platform is used, with no separate dictionary to maintain.
        """
        names: Dict[str, str] = {}
        try:
            for row in self.session.query(
                IngredientLimit.ingredient_key, IngredientLimit.ingredient_name
            ).all():
                names[row[0]] = row[1]
            for row in self.session.query(
                DrugIngredient.ingredient_key, DrugIngredient.ingredient_name
            ).distinct().all():
                names.setdefault(row[0], row[1])
        except Exception as exc:      # a lexicon miss degrades to an RxNorm lookup
            logger.warning("Could not build ingredient lexicon: %s", exc)

        for key in INGREDIENT_CLASSES:
            names.setdefault(key, key)
        return names

    @staticmethod
    def _lexicon_pattern(lexicon: Dict[str, str]):
        """One alternation over every known ingredient, longest term first."""
        terms = [k for k in lexicon if k and len(k) >= 4]
        if not terms:
            return None
        terms.sort(key=len, reverse=True)
        return re.compile(
            r"\b(" + "|".join(re.escape(t) for t in terms) + r")\b", re.IGNORECASE
        )

    @staticmethod
    def _candidate_name(line: str) -> Optional[str]:
        """The probable drug name on a line that carries a strength.

        Everything before the first digit, minus the dosage-form prefix. On a
        line like "Tab. Dolo 650mg 1-0-1" that leaves "Dolo".
        """
        head = _FORM_PREFIX_RE.sub("", line)
        head = re.split(r"\d", head, maxsplit=1)[0]
        head = re.sub(r"[^A-Za-z\s\-]", " ", head)
        name = " ".join(head.split()).strip(" -")
        return name if len(name) >= 3 else None

    # ------------------------------------------------------------------
    # Dose and frequency
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_strength(line: str) -> Optional[Dict[str, Any]]:
        match = _STRENGTH_RE.search(line)
        if not match:
            return None
        unit = match.group("unit").upper()
        amount = float(match.group("amount"))
        factor = _UNIT_TO_MG.get(unit)
        return {
            "text": match.group(0),
            "amount": amount,
            "unit": unit,
            "mg": round(amount * factor, 6) if factor else None,
        }

    @staticmethod
    def _apply_dosing(med: DetectedMedication, line: str) -> None:
        """Read units-per-dose and doses-per-day off the line, if stated.

        Whether a value was read or defaulted is recorded on the medication.
        An assumed once-a-day is the conservative direction — it can only
        understate a daily total — and the pipeline says so in its caveat
        rather than letting the number stand unqualified.
        """
        numeric = _NUMERIC_SIG_RE.search(line)
        if numeric:
            slots = [float(g) for g in numeric.groups()]
            taken = [s for s in slots if s > 0]
            if taken:
                med.units_per_dose = max(taken)
                med.doses_per_day = float(len(taken))
                med.units_source = "parsed"
                med.frequency_source = "parsed"
                med.schedule_note = numeric.group(0)
                return

        units = _UNITS_RE.search(line)
        if units:
            count = float(units.group("count"))
            if 0 < count <= 20:
                med.units_per_dose = count
                med.units_source = "parsed"

        for pattern, per_day in _FREQUENCY_PATTERNS:
            hit = pattern.search(line)
            if hit:
                med.doses_per_day = per_day
                med.frequency_source = "parsed"
                med.schedule_note = hit.group(0)
                return

    # ------------------------------------------------------------------
    # RxNorm resolution
    # ------------------------------------------------------------------

    def _resolve(self, med: DetectedMedication, strength: Optional[Dict]) -> None:
        """Attach an RxNorm concept so the rule engine can see the ingredients.

        Failure is left in place, not papered over: an unresolved medication
        keeps `rxcui=None`, which the rule engine reports through RULE-GAP-01
        as an item it could not check.
        """
        # Search with the term as it appeared on the page, not the curated
        # display name. The limit table stores "Acetaminophen (paracetamol)",
        # and RxNorm matches nothing for a name carrying a parenthetical gloss.
        search_name = (med.matched_term or med.display_name or "").strip()
        if not search_name:
            self._mark_unresolved(med)
            return

        # Two queries, both always run and merged. The strength-qualified one is
        # more precise when RxNorm has an exact product; the plain name is what
        # actually returns the clean single-ingredient tablets, because RxNav
        # falls back to its approximate matcher for "acetaminophen 500 mg" and
        # that returns combination packs. Searching only the qualified form made
        # a plain paracetamol line resolve to a three-drug cold-and-flu pack.
        queries = []
        if strength and strength.get("unit"):
            queries.append(f"{search_name} {strength['amount']:g} {strength['unit'].lower()}")
        queries.append(search_name)

        try:
            hits, seen = [], set()
            for query in queries:
                for hit in self.drug_data.search_products(query, limit=8):
                    if hit["rxcui"] in seen:
                        continue
                    seen.add(hit["rxcui"])
                    hits.append(hit)
            if not hits:
                self._mark_unresolved(med)
                return

            concept = self._best_concept(
                hits,
                normalise_ingredient_key(search_name),
                strength.get("mg") if strength else None,
            )
            if concept is None:
                self._mark_unresolved(med)
                return

            med.rxcui = concept.rxcui
            med.concept = concept
            med.resolved_name = concept.name
            med.resolution_status = "resolved"

            # RxNorm may only offer a combination product for a line that named
            # one drug. The rules then run over ingredients the prescription
            # never mentioned, and a finding about one of them would be about a
            # drug the patient is not taking. We cannot invent a better product,
            # so we name the discrepancy instead of letting it pass unremarked.
            extra = sorted(
                {i.ingredient_key for i in concept.ingredients} - {normalise_ingredient_key(search_name)}
            )
            med.extra_ingredients = extra
        except Exception as exc:
            logger.warning("RxNorm resolution failed for %r: %s", search_name, exc)
            self._mark_unresolved(med)

    def _best_concept(self, hits: List[Dict[str, Any]], wanted_key: str,
                      wanted_mg: Optional[float] = None):
        """Pick the closest product among RxNorm's candidates.

        Taking the first hit blindly is wrong in a way that shows up directly in
        the findings: a search for "aspirin 75 mg" can return a combination
        product, and every extra ingredient in it then gets reported as a drug
        the patient is taking. Candidates are therefore ranked, in order, by:
        whether they contain the ingredient we searched for, whether they are a
        pack, how many ingredients they carry, and whether the strength matches
        the page. The plainest exact product wins.
        """
        # Rank candidates before spending a lookup on any of them. Only a
        # bounded number of concepts get fetched, so if the plain product is not
        # near the front it never gets considered at all — that is how
        # "acetaminophen 500 MG / methionine 250 MG" beat the plain tablet and
        # put methionine into the findings.
        #
        # RxNorm names combination products by joining ingredients with "/", so
        # counting slashes orders by ingredient count for free, with no network
        # call. Cheaper than fetching every concept, and it usually puts the
        # exact single-ingredient product first, where the short-circuit below
        # ends the search immediately.
        ordered = sorted(hits, key=lambda h: self._candidate_key(h, wanted_key))

        best, best_rank = None, None
        for hit in ordered[:8]:
            concept = self.drug_data.get_concept(hit["rxcui"])
            if concept is None or not concept.ingredients:
                continue

            keys = {i.ingredient_key for i in concept.ingredients}
            contains_wanted = wanted_key in keys if wanted_key else False
            is_pack = (concept.tty or "") in ("BPCK", "GPCK")
            strength_matches = wanted_mg is not None and any(
                i.strength_mg is not None
                and i.ingredient_key == wanted_key
                and abs(i.strength_mg - wanted_mg) < 0.01
                for i in concept.ingredients
            )
            # Sorts to: contains the searched ingredient, then not a pack, then
            # fewest ingredients. The pack penalty is applied again here and not
            # only in the pre-sort, because RxNorm's approximate matcher returns
            # candidates with no term type at all, which the pre-sort cannot
            # rank. A single-ingredient exact match short-circuits.
            rank = (not contains_wanted, is_pack, len(keys), not strength_matches)
            if best_rank is None or rank < best_rank:
                best, best_rank = concept, rank
            if contains_wanted and not is_pack and len(keys) == 1 and strength_matches:
                break
        return best

    @staticmethod
    def _candidate_key(hit: Dict[str, Any], wanted_key: str):
        """Order RxNorm candidates cheaply, from their names alone."""
        name = (hit.get("name") or "").lower()
        return (
            _TTY_RANK.get(hit.get("tty"), 3),          # single products before packs
            name.count("/"),                            # fewest ingredients
            0 if wanted_key and name.startswith(wanted_key) else 1,
            len(name),
        )

    @staticmethod
    def _mark_unresolved(med: DetectedMedication) -> None:
        """Record a failed lookup without rewriting how the name was read.

        A name taken from the curated ingredient table stays a certain read
        even when RxNorm offers no product for it — the two facts are reported
        separately rather than collapsed into one confidence score.
        """
        med.resolution_status = "not_found"
        if med.match_confidence != "high":
            med.match_confidence = "low"
