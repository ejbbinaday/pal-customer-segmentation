"""Head-to-head: would k-prototypes / k-modes improve the model over the current LCA layer?

`src/cluster_diagnostic.py` ran k-prototypes **once** at k* as a cross-check (ARI 0.20). That is not
enough to answer "would it improve the model?", so this script tests the three claims that decide it:

  1. **Natural k** — does a mixed-type *distance* method find an elbow where LCA's BIC found none?
     (k-prototypes / k-modes cost + relative gain per k.)
  2. **Taxonomy agreement** — ARI vs the rule-based proxy segments across the whole k sweep, for
     k-prototypes, k-modes and LCA on the *same* rows, plus method-vs-method ARI (if two mixed-type
     methods disagree with each other, neither is recovering real structure).
  3. **Stability & separation** — split-half stability (fit on A → predict B, vs fit on B) and a
     **Gower** silhouette (a distance that respects mixed types, unlike Euclidean on one-hots).

Then the only place clustering actually has a job in the current methodology (`docs/methodology.md`:
rules primary, LCA refines): a **sub-segmentation head-to-head inside the big parent segments** —
k-prototypes vs LCA on stability + separation. That is the test that could change the pipeline.

Read-only on features; writes `outputs/kproto_compare/summary.md`.
Run:  python src/kproto_compare.py            (~10-20 min)
      python src/kproto_compare.py --quick    (smaller sample / shorter sweep)
"""

import argparse
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from kmodes.kmodes import KModes
from kmodes.kprototypes import KPrototypes
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler
from stepmix.stepmix import StepMix

ROOT = Path(__file__).resolve().parents[1]
BOOKING = ROOT / "data" / "interim" / "pal_features_booking.parquet"
OUT = ROOT / "outputs" / "kproto_compare"

SEED = 42
SAMPLE = 20_000  # rows for the k sweep (kmodes is pure-Python; 20k is the practical ceiling)
SIL_N = 4_000  # rows for the Gower silhouette (O(n^2) memory)
K_RANGE = range(3, 13)
STABILITY_K = (5, 9, 10)  # k=5 best-ARI, k=9 LCA BIC pick, k=10 the business taxonomy size
SUB_PARENTS = ["Budget/Adventure", "OFW/Migrant", "Balikbayan/VFR"]
SUB_SAMPLE = 12_000
SUB_K = 4  # the business-actionable cap used by src/sub_segment.py

# Same feature set as src/cluster_diagnostic.py, so results are comparable to the 2026-07-23 decision.
NUMERIC = ["lead_days", "value_tier", "log_rev", "n_coupons"]
BINARY = ["round_trip", "foreign_issue", "is_group", "connecting", "peak_month", "corp_channel"]
NOMINAL = ["dest_region"]


# ── data ─────────────────────────────────────────────────────────────────────────
def load_sample(n: int, where: str = "") -> pd.DataFrame:
    con = duckdb.connect()
    con.execute("PRAGMA threads=6")
    df = con.execute(f"""
        SELECT lead_days, max_tier AS value_tier, rev_pos, n_coupons,
               coalesce(dest_region, 'Domestic') AS dest_region,
               round_trip::INT round_trip, foreign_issue::INT foreign_issue,
               is_group::INT is_group, connecting::INT connecting,
               peak_month::INT peak_month, corp_channel::INT corp_channel,
               proxy_segment
        FROM (SELECT * FROM read_parquet('{BOOKING}') {where})
        USING SAMPLE {n} ROWS (reservoir, {SEED})
    """).fetchdf()
    df["lead_days"] = df["lead_days"].clip(0, 365)
    df["value_tier"] = df["value_tier"].fillna(df["value_tier"].median())
    df["log_rev"] = np.log1p(df["rev_pos"].clip(lower=0))
    df["n_coupons"] = df["n_coupons"].clip(1, 8)
    return df.reset_index(drop=True)


