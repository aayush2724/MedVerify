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
import time
import uuid
from typing import Any, Dict, List, Optional

from ..database import db
from ..models import SafetyCheck, UserMedication
from ..repositories.audit_repository import AuditRepository
from .drug_data_service import DrugDataService

logger = logging.getLogger(__name__)

RULE_ENGINE_VERSION = "rules-v1"

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
        """Run every Phase-1 rule over the user's active medication list."""
        start = time.time()

        # JWT identities arrive as strings; the column is a native UUID.
        user_uuid = self._as_uuid(user_id)
        medications = (
            self.session.query(UserMedication)
            .filter_by(user_id=user_uuid, is_active=True)
            .order_by(UserMedication.created_at.asc())
            .all()
        ) if user_uuid else []

        snapshot = [self._snapshot(m) for m in medications]
        ingredient_totals = self._aggregate_ingredients(medications)

        findings: List[Dict[str, Any]] = []
        findings.extend(self._rule_duplicate_ingredient(ingredient_totals))
        findings.extend(self._rule_cumulative_dose(ingredient_totals))
        findings.extend(self._rule_unassessable(ingredient_totals))

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
        }

        if persist:
            check = self._persist(user_id, result)
            result["check_id"] = str(check.id) if check else None
            # The audit trail records which data sources backed this result, so
            # a finding stays explainable long after the caches have rolled.
            self.audit.log(
                user_id=user_id,
                action='MEDICATION_SAFETY_CHECK',
                resource_type='SafetyCheck',
                resource_id=check.id if check else None,
                ip_address=ip_address,
                model_version=RULE_ENGINE_VERSION,
                details={
                    "medication_count": len(snapshot),
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

    def _persist(self, user_id: str, result: Dict[str, Any]) -> Optional[SafetyCheck]:
        try:
            check = SafetyCheck(
                user_id=self._as_uuid(user_id),
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
