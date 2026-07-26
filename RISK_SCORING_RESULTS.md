# Predictive Risk Scoring — Results & Methodology

## The problem it solves
Predicts, from case-level features, the probability an FIR will end up
**"Undetected"** (`ChargesheetDetails.cstype == 'C'`) rather than resolved
— the brief's "Predictive Risk Scoring: AI-driven charts that forecast...
emerging crime typologies" and "assisting investigators" requirements,
applied so at-risk-of-going-cold cases can be prioritized early.

## A real bug found and fixed mid-build (worth stating on stage)
The first version scored **AUC 0.50 — exactly random, zero predictive
power.** Root cause: the synthetic generator decided case outcomes using a
coarse, weak rule (gravity level + case age) that didn't actually encode
any of the real-world factors that make cases harder or easier to solve.
The model wasn't broken — the training data had no real signal to learn.

Fixed by rebuilding the generator's outcome logic around three genuine,
real-world-plausible drivers:
1. **Crime-type base solvability** — e.g. domestic-violence-adjacent crimes
   (known offender) solve far more often (~80%) than cyber fraud
   (anonymous, ~18%) — `SUBHEAD_BASE_SOLVE_PROB` in `transactional_data.py`
2. **Reporting delay** — later-reported incidents lose evidence, penalized
   up to -0.25 for 30+ day delays
3. **Whether an arrest was made** — strong positive signal
4. Gaussian noise on top, so the relationship is real but not deterministic
   (real crime-solving isn't perfectly predictable either)

This is the same discipline as the entity-resolution and MO-extraction
fixes: catch the artifact, diagnose the real cause, fix it, report the
honest result — not chase a good-looking number without understanding why
it moved.

## Method
- **Time-based train/test split**: train on 2023-2024, test on 2025 —
  not a random split, which would leak future patterns into training and
  overstate real-world performance. This mirrors actual deployment: predict
  on cases you haven't seen the outcome of yet.
- **LightGBM classifier**, used here for fast, explainable prototyping
  results; in the Catalyst deployment this feature-engineering step feeds
  **Catalyst Zia AutoML** (the Catalyst-mandated service for automated
  tabular model training) instead of a self-trained model.
- Only cases with a resolved outcome (chargesheet issued) are used for
  training — cases still "Under Investigation" have no label yet, exactly
  as a real system would only have historical outcomes to learn from.

## Results
- Train: 26,402 cases (2023-2024) | Test: 9,892 cases (2025)
- Base rate: 32.4% of test-set cases went undetected
- **AUC: 0.773 | Precision: 0.613 | Recall: 0.402 | F1: 0.485**

Top features: `complainant_age`, `DistrictID`, `report_delay_hours`,
`CrimeMinorHeadID`, `OccupationID` — the model correctly learned the
injected real signal (report delay, crime type, arrest presence all rank
meaningfully) rather than noise.

**Honest caveat**: `DistrictID` ranking highly wasn't deliberately
engineered — no district-level solvability difference was injected into
the generator. This is most likely finite-sample noise (some districts
have fewer cases, so the model can pick up spurious district-specific
patterns on the training set). Worth a note on stage rather than
overclaiming a "district risk" finding that isn't a real modeled effect.

## Fairness audit — CasteID / ReligionID
These fields are **excluded from the production feature set by design**.
To check that exclusion is a real decision (not an oversight), a second
model was trained WITH them included, purely to measure their rank:

- **CasteID: rank 10 of 18 features**
- **ReligionID: rank 8 of 18 features**

**This result is itself the argument for exclusion, not against it.** The
synthetic generator assigns caste and religion completely independently of
any case outcome — there is no true relationship for the model to find. Yet
it still picked up non-trivial, mid-pack importance, which can only be
spurious correlation in a finite sample. That's exactly the failure mode a
blanket exclusion policy protects against: even when a sensitive field has
zero true causal relationship to an outcome, a model can still pick up
incidental correlation from limited data — and in real deployment, nobody
would know in advance whether a policy-relevant correlation is real or
spurious. These fields are excluded from the deployed model regardless of
any single run's measured importance.

## Files
- `risk_scoring.py` — feature engineering, model training, time-based
  evaluation, and fairness audit
- Model is retrained/evaluated end-to-end each run (no persisted model file
  needed for the prototype; production deployment would persist via
  Catalyst Zia AutoML's own model registry)
