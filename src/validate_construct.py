"""Construct validity — are the 10 segments distinguishable on evidence the rules never saw?

The project's validation has been circular by construction: agreement is scored against
`proxy_segment`, which the rule waterfall produced. This asks a question that needs no ground-truth
labels, so it works whether or not SME labelling ever happens:

    For every pair of segments, can a classifier tell them apart using ONLY fields the rules
    never touched? (`src/validation_anchors.py` enforces which fields those are.)

Held-out ROC-AUC per pair gives a **segment-distinguishability matrix**: AUC ≈ 0.5 means two segments
are indistinguishable on independent evidence, i.e. the rule separating them may be drawing a line
where no line exists. High AUC means the split is corroborated by data that did not create it.

**The controls are what make the AUCs mean anything.** A bare 0.62 is uninterpretable, so every run
also reports:

  • **Negative control** — each segment split randomly in half and run through the identical pipeline.
    Must land ≈0.50. This is a self-test: if it doesn't, the harness leaks and every other number in
    the report is void. Read it first.
  • **Positive controls** — pairs we expect to genuinely differ (Corporate vs Budget/Adventure, etc.),
    calibrating the top of the scale.

Then the question that motivated this: **OFW/Migrant vs Balikbayan/VFR — 6.8M bookings, 30% of the
base, separated by a single bit (`round_trip`).** It gets a dedicated section on the isolated
population where that bit is the only difference, plus two robustness checks (matched within-country,
and base-rate-normalised seasonality). Also profiles the 2.19M `Unassigned` on the same anchors.

Read-only on `data/interim/pal_features_*.parquet`. Writes `outputs/validate_construct/`.

Run:  python src/validate_construct.py            # ~10-20 min
      python src/validate_construct.py --quick    # ~2 min, smaller sample
"""

from __future__ import annotations

import argparse
import itertools
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from validation_anchors import (
    ANCHORS,
    BASE_WHERE,
    CLEAN_PAIR_WHERE,
    SEED,
    TIER_A,
    admissible_for_groups,
    categorical_mask,
    feature_columns,
    load_anchors,
    segment_counts,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "validate_construct"

PER_SEGMENT = 30_000
MIN_ROWS = 400  # below this a pair's AUC is noise, not a finding
TEST_FRAC = 0.3
PAIR_QUESTION = ("OFW/Migrant", "Balikbayan/VFR")
POSITIVE_CONTROLS = [
    ("Corporate", "Budget/Adventure"),
    ("Pilgrimage", "Balikbayan/VFR"),
    ("Premium Bleisure", "Budget/Adventure"),
]

# AUC bands. 0.60 is the floor for "distinguishable at all" — below it, independent evidence does not
# support treating the two groups as different populations.
BANDS = (
    (0.60, "not distinguishable"),
    (0.75, "weakly distinguishable"),
    (1.01, "clearly distinct"),
)


def band(auc: float) -> str:
    if not np.isfinite(auc):
        return "n/a"
    return next(label for edge, label in BANDS if auc < edge)


def fit_pair(
    df: pd.DataFrame,
    label: np.ndarray,
    cols: list[str],
    seed: int = SEED,
    importances: bool = False,
) -> dict:
    """Train on `cols` only, return held-out AUC (+ optional permutation importances)."""
    X, y = df[cols], np.asarray(label)
    if len(np.unique(y)) < 2 or min(np.bincount(y)) < 20:
        return {"auc": float("nan"), "n": len(df), "top_anchors": None}
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=TEST_FRAC, random_state=seed, stratify=y)
    m = HistGradientBoostingClassifier(
        categorical_features=categorical_mask(cols),
        max_iter=200,
        learning_rate=0.1,
        random_state=seed,
    ).fit(Xtr, ytr)
    auc = float(roc_auc_score(yte, m.predict_proba(Xte)[:, 1]))
    out = {"auc": round(auc, 3), "n": len(df), "top_anchors": None}
    if importances:
        r = permutation_importance(
            m, Xte, yte, scoring="roc_auc", n_repeats=5, random_state=seed, n_jobs=1
        )
        order = np.argsort(r.importances_mean)[::-1]
        out["top_anchors"] = ", ".join(
            f"{cols[i]} ({r.importances_mean[i]:+.3f})" for i in order[:3]
        )
        out["importances"] = {cols[i]: round(float(r.importances_mean[i]), 4) for i in order}
    return out


