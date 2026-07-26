"""
Sweeps MATCH_THRESHOLD to show the real precision/recall tradeoff, instead
of reporting one cherry-picked operating point. Candidate pair scoring
(the expensive part) runs ONCE; only the cheap union-find clustering step
re-runs per threshold.
"""

import pandas as pd
import entity_resolution as er
from evaluate_entity_resolution import evaluate

ACCUSED_PATH = "../synthetic_data/Accused.csv"
GT_PATH = "../synthetic_data/entity_resolution_ground_truth.csv"

THRESHOLDS = [0.80, 0.83, 0.85, 0.87, 0.89, 0.91, 0.93, 0.95]


def main():
    accused = pd.read_csv(ACCUSED_PATH)
    gt = pd.read_csv(GT_PATH)

    df = er.prepare_accused_df(accused)
    candidate_pairs = er.compute_candidate_pairs(df)
    all_ids = df["AccusedMasterID"].tolist()

    results = []
    for t in THRESHOLDS:
        resolved_map = er.cluster_at_threshold(all_ids, candidate_pairs, t)
        df["ResolvedPersonID"] = df["AccusedMasterID"].map(resolved_map)
        eval_df = df[["AccusedMasterID", "CaseMasterID", "AccusedName", "AgeYear", "GenderID", "ResolvedPersonID"]]
        print(f"\n### Threshold = {t} ###")
        metrics = evaluate(eval_df, gt)
        metrics["threshold"] = t
        results.append(metrics)

    print("\n" + "=" * 70)
    print("THRESHOLD SWEEP SUMMARY")
    print("=" * 70)
    print(f"{'Threshold':>10} | {'Precision':>10} | {'Recall':>10} | {'F1':>10} | {'#Clusters':>10}")
    for m in results:
        print(f"{m['threshold']:>10} | {m['precision']:>10.4f} | {m['recall']:>10.4f} | "
              f"{m['f1']:>10.4f} | {m['n_pred_clusters']:>10,}")

    best = max(results, key=lambda m: m["f1"])
    print(f"\nBest F1 at threshold={best['threshold']}: "
          f"P={best['precision']:.4f} R={best['recall']:.4f} F1={best['f1']:.4f}")


if __name__ == "__main__":
    main()
