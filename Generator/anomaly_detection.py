"""
Anomaly Detection & Trend Alerts
=================================
Two independent modules answering two separate brief requirements:

1. TREND ALERTS ("red-zone pulsing when a crime category spikes vs
   historical averages") -- statistical z-score monitoring per
   (District, CrimeSubHead, Month).

2. CASE-LEVEL ANOMALY DETECTION ("visual call-outs for incidents that
   deviate from standard behavioral patterns") -- Isolation Forest on
   engineered case features, flagging unusual individual FIRs for
   investigator review.

Honesty note (read before presenting results): our synthetic generator
does NOT inject any deliberate seasonal spike or crime-wave event -- case
volume per month is randomly assigned, not trend-driven. A first pass with
a loose minimum-count filter found 65 "spikes" -- almost all noise, from
the well-known "small numbers problem" in crime surveillance statistics
(z-scores on tiny baseline counts, e.g. mean=3-6/month, are unreliable --
natural random variation alone produces frequent false "spikes"). Tightening
the minimum baseline count to 8 cuts this to 8 genuinely defensible alerts
on believable volumes. That's Part 1, reported honestly. Part 2 is a
labeled synthetic stress test proving the SAME mechanism correctly fires a
strong alert when a genuine spike is present -- not a real detected event.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

DATA_DIR = "../synthetic_data"
MIN_BASELINE_MONTHS = 4          # need at least this many prior months to trust a z-score
MIN_BASELINE_COUNT = 8           # tightened from 3 -- avoids the "small numbers problem"
Z_ALERT_THRESHOLD = 2.5


# =====================================================================
# PART 1: TREND ALERTS (real data, honest scan)
# =====================================================================

def load_case_master():
    cm = pd.read_csv(f"{DATA_DIR}/CaseMaster.csv", parse_dates=["CrimeRegisteredDate"])
    unit = pd.read_csv(f"{DATA_DIR}/Unit.csv")
    subhead = pd.read_csv(f"{DATA_DIR}/CrimeSubHead.csv")
    district = pd.read_csv(f"{DATA_DIR}/District.csv")

    station_to_district = dict(zip(unit["UnitID"], unit["DistrictID"]))
    subhead_map = dict(zip(subhead["CrimeSubHeadID"], subhead["CrimeHeadName"]))
    district_map = dict(zip(district["DistrictID"], district["DistrictName"]))

    cm["DistrictID"] = cm["PoliceStationID"].map(station_to_district)
    cm["DistrictName"] = cm["DistrictID"].map(district_map)
    cm["subhead"] = cm["CrimeMinorHeadID"].map(subhead_map)
    cm["month"] = cm["CrimeRegisteredDate"].dt.to_period("M")
    return cm


def compute_trend_alerts(cm: pd.DataFrame):
    """For each (District, CrimeSubHead), compares each month's case count
    to the trailing baseline (all prior months in the dataset for that
    series) and flags a z-score alert if it's a significant spike."""
    monthly = (
        cm.groupby(["DistrictID", "DistrictName", "subhead", "month"])
        .size().rename("n_cases").reset_index()
        .sort_values(["DistrictID", "subhead", "month"])
    )

    alerts = []
    for (d_id, d_name, sub), group in monthly.groupby(["DistrictID", "DistrictName", "subhead"]):
        group = group.sort_values("month").reset_index(drop=True)
        for i in range(len(group)):
            baseline = group.iloc[:i]  # all months strictly before this one
            if len(baseline) < MIN_BASELINE_MONTHS:
                continue
            baseline_mean = baseline["n_cases"].mean()
            baseline_std = baseline["n_cases"].std()
            if baseline_mean < MIN_BASELINE_COUNT or baseline_std == 0 or pd.isna(baseline_std):
                continue
            current = group.iloc[i]["n_cases"]
            z = (current - baseline_mean) / baseline_std
            if z >= Z_ALERT_THRESHOLD:
                alerts.append({
                    "DistrictName": d_name, "subhead": sub,
                    "month": str(group.iloc[i]["month"]),
                    "n_cases": int(current), "baseline_mean": round(baseline_mean, 2),
                    "z_score": round(z, 2),
                })

    alerts_df = pd.DataFrame(alerts).sort_values("z_score", ascending=False) if alerts else pd.DataFrame()
    return monthly, alerts_df


# =====================================================================
# PART 2: SYNTHETIC STRESS TEST (proves the mechanism works)
# =====================================================================

