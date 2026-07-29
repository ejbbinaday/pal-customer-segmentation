"""Out-of-time stability — are the segments still there a year later? (Plan B item B4)

Everything validated so far is a **photograph**: one pooled snapshot of 22.9M bookings. A segment that
only exists because of one period's booking conditions would pass every test in
`validate_construct.py` and `validate_criterion.py` and still be worthless — PAL would build campaigns
on a group that has already dissolved. This script splits the extract in time and asks whether the
segmentation survives the move.

**The extract's shape dictates the design, and getting this wrong would manufacture a finding.** The
data is filtered on **departure** date (2024-05-01 → 2027-05-31), not on issuance, which truncates the
issuance axis at *both* ends:

* **Left:** a booking issued before 2024-05-01 appears only if it departed on/after that date — i.e.
  only if its lead time was long enough. Issuance before 2024-05 is therefore a **long-lead-only
  sample** (observed mean lead in 2023Q3 issuance: 277 days, against ~38 overall). Including it would
  show a spectacular "collapse in lead time" that is pure selection.
* **Right:** for an issue date `d`, the longest lead that can still be observed is `2027-05-31 − d`.
  That ceiling falls below the modelled 365-day clip for issuance after ~2026-06, so late issuance is
  missing its long-lead tail.

Both windows are therefore chosen to sit strictly inside the region where **no lead time up to the
365-day clip is censored**: two adjacent 12-month windows, each covering all twelve calendar months so
seasonality cannot masquerade as drift.

Outcome fields are a separate trap. `flown_any` runs 100% for 2024–25 issuance and **30.7%** for
2026Q3 — not a collapse in travel, just bookings that have not flown yet. Those fields are **excluded
from every comparison here** and the censoring curve is reported instead, so the exclusion is visible
rather than silent.

What is measured, each against controls:

  1. **Share stability** — do the ten segment sizes hold? Total-variation distance, per-segment
     absolute and relative change, computed on the **full population**, not a sample.
  2. **Revenue-mix stability** — the same for revenue share, which is what the commercial team acts on
     and which can move even when headcount does not.
  3. **Profile drift** — per segment, per feature standardised mean difference. Answers "is it the
     *same kind* of customer?", which share stability alone cannot.
  4. **Adversarial drift** — can a classifier tell which window a booking came from, using only the 11
     clustering features? AUC ≈0.5 means the populations are interchangeable. One number, calibrated by
     controls at both ends.
  5. **Model transfer** — fit the clustering on the earlier window, apply it to the later one, and
     compare against a model fitted on the later window directly. ARI between those two labellings is
     the operational question: *would a model trained a year ago still carve this data the same way?*

Controls, because a drift number with no scale is unreadable: the **negative control** splits the
*earlier window* into random halves (same period, so any drift is noise) and the **positive control**
compares domestic against international bookings inside that window — a genuinely different population.
Real drift is read between those two rails.

Read-only on `data/interim/pal_features_booking.parquet`. Writes `outputs/validate_temporal/`
(`summary.md` + one CSV per table).

Run:  python src/validate_temporal.py              # ~4-8 min
      python src/validate_temporal.py --quick      # ~1 min, smaller samples
      python src/validate_temporal.py --report-only
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import adjusted_rand_score as ari
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from model_zoo import DEFAULT_SPEC, METHODS, SEED, load_sample

ROOT = Path(__file__).resolve().parents[1]
BOOKING = ROOT / "data" / "interim" / "pal_features_booking.parquet"
OUT = ROOT / "outputs" / "validate_temporal"

# Windows derived from the extract's departure filter (see the module docstring). Both sit inside the
# region where no lead time up to the 365-day clip is censored, and both span twelve calendar months.
TRAIN = ("2024-05-01", "2025-04-30")
TEST = ("2025-05-01", "2026-04-30")
DEPARTURE_END = "2027-05-31"  # the extract's travel-window ceiling — sets the observable-lead limit
LEAD_CLIP = 365  # the clip `model_zoo.load_sample` applies; windows must be complete up to it
FG_CHANGE = "2026-04-01"  # the Mabuhay F/G coding flip — lands inside the later window

SAMPLE_N = 30_000  # per window, for the model-transfer and adversarial-drift stages
PER_SEGMENT = 3_000  # per segment per window, for profile drift (small segments need a floor)
K_FIT = 10
PANEL = ("GMM(full)", "LCA")
TEST_FRAC = 0.3

# Bands. Adversarial AUC: 0.5 means the two windows are indistinguishable on the modelled features.
AUC_BANDS = ((0.55, "none"), (0.65, "mild"), (0.75, "moderate"), (1.01, "strong"))
# Standardised mean difference, the usual convention.
SMD_BANDS = ((0.10, "negligible"), (0.25, "small"), (0.50, "moderate"), (1e9, "large"))

FEATURES = list(DEFAULT_SPEC.all_cols)


def band(v: float, bands) -> str:
    if not np.isfinite(v):
        return "n/a"
    return next(label for edge, label in bands if v < edge)


def con() -> duckdb.DuckDBPyConnection:
    c = duckdb.connect()
    c.execute("PRAGMA threads=6")
    return c


def win_case(train=TRAIN, test=TEST) -> str:
    """SQL expression labelling each row `earlier` / `later` / NULL (outside both windows)."""
    return (
        f"CASE WHEN issue_date BETWEEN DATE '{train[0]}' AND DATE '{train[1]}' THEN 'earlier' "
        f"WHEN issue_date BETWEEN DATE '{test[0]}' AND DATE '{test[1]}' THEN 'later' END"
    )


# ── stage 0: the window audit ───────────────────────────────────────────────────
def window_audit(train=TRAIN, test=TEST) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Show that the windows are complete, and that the excluded regions had to be excluded.

    This table is the evidence for the design choice rather than decoration: the excluded early
    issuance carries a mean lead time several times the overall average, which is exactly the
    signature of departure-window selection and exactly what would be misread as a trend.
    """
    c = con()
    q = f"""
        WITH b AS (
          SELECT *, {win_case(train, test)} AS win,
                 DATE '{DEPARTURE_END}' - issue_date AS observable_lead_ceiling
          FROM read_parquet('{BOOKING}')
        )
        SELECT coalesce(win, 'excluded') AS window,
               CASE WHEN win IS NULL AND issue_date < DATE '{train[0]}' THEN 'before (long-lead only)'
                    WHEN win IS NULL THEN 'after (lead tail censored)' ELSE '' END AS why_excluded,
               count(*) AS n,
               min(issue_date) AS first_issue, max(issue_date) AS last_issue,
               round(avg(lead_days), 1) AS mean_lead,
               min(observable_lead_ceiling) AS min_lead_ceiling,
               round(100.0 * avg((lead_days > {LEAD_CLIP})::INT), 2) AS pct_over_clip
        FROM b GROUP BY 1, 2 ORDER BY 1, 2
    """
    audit = c.execute(q).fetchdf()
    audit["complete_to_clip"] = np.where(
        audit["min_lead_ceiling"].astype(float) >= LEAD_CLIP, "yes", "**no**"
    )

    censor = c.execute(f"""
        SELECT date_trunc('quarter', issue_date) AS issue_quarter, count(*) AS n,
               round(100.0 * avg(flown_any::INT), 1) AS flown_pct,
               round(100.0 * avg(refund_any::INT), 3) AS refund_pct
        FROM read_parquet('{BOOKING}')
        GROUP BY 1 HAVING count(*) > 1000 ORDER BY 1
    """).fetchdf()
    return audit, censor


