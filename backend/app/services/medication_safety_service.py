"""
Medication Safety Service — Module 2, Phase 1

A transparent, auditable rule engine over the user's medication list. It answers
two questions that account for most real-world consumer medication harm:

  1. Is the same active ingredient present in more than one product?
  2. Does the combined daily total of an ingredient reach its labeled maximum?

DESIGN CONSTRAINTS (enforced, not just documented)
--------------------------------------------------
* No machine-learned safety verdict. Every finding is produced by a named rule
  over sourced facts, and carries the rule id that fired.
* No finding may leave this module without at least one citation and a
  consult-a-professional caveat — `_finding()` raises if either is missing, so
  a future rule cannot accidentally ship an uncited claim.
* The tool never says "this is safe for you". It reports what it observed, what
  the label says, and who to ask. That framing is what keeps this an
  informational aid rather than clinical decision support.
* An unknown ingredient or an unparseable strength produces an explicit
  "cannot assess" finding. Silence would read as "checked and fine".
"""

import logging
import re
import time
import uuid
from typing import Any, Dict, List, Optional

from ..data.interaction_classes import CONTRAINDICATION_PHRASES, INGREDIENT_CLASSES
from ..database import db
from ..models import SafetyCheck, UserMedication
from ..repositories.audit_repository import AuditRepository
from .drug_data_service import DrugDataService

logger = logging.getLogger(__name__)

RULE_ENGINE_VERSION = "rules-v2"

SEVERITY_ORDER = {"none": 0, "info": 1, "moderate": 2, "high": 3}

# Attached verbatim to every finding. The spec requires the caveat to live
# inside the result, not only in page furniture that a screenshot can crop off.
CONSULT_CAVEAT = (
    "This is an informational check against published label data — not medical "
    "advice, and not a review of your personal medical history. Confirm with a "
    "pharmacist or doctor before changing anything you take."
)

# Fraction of the labeled maximum at which we raise an early warning rather
# than waiting for the limit to be crossed outright.
APPROACHING_LIMIT_RATIO = 0.8

# Phase 2 — interaction scanning.
#
# One openFDA label lookup happens per distinct ingredient, so a very long list
# is capped. The cap is reported through RULE-GAP-05 rather than applied
# silently: a list that was only partly scanned must never read as fully
# scanned.
MAX_INTERACTION_INGREDIENTS = 25

# Longest verbatim label sentence quoted back to the user in a finding.
MAX_EXCERPT_CHARS = 400

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

# A combination product's own warnings recite what is inside it ("each caplet
# contains acetaminophen"). Read literally that looks like drug A's label
# naming drug B, when it is really the label describing itself. Sentences that
# are plainly compositional are skipped so co-formulation is not misreported as
# an interaction — RULE-DUP-01 is what covers shared ingredients.
_COMPOSITION_RE = re.compile(
    r"\b(active ingredient|inactive ingredient|each (tablet|caplet|capsule|"
    r"softgel|dose|teaspoon|packet)|this product contains|contains\s+\d)",
    re.IGNORECASE,
)


