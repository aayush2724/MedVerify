"""
Curated labeled maximum daily doses for common consumer medications.

WHY THIS IS A HAND-CURATED TABLE, NOT A MODEL OR A SCRAPER
----------------------------------------------------------
The spec forbids an ML-derived safety verdict, and openFDA exposes dosing only
as free-text prose inside `dosage_and_administration` — parsing a number out of
that is unreliable and would silently produce wrong maxima. So the numeric
limit lives here, in a reviewable table where every row names the document it
came from, and the openFDA label text is fetched separately and attached to a
finding purely as a verbatim citation the user can read for themselves.

SCOPE AND LIMITS OF THIS TABLE
------------------------------
* Adult (>= 12 years) over-the-counter dosing only, unless a row says otherwise.
* These are *labeled maxima for self-care*, not clinical dosing ceilings. A
  clinician may direct a different dose, and several of these limits are lower
  for people who drink alcohol, are pregnant, or have liver or kidney disease.
* An ingredient absent from this table yields "no published limit on file" —
  the rule engine must never infer a limit it does not have.

Every value below is transcribed from the cited FDA OTC monograph or approved
label. Review this file whenever a monograph changes.
"""

# audience: 'adult' — self-care dosing for ages 12+ unless the note says otherwise.
INGREDIENT_LIMITS = [
    {
        "ingredient_key": "acetaminophen",
        "ingredient_name": "Acetaminophen (paracetamol)",
        "max_daily_mg": 4000.0,
        "source_name": "FDA OTC internal analgesic monograph (21 CFR 343.50)",
        "source_url": "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfcfr/CFRSearch.cfm?fr=343.50",
        "caution_note": (
            "Many manufacturers now label a lower 3,000 mg daily maximum, and the safe "
            "limit is lower still with regular alcohol use or liver disease. Acetaminophen "
            "is the most common cause of accidental overdose because it is hidden inside "
            "combination cold, flu and sleep products."
        ),
    },
    {
        "ingredient_key": "ibuprofen",
        "ingredient_name": "Ibuprofen",
        "max_daily_mg": 1200.0,
        "source_name": "FDA OTC internal analgesic monograph (21 CFR 343.50)",
        "source_url": "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfcfr/CFRSearch.cfm?fr=343.50",
        "caution_note": (
            "1,200 mg is the over-the-counter self-care maximum. Higher doses are used "
            "only under a clinician's direction. Combining several NSAIDs raises the risk "
            "of stomach bleeding and kidney injury."
        ),
    },
    {
        "ingredient_key": "naproxen",
        "ingredient_name": "Naproxen sodium",
        "max_daily_mg": 660.0,
        "source_name": "FDA OTC internal analgesic monograph (21 CFR 343.50)",
        "source_url": "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfcfr/CFRSearch.cfm?fr=343.50",
        "caution_note": "Over-the-counter maximum is 660 mg naproxen sodium (about 600 mg naproxen base) per day.",
    },
    {
        "ingredient_key": "aspirin",
        "ingredient_name": "Aspirin (acetylsalicylic acid)",
        "max_daily_mg": 4000.0,
        "source_name": "FDA OTC internal analgesic monograph (21 CFR 343.50)",
        "source_url": "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfcfr/CFRSearch.cfm?fr=343.50",
        "caution_note": (
            "Applies to aspirin taken for pain relief. Low-dose aspirin taken for heart "
            "protection is a different regimen — do not change it without asking your doctor. "
            "Aspirin should not be given to children or teenagers recovering from viral illness."
        ),
    },
    {
        "ingredient_key": "diphenhydramine",
        "ingredient_name": "Diphenhydramine",
        "max_daily_mg": 300.0,
        "source_name": "FDA OTC antihistamine monograph (21 CFR 341.72)",
        "source_url": "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfcfr/CFRSearch.cfm?fr=341.72",
        "caution_note": (
            "Appears in both allergy products and night-time pain/sleep products, so it is "
            "easy to double up without noticing. Causes marked drowsiness; the limit is "
            "lower for older adults."
        ),
    },
    {
        "ingredient_key": "doxylamine",
        "ingredient_name": "Doxylamine succinate",
        "max_daily_mg": 25.0,
        "source_name": "FDA OTC nighttime sleep-aid monograph (21 CFR 338.50)",
        "source_url": "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfcfr/CFRSearch.cfm?fr=338.50",
        "caution_note": "25 mg is the labeled night-time sleep-aid maximum for a single day.",
    },
    {
        "ingredient_key": "dextromethorphan",
        "ingredient_name": "Dextromethorphan",
        "max_daily_mg": 120.0,
        "source_name": "FDA OTC antitussive monograph (21 CFR 341.74)",
        "source_url": "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfcfr/CFRSearch.cfm?fr=341.74",
        "caution_note": "Found in most multi-symptom cough and cold products; check every product on your list.",
    },
    {
        "ingredient_key": "guaifenesin",
        "ingredient_name": "Guaifenesin",
        "max_daily_mg": 2400.0,
        "source_name": "FDA OTC expectorant monograph (21 CFR 341.78)",
        "source_url": "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfcfr/CFRSearch.cfm?fr=341.78",
        "caution_note": None,
    },
    {
        "ingredient_key": "pseudoephedrine",
        "ingredient_name": "Pseudoephedrine",
        "max_daily_mg": 240.0,
        "source_name": "FDA OTC nasal decongestant monograph (21 CFR 341.80)",
        "source_url": "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfcfr/CFRSearch.cfm?fr=341.80",
        "caution_note": "Can raise blood pressure and heart rate. Ask a pharmacist first if you take blood-pressure medication.",
    },
    {
        "ingredient_key": "phenylephrine",
        "ingredient_name": "Phenylephrine (oral)",
        "max_daily_mg": 60.0,
        "source_name": "FDA OTC nasal decongestant monograph (21 CFR 341.80)",
        "source_url": "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfcfr/CFRSearch.cfm?fr=341.80",
        "caution_note": "Limit applies to oral phenylephrine, not nasal sprays.",
    },
    {
        "ingredient_key": "chlorpheniramine",
        "ingredient_name": "Chlorpheniramine maleate",
        "max_daily_mg": 24.0,
        "source_name": "FDA OTC antihistamine monograph (21 CFR 341.72)",
        "source_url": "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfcfr/CFRSearch.cfm?fr=341.72",
        "caution_note": None,
    },
    {
        "ingredient_key": "loratadine",
        "ingredient_name": "Loratadine",
        "max_daily_mg": 10.0,
        "source_name": "FDA-approved OTC label (Claritin, NDA 019658)",
        "source_url": "https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query=loratadine",
        "caution_note": None,
    },
    {
        "ingredient_key": "cetirizine",
        "ingredient_name": "Cetirizine",
        "max_daily_mg": 10.0,
        "source_name": "FDA-approved OTC label (Zyrtec, NDA 019835)",
        "source_url": "https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query=cetirizine",
        "caution_note": "Adults over 65 and people with kidney problems are labeled for 5 mg per day.",
    },
    {
        "ingredient_key": "fexofenadine",
        "ingredient_name": "Fexofenadine",
        "max_daily_mg": 180.0,
        "source_name": "FDA-approved OTC label (Allegra, NDA 020872)",
        "source_url": "https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query=fexofenadine",
        "caution_note": None,
    },
    {
        "ingredient_key": "famotidine",
        "ingredient_name": "Famotidine",
        "max_daily_mg": 40.0,
        "source_name": "FDA-approved OTC label (Pepcid AC)",
        "source_url": "https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query=famotidine",
        "caution_note": "20 mg twice daily is the over-the-counter maximum, for no more than 14 days of self-treatment.",
    },
    {
        "ingredient_key": "omeprazole",
        "ingredient_name": "Omeprazole",
        "max_daily_mg": 20.0,
        "source_name": "FDA-approved OTC label (Prilosec OTC)",
        "source_url": "https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query=omeprazole",
        "caution_note": "Labeled for a 14-day self-treatment course, up to three courses a year.",
    },
    {
        "ingredient_key": "loperamide",
        "ingredient_name": "Loperamide",
        "max_daily_mg": 8.0,
        "source_name": "FDA OTC antidiarrheal monograph (21 CFR 335.80)",
        "source_url": "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfcfr/CFRSearch.cfm?fr=335.80",
        "caution_note": (
            "The FDA has warned that doses above the labeled maximum can cause serious and "
            "sometimes fatal heart rhythm problems."
        ),
    },
    {
        "ingredient_key": "caffeine",
        "ingredient_name": "Caffeine",
        "max_daily_mg": 400.0,
        "source_name": "FDA consumer guidance on caffeine intake",
        "source_url": "https://www.fda.gov/consumers/consumer-updates/spilling-beans-how-much-caffeine-too-much",
        "caution_note": (
            "400 mg a day is FDA's general guidance for healthy adults, not a monograph "
            "limit. It does not count caffeine from coffee, tea or energy drinks, which "
            "this tool cannot see."
        ),
    },
]