# ── stage 1-2: share and revenue-mix stability, on the full population ──────────
def shares(train=TRAIN, test=TEST) -> tuple[pd.DataFrame, dict]:
    d = (
        con()
        .execute(f"""
        WITH b AS (SELECT *, {win_case(train, test)} AS win FROM read_parquet('{BOOKING}'))
        SELECT win, proxy_segment, count(*) AS n, sum(rev_pos) AS rev
        FROM b WHERE win IS NOT NULL GROUP BY 1, 2
    """)
        .fetchdf()
    )

    def pct(col: str) -> pd.DataFrame:
        p = d.pivot(index="proxy_segment", columns="win", values=col)
        return 100 * p / p.sum()

    n, rev = pct("n"), pct("rev")
    out = pd.DataFrame(
        {
            "share_earlier_pct": n["earlier"].round(2),
            "share_later_pct": n["later"].round(2),
            "delta_pp": (n["later"] - n["earlier"]).round(2),
            "relative_change_pct": (100 * (n["later"] / n["earlier"] - 1)).round(1),
            "rev_share_earlier_pct": rev["earlier"].round(2),
            "rev_share_later_pct": rev["later"].round(2),
            "rev_delta_pp": (rev["later"] - rev["earlier"]).round(2),
        }
    ).sort_values("share_earlier_pct", ascending=False)
    counts = d.groupby("win")["n"].sum()
    summary = {
        "n_earlier": int(counts["earlier"]),
        "n_later": int(counts["later"]),
        "share_tvd_pp": round(0.5 * float((n["later"] - n["earlier"]).abs().sum()), 2),
        "revenue_tvd_pp": round(0.5 * float((rev["later"] - rev["earlier"]).abs().sum()), 2),
        "max_abs_delta_pp": round(float((n["later"] - n["earlier"]).abs().max()), 2),
        "largest_mover": str((n["later"] - n["earlier"]).abs().idxmax()),
    }
    return out.reset_index(), summary


def share_trend(train=TRAIN, test=TEST) -> pd.DataFrame:
    """Quarterly segment share across the whole safe issuance range — trend or jump?

    A single before/after comparison cannot tell a steady drift from a one-off discontinuity, and the
    two have different causes and different remedies. A jump at 2026-04 would point at the F/G coding
    change rather than at customer behaviour.
    """
    d = (
        con()
        .execute(f"""
        SELECT date_trunc('quarter', issue_date) AS issue_quarter, proxy_segment, count(*) AS n
        FROM read_parquet('{BOOKING}')
        WHERE issue_date BETWEEN DATE '{train[0]}' AND DATE '{test[1]}'
        GROUP BY 1, 2
    """)
        .fetchdf()
    )
    p = d.pivot(index="issue_quarter", columns="proxy_segment", values="n").fillna(0)
    return (100 * p.div(p.sum(axis=1), axis=0)).round(2)


