"""
Drug Data Service — Module 2 (Medication Safety Check)

Thin, cached client over the public drug-data sources the safety rule engine
cites:

  * RxNorm / RxNav (NLM)  — product search, and the active-ingredient
    breakdown with per-unit strength (via SCDC concepts).
  * openFDA drug label    — verbatim label text used as the citation attached
    to a finding.

Every outbound call is written through `ExternalApiCache`, so repeated lookups
never touch the network and the module keeps working (on cached data) when an
upstream API is unreachable. Nothing here makes a safety judgement — it only
supplies sourced facts to `medication_safety_service`.
"""

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

from ..database import db
from ..models import DrugConcept, DrugIngredient, ExternalApiCache, IngredientLimit

logger = logging.getLogger(__name__)

RXNAV_BASE = "https://rxnav.nlm.nih.gov/REST"
OPENFDA_LABEL_URL = "https://api.fda.gov/drug/label.json"

# Product data is stable; label text changes rarely. Long TTLs keep the hot
# path off the network entirely.
CONCEPT_TTL = timedelta(days=30)
CACHE_TTL = timedelta(days=7)
REQUEST_TIMEOUT = 8

# Product term types worth showing a consumer, in preference order. Single
# products first, packs (BPCK/GPCK) last: a pack bundles several products, so
# it is rarely what someone means by one line on a prescription or one entry on
# their list. `search_products` walks this tuple in order rather than the order
# RxNav happens to return its groups in — RxNav puts pack groups first, which
# without this filled the whole result page with cold-and-flu packs before a
# plain "acetaminophen 500 MG Oral Tablet" was ever reached.
_PRODUCT_TTYS = ("SCD", "SBD", "BPCK", "GPCK")

# Mass units RxNorm uses, normalised to milligrams. Volume/activity units
# (ML, UNT, %) intentionally map to None — a cumulative-dose comparison against
# a mg limit is only meaningful for mass.
_UNIT_TO_MG = {
    "MG": 1.0,
    "G": 1000.0,
    "GM": 1000.0,
    "MCG": 0.001,
    "UG": 0.001,
}

_STRENGTH_RE = re.compile(
    r"^(?P<name>.+?)\s+(?P<amount>\d+(?:\.\d+)?)\s*(?P<unit>MG|MCG|UG|G|GM|ML|UNT|%)\b",
    re.IGNORECASE,
)


def normalise_ingredient_key(name: str) -> str:
    """Collapse an ingredient name to a stable match key.

    RxNorm names the same moiety several ways ("acetaminophen",
    "Acetaminophen"), and salt forms ("diphenhydramine hydrochloride") must
    still collide with the base ingredient so a duplicate is actually caught.
    """
    key = (name or "").strip().lower()
    key = re.sub(r"\s+", " ", key)
    # Strip common salt/hydrate suffixes so salt forms match the base moiety.
    key = re.sub(
        r"\b(hydrochloride|hydrobromide|bitartrate|maleate|sulfate|sulphate|"
        r"citrate|tartrate|succinate|fumarate|besylate|mesylate|sodium|"
        r"potassium|calcium|magnesium|monohydrate|dihydrate|anhydrous)\b",
        "",
        key,
    )
    return re.sub(r"\s+", " ", key).strip()


def _product_rank(name: str, term_key: str):
    """Order products within one term type, from the name alone.

    RxNorm names a combination product by joining its ingredients with "/", so
    counting slashes orders by ingredient count without a second API call.

    This matters because RxNav returns its concepts in its own order and a
    `limit` truncates whatever arrives first. A search for "acetaminophen"
    otherwise returns eight oxycodone and cold-and-flu combinations and never
    reaches the plain paracetamol tablet — which is both a poor autocomplete
    for someone adding their own medication, and how the prescription pipeline
    ended up resolving a plain paracetamol line to a combination product and
    reporting drugs the patient was not taking.
    """
    lowered = (name or "").lower()
    return (
        lowered.count("/"),                              # fewest ingredients first
        0 if term_key and lowered.startswith(term_key) else 1,
        len(lowered),                                    # then the plainest name
    )