def to_codes(df: pd.DataFrame, binary: list[str] | None = None) -> pd.DataFrame:
    """All features → integer codes (binned numerics) — the input LCA and k-modes share."""
    binary = BINARY if binary is None else binary
    out = pd.DataFrame(index=df.index)
    out["lead_bucket"] = pd.cut(df["lead_days"], [-1, 3, 14, 45, 120, 999], labels=False)
    out["value_tier"] = df["value_tier"].round().astype(int) - 1
    out["rev_bucket"] = pd.qcut(df["log_rev"].rank(method="first"), 5, labels=False)
    out["n_coupons_b"] = np.clip(df["n_coupons"] - 1, 0, 3)
    out["dest_region"] = df["dest_region"].astype("category").cat.codes
    for b in binary:
        out[b] = df[b].astype(int)
    keep = [c for c in out.columns if out[c].nunique() > 1]  # drop constants (within-parent runs)
    return out[keep].astype(int)


def mixed_matrix(
    df: pd.DataFrame, scaler: StandardScaler | None = None, cats: list[str] | None = None
) -> tuple[np.ndarray, list[int], StandardScaler]:
    """k-prototypes input: standardised numerics + raw categoricals as an object array."""
    cats = (BINARY + NOMINAL) if cats is None else cats
    if scaler is None:
        scaler = StandardScaler().fit(df[NUMERIC])
    num = scaler.transform(df[NUMERIC])
    cat = df[cats].astype(str).to_numpy()
    X = np.concatenate([num, cat], axis=1).astype(object)
    return X, list(range(len(NUMERIC), len(NUMERIC) + len(cats))), scaler


# ── Gower distance (mixed-type-correct separation metric) ────────────────────────
def gower(df: pd.DataFrame, cats: list[str] | None = None) -> np.ndarray:
    """Gower dissimilarity: range-normalised |diff| on numerics, 0/1 mismatch on categoricals."""
    cats = (BINARY + NOMINAL) if cats is None else cats
    n = len(df)
    acc = np.zeros((n, n), dtype=np.float32)
    for c in NUMERIC:
        v = df[c].to_numpy(dtype=np.float32)
        rng = float(v.max() - v.min()) or 1.0
        acc += np.abs(v[:, None] - v[None, :]) / rng
    for c in cats:
        v = df[c].astype(str).to_numpy()
        acc += (v[:, None] != v[None, :]).astype(np.float32)
    return acc / (len(NUMERIC) + len(cats))


def gower_sil(dist: np.ndarray, labels: np.ndarray) -> float:
    """Silhouette on a precomputed Gower matrix; nan if the solution collapsed to one cluster."""
    if len(np.unique(labels)) < 2:
        return float("nan")
    return round(float(silhouette_score(dist, labels, metric="precomputed")), 3)


# ── fitters (uniform interface: fit on `a`, return labels for a and for b) ───────
def fit_kproto(a: pd.DataFrame, k: int, b: pd.DataFrame | None = None, cats=None):
    Xa, idx, scaler = mixed_matrix(a, cats=cats)
    m = KPrototypes(n_clusters=k, init="Huang", n_init=2, random_state=SEED, n_jobs=1)
    la = m.fit_predict(Xa, categorical=idx)
    lb = None
    if b is not None:
        Xb, _, _ = mixed_matrix(b, scaler=scaler, cats=cats)
        lb = m.predict(Xb, categorical=idx)
    return la, lb, float(m.cost_)


def fit_kmodes(a: pd.DataFrame, k: int, b: pd.DataFrame | None = None, binary=None):
    ca = to_codes(a, binary=binary)
    m = KModes(n_clusters=k, init="Huang", n_init=2, random_state=SEED, n_jobs=1)
    la = m.fit_predict(ca)
    lb = None
    if b is not None:
        cb = to_codes(b, binary=binary)[ca.columns]
        lb = m.predict(cb)
    return la, lb, float(m.cost_)


def fit_lca(a: pd.DataFrame, k: int, b: pd.DataFrame | None = None, binary=None):
    ca = to_codes(a, binary=binary)
    m = StepMix(
        n_components=k,
        measurement="categorical",
        n_init=2,
        random_state=SEED,
        verbose=0,
        progress_bar=False,
    )
    m.fit(ca)
    la = m.predict(ca)
    lb = None
    if b is not None:
        cb = to_codes(b, binary=binary)[ca.columns]
        lb = m.predict(cb)
    return la, lb, float(m.bic(ca))


FITTERS = {"k-prototypes": fit_kproto, "k-modes": fit_kmodes, "LCA": fit_lca}