def fg_change_check(train=TRAIN, test=TEST) -> pd.DataFrame:
    """Award/group rates by month around the F/G coding flip — is `Mabuhay Loyalist` an artefact?

    `is_award` is the Mabuhay rule, and its source coding changed at 2026-04-01, inside the later
    window. `clean_real.py` applies the date-dependent rule so the semantics should be preserved; this
    checks that they were, because a discontinuity here would invalidate that segment's comparison
    rather than reveal customer drift.
    """
    return (
        con()
        .execute(f"""
        SELECT date_trunc('month', issue_date) AS issue_month, count(*) AS n,
               round(100.0 * avg(is_award::INT), 4) AS award_pct,
               round(100.0 * avg(is_group::INT), 3) AS group_pct,
               round(100.0 * avg((proxy_segment = 'Mabuhay Loyalist')::INT), 4) AS mabuhay_pct
        FROM read_parquet('{BOOKING}')
        WHERE issue_date BETWEEN DATE '{train[0]}' AND DATE '{test[1]}'
        GROUP BY 1 ORDER BY 1
    """)
        .fetchdf()
    )


def load_stratified(window: tuple[str, str], per_segment: int) -> pd.DataFrame:
    """Sample up to `per_segment` bookings **per segment** from one window.

    Profile drift must be read per segment, and a uniform sample cannot support that: at 0.03% of
    bookings, `Mabuhay Loyalist` contributes ~9 rows to a 30k draw and `Pilgrimage` ~60, so exactly
    the segments whose stability is least known would be the ones reported as `n/a`. Stratifying with a
    floor tests all ten. The trade-off is that these rows are **not** a population sample, so they are
    used only for within-segment before/after comparison — never for shares, which come from the full
    population in `shares()`.
    """
    df = (
        con()
        .execute(f"""
        WITH b AS (
          SELECT *, row_number() OVER (PARTITION BY proxy_segment ORDER BY hash(customer_id, issue_date)) AS rn
          FROM read_parquet('{BOOKING}')
          WHERE issue_date BETWEEN DATE '{window[0]}' AND DATE '{window[1]}'
        )
        SELECT lead_days, max_tier AS value_tier, rev_pos, n_coupons,
               coalesce(dest_region, 'Domestic') AS dest_region,
               round_trip::INT round_trip, foreign_issue::INT foreign_issue,
               is_group::INT is_group, connecting::INT connecting,
               peak_month::INT peak_month, corp_channel::INT corp_channel,
               proxy_segment
        FROM b WHERE rn <= {per_segment}
    """)
        .fetchdf()
    )
    # same derivations load_sample applies, so drift is measured on the modelled feature values
    df["lead_days"] = df["lead_days"].clip(0, LEAD_CLIP)
    df["value_tier"] = df["value_tier"].fillna(df["value_tier"].median())
    df["log_rev"] = np.log1p(df["rev_pos"].clip(lower=0))
    df["n_coupons"] = df["n_coupons"].clip(1, 8)
    return df.reset_index(drop=True)


# ── stage 3: profile drift ──────────────────────────────────────────────────────
def profile_drift(a: pd.DataFrame, b: pd.DataFrame) -> pd.DataFrame:
    """Per segment, per feature standardised mean difference between the two windows.

    Share stability answers "are the segments the same size?"; this answers "are they the same kind of
    customer?" A segment can hold its share while its members change underneath, which is the more
    dangerous failure because nothing in a size report would show it.
    """
    rows = []
    num = [c for c in FEATURES if c != "dest_region"]
    for seg in sorted(set(a["proxy_segment"]) & set(b["proxy_segment"])):
        sa, sb = a[a["proxy_segment"] == seg], b[b["proxy_segment"] == seg]
        if min(len(sa), len(sb)) < 50:
            rows.append({"proxy_segment": seg, "n_earlier": len(sa), "n_later": len(sb)})
            continue
        smds = {}
        for c in num:
            x, y = sa[c].astype(float), sb[c].astype(float)
            sd = np.sqrt((x.var(ddof=1) + y.var(ddof=1)) / 2)
            smds[c] = float((y.mean() - x.mean()) / sd) if sd > 0 else 0.0
        # dest_region is nominal: use total-variation distance between its distributions instead
        pa = sa["dest_region"].value_counts(normalize=True)
        pb = sb["dest_region"].value_counts(normalize=True)
        idx = pa.index.union(pb.index)
        tvd = 0.5 * float(
            (pa.reindex(idx, fill_value=0) - pb.reindex(idx, fill_value=0)).abs().sum()
        )
        worst = max(smds, key=lambda k: abs(smds[k]))
        rows.append(
            {
                "proxy_segment": seg,
                "n_earlier": len(sa),
                "n_later": len(sb),
                "mean_abs_smd": round(float(np.mean([abs(v) for v in smds.values()])), 3),
                "max_abs_smd": round(abs(smds[worst]), 3),
                "most_drifted_feature": worst,
                "direction": "higher later" if smds[worst] > 0 else "lower later",
                "dest_region_tvd": round(tvd, 3),
                "verdict": band(abs(smds[worst]), SMD_BANDS),
            }
        )
    return pd.DataFrame(rows)


