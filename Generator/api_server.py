"""
CrimeGraph API Server
======================
Serves all analytical outputs as clean REST JSON endpoints for the frontend.
In the Catalyst deployment, each endpoint here becomes a Catalyst Function;
this Flask server is the local-dev equivalent so the frontend can be built
and tested before that migration.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import json
import os

app = Flask(__name__)
CORS(app)

DATA_DIR = "../synthetic_data"


def load_csv(name):
    return pd.read_csv(f"{DATA_DIR}/{name}.csv")


@app.route("/api/districts")
def get_districts():
    district = load_csv("District")
    overlay = load_csv("district_socioeconomic_overlay")
    merged = district.merge(overlay, on=["DistrictID", "DistrictName"], how="left")
    return jsonify(merged.to_dict(orient="records"))


@app.route("/api/cases")
def get_cases():
    cm = load_csv("CaseMaster")
    unit = load_csv("Unit")
    subhead = load_csv("CrimeSubHead")

    station_to_district = dict(zip(unit["UnitID"], unit["DistrictID"]))
    subhead_map = dict(zip(subhead["CrimeSubHeadID"], subhead["CrimeHeadName"]))
    cm["DistrictID"] = cm["PoliceStationID"].map(station_to_district)
    cm["subhead"] = cm["CrimeMinorHeadID"].map(subhead_map)
    cm["hour"] = pd.to_datetime(cm["IncidentFromDate"]).dt.hour

    district_id = request.args.get("district_id", type=int)
    if district_id:
        cm = cm[cm["DistrictID"] == district_id]

    cm = cm.dropna(subset=["latitude", "longitude"])
    cols = ["CaseMasterID", "CrimeNo", "latitude", "longitude", "subhead",
            "CrimeRegisteredDate", "GravityOffenceID", "DistrictID", "PoliceStationID", "hour"]
    return jsonify(cm[cols].head(3000).to_dict(orient="records"))


@app.route("/api/network")
def get_network():
    with open(f"{DATA_DIR}/network_graph.json") as f:
        return jsonify(json.load(f))


@app.route("/api/repeat-offenders")
def get_repeat_offenders():
    df = load_csv("repeat_offender_profiles")
    df = df[df["n_cases"] >= 2].sort_values("n_cases", ascending=False)
    return jsonify(df.head(200).to_dict(orient="records"))


@app.route("/api/mo-signatures")
def get_mo_signatures():
    df = load_csv("mo_signatures")
    df = df[df["mo_consistency"] >= 0.6].sort_values("mo_consistency", ascending=False)
    return jsonify(df.head(200).to_dict(orient="records"))


@app.route("/api/anomalies")
def get_anomalies():
    df = load_csv("case_anomalies")
    return jsonify(df.to_dict(orient="records"))


@app.route("/api/stats")
def get_stats():
    """Summary numbers for the dashboard header."""
    cm = load_csv("CaseMaster")
    accused = load_csv("Accused")
    resolved = load_csv("resolved_persons")
    repeat = load_csv("repeat_offender_profiles")
    anomalies = load_csv("case_anomalies")

    return jsonify({
        "total_cases": len(cm),
        "total_accused_entries": len(accused),
        "resolved_persons": resolved["ResolvedPersonID"].nunique(),
        "repeat_offenders": len(repeat[repeat["n_cases"] >= 2]),
        "cross_jurisdiction_offenders": len(repeat[repeat["cross_jurisdiction"] == True]),
        "anomalous_cases_flagged": len(anomalies),
    })

@app.route("/api/trend-alerts")
def get_trend_alerts():
    path = f"{DATA_DIR}/trend_alerts.csv"
    if not os.path.exists(path):
        return jsonify([])
    return jsonify(pd.read_csv(path).to_dict(orient="records"))


@app.route("/api/district-centroids")
def get_district_centroids():
    cm = load_csv("CaseMaster")
    unit = load_csv("Unit")
    district = load_csv("District")
    station_to_district = dict(zip(unit["UnitID"], unit["DistrictID"]))
    cm["DistrictID"] = cm["PoliceStationID"].map(station_to_district)
    cm = cm.dropna(subset=["latitude", "longitude"])
    centroids = cm.groupby("DistrictID")[["latitude", "longitude"]].mean().reset_index()
    centroids.columns = ["DistrictID", "avg_lat", "avg_lon"]
    centroids = centroids.merge(district[["DistrictID", "DistrictName"]], on="DistrictID")
    return jsonify(centroids.to_dict(orient="records"))

@app.route("/api/top-offenders")
def get_top_offenders():
    """List of repeat offenders for the network search panel. Filtered to
    a plausible case-count range (2-15) -- higher counts in this dataset
    are almost always entity-resolution over-merge artifacts, documented
    in ENTITY_RESOLUTION_RESULTS.md, not real individuals. Showing those
    at the top of a 'most active offenders' list would misrepresent the
    tool's actual accuracy."""
    profiles = load_csv("repeat_offender_profiles")
    subhead = load_csv("CrimeSubHead")
    mo = load_csv("mo_signatures")

    sub_map = dict(zip(subhead["CrimeSubHeadID"], subhead["CrimeHeadName"]))
    plausible = profiles[(profiles["n_cases"] >= 2) & (profiles["n_cases"] <= 15)].copy()
    plausible["dominant_crime"] = plausible["dominant_crime_subhead_id"].map(sub_map)
    plausible = plausible.merge(
        mo[["ResolvedPersonID", "dominant_mo_phrase", "mo_consistency"]],
        on="ResolvedPersonID", how="left"
    )
    plausible = plausible.sort_values("n_cases", ascending=False).head(150)
    return jsonify(plausible.to_dict(orient="records"))