def pair_frame(df: pd.DataFrame, a: str, b: str) -> tuple[pd.DataFrame, np.ndarray]:
    """Balanced two-segment frame — equal n per side so AUC is not read off a skewed prior."""
    sa, sb = df[df["proxy_segment"] == a], df[df["proxy_segment"] == b]
    n = min(len(sa), len(sb))
    if n < MIN_ROWS // 2:
        return pd.DataFrame(), np.array([])
    sa = sa.sample(n, random_state=SEED)
    sb = sb.sample(n, random_state=SEED)
    both = pd.concat([sa, sb], ignore_index=True)
    return both, (both["proxy_segment"] == b).to_numpy().astype(int)


# ── the matrix ──────────────────────────────────────────────────────────────────
def matrix(df: pd.DataFrame, cols: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Two matrices in one pass.

    `strict` uses TIER_A only (independent of every rule field) so all 45 cells are directly
    comparable. `adaptive` additionally admits the geography/channel anchors *per pair*, but only
    where the rule bit they encode is not what separates that pair — maximum power, full disclosure
    of what was withheld.
    """
    segs = [s for s in df["proxy_segment"].value_counts().index if s != "Unassigned"]
    strict_cols = [c for c in cols if c in TIER_A]
    mat = pd.DataFrame(index=segs, columns=segs, dtype=object)
    rows = []
    for a, b in itertools.combinations(segs, 2):
        sub, y = pair_frame(df, a, b)
        if not len(sub):
            mat.loc[a, b] = mat.loc[b, a] = None
            continue
        ma, mb = sub["proxy_segment"] == a, sub["proxy_segment"] == b
        usable, dropped = admissible_for_groups(sub, ma, mb, cols)
        strict = fit_pair(sub, y, strict_cols, importances=True)
        adaptive = fit_pair(sub, y, usable) if set(usable) != set(strict_cols) else strict
        mat.loc[a, b] = mat.loc[b, a] = strict["auc"]
        rows.append(
            {
                "segment_a": a,
                "segment_b": b,
                "n_per_side": strict["n"] // 2,
                "auc_strict": strict["auc"],
                "verdict_strict": band(strict["auc"]),
                "auc_adaptive": adaptive["auc"],
                "anchors_withheld": "; ".join(dropped) or "none",
                "top_anchors_strict": strict["top_anchors"],
            }
        )
        print(
            f"  {a[:17]:17s} vs {b[:17]:17s} strict={strict['auc']} "
            f"adaptive={adaptive['auc']}  {band(strict['auc'])}"
        )
    for s in segs:
        mat.loc[s, s] = "—"
    return mat, pd.DataFrame(rows).sort_values("auc_strict")


def controls(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Negative (random half-splits, must be ≈0.50) and positive (expected-different) controls.

    Deliberately asymmetric. The **negative** control gets *all* anchors — the more features, the more
    chance of spuriously fitting noise, so that is the stronger self-test. The **positive** controls
    get the *strict* anchors only, so they calibrate the same scale the headline matrix is on;
    on all anchors they would be inflated by exactly the leaks §2 describes.
    """
    strict_cols = [c for c in cols if c in TIER_A]
    rows = []
    for s in df["proxy_segment"].value_counts().index[:6]:
        sub = df[df["proxy_segment"] == s]
        if len(sub) < MIN_ROWS:
            continue
        rng = np.random.default_rng(SEED)
        y = rng.integers(0, 2, len(sub))
        r = fit_pair(sub, y, cols)
        rows.append(
            {
                "control": "negative (random half-split)",
                "pair": s,
                "n": r["n"],
                "auc": r["auc"],
                "expected": "≈0.50",
            }
        )
        print(f"  negative  {s[:26]:26s} AUC={r['auc']}  (expect ~0.50)")
    for a, b in POSITIVE_CONTROLS:
        sub, y = pair_frame(df, a, b)
        if not len(sub):
            continue
        r = fit_pair(sub, y, strict_cols)
        rows.append(
            {
                "control": "positive (expected different, strict anchors)",
                "pair": f"{a} vs {b}",
                "n": r["n"],
                "auc": r["auc"],
                "expected": "well above 0.60",
            }
        )
        print(f"  positive  {a[:12]} vs {b[:12]:14s} AUC={r['auc']} (strict)")
    return pd.DataFrame(rows)


# ── the motivating question ─────────────────────────────────────────────────────
def ofw_balikbayan(cols: list[str], per_segment: int) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    """OFW/Migrant vs Balikbayan/VFR on the population where `round_trip` is the only difference."""
    a, b = PAIR_QUESTION
    df = load_anchors(per_segment, where=CLEAN_PAIR_WHERE, segments=[a, b])
    sub, y = pair_frame(df, a, b)
    # On this population every rule bit except round_trip is held constant by CLEAN_PAIR_WHERE, so
    # the geography/channel anchors are legitimately independent *here*. Verified, not assumed.
    usable, dropped = admissible_for_groups(
        sub, sub["proxy_segment"] == a, sub["proxy_segment"] == b, cols
    )
    head = fit_pair(sub, y, usable, importances=True)
    head["anchors_used"] = ", ".join(usable)
    head["anchors_withheld"] = "; ".join(dropped) or "none — every rule bit is constant here"
    print(f"  clean population: AUC={head['auc']}  ({head['n']:,} rows)  {band(head['auc'])}")
    print(f"  anchors withheld: {head['anchors_withheld']}")

    # robustness 1 — matched within issue_country: same origin market, so geography cannot carry it
    per_country = []
    for country, g in sub.groupby("issue_country", observed=True):
        yy = (g["proxy_segment"] == b).to_numpy().astype(int)
        if len(g) < 1_000 or len(np.unique(yy)) < 2 or min(np.bincount(yy)) < 200:
            continue
        inner = [c for c in cols if c != "issue_country"]
        r = fit_pair(g, yy, inner, importances=False)
        per_country.append(
            {"issue_country": country, "n": r["n"], "auc": r["auc"], "verdict": band(r["auc"])}
        )
    matched = pd.DataFrame(per_country).sort_values("auc", ascending=False)

    # robustness 2 — seasonality, base-rate normalised (most segments peak in May regardless)
    seas = (
        sub.groupby(["proxy_segment", "dep_month"], observed=True).size().rename("n").reset_index()
    )
    seas["dep_month"] = seas["dep_month"].astype(int)  # was categorical — no arithmetic on that
    seas["pct"] = seas.groupby("proxy_segment", observed=True)["n"].transform(
        lambda s: 100 * s / s.sum()
    )
    base = seas.groupby("dep_month")["n"].sum()
    base = 100 * base / base.sum()
    seas["index_vs_base"] = (seas["pct"] / seas["dep_month"].map(base)).round(3)
    season = seas.pivot(index="dep_month", columns="proxy_segment", values="index_vs_base")
    return head, matched, season.sort_index()


def unassigned_profile(cols: list[str], per_segment: int) -> pd.DataFrame:
    """Is the 2.19M `Unassigned` bucket one coherent missing segment, or a grab bag?

    Tested as distinguishability against every named segment: if `Unassigned` were a single coherent
    population the rules simply miss, it should be *separable* from all of them.
    """
    df = load_anchors(per_segment, where=BASE_WHERE)
    rows = []
    for s in df["proxy_segment"].value_counts().index:
        if s == "Unassigned":
            continue
        sub, y = pair_frame(df, "Unassigned", s)
        if not len(sub):
            continue
        usable, dropped = admissible_for_groups(
            sub, sub["proxy_segment"] == "Unassigned", sub["proxy_segment"] == s, cols
        )
        r = fit_pair(sub, y, usable)
        rows.append(
            {
                "vs_segment": s,
                "n_per_side": r["n"] // 2,
                "auc": r["auc"],
                "verdict": band(r["auc"]),
                "anchors_withheld": "; ".join(dropped) or "none",
            }
        )
        print(f"  Unassigned vs {s[:20]:20s} AUC={r['auc']}  {band(r['auc'])}")
    return pd.DataFrame(rows).sort_values("auc")


# ── report ──────────────────────────────────────────────────────────────────────
def write_report(mat, pairs, ctl, head, matched, season, unass, pops, cols, cfg) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    neg = ctl[ctl["control"].str.startswith("negative")]["auc"]
    neg_ok = bool(len(neg)) and neg.between(0.45, 0.55).all()
    pos = ctl[ctl["control"].str.startswith("positive")]["auc"]
    q_auc = head["auc"]

    anchor_tbl = pd.DataFrame(
        [
            {"anchor": k, "why it is independent of the rules": v}
            for k, v in ANCHORS.items()
            if k in cols
        ]
    )
    lines = [
        "# Construct validity — are the segments distinguishable on evidence the rules never saw?\n",
        f"Sample: up to **{cfg['per_segment']:,}** bookings per segment, seed {SEED}, held-out "
        f"{int(TEST_FRAC * 100)}% per pair. Runtime **{cfg['secs'] / 60:.1f} min**."
        + ("  \n**`--quick` run — reduced sample; directional only.**" if cfg["quick"] else ""),
        "\nThis is **non-circular**: no field the rule waterfall consumes is available to any model "
        "here. `src/validation_anchors.py` enforces it, and raises rather than warns.\n",
        "## 0. Read this first — the negative control\n",
        "Each segment split **randomly in half** and run through the identical pipeline. There is no "
        "real difference to find, so AUC must be ≈0.50. If it is not, the harness leaks and every "
        "other number below is void.\n",
        ctl.to_markdown(index=False),
        f"\n**Negative control {'PASSED' if neg_ok else 'FAILED'}** "
        f"(range {neg.min():.3f}–{neg.max():.3f}, expected 0.45–0.55). "
        + (
            f"Positive controls land at {pos.min():.3f}–{pos.max():.3f}, so the scale is calibrated: "
            "the gap between those two rows is the range in which a real difference shows up.\n"
            if neg_ok
            else "**Do not interpret anything below** — fix the leak first.\n"
        ),
        "## 1. What the models were allowed to see\n",
        anchor_tbl.to_markdown(index=False),
        "\nExcluded as circular (consumed by the waterfall): `is_award`, `corp_channel`, "
        "`any_business`, `lead_days`, `pilgrimage`, `sea_crew`, `foreign_issue`, `is_international`, "
        "`max_tier`, `round_trip`, `any_premium`, `is_group`, `is_domestic`. Excluded as trip-type "
        "proxies (they leak `round_trip`): `rev_pos`, `n_coupons`, `connecting`, `n_directions`, "
        "`min_tier`.\n",
        "**Sea-crew bookings are excluded throughout.** `channel` is an anchor and one of its levels "
        "is literally `Sea Crew`, which *is* the OFW rule — keeping them would leak the rule through "
        "an anchor. That is why OFW/Migrant appears below at 2.82M rather than 3.92M: a booking whose "
        "channel says Sea Crew is identified by definition and needs no validation.\n",
        "### Populations analysed\n",
        pops.to_markdown(index=False),
        "\n## 2. Segment-distinguishability matrix (held-out AUC, strict anchors)\n",
        "**<0.60 not distinguishable · 0.60–0.75 weakly · >0.75 clearly distinct.**\n",
        "The matrix uses **strict (Tier-A) anchors only** — `age`, `age_known`, `dep_month`, "
        "`n_bookings` — so every cell is directly comparable. The other three anchors are *finer "
        "versions of fields the rules do use*: `dest_region == 'Domestic'` **is** `is_domestic`, "
        "`issue_country != 'PH'` **is** `foreign_issue`, `channel IN ('TMC','Corporate Web Portal')` "
        "**is** `corp_channel`. Admitting those for a pair the rules split on that very bit returns "
        "AUC ≈ 1.0 and proves only that the rule was applied consistently — a name-based guard cannot "
        "catch that, so admissibility is decided **per pair**: an anchor is allowed only where the "
        "rule bit it encodes is *not* the boundary under test. `auc_adaptive` is that "
        "maximum-power version and `anchors_withheld` records what it dropped and why.\n",
        mat.to_markdown(),
        "\n### Ranked by strict AUC, with what does the distinguishing\n",
        pairs.to_markdown(index=False),
        "\n`top_anchors_strict` is permutation importance on the held-out split — the anchors whose "
        "shuffling costs the most AUC.\n",
        f"\n## 3. The motivating question — {PAIR_QUESTION[0]} vs {PAIR_QUESTION[1]}\n",
        "These two segments are **6.8M bookings, 30% of the base**, and the waterfall separates them "
        "on a **single bit**: `round_trip` (one-way → OFW, round-trip → Balikbayan). Tested here on "
        "the isolated population where every higher-priority branch is excluded, so that bit is the "
        "*only* difference between the two groups.\n",
        f"- **Held-out AUC: {q_auc}** on {head['n']:,} balanced rows → **{band(q_auc)}**",
        f"- Anchors used: `{head['anchors_used']}`",
        f"- Anchors withheld: {head['anchors_withheld']} — every rule bit except `round_trip` is held "
        "constant on this population, so geography and channel are legitimately independent *here* "
        "(checked, not assumed)",
        f"- Most informative anchors: {head['top_anchors']}\n",
        "### Robustness 1 — matched within issue_country\n",
        "Same origin market on both sides, and `issue_country` withheld, so geography cannot carry "
        "the result.\n",
        matched.to_markdown(index=False) if len(matched) else "_no country had enough of both_",
        "\n### Robustness 2 — seasonality, base-rate normalised\n",
        "The rules use no month at all, so departure timing is a clean anchor. Values are indexed "
        "against the pooled monthly distribution (**1.0 = the base rate**), because most segments peak "
        "in May regardless of type — a raw peak proves nothing.\n",
        season.to_markdown(),
        "\n## 4. The `Unassigned` bucket — coherent missing segment, or grab bag?\n",
        "If `Unassigned` were one population the rules simply fail to catch, it should be separable "
        "from every named segment. Low AUCs mean it is a residue, not a segment.\n",
        unass.to_markdown(index=False),
        "\n## 5. What this settles, and what it does not\n",
        "- **Non-circular.** Nothing here is measured against the rules' own output, so these numbers "
        "survive the arrival (or non-arrival) of SME labels.\n",
        "- **It cannot confirm the segment *names*.** Distinguishability shows two groups differ; it "
        "cannot show the group labelled `Corporate` is what PAL's commercial team means by Corporate. "
        "That remains a business judgement — quote this as *behaviourally validated, names not "
        "externally confirmed*.\n",
        "- **A low AUC is evidence about the boundary, not proof of identity.** Two segments that are "
        "indistinguishable on these anchors might still differ on evidence we do not hold (loyalty "
        "tier, length of stay, ancillary spend — all known gaps).\n",
        "- **No taxonomy change follows automatically.** If a split is unsupported, the output is a "
        "*proposal* to PAL with the evidence attached, not a unilateral merge.\n",
    ]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n")
    for name, tbl in [
        ("auc_matrix", mat.reset_index()),
        ("pairs", pairs),
        ("controls", ctl),
        ("ofw_balikbayan_matched", matched),
        ("ofw_balikbayan_seasonality", season.reset_index()),
        ("unassigned", unass),
        ("populations", pops),
    ]:
        if len(tbl):
            tbl.to_csv(OUT / f"{name}.csv", index=False)
    print("\nWrote", OUT / "summary.md")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="smaller sample")
    args = ap.parse_args()
    per_segment = 4_000 if args.quick else PER_SEGMENT
    t0 = time.time()

    print(f"Loading anchors (up to {per_segment:,}/segment) ...")
    df = load_anchors(per_segment, where=BASE_WHERE)
    cols = feature_columns(df)  # raises CircularityError if anything inadmissible slipped in
    print(f"  {len(df):,} rows · anchors: {', '.join(cols)}")
    pops = segment_counts(BASE_WHERE)

    print("\n[1/4] Controls (read the negative one first) ...")
    ctl = controls(df, cols)
    print("\n[2/4] Distinguishability matrix ...")
    mat, pairs = matrix(df, cols)
    print(f"\n[3/4] {PAIR_QUESTION[0]} vs {PAIR_QUESTION[1]} ...")
    head, matched, season = ofw_balikbayan(cols, per_segment)
    print("\n[4/4] Unassigned profile ...")
    unass = unassigned_profile(cols, per_segment)

    write_report(
        mat,
        pairs,
        ctl,
        head,
        matched,
        season,
        unass,
        pops,
        cols,
        {"per_segment": per_segment, "secs": time.time() - t0, "quick": args.quick},
    )


if __name__ == "__main__":
    main()