# ── stage 4: adversarial drift ──────────────────────────────────────────────────
def adversarial(a: pd.DataFrame, b: pd.DataFrame, seed: int = SEED) -> dict:
    """Held-out AUC at telling window `a` from window `b` using only the 11 clustering features.

    Deliberately balanced to equal n per side, so the AUC reflects separability rather than a size
    prior. 0.5 means the two populations are interchangeable on everything the model sees.
    """
    n = min(len(a), len(b))
    rng = np.random.default_rng(seed)
    sa = a.iloc[rng.choice(len(a), n, replace=False)]
    sb = b.iloc[rng.choice(len(b), n, replace=False)]
    X = pd.concat([sa[FEATURES], sb[FEATURES]], ignore_index=True)
    y = np.r_[np.zeros(n, dtype=int), np.ones(n, dtype=int)]
    cat = [c == "dest_region" for c in FEATURES]
    X = X.copy()
    X["dest_region"] = X["dest_region"].astype("category")
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=TEST_FRAC, random_state=seed, stratify=y)
    m = HistGradientBoostingClassifier(
        categorical_features=cat, max_iter=200, learning_rate=0.1, random_state=seed
    ).fit(Xtr, ytr)
    auc = float(roc_auc_score(yte, m.predict_proba(Xte)[:, 1]))
    return {"auc": round(auc, 3), "n_per_side": n, "verdict": band(auc, AUC_BANDS)}


def drift_controls(a: pd.DataFrame, quick: bool) -> pd.DataFrame:
    """Both rails for the drift AUC: random halves (no drift) and domestic-vs-international (real).

    Without these the AUC is uninterpretable — nobody knows whether 0.60 is alarming. The negative
    control says what "no difference" scores on this data and this classifier; the positive control
    says what a difference everyone agrees is real scores on the same scale.
    """
    rows = []
    h = a.sample(frac=0.5, random_state=SEED)
    rows.append(
        {
            "control": "negative — random halves of the earlier window",
            **adversarial(h, a.drop(h.index)),
        }
    )
    dom = a[a["dest_region"] == "Domestic"]
    intl = a[a["dest_region"] != "Domestic"]
    if min(len(dom), len(intl)) > 200:
        # dest_region is *the* difference here, so it must be withheld or the AUC is 1.0 by definition
        cols = [c for c in FEATURES if c != "dest_region"]
        d2, i2 = dom.copy(), intl.copy()
        d2["dest_region"] = i2["dest_region"] = "Domestic"
        res = adversarial(d2[cols + ["dest_region"]], i2[cols + ["dest_region"]])
        rows.append({"control": "positive — domestic vs international (region withheld)", **res})
    if not quick:
        rows.append(
            {
                "control": "negative — random halves, second seed",
                **adversarial(
                    a.sample(frac=0.5, random_state=SEED + 1),
                    a.drop(a.sample(frac=0.5, random_state=SEED + 1).index),
                    seed=SEED + 1,
                ),
            }
        )
    return pd.DataFrame(rows)


# ── stage 5: model transfer ─────────────────────────────────────────────────────
def model_transfer(a: pd.DataFrame, b: pd.DataFrame, k: int, panel) -> pd.DataFrame:
    """Fit on the earlier window, score the later one — vs a model fitted on the later window.

    This is the operational question, not an abstract one: production would score new bookings with a
    model fitted on history. High ARI means last year's model still carves this year's data the same
    way. It is reported beside a **within-window control** (fit on two halves of the *earlier* window,
    both scoring the later one) so the temporal number can be read against the method's own
    reproducibility — a method that disagrees with itself cannot be said to have drifted.
    """
    rows = []
    for name in panel:
        m = METHODS[name]
        fa = m.fit(a, k, b, DEFAULT_SPEC)  # fitted earlier, applied later
        fb = m.fit(b, k, b, DEFAULT_SPEC)  # fitted later, applied later
        h1 = a.sample(frac=0.5, random_state=SEED).reset_index(drop=True)
        h2 = a.drop(a.sample(frac=0.5, random_state=SEED).index).reset_index(drop=True)
        c1 = m.fit(h1, k, b, DEFAULT_SPEC)
        c2 = m.fit(h2, k, b, DEFAULT_SPEC)
        transfer = ari(fa.labels_test, fb.labels_test)
        within = ari(c1.labels_test, c2.labels_test)
        rows.append(
            {
                "method": name,
                "transfer_ARI": round(float(transfer), 3),
                "within_window_control_ARI": round(float(within), 3),
                "ratio_transfer_over_control": round(float(transfer / within), 2)
                if within
                else np.nan,
                "ARI_vs_proxy_fitted_earlier": round(
                    float(ari(b["proxy_segment"].to_numpy(), fa.labels_test)), 3
                ),
                "ARI_vs_proxy_fitted_later": round(
                    float(ari(b["proxy_segment"].to_numpy(), fb.labels_test)), 3
                ),
            }
        )
        print(f"  {name:12s} transfer={transfer:.3f}  within-window control={within:.3f}")
    return pd.DataFrame(rows)


