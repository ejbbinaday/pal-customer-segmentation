"""Drift monitoring on the REAL booking table — Regime C of `docs/monitoring-metrics.md`.

`monitor_metrics.py` holds the metric implementations and is dataset-agnostic, but its `main()` builds
a report for the superseded `sample-features.csv` prototype: prototype column names, its own copy of the
pre-v2 waterfall, and an HDBSCAN fit. This module is the real-data entrypoint — it imports the same
metric functions and runs them on `pal_features_booking.parquet` with the shipped `proxy_segment`.

**Regime A (DBCV / silhouette / noise rate) is deliberately NOT computed here, and its absence is a
finding rather than a gap.** Those metrics score the density of a *fitted clustering*. The shipped
labeller is a deterministic rule waterfall: there is no fitted clustering to score, no noise class, and
no density structure to degrade — `model_stress_test.py` established that the population is a continuum
(separation ceilings at 0.381 across ten methods), which is why the rules label in the first place.
Reporting a DBCV for this model would be measuring something the deliverable does not contain.

**Cross-window ARI is likewise not applicable.** ARI compares two labellings of the *same* units; the
waterfall is deterministic, so re-applying it to the same bookings is the identity and scores 1.0 by
construction. The real stability question — does a model fitted a year earlier still carve the later
data — is answered by V4 (`validate_temporal.py`), where **the methods disagree**: GMM(full) transfers
at ARI 0.740 against a 0.595 within-window ceiling (ratio 1.24) while LCA reaches 0.648 against 0.726
(0.89). Quote the panel, not one method. This module does not restate it. (The earlier LCA "0.729 vs
0.645, ratio 1.13" is **withdrawn** — it came from a silent ~43% sample; see the 18 Aug re-run.)

What is left is the question that *does* apply to a deterministic labeller: **the rules cannot drift,
so drift can only enter through the input distribution.** That is exactly what PSI measures.

Windows are imported from `validate_temporal` so the two never diverge: two adjacent 12-month spans
chosen to sit inside the region where no lead time up to the 365-day clip is censored.

Read-only. Writes `outputs/monitor_real/{summary.md,feature_psi.csv,segment_drift.csv,report.json}`.
Run:  python src/monitor_real.py
"""

import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from monitor_metrics import (
    PSI_INVESTIGATE,
    PSI_RETRAIN,
    psi_categorical,
    psi_numeric,
    psi_verdict,
    volume_drift,
)
from validate_temporal import TEST, TRAIN

ROOT = Path(__file__).resolve().parents[1]
BOOKING = ROOT / "data" / "interim" / "pal_features_booking.parquet"
OUT = ROOT / "outputs" / "monitor_real"

# Hash-ordered, so the sample is uniform, exact and reproducible across runs. 1M per window makes the
# PSI estimate far tighter than the 0.10 decision threshold.
SAMPLE_N = 1_000_000
SEG_FLAG_THRESHOLD = 30.0  # |relative share change| %, mirrors monitor_metrics.volume_drift

# The rule inputs — the only fields whose drift can move a label — plus the two derived outputs.
NUMERIC = ["lead_days", "n_coupons", "max_tier", "rev_pos", "stay_nights"]
CATEGORICAL = ["dest_region", "channel", "issue_country", "route_theme", "value_band"]
BOOLEAN = [
    "round_trip",
    "is_international",
    "is_group",
    "is_award",
    "foreign_issue",
    "corp_channel",
    "any_premium",
    "any_business",
    "any_cabin_j",
    "sea_crew",
    "connecting",
    "pilgrimage",
    "is_last_minute",
]
COLS = ["proxy_segment", *NUMERIC, *CATEGORICAL, *BOOLEAN]


def window(con, lo: str, hi: str) -> pd.DataFrame:
    return con.execute(f"""
        SELECT {", ".join(COLS)}
        FROM read_parquet('{BOOKING}')
        WHERE issue_date BETWEEN DATE '{lo}' AND DATE '{hi}'
        ORDER BY hash(customer_id, issue_date)
        LIMIT {SAMPLE_N}
    """).fetchdf()


EPS = 1e-6  # the floor `monitor_metrics.psi_categorical` clips zero-share categories to


