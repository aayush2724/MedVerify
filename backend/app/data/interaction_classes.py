"""
Curated drug-class vocabulary used by the interaction rule (RULE-INT-01).

WHY A CURATED TABLE AND NOT AN INFERENCE
----------------------------------------
An openFDA label's `drug_interactions` section is free-text prose written for a
human. It names some interacting drugs outright ("do not take with warfarin")
but names most of them by *class* ("MAO inhibitors", "other NSAIDs", "CNS
depressants"). Matching only on ingredient names would therefore miss the
majority of what a label actually warns about, and the tool would look clean
when the label is not.

The alternative — asking a model to read the prose and decide whether two drugs
interact — is exactly the ML safety verdict this module forbids. So the bridge
between "the label says CNS depressants" and "your list contains oxycodone"
lives here instead: a flat, reviewable table mapping an ingredient key to the
class terms a label would use for it. Every entry can be checked by a human
against the label language it is meant to catch.

HOW A MATCH IS REPORTED
-----------------------
The rule distinguishes the two match strengths and says which one fired:

* `ingredient` — drug A's label names drug B outright. Unambiguous.
* `class`      — drug A's label names a class that B belongs to per this table.
                 Reported, but the finding says so in words, because a class
                 sentence may or may not apply to the specific product.

A class term is only worth listing if a label would plausibly print it. Terms
are matched case-insensitively on word boundaries, so keep them specific:
"nsaid" is useful, "pain reliever" would fire on almost every label.
"""