class MedicationSafetyService:
    def __init__(self, db_session=None):
        self.session = db_session or db.session
        self.drug_data = DrugDataService(self.session)
        self.audit = AuditRepository(self.session)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run_check(self, user_id: str, ip_address: str = None,
                  persist: bool = True) -> Dict[str, Any]:
        """Run every rule over the user's saved medication list."""
        # JWT identities arrive as strings; the column is a native UUID.
        user_uuid = self._as_uuid(user_id)
        medications = (
            self.session.query(UserMedication)
            .filter_by(user_id=user_uuid, is_active=True)
            .order_by(UserMedication.created_at.asc())
            .all()
        ) if user_uuid else []

        return self.run_check_on(
            medications, user_id, ip_address=ip_address, persist=persist,
        )

    def run_check_on(self, medications: List[Any], user_id: str,
                     ip_address: str = None, persist: bool = True,
                     source: str = "list",
                     verification_record_id=None,
                     audit_action: str = "MEDICATION_SAFETY_CHECK",
                     provenance: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run every rule over an explicit medication list.

        Split out from `run_check` so Phase 3 can check a list read off a
        prescription without first writing it to the user's saved list. The
        rules themselves are identical either way — what changes is where the
        list came from, which travels with the result as `source` and
        `provenance` so a reader can tell a confirmed list from an OCR guess.

        `medications` only needs to *quack* like `UserMedication`: the rules
        read `id`, `rxcui`, `display_name`, `units_per_dose`, `doses_per_day`,
        `schedule_note`, `entry_source` and `concept`.
        """
        start = time.time()

        snapshot = [self._snapshot(m) for m in medications]
        ingredient_totals = self._aggregate_ingredients(medications)

        findings: List[Dict[str, Any]] = []
        interaction_findings, interaction_coverage = self._rule_interactions(ingredient_totals)
        findings.extend(self._rule_duplicate_ingredient(ingredient_totals))
        findings.extend(self._rule_cumulative_dose(ingredient_totals))
        findings.extend(interaction_findings)
        findings.extend(self._rule_unassessable(ingredient_totals))
        findings.extend(self._rule_interaction_gaps(interaction_coverage))

        findings.sort(key=lambda f: -SEVERITY_ORDER.get(f["severity"], 0))

        severity_summary = {"high": 0, "moderate": 0, "info": 0}
        for finding in findings:
            severity_summary[finding["severity"]] = severity_summary.get(finding["severity"], 0) + 1

        highest = "none"
        for finding in findings:
            if SEVERITY_ORDER[finding["severity"]] > SEVERITY_ORDER[highest]:
                highest = finding["severity"]

        sources_used = self._collect_sources(findings)
        elapsed_ms = int((time.time() - start) * 1000)

        result = {
            "medications_checked": snapshot,
            "findings": findings,
            "severity_summary": severity_summary,
            "highest_severity": highest,
            "sources_used": sources_used,
            "rule_engine_version": RULE_ENGINE_VERSION,
            "processing_time_ms": elapsed_ms,
            "disclaimer": CONSULT_CAVEAT,
            "source": source,
            "provenance": provenance,
        }

        if persist:
            check = self._persist(user_id, result, verification_record_id)
            result["check_id"] = str(check.id) if check else None
            # The audit trail records which data sources backed this result, so
            # a finding stays explainable long after the caches have rolled.
            self.audit.log(
                user_id=user_id,
                action=audit_action,
                resource_type='SafetyCheck',
                resource_id=check.id if check else None,
                ip_address=ip_address,
                model_version=RULE_ENGINE_VERSION,
                details={
                    "medication_count": len(snapshot),
                    "source": source,
                    "highest_severity": highest,
                    "severity_summary": severity_summary,
                    "sources_used": sources_used,
                    "rule_ids_fired": sorted({f["rule_id"] for f in findings}),
                    "processing_time_ms": elapsed_ms,
                },
            )

        return result

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def _aggregate_ingredients(self, medications: List[UserMedication]) -> Dict[str, Dict[str, Any]]:
        """Group the list by active ingredient and total the daily exposure.

        Daily mg for one product = strength per unit x units per dose x doses per day.
        """
        totals: Dict[str, Dict[str, Any]] = {}

        for med in medications:
            concept = med.concept
            if concept is None and med.rxcui:
                concept = self.drug_data.get_concept(med.rxcui)

            ingredients = list(concept.ingredients) if concept is not None else []

            if not ingredients:
                # Manually typed entry with no RxNorm match — we cannot see
                # inside it, and must say so rather than pass it silently.
                bucket = totals.setdefault("__unmatched__", {
                    "ingredient_key": "__unmatched__",
                    "ingredient_name": None,
                    "contributions": [],
                    "total_mg": 0.0,
                    "unmatched": True,
                })
                bucket["contributions"].append({
                    "medication_id": str(med.id),
                    "product": med.display_name,
                    "daily_mg": None,
                    "reason": "No RxNorm match for this entry",
                })
                continue

            per_day = float(med.units_per_dose or 1) * float(med.doses_per_day or 1)

            for ing in ingredients:
                bucket = totals.setdefault(ing.ingredient_key, {
                    "ingredient_key": ing.ingredient_key,
                    "ingredient_name": ing.ingredient_name,
                    "contributions": [],
                    "total_mg": 0.0,
                    "unmatched": False,
                })
                daily_mg = round(ing.strength_mg * per_day, 3) if ing.strength_mg else None
                if daily_mg is not None:
                    bucket["total_mg"] = round(bucket["total_mg"] + daily_mg, 3)
                bucket["contributions"].append({
                    "medication_id": str(med.id),
                    "product": med.display_name,
                    "strength_mg": ing.strength_mg,
                    "units_per_dose": float(med.units_per_dose or 1),
                    "doses_per_day": float(med.doses_per_day or 1),
                    "daily_mg": daily_mg,
                    "reason": None if daily_mg is not None else "Strength not published in a milligram unit",
                })

        return totals

    # ------------------------------------------------------------------
    # Rules
    # ------------------------------------------------------------------

    def _rule_duplicate_ingredient(self, totals: Dict[str, Dict]) -> List[Dict[str, Any]]:
        """RULE-DUP-01 — the same active ingredient in two or more products."""
        findings = []

        for key, bucket in totals.items():
            if bucket.get("unmatched"):
                continue
            products = {c["product"] for c in bucket["contributions"]}
            if len(products) < 2:
                continue

            name = bucket["ingredient_name"]
            limit = self.drug_data.get_limit(key)
            citations = [limit.citation()] if limit else []
            citations.append({
                "source": "RxNorm (US National Library of Medicine)",
                "url": "https://www.nlm.nih.gov/research/umls/rxnorm/",
                "excerpt": "Ingredient composition for these products resolved via RxNorm concepts.",
            })

            product_list = ", ".join(sorted(products))
            message = (
                f"{product_list} all contain {name}. People often take combination "
                f"products without realising they share an ingredient, which makes the "
                f"daily total add up faster than expected."
            )
            if bucket["total_mg"]:
                message += f" Combined, they come to about {self._fmt_mg(bucket['total_mg'])} of {name} a day."

            findings.append(self._finding(
                rule_id="RULE-DUP-01",
                severity="moderate",
                title=f"{name} appears in {len(products)} products",
                message=message,
                ingredient=name,
                products=sorted(products),
                evidence={
                    "ingredient_key": key,
                    "product_count": len(products),
                    "combined_daily_mg": bucket["total_mg"] or None,
                    "contributions": bucket["contributions"],
                },
                citations=citations,
            ))

        return findings

    def _rule_cumulative_dose(self, totals: Dict[str, Dict]) -> List[Dict[str, Any]]:
        """RULE-DOSE-01 — combined daily total against the labeled maximum."""
        findings = []

        for key, bucket in totals.items():
            if bucket.get("unmatched") or not bucket["total_mg"]:
                continue

            limit = self.drug_data.get_limit(key)
            if limit is None or not limit.max_daily_mg:
                continue

            total = bucket["total_mg"]
            ratio = total / limit.max_daily_mg
            if ratio < APPROACHING_LIMIT_RATIO:
                continue

            name = bucket["ingredient_name"]
            products = sorted({c["product"] for c in bucket["contributions"]})
            citations = [limit.citation()]

            # Attach the verbatim label text so the user can read the source
            # rather than take our word for the number.
            excerpt = self.drug_data.fetch_label_excerpt(name)
            if excerpt:
                citations.append(excerpt)

            if ratio >= 1.0:
                severity = "high"
                title = f"{name} total may exceed the labeled daily maximum"
                message = (
                    f"Taken as entered, {' and '.join(products)} come to about "
                    f"{self._fmt_mg(total)} of {name} a day. The labeled maximum for "
                    f"self-care is {self._fmt_mg(limit.max_daily_mg)}."
                )
            else:
                severity = "moderate"
                title = f"{name} total is close to the labeled daily maximum"
                message = (
                    f"Taken as entered, {' and '.join(products)} come to about "
                    f"{self._fmt_mg(total)} of {name} a day — around "
                    f"{int(ratio * 100)}% of the {self._fmt_mg(limit.max_daily_mg)} "
                    f"labeled maximum, leaving little room for another dose."
                )

            if limit.caution_note:
                message += f" {limit.caution_note}"

            findings.append(self._finding(
                rule_id="RULE-DOSE-01",
                severity=severity,
                title=title,
                message=message,
                ingredient=name,
                products=products,
                evidence={
                    "ingredient_key": key,
                    "combined_daily_mg": total,
                    "labeled_max_daily_mg": limit.max_daily_mg,
                    "percent_of_max": round(ratio * 100, 1),
                    "contributions": bucket["contributions"],
                },
                citations=citations,
            ))

        return findings

    def _rule_unassessable(self, totals: Dict[str, Dict]) -> List[Dict[str, Any]]:
        """RULE-GAP-01/02/03 — say plainly what could not be checked.

        A quiet result must never be mistaken for a clean one.
        """
        findings = []

        unmatched = totals.get("__unmatched__")
        if unmatched:
            products = sorted({c["product"] for c in unmatched["contributions"]})
            findings.append(self._finding(
                rule_id="RULE-GAP-01",
                severity="info",
                title=f"{len(products)} item(s) could not be checked",
                message=(
                    f"{', '.join(products)} could not be matched to a known product, so "
                    f"its ingredients are unknown to this tool and it was left out of the "
                    f"duplicate and dose checks. Try searching for it by name, or ask a "
                    f"pharmacist to review it with you."
                ),
                ingredient=None,
                products=products,
                evidence={"contributions": unmatched["contributions"]},
                citations=[{
                    "source": "RxNorm (US National Library of Medicine)",
                    "url": "https://www.nlm.nih.gov/research/umls/rxnorm/",
                    "excerpt": "No matching RxNorm concept was found for this entry.",
                }],
            ))

        for key, bucket in totals.items():
            if key == "__unmatched__" or bucket.get("unmatched"):
                continue

            name = bucket["ingredient_name"]
            no_strength = [c for c in bucket["contributions"] if c.get("daily_mg") is None]
            limit = self.drug_data.get_limit(key)

            if no_strength:
                products = sorted({c["product"] for c in no_strength})
                findings.append(self._finding(
                    rule_id="RULE-GAP-02",
                    severity="info",
                    title=f"Dose total not calculated for {name}",
                    message=(
                        f"{', '.join(products)} contains {name}, but its strength is not "
                        f"published in a milligram unit that this tool can add up (liquids "
                        f"and sprays are often listed this way). The duplicate check still "
                        f"applies; the daily-total check does not."
                    ),
                    ingredient=name,
                    products=products,
                    evidence={"ingredient_key": key, "contributions": no_strength},
                    citations=[{
                        "source": "RxNorm (US National Library of Medicine)",
                        "url": "https://www.nlm.nih.gov/research/umls/rxnorm/",
                        "excerpt": f"No milligram-based strength published for {name} in these products.",
                    }],
                ))

            elif limit is None and bucket["total_mg"]:
                findings.append(self._finding(
                    rule_id="RULE-GAP-03",
                    severity="info",
                    title=f"No published daily limit on file for {name}",
                    message=(
                        f"Your list comes to about {self._fmt_mg(bucket['total_mg'])} of "
                        f"{name} a day. This tool has no labeled daily maximum on file for "
                        f"{name}, so it cannot tell you whether that total is within the "
                        f"labeled range. A pharmacist can check the product label with you."
                    ),
                    ingredient=name,
                    products=sorted({c["product"] for c in bucket["contributions"]}),
                    evidence={
                        "ingredient_key": key,
                        "combined_daily_mg": bucket["total_mg"],
                        "labeled_max_daily_mg": None,
                    },
                    citations=[{
                        "source": "MedVerify curated limit table",
                        "url": None,
                        "excerpt": (
                            f"No entry for '{key}'. Limits are curated from FDA OTC "
                            f"monographs and approved labels; absence means unknown, not safe."
                        ),
                    }],
                ))

        return findings

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _finding(rule_id: str, severity: str, title: str, message: str,
                 ingredient: Optional[str], products: List[str],
                 evidence: Dict[str, Any], citations: List[Dict]) -> Dict[str, Any]:
        """Build a finding, refusing to emit one that is not properly sourced.

        This guard is the enforcement point for the project's non-negotiable
        rule: nothing user-facing ships without a citation and a caveat.
        """
        if severity not in SEVERITY_ORDER or severity == "none":
            raise ValueError(f"Invalid finding severity: {severity}")
        if not citations or not any(c.get("source") for c in citations):
            raise ValueError(f"Finding {rule_id} has no source citation")

        return {
            "rule_id": rule_id,
            "severity": severity,
            "title": title,
            "message": message,
            "ingredient": ingredient,
            "products": products,
            "evidence": evidence,
            "citations": citations,
            "caveat": CONSULT_CAVEAT,
        }

    @staticmethod
    def _as_uuid(value) -> Optional[uuid.UUID]:
        try:
            return uuid.UUID(str(value))
        except (ValueError, TypeError, AttributeError):
            return None

    @staticmethod
    def _fmt_mg(value: Optional[float]) -> str:
        if value is None:
            return "an unknown amount"
        if value >= 1000 and float(value).is_integer():
            return f"{int(value):,} mg"
        return f"{round(value, 2):g} mg"

    @staticmethod
    def _snapshot(med: UserMedication) -> Dict[str, Any]:
        concept = med.concept
        return {
            "medication_id": str(med.id),
            "display_name": med.display_name,
            "rxcui": med.rxcui,
            "units_per_dose": float(med.units_per_dose or 1),
            "doses_per_day": float(med.doses_per_day or 1),
            "schedule_note": med.schedule_note,
            "entry_source": med.entry_source,
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

    @staticmethod
    def _collect_sources(findings: List[Dict]) -> List[Dict[str, Any]]:
        seen, sources = set(), []
        for finding in findings:
            for citation in finding.get("citations", []):
                marker = (citation.get("source"), citation.get("url"))
                if marker in seen:
                    continue
                seen.add(marker)
                sources.append({
                    "source": citation.get("source"),
                    "url": citation.get("url"),
                    "label_id": citation.get("label_id"),
                    "retrieved_at": citation.get("retrieved_at"),
                })
        return sources

    def _persist(self, user_id: str, result: Dict[str, Any],
                 verification_record_id=None) -> Optional[SafetyCheck]:
        try:
            check = SafetyCheck(
                user_id=self._as_uuid(user_id),
                verification_record_id=verification_record_id,
                source=result.get("source", "list"),
                medication_snapshot=result["medications_checked"],
                findings=result["findings"],
                severity_summary=result["severity_summary"],
                highest_severity=result["highest_severity"],
                sources_used=result["sources_used"],
                rule_engine_version=RULE_ENGINE_VERSION,
                processing_time_ms=result["processing_time_ms"],
            )
            self.session.add(check)
            self.session.commit()
            return check
        except Exception as exc:
            logger.error("Failed to persist safety check: %s", exc)
            self.session.rollback()
            return None

    def list_checks(self, user_id: str, limit: int = 20) -> List[SafetyCheck]:
        return (
            self.session.query(SafetyCheck)
            .filter_by(user_id=self._as_uuid(user_id))
            .order_by(SafetyCheck.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_check(self, check_id: str, user_id: str) -> Optional[SafetyCheck]:
        check_uuid, user_uuid = self._as_uuid(check_id), self._as_uuid(user_id)
        if check_uuid is None or user_uuid is None:
            return None
        return (
            self.session.query(SafetyCheck)
            .filter_by(id=check_uuid, user_id=user_uuid)
            .first()
        )

    # ------------------------------------------------------------------
    # Phase 2 — drug–drug interactions (RULE-INT-01, RULE-GAP-04/05)
    # ------------------------------------------------------------------

    def _rule_interactions(self, totals: Dict[str, Dict]):
        """RULE-INT-01 — one drug's own label warns about another on the list.

        NLM retired the RxNav interaction API in January 2024, so there is no
        longer a public endpoint that answers "do A and B interact?". What is
        still published is the label text itself. This rule therefore does the
        only honest thing available: it reads each ingredient's openFDA label
        and reports, verbatim, where that label warns about something else the
        user is taking. The claim it makes is "this label says X", which is
        checkable, rather than "these drugs interact", which would be a
        clinical judgement this module does not make.

        Returns `(findings, coverage)`; coverage drives the gap rules so an
        ingredient whose label could not be read is reported rather than
        quietly dropped.
        """
        buckets = {
            key: bucket for key, bucket in totals.items()
            if key != "__unmatched__" and not bucket.get("unmatched")
            and bucket.get("ingredient_name")
        }
        coverage = {"scanned": [], "no_label": [], "no_interaction_text": [], "skipped": []}

        # An interaction needs two sides. One ingredient is not a quiet pass —
        # there is simply no pair to check, and the gap rules stay silent too.
        if len(buckets) < 2:
            return [], coverage

        ordered = sorted(buckets.values(), key=lambda b: b["ingredient_key"])
        scanned = ordered[:MAX_INTERACTION_INGREDIENTS]
        coverage["skipped"] = [b["ingredient_name"] for b in ordered[MAX_INTERACTION_INGREDIENTS:]]

        labels: Dict[str, Dict[str, Any]] = {}
        for bucket in scanned:
            payload = self.drug_data.fetch_interaction_sections(bucket["ingredient_name"])
            if payload is None:
                coverage["no_label"].append(bucket["ingredient_name"])
            elif not payload.get("sections"):
                coverage["no_interaction_text"].append(bucket["ingredient_name"])
            else:
                labels[bucket["ingredient_key"]] = payload
                coverage["scanned"].append(bucket["ingredient_name"])

        # Scan every ordered pair. Both directions are kept: a warning that
        # appears on both labels is stronger evidence than one that appears on
        # only one, and the finding shows both.
        pairs: Dict[frozenset, Dict[str, Any]] = {}
        for source in scanned:
            payload = labels.get(source["ingredient_key"])
            if payload is None:
                continue
            for target in scanned:
                if target["ingredient_key"] == source["ingredient_key"]:
                    continue
                for hit in self._scan_sections(payload["sections"], target):
                    entry = pairs.setdefault(
                        frozenset((source["ingredient_key"], target["ingredient_key"])),
                        {"keys": sorted((source["ingredient_key"], target["ingredient_key"])),
                         "mentions": []},
                    )
                    entry["mentions"].append({
                        **hit,
                        "warned_on_label_of": source["ingredient_name"],
                        "warns_about": target["ingredient_name"],
                        "label_id": payload.get("label_id"),
                        "label_url": payload.get("url"),
                        "brand_name": payload.get("brand_name"),
                        "retrieved_at": payload.get("retrieved_at"),
                    })

        findings = []
        for entry in sorted(pairs.values(), key=lambda e: e["keys"]):
            findings.append(self._interaction_finding(entry, buckets))
        return findings, coverage

    def _interaction_finding(self, entry: Dict[str, Any],
                             buckets: Dict[str, Dict]) -> Dict[str, Any]:
        """Turn one ingredient pair's label mentions into a sourced finding."""
        # Strongest evidence first: an outright "do not take" beats a general
        # caution, and a label naming the drug beats one naming its class.
        mentions = sorted(
            entry["mentions"],
            key=lambda m: (
                not m["contraindication"],
                m["match_type"] != "ingredient",
                len(m["sentence"]),
            ),
        )
        primary = mentions[0]
        contraindicated = any(m["contraindication"] for m in mentions)

        left, right = (buckets[k] for k in entry["keys"])
        name_a, name_b = left["ingredient_name"], right["ingredient_name"]
        products = sorted(
            {c["product"] for c in left["contributions"]}
            | {c["product"] for c in right["contributions"]}
        )

        section_label = primary["section"].replace("_", " ").capitalize()
        if primary["match_type"] == "ingredient":
            basis = (
                f"The {primary['warned_on_label_of']} label names "
                f"{primary['warns_about']} directly, under “{section_label}”:"
            )
        else:
            basis = (
                f"The {primary['warned_on_label_of']} label warns about "
                f"“{primary['matched_term']}” — the class "
                f"{primary['warns_about']} belongs to — under “{section_label}”:"
            )

        message = f"{basis} “{primary['sentence']}”"
        if contraindicated:
            message += (
                " That is do-not-combine wording on the label itself, which is why "
                "this is flagged at the highest level."
            )
        if len(mentions) > 1:
            message += f" {len(mentions)} label passages mention this pairing."
        message += (
            " openFDA does not publish an interaction severity grade, so this "
            "ranking reflects the label's own wording, not a clinical severity "
            "rating. Ask a pharmacist whether it applies to you."
        )

        citations = [{
            "source": "openFDA drug label",
            "label_id": primary.get("label_id"),
            "url": primary.get("label_url"),
            "excerpt": primary["sentence"],
            "section": primary["section"],
            "retrieved_at": primary.get("retrieved_at"),
        }]

        return self._finding(
            rule_id="RULE-INT-01",
            severity="high" if contraindicated else "moderate",
            title=f"{name_a} and {name_b} are named together on a label",
            message=message,
            ingredient=name_a,
            products=products,
            evidence={
                "ingredient_keys": entry["keys"],
                "ingredients": [name_a, name_b],
                "match_type": primary["match_type"],
                "matched_term": primary["matched_term"],
                "contraindication_wording": contraindicated,
                "mention_count": len(mentions),
                "mentions": mentions[:5],
            },
            citations=citations,
        )

    @staticmethod
    def _rule_interaction_gaps(coverage: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """RULE-GAP-04/05 — name the ingredients the interaction scan could not cover."""
        findings = []

        unreadable = sorted(set(coverage["no_label"]) | set(coverage["no_interaction_text"]))
        if unreadable:
            findings.append(MedicationSafetyService._finding(
                rule_id="RULE-GAP-04",
                severity="info",
                title=f"Interactions not checked for {len(unreadable)} ingredient(s)",
                message=(
                    f"No openFDA label with interaction text could be read for "
                    f"{', '.join(unreadable)}, so this tool could not check "
                    f"{'them' if len(unreadable) > 1 else 'it'} against the rest of your "
                    f"list. That is a gap in the data, not a clean result — a "
                    f"pharmacist can review these against everything else you take."
                ),
                ingredient=None,
                products=[],
                evidence={
                    "no_label_found": sorted(set(coverage["no_label"])),
                    "label_without_interaction_text": sorted(set(coverage["no_interaction_text"])),
                },
                citations=[{
                    "source": "openFDA drug label",
                    "url": "https://open.fda.gov/apis/drug/label/",
                    "excerpt": (
                        "No published label section carrying interaction text was "
                        "available for these ingredients at the time of this check."
                    ),
                }],
            ))

        if coverage["skipped"]:
            findings.append(MedicationSafetyService._finding(
                rule_id="RULE-GAP-05",
                severity="info",
                title="Interaction check stopped at the ingredient limit",
                message=(
                    f"This list resolves to more than {MAX_INTERACTION_INGREDIENTS} distinct "
                    f"active ingredients, so the interaction scan covered the first "
                    f"{MAX_INTERACTION_INGREDIENTS} and left out "
                    f"{', '.join(sorted(set(coverage['skipped'])))}. A list this long is "
                    f"worth reviewing with a pharmacist in full rather than in part."
                ),
                ingredient=None,
                products=[],
                evidence={
                    "ingredient_cap": MAX_INTERACTION_INGREDIENTS,
                    "not_scanned": sorted(set(coverage["skipped"])),
                },
                citations=[{
                    "source": "MedVerify rule engine",
                    "url": None,
                    "excerpt": (
                        f"Interaction scanning is capped at {MAX_INTERACTION_INGREDIENTS} "
                        f"ingredients per check; the remainder are reported as unscanned."
                    ),
                }],
            ))

        return findings

    @staticmethod
    def _scan_sections(sections: List[Dict[str, str]],
                       target: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find sentences in one label that name `target` or its drug class."""
        key = target["ingredient_key"]
        name = (target["ingredient_name"] or "").strip().lower()
        ingredient_terms = {t for t in (key, name) if t}
        class_terms = {t.lower() for t in INGREDIENT_CLASSES.get(key, [])} - ingredient_terms

        hits, seen = [], set()
        for section in sections:
            for sentence in _SENTENCE_SPLIT_RE.split(section.get("text") or ""):
                sentence = sentence.strip()
                if not sentence or _COMPOSITION_RE.search(sentence):
                    continue

                lowered = sentence.lower()
                term = MedicationSafetyService._first_term(lowered, ingredient_terms)
                match_type = "ingredient"
                if term is None:
                    term = MedicationSafetyService._first_term(lowered, class_terms)
                    match_type = "class"
                if term is None:
                    continue

                marker = (section["section"], lowered[:120])
                if marker in seen:
                    continue
                seen.add(marker)

                hits.append({
                    "section": section["section"],
                    "sentence": sentence[:MAX_EXCERPT_CHARS],
                    "match_type": match_type,
                    "matched_term": term,
                    "contraindication": any(p in lowered for p in CONTRAINDICATION_PHRASES),
                })
        return hits

    @staticmethod
    def _first_term(text: str, terms) -> Optional[str]:
        """Longest whole-word term present in `text`, or None.

        Longest-first so "cns depressant" is reported rather than a shorter
        term that happens to sit inside it.
        """
        for term in sorted(terms, key=len, reverse=True):
            if re.search(rf"\b{re.escape(term)}\b", text):
                return term
        return None