def categorical_detail(ref: pd.Series, cur: pd.Series) -> pd.DataFrame:
    """Break a categorical PSI into per-category contributions.

    A headline PSI is not interpretable on its own: a single **new** category can dominate it, and its
    contribution is `share x log(share / EPS)` — i.e. partly a function of the clipping floor rather
    than of the data. Splitting the total is the only way to tell "the mix scrambled" from "one new
    value appeared", which are different operational problems with different responses.
    """
    r = ref.value_counts(normalize=True)
    c = cur.value_counts(normalize=True)
    cats = r.index.union(c.index)
    r = r.reindex(cats).fillna(0.0)
    c = c.reindex(cats).fillna(0.0)
    contrib = (np.clip(c, EPS, None) - np.clip(r, EPS, None)) * np.log(
        np.clip(c, EPS, None) / np.clip(r, EPS, None)
    )
    status = np.where(r == 0, "new", np.where(c == 0, "gone", "shared"))
    return (
        pd.DataFrame(
            {
                "category": cats.astype(str),
                "ref_pct": (100 * r).round(3).to_numpy(),
                "cur_pct": (100 * c).round(3).to_numpy(),
                "psi_contribution": contrib.round(4).to_numpy(),
                "status": status,
            }
        )
        .sort_values("psi_contribution", ascending=False)
        .reset_index(drop=True)
    )


