"""Criterion validity — do the segments predict outcomes they were never built to predict?

Construct validity (`src/validate_construct.py`) asks whether segments *differ*. This asks whether
they are *useful*: a segmentation earns its place if it carries signal about what customers go on to
do. That is non-circular whenever the outcome is a field no rule consumes.

Three outcomes, none of them referenced by the waterfall (`src/features_real.py`):

  • **`flown_any`** — primary. ~1.18M non-flown bookings, ≈5% base rate: enough events everywhere.
  • **`refund_any`** — secondary and *deliberately skipped where infeasible*. Refunds are extremely
    rare (Family 3 events, Mabuhay Loyalist 5, Pilgrimage 75 in the whole 22.9M), so a per-segment
    refund model there would be noise dressed as a result. The report says so rather than fitting it.
  • **`rebook_180d`** — did the customer book again within 180 days? Genuinely forward-looking.
    **Right-censoring matters:** bookings issued within 180 days of the extract's last issue date
    cannot have been observed for a full window, so they are excluded rather than counted as "no
    rebooking" — the same forward-book boundary that distorts trend visuals would otherwise
    manufacture a fake decline in loyalty.

For each outcome, a four-rung ladder scored on a held-out split:

    null (base rate) → segment only → the 11 clustering features → features + segment

Two numbers, not a win/loss verdict:

  • **signal retained** = (AUC_segment − 0.5) / (AUC_features − 0.5) — the share of achievable
    discrimination that survives collapsing down to 10 business-meaningful labels.
  • **incremental value** = AUC(features + segment) − AUC(features) — whether the label adds anything
    beyond the raw features. Near zero means the segmentation is a lossy re-encoding: fine for
    communication and targeting, not a source of new signal.

**`signal_retained` can legitimately exceed 1.0, and that is a finding rather than a bug.** The segment
label is *not* a pure compression of the 11 features: the waterfall also reads `sea_crew`, `is_award`,
`pilgrimage`, `any_premium`, `any_business`, `is_domestic` and `is_international`, **none of which is in
the clustering feature set**. So a ratio above 1 says the rule inputs living outside that set carry
real outcome signal the clustering never had access to.

Rare-event caution built in: when adding the 11 features *lowers* AUC versus the label alone, the model
is overfitting a handful of events, and the row is flagged `unstable` rather than presented as a result.

Read-only on `data/interim/pal_features_*.parquet`. Writes `outputs/validate_criterion/`.

Run:  python src/validate_criterion.py            # ~5-10 min
      python src/validate_criterion.py --quick    # ~1 min
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import train_test_split

from validation_anchors import BOOKING, SEED, assert_admissible

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "validate_criterion"

SAMPLE = 300_000
TEST_FRAC = 0.3
MIN_EVENTS = 200  # below this an outcome is not modellable — report, do not fit
REBOOK_WINDOW = 180

# The 11 features the clustering used (docs/methodology.md). Used here as the *reference* rung: how
# much signal is available before compressing to 10 labels. These ARE rule inputs — which is fine,
# because the thing being validated is the outcome prediction, not the segment boundary.
FEATURES = [
    "lead_days",
    "value_tier",
    "log_rev",
    "n_coupons",
    "round_trip",
    "foreign_issue",
    "is_group",
    "connecting",
    "peak_month",
    "corp_channel",
    "dest_region",
]
CATEGORICAL = ("dest_region", "proxy_segment")
OUTCOMES = ("flown_any", "refund_any", "rebook_180d")


def load(n: int, seed: int = SEED) -> tuple[pd.DataFrame, dict]:
    """Booking sample with the 11 features, the segment label, and the three outcomes.

    `rebook_180d` needs the *next* booking date per customer, so it is computed with a window over the
    full table before sampling — a customer's next trip cannot be known from a sample of their trips.
    """
    con = duckdb.connect()
    con.execute("PRAGMA threads=6")
    meta = con.execute(
        f"SELECT max(issue_date) AS last_issue FROM read_parquet('{BOOKING}')"
    ).fetchdf()
    last_issue = meta["last_issue"].iloc[0]
    df = con.execute(f"""
        WITH nb AS (
            SELECT customer_id, issue_date, proxy_segment,
                   least(greatest(lead_days, 0), 365)          AS lead_days,
                   max_tier                                    AS value_tier,
                   ln(1 + greatest(rev_pos, 0))                AS log_rev,
                   least(greatest(n_coupons, 1), 8)            AS n_coupons,
                   round_trip::INT round_trip, foreign_issue::INT foreign_issue,
                   is_group::INT is_group, connecting::INT connecting,
                   peak_month::INT peak_month, corp_channel::INT corp_channel,
                   coalesce(dest_region, 'Domestic')           AS dest_region,
                   flown_any::INT AS flown_any, refund_any::INT AS refund_any,
                   lead(issue_date) OVER (
                       PARTITION BY customer_id ORDER BY issue_date
                   ) AS next_issue
            FROM read_parquet('{BOOKING}')
        ),
        r AS (
            SELECT *, row_number() OVER (
                ORDER BY hash(customer_id || '|' || issue_date::VARCHAR || '|' || {seed})
            ) AS rn
            FROM nb
        )
        SELECT * EXCLUDE (rn) FROM r WHERE rn <= {n}
    """).fetchdf()

    # right-censoring: only bookings with a fully observable 180-day window can answer "rebooked?"
    df["issue_date"] = pd.to_datetime(df["issue_date"])
    cutoff = pd.Timestamp(last_issue) - pd.Timedelta(days=REBOOK_WINDOW)
    observable = df["issue_date"] <= cutoff
    gap = (pd.to_datetime(df["next_issue"]) - df["issue_date"]).dt.days
    df["rebook_180d"] = np.where(
        observable, ((gap <= REBOOK_WINDOW) & gap.notna()).astype(float), np.nan
    )
    df["value_tier"] = df["value_tier"].fillna(df["value_tier"].median())
    for c in CATEGORICAL:
        df[c] = df[c].astype("category")
    info = {
        "last_issue": str(last_issue),
        "rebook_cutoff": str(cutoff.date()),
        "rebook_observable": int(observable.sum()),
        "rebook_censored": int((~observable).sum()),
    }
    return df, info


def fit(df: pd.DataFrame, cols: list[str], y: np.ndarray, seed: int = SEED) -> tuple[float, float]:
    """Held-out AUC and log-loss. `cols == []` is the null model (base rate only)."""
    if not cols:
        ytr, yte = train_test_split(y, test_size=TEST_FRAC, random_state=seed, stratify=y)
        p = np.full(len(yte), ytr.mean())
        return 0.5, float(log_loss(yte, p, labels=[0, 1]))
    Xtr, Xte, ytr, yte = train_test_split(
        df[cols], y, test_size=TEST_FRAC, random_state=seed, stratify=y
    )
    m = HistGradientBoostingClassifier(
        categorical_features=[c in CATEGORICAL for c in cols],
        max_iter=200,
        learning_rate=0.1,
        random_state=seed,
    ).fit(Xtr, ytr)
    p = m.predict_proba(Xte)[:, 1]
    return round(float(roc_auc_score(yte, p)), 4), round(float(log_loss(yte, p, labels=[0, 1])), 5)


def ladder(df: pd.DataFrame, outcome: str) -> tuple[pd.DataFrame, dict]:
    """null → segment-only → features-only → features+segment, for one outcome."""
    sub = df[df[outcome].notna()]
    y = sub[outcome].to_numpy().astype(int)
    events = int(y.sum())
    minority = min(events, len(y) - events)
    if minority < MIN_EVENTS:
        return pd.DataFrame(), {
            "outcome": outcome,
            "skipped": (
                f"only {minority:,} minority-class events in {len(y):,} rows "
                f"(<{MIN_EVENTS}) — not modellable, so not fitted"
            ),
        }
    rungs = {
        "null (base rate)": [],
        "segment only": ["proxy_segment"],
        "features only (11)": FEATURES,
        "features + segment": FEATURES + ["proxy_segment"],
    }
    rows = []
    for name, cols in rungs.items():
        if cols:
            assert_admissible([c for c in cols if c == outcome])  # an outcome is never an input
        auc, ll = fit(sub, cols, y)
        rows.append({"model": name, "n_features": len(cols), "auc": auc, "log_loss": ll})
        print(f"    {name:22s} AUC={auc:.4f}  logloss={ll:.5f}")
    tbl = pd.DataFrame(rows).set_index("model")
    a_seg = tbl.loc["segment only", "auc"]
    a_ftr = tbl.loc["features only (11)", "auc"]
    a_both = tbl.loc["features + segment", "auc"]
    summary = {
        "outcome": outcome,
        "n": len(y),
        "events": events,
        "base_rate_pct": round(100 * y.mean(), 3),
        "auc_segment_only": a_seg,
        "auc_features": a_ftr,
        "auc_features_plus_segment": a_both,
        "signal_retained": (
            round(float((a_seg - 0.5) / (a_ftr - 0.5)), 3) if a_ftr > 0.5 else float("nan")
        ),
        "incremental_value": round(float(a_both - a_ftr), 4),
        # Adding features should never *hurt* — when it does, the model is fitting a handful of rare
        # events rather than signal, and none of this outcome's AUCs should be quoted.
        "unstable": bool(a_both < a_seg - 0.05),
        "skipped": None,
    }
    if summary["unstable"]:
        print(
            f"    ⚠ UNSTABLE — features+segment ({a_both:.3f}) < segment alone ({a_seg:.3f}); "
            f"only {min(events, len(y) - events):,} minority events. Treat as indicative only."
        )
    return tbl.reset_index(), summary


def by_segment(df: pd.DataFrame) -> pd.DataFrame:
    """Raw outcome rates per segment, with event counts so infeasible cells are visible."""
    rows = []
    for s, g in df.groupby("proxy_segment", observed=True):
        r = {"proxy_segment": s, "n": len(g)}
        for o in OUTCOMES:
            v = g[o].dropna()
            r[f"{o}_pct"] = round(100 * float(v.mean()), 3) if len(v) else float("nan")
            r[f"{o}_events"] = int(v.sum()) if len(v) else 0
        rows.append(r)
    return pd.DataFrame(rows).sort_values("n", ascending=False)


def write_report(ladders, summaries, rates, info, cfg) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    summ = pd.DataFrame(summaries)
    lines = [
        "# Criterion validity — do the segments predict what they were not built to predict?\n",
        f"Sample: **{cfg['n']:,}** bookings, seed {SEED}, held-out {int(TEST_FRAC * 100)}%. "
        f"Runtime **{cfg['secs'] / 60:.1f} min**."
        + ("  \n**`--quick` run — directional only.**" if cfg["quick"] else ""),
        "\nOutcomes are fields **no proxy rule consumes**, so this evidence is non-circular: a "
        "segmentation that predicts refunds, no-shows and rebooking is carrying real information, "
        "whatever the labels are called.\n",
        "## 0. How to read this\n",
        "Two numbers, not a win/loss verdict:\n",
        "- **`signal_retained`** = `(AUC_segment − 0.5) / (AUC_features − 0.5)` — the share of "
        "achievable discrimination that survives collapsing down to 10 business labels.\n",
        "- **`incremental_value`** = `AUC(features + segment) − AUC(features)` — whether the label "
        "adds anything beyond the features. **Near zero means the segmentation is a lossy "
        "re-encoding**: still valuable for communication and targeting, but not a source of new "
        "signal, and it must not be sold as one.\n",
        "**A `signal_retained` above 1.0 is a finding, not a bug.** The segment label is *not* a pure "
        "compression of the 11 clustering features — the waterfall also reads `sea_crew`, `is_award`, "
        "`pilgrimage`, `any_premium`, `any_business`, `is_domestic` and `is_international`, **none of "
        "which is in the clustering feature set**. A ratio above 1 therefore says those rule inputs "
        "carry outcome signal the clustering never had access to.\n",
        "**Check the `unstable` column before quoting anything.** It flags outcomes where adding the 11 "
        "features *lowered* AUC versus the label alone — impossible with real signal, so the model is "
        "fitting a handful of rare events. Those AUCs are indicative at best.\n",
        "## 1. Headline\n",
        summ.to_markdown(index=False),
        "\n## 2. The ladders\n",
    ]
    for outcome, tbl in ladders.items():
        lines.append(f"### `{outcome}`\n")
        lines.append(tbl.to_markdown(index=False) if len(tbl) else "_skipped_")
        lines.append("")
    skipped = summ[summ["skipped"].notna()]
    if len(skipped):
        lines += [
            "\n## 3. Deliberately not fitted\n",
            "Rare-event outcomes where a model would be noise with a confidence interval. Stated "
            "rather than quietly fitted:\n",
            skipped[["outcome", "skipped"]].to_markdown(index=False),
        ]
    lines += [
        "\n## 4. Raw outcome rates per segment\n",
        "`*_events` are absolute counts — read them before trusting any rate. Refunds in particular "
        "are so rare in the small segments that their percentages are not usable.\n",
        rates.to_markdown(index=False),
        "\n## 5. Censoring and other caveats\n",
        f"- **`rebook_180d` right-censoring handled explicitly.** Last issue date in the extract is "
        f"**{info['last_issue']}**, so only bookings issued on or before **{info['rebook_cutoff']}** "
        f"have a fully observable 180-day window: **{info['rebook_observable']:,} usable, "
        f'{info["rebook_censored"]:,} excluded.** Counting censored rows as "did not rebook" would '
        "manufacture a fake collapse in loyalty at the extract boundary — the same trap that makes "
        "unfiltered trend visuals draw a cliff.\n",
        "- **`flown_any` is the reliable outcome here**; `refund_any` is usable only in the largest "
        "segments.\n",
        "- The 11-feature rung includes rule inputs by design: the question is how much *outcome* "
        "signal exists before compression, not whether the segment boundary is justified — that is "
        "`src/validate_construct.py`'s job.\n",
        "- Prediction is not causation. A segment that predicts no-shows is not a reason to treat "
        "those customers differently without a policy decision behind it.\n",
    ]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n")
    summ.to_csv(OUT / "headline.csv", index=False)
    rates.to_csv(OUT / "segment_rates.csv", index=False)
    for outcome, tbl in ladders.items():
        if len(tbl):
            tbl.to_csv(OUT / f"ladder_{outcome}.csv", index=False)
    print("\nWrote", OUT / "summary.md")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="smaller sample")
    args = ap.parse_args()
    n = 40_000 if args.quick else SAMPLE
    t0 = time.time()

    print(f"Loading {n:,} bookings (+ next-booking window over the full table) ...")
    df, info = load(n)
    print(
        f"  rebook window observable on {info['rebook_observable']:,}; "
        f"{info['rebook_censored']:,} censored (issued after {info['rebook_cutoff']})"
    )

    ladders, summaries = {}, []
    for outcome in OUTCOMES:
        print(f"\n[{outcome}]")
        tbl, summary = ladder(df, outcome)
        if summary.get("skipped"):
            print(f"    skipped — {summary['skipped']}")
        ladders[outcome] = tbl
        summaries.append(summary)

    rates = by_segment(df)
    write_report(
        ladders,
        summaries,
        rates,
        info,
        {"n": len(df), "secs": time.time() - t0, "quick": args.quick},
    )
    print()
    print(pd.DataFrame(summaries).to_string(index=False))


if __name__ == "__main__":
    main()
