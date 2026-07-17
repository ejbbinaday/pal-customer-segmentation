"""v3 prototype clustering — Stages P4–P5 (improved).

Improvements over the first pass (see docs/knowledge-base.md §15, docs/v3-prototype-findings.md):
  • hold-out split          — fit on train, score a held-out test set inductively
  • compact features (24)    — Tier-3 pruning of the 19 collinear/duplicate columns
  • mixed-type scaling       — StandardScaler on continuous cols only; binaries kept {0,1}
  • decoupled penalties      — HDBSCAN discovery is UNWEIGHTED; penalties enter only in the
                               cost metric (not the feature space)
  • Unassigned bucket        — rows past a distance threshold are left low-confidence, not forced
  • negative learning (P3b)  — applied in features_v3.build()

Deployable scorer = (fitted scaler + proxy-seed segment centroids + distance threshold);
HDBSCAN is used for the unsupervised structure check, nearest-centroid for inductive labelling.

Note: recall here is still measured vs proxy labels (circular) until SME ground-truth arrives.
Drop a `data/labels/sme_sample.csv` (cols: `Unique Identifier`,`true_segment`) to get a real
hold-out recall — the script picks it up automatically.

Run:
    python src/prototype_v3.py    → outputs/prototype_v3_output/
"""

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from sklearn.cluster import HDBSCAN
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from features_v3 import (  # noqa: E402
    CONTINUOUS_FEATURES,
    build,
    build_compact_matrix,
)
from monitor_metrics import dbcv  # noqa: E402
from pal_colors import SEG_COLORS  # noqa: E402

OUTPUT = ROOT / "outputs" / "prototype_v3_output"
SME_LABELS = ROOT / "data" / "labels" / "sme_sample.csv"

PENALTY = {  # used ONLY for cost-weighting misclassifications (not the feature space)
    "Corporate": 10,
    "Mabuhay Loyalist": 8,
    "OFW/Migrant": 5,
    "Premium Bleisure": 4,
    "Pilgrimage": 3,
    "Balikbayan/VFR": 2,
    "Family": 2,
    "Digital Nomad": 2,
    "Last-Minute": 1,
    "Budget/Adventure": 1,
}
TEST_SIZE = 0.2
MIN_CLUSTER_SIZE = 30
MIN_SAMPLES = 5
MIN_SEED = 5  # min proxy rows for a segment to be a mapping target
UNASSIGNED_PCTL = 95  # train nearest-centroid distance percentile → low-confidence cut


def _scale(scaler: StandardScaler, X: pd.DataFrame) -> np.ndarray:
    """Scale continuous columns; leave binary flags at {0,1} (mixed-type handling)."""
    out = X.copy()
    out[CONTINUOUS_FEATURES] = scaler.transform(X[CONTINUOUS_FEATURES])
    return out.to_numpy(dtype=float)


def _assign(
    rows: np.ndarray, centroids: np.ndarray, names: list[str], threshold: float
) -> tuple[np.ndarray, np.ndarray]:
    """Inductive labeller: nearest seed centroid, or 'Unassigned' past the distance threshold."""
    d = cdist(rows, centroids)
    nearest = d.argmin(axis=1)
    mind = d.min(axis=1)
    segs = np.array([names[i] for i in nearest], dtype=object)
    segs[mind > threshold] = "Unassigned"
    return segs, mind


