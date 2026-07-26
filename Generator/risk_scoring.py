"""
Predictive Risk Scoring
=======================
Predicts, AT THE TIME AN FIR IS REGISTERED, the probability it will end up
"Undetected" (ChargesheetDetails.cstype == 'C') rather than resolved
(chargesheeted, 'A') or found false ('B'). This is the brief's "Predictive
Risk Scoring: AI-driven charts that forecast potential high-risk areas" —
applied at the case level so investigators can prioritize.

Design choices worth defending on stage:
1. TIME-BASED split (train on 2023-2024, test on 2025), not random —
   a random split leaks future station-level patterns into training and
   overstates real-world performance. This is how it would actually be
   deployed: predict on cases you haven't seen the outcome of yet.
2. CasteID and ReligionID are EXCLUDED from the feature set by design.
   A fairness audit below explicitly checks what would happen if they were
   included (their feature-importance rank), to prove the exclusion isn't
   just "we forgot them" but a deliberate, checked decision.
3. In production (Catalyst), this feature-engineering step is what you'd
   feed into Catalyst Zia AutoML rather than a self-trained LightGBM model
   — the model choice here is to produce fast, explainable, evidence-backed
   numbers during prototyping.
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.metrics import roc_auc_score, precision_recall_fscore_support, confusion_matrix

DATA_DIR = "../synthetic_data"

EXCLUDED_SENSITIVE_FEATURES = ["CasteID", "ReligionID"]


def load_and_join():
    case_master = pd.read_csv(f"{DATA_DIR}/CaseMaster.csv", parse_dates=["CrimeRegisteredDate"])
    chargesheet = pd.read_csv(f"{DATA_DIR}/ChargesheetDetails.csv")
    complainant = pd.read_csv(f"{DATA_DIR}/ComplainantDetails.csv")
    accused = pd.read_csv(f"{DATA_DIR}/Accused.csv")
    victim = pd.read_csv(f"{DATA_DIR}/Victim.csv")
    arrest = pd.read_csv(f"{DATA_DIR}/ArrestSurrender.csv")
    unit = pd.read_csv(f"{DATA_DIR}/Unit.csv")

    station_to_district = dict(zip(unit["UnitID"], unit["DistrictID"]))
    case_master["DistrictID"] = case_master["PoliceStationID"].map(station_to_district)

    # Only cases with a known outcome (chargesheeted/false/undetected) can be
    # used for TRAINING -- these are the ones with a resolved cstype.
    labeled = case_master.merge(chargesheet[["CaseMasterID", "cstype"]], on="CaseMasterID", how="inner")
    labeled["target_undetected"] = (labeled["cstype"] == "C").astype(int)

    # ---------------- Feature engineering ----------------
    n_accused = accused.groupby("CaseMasterID").size().rename("n_accused")
    n_victims = victim.groupby("CaseMasterID").size().rename("n_victims")
    n_arrests = arrest.groupby("CaseMasterID").size().rename("n_arrests")

    # One complainant-level feature per case (first complainant), EXCLUDING
    # caste/religion from the feature set entirely.
    comp_first = complainant.sort_values("ComplainantID").groupby("CaseMasterID").first()
    comp_feats = comp_first[["AgeYear", "OccupationID", "GenderID"]].rename(
        columns={"AgeYear": "complainant_age", "GenderID": "complainant_gender"})

    df = labeled.merge(n_accused, on="CaseMasterID", how="left")
    df = df.merge(n_victims, on="CaseMasterID", how="left")
    df = df.merge(n_arrests, on="CaseMasterID", how="left")
    df = df.merge(comp_feats, on="CaseMasterID", how="left")

    for col in ["n_accused", "n_victims", "n_arrests"]:
        df[col] = df[col].fillna(0)
    df["has_arrest"] = (df["n_arrests"] > 0).astype(int)

    df["reg_month"] = df["CrimeRegisteredDate"].dt.month
    df["reg_dow"] = df["CrimeRegisteredDate"].dt.dayofweek
    df["reg_year"] = df["CrimeRegisteredDate"].dt.year

    info_dt = pd.to_datetime(df["InfoReceivedPSDate"])
    incident_dt = pd.to_datetime(df["IncidentFromDate"])
    df["report_delay_hours"] = (info_dt - incident_dt).dt.total_seconds() / 3600.0
    df["report_delay_hours"] = df["report_delay_hours"].clip(lower=0).fillna(0)

    df["has_gps"] = df["latitude"].notna().astype(int)

    return df


FEATURE_COLS = [
    "GravityOffenceID", "CaseCategoryID", "CrimeMajorHeadID", "CrimeMinorHeadID",
    "DistrictID", "n_accused", "n_victims", "n_arrests", "has_arrest",
    "complainant_age", "OccupationID", "complainant_gender",
    "reg_month", "reg_dow", "report_delay_hours", "has_gps",
]
CATEGORICAL_COLS = ["GravityOffenceID", "CaseCategoryID", "CrimeMajorHeadID",
                     "CrimeMinorHeadID", "DistrictID", "OccupationID", "complainant_gender"]


def time_based_split(df):
    train = df[df["reg_year"].isin([2023, 2024])]
    test = df[df["reg_year"] == 2025]
    return train, test


def train_and_evaluate(df, extra_features=None):
    features = FEATURE_COLS + (extra_features or [])
    cat_cols = [c for c in CATEGORICAL_COLS if c in features]

    train, test = time_based_split(df)
    X_train, y_train = train[features].copy(), train["target_undetected"]
    X_test, y_test = test[features].copy(), test["target_undetected"]

    for c in cat_cols:
        X_train[c] = X_train[c].astype("category")
        X_test[c] = X_test[c].astype("category")

    model = lgb.LGBMClassifier(
        n_estimators=300, learning_rate=0.05, max_depth=6,
        num_leaves=31, random_state=42, verbose=-1,
    )
    model.fit(X_train, y_train, categorical_feature=cat_cols)

    proba = model.predict_proba(X_test)[:, 1]
    preds = (proba >= 0.5).astype(int)

    auc = roc_auc_score(y_test, proba)
    precision, recall, f1, _ = precision_recall_fscore_support(y_test, preds, average="binary")
    cm = confusion_matrix(y_test, preds)

    print(f"\nTrain: {len(X_train):,} cases (2023-2024) | Test: {len(X_test):,} cases (2025)")
    print(f"Base rate (test set): {y_test.mean():.3f} of cases go undetected")
    print(f"AUC: {auc:.4f} | Precision: {precision:.4f} | Recall: {recall:.4f} | F1: {f1:.4f}")
    print(f"Confusion matrix [[TN, FP], [FN, TP]]:\n{cm}")

    importances = pd.Series(model.feature_importances_, index=features).sort_values(ascending=False)
    print("\nFeature importances:")
    print(importances.to_string())

    return model, importances, {"auc": auc, "precision": precision, "recall": recall, "f1": f1}


def fairness_audit(df):
    """Trains a model WITH CasteID/ReligionID included, purely to check and
    report their feature-importance rank -- proving the production
    exclusion is a checked decision, not an oversight."""
    print("\n" + "=" * 60)
    print("FAIRNESS AUDIT: checking CasteID/ReligionID influence")
    print("(these are EXCLUDED from the production model regardless of result)")
    print("=" * 60)
    complainant = pd.read_csv(f"{DATA_DIR}/ComplainantDetails.csv")
    comp_first = complainant.sort_values("ComplainantID").groupby("CaseMasterID").first()
    df_audit = df.merge(comp_first[["CasteID", "ReligionID"]], on="CaseMasterID", how="left")

    _, importances, _ = train_and_evaluate(df_audit, extra_features=["CasteID", "ReligionID"])
    rank = importances.rank(ascending=False)
    print(f"\nCasteID importance rank: {int(rank['CasteID'])} of {len(importances)} features")
    print(f"ReligionID importance rank: {int(rank['ReligionID'])} of {len(importances)} features")
    print("These fields remain excluded from the deployed model regardless of this result.")


if __name__ == "__main__":
    print("Loading and engineering features...")
    df = load_and_join()

    print("\n" + "=" * 60)
    print("PRODUCTION MODEL (caste/religion excluded)")
    print("=" * 60)
    model, importances, metrics = train_and_evaluate(df)

    fairness_audit(df)