@app.route("/api/network/person/<int:person_id>")
def get_person_network(person_id):
    """1-hop ego network for one resolved person -- direct co-accused
    links only. Every node in the full graph has a manageable 1-hop
    neighborhood (max ~133 nodes even for the largest hub), so no
    additional capping is needed here."""
    with open(f"{DATA_DIR}/network_graph.json") as f:
        full_graph = json.load(f)

    edges = [e for e in full_graph["edges"] if e["source"] == person_id or e["target"] == person_id]
    connected_ids = {person_id}
    for e in edges:
        connected_ids.add(e["source"])
        connected_ids.add(e["target"])

    nodes = [n for n in full_graph["nodes"] if n["id"] in connected_ids]
    return jsonify({"nodes": nodes, "edges": edges, "center_id": person_id})

@app.route("/api/risk-scores")
def get_risk_scores():
    path = f"{DATA_DIR}/case_risk_scores.csv"
    if not os.path.exists(path):
        return jsonify([])
    df = pd.read_csv(path)
    return jsonify(df.head(100).to_dict(orient="records"))

@app.route("/api/stations")
def get_stations():
    unit = load_csv("Unit")
    cm = load_csv("CaseMaster")
    district_id = request.args.get("district_id", type=int)

    stations = unit[unit["TypeID"] == 5].copy()  # TypeID 5 = Police Station
    if district_id:
        stations = stations[stations["DistrictID"] == district_id]

    case_counts = cm.groupby("PoliceStationID").size().rename("case_count")
    coords = cm.dropna(subset=["latitude", "longitude"]).groupby("PoliceStationID")[["latitude", "longitude"]].mean()

    stations = stations.merge(case_counts, left_on="UnitID", right_index=True, how="left")
    stations = stations.merge(coords, left_on="UnitID", right_index=True, how="left")
    stations["case_count"] = stations["case_count"].fillna(0)
    stations = stations.sort_values("case_count", ascending=False)

    return jsonify(stations[["UnitID", "UnitName", "case_count", "latitude", "longitude"]].to_dict(orient="records"))

@app.route("/api/network/person/<int:person_id>/full")
def get_person_full_network(person_id):
    """Extends the co-accused network with victim and location nodes --
    directly answers the brief's 'connections between suspects, victims,
    and recurring locations' requirement."""
    resolved = load_csv("resolved_persons")
    victim = load_csv("Victim")
    unit = load_csv("Unit")
    cm = load_csv("CaseMaster")
    with open(f"{DATA_DIR}/network_graph.json") as f:
        full_graph = json.load(f)

    edges = [e for e in full_graph["edges"] if e["source"] == person_id or e["target"] == person_id]
    connected_ids = {person_id}
    for e in edges:
        connected_ids.add(e["source"]); connected_ids.add(e["target"])
    suspect_nodes = [dict(n, node_type="suspect") for n in full_graph["nodes"] if n["id"] in connected_ids]

    person_cases = resolved[resolved["ResolvedPersonID"] == person_id]["CaseMasterID"].tolist()

    vics = victim[victim["CaseMasterID"].isin(person_cases)]
    victim_nodes = [
        {"id": f"v{row.VictimMasterID}", "node_type": "victim", "label": row.VictimName, "n_cases": 1}
        for row in vics.itertuples()
    ]
    victim_edges = [
        {"source": person_id, "target": f"v{row.VictimMasterID}", "weight": 1, "edge_type": "victim"}
        for row in vics.itertuples()
    ]

    case_stations = cm[cm["CaseMasterID"].isin(person_cases)][["CaseMasterID", "PoliceStationID"]]
    station_ids = case_stations["PoliceStationID"].unique().tolist()
    station_names = dict(zip(unit["UnitID"], unit["UnitName"]))
    location_nodes = [
        {"id": f"s{sid}", "node_type": "location", "label": station_names.get(sid, f"Station {sid}"), "n_cases": 1}
        for sid in station_ids
    ]
    location_edges = [
        {"source": person_id, "target": f"s{sid}", "weight": 1, "edge_type": "location"}
        for sid in station_ids
    ]

    return jsonify({
        "nodes": suspect_nodes + victim_nodes + location_nodes,
        "edges": edges + victim_edges + location_edges,
        "center_id": person_id,
    })

if __name__ == "__main__":
    print("Starting CrimeGraph API server on http://localhost:5000 ...")
    app.run(debug=True, port=5000)