def _recall_and_cost(truth: pd.Series, pred: pd.Series) -> dict:
    per_seg, cost, total = {}, 0.0, len(truth)
    for seg in sorted(truth.unique()):
        sub = truth == seg
        hits = int(((pred == seg) & sub).sum())
        per_seg[seg] = round(hits / int(sub.sum()), 3)
        cost += (int(sub.sum()) - hits) * PENALTY.get(seg, 1)
    return {
        "per_segment_recall": per_seg,
        "weighted_cost": round(cost, 1),
        "cost_per_record": round(cost / total, 3) if total else None,
        "n": total,
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    print("P1–P3(+P3b) — building v3 features (with negative learning) ...")
    df = build().reset_index(drop=True)
    X = build_compact_matrix(df)
    proxy = df["proxy_segment"]

    # hold-out split (stratify on proxy label when every class has >= 2 members)
    strat = proxy if proxy.value_counts().min() >= 2 else None
    idx = np.arange(len(df))
    itr, ite = train_test_split(idx, test_size=TEST_SIZE, random_state=42, stratify=strat)
    print(f"       split: train={len(itr)}  test={len(ite)}  (stratified={strat is not None})")

    scaler = StandardScaler().fit(X.iloc[itr][CONTINUOUS_FEATURES])
    Xtr, Xte = _scale(scaler, X.iloc[itr]), _scale(scaler, X.iloc[ite])
    proxy_tr, proxy_te = (
        proxy.iloc[itr].reset_index(drop=True),
        proxy.iloc[ite].reset_index(drop=True),
    )

    # P4 discovery — UNWEIGHTED HDBSCAN on train (structure check only)
    print(f"P4 — HDBSCAN discovery on train (min_cluster_size={MIN_CLUSTER_SIZE}, unweighted) ...")
    labels = HDBSCAN(min_cluster_size=MIN_CLUSTER_SIZE, min_samples=MIN_SAMPLES).fit_predict(Xtr)
    n_clusters = len({c for c in labels if c != -1})
    noise_pct = float((labels == -1).mean() * 100)
    quality = {}
    if n_clusters >= 2:
        nz = labels != -1
        quality = {
            "dbcv": round(float(dbcv(Xtr, labels)), 3),
            "silhouette": round(float(silhouette_score(Xtr[nz], labels[nz])), 3),
        }
    print(f"       {n_clusters} clusters, {noise_pct:.1f}% noise, quality={quality}")

    # proxy-seed segment centroids (train only) — the deployable labeller
    names, cents = [], []
    for seg in PENALTY:
        m = (proxy_tr == seg).to_numpy()
        if m.sum() >= MIN_SEED:
            names.append(seg)
            cents.append(Xtr[m].mean(axis=0))
    centroids = np.vstack(cents)

    # Unassigned threshold from train nearest-centroid distances
    train_mind = cdist(Xtr, centroids).min(axis=1)
    threshold = float(np.percentile(train_mind, UNASSIGNED_PCTL))

    print("P4 — inductive nearest-centroid scoring (+ Unassigned bucket) ...")
    pred_tr, _ = _assign(Xtr, centroids, names, threshold)
    pred_te, _ = _assign(Xte, centroids, names, threshold)

    # P5 — validation on the labelled subsets (proxy-referenced; circular until SME labels)
    print("P5 — validating (train + HOLD-OUT) ...")
    lab_tr = proxy_tr != "Unassigned"
    lab_te = proxy_te != "Unassigned"
    train_val = _recall_and_cost(proxy_tr[lab_tr], pd.Series(pred_tr)[lab_tr])
    holdout_val = _recall_and_cost(proxy_te[lab_te], pd.Series(pred_te)[lab_te])

    seeded = set(names)
    report = {
        "config": {
            "test_size": TEST_SIZE,
            "min_cluster_size": MIN_CLUSTER_SIZE,
            "penalty_weighting": "cost-only (discovery unweighted)",
            "features": f"{X.shape[1]} compact",
            "unassigned_pctl": UNASSIGNED_PCTL,
        },
        "train_discovery": {"clusters": n_clusters, "noise_pct": round(noise_pct, 1), **quality},
        "seeded_segments": names,
        "unassignable_no_seed": [s for s in PENALTY if s not in seeded],
        "unassigned_rate": {
            "train": round(float((pred_tr == "Unassigned").mean()), 3),
            "test": round(float((pred_te == "Unassigned").mean()), 3),
        },
        "validation_train_proxy": train_val,
        "validation_holdout_proxy": holdout_val,
        "note": "recall is proxy-referenced (circular) until data/labels/sme_sample.csv is provided",
    }

    # SME ground-truth hook — non-circular hold-out recall when labels arrive
    if SME_LABELS.exists():
        sme = pd.read_csv(SME_LABELS)
        test_df = df.iloc[ite].reset_index(drop=True).assign(pred=pred_te)
        merged = test_df.merge(sme, on="Unique Identifier", how="inner")
        if len(merged):
            report["validation_holdout_SME"] = _recall_and_cost(
                merged["true_segment"], merged["pred"]
            )
            print(f"       SME ground-truth: {len(merged)} labelled test rows")
    else:
        print(f"       (awaiting SME labels at {SME_LABELS.relative_to(ROOT)})")

    (OUTPUT / "prototype_v3_report.json").write_text(json.dumps(report, indent=2))
    out_df = df.iloc[ite].reset_index(drop=True).assign(model_segment=pred_te)
    keep = [c for c in out_df.columns if not c.startswith("_")]
    out_df[keep].to_csv(OUTPUT / "prototype_v3_holdout_scored.csv", index=False)
    _fig_pca(Xte, pred_te)

    print("\n=== summary ===")
    print(f"  train discovery: {n_clusters} clusters, {noise_pct:.1f}% noise, {quality}")
    print(
        f"  unassigned rate: train {report['unassigned_rate']['train']:.0%}  "
        f"test {report['unassigned_rate']['test']:.0%}"
    )
    print(
        f"  HOLD-OUT weighted cost: {holdout_val['weighted_cost']} "
        f"({holdout_val['cost_per_record']}/labelled record, n={holdout_val['n']})"
    )
    print("  HOLD-OUT per-segment recall (vs proxy — circular until SME labels):")
    for seg, r in sorted(holdout_val["per_segment_recall"].items(), key=lambda kv: -kv[1]):
        print(f"    {seg:20s} {r:.0%}")
    print(f"  NOT assignable (no seed): {report['unassignable_no_seed']}")
    print(f"\nsaved → {OUTPUT}/")


def _fig_pca(Xte: np.ndarray, segs: np.ndarray) -> None:
    pcs = PCA(n_components=2, random_state=42).fit_transform(Xte)
    fig, ax = plt.subplots(figsize=(9, 7))
    for seg in pd.unique(segs):
        m = segs == seg
        color = "#6B7280" if seg == "Unassigned" else SEG_COLORS.get(seg, "#888888")
        ax.scatter(pcs[m, 0], pcs[m, 1], s=16, alpha=0.7, color=color, label=seg)
    ax.set_title("v3 prototype — held-out set, model segments (PCA of compact features)")
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.legend(fontsize=8, markerscale=1.5, loc="best")
    fig.savefig(OUTPUT / "fig_p01_holdout_pca.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
