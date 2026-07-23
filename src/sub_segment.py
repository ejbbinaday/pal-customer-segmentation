"""Sub-segmentation — LCA *within* the largest rule segments (hybrid refinement layer).

The mixed-type diagnostic (`src/cluster_diagnostic.py`) showed the base is a continuum: the rule-based
purpose×value segments are the primary labels, and clustering's value is finding actionable
**sub-types inside the big segments**. This runs Latent Class Analysis within each large parent
segment (esp. Budget/Adventure), picks the sub-count by BIC, and profiles the sub-types.

Top-level 10 segments stay intact; this only adds a `sub_segment` descriptor within each parent.

Read-only on features; writes `outputs/sub_segments/summary.md`.
Run:  python src/sub_segment.py
"""

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from stepmix.stepmix import StepMix

ROOT = Path(__file__).resolve().parents[1]
BOOKING = ROOT / "data" / "interim" / "pal_features_booking.parquet"
OUT = ROOT / "outputs" / "sub_segments"

PARENTS = ["Budget/Adventure", "OFW/Migrant", "Balikbayan/VFR", "Last-Minute"]
SAMPLE = 40_000  # per parent
# BIC is monotone within segments too (continuum), so cap sub-count at a business-actionable max
# and take the best BIC within it — deliberate pragmatic cut, not a "natural" k.
K_RANGE = range(2, 5)
SEED = 42


def load_parent(con, seg: str) -> pd.DataFrame:
    df = con.execute(f"""
        SELECT lead_days, max_tier AS value_tier, rev_pos, n_coupons,
               coalesce(dest_region,'Domestic') dest_region,
               round_trip::INT round_trip, connecting::INT connecting,
               peak_month::INT peak_month, foreign_issue::INT foreign_issue
        FROM read_parquet('{BOOKING}')
        WHERE proxy_segment = '{seg}'
        USING SAMPLE {SAMPLE} ROWS (reservoir, {SEED})
    """).fetchdf()
    df["lead_days"] = df["lead_days"].clip(0, 365)
    df["value_tier"] = df["value_tier"].fillna(df["value_tier"].median())
    df["n_coupons"] = df["n_coupons"].clip(1, 8)
    return df


def code(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    out["lead_bucket"] = pd.cut(df["lead_days"], [-1, 3, 14, 45, 120, 999], labels=False)
    out["value_tier"] = df["value_tier"].round().astype(int)
    out["n_coupons_b"] = np.clip(df["n_coupons"] - 1, 0, 3)
    out["dest_region"] = df["dest_region"].astype("category").cat.codes
    for b in ["round_trip", "connecting", "peak_month", "foreign_issue"]:
        out[b] = df[b].astype(int)
    # drop within-parent constant columns (no information)
    keep = [c for c in out.columns if out[c].nunique() > 1]
    return out[keep].astype(int)


def best_lca(codes: pd.DataFrame):
    best = None
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
        bic = m.bic(codes)
        if best is None or bic < best[1]:
            best = (k, bic, m)
    k, _, m = best
    return k, m.predict(codes)


def name_sub(row) -> str:
    dirn = "round-trip" if row["pct_rt"] >= 50 else "one-way"
    if row["med_lead"] <= 3:
        timing = "last-minute"
    elif row["med_lead"] <= 14:
        timing = "short-lead"
    elif row["med_lead"] <= 45:
        timing = "advance"
    else:
        timing = "far-advance"
    tier = {1: "supersaver", 2: "saver", 3: "value", 4: "flex"}.get(int(row["med_tier"]), "premium")
    return f"{dirn} · {timing} · {tier}"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("PRAGMA threads=6")
    lines = [
        "# Sub-segmentation (LCA within large rule segments)\n",
        "Top-level 10 segments unchanged; sub-types below are the actionable refinement.\n",
    ]

    for seg in PARENTS:
        df = load_parent(con, seg)
        codes = code(df)
        k, labels = best_lca(codes)
        df = df.assign(sub=labels)
        n_total = len(df)
        prof = (
            df.groupby("sub")
            .agg(
                n=("sub", "size"),
                pct=("sub", lambda s, n=n_total: round(100 * len(s) / n, 1)),
                med_lead=("lead_days", "median"),
                med_tier=("value_tier", "median"),
                med_rev=("rev_pos", "median"),
                pct_rt=("round_trip", lambda s: round(100 * s.mean())),
                pct_conn=("connecting", lambda s: round(100 * s.mean())),
            )
            .reset_index()
        )
        prof["sub_name"] = prof.apply(name_sub, axis=1)
        lines += [
            f"\n## {seg} — {len(df):,} sampled → **{k} sub-types** (BIC)\n",
            prof[
                ["sub_name", "n", "pct", "med_lead", "med_tier", "med_rev", "pct_rt", "pct_conn"]
            ].to_markdown(index=False),
            "",
        ]
        print(f"{seg}: {k} sub-types")

    (OUT / "summary.md").write_text("\n".join(lines) + "\n")
    print("Wrote", OUT / "summary.md")


if __name__ == "__main__":
    main()