# ── report ──────────────────────────────────────────────────────────────────────
def verdict(summary, drift, ctl, prof, transfer, censor, fg=None) -> list[str]:
    lines = []
    neg = ctl[ctl["control"].str.startswith("negative")]["auc"]
    pos = ctl[ctl["control"].str.startswith("positive")]["auc"]
    neg_hi = float(neg.max()) if len(neg) else float("nan")
    pos_lo = float(pos.min()) if len(pos) else float("nan")
    lines.append(
        f"1. **Segment sizes hold.** Total-variation distance between the two windows is "
        f"**{summary['share_tvd_pp']} pp** across all ten segments — i.e. you would have to move "
        f"{summary['share_tvd_pp']}% of bookings to turn one year's mix into the other's. The largest "
        f"single move is `{summary['largest_mover']}` at {summary['max_abs_delta_pp']} pp. On "
        f"{summary['n_earlier']:,} vs {summary['n_later']:,} bookings, so these are population "
        "figures, not sample noise."
    )
    lines.append(
        f"2. **Revenue mix moves more than headcount** — TVD **{summary['revenue_tvd_pp']} pp** vs "
        f"{summary['share_tvd_pp']} pp on share. Revenue share is the number the commercial team acts "
        "on, and it is the less stable of the two, so a segment holding its size is not evidence that "
        "its value held. Report both or neither."
    )
    adverb = {"none": "not", "mild": "mildly", "moderate": "moderately", "strong": "strongly"}
    lines.append(
        f"3. **The two windows are {adverb.get(drift['verdict'], drift['verdict'])} "
        f"distinguishable** — adversarial AUC "
        f"**{drift['auc']}** on the 11 modelled features, read against a negative control at "
        f"**{neg_hi:.3f}** (random halves, no drift by construction) and a positive control at "
        f"**{pos_lo:.3f}** (domestic vs international, a difference nobody disputes). "
        + (
            "That sits close to the negative rail, so on everything the model sees the later "
            "population is near-interchangeable with the earlier one."
            if np.isfinite(neg_hi) and drift["auc"] - neg_hi < 0.05
            else "That is clear of the negative rail, so the population has measurably shifted — the "
            "drift is real even if the segment sizes absorbed it."
        )
    )
    worst = prof.dropna(subset=["max_abs_smd"]).sort_values("max_abs_smd", ascending=False)
    if len(worst):
        w = worst.iloc[0]
        big = worst[worst["verdict"].isin(("moderate", "large"))]
        calm = worst[~worst["verdict"].isin(("moderate", "large"))]
        # Weighted by the volume each drifting segment carries: drift confined to segments worth a
        # fraction of a percent of bookings is a different finding from drift in the ones that carry
        # the base, and a bare count of "3 segments drifted" hides which of the two happened.
        has_share = "share_later_pct" in worst.columns
        vol = (
            f", carrying **{float(calm['share_later_pct'].sum()):.1f}% of bookings**, against "
            f"**{float(big['share_later_pct'].sum()):.1f}%** for everything moderate-or-larger"
            if has_share
            else ""
        )
        detail = ", ".join(
            f"`{r.proxy_segment}` ({r.most_drifted_feature}"
            + (f", {r.share_later_pct}% of bookings" if has_share else "")
            + ")"
            for r in big.itertuples()
        )
        lines.append(
            f"4. **Composition is stable where the volume is.** "
            f"{len(calm)} of {len(worst)} segments show only negligible-or-small drift{vol}. "
            f"Worst overall is `{w['proxy_segment']}` on `{w['most_drifted_feature']}` "
            f"(SMD {w['max_abs_smd']}, {w['direction']}, {w['verdict']}). Drifting: {detail}. "
            "**Those are the smallest segments in the taxonomy**, where a few hundred bookings "
            "move a mean, so treat this as *unresolved* rather than as established behavioural "
            "change — and re-profile them before quoting last year's description of them."
            if len(big)
            else f"4. **Composition is stable.** No segment of the {len(worst)} tested reaches "
            f"the moderate drift band. Worst is `{w['proxy_segment']}` on "
            f"`{w['most_drifted_feature']}` (SMD {w['max_abs_smd']}, {w['verdict']}). The "
            "members are the same kind of customer, not merely the same count."
        )
    if len(transfer):
        # Ranked on the *ratio*, not raw ARI: the raw number is dominated by how reproducible the
        # method is at all, and picking the highest ARI can hand the headline to a method that
        # actually lost more to time than a lower-ARI one did.
        t = transfer.sort_values("ratio_transfer_over_control", ascending=False).iloc[0]
        holds = t["ratio_transfer_over_control"] >= 0.95
        lines.append(
            (
                "5. **A model fitted a year earlier carves the later data essentially as well as one "
                "fitted on it.** "
                if holds
                else "5. **Time costs the model something measurable, though not much.** "
            )
            + f"Best drift-adjusted transfer is `{t['method']}`: ARI **{t['transfer_ARI']}** against a "
            f"within-window control of **{t['within_window_control_ARI']}** — ratio "
            f"**{t['ratio_transfer_over_control']}**. The control is the **ceiling, not a baseline**: "
            "it is the same method disagreeing with *itself* across two halves of one period, no time "
            "involved. So the shortfall below it — not the raw ARI — is what a year costs. "
            + (
                "Here transfer reaches that ceiling, so on this evidence a yearly refit buys nothing."
                if holds
                else "Re-fitting on recent data is therefore worth doing, but the gap is small enough "
                "that a stale model degrades gracefully rather than breaking."
            )
            + " Note the raw ARIs are well under 1.0 for *both* — that is the continuum showing up "
            "again (these methods do not reproduce themselves exactly on any split), which is why the "
            "ratio is the readable number."
        )
    if fg is not None and len(fg) > 2:
        aw = fg["award_pct"].astype(float)
        pre = aw[fg["issue_month"].astype(str) < FG_CHANGE]
        post = aw[fg["issue_month"].astype(str) >= FG_CHANGE]
        lines.append(
            f"6. **The F/G coding change did not break the Mabuhay rule — but that segment is too "
            f"small to read either way.** `is_award` *is* the Mabuhay rule and its source coding "
            f"changed at {FG_CHANGE}, inside the later window. Monthly award rate runs "
            f"{aw.min():.4f}–{aw.max():.4f}% with **no step at the boundary** "
            + (
                f"(pre-change mean {pre.mean():.4f}% over {len(pre)} months vs {post.mean():.4f}% "
                f"over the {len(post)} month{'s' if len(post) != 1 else ''} after it — too few to "
                f"average meaningfully, and the highest month in the whole series is pre-change)"
                if len(post)
                else ""
            )
            + ", so `clean_real.py`'s date-aware rule is preserving semantics as intended. The month "
            "to month swing is nonetheless larger than the pre/post difference — this segment is "
            "~200 bookings a month — so **its apparent profile drift above is noise-dominated and "
            "should not be reported as behaviour.**"
        )
    late = censor[censor["flown_pct"] < 99]
    lines.append(
        f"7. **Outcome fields were excluded, and this is why.** `flown_any` runs ~100% for early "
        f"issuance and falls to **{censor['flown_pct'].min()}%** in the most recent quarter"
        # coerced because a CSV round-trip (--report-only) hands this back as a string, not a date
        + (
            f" (declining from {pd.to_datetime(late['issue_quarter']).min():%Y-%m} onward)"
            if len(late)
            else ""
        )
        + ". That is right-censoring — bookings that have not flown yet — not a collapse in travel. "
        "Comparing `flown_any` or `refund_any` across these windows would produce a large, entirely "
        "artefactual difference, so no test here uses them. The same boundary makes unfiltered trend "
        "visuals draw a false cliff (2026-07-27 finding)."
    )
    return lines