class DrugDataService:
    def __init__(self, db_session=None):
        self.session = db_session or db.session

    # ------------------------------------------------------------------
    # Cache plumbing
    # ------------------------------------------------------------------

    def _cache_get(self, cache_key: str, ttl: timedelta) -> Optional[Any]:
        row = self.session.get(ExternalApiCache, cache_key)
        if row is None:
            return None
        fetched = row.fetched_at
        if fetched is not None:
            if fetched.tzinfo is None:
                fetched = fetched.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - fetched > ttl:
                return None
        return row.payload

    def _cache_put(self, cache_key: str, provider: str, payload: Any, status: str = "OK") -> None:
        try:
            row = self.session.get(ExternalApiCache, cache_key)
            if row is None:
                row = ExternalApiCache(cache_key=cache_key, provider=provider)
                self.session.add(row)
            row.payload = payload
            row.status = status
            row.provider = provider
            row.fetched_at = datetime.now(timezone.utc)
            self.session.commit()
        except Exception as exc:  # cache writes must never break a request
            logger.warning("Could not write API cache for %s: %s", cache_key, exc)
            self.session.rollback()

    def _get_json(self, url: str, params: Dict[str, Any], provider: str,
                  ttl: timedelta = CACHE_TTL) -> Optional[dict]:
        """Cached GET. Returns None when the call fails and nothing is cached."""
        cache_key = f"{provider}:{url}?{json.dumps(params, sort_keys=True)}"
        cached = self._cache_get(cache_key, ttl)
        if cached is not None:
            return cached

        try:
            resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 404:
                self._cache_put(cache_key, provider, {}, status="EMPTY")
                return {}
            resp.raise_for_status()
            data = resp.json()
            self._cache_put(cache_key, provider, data)
            return data
        except Exception as exc:
            logger.warning("%s lookup failed (%s): %s", provider, url, exc)
            # Fall back to a stale cache entry rather than losing the feature.
            stale = self.session.get(ExternalApiCache, cache_key)
            return stale.payload if stale is not None else None

    # ------------------------------------------------------------------
    # RxNorm — product search
    # ------------------------------------------------------------------

    def search_products(self, term: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Autocomplete against RxNorm. Returns consumer-facing product rows."""
        term = (term or "").strip()
        if len(term) < 2:
            return []

        results: List[Dict[str, Any]] = []
        seen = set()

        data = self._get_json(f"{RXNAV_BASE}/drugs.json", {"name": term}, "rxnav") or {}

        # Index the response by term type first, then walk _PRODUCT_TTYS in our
        # own preference order. Consuming the groups in response order instead
        # lets whichever type RxNav returns first exhaust `limit`.
        by_tty: Dict[str, List[dict]] = {}
        for group in (data.get("drugGroup") or {}).get("conceptGroup") or []:
            if group.get("tty") in _PRODUCT_TTYS:
                by_tty.setdefault(group["tty"], []).extend(
                    group.get("conceptProperties") or []
                )

        term_key = term.lower()
        for tty in _PRODUCT_TTYS:
            group = sorted(
                by_tty.get(tty, []),
                key=lambda prop: _product_rank(prop.get("name"), term_key),
            )
            for prop in group:
                rxcui = prop.get("rxcui")
                if not rxcui or rxcui in seen:
                    continue
                seen.add(rxcui)
                results.append({
                    "rxcui": rxcui,
                    "name": prop.get("name"),
                    "synonym": prop.get("synonym") or None,
                    "tty": tty,
                    "is_branded": tty in ("SBD", "BPCK"),
                    "source": "RxNorm",
                })
                if len(results) >= limit:
                    break
            if len(results) >= limit:
                break

        # Exact-name search misses misspellings and brand shorthand; the
        # approximate matcher covers those.
        if len(results) < limit:
            approx = self._get_json(
                f"{RXNAV_BASE}/approximateTerm.json",
                {"term": term, "maxEntries": limit},
                "rxnav",
            ) or {}
            for cand in (approx.get("approximateGroup") or {}).get("candidate") or []:
                rxcui = cand.get("rxcui")
                name = cand.get("name")
                if not rxcui or not name or rxcui in seen:
                    continue
                seen.add(rxcui)
                results.append({
                    "rxcui": rxcui,
                    "name": name,
                    "synonym": None,
                    "tty": None,
                    "is_branded": False,
                    "source": "RxNorm (approximate match)",
                })
                if len(results) >= limit:
                    break

        return results[:limit]

    # ------------------------------------------------------------------
    # RxNorm — ingredient breakdown
    # ------------------------------------------------------------------

    def get_concept(self, rxcui: str, force_refresh: bool = False) -> Optional[DrugConcept]:
        """Return a cached `DrugConcept` with ingredients, fetching if needed."""
        rxcui = str(rxcui).strip()
        if not rxcui:
            return None

        concept = self.session.get(DrugConcept, rxcui)
        if concept is not None and not force_refresh:
            refreshed = concept.refreshed_at
            if refreshed is not None and refreshed.tzinfo is None:
                refreshed = refreshed.replace(tzinfo=timezone.utc)
            if refreshed is None or datetime.now(timezone.utc) - refreshed <= CONCEPT_TTL:
                if concept.ingredients:
                    return concept

        props = self._get_json(
            f"{RXNAV_BASE}/rxcui/{rxcui}/properties.json", {}, "rxnav", ttl=CONCEPT_TTL
        ) or {}
        prop = props.get("properties") or {}
        name = prop.get("name")
        if not name and concept is None:
            return None

        if concept is None:
            concept = DrugConcept(rxcui=rxcui, name=name or rxcui)
            self.session.add(concept)

        if name:
            concept.name = name
        concept.tty = prop.get("tty") or concept.tty
        concept.synonym = prop.get("synonym") or concept.synonym
        concept.is_branded = (concept.tty or "") in ("SBD", "BPCK")
        concept.payload = prop or concept.payload
        concept.refreshed_at = datetime.now(timezone.utc)

        ingredients = self._fetch_ingredients(rxcui)
        if ingredients:
            # Replace wholesale — a partial refresh could leave a stale
            # ingredient behind and silently skew the dose maths.
            for existing in list(concept.ingredients):
                self.session.delete(existing)
            concept.ingredients = [DrugIngredient(**row) for row in ingredients]

        try:
            self.session.commit()
        except Exception as exc:
            logger.error("Failed to persist concept %s: %s", rxcui, exc)
            self.session.rollback()
            return self.session.get(DrugConcept, rxcui)

        return concept

    def _fetch_ingredients(self, rxcui: str) -> List[Dict[str, Any]]:
        """Derive active ingredients + per-unit strength for a product.

        SCDC concepts ("acetaminophen 325 MG") carry the strength; IN concepts
        are the fallback when a product has no dose-form strength attached.
        """
        # The tty list must keep its literal '+' separators: passing it through
        # the params dict percent-encodes them to %2B and RxNav answers 400.
        data = self._get_json(
            f"{RXNAV_BASE}/rxcui/{rxcui}/related.json?tty=IN+PIN+SCDC",
            {},
            "rxnav",
            ttl=CONCEPT_TTL,
        ) or {}

        by_tty: Dict[str, List[dict]] = {}
        for group in (data.get("relatedGroup") or {}).get("conceptGroup") or []:
            by_tty[group.get("tty")] = group.get("conceptProperties") or []

        rows: List[Dict[str, Any]] = []
        seen_keys = set()

        for scdc in by_tty.get("SCDC", []):
            parsed = self._parse_strength(scdc.get("name") or "")
            if not parsed:
                continue
            key = normalise_ingredient_key(parsed["name"])
            if not key or key in seen_keys:
                continue
            seen_keys.add(key)
            rows.append({
                "ingredient_rxcui": scdc.get("rxcui"),
                "ingredient_name": parsed["name"],
                "ingredient_key": key,
                "strength_amount": parsed["amount"],
                "strength_unit": parsed["unit"],
                "strength_mg": parsed["mg"],
                "source": "RxNorm",
            })

        # Ingredients with no SCDC strength still matter for duplicate
        # detection, even though they cannot contribute to a dose total.
        for ing in by_tty.get("IN", []) + by_tty.get("PIN", []):
            name = ing.get("name") or ""
            key = normalise_ingredient_key(name)
            if not key or key in seen_keys:
                continue
            seen_keys.add(key)
            rows.append({
                "ingredient_rxcui": ing.get("rxcui"),
                "ingredient_name": name,
                "ingredient_key": key,
                "strength_amount": None,
                "strength_unit": None,
                "strength_mg": None,
                "source": "RxNorm",
            })

        return rows

    @staticmethod
    def _parse_strength(scdc_name: str) -> Optional[Dict[str, Any]]:
        match = _STRENGTH_RE.match(scdc_name.strip())
        if not match:
            return None
        unit = match.group("unit").upper()
        amount = float(match.group("amount"))
        factor = _UNIT_TO_MG.get(unit)
        return {
            "name": match.group("name").strip(),
            "amount": amount,
            "unit": unit,
            "mg": round(amount * factor, 6) if factor else None,
        }

    # ------------------------------------------------------------------
    # Dose limits + openFDA citations
    # ------------------------------------------------------------------

    def get_limit(self, ingredient_key: str) -> Optional[IngredientLimit]:
        """Curated labeled maximum for an ingredient, or None if unknown.

        Returning None is meaningful: the rule engine reports "no published
        limit on file" rather than inventing one.
        """
        if not ingredient_key:
            return None
        return (
            self.session.query(IngredientLimit)
            .filter_by(ingredient_key=ingredient_key)
            .first()
        )

    def fetch_label_excerpt(self, ingredient_name: str) -> Optional[Dict[str, Any]]:
        """Pull verbatim openFDA label text to cite alongside a finding.

        Used for display only — the numeric limit always comes from the curated
        `ingredient_limits` table, never from parsing this free text.
        """
        if not ingredient_name:
            return None

        data = self._get_json(
            OPENFDA_LABEL_URL,
            {
                "search": f'openfda.generic_name:"{ingredient_name}"'
                          f' AND _exists_:dosage_and_administration',
                "limit": 1,
            },
            "openfda",
        ) or {}

        results = data.get("results") or []
        if not results:
            return None

        label = results[0]
        openfda = label.get("openfda") or {}
        text = " ".join(label.get("dosage_and_administration") or [])[:600]
        set_id = label.get("set_id")
        return {
            "source": "openFDA drug label",
            "label_id": set_id,
            "url": f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={set_id}" if set_id else None,
            "brand_name": (openfda.get("brand_name") or [None])[0],
            "excerpt": text or None,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # openFDA interaction prose (Phase 2)
    # ------------------------------------------------------------------

    # Sections of an openFDA label that carry interaction warnings, in
    # descending order of how specific they are. A prescription label puts them
    # in `drug_interactions`; an OTC label usually puts the same warning under
    # "ask a doctor or pharmacist before use if you are taking...". Scanning all
    # of them is deliberate — an OTC-only search would silently miss the
    # warnings that matter most to a consumer. Each section is kept separate so
    # a finding can cite the exact one it read.
    _INTERACTION_SECTIONS = (
        "drug_interactions",
        "drug_and_or_laboratory_test_interactions",
        "ask_a_doctor_or_pharmacist_before_use",
        "do_not_use",
        "warnings",
    )

    def fetch_interaction_sections(self, ingredient_name: str) -> Optional[Dict[str, Any]]:
        """Verbatim interaction prose from an openFDA label, by section.

        Returns the raw text only. Deciding whether any of it applies to the
        user's list is the rule engine's job — this service supplies sourced
        facts and makes no safety judgement of its own.

        Returns None when no label could be found, and a payload with an empty
        `sections` list when a label exists but publishes no interaction prose.
        Those two cases mean different things to the caller, so they are not
        collapsed into one.
        """
        if not ingredient_name:
            return None

        data = self._get_json(
            OPENFDA_LABEL_URL,
            {"search": f'openfda.generic_name:"{ingredient_name}"', "limit": 3},
            "openfda",
        ) or {}

        results = data.get("results") or []
        if not results:
            return None

        # Prefer the first label that actually publishes interaction prose;
        # fall back to the first label so "found nothing" stays distinguishable
        # from "found no label at all".
        chosen, chosen_sections = results[0], []
        for label in results:
            sections = self._extract_sections(label)
            if sections:
                chosen, chosen_sections = label, sections
                break

        openfda = chosen.get("openfda") or {}
        set_id = chosen.get("set_id")
        return {
            "source": "openFDA drug label",
            "label_id": set_id,
            "url": (
                f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={set_id}"
                if set_id else None
            ),
            "brand_name": (openfda.get("brand_name") or [None])[0],
            "generic_name": (openfda.get("generic_name") or [None])[0],
            "sections": chosen_sections,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    def _extract_sections(cls, label: Dict[str, Any]) -> List[Dict[str, str]]:
        """Flatten the interaction-bearing sections of one openFDA label."""
        sections = []
        for field in cls._INTERACTION_SECTIONS:
            text = " ".join(label.get(field) or []).strip()
            if text:
                sections.append({"section": field, "text": text})
        return sections
