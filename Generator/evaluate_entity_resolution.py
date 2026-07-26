"""
Evaluates the entity resolution output against the known ground truth
(entity_resolution_ground_truth.csv + the assumption that any Accused row
NOT in that file is a true singleton — a distinct real person appearing
exactly once, per how the generator built it).

Standard record-linkage evaluation: pairwise precision/recall/F1 over all
same-person pairs, computed via combinatorics per cluster (no need to
materialize every pair explicitly, which would be too slow at this scale).
"""

from itertools import combinations
from collections import defaultdict
import pandas as pd


def cluster_sizes_to_pair_count(sizes):
    return sum(n * (n - 1) // 2 for n in sizes)


def build_true_clusters(accused_ids, ground_truth_df):
    """Every AccusedMasterID not in ground_truth is its own singleton true person."""
    true_cluster = {}
    for _, row in ground_truth_df.iterrows():
        true_cluster[row["AccusedMasterID"]] = f"gt_{row['person_master_id']}"
    next_singleton = 0
    for aid in accused_ids:
        if aid not in true_cluster:
            true_cluster[aid] = f"singleton_{next_singleton}"
            next_singleton += 1
    return true_cluster


def evaluate(resolved_df: pd.DataFrame, ground_truth_df: pd.DataFrame):
    accused_ids = resolved_df["AccusedMasterID"].tolist()
    true_cluster = build_true_clusters(accused_ids, ground_truth_df)

    resolved_df = resolved_df.copy()
    resolved_df["true_cluster"] = resolved_df["AccusedMasterID"].map(true_cluster)

    # ---- True positive pairs: same true_cluster AND same ResolvedPersonID ----
    tp = 0
    for _, grp in resolved_df.groupby("true_cluster"):
        for _, sub in grp.groupby("ResolvedPersonID"):
            n = len(sub)
            tp += n * (n - 1) // 2

    # ---- Total actual same-person pairs (recall denominator) ----
    true_sizes = resolved_df.groupby("true_cluster").size().tolist()
    total_true_pairs = cluster_sizes_to_pair_count(true_sizes)

    # ---- Total predicted same-person pairs (precision denominator) ----
    pred_sizes = resolved_df.groupby("ResolvedPersonID").size().tolist()
    total_pred_pairs = cluster_sizes_to_pair_count(pred_sizes)

    precision = tp / total_pred_pairs if total_pred_pairs else 0.0
    recall = tp / total_true_pairs if total_true_pairs else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    n_true_clusters = resolved_df["true_cluster"].nunique()
    n_pred_clusters = resolved_df["ResolvedPersonID"].nunique()

    print("=" * 60)
    print("ENTITY RESOLUTION EVALUATION")
    print("=" * 60)
    print(f"Total accused rows           : {len(resolved_df):,}")
    print(f"True distinct persons        : {n_true_clusters:,}")
    print(f"Predicted distinct persons    : {n_pred_clusters:,}")
    print(f"True same-person pairs        : {total_true_pairs:,}")
    print(f"Predicted same-person pairs   : {total_pred_pairs:,}")
    print(f"Correct (true positive) pairs : {tp:,}")
    print("-" * 60)
    print(f"Precision : {precision:.4f}")
    print(f"Recall    : {recall:.4f}")
    print(f"F1        : {f1:.4f}")
    print("=" * 60)
    return {"precision": precision, "recall": recall, "f1": f1,
            "n_true_clusters": n_true_clusters, "n_pred_clusters": n_pred_clusters}


if __name__ == "__main__":
    resolved = pd.read_csv("../synthetic_data/resolved_persons.csv")
    gt = pd.read_csv("../synthetic_data/entity_resolution_ground_truth.csv")
    evaluate(resolved, gt)
