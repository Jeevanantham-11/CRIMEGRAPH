"""
MO (Modus Operandi) Signature Extraction
=========================================
Mines the free-text `CaseMaster.BriefFacts` field — unstructured narrative
that every other module in a typical hackathon entry ignores — to build a
per-person MO signature and show where it recurs across cases/districts.

Production note: this uses a phrase-matching extractor as a clear, fast,
demo-able proxy for what would be a Catalyst Zia Text Analytics call in
production (entity/keyword extraction on free text). The downstream logic
(signature aggregation, consistency scoring, cross-jurisdiction matching)
is identical either way — only the extraction step would change.
"""

import re
from collections import Counter, defaultdict

import pandas as pd

DATA_DIR = "../synthetic_data"

# Master phrase list mirrors config used at generation time — in production
# this would instead be a growing list of extracted keyword clusters from
# Zia Text Analytics output, not a fixed vocabulary.
MO_PHRASE_CATEGORIES = {
    "property": [
        "The accused gained entry through a rear window left unlatched.",
        "The accused targeted unattended shops during the late-night hours.",
        "The accused used a duplicate key/lock-picking method to gain entry.",
        "The accused used a rented vehicle with tampered number plates to transport stolen goods.",
        "The accused worked in a group of two, one keeping watch while the other broke in.",
    ],
    "violent_person": [
        "The accused used a two-wheeler to approach and flee the scene rapidly.",
        "The accused wore a helmet throughout to avoid CCTV identification.",
        "The accused was known to the victim through a prior personal dispute.",
        "The accused waylaid the victim along a known secluded route.",
    ],
    "women_children": [
        "The accused approached the victim through a fake social media profile.",
        "The accused was a person known to the victim's family.",
        "The accused lured the victim on the pretext of a job offer.",
    ],
    "cyber_economic": [
        "The accused posed as a bank/delivery representative to gain the victim's trust.",
        "The accused used a spoofed phone number to contact the victim.",
        "The accused operated using a fraudulent online payment link.",
    ],
    "public_order": [
        "The accused operated in daylight hours near crowded public spaces.",
        "The accused acted as part of an organized group during the incident.",
    ],
    "narcotics_arms": [
        "The accused was found in possession of the contraband during a routine check.",
        "The accused used a concealed compartment in the vehicle to transport the contraband.",
    ],
}
ALL_PHRASES = [p for phrases in MO_PHRASE_CATEGORIES.values() for p in phrases]


def extract_mo_sentences(brief_facts: str) -> list:
    """Extracts which known MO phrases appear in a case narrative. In
    production, replace this function's body with a Zia Text Analytics
    call and map its extracted key-phrases to an MO taxonomy — everything
    downstream (signature building, consistency scoring) stays the same."""
    if not isinstance(brief_facts, str):
        return []
    return [phrase for phrase in ALL_PHRASES if phrase in brief_facts]


def build_mo_signatures():
    case_master = pd.read_csv(f"{DATA_DIR}/CaseMaster.csv")
    resolved = pd.read_csv(f"{DATA_DIR}/resolved_persons.csv")
    unit = pd.read_csv(f"{DATA_DIR}/Unit.csv")

    station_to_district = dict(zip(unit["UnitID"], unit["DistrictID"]))
    case_master["DistrictID"] = case_master["PoliceStationID"].map(station_to_district)

    print("Extracting MO phrases from BriefFacts text...")
    case_master["mo_phrases"] = case_master["BriefFacts"].map(extract_mo_sentences)
    case_to_phrases = dict(zip(case_master["CaseMasterID"], case_master["mo_phrases"]))
    case_to_district = dict(zip(case_master["CaseMasterID"], case_master["DistrictID"]))

    # ---------------- Build per-person MO signature ----------------
    person_cases = resolved.groupby("ResolvedPersonID")["CaseMasterID"].apply(list)

    signatures = []
    for person_id, case_ids in person_cases.items():
        phrase_counter = Counter()
        phrase_to_districts = defaultdict(set)
        for c in case_ids:
            phrases = case_to_phrases.get(c, [])
            district = case_to_district.get(c)
            for p in phrases:
                phrase_counter[p] += 1
                if district is not None:
                    phrase_to_districts[p].add(district)

        n_cases = len(case_ids)
        if not phrase_counter:
            signatures.append({
                "ResolvedPersonID": person_id, "n_cases": n_cases,
                "dominant_mo_phrase": None, "mo_consistency": 0.0,
                "n_districts_with_dominant_mo": 0,
            })
            continue

        dominant_phrase, dominant_count = phrase_counter.most_common(1)[0]
        signatures.append({
            "ResolvedPersonID": person_id,
            "n_cases": n_cases,
            "dominant_mo_phrase": dominant_phrase,
            "mo_consistency": round(dominant_count / n_cases, 3),
            "n_districts_with_dominant_mo": len(phrase_to_districts[dominant_phrase]),
        })

    sig_df = pd.DataFrame(signatures)
    sig_df.to_csv(f"{DATA_DIR}/mo_signatures.csv", index=False)

    repeat = sig_df[sig_df["n_cases"] >= 2]
    high_consistency = repeat[repeat["mo_consistency"] >= 0.6]

    print(f"\n{len(sig_df):,} resolved persons profiled")
    print(f"{len(repeat):,} are repeat offenders (2+ cases)")
    print(f"{len(high_consistency):,} show a consistent MO signature (>=60% of their cases "
          f"share the same dominant phrase)")

    # Large-case-count, low-consistency clusters are almost certainly entity-
    # resolution over-merges (precision is 62.8%, see ENTITY_RESOLUTION_RESULTS.md),
    # not real people with 100+ FIRs. Restrict the "clean" view to a plausible
    # per-person case range so the reported consistency number and demo
    # highlights aren't diluted/distorted by that known limitation.
    plausible = repeat[repeat["n_cases"] <= 15]
    print(f"Mean MO consistency among plausible repeat offenders (<=15 cases, "
          f"n={len(plausible):,}): {plausible['mo_consistency'].mean():.3f}")
    print(f"(Mean across ALL repeat offenders incl. likely over-merged clusters: "
          f"{repeat['mo_consistency'].mean():.3f} -- lower, as expected, since large low-consistency "
          f"clusters are diluting it)")

    cross_district_clean = plausible[
        (plausible["n_districts_with_dominant_mo"] >= 2) & (plausible["mo_consistency"] >= 0.6)
    ]
    print(f"{len(cross_district_clean):,} plausible repeat offenders repeat their SAME dominant MO "
          f"phrase across 2+ districts with >=60% consistency -- direct, credible evidence for "
          f"cross-jurisdiction MO tracking")

    print("\nTop 5 demo highlights (plausible case count, ranked by consistency then district spread):")
    demo_rows = cross_district_clean.sort_values(
        ["mo_consistency", "n_districts_with_dominant_mo"], ascending=False
    ).head(5)
    print(demo_rows.to_string(index=False))

    return sig_df


if __name__ == "__main__":
    build_mo_signatures()
