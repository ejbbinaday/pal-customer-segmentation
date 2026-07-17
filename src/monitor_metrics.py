"""Model monitoring metrics — PAL customer segmentation.

Implements the Regime-A (quality) and Regime-C (drift/stability) metrics from
`monitoring-metrics.md`:

  • DBCV   — Density-Based Clustering Validation (correct primary quality metric
             for HDBSCAN; self-contained, no `hdbscan` library needed)
  • PSI    — Population Stability Index (segment-mix + feature drift)
  • ARI    — Adjusted Rand Index (cross-refresh + bootstrap stability)
  • drift  — per-segment volume + centroid drift, noise-rate trend

The functions are importable and dataset-agnostic. Run as a script to produce a
monitoring report on `sample-features.csv`:

    python monitor_metrics.py

It reproduces the pipeline's feature engineering + proxy labels, fits HDBSCAN,
computes DBCV, and simulates a reference-vs-current monthly refresh (by booking
month) to demonstrate PSI / ARI / drift. Writes:

    monitor_output/monitoring_report.json
    monitor_output/monitoring_summary.txt
"""

import warnings

warnings.filterwarnings("ignore")

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse.csgraph import minimum_spanning_tree
from scipy.spatial.distance import cdist
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)

ROOT = Path(__file__).resolve().parents[1]

# thresholds mirror monitoring-metrics.md §4
PSI_INVESTIGATE, PSI_RETRAIN = 0.10, 0.25
ARI_ACCEPTABLE, ARI_STABLE = 0.75, 0.90
NOISE_RETRAIN_PCT = 12.0

PENALTY = {
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


# ══════════════════════════════════════════════════════════════════════════════
# DBCV — Density-Based Clustering Validation (Moulavi et al., 2014)
# ══════════════════════════════════════════════════════════════════════════════
def dbcv(X, labels, max_points=6000, seed=42):
    """Density-Based Clustering Validation score in [-1, 1] (higher = better).

    Correct primary quality metric for density-based clusterings (HDBSCAN/DBSCAN),
    unlike Silhouette/Davies-Bouldin which assume convex clusters. Noise (label -1)
    is excluded from clusters but counts toward the N used for cluster weighting.

    Dense pairwise distances are used, so points are subsampled to `max_points`.
    """
    X = np.asarray(X, dtype=float)
    labels = np.asarray(labels)

    # subsample for tractable O(n^2) distances, preserving label proportions loosely
    if len(X) > max_points:
        rng = np.random.default_rng(seed)
        idx = rng.choice(len(X), size=max_points, replace=False)
        X, labels = X[idx], labels[idx]

    n_total = len(labels)
    dim = X.shape[1]
    clusters = [c for c in np.unique(labels) if c != -1]
    if len(clusters) < 2:
        return float("nan")

    # all-points core distance within each cluster (density estimate at each point)
    core = np.full(n_total, np.inf)
    cluster_idx = {}
    for c in clusters:
        members = np.where(labels == c)[0]
        cluster_idx[c] = members
        if len(members) < 2:
            core[members] = np.inf
            continue
        d = cdist(X[members], X[members])
        np.fill_diagonal(d, np.inf)
        with np.errstate(divide="ignore"):
            inv = (1.0 / d) ** dim  # (1/dist)^dim
        inv[~np.isfinite(inv)] = 0.0  # coincident points contribute 0
        denom = len(members) - 1
        s = inv.sum(axis=1) / denom
        with np.errstate(divide="ignore"):
            core[members] = s ** (-1.0 / dim)

    def mreach(i_idx, j_idx):
        """Mutual reachability matrix between two index sets."""
        d = cdist(X[i_idx], X[j_idx])
        return np.maximum(np.maximum(d, core[i_idx][:, None]), core[j_idx][None, :])

    # Density Sparseness of a Cluster: max edge of its internal mutual-reachability MST
    dsc = {}
    for c in clusters:
        m = cluster_idx[c]
        if len(m) < 2:
            dsc[c] = 0.0
            continue
        mr = mreach(m, m)
        mst = minimum_spanning_tree(mr).toarray()
        dsc[c] = mst[mst > 0].max() if (mst > 0).any() else 0.0

    # Density Separation between clusters: min mutual-reachability across the pair
    validity, weights = [], []
    for c in clusters:
        m = cluster_idx[c]
        min_dspc = np.inf
        for o in clusters:
            if o == c:
                continue
            min_dspc = min(min_dspc, mreach(m, cluster_idx[o]).min())
        denom = max(min_dspc, dsc[c])
        v = 0.0 if denom == 0 else (min_dspc - dsc[c]) / denom
        validity.append(v)
        weights.append(len(m))

    # weighted by cluster size over TOTAL points (noise dilutes the score)
    return float(np.sum(np.array(validity) * np.array(weights)) / n_total)


# ══════════════════════════════════════════════════════════════════════════════
# PSI — Population Stability Index
# ══════════════════════════════════════════════════════════════════════════════
def psi_numeric(reference, current, bins=10, eps=1e-6):
    """PSI for a numeric variable using reference quantile bin edges."""
    reference = np.asarray(reference, dtype=float)
    current = np.asarray(current, dtype=float)
    edges = np.unique(np.quantile(reference, np.linspace(0, 1, bins + 1)))
    edges[0], edges[-1] = -np.inf, np.inf
    ref_pct = np.histogram(reference, bins=edges)[0] / len(reference)
    cur_pct = np.histogram(current, bins=edges)[0] / len(current)
    ref_pct = np.clip(ref_pct, eps, None)
    cur_pct = np.clip(cur_pct, eps, None)
    return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))


