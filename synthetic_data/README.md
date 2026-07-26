# CrimeGraph — Synthetic Dataset (v1)

Generated for KSP Datathon 2026, Challenge 02. Covers **all 31 Karnataka
districts**, **3 years (2023–2025)**, ~1,134 police stations/units, ~39.6K
FIRs, ~68K accused entries.

## Why this dataset is built the way it is

**1. Schema-exact.** Every CSV matches the column names, types, and FK
relationships from the official ER document exactly. If real KSP data is
ever loaded in, it goes into the *same* table structure — no schema
migration, no code changes downstream. This is the whole point: the
generator and a real-data importer are interchangeable inputs to the same
pipeline (see `generate_all.py` — it calls one `build_*` function per
source; a real-data adapter would be a third function with the same output
shape).

**2. Real reference data, not invented values.**
- All 31 actual Karnataka districts, population-weighted for station count
  and case volume (`config.py: DISTRICTS`)
- NCRB-style crime-head/sub-head taxonomy (Crimes Against Body/Women/
  Property/Economic/Public Order, Special & Local Laws)
- Real Acts: IPC, BNS 2023 (India's mid-transition — both included since a
  real feed will contain a mix), NDPS, Arms Act, POCSO
- Approximate real district centroid coordinates for geospatial jitter

**3. `CrimeNo`/`CaseNo` generated with the exact encoding formula** from the
ER document (1-digit category + 4-digit district + 4-digit station +
4-digit year + 5-digit serial). See `crimeno_utils.py` — the same
encode/decode module would validate real FIR numbers unmodified.

**4. Deliberately realistic messiness — this is the important part.**
Real government records are never clean, and a model that only works on
clean synthetic data proves nothing. Injected:
- **Identity collisions**: 1,800 "real people" reappear across multiple FIRs
  (avg ~13 appearances each) with name-spelling drift, abbreviation,
  transliteration variants, and ±1-2yr age drift — see
  `name_variants.py` and `entity_resolution_ground_truth.csv`
- **Missing data**: ~4% of FIRs missing GPS, ~10% missing complainant
  occupation, ~3% missing complainant age
- **Category-coherent but non-trivial MO text** in `BriefFacts` — repeat
  offenders carry a "specialty" MO category; when they reoffend within that
  category, the narrative repeats their signature method (genuine MO
  pattern for text-mining to find); outside their specialty, a
  category-appropriate (not their own) phrase is used so narratives never
  read as nonsensical

**5. `entity_resolution_ground_truth.csv` is not part of the real ER
schema** — it's the labeled truth of which `AccusedMasterID` rows are the
same real person. This is what lets the entity-resolution module report
actual precision/recall instead of just describing its method. Do not
present this file as police data; it's evaluation scaffolding only.

**6. `ChargesheetDetails.cstype` (A/B/C) is correlated with case gravity and
age-of-case**, giving the predictive risk-scoring module a genuine,
learnable signal instead of a random label.

**7. Sensitive fields (`CasteID`, `ReligionID`) are populated using official
Indian administrative categories** (General/OBC/SC/ST, per statutory
reporting convention) but are excluded from all ML feature sets by design —
see the fairness-audit module. They exist here only so the socio-demographic
correlation dashboard (an explicit brief requirement) has data to overlay,
always at aggregate/k-anonymized level.

## Known limitations (be upfront about these on stage)

- Case volume is scaled down (`SCALE_FACTOR` in `config.py`) from real
  statewide order-of-magnitude for a demo-sized dataset — bump it up if your
  Catalyst plan can handle more rows
- District centroids are approximate town-level coordinates, not surveyed
  station coordinates — fine for demo hotspot mapping, not for operational use
- Name generation uses `Faker('en_IN')`, which won't perfectly capture every
  regional naming convention across Karnataka — real data will be messier
  in ways this doesn't fully anticipate

## Files

All in `../synthetic_data/`:
- 25 CSVs matching the ER schema tables exactly (see filenames)
- `entity_resolution_ground_truth.csv` — evaluation-only labels (not a real table)

## Regenerating / scaling up

```
cd crimegraph_data
python3 generate_all.py
```
Edit `config.py: SCALE_FACTOR`, `YEARS` to change volume/time range.
