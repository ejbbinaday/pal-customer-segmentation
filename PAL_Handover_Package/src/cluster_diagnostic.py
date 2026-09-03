"""Mixed-type clustering diagnostic — is the segmentation data-driven-able, and with which method?

Per the 2026-07-23 decision to use a **data-driven method that handles mixed types**, this compares
two principled options on a stratified booking sample (density-based HDBSCAN was rejected — the data
is categorical-heavy, not dense blobs):

  • Latent Class Analysis (finite mixture, `stepmix`) — model-based; **BIC** picks #classes.
  • k-prototypes (`kmodes`) — hard clusters via mixed numeric+categorical distance (cross-check).

It reports, for a sweep of k: LCA BIC + entropy, and how well each solution agrees with the rule-based
proxy segments (Adjusted Rand Index) — telling us whether real structure exists and lines up with the
business taxonomy, or whether the data is a continuum (→ keep rules primary, clustering as refinement).

Read-only on features; writes `outputs/cluster_diagnostic/summary.md`.
Run:  python src/cluster_diagnostic.py
"""

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from kmodes.kprototypes import KPrototypes
from sklearn.metrics import adjusted_rand_score
from sklearn.preprocessing import StandardScaler
from stepmix.stepmix import StepMix

ROOT = Path(__file__).resolve().parents[1]
BOOKING = ROOT / "data" / "interim" / "pal_features_booking.parquet"
OUT = ROOT / "outputs" / "cluster_diagnostic"

SAMPLE_LCA = 60_000  # LCA is cheap; k-prototypes runs on a subset of this
SAMPLE_KPROTO = 20_000
K_RANGE = range(3, 10)
SEED = 42

NUMERIC = ["lead_days", "value_tier", "log_rev", "n_coupons"]
BINARY = ["round_trip", "foreign_issue", "is_group", "connecting", "peak_month", "corp_channel"]
NOMINAL = ["dest_region"]


def load_sample() -> pd.DataFrame:
    con = duckdb.connect()
    con.execute("PRAGMA threads=6")
    df = con.execute(f"""
        SELECT lead_days, max_tier AS value_tier, rev_pos, n_coupons,
               coalesce(dest_region, 'Domestic') AS dest_region,
               round_trip::INT round_trip, foreign_issue::INT foreign_issue,
               is_group::INT is_group, connecting::INT connecting,
               peak_month::INT peak_month, corp_channel::INT corp_channel,
               proxy_segment
        FROM read_parquet('{BOOKING}') USING SAMPLE {SAMPLE_LCA} ROWS (reservoir, {SEED})
    """).fetchdf()
    # engineered numerics
    df["lead_days"] = df["lead_days"].clip(0, 365)
    df["value_tier"] = df["value_tier"].fillna(df["value_tier"].median())
    df["log_rev"] = np.log1p(df["rev_pos"].clip(lower=0))
    df["n_coupons"] = df["n_coupons"].clip(1, 8)
    return df


def to_categorical_codes(df: pd.DataFrame) -> pd.DataFrame:
    """All features → integer codes for LCA (bin numerics into interpretable buckets)."""
    out = pd.DataFrame(index=df.index)
    out["lead_bucket"] = pd.cut(df["lead_days"], [-1, 3, 14, 45, 120, 999], labels=False)
    out["value_tier"] = df["value_tier"].round().astype(int) - 1  # 0-based
    out["rev_bucket"] = pd.qcut(df["log_rev"].rank(method="first"), 5, labels=False)
    out["n_coupons_b"] = np.clip(df["n_coupons"] - 1, 0, 3)
    out["dest_region"] = df["dest_region"].astype("category").cat.codes
    for b in BINARY:
        out[b] = df[b].astype(int)
    return out.astype(int)


def run_lca(codes: pd.DataFrame) -> tuple[pd.DataFrame, dict[int, np.ndarray]]:
    rows, labels = [], {}
    for k in K_RANGE:
        m = StepMix(
            n_components=k,
            measurement="categorical",
            n_init=2,
            random_state=SEED,
            verbose=0,
            progress_bar=False,
        )
        m.fit(codes)
        rows.append({"k": k, "BIC": round(m.bic(codes), 1), "AIC": round(m.aic(codes), 1)})
        labels[k] = m.predict(codes)
    return pd.DataFrame(rows), labels