def psi_categorical(reference, current, eps=1e-6):
    """PSI for a categorical variable (e.g. segment mix) over shared categories."""
    ref = pd.Series(reference).value_counts(normalize=True)
    cur = pd.Series(current).value_counts(normalize=True)
    cats = ref.index.union(cur.index)
    r = np.clip(ref.reindex(cats).fillna(0).values, eps, None)
    c = np.clip(cur.reindex(cats).fillna(0).values, eps, None)
    return float(np.sum((c - r) * np.log(c / r)))


def psi_verdict(value):
    if value > PSI_RETRAIN:
        return "RETRAIN"
    if value > PSI_INVESTIGATE:
        return "INVESTIGATE"
    return "STABLE"


# ══════════════════════════════════════════════════════════════════════════════
# ARI — stability
# ══════════════════════════════════════════════════════════════════════════════
def ari_verdict(value):
    if value >= ARI_STABLE:
        return "VERY STABLE"
    if value >= ARI_ACCEPTABLE:
        return "ACCEPTABLE"
    return "UNSTABLE"


def bootstrap_stability(fit_fn, X, n_runs=5, sample_frac=0.9, seed=42):
    """Mean pairwise ARI across re-fits on resamples (measured on shared points).

    `fit_fn(X_subset) -> labels` fits the clustering and returns integer labels.
    """
    rng = np.random.default_rng(seed)
    n = len(X)
    runs = []
    for _ in range(n_runs):
        idx = rng.choice(n, size=int(sample_frac * n), replace=False)
        runs.append((set(idx.tolist()), dict(zip(idx.tolist(), fit_fn(X[idx])))))
    aris = []
    for i in range(len(runs)):
        for j in range(i + 1, len(runs)):
            shared = sorted(runs[i][0] & runs[j][0])
            if len(shared) < 10:
                continue
            a = [runs[i][1][k] for k in shared]
            b = [runs[j][1][k] for k in shared]
            aris.append(adjusted_rand_score(a, b))
    return float(np.mean(aris)) if aris else float("nan")


# ══════════════════════════════════════════════════════════════════════════════
# Drift — segment volume + centroid
# ══════════════════════════════════════════════════════════════════════════════
def volume_drift(ref_labels, cur_labels):
    """Per-segment share (%) reference vs current and relative change."""
    ref = pd.Series(ref_labels).value_counts(normalize=True) * 100
    cur = pd.Series(cur_labels).value_counts(normalize=True) * 100
    segs = ref.index.union(cur.index)
    out = {}
    for s in segs:
        r, c = ref.get(s, 0.0), cur.get(s, 0.0)
        rel = ((c - r) / r * 100) if r > 0 else float("inf")
        out[s] = {
            "ref_pct": round(r, 2),
            "cur_pct": round(c, 2),
            "rel_change_pct": round(rel, 1) if np.isfinite(rel) else None,
            "flag": bool(abs(rel) > 30) if np.isfinite(rel) else True,
        }
    return out


def centroid_drift(X_ref, ref_labels, X_cur, cur_labels):
    """Euclidean shift of each segment centroid (in scaled space), flagged > 1.0."""
    ref_labels, cur_labels = np.asarray(ref_labels), np.asarray(cur_labels)
    out = {}
    for s in np.unique(ref_labels):
        if s == -1 or s not in set(cur_labels):
            continue
        rc = X_ref[ref_labels == s].mean(axis=0)
        cc = X_cur[cur_labels == s].mean(axis=0)
        shift = float(np.linalg.norm(rc - cc))
        out[str(s)] = {"centroid_shift": round(shift, 3), "flag": bool(shift > 1.0)}
    return out