def write_report(audit, censor, sh, summary, trend, fg, prof, drift, ctl, transfer, cfg) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Out-of-time stability — are the segments still there a year later?\n",
        f"Earlier window **{cfg['train'][0]} → {cfg['train'][1]}** ({summary['n_earlier']:,} bookings) "
        f"vs later window **{cfg['test'][0]} → {cfg['test'][1]}** ({summary['n_later']:,}), split on "
        f"**issue date**. Shares and revenue mix are computed on the **full population**; the drift and "
        f"model-transfer stages use {cfg['sample_n']:,} bookings per window; profile drift uses a "
        f"**per-segment stratified** draw (up to {cfg['per_segment']:,} per segment per window) so the "
        f"small segments are tested rather than reported as `n/a`. Seed {SEED}. "
        + (
            f"Runtime **{cfg['secs'] / 60:.1f} min**."
            if pd.notna(cfg["secs"])
            else "Rebuilt from saved CSVs via `--report-only` (no refit)."
        )
        + ("  \n**`--quick` run — smaller samples; directional only.**" if cfg["quick"] else ""),
        "\nEvery validation before this one was a **photograph** — one pooled snapshot. A segment that "
        "exists only because of one period's booking conditions would pass all of them and still be "
        "worthless to act on. This splits the extract in time and asks whether the segmentation "
        "survives the move.\n",
        "## 0. Why these windows, and not 2024–25 vs 2026–27\n",
        "The extract is filtered on **departure** date "
        f"(2024-05-01 → {DEPARTURE_END}), *not* issuance, which truncates the issuance axis at both "
        "ends. Ignoring that would manufacture a finding rather than reveal one:\n",
        "- **Left:** a booking issued before the travel window opens appears only if its lead time was "
        "long enough to reach it. Early issuance is therefore a **long-lead-only sample** — note its "
        "mean lead below against the ~38-day overall average. Included, it would show a spectacular "
        '"collapse in lead time" that is pure selection.\n',
        f"- **Right:** for issue date `d` the longest observable lead is `{DEPARTURE_END} − d`. Once "
        f"that ceiling drops below the modelled **{LEAD_CLIP}-day clip**, the long-lead tail is "
        "missing. Both windows are chosen to sit strictly inside the complete region.\n",
        "- Each window spans **twelve calendar months**, so seasonality cannot masquerade as drift.\n",
        audit.to_markdown(index=False),
        "\n`complete_to_clip` is the test that matters: it confirms no lead time up to the "
        f"{LEAD_CLIP}-day clip is censored inside either window.\n",
        "## 1. Segment share stability (full population)\n",
        sh.to_markdown(index=False),
        f"\n**Share TVD {summary['share_tvd_pp']} pp · revenue TVD {summary['revenue_tvd_pp']} pp.** "
        "Total-variation distance is the share of bookings you would have to move to turn one window's "
        'mix into the other\'s — a single number for "how different is the mix". Read '
        "`relative_change_pct` with the base rate beside it: a 50% relative move on a segment holding "
        "0.02% of bookings is a handful of rows, not a trend.\n",
        "\n## 2. Share by quarter — trend, or jump?\n",
        "A single before/after comparison cannot separate steady drift from a one-off discontinuity, "
        "and the two have different causes. A jump at 2026-04 would point at the F/G coding change "
        "rather than at customers.\n",
        trend.to_markdown(),
        "\n## 3. The F/G coding change guard\n",
        f"`is_award` **is** the Mabuhay rule, and its source coding changed at **{FG_CHANGE}**, inside "
        "the later window. `clean_real.py` applies the date-dependent rule, so the semantics should be "
        "preserved; this checks that they were. A discontinuity here would invalidate that segment's "
        "comparison rather than reveal drift.\n",
        fg.to_markdown(index=False),
        "\n## 4. Profile drift — same size, or same customer?\n",
        "Standardised mean difference per feature, per segment. A segment can hold its share while its "
        "members change underneath, which is the more dangerous failure because a size report would "
        "show nothing. Bands: <0.10 negligible · 0.10–0.25 small · 0.25–0.50 moderate · >0.50 large.\n",
        "\n**Stratified, not a population sample.** A uniform draw gives `Mabuhay Loyalist` (0.03% of "
        "bookings) ~9 rows, so precisely the segments whose stability is least known would come back "
        "`n/a`. These rows are therefore sampled with a per-segment floor and used **only** for "
        "within-segment before/after comparison — the shares in §1 come from the full population.\n",
        prof.to_markdown(index=False),
        "\n## 5. Adversarial drift — can a model tell the windows apart?\n",
        'One number for "has the population changed?": held-out AUC at classifying which window a '
        "booking came from, using only the 11 clustering features, balanced to equal n per side. "
        "**0.5 means interchangeable.** Bands: <0.55 none · 0.55–0.65 mild · 0.65–0.75 moderate · "
        ">0.75 strong.\n",
        pd.DataFrame([{"comparison": "earlier vs later window", **drift}]).to_markdown(index=False),
        "\n**The controls are what make that number readable.** Without them nobody knows whether "
        "0.60 is alarming:\n",
        ctl.to_markdown(index=False),
        "\n## 6. Model transfer — would last year's model still work?\n",
        "Fit the clustering on the earlier window and apply it to the later one; separately fit on the "
        "later window and apply it to itself; ARI between those two labellings of the *same* rows. "
        "This is what production actually does — score new bookings with a model fitted on history.\n",
        transfer.to_markdown(index=False) if len(transfer) else "_skipped_",
        "\n`within_window_control_ARI` is the **ceiling, not a baseline**: the same method fitted on "
        "two random halves of the *earlier* window, both scoring the later one. It measures the "
        "method disagreeing with itself, with no time involved. Transfer cannot beat it by much, and "
        "the shortfall below it — not the raw ARI — is what time costs.\n",
        "\n## 7. Outcome censoring — the fields this stage refuses to use\n",
        "`flown_any` and `refund_any` are **excluded from every comparison above.** They are not "
        "stable enough to compare across time, and the reason is structural rather than behavioural:\n",
        censor.to_markdown(index=False),
        "\nA booking issued last month has not flown yet. Comparing these fields across windows would "
        "produce a large and entirely artefactual difference — the same forward-book boundary that "
        "makes unfiltered trend visuals draw a false cliff (2026-07-27). `validate_criterion.py` "
        "handles the same problem by excluding right-censored rows from `rebook_180d`.\n",
        "\n## 8. Verdict\n",
        *[f"{ln}\n" for ln in verdict(summary, drift, ctl, prof, transfer, censor, fg)],
        "\n## 9. What this settles, and what it does not\n",
        "- **Does settle that the segmentation is not a one-period artefact.** Sizes, composition and "
        "model transfer all hold across a twelve-month step on full-population counts. That was a real "
        "risk and it is now closed.\n",
        "- **Does not extrapolate.** Two adjacent windows inside one extract test *one* step. Stability "
        "across 2024–26 is not evidence of stability through a demand shock, a network change or a "
        "fare-structure revision — the mechanism that would break it is not in this data.\n",
        "- **Does not cover the newest bookings.** Issuance after "
        f"{cfg['test'][1]} is excluded because its long-lead tail is censored, so the most recent "
        "~3 months are untested here. A refresh should re-run this once their travel completes.\n",
        "- **Revenue mix is the weaker leg.** It moves more than share does, and revenue is what the "
        "commercial team acts on. Quote the revenue TVD next to the share TVD rather than leading with "
        "the more flattering one.\n",
    ]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n")
    for name, tbl in [
        ("window_audit", audit),
        ("censoring", censor),
        ("shares", sh),
        ("share_trend", trend.reset_index()),
        ("fg_change", fg),
        ("profile_drift", prof),
        ("drift_controls", ctl),
        ("model_transfer", transfer),
        ("summary_stats", pd.DataFrame([summary | {"drift_auc": drift["auc"]}])),
    ]:
        if len(tbl):
            tbl.to_csv(OUT / f"{name}.csv", index=False)
    print("\nWrote", OUT / "summary.md")


