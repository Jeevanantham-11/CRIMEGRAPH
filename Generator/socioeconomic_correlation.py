"""
Socio-Economic Correlation Overlay
====================================
Brief requirement: "Socio-Economic Correlation: Overlays crime data with
urbanization patterns, population distribution, and socio-economic
indicators to understand the 'why' behind the 'where'."

IMPORTANT — read before presenting results:
Real district-level socio-economic indicators (population, urbanization %,
literacy rate, unemployment rate) are NOT available in this ER schema or
in any public dataset we've pulled in here. For this prototype, indicators
are synthetically generated, anchored to each district's real relative
population weight (from config.py), which already drives real case volume
in the generator.

To make the OVERLAY MECHANISM itself demonstrable (not just a stub that
shows nothing), unemployment_rate is deliberately constructed to correlate
with each district's REAL property-crime rate (computed from actual
CaseMaster data) -- mirroring economic-strain theory, one of the most
replicated findings in criminology (economic hardship correlates with
property crime). This is a designed demonstration, not a real finding.

literacy_rate, by contrast, is generated WITHOUT any injected relationship
to crime rate, specifically to prove the tool correctly reports "no
significant correlation" when none exists -- rather than always finding
whatever pattern it's pointed at. Production deployment would replace both
indicators with real data from Karnataka's Directorate of Economics and
Statistics / Census, and whatever correlation is found there would be a
real empirical result to interpret carefully (correlation is not causation,
and any such finding needs careful, non-stigmatizing framing before use in
policy).
"""

import random
import numpy as np
import pandas as pd
from scipy import stats

import config as cfg

DATA_DIR = "../synthetic_data"
random.seed(7)
np.random.seed(7)

KARNATAKA_TOTAL_POPULATION = 64_000_000  # approx order-of-magnitude anchor


def load_case_master():
    cm = pd.read_csv(f"{DATA_DIR}/CaseMaster.csv")
    unit = pd.read_csv(f"{DATA_DIR}/Unit.csv")
    subhead = pd.read_csv(f"{DATA_DIR}/CrimeSubHead.csv")
    district = pd.read_csv(f"{DATA_DIR}/District.csv")

    station_to_district = dict(zip(unit["UnitID"], unit["DistrictID"]))
    subhead_map = dict(zip(subhead["CrimeSubHeadID"], subhead["CrimeHeadName"]))
    cm["DistrictID"] = cm["PoliceStationID"].map(station_to_district)
    cm["subhead"] = cm["CrimeMinorHeadID"].map(subhead_map)
    return cm, district


PROPERTY_SUBHEADS = {"Theft", "Auto Theft", "Burglary", "Robbery", "Dacoity", "Criminal Breach of Trust"}


def build_district_indicators(cm: pd.DataFrame, district: pd.DataFrame):
    total_weight = sum(w for _, w in cfg.DISTRICTS)
    weight_map = dict(cfg.DISTRICTS)

    total_cases = cm.groupby("DistrictID").size().rename("total_cases")
    property_cases = cm[cm["subhead"].isin(PROPERTY_SUBHEADS)].groupby("DistrictID").size().rename("property_cases")

    rows = []
    for _, d in district.iterrows():
        d_id, d_name = d["DistrictID"], d["DistrictName"]
        weight = weight_map[d_name]
        population = round(KARNATAKA_TOTAL_POPULATION * (weight / total_weight))

        # Urbanization scales with relative weight (bigger/denser districts = more urban)
        urbanization_pct = round(min(95, 20 + 60 * (weight / max(w for _, w in cfg.DISTRICTS))), 1)
        # Literacy correlates with urbanization (real, well-established pattern) + noise,
        # but has NO relationship to crime rate injected -- a genuine "control" indicator.
        literacy_rate = round(min(95, max(60, 68 + urbanization_pct * 0.22 + random.gauss(0, 3))), 1)

        rows.append({
            "DistrictID": d_id, "DistrictName": d_name, "population": population,
            "urbanization_pct": urbanization_pct, "literacy_rate": literacy_rate,
        })

    df = pd.DataFrame(rows)
    df = df.merge(total_cases, on="DistrictID", how="left").merge(property_cases, on="DistrictID", how="left")
    df["total_cases"] = df["total_cases"].fillna(0)
    df["property_cases"] = df["property_cases"].fillna(0)

    df["crime_rate_per_100k"] = df["total_cases"] / df["population"] * 100_000
    df["property_crime_rate_per_100k"] = df["property_cases"] / df["population"] * 100_000

    # unemployment_rate DELIBERATELY built to correlate with property crime rate
    # (see module docstring) -- normalized then scaled into a realistic 3-14% band.
    normalized = (df["property_crime_rate_per_100k"] - df["property_crime_rate_per_100k"].min()) / (
        df["property_crime_rate_per_100k"].max() - df["property_crime_rate_per_100k"].min()
    )
    df["unemployment_rate"] = round(3 + normalized * 8 + np.random.normal(0, 0.8, len(df)), 1).clip(2, 15)

    return df


def run_correlation_analysis(df: pd.DataFrame):
    print("\n" + "=" * 60)
    print("CORRELATION 1: unemployment_rate vs property_crime_rate_per_100k")
    print("(deliberately modeled relationship -- demonstrates the overlay mechanism)")
    print("=" * 60)
    r1, p1 = stats.pearsonr(df["unemployment_rate"], df["property_crime_rate_per_100k"])
    print(f"Pearson r = {r1:.3f} (p = {p1:.4f})")
    print("Interpretation: as designed, higher-unemployment districts show higher property "
          "crime rates in this synthetic dataset -- consistent with economic-strain theory. "
          "This is a MODELED relationship for this prototype, not an empirical finding.")

    print("\n" + "=" * 60)
    print("CORRELATION 2: literacy_rate vs total crime_rate_per_100k")
    print("(NO relationship was injected -- this is the honesty check)")
    print("=" * 60)
    r2, p2 = stats.pearsonr(df["literacy_rate"], df["crime_rate_per_100k"])
    print(f"Pearson r = {r2:.3f} (p = {p2:.4f})")
    if abs(r2) < 0.3 or p2 > 0.05:
        print("Correctly shows NO significant correlation -- proving the module distinguishes "
              "real signal from non-signal rather than reporting a pattern regardless of "
              "whether one exists.")
    else:
        print("Note: some incidental correlation appeared despite none being injected -- "
              "consistent with the same small-sample-noise caveat raised in the risk-scoring "
              "fairness audit. Worth re-running with a different random seed to check stability.")

    print("\n" + "=" * 60)
    print("Top 5 districts by property crime rate (for the overlay dashboard)")
    print("=" * 60)
    print(df.sort_values("property_crime_rate_per_100k", ascending=False)
          [["DistrictName", "population", "urbanization_pct", "unemployment_rate",
            "property_crime_rate_per_100k"]].head(5).to_string(index=False))


if __name__ == "__main__":
    print("Loading case data and building district indicators...")
    cm, district = load_case_master()
    df = build_district_indicators(cm, district)
    df.to_csv(f"{DATA_DIR}/district_socioeconomic_overlay.csv", index=False)
    print(f"Saved -> {DATA_DIR}/district_socioeconomic_overlay.csv ({len(df)} districts)")

    run_correlation_analysis(df)