def run_kproto(df: pd.DataFrame, k: int) -> np.ndarray:
    sub = df.sample(SAMPLE_KPROTO, random_state=SEED).reset_index(drop=True)
    num = StandardScaler().fit_transform(sub[NUMERIC])
    cat = sub[BINARY + NOMINAL].astype(str).to_numpy()
    X = np.concatenate([num, cat], axis=1).astype(object)
    cat_idx = list(range(len(NUMERIC), len(NUMERIC) + len(BINARY) + len(NOMINAL)))
    kp = KPrototypes(n_clusters=k, init="Huang", n_init=2, random_state=SEED, n_jobs=1)
    lab = kp.fit_predict(X, categorical=cat_idx)
    return sub["proxy_segment"].to_numpy(), lab


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print("Loading sample ...")
    df = load_sample()
    codes = to_categorical_codes(df)

    print("LCA BIC sweep ...")
    bic_tbl, lca_labels = run_lca(codes)
    k_star = int(bic_tbl.loc[bic_tbl["BIC"].idxmin(), "k"])
    ari_lca = {
        k: round(adjusted_rand_score(df["proxy_segment"], lca_labels[k]), 3) for k in K_RANGE
    }
    bic_tbl["ARI_vs_proxy"] = bic_tbl["k"].map(ari_lca)

    print(f"k-prototypes cross-check at k={k_star} ...")
    proxy_kp, kp_labels = run_kproto(df, k_star)
    ari_kp = round(adjusted_rand_score(proxy_kp, kp_labels), 3)

    # profile the LCA solution at k*: cluster size + dominant proxy + mean traits
    prof = df.copy()
    prof["cluster"] = lca_labels[k_star]
    dom = prof.groupby("cluster")["proxy_segment"].agg(lambda s: s.value_counts().index[0])
    summary = prof.groupby("cluster").agg(
        n=("cluster", "size"),
        pct=("cluster", lambda s: round(100 * len(s) / len(prof), 1)),
        med_lead=("lead_days", "median"),
        med_tier=("value_tier", "median"),
        med_rev=("rev_pos", "median"),
        pct_intl=("dest_region", lambda s: round(100 * (s != "Domestic").mean(), 0)),
        pct_rt=("round_trip", lambda s: round(100 * s.mean(), 0)),
    )
    summary["dominant_proxy"] = dom

    lines = [
        "# Mixed-type clustering diagnostic\n",
        f"Stratified sample: **{len(df):,}** bookings (LCA) / {SAMPLE_KPROTO:,} (k-prototypes). "
        f"Features: {len(NUMERIC)} numeric + {len(BINARY)} binary + {len(NOMINAL)} nominal.\n",
        "## Latent Class Analysis — model selection (lower BIC = better)\n",
        bic_tbl.to_markdown(index=False),
        f"\n**BIC picks k = {k_star}.**\n",
        "## Agreement with rule-based proxy segments (Adjusted Rand Index)\n",
        f"- LCA @ k={k_star} vs proxy: **{ari_lca[k_star]}**  "
        f"(ARI 1.0 = identical, 0 = random; higher = data structure matches the rules)",
        f"- k-prototypes @ k={k_star} vs proxy: **{ari_kp}**",
        "\n*Interpretation:* high ARI → the data-driven clusters largely reproduce the business "
        "segments (rules are well-founded). Low ARI → the natural structure differs from the "
        "taxonomy (worth reconciling) or the data is a continuum.\n",
        f"## LCA cluster profile @ k={k_star}\n",
        summary.reset_index().to_markdown(index=False),
        "",
    ]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n")
    print(f"\nk*={k_star}  LCA-ARI={ari_lca[k_star]}  kproto-ARI={ari_kp}")
    print("Wrote", OUT / "summary.md")


if __name__ == "__main__":
    main()