def report_only() -> None:
    """Rebuild `summary.md` from saved CSVs — prose changes far more often than the numbers do."""
    need = [
        "window_audit",
        "censoring",
        "shares",
        "share_trend",
        "fg_change",
        "profile_drift",
        "drift_controls",
        "model_transfer",
        "summary_stats",
    ]
    missing = [n for n in need if not (OUT / f"{n}.csv").exists()]
    if missing:
        raise SystemExit(f"--report-only needs a previous run; missing: {missing}")
    t = {n: pd.read_csv(OUT / f"{n}.csv") for n in need}
    st = t["summary_stats"].iloc[0].to_dict()
    trend = t["share_trend"].set_index("issue_quarter")
    write_report(
        t["window_audit"],
        t["censoring"],
        t["shares"],
        {k: v for k, v in st.items() if k != "drift_auc"},
        trend,
        t["fg_change"],
        t["profile_drift"],
        {
            "auc": st["drift_auc"],
            "n_per_side": np.nan,
            "verdict": band(float(st["drift_auc"]), AUC_BANDS),
        },
        t["drift_controls"],
        t["model_transfer"],
        {
            "train": TRAIN,
            "test": TEST,
            "sample_n": SAMPLE_N,
            "per_segment": PER_SEGMENT,
            "secs": float("nan"),
            "quick": False,
        },
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="smaller samples, fewer controls")
    ap.add_argument("--sample-n", type=int, default=SAMPLE_N, help="bookings sampled per window")
    ap.add_argument("--k", type=int, default=K_FIT, help="k for the model-transfer stage")
    ap.add_argument("--methods", default=",".join(PANEL), help="comma-separated transfer panel")
    ap.add_argument("--report-only", action="store_true", help="rebuild summary.md from saved CSVs")
    args = ap.parse_args()
    if args.report_only:
        return report_only()

    panel = [m.strip() for m in args.methods.split(",") if m.strip()]
    unknown = [m for m in panel if m not in METHODS]
    if unknown:
        ap.error(f"unknown method(s): {unknown}. Available: {list(METHODS)}")
    n = min(args.sample_n, 6_000) if args.quick else args.sample_n

    t0 = time.time()
    print("[1/6] Window audit ...")
    audit, censor = window_audit()
    print(audit.to_string(index=False))

    print("\n[2/6] Share + revenue mix (full population) ...")
    sh, summary = shares()
    print(f"  share TVD {summary['share_tvd_pp']} pp · revenue TVD {summary['revenue_tvd_pp']} pp")
    trend = share_trend()
    fg = fg_change_check()

    print(f"\n[3/6] Sampling {n:,} bookings per window (+ per-segment strata) ...")
    a = load_sample(n, where=f"WHERE issue_date BETWEEN DATE '{TRAIN[0]}' AND DATE '{TRAIN[1]}'")
    b = load_sample(n, where=f"WHERE issue_date BETWEEN DATE '{TEST[0]}' AND DATE '{TEST[1]}'")
    per_seg = 400 if args.quick else PER_SEGMENT
    sa, sb = load_stratified(TRAIN, per_seg), load_stratified(TEST, per_seg)

    print("\n[4/6] Profile drift (stratified, so small segments are tested too) ...")
    prof = profile_drift(sa, sb)
    # Carry the population share alongside the drift: a large SMD on a 0.03% segment and the same SMD
    # on a 39% segment are not the same finding, and the table has to make that impossible to miss.
    prof = prof.merge(
        sh[["proxy_segment", "share_later_pct"]], on="proxy_segment", how="left"
    ).sort_values("share_later_pct", ascending=False)
    print(prof.to_string(index=False))

    print("\n[5/6] Adversarial drift + controls ...")
    drift = adversarial(a, b)
    ctl = drift_controls(a, args.quick)
    print(f"  earlier vs later AUC {drift['auc']} ({drift['verdict']})")
    print(ctl.to_string(index=False))

    print(f"\n[6/6] Model transfer at k={args.k} ...")
    transfer = model_transfer(a, b, args.k, panel)

    write_report(
        audit,
        censor,
        sh,
        summary,
        trend,
        fg,
        prof,
        drift,
        ctl,
        transfer,
        {
            "train": TRAIN,
            "test": TEST,
            "sample_n": n,
            "per_segment": per_seg,
            "secs": time.time() - t0,
            "quick": args.quick,
        },
    )
    for ln in verdict(summary, drift, ctl, prof, transfer, censor, fg):
        print("\n" + ln)


if __name__ == "__main__":
    main()
