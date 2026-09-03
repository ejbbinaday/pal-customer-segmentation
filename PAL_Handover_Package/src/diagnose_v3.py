"""v3 clustering diagnostic — is there real structure to cluster?

Answers the question the shipped prototype metrics raised: are the weak scores a
tuning artifact, or does the v3 data simply lack latent cluster structure? Uses
DEFENSIBLE, non-circular metrics only (no recall-vs-proxy):

  • feature hygiene — drop the collinear / complement / duplicate features
  • DBCV                — density-based cluster validity (correct for HDBSCAN)
  • bootstrap ARI       — cluster stability across resamples (reused from monitor_metrics)
  • KMeans silhouette sweep — a real k shows a PEAK; a monotonic drift means no k
  • PCA reduction       — retry HDBSCAN on a compact PCA space

Run:
    python src/diagnose_v3.py    → outputs/diagnose_v3_output/diagnosis.json
"""

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.cluster import HDBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from features_v3 import build  # noqa: E402
from monitor_metrics import bootstrap_stability, dbcv  # noqa: E402

OUTPUT = ROOT / "outputs" / "diagnose_v3_output"

# Compact, non-redundant behavioral subspace (drops the perfectly-collinear /
# complement / duplicate features flagged in the |corr|>0.9 scan).
COMPACT = [
    "lead_time",
    "net_fare",
    "ancillary",
    "ancillary_ratio",
    "fare_tier",
    "cabin_ord",
    "age",
    "dep_hour",
    "n_legs",
    "red_eye",
    "is_weekend",
    "is_peak_season",
    "changed_itinerary",
    "is_nonstop",
    "is_codeshare",
    "is_domestic",
    "is_long_haul",
    "pos_mismatch",
    "is_group",
    "gender_male",
    "is_gds",
    "is_ota",
    "is_child",
    "is_senior",
]


def _hdbscan_scores(Xs: np.ndarray, mcs: int) -> dict:
    lab = HDBSCAN(min_cluster_size=mcs, min_samples=5).fit_predict(Xs)
    k = len({c for c in lab if c != -1})
    noise = float((lab == -1).mean() * 100)
    d = float(dbcv(Xs, lab)) if k >= 2 else float("nan")
    stab = bootstrap_stability(
        lambda x: HDBSCAN(min_cluster_size=mcs, min_samples=5).fit_predict(x), Xs
    )
    return {
        "min_cluster_size": mcs,
        "clusters": k,
        "noise_pct": round(noise, 1),
        "dbcv": round(d, 3),
        "bootstrap_ari": round(float(stab), 3),
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    df = build()

    Xfull = df[COMPACT].apply(lambda s: s.astype(float)).fillna(0.0).to_numpy()
    Xs = StandardScaler().fit_transform(Xfull)
    print(f"compact feature set: {Xs.shape[0]} rows × {Xs.shape[1]} features (was 58)")

    # 1) HDBSCAN on the cleaned space, unweighted
    hdb = [_hdbscan_scores(Xs, mcs) for mcs in (15, 30, 50)]

    # 2) KMeans silhouette sweep — look for a PEAK (real k) vs monotonic drift (no k)
    km = {
        k: round(
            float(
                silhouette_score(
                    Xs, KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(Xs)
                )
            ),
            3,
        )
        for k in (4, 5, 6, 8, 10, 12)
    }

    # 3) PCA-reduced retry (90% variance) — does compressing help density?
    pca = PCA(n_components=0.90, random_state=42).fit(Xs)
    Xp = pca.transform(Xs)
    hdb_pca = _hdbscan_scores(Xp, 30)
    hdb_pca["pca_components_for_90pct_var"] = int(Xp.shape[1])

    best_dbcv = max(h["dbcv"] for h in hdb if not np.isnan(h["dbcv"]))
    km_peaks = max(km, key=km.get)
    report = {
        "n_rows": int(Xs.shape[0]),
        "n_features_compact": int(Xs.shape[1]),
        "hdbscan_unweighted": hdb,
        "hdbscan_on_pca90": hdb_pca,
        "kmeans_silhouette_by_k": km,
        "interpretation": {
            "best_dbcv": best_dbcv,
            "dbcv_verdict": "structure" if best_dbcv > 0.3 else "little/none (~0)",
            "kmeans_argmax_k": km_peaks,
            "kmeans_monotonic_in_k": km[12] >= km[10] >= km[8],
        },
    }
    (OUTPUT / "diagnosis.json").write_text(json.dumps(report, indent=2))

    print("\n=== HDBSCAN (unweighted, cleaned features) ===")
    for h in hdb:
        print(
            f"  mcs={h['min_cluster_size']:3d}  clusters={h['clusters']:2d}  "
            f"noise={h['noise_pct']:4.1f}%  DBCV={h['dbcv']:.3f}  ARI={h['bootstrap_ari']:.3f}"
        )
    print(
        f"  on PCA-90 ({hdb_pca['pca_components_for_90pct_var']} comps): "
        f"clusters={hdb_pca['clusters']} noise={hdb_pca['noise_pct']}% DBCV={hdb_pca['dbcv']:.3f}"
    )
    print("\n=== KMeans silhouette sweep (peak = real k; drift = no k) ===")
    print("  " + "  ".join(f"k{k}={v:.3f}" for k, v in km.items()))
    print(
        f"\nverdict: best DBCV={best_dbcv:.3f} → {report['interpretation']['dbcv_verdict']}; "
        f"KMeans argmax at k={km_peaks}, monotonic={report['interpretation']['kmeans_monotonic_in_k']}"
    )
    print(f"\nsaved → {OUTPUT / 'diagnosis.json'}")


if __name__ == "__main__":
    main()
