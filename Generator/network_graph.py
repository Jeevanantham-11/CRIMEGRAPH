"""
Criminal Network & Link Analysis
================================
Uses the entity-resolved identities (resolved_persons.csv) to build the
actual criminal network the brief asks for:
  - Relationship mapping: node graph of co-accused (people charged together)
  - Repeat offender tracking: which resolved persons appear across multiple
    FIRs, and in how many districts (cross-jurisdiction MO tracking)
  - Association detection: connected components / communities = suspected
    organized-crime clusters, not spottable in isolated Excel sheets

Nodes = ResolvedPersonID (a real individual, post entity-resolution)
Edges = two persons named as co-accused in the same CaseMasterID, weighted
        by how many cases they share

Output: a JSON file ready to feed a D3.js force-directed graph in the
frontend, plus a CSV of repeat-offender profiles for the dashboard table.
"""

import json
from collections import defaultdict
from itertools import combinations

import pandas as pd
import networkx as nx
import community as community_louvain

DATA_DIR = "../synthetic_data"
OUT_DIR = "../synthetic_data"


def build_network():
    resolved = pd.read_csv(f"{DATA_DIR}/resolved_persons.csv")
    case_master = pd.read_csv(f"{DATA_DIR}/CaseMaster.csv")
    unit = pd.read_csv(f"{DATA_DIR}/Unit.csv")

    # Map CaseMasterID -> DistrictID (via PoliceStationID -> Unit.DistrictID)
    station_to_district = dict(zip(unit["UnitID"], unit["DistrictID"]))
    case_master["DistrictID"] = case_master["PoliceStationID"].map(station_to_district)
    case_to_district = dict(zip(case_master["CaseMasterID"], case_master["DistrictID"]))
    case_to_subhead = dict(zip(case_master["CaseMasterID"], case_master["CrimeMinorHeadID"]))

    # ---------------- Build co-accused edges ----------------
    persons_per_case = resolved.groupby("CaseMasterID")["ResolvedPersonID"].apply(
        lambda x: sorted(set(x))
    )

    edge_weight = defaultdict(int)
    edge_cases = defaultdict(list)
    for case_id, persons in persons_per_case.items():
        if len(persons) < 2:
            continue
        for p1, p2 in combinations(persons, 2):
            edge_weight[(p1, p2)] += 1
            edge_cases[(p1, p2)].append(case_id)

    G = nx.Graph()
    for (p1, p2), w in edge_weight.items():
        G.add_edge(p1, p2, weight=w)

    print(f"Network built: {G.number_of_nodes():,} nodes (persons with co-accused links), "
          f"{G.number_of_edges():,} edges")

    # ---------------- Community detection (suspected associate clusters) ----------------
    if G.number_of_edges() > 0:
        partition = community_louvain.best_partition(G, weight="weight", random_state=42)
    else:
        partition = {}
    n_communities = len(set(partition.values())) if partition else 0
    print(f"Detected {n_communities:,} communities (candidate organized-crime clusters)")

    # ---------------- Repeat-offender + cross-jurisdiction profile ----------------
    person_cases = resolved.groupby("ResolvedPersonID")["CaseMasterID"].apply(list)
    profiles = []
    for person_id, case_ids in person_cases.items():
        n_cases = len(case_ids)
        districts = {case_to_district.get(c) for c in case_ids if case_to_district.get(c) is not None}
        subheads = [case_to_subhead.get(c) for c in case_ids if case_to_subhead.get(c) is not None]
        degree = G.degree(person_id, weight=None) if person_id in G else 0
        profiles.append({
            "ResolvedPersonID": person_id,
            "n_cases": n_cases,
            "n_districts": len(districts),
            "cross_jurisdiction": len(districts) > 1,
            "n_co_accused_links": degree,
            "community_id": partition.get(person_id, -1),
            "dominant_crime_subhead_id": max(set(subheads), key=subheads.count) if subheads else None,
        })

    profiles_df = pd.DataFrame(profiles).sort_values(
        ["n_cases", "n_districts"], ascending=False
    )

    repeat_offenders = profiles_df[profiles_df["n_cases"] >= 2]
    cross_jurisdiction = profiles_df[profiles_df["cross_jurisdiction"]]
    print(f"\n{len(repeat_offenders):,} resolved persons are repeat offenders (2+ FIRs)")
    print(f"{len(cross_jurisdiction):,} of them operate across multiple districts")

    profiles_df.to_csv(f"{OUT_DIR}/repeat_offender_profiles.csv", index=False)

    # ---------------- Export graph for D3 frontend ----------------
    nodes = [
        {
            "id": int(pid),
            "n_cases": int(profiles_df.loc[profiles_df["ResolvedPersonID"] == pid, "n_cases"].values[0])
            if pid in profiles_df["ResolvedPersonID"].values else 1,
            "community": partition.get(pid, -1),
        }
        for pid in G.nodes()
    ]
    edges = [
        {"source": int(p1), "target": int(p2), "weight": w, "shared_cases": edge_cases[(p1, p2)]}
        for (p1, p2), w in edge_weight.items()
    ]
    graph_json = {"nodes": nodes, "edges": edges}
    with open(f"{OUT_DIR}/network_graph.json", "w") as f:
        json.dump(graph_json, f)
    print(f"\nGraph exported -> {OUT_DIR}/network_graph.json "
          f"({len(nodes):,} nodes, {len(edges):,} edges)")

    return profiles_df, G, partition


if __name__ == "__main__":
    build_network()
