"""
Entity Resolution Engine
========================
Resolves which `Accused` rows (one row per person PER CASE, per the ER
schema) actually refer to the same real individual across different FIRs —
the core gap identified in the schema review (no master identity table
exists for Accused, Complainant, or Victim).

Approach: phonetic blocking (Soundex on surname) to keep comparisons
tractable, weighted similarity scoring (surname + given-name + age
tolerance), threshold-based match graph, then connected-components
clustering (Union-Find) to produce a `ResolvedPersonID` per Accused row.

This is a classic probabilistic record-linkage design (Fellegi-Sunter
lineage), deliberately rule-based rather than a black-box classifier —
in a real deployment, thresholds here would be tuned against a small set
of manually-confirmed matches from investigators, not against unlabeled
production data.
"""

import time
import jellyfish
import pandas as pd

SURNAME_SIM_WEIGHT = 0.45
GIVEN_NAME_SIM_WEIGHT = 0.40
AGE_SIM_WEIGHT = 0.15
SURNAME_HARD_GATE = 0.93   # empirically calibrated: 97%+ of TRUE injected surname variants
                            # score >= this; raising further excludes very few true positives
                            # while cutting most false phonetic-neighbor collisions (Soundex
                            # blocking is deliberately loose, so this gate does the real work)
INITIAL_MATCH_CREDIT = 0.70  # an initial ("M.") matching a full given name's first letter is
                              # weak evidence on its own — full credit here was creating "hub"
                              # records that transitively chained many unrelated people together
MATCH_THRESHOLD = 0.87
AGE_TOLERANCE_FULL = 2   # years; drift within this = full credit
AGE_TOLERANCE_HALF = 4   # years; drift within this = partial credit
AGE_HALF_CREDIT = 0.35


def split_name(name: str):
    parts = str(name).replace(".", ". ").split()
    parts = [p.strip(".") for p in parts if p.strip(".")]
    if not parts:
        return "", ""
    surname = parts[-1]
    given = " ".join(parts[:-1])
    return given, surname


def given_name_similarity(g1: str, g2: str) -> float:
    g1c, g2c = g1.replace(" ", "").lower(), g2.replace(" ", "").lower()
    if not g1c or not g2c:
        return 0.5  # one side has no given name recorded at all — partial credit
    shorter, longer = (g1c, g2c) if len(g1c) <= len(g2c) else (g2c, g1c)
    if len(shorter) <= 2:  # looks like an initial (e.g. "E" for "Edhitha")
        return INITIAL_MATCH_CREDIT if longer.startswith(shorter) else 0.0
    return jellyfish.jaro_winkler_similarity(g1c, g2c)


def age_similarity(a1, a2) -> float:
    if pd.isna(a1) or pd.isna(a2):
        return 0.5
    diff = abs(a1 - a2)
    return 1.0 if diff <= AGE_TOLERANCE_FULL else 0.0


def pair_score(row1, row2):
    """Returns None if the pair fails the hard surname gate (not a candidate
    at all), otherwise the weighted similarity score."""
    surname_sim = jellyfish.jaro_winkler_similarity(row1["surname"], row2["surname"])
    if surname_sim < SURNAME_HARD_GATE:
        return None
    given_sim = given_name_similarity(row1["given"], row2["given"])
    age_sim = age_similarity(row1["AgeYear"], row2["AgeYear"])
    return (
        SURNAME_SIM_WEIGHT * surname_sim
        + GIVEN_NAME_SIM_WEIGHT * given_sim
        + AGE_SIM_WEIGHT * age_sim
    )


class UnionFind:
    def __init__(self, ids):
        self.parent = {i: i for i in ids}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x, y):
        rx, ry = self.find(x), self.find(y)
        if rx != ry:
            self.parent[ry] = rx


def compute_candidate_pairs(df: pd.DataFrame, max_block_size: int = 700):
    """Computes every candidate pair's score ONCE (respecting the hard surname
    gate). Returns a list of (id1, id2, score) so clustering can be re-run at
    different MATCH_THRESHOLDs without repeating the expensive similarity work."""
    t0 = time.time()
    candidate_pairs = []
    n_comparisons = 0
    n_blocks_oversize = 0

    for block_key, group in df.groupby("block_key"):
        records = group[["AccusedMasterID", "given", "surname", "AgeYear"]].to_dict("records")
        n = len(records)
        if n < 2:
            continue
        if n > max_block_size:
            n_blocks_oversize += 1
            sub = group.copy()
            sub["age_decade"] = (sub["AgeYear"].fillna(-1) // 10)
            for _, subgroup in sub.groupby("age_decade"):
                sub_records = subgroup[["AccusedMasterID", "given", "surname", "AgeYear"]].to_dict("records")
                for i in range(len(sub_records)):
                    for j in range(i + 1, len(sub_records)):
                        n_comparisons += 1
                        score = pair_score(sub_records[i], sub_records[j])
                        if score is not None:
                            candidate_pairs.append(
                                (sub_records[i]["AccusedMasterID"], sub_records[j]["AccusedMasterID"], score))
            continue

        for i in range(n):
            for j in range(i + 1, n):
                n_comparisons += 1
                score = pair_score(records[i], records[j])
                if score is not None:
                    candidate_pairs.append((records[i]["AccusedMasterID"], records[j]["AccusedMasterID"], score))

    elapsed = time.time() - t0
    print(f"Candidate scoring done in {elapsed:.1f}s | {n_comparisons:,} pairwise comparisons "
          f"| {len(candidate_pairs):,} passed the surname gate | {n_blocks_oversize} oversized blocks")
    return candidate_pairs


def cluster_at_threshold(all_ids, candidate_pairs, threshold):
    uf = UnionFind(all_ids)
    for id1, id2, score in candidate_pairs:
        if score >= threshold:
            uf.union(id1, id2)
    return {i: uf.find(i) for i in all_ids}


def prepare_accused_df(accused_df: pd.DataFrame):
    df = accused_df.copy()
    df["given"], df["surname"] = zip(*df["AccusedName"].map(split_name))
    df["surname_soundex"] = df["surname"].map(lambda s: jellyfish.soundex(s) if s else "")
    df["block_key"] = df["surname_soundex"] + "_" + df["GenderID"].astype(str)
    return df


def resolve_entities(accused_df: pd.DataFrame, max_block_size: int = 700):
    """Convenience wrapper: single-threshold resolve (uses module MATCH_THRESHOLD)."""
    df = prepare_accused_df(accused_df)
    candidate_pairs = compute_candidate_pairs(df, max_block_size)
    resolved_map = cluster_at_threshold(df["AccusedMasterID"].tolist(), candidate_pairs, MATCH_THRESHOLD)
    df["ResolvedPersonID"] = df["AccusedMasterID"].map(resolved_map)
    return df[["AccusedMasterID", "CaseMasterID", "AccusedName", "AgeYear", "GenderID", "ResolvedPersonID"]]


if __name__ == "__main__":
    accused = pd.read_csv("../synthetic_data/Accused.csv")
    resolved = resolve_entities(accused)
    out_path = "../synthetic_data/resolved_persons.csv"
    resolved.to_csv(out_path, index=False)
    n_clusters = resolved["ResolvedPersonID"].nunique()
    print(f"\n{len(resolved):,} accused rows resolved into {n_clusters:,} distinct predicted persons")
    print(f"Saved -> {out_path}")