# ── test 1+2+3: the k sweep ─────────────────────────────────────────────────────
def sweep(df: pd.DataFrame, ks) -> tuple[pd.DataFrame, dict]:
    sil_idx = df.sample(min(SIL_N, len(df)), random_state=SEED).index
    dist = gower(df.loc[sil_idx])
    proxy = df["proxy_segment"].to_numpy()
    rows, labels = [], {}

    for name, fit in FITTERS.items():
        for k in ks:
            t0 = time.time()
            lab, _, cost = fit(df, k)
            labels[(name, k)] = lab
            rows.append(
                {
                    "method": name,
                    "k": k,
                    "cost_or_BIC": round(cost, 1),
                    "ARI_vs_proxy": round(adjusted_rand_score(proxy, lab), 3),
                    "gower_sil": gower_sil(dist, lab[df.index.get_indexer(sil_idx)]),
                    "n_clusters_used": int(len(np.unique(lab))),
                    "secs": round(time.time() - t0, 1),
                }
            )
            print(
                f"  {name:14s} k={k:2d}  {rows[-1]['secs']:6.1f}s  "
                f"ARI={rows[-1]['ARI_vs_proxy']:.3f}  sil={rows[-1]['gower_sil']}"
            )
    return pd.DataFrame(rows), labels


def cross_method(labels: dict, ks) -> pd.DataFrame:
    """Do the methods agree with each other? Low pairwise ARI ⇒ no reproducible structure."""
    pairs = [("k-prototypes", "LCA"), ("k-prototypes", "k-modes"), ("k-modes", "LCA")]
    rows = []
    for k in ks:
        r = {"k": k}
        for x, y in pairs:
            r[f"{x} vs {y}"] = round(adjusted_rand_score(labels[(x, k)], labels[(y, k)]), 3)
        rows.append(r)
    return pd.DataFrame(rows)


def stability(df: pd.DataFrame, ks, cats=None, binary=None) -> pd.DataFrame:
    """Split-half: fit on A → predict B, vs fit directly on B. High ARI = reproducible clusters."""
    a = df.sample(frac=0.5, random_state=SEED)
    b = df.drop(a.index).reset_index(drop=True)
    a = a.reset_index(drop=True)
    rows = []
    for name, fit in FITTERS.items():
        kw = {"cats": cats} if name == "k-prototypes" else {"binary": binary}
        for k in ks:
            _, b_from_a, _ = fit(a, k, b, **kw)
            b_direct, _, _ = fit(b, k, **kw)
            rows.append(
                {
                    "method": name,
                    "k": k,
                    "split_half_ARI": round(adjusted_rand_score(b_from_a, b_direct), 3),
                }
            )
            print(f"  stability {name:14s} k={k:2d}  ARI={rows[-1]['split_half_ARI']:.3f}")
    return pd.DataFrame(rows)


# ── test 4: sub-segmentation head-to-head (the decision-relevant test) ──────────
SUB_BINARY = ["round_trip", "connecting", "peak_month", "foreign_issue"]


def sub_head_to_head(parents: list[str], k: int) -> pd.DataFrame:
    rows = []
    for seg in parents:
        df = load_sample(SUB_SAMPLE, where=f"WHERE proxy_segment = '{seg.replace(chr(39), '')}'")
        if len(df) < 500:
            print(f"  {seg}: only {len(df)} rows — skipped")
            continue
        sil_idx = df.sample(min(SIL_N, len(df)), random_state=SEED).index
        dist = gower(df.loc[sil_idx], cats=SUB_BINARY + NOMINAL)
        a = df.sample(frac=0.5, random_state=SEED)
        b = df.drop(a.index).reset_index(drop=True)
        a = a.reset_index(drop=True)

        for name, fit in FITTERS.items():
            kw = (
                {"cats": SUB_BINARY + NOMINAL} if name == "k-prototypes" else {"binary": SUB_BINARY}
            )
            lab, _, _ = fit(df, k, **kw)
            _, b_from_a, _ = fit(a, k, b, **kw)
            b_direct, _, _ = fit(b, k, **kw)
            sizes = pd.Series(lab).value_counts(normalize=True)
            rows.append(
                {
                    "parent": seg,
                    "method": name,
                    "gower_sil": gower_sil(dist, lab[df.index.get_indexer(sil_idx)]),
                    "split_half_ARI": round(adjusted_rand_score(b_from_a, b_direct), 3),
                    "smallest_sub_pct": round(100 * sizes.min(), 1),
                    "largest_sub_pct": round(100 * sizes.max(), 1),
                }
            )
            print(
                f"  {seg:18s} {name:14s} sil={rows[-1]['gower_sil']} "
                f"stab={rows[-1]['split_half_ARI']:.3f}"
            )
    return pd.DataFrame(rows)