# ---------------------------------------------------------------------------
# ingredient key -> class terms a label might use for it
#
# Keys must be the output of `normalise_ingredient_key`, i.e. lower-cased with
# salt suffixes stripped ("diphenhydramine hydrochloride" -> "diphenhydramine").
# ---------------------------------------------------------------------------
INGREDIENT_CLASSES = {
    # --- Analgesics / antipyretics ------------------------------------------
    "acetaminophen": [
        "acetaminophen", "paracetamol", "apap",
    ],
    "ibuprofen": [
        "nsaid", "nsaids", "nonsteroidal anti-inflammatory",
        "non-steroidal anti-inflammatory", "anti-inflammatory drug",
    ],
    "naproxen": [
        "nsaid", "nsaids", "nonsteroidal anti-inflammatory",
        "non-steroidal anti-inflammatory", "anti-inflammatory drug",
    ],
    "aspirin": [
        "nsaid", "nsaids", "salicylate", "salicylates",
        "nonsteroidal anti-inflammatory", "antiplatelet",
    ],
    "diclofenac": [
        "nsaid", "nsaids", "nonsteroidal anti-inflammatory",
    ],
    "celecoxib": [
        "nsaid", "nsaids", "cox-2 inhibitor",
    ],

    # --- Opioids -------------------------------------------------------------
    "oxycodone": [
        "opioid", "opioids", "narcotic", "narcotics",
        "cns depressant", "cns depressants",
        "central nervous system depressant", "central nervous system depressants",
    ],
    "hydrocodone": [
        "opioid", "opioids", "narcotic", "narcotics",
        "cns depressant", "cns depressants",
        "central nervous system depressant", "central nervous system depressants",
    ],
    "codeine": [
        "opioid", "opioids", "narcotic", "narcotics",
        "cns depressant", "cns depressants",
        "central nervous system depressant", "central nervous system depressants",
    ],
    "tramadol": [
        "opioid", "opioids", "narcotic", "narcotics",
        "serotonergic", "serotonergic drug", "serotonergic drugs",
        "cns depressant", "cns depressants",
        "central nervous system depressant", "central nervous system depressants",
    ],
    "morphine": [
        "opioid", "opioids", "narcotic", "narcotics",
        "cns depressant", "cns depressants",
        "central nervous system depressant", "central nervous system depressants",
    ],

    # --- Sedating antihistamines --------------------------------------------
    "diphenhydramine": [
        "antihistamine", "antihistamines", "sedating antihistamine",
        "anticholinergic", "anticholinergics",
        "cns depressant", "cns depressants",
        "central nervous system depressant", "central nervous system depressants",
    ],
    "doxylamine": [
        "antihistamine", "antihistamines", "sedating antihistamine",
        "anticholinergic", "anticholinergics",
        "cns depressant", "cns depressants",
        "central nervous system depressant", "central nervous system depressants",
    ],
    "chlorpheniramine": [
        "antihistamine", "antihistamines", "sedating antihistamine",
        "anticholinergic", "anticholinergics",
        "cns depressant", "cns depressants",
    ],
    "cetirizine": ["antihistamine", "antihistamines"],
    "loratadine": ["antihistamine", "antihistamines"],

    # --- Sedative-hypnotics / anxiolytics ------------------------------------
    "alprazolam": [
        "benzodiazepine", "benzodiazepines",
        "cns depressant", "cns depressants",
        "central nervous system depressant", "central nervous system depressants",
        "sedative", "sedatives", "tranquilizer", "tranquilizers",
    ],
    "lorazepam": [
        "benzodiazepine", "benzodiazepines",
        "cns depressant", "cns depressants",
        "central nervous system depressant", "central nervous system depressants",
        "sedative", "sedatives", "tranquilizer", "tranquilizers",
    ],
    "diazepam": [
        "benzodiazepine", "benzodiazepines",
        "cns depressant", "cns depressants",
        "central nervous system depressant", "central nervous system depressants",
        "sedative", "sedatives", "tranquilizer", "tranquilizers",
    ],
    "zolpidem": [
        "sedative", "sedatives", "hypnotic", "hypnotics",
        "cns depressant", "cns depressants",
        "central nervous system depressant", "central nervous system depressants",
    ],

    # --- Anticoagulants / antiplatelets --------------------------------------
    "warfarin": [
        "anticoagulant", "anticoagulants", "blood thinner", "blood thinners",
        "coumarin", "vitamin k antagonist",
    ],
    "apixaban": [
        "anticoagulant", "anticoagulants", "blood thinner", "blood thinners",
    ],
    "rivaroxaban": [
        "anticoagulant", "anticoagulants", "blood thinner", "blood thinners",
    ],
    "clopidogrel": [
        "antiplatelet", "antiplatelets", "blood thinner", "blood thinners",
    ],

    # --- Antidepressants -----------------------------------------------------
    "fluoxetine": [
        "ssri", "ssris", "selective serotonin reuptake inhibitor",
        "antidepressant", "antidepressants",
        "serotonergic", "serotonergic drug", "serotonergic drugs",
    ],
    "sertraline": [
        "ssri", "ssris", "selective serotonin reuptake inhibitor",
        "antidepressant", "antidepressants",
        "serotonergic", "serotonergic drug", "serotonergic drugs",
    ],
    "escitalopram": [
        "ssri", "ssris", "selective serotonin reuptake inhibitor",
        "antidepressant", "antidepressants",
        "serotonergic", "serotonergic drug", "serotonergic drugs",
    ],
    "citalopram": [
        "ssri", "ssris", "selective serotonin reuptake inhibitor",
        "antidepressant", "antidepressants",
        "serotonergic", "serotonergic drug", "serotonergic drugs",
    ],
    "venlafaxine": [
        "snri", "snris", "antidepressant", "antidepressants",
        "serotonergic", "serotonergic drug", "serotonergic drugs",
    ],
    "duloxetine": [
        "snri", "snris", "antidepressant", "antidepressants",
        "serotonergic", "serotonergic drug", "serotonergic drugs",
    ],
    "amitriptyline": [
        "tricyclic antidepressant", "tricyclic antidepressants", "tricyclic",
        "antidepressant", "antidepressants", "anticholinergic", "anticholinergics",
        "cns depressant", "cns depressants",
    ],

    # --- Decongestants / stimulants ------------------------------------------
    "pseudoephedrine": [
        "decongestant", "decongestants", "sympathomimetic", "sympathomimetics",
        "stimulant", "stimulants",
    ],
    "phenylephrine": [
        "decongestant", "decongestants", "sympathomimetic", "sympathomimetics",
    ],
    "caffeine": ["stimulant", "stimulants", "xanthine"],

    # --- Gastro / cardiovascular / other common ------------------------------
    "omeprazole": [
        "proton pump inhibitor", "proton pump inhibitors", "ppi", "ppis",
    ],
    "pantoprazole": [
        "proton pump inhibitor", "proton pump inhibitors", "ppi", "ppis",
    ],
    "metformin": ["antidiabetic", "antidiabetics", "biguanide"],
    "lisinopril": [
        "ace inhibitor", "ace inhibitors",
        "angiotensin converting enzyme inhibitor", "antihypertensive",
    ],
    "losartan": [
        "arb", "angiotensin receptor blocker", "angiotensin ii receptor",
        "antihypertensive",
    ],
    "atorvastatin": ["statin", "statins", "hmg-coa reductase inhibitor"],
    "simvastatin": ["statin", "statins", "hmg-coa reductase inhibitor"],
    "levothyroxine": ["thyroid hormone", "thyroid hormones"],
    "prednisone": ["corticosteroid", "corticosteroids", "steroid", "steroids"],
    "dextromethorphan": [
        "serotonergic", "serotonergic drug", "serotonergic drugs",
        "cough suppressant", "antitussive",
    ],
    "guaifenesin": ["expectorant"],
}


# ---------------------------------------------------------------------------
# Label phrases that mark an outright "do not combine" instruction.
#
# These escalate a finding from `moderate` to `high`. They are matched against
# the specific sentence that mentioned the other drug — never the whole
# section — so a strong phrase elsewhere on the label cannot escalate an
# unrelated sentence. The finding always quotes the sentence that fired, so the
# escalation is visible and checkable rather than a hidden score.
# ---------------------------------------------------------------------------
CONTRAINDICATION_PHRASES = (
    "do not take",
    "do not use",
    "should not be taken",
    "should not be used",
    "must not be taken",
    "must not be used",
    "is contraindicated",
    "are contraindicated",
    "contraindicated in",
    "avoid use",
    "avoid taking",
    "avoid concomitant",
    "avoid concurrent",
    "should be avoided",
    "never take",
)