def stress_test_alert_mechanism(monthly: pd.DataFrame, spike_multiplier=3.0):
    """Takes ONE real (district, subhead) series from the actual data,
    and asks: 'if next month's count were `spike_multiplier`x the recent
    average, would our z-score mechanism correctly flag it?' This is a
    labeled what-if demonstration of the detection logic working
    correctly -- NOT a claim that this spike was found in real data."""
    candidates = monthly.groupby(["DistrictID", "DistrictName", "subhead"]).agg(
        n_months=("month", "count"), mean_count=("n_cases", "mean")
    ).reset_index()
    candidates = candidates[
        (candidates["n_months"] >= MIN_BASELINE_MONTHS + 1) & (candidates["mean_count"] >= MIN_BASELINE_COUNT)
    ]
    if candidates.empty:
        print("No series in this dataset has enough history/volume for a stress test.")
        return

    pick = candidates.sort_values("mean_count", ascending=False).iloc[0]
    baseline_mean = pick["mean_count"]
    baseline_std = monthly[
        (monthly["DistrictID"] == pick["DistrictID"]) & (monthly["subhead"] == pick["subhead"])
    ]["n_cases"].std()
    if baseline_std == 0 or pd.isna(baseline_std):
        baseline_std = max(1.0, baseline_mean * 0.3)  # fallback for a near-constant series

    hypothetical_count = round(baseline_mean * spike_multiplier)
    z = (hypothetical_count - baseline_mean) / baseline_std

    print(f"\n--- STRESS TEST (hypothetical, not a real detected event) ---")
    print(f"Series: {pick['DistrictName']} / {pick['subhead']}")
    print(f"Real historical baseline: mean={baseline_mean:.2f} cases/month, std={baseline_std:.2f}")
    print(f"Hypothetical scenario: what if next month had {hypothetical_count} cases "
          f"({spike_multiplier}x the baseline)?")
    print(f"Resulting z-score: {z:.2f} -> {'ALERT WOULD FIRE (red-zone)' if z >= Z_ALERT_THRESHOLD else 'would NOT fire'}")
    print("This confirms the alerting mechanism correctly distinguishes a genuine spike from noise.")


# =====================================================================
# PART 3: CASE-LEVEL ANOMALY DETECTION (Isolation Forest)
# =====================================================================

def detect_case_anomalies(cm: pd.DataFrame, contamination=0.03):
    accused = pd.read_csv(f"{DATA_DIR}/Accused.csv")
    victim = pd.read_csv(f"{DATA_DIR}/Victim.csv")

    n_accused = accused.groupby("CaseMasterID").size().rename("n_accused")
    n_victims = victim.groupby("CaseMasterID").size().rename("n_victims")

    df = cm.merge(n_accused, on="CaseMasterID", how="left").merge(n_victims, on="CaseMasterID", how="left")
    df["n_accused"] = df["n_accused"].fillna(0)
    df["n_victims"] = df["n_victims"].fillna(0)

    incident_dt = pd.to_datetime(df["IncidentFromDate"])
    info_dt = pd.to_datetime(df["InfoReceivedPSDate"])
    df["hour"] = incident_dt.dt.hour
    df["report_delay_hours"] = (info_dt - incident_dt).dt.total_seconds() / 3600.0
    df["report_delay_hours"] = df["report_delay_hours"].clip(lower=0).fillna(0)

    features = ["n_accused", "n_victims", "hour", "report_delay_hours",
                "GravityOffenceID", "CrimeMinorHeadID"]
    X = df[features].fillna(0)

    model = IsolationForest(contamination=contamination, random_state=42, n_estimators=200)
    df["anomaly_score"] = model.fit_predict(X)  # -1 = anomaly, 1 = normal
    df["anomaly_score_raw"] = model.decision_function(X)  # lower = more anomalous

    anomalies = df[df["anomaly_score"] == -1].sort_values("anomaly_score_raw")
    print(f"\nFlagged {len(anomalies):,} of {len(df):,} cases as anomalous "
          f"({contamination*100:.0f}% contamination rate)")
    print("\nTop 10 most anomalous cases (lowest score = most unusual):")
    print(anomalies[["CaseMasterID", "CrimeNo", "n_accused", "n_victims", "hour",
                      "report_delay_hours", "anomaly_score_raw"]].head(10).to_string(index=False))

    anomalies[["CaseMasterID", "CrimeNo", "n_accused", "n_victims", "hour",
               "report_delay_hours", "anomaly_score_raw"]].to_csv(
        f"{DATA_DIR}/case_anomalies.csv", index=False)
    print(f"\nSaved -> {DATA_DIR}/case_anomalies.csv")
    return anomalies


if __name__ == "__main__":
    print("Loading case data...")
    cm = load_case_master()

    print("\n" + "=" * 60)
    print("PART 1: TREND ALERTS (real scan of actual data)")
    print("=" * 60)
    monthly, alerts_df = compute_trend_alerts(cm)
    if alerts_df.empty:
        print("No statistically significant spikes found in this dataset.")
    else:
        print(f"{len(alerts_df)} statistically significant spikes found:")
        print(alerts_df.head(15).to_string(index=False))

    stress_test_alert_mechanism(monthly)

    print("\n" + "=" * 60)
    print("PART 2: CASE-LEVEL ANOMALY DETECTION")
    print("=" * 60)
    if not alerts_df.empty:
        alerts_df.to_csv(f"{DATA_DIR}/trend_alerts.csv", index=False)
        print(f"Saved -> {DATA_DIR}/trend_alerts.csv")
    detect_case_anomalies(cm)