# ── report ──────────────────────────────────────────────────────────────────────
def elbow_table(sweep_df: pd.DataFrame) -> pd.DataFrame:
    """Relative cost gain per extra cluster — an elbow shows up as a sharp drop in this column."""
    out = []
    for name, g in sweep_df.groupby("method", sort=False):
        g = g.sort_values("k")
        gain = -g["cost_or_BIC"].diff() / g["cost_or_BIC"].abs().shift()
        for k, v in zip(g["k"], gain, strict=True):
            out.append(
                {
                    "method": name,
                    "k": k,
                    "rel_gain_vs_prev_k": None if pd.isna(v) else round(float(v), 4),
                }
            )
    return pd.DataFrame(out).pivot(index="k", columns="method", values="rel_gain_vs_prev_k")


def write_report(sweep_df, cross_df, stab_df, sub_df, n_rows, ks) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    best = sweep_df.loc[sweep_df.groupby("method")["ARI_vs_proxy"].idxmax()]
    lines = [
        "# Would k-prototypes / k-modes improve the model?\n",
        f"Sample: **{n_rows:,}** bookings from `pal_features_booking.parquet` "
        f"({len(NUMERIC)} numeric + {len(BINARY)} binary + {len(NOMINAL)} nominal), seed {SEED}. "
        f"k sweep {min(ks)}–{max(ks)}. Same feature set as `src/cluster_diagnostic.py`, so this "
        "extends the 2026-07-23 decision rather than re-deriving it.\n",
        "Metrics: **cost** (k-prototypes/k-modes, lower=better) vs **BIC** (LCA, lower=better); "
        "**ARI vs proxy** = agreement with the rule-based segments; **Gower silhouette** = separation "
        "under a mixed-type distance (≈0 means no separation); **split-half ARI** = reproducibility.\n",
        "## 1. Full sweep\n",
        sweep_df.to_markdown(index=False),
        "\n## 2. Elbow test — relative cost/BIC gain per extra cluster\n",
        "A natural *k* shows up as a sharp fall in these values (gains collapse after the true k).\n",
        elbow_table(sweep_df).to_markdown(),
        "\n## 3. Do the methods agree with each other? (pairwise ARI)\n",
        cross_df.to_markdown(index=False),
        "\n## 4. Split-half stability (fit on half A → predict B, vs fit on B)\n",
        stab_df.pivot(index="k", columns="method", values="split_half_ARI").to_markdown(),
        "\n## 5. Sub-segmentation head-to-head inside the big rule segments "
        f"(k={SUB_K}, the `sub_segment.py` cap)\n",
        sub_df.to_markdown(index=False) if len(sub_df) else "_skipped_",
        "\n## Best ARI per method\n",
        best[["method", "k", "ARI_vs_proxy", "gower_sil"]].to_markdown(index=False),
        "",
    ]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n")
    sweep_df.to_csv(OUT / "sweep.csv", index=False)
    print("\nWrote", OUT / "summary.md")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="smaller sample and k sweep")
    args = ap.parse_args()
    n = 5_000 if args.quick else SAMPLE
    ks = range(3, 7) if args.quick else K_RANGE
    stab_ks = (5,) if args.quick else STABILITY_K
    parents = SUB_PARENTS[:1] if args.quick else SUB_PARENTS

    print(f"Loading {n:,} bookings ...")
    df = load_sample(n)
    print("Sweeping k ...")
    sweep_df, labels = sweep(df, ks)
    cross_df = cross_method(labels, ks)
    print("Split-half stability ...")
    stab_df = stability(df, stab_ks)
    print("Sub-segmentation head-to-head ...")
    sub_df = sub_head_to_head(parents, SUB_K)
    write_report(sweep_df, cross_df, stab_df, sub_df, len(df), ks)


if __name__ == "__main__":
    main()
