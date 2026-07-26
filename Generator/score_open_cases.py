"""
Scores currently OPEN cases (Under Investigation, no chargesheet yet) with
the risk model -- this is the actual deployable output: "here are the FIRs
most likely to go undetected if not prioritized," not just a backtest metric.

Trains on ALL labeled (already-resolved) cases -- for a deployed scoring
job this is correct (use all available history), unlike the earlier
evaluation script which held out 2025 specifically to test generalization.
"""

import pandas as pd
import lightgbm as lgb

import risk_scoring as rs  # reuse load_and_join, FEATURE_COLS, CATEGORICAL_COLS

DATA_DIR = "../synthetic_data"


def score_open_cases():
    case_master = pd.read_csv(f"{DATA_DIR}/CaseMaster.csv", parse_dates=["CrimeRegisteredDate"])
    chargesheet = pd.read_csv(f"{DATA_DIR}/ChargesheetDetails.csv")
    unit = pd.read_csv(f"{DATA_DIR}/Unit.csv")
    district = pd.read_csv(f"{DATA_DIR}/District.csv")
    subhead = pd.read_csv(f"{DATA_DIR}/CrimeSubHead.csv")

    station_to_district = dict(zip(unit["UnitID"], unit["DistrictID"]))
    district_map = dict(zip(district["DistrictID"], district["DistrictName"]))
    subhead_map = dict(zip(subhead["CrimeSubHeadID"], subhead["CrimeHeadName"]))

    print("Training production model on ALL labeled (resolved) cases...")
    labeled_df = rs.load_and_join()
    features = rs.FEATURE_COLS
    cat_cols = rs.CATEGORICAL_COLS
    X_train = labeled_df[features].copy()
    y_train = labeled_df["target_undetected"]
    for c in cat_cols:
        X_train[c] = X_train[c].astype("category")

    model = lgb.LGBMClassifier(
        n_estimators=300, learning_rate=0.05, max_depth=6,
        num_leaves=31, random_state=42, verbose=-1,
    )
    model.fit(X_train, y_train, categorical_feature=cat_cols)

    print("Scoring currently open cases (Under Investigation, no chargesheet)...")
    open_cases = case_master[~case_master["CaseMasterID"].isin(chargesheet["CaseMasterID"])].copy()
    open_cases["DistrictID"] = open_cases["PoliceStationID"].map(station_to_district)

    accused = pd.read_csv(f"{DATA_DIR}/Accused.csv")
    victim = pd.read_csv(f"{DATA_DIR}/Victim.csv")
    arrest = pd.read_csv(f"{DATA_DIR}/ArrestSurrender.csv")
    complainant = pd.read_csv(f"{DATA_DIR}/ComplainantDetails.csv")

    n_accused = accused.groupby("CaseMasterID").size().rename("n_accused")
    n_victims = victim.groupby("CaseMasterID").size().rename("n_victims")
    n_arrests = arrest.groupby("CaseMasterID").size().rename("n_arrests")
    comp_first = complainant.sort_values("ComplainantID").groupby("CaseMasterID").first()
    comp_feats = comp_first[["AgeYear", "OccupationID", "GenderID"]].rename(
        columns={"AgeYear": "complainant_age", "GenderID": "complainant_gender"})

    df = open_cases.merge(n_accused, on="CaseMasterID", how="left")
    df = df.merge(n_victims, on="CaseMasterID", how="left")
    df = df.merge(n_arrests, on="CaseMasterID", how="left")
    df = df.merge(comp_feats, on="CaseMasterID", how="left")
    for col in ["n_accused", "n_victims", "n_arrests"]:
        df[col] = df[col].fillna(0)
    df["has_arrest"] = (df["n_arrests"] > 0).astype(int)
    df["reg_month"] = df["CrimeRegisteredDate"].dt.month
    df["reg_dow"] = df["CrimeRegisteredDate"].dt.dayofweek
    info_dt = pd.to_datetime(df["InfoReceivedPSDate"])
    incident_dt = pd.to_datetime(df["IncidentFromDate"])
    df["report_delay_hours"] = (info_dt - incident_dt).dt.total_seconds() / 3600.0
    df["report_delay_hours"] = df["report_delay_hours"].clip(lower=0).fillna(0)
    df["has_gps"] = df["latitude"].notna().astype(int)

    X_score = df[features].copy()
    for c in cat_cols:
        X_score[c] = X_score[c].astype("category")

    df["risk_score"] = model.predict_proba(X_score)[:, 1]
    df["DistrictName"] = df["DistrictID"].map(district_map)
    df["subhead"] = df["CrimeMinorHeadID"].map(subhead_map)

    out = df[["CaseMasterID", "CrimeNo", "DistrictName", "subhead", "GravityOffenceID",
              "CrimeRegisteredDate", "risk_score"]].sort_values("risk_score", ascending=False)
    out.to_csv(f"{DATA_DIR}/case_risk_scores.csv", index=False)

    print(f"\nScored {len(out):,} open cases.")
    print(f"High-risk (>0.6): {(out['risk_score'] > 0.6).sum():,}")
    print(f"Mean risk score: {out['risk_score'].mean():.3f}")
    print(f"Saved -> {DATA_DIR}/case_risk_scores.csv")
    print("\nTop 5 highest-risk open cases:")
    print(out.head(5).to_string(index=False))


if __name__ == "__main__":
    score_open_cases()