# ══════════════════════════════════════════════════════════════════════════════
# Pipeline-consistent feature engineering + proxy labels (mirrors hdbscan_final.py)
# ══════════════════════════════════════════════════════════════════════════════
def load_features(path=ROOT / "data" / "raw" / "sample-features.csv"):
    df = pd.read_csv(path)
    df["Average Fare"] = df["Average Fare"].str.replace("$", "", regex=False).astype(float)
    df["PNRCreationDate"] = pd.to_datetime(df["PNRCreationDate"], dayfirst=True, errors="coerce")
    df["Flight Date"] = pd.to_datetime(df["Flight Date"], dayfirst=True, errors="coerce")
    df["lead_time"] = (df["Flight Date"] - df["PNRCreationDate"]).dt.days
    df["fare_per_pax"] = df["Average Fare"] / df["PAX Count"]
    df["booking_month"] = df["PNRCreationDate"].dt.month
    df = df.dropna(subset=["lead_time"]).copy()
    df["cabin_ord"] = df["Cabin"].map({"Y": 0, "W": 1, "J": 2}).fillna(0)
    df["is_dom"] = (df["Entity"] == "DOM").astype(int)
    return df


def build_matrix(df):
    from sklearn.preprocessing import StandardScaler

    cat_cols = ["Region", "Farebrand", "Itinerary Type", "Ticketing Channel"]
    df_enc = pd.get_dummies(
        df[cat_cols].fillna("Unknown"), columns=cat_cols, prefix_sep="=", dtype=int
    )
    num_cols = [
        "lead_time",
        "Average Fare",
        "fare_per_pax",
        "PAX Count",
        "cabin_ord",
        "is_dom",
        "booking_month",
    ]
    X_raw = pd.concat([df[num_cols].reset_index(drop=True), df_enc.reset_index(drop=True)], axis=1)
    return StandardScaler().fit_transform(X_raw), X_raw.columns.tolist()


def proxy_labels(df):
    """Priority-ordered proxy rules (mirrors hdbscan_final.py Stage 3)."""
    seg = pd.Series(["Budget/Adventure"] * len(df), index=df.index)
    seg[df["Farebrand"].isin(["Economy Supersaver", "Economy Saver"])] = "Budget/Adventure"
    nomad = (df["lead_time"] > 30) & (df["Cabin"] == "Y") & (df["PAX Count"] == 1)
    seg[nomad] = "Digital Nomad"
    seg[df["lead_time"] <= 3] = "Last-Minute"
    seg[df["PAX Count"].between(3, 5)] = "Family"
    seg[
        (df["Region"] == "Middle East") & (df["Ticketing Channel"] == "Traditional Travel Agency")
    ] = "Pilgrimage"
    seg[df["Itinerary Type"] == "Beyonds (INT - DOM)"] = "Balikbayan/VFR"
    seg[(df["Region"] == "Middle East") & (df["Ticketing Channel"] == "Sea Crew")] = "OFW/Migrant"
    seg[df["Cabin"] == "W"] = "Premium Bleisure"
    seg[df["Cabin"] == "J"] = "Corporate"
    return seg.values


# ══════════════════════════════════════════════════════════════════════════════
# Report
# ══════════════════════════════════════════════════════════════════════════════
def main():
    from sklearn.cluster import HDBSCAN

    OUT = ROOT / "outputs" / "monitor_output"
    OUT.mkdir(parents=True, exist_ok=True)

    print("Loading + engineering features ...")
    df = load_features()
    X, feat_names = build_matrix(df)
    print(f"  matrix: {X.shape}")

    def fit_hdbscan(Xin):
        return HDBSCAN(min_cluster_size=150, min_samples=10, n_jobs=-1).fit_predict(Xin)

    print("Fitting HDBSCAN (full) ...")
    labels = fit_hdbscan(X)
    noise_pct = float((labels == -1).mean() * 100)
    n_clusters = int(len({c for c in labels if c != -1}))
    print(f"  clusters={n_clusters}  noise={noise_pct:.1f}%")

    # ── Regime A: quality (incl. DBCV) ────────────────────────────────────────
    print("Computing quality metrics (Silhouette / DB / CH / DBCV) ...")
    mask = labels != -1
    rng = np.random.default_rng(42)
    sil_idx = rng.choice(np.where(mask)[0], size=min(8000, mask.sum()), replace=False)
    quality = {
        "silhouette": round(float(silhouette_score(X[sil_idx], labels[sil_idx])), 4),
        "davies_bouldin": round(float(davies_bouldin_score(X[mask], labels[mask])), 4),
        "calinski_harabasz": round(float(calinski_harabasz_score(X[mask], labels[mask])), 1),
        "dbcv": round(dbcv(X, labels), 4),
        "noise_pct": round(noise_pct, 2),
        "n_clusters": n_clusters,
        "noise_flag": bool(noise_pct > NOISE_RETRAIN_PCT),
    }
    print(f"  DBCV={quality['dbcv']}  (Silhouette={quality['silhouette']})")

    # ── Regime C: drift, simulated reference(early month) vs current(later) ───
    print("Simulating monthly refresh (booking-month split) for PSI/ARI/drift ...")
    seg = proxy_labels(df)
    months = np.sort(df["booking_month"].dropna().unique())
    if len(months) >= 2:
        cut = months[len(months) // 2]
        ref_mask = (df["booking_month"] < cut).values
    else:  # single-month sample → random 50/50 split as a stand-in
        ref_mask = rng.random(len(df)) < 0.5
    cur_mask = ~ref_mask

    psi_segment = psi_categorical(seg[ref_mask], seg[cur_mask])
    feature_psi = {
        f: round(psi_numeric(df[f].values[ref_mask], df[f].values[cur_mask]), 4)
        for f in ["lead_time", "fare_per_pax", "cabin_ord"]
    }
    n_feat_flag = sum(v > PSI_INVESTIGATE for v in feature_psi.values())

    print("Computing bootstrap stability (ARI over re-fits) ...")
    ari = bootstrap_stability(fit_hdbscan, X, n_runs=4, sample_frac=0.9)

    drift = {
        "psi_segment_mix": round(psi_segment, 4),
        "psi_segment_verdict": psi_verdict(psi_segment),
        "psi_features": feature_psi,
        "n_features_over_0.10": int(n_feat_flag),
        "ari_bootstrap_stability": round(ari, 4),
        "ari_verdict": ari_verdict(ari),
        "volume_drift": volume_drift(seg[ref_mask], seg[cur_mask]),
        "centroid_drift": centroid_drift(X[ref_mask], seg[ref_mask], X[cur_mask], seg[cur_mask]),
    }

    # ── retrain decision (monitoring-metrics.md §5) ───────────────────────────
    triggers = []
    if psi_segment > PSI_RETRAIN:
        triggers.append(f"segment-mix PSI {psi_segment:.3f} > {PSI_RETRAIN}")
    if n_feat_flag >= 2:
        triggers.append(f"{n_feat_flag} features with PSI > {PSI_INVESTIGATE}")
    if np.isfinite(ari) and ari < ARI_ACCEPTABLE:
        triggers.append(f"ARI {ari:.3f} < {ARI_ACCEPTABLE}")
    if noise_pct > NOISE_RETRAIN_PCT:
        triggers.append(f"noise {noise_pct:.1f}% > {NOISE_RETRAIN_PCT}%")

    report = {
        "dataset": "sample-features.csv",
        "n_records": int(len(df)),
        "regime_A_quality": quality,
        "regime_C_monitoring": drift,
        "retrain_triggered": bool(triggers),
        "retrain_reasons": triggers,
    }

    (OUT / "monitoring_report.json").write_text(json.dumps(report, indent=2))

    lines = [
        "PAL SEGMENTATION — MONITORING REPORT",
        "=" * 52,
        f"Records: {len(df):,}   Clusters: {n_clusters}   Noise: {noise_pct:.1f}%",
        "",
        "QUALITY (Regime A)",
        f"  DBCV               {quality['dbcv']:>8}   (primary for HDBSCAN)",
        f"  Silhouette         {quality['silhouette']:>8}   (convex-biased, secondary)",
        f"  Davies-Bouldin     {quality['davies_bouldin']:>8}",
        f"  Calinski-Harabasz  {quality['calinski_harabasz']:>8}",
        "",
        "DRIFT / STABILITY (Regime C)",
        f"  Segment-mix PSI    {psi_segment:>8.4f}   [{psi_verdict(psi_segment)}]",
        "  Feature PSI        " + ", ".join(f"{k}={v}" for k, v in feature_psi.items()),
        f"  Bootstrap ARI      {ari:>8.4f}   [{ari_verdict(ari)}]",
        "",
        "RETRAIN DECISION",
        ("  TRIGGERED: " + "; ".join(triggers)) if triggers else "  No retrain triggers fired.",
    ]
    summary = "\n".join(lines)
    (OUT / "monitoring_summary.txt").write_text(summary + "\n")
    print("\n" + summary)
    print("\nsaved → monitor_output/monitoring_report.json")
    print("saved → monitor_output/monitoring_summary.txt")


if __name__ == "__main__":
    main()