def feature_psi(ref: pd.DataFrame, cur: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in NUMERIC:
        r, c = ref[col].dropna(), cur[col].dropna()
        # A NULL rate that moves is drift in its own right: `stay_nights` is NULL exactly on one-ways,
        # so its coverage IS the round_trip share. Report it rather than let dropna() hide it.
        rows.append(
            {
                "feature": col,
                "kind": "numeric",
                "psi": round(psi_numeric(r, c), 4),
                "ref_coverage_pct": round(100 * len(r) / len(ref), 2),
                "cur_coverage_pct": round(100 * len(c) / len(cur), 2),
            }
        )
    for col in CATEGORICAL + BOOLEAN:
        det = categorical_detail(ref[col], cur[col])
        appeared = det[det.status == "new"]
        rows.append(
            {
                "feature": col,
                "kind": "categorical" if col in CATEGORICAL else "boolean",
                "psi": round(psi_categorical(ref[col], cur[col]), 4),
                # Same PSI with categories absent from the reference window removed. Where the two
                # verdicts disagree, the drift is an arrival, not a redistribution.
                "psi_excl_new": round(float(det[det.status != "new"].psi_contribution.sum()), 4),
                "new_categories": "; ".join(appeared.category),
                "ref_coverage_pct": round(100 * ref[col].notna().mean(), 2),
                "cur_coverage_pct": round(100 * cur[col].notna().mean(), 2),
            }
        )
    out = pd.DataFrame(rows)
    out["new_categories"] = out.new_categories.fillna("")  # numeric rows have no category axis
    out["verdict"] = out.psi.map(psi_verdict)
    out["verdict_excl_new"] = out.psi_excl_new.fillna(out.psi).map(psi_verdict)
    return out.sort_values("psi", ascending=False).reset_index(drop=True)


def segment_drift(ref: pd.DataFrame, cur: pd.DataFrame) -> pd.DataFrame:
    vd = volume_drift(ref.proxy_segment, cur.proxy_segment)
    rev = {
        "ref": ref.groupby("proxy_segment").rev_pos.mean(),
        "cur": cur.groupby("proxy_segment").rev_pos.mean(),
    }
    rows = []
    for seg, d in vd.items():
        r, c = float(rev["ref"].get(seg, float("nan"))), float(rev["cur"].get(seg, float("nan")))
        rows.append(
            {
                "segment": seg,
                **d,
                "ref_rev_per_booking": round(r, 2),
                "cur_rev_per_booking": round(c, 2),
                "rev_rel_change_pct": round(100 * (c - r) / r, 1) if r else None,
            }
        )
    return pd.DataFrame(rows).sort_values("cur_pct", ascending=False).reset_index(drop=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("PRAGMA threads=6")

    print(f"Reference window {TRAIN[0]} → {TRAIN[1]}")
    ref = window(con, *TRAIN)
    print(f"Current   window {TEST[0]} → {TEST[1]}")
    cur = window(con, *TEST)
    print(f"  {len(ref):,} vs {len(cur):,} bookings")

    mix_psi = round(psi_categorical(ref.proxy_segment, cur.proxy_segment), 4)
    feats = feature_psi(ref, cur)
    segs = segment_drift(ref, cur)

    feats.to_csv(OUT / "feature_psi.csv", index=False)
    segs.to_csv(OUT / "segment_drift.csv", index=False)

    worst = feats.iloc[0]
    flagged = feats[feats.verdict != "STABLE"]
    moved = segs[segs.flag]

    # A flagged feature is only actionable with its per-category split — write one file per flag.
    details = {}
    for col in flagged[flagged.kind != "numeric"].feature:
        det = categorical_detail(ref[col], cur[col])
        det.to_csv(OUT / f"psi_contributions_{col}.csv", index=False)
        details[col] = det

    report = {
        "dataset": "data/interim/pal_features_booking.parquet",
        "taxonomy": "waterfall v2 — 11 segments + Unassigned",
        "reference_window": list(TRAIN),
        "current_window": list(TEST),
        "n_reference": int(len(ref)),
        "n_current": int(len(cur)),
        "segment_mix_psi": mix_psi,
        "segment_mix_verdict": psi_verdict(mix_psi),
        "features_flagged": int(len(flagged)),
        "worst_feature": {
            "feature": worst.feature,
            "psi": float(worst.psi),
            "psi_excl_new_categories": (
                None if pd.isna(worst.psi_excl_new) else float(worst.psi_excl_new)
            ),
            "new_categories": worst.new_categories,
            "verdict": worst.verdict,
            "verdict_excl_new": worst.verdict_excl_new,
        },
        "segments_flagged": moved.segment.tolist(),
        "regime_a_dbcv": None,
        "regime_a_note": (
            "not applicable — the shipped labeller is a deterministic rule waterfall, not a fitted "
            "clustering; there is no density structure to score"
        ),
        "cross_window_ari": None,
        "cross_window_ari_note": (
            "not applicable — a deterministic labeller re-applied to the same rows scores 1.0 by "
            "construction; see validate_temporal.py, where transfer is method-dependent "
            "(GMM(full) ratio 1.24, LCA 0.89)"
        ),
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2))

    detail_md = []
    for col, det in details.items():
        top = det.head(5)
        detail_md += [
            f"\n### `{col}` — where the PSI comes from\n",
            top.to_markdown(index=False),
            "\n",
        ]

    lines = [
        "# Drift monitoring — real data, waterfall v2\n",
        f"Reference **{TRAIN[0]} → {TRAIN[1]}** ({len(ref):,} bookings) vs "
        f"current **{TEST[0]} → {TEST[1]}** ({len(cur):,}), hash-sampled from "
        "`pal_features_booking.parquet`. PSI bands: "
        f"< {PSI_INVESTIGATE} stable · {PSI_INVESTIGATE}–{PSI_RETRAIN} investigate · "
        f"> {PSI_RETRAIN} retrain.\n",
        f"\n**Segment-mix PSI: {mix_psi} — {psi_verdict(mix_psi)}.**\n",
        "\n## Feature drift (rule inputs)\n",
        feats.to_markdown(index=False),
        "\n\n`psi_excl_new` recomputes PSI with categories absent from the reference window removed. "
        "Where it disagrees with `psi`, **the drift is an arrival, not a redistribution** — and the "
        f"headline number is partly an artifact: a new category contributes `share x log(share/{EPS})`, "
        "so its size depends on the clipping floor as much as on the data.\n",
        *detail_md,
        "\n## Segment drift\n",
        segs.to_markdown(index=False),
        "\n\n## Not computed, and why\n",
        "- **DBCV / silhouette / noise rate (Regime A)** — these score a fitted clustering. The "
        "deliverable is a deterministic rule waterfall; there is no clustering, no noise class and no "
        "density to degrade. `model_stress_test.py` put separation at a 0.381 ceiling across ten "
        "methods, which is *why* the rules label.\n",
        "- **Cross-window ARI** — a deterministic labeller re-applied to the same bookings scores 1.0 "
        "by construction. The stability question is answered by V4, and there **the methods disagree**: "
        "GMM(full) transfers at **1.24** of its within-window ceiling, LCA at **0.89** "
        "(`outputs/validate_temporal/`). The earlier LCA ratio of 1.13 is withdrawn (43% sample).\n",
        "\n## Reading this\n",
        "The rules cannot drift — they are code. Drift can only enter through the **input "
        "distribution**, which is what every number above measures. A flagged feature means the "
        "population feeding a rule has moved, not that the rule is wrong.\n",
    ]
    (OUT / "summary.md").write_text("".join(lines))

    print(f"  segment-mix PSI {mix_psi} ({psi_verdict(mix_psi)})")
    print(f"  worst feature: {worst.feature} PSI {worst.psi} ({worst.verdict})")
    print(f"  features flagged: {len(flagged)} · segments flagged: {len(moved)}")
    print(f"  wrote {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
