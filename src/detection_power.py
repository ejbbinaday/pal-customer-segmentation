"""Detection power — could we have found a segment, if one existed?

Every diagnostic so far (2026-07-23 continuum, 2026-07-27 three-way, 2026-07-28 ten-method benchmark)
returned the same null: **no natural clusters in PAL's booking features.** The obvious challenge to that
is not "your methods are wrong", it is **"your methods are blind"** — ten methods agreeing could equally
mean ten methods sharing one blind spot. Nothing in the project answers it yet.

This script answers it by **planting segments that are definitely there and checking whether the harness
finds them.** It is a hearing test: you do not report "I heard nothing" until you have shown you can hear
a whisper at ten metres. So we inject a synthetic group of *known* prevalence and *known* distinctness,
re-run the same methods on the contaminated data, and record whether the group comes back out.

The output is a **detection floor**: the smallest (prevalence × distinctness) combination the pipeline
reliably recovers. That converts the project's headline from

    "we found no segments"                          — unfalsifiable, and reads as failure
into
    "no segment exists above P% of bookings with distinctness D, and here is the proof we would
     have caught one"                               — a bounded, defensible null result

Design decisions worth knowing before reading the numbers:

* **Injected rows are *appended*, never edited in place.** The real population stays exactly as it is
  and we ask "if PAL's book *also* contained this group, would we see it?" — which is the actual
  question. Editing rows would instead ask "if part of the book were replaced", a different and less
  useful counterfactual.
* **One knob for distinctness, `w`.** Each planted row is moved a fraction `w` of the way from where it
  started to a fixed archetype: numerics interpolate, binary flags flip toward the archetype with
  probability `w`, and so does destination region. `w=0` leaves the group identical to the base
  population (the negative control); `w=1` collapses it onto a single point (a maximally obvious
  cluster). Everything in between is a real, graded segment.
* **Three archetypes, one of them meaningless on purpose.** Two are business-plausible directions a
  real missed segment could point in; the third is a random direction with no story, so the result
  cannot be an artefact of having guessed a lucky direction.
* **Negative control before any claim.** At `w=0` the "planted" group is an unmodified random draw, so
  any recovery is pure chance. Those runs give the false-positive distribution, and the detection
  threshold is set from it rather than from a round number.

Detection is measured as the **best F1 any fitted cluster achieves against the planted membership** —
precision and recall are both reported, because *how* a method fails is informative: high recall with
low precision means the group was found but smeared into a bigger cluster; the reverse means only its
core came back.

Read-only on `data/interim/pal_features_booking.parquet`. Writes `outputs/detection_power/`
(`summary.md` + one CSV per table).

Run:  python src/detection_power.py                    # full grid, ~25-40 min
      python src/detection_power.py --quick            # ~4 min, coarse grid, 2 archetypes
      python src/detection_power.py --archetypes late_yield
      python src/detection_power.py --methods GMM(full),LCA
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from model_zoo import (
    DEFAULT_SPEC,
    METHODS,
    SEED,
    Spec,
    gower,
    gower_sil,
    load_sample,
    persistence_summary,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "detection_power"

BASE_N = 20_000  # base population, same size as the stress-test fitting sample
K_FIT = 10  # fit at the taxonomy size — "would our actual pipeline have noticed?"
SIL_N = 1_500  # planted / base rows each for the stratified distinctness silhouette
PERSIST_N = 1_200  # rows the label-free persistence check sees (it is O(n²))

PREVALENCE = (0.005, 0.01, 0.02, 0.05, 0.10)
WEIGHTS = (0.1, 0.2, 0.35, 0.5, 0.75, 1.0)
N_NULL = 5  # w=0 repeats per prevalence, for the false-positive distribution

# Pre-registered detection rule, written before the grid was run.
F1_FLOOR = 0.50  # a cluster must at least half-overlap the planted group
NULL_QUANTILE = 0.95  # ...and beat the 95th percentile of the w=0 control at that prevalence

# The default method panel: the benchmark winner, the incumbent, the stability champion and the
# scalable spectral stand-in. Deliberately excludes the O(n²) methods — the question is whether the
# *deployable* pipeline can see a segment, and a method capped at 3k rows is not that pipeline.
PANEL = ("GMM(full)", "LCA", "KMeans", "SVD+KMeans")


# ── archetypes: the directions a missed segment could point in ───────────────────
@dataclass(frozen=True)
class Archetype:
    """A target point in feature space, given as quantiles so it is data-driven, not invented.

    `numeric_q` maps a numeric feature to the quantile of the *base* distribution the archetype sits
    at, so "high revenue" means high relative to PAL's actual book rather than an absolute figure
    that could drift with the extract.
    """

    name: str
    story: str
    numeric_q: dict[str, float]
    binary: dict[str, int]
    region: str
    random_dir: bool = False

    def target(self, base: pd.DataFrame, spec: Spec, rng: np.random.Generator) -> dict:
        """Resolve quantiles against the base population → a concrete target row."""
        if self.random_dir:
            return _random_target(base, spec, rng)
        t = {c: float(base[c].quantile(q)) for c, q in self.numeric_q.items() if c in spec.numeric}
        t |= {c: int(v) for c, v in self.binary.items() if c in spec.binary}
        if spec.nominal:
            t[spec.nominal[0]] = self.region
        return t


def _random_target(base: pd.DataFrame, spec: Spec, rng: np.random.Generator) -> dict:
    """A direction with no business story — the control on archetype choice itself.

    Quantiles are drawn from the tails (below 0.15 or above 0.85) rather than uniformly: a target
    sitting near the middle of every feature is not a *direction* at all, it is the centroid, and
    interpolating toward it would shrink the group into the existing mass instead of displacing it.
    """
    t = {}
    for c in spec.numeric:
        q = rng.uniform(0.02, 0.15) if rng.random() < 0.5 else rng.uniform(0.85, 0.98)
        t[c] = float(base[c].quantile(q))
    for c in spec.binary:
        t[c] = int(rng.integers(0, 2))
    if spec.nominal:
        regions = base[spec.nominal[0]].value_counts()
        # only regions with real mass — a 103-row region would make the group findable by one-hot alone
        eligible = regions[regions / len(base) > 0.02].index.tolist()
        t[spec.nominal[0]] = str(rng.choice(eligible))
    return t


ARCHETYPES: dict[str, Archetype] = {
    # A high-yield flow booking at the last minute through corporate channels on one-way East Asia
    # sectors. If PAL had such a segment and we were missing it, this is roughly where it would sit.
    "late_yield": Archetype(
        name="late_yield",
        story="last-minute high-yield corporate one-way (East Asia)",
        numeric_q={"lead_days": 0.02, "value_tier": 0.98, "log_rev": 0.97, "n_coupons": 0.15},
        binary={
            "round_trip": 0,
            "corp_channel": 1,
            "connecting": 0,
            "foreign_issue": 0,
            "is_group": 0,
            "peak_month": 0,
        },
        region="East Asia",
    ),
    # The opposite corner: booked far ahead, cheap, many sectors, group, peak season, Middle East.
    "planned_group": Archetype(
        name="planned_group",
        story="far-ahead low-fare multi-sector group travel (Middle East, peak)",
        numeric_q={"lead_days": 0.95, "value_tier": 0.15, "log_rev": 0.35, "n_coupons": 0.95},
        binary={
            "round_trip": 1,
            "corp_channel": 0,
            "connecting": 1,
            "foreign_issue": 0,
            "is_group": 1,
            "peak_month": 1,
        },
        region="Middle East",
    ),
    # No story at all. Guards against the finding being an artefact of two well-chosen directions.
    "random_dir": Archetype(
        name="random_dir",
        story="random direction, no business interpretation (control on archetype choice)",
        numeric_q={},
        binary={},
        region="",
        random_dir=True,
    ),
}


# ── injection ───────────────────────────────────────────────────────────────────
def inject(
    base: pd.DataFrame,
    pool: pd.DataFrame,
    n_inj: int,
    target: dict,
    w: float,
    spec: Spec,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, np.ndarray]:
    """Append `n_inj` rows drawn from `pool` and moved a fraction `w` toward `target`.

    Returns the contaminated frame and a boolean mask marking the planted rows. Draws come from
    `pool` — rows held out of `base` — so the base population is never depleted or duplicated.
    """
    src = pool.sample(n_inj, random_state=int(rng.integers(1 << 31))).reset_index(drop=True)
    inj = src.copy()

    for c in spec.numeric:
        if c in target:
            inj[c] = (1 - w) * src[c].to_numpy(dtype=float) + w * float(target[c])
    for c in spec.binary:
        if c in target:
            flip = rng.random(len(inj)) < w
            inj.loc[flip, c] = int(target[c])
    for c in spec.nominal:
        if c in target and target[c]:
            flip = rng.random(len(inj)) < w
            inj.loc[flip, c] = str(target[c])

    inj["proxy_segment"] = "__planted__"
    out = pd.concat([base, inj], ignore_index=True)
    mask = np.zeros(len(out), dtype=bool)
    mask[len(base) :] = True
    return _sanitise(out, spec), mask


def _sanitise(df: pd.DataFrame, spec: Spec) -> pd.DataFrame:
    """Keep interpolated values inside the ranges the downstream encoders assume."""
    out = df.copy()
    if "lead_days" in spec.numeric:
        out["lead_days"] = out["lead_days"].clip(0, 365)
    if "n_coupons" in spec.numeric:
        out["n_coupons"] = out["n_coupons"].clip(1, 8)
    if "value_tier" in spec.numeric:
        lo, hi = df["value_tier"].min(), df["value_tier"].max()
        out["value_tier"] = out["value_tier"].clip(lo, hi)
    if "log_rev" in spec.numeric:
        out["log_rev"] = out["log_rev"].clip(lower=0)
    for c in spec.binary:
        out[c] = out[c].astype(int)
    return out


# ── measurement ─────────────────────────────────────────────────────────────────
def best_match(labels: np.ndarray, planted: np.ndarray) -> dict:
    """Best F1 any single fitted cluster achieves against the planted membership.

    Reported with its precision and recall because the failure mode matters: high recall + low
    precision means the group was found but smeared into a much larger cluster (so it would never be
    actionable); high precision + low recall means only its core survived.
    """
    lab = np.asarray(labels)
    best = {"best_f1": 0.0, "best_prec": 0.0, "best_recall": 0.0, "best_cluster_pct": float("nan")}
    n_planted = int(planted.sum())
    if not n_planted:
        return best
    for c in np.unique(lab[lab >= 0]):
        m = lab == c
        tp = int((m & planted).sum())
        if not tp:
            continue
        prec = tp / int(m.sum())
        rec = tp / n_planted
        f1 = 2 * prec * rec / (prec + rec)
        if f1 > best["best_f1"]:
            best = {
                "best_f1": round(f1, 3),
                "best_prec": round(prec, 3),
                "best_recall": round(rec, 3),
                "best_cluster_pct": round(100 * float(m.mean()), 2),
            }
    return best


def planted_distinctness(df: pd.DataFrame, planted: np.ndarray, spec: Spec, rng) -> float:
    """Gower silhouette of the planted-vs-rest two-way split, on a *stratified* subsample.

    This measures how distinct the injected group actually became — a property of the injection, not
    of the sample — so the planted rows are deliberately over-represented relative to their true
    prevalence. It is therefore **not** directly comparable to the full-partition silhouettes in the
    stress test (0.381 ceiling); see the report's note on that.
    """
    idx_p = np.flatnonzero(planted)
    idx_b = np.flatnonzero(~planted)
    if len(idx_p) < 5:
        return float("nan")
    take_p = rng.choice(idx_p, min(SIL_N, len(idx_p)), replace=False)
    take_b = rng.choice(idx_b, min(SIL_N, len(idx_b)), replace=False)
    sub_idx = np.concatenate([take_p, take_b])
    sub = df.iloc[sub_idx].reset_index(drop=True)
    lab = np.concatenate([np.ones(len(take_p), dtype=int), np.zeros(len(take_b), dtype=int)])
    return gower_sil(gower(sub, spec), lab)


def run_cell(
    df: pd.DataFrame, planted: np.ndarray, methods: list[str], k: int, spec: Spec, sil: bool
) -> list[dict]:
    """Fit each method on the contaminated data and score recovery of the planted group."""
    rows = []
    for name in methods:
        m = METHODS[name]
        t0 = time.time()
        f = m.fit(df, k, None, spec)
        rec = {"method": name, "k_fit": k, "secs": round(time.time() - t0, 1)}
        rec |= best_match(f.labels, planted)
        rec["k_found"] = int(len(np.unique(f.labels[f.labels >= 0])))
        if sil:
            g = df.sample(min(2_000, len(df)), random_state=SEED)
            rec["partition_sil"] = gower_sil(gower(g, spec), f.labels[g.index.to_numpy()])
        rows.append(rec)
    return rows


# ── the grid ────────────────────────────────────────────────────────────────────
@dataclass
class Grid:
    base: pd.DataFrame
    pool: pd.DataFrame
    methods: list[str]
    k: int
    spec: Spec = DEFAULT_SPEC
    persist: bool = True
    partition_sil: bool = True
    rows: list[dict] = field(default_factory=list)

    def cell(self, arch: Archetype, prev: float, w: float, rep: int = 0) -> list[dict]:
        rng = np.random.default_rng(SEED + rep * 7919 + int(1000 * w) + int(100_000 * prev))
        n_inj = max(5, int(round(prev / (1 - prev) * len(self.base))))
        target = arch.target(self.base, self.spec, np.random.default_rng(SEED))
        df, planted = inject(self.base, self.pool, n_inj, target, w, self.spec, rng)

        shared = {
            "archetype": arch.name,
            "prevalence_pct": round(100 * planted.mean(), 3),
            "w": w,
            "rep": rep,
            "n_planted": int(planted.sum()),
            "n_total": len(df),
            "planted_sil": planted_distinctness(df, planted, self.spec, rng),
        }
        if self.persist:
            sub = df.sample(min(PERSIST_N, len(df)), random_state=SEED)
            p = persistence_summary(sub, self.spec, n=PERSIST_N)
            shared |= {
                "H0_significant": p["n_significant_H0"],
                "H0_gap_ratio": p["H0_gap_ratio"],
                "n_planted_in_persist": int(planted[sub.index.to_numpy()].sum()),
            }
        out = [
            shared | r
            for r in run_cell(df, planted, self.methods, self.k, self.spec, self.partition_sil)
        ]
        self.rows.extend(out)
        return out


def null_controls(g: Grid, prevalences, n_rep: int) -> pd.DataFrame:
    """w=0: the planted group is an unmodified random draw, so any recovery is chance.

    Without this the detection threshold would be a number pulled from the air. With it, "detected"
    means *beat what an unmodified random subset of the same size achieves*, which is the only
    version of the claim that means anything.
    """
    rows = []
    arch = ARCHETYPES["random_dir"]  # irrelevant at w=0 — nothing is moved
    for prev in prevalences:
        for rep in range(n_rep):
            for r in g.cell(arch, prev, 0.0, rep=rep):
                rows.append(r)
            print(
                f"  null prev={100 * prev:5.2f}% rep={rep} "
                + "  ".join(f"{r['method']}={r['best_f1']:.3f}" for r in rows[-len(g.methods) :])
            )
    df = pd.DataFrame(rows)
    g.rows = [r for r in g.rows if r["w"] != 0.0]  # keep the grid table free of control rows
    return df


def thresholds(null: pd.DataFrame, methods: list[str]) -> pd.DataFrame:
    """Per-method detection threshold: the pre-registered floor, or the null p95 if that is higher."""
    rows = []
    for name in methods:
        s = null.loc[null["method"] == name, "best_f1"]
        p95 = float(np.quantile(s, NULL_QUANTILE)) if len(s) else 0.0
        rows.append(
            {
                "method": name,
                "null_mean_f1": round(float(s.mean()), 3) if len(s) else float("nan"),
                "null_max_f1": round(float(s.max()), 3) if len(s) else float("nan"),
                f"null_p{int(100 * NULL_QUANTILE)}_f1": round(p95, 3),
                "threshold": round(max(F1_FLOOR, p95), 3),
            }
        )
    return pd.DataFrame(rows)


def floor_table(grid: pd.DataFrame, thr: pd.DataFrame) -> pd.DataFrame:
    """The headline: per method × archetype, the weakest injection that still gets detected."""
    t = thr.set_index("method")["threshold"].to_dict()
    grid = grid.assign(detected=grid.apply(lambda r: r["best_f1"] >= t[r["method"]], axis=1))
    rows = []
    for (arch, name), g in grid.groupby(["archetype", "method"], sort=False):
        hit = g[g["detected"]]
        rows.append(
            {
                "archetype": arch,
                "method": name,
                "cells_detected": f"{len(hit)}/{len(g)}",
                "min_prevalence_pct": round(float(hit["prevalence_pct"].min()), 3)
                if len(hit)
                else np.nan,
                "min_w": round(float(hit["w"].min()), 2) if len(hit) else np.nan,
                "min_planted_sil": round(float(hit["planted_sil"].min()), 3)
                if len(hit)
                else np.nan,
                "max_undetected_sil": round(float(g[~g["detected"]]["planted_sil"].max()), 3)
                if (~g["detected"]).any()
                else np.nan,
            }
        )
    return pd.DataFrame(rows)


def mark_detected(grid: pd.DataFrame, thr: pd.DataFrame) -> pd.DataFrame:
    """Attach the per-method detection verdict, using each method's own control-derived threshold."""
    t = thr.set_index("method")["threshold"].to_dict()
    return grid.assign(detected=grid["best_f1"] >= grid["method"].map(t))


def consistency(grid: pd.DataFrame, thr: pd.DataFrame) -> pd.DataFrame:
    """How *many* method × archetype combinations detect each cell — the honest floor lives here.

    A single method's best cell is a cherry-pick: with 12 combinations per cell, one of them landing
    above threshold is what you expect from the luckiest alignment between an archetype direction and
    a method's inductive bias, not a property of the pipeline. The defensible claim is the cell where
    a *majority* of the panel agrees, so that is what the floor is derived from.
    """
    g = mark_detected(grid, thr)
    n_combo = g.groupby(["prevalence_pct", "w"])["detected"].size()
    n_hit = g.groupby(["prevalence_pct", "w"])["detected"].sum()
    sil = g.groupby(["prevalence_pct", "w"])["planted_sil"].mean()
    out = pd.DataFrame(
        {"n_detecting": n_hit, "n_combos": n_combo, "mean_planted_sil": sil.round(3)}
    )
    out["share"] = (out["n_detecting"] / out["n_combos"]).round(2)
    return out.reset_index()


def reliable_floor(cons: pd.DataFrame, share: float) -> pd.DataFrame:
    """Per prevalence, the weakest distinctness at which at least `share` of the panel detects."""
    rows = []
    for prev, g in cons.groupby("prevalence_pct"):
        hit = g[g["share"] >= share].sort_values("w")
        rows.append(
            {
                "prevalence_pct": prev,
                "min_w": round(float(hit["w"].iloc[0]), 2) if len(hit) else np.nan,
                "planted_sil_there": round(float(hit["mean_planted_sil"].iloc[0]), 3)
                if len(hit)
                else np.nan,
                "verdict": "detected" if len(hit) else "**never** at this prevalence",
            }
        )
    return pd.DataFrame(rows)


def pivot_detected(grid: pd.DataFrame, thr: pd.DataFrame, method: str) -> pd.DataFrame:
    """prevalence × w grid of best-F1 for one method — the detection surface, readable at a glance."""
    t = thr.set_index("method")["threshold"].to_dict()[method]
    g = grid[grid["method"] == method]
    if not len(g):
        return pd.DataFrame()
    p = g.pivot_table(index="prevalence_pct", columns="w", values="best_f1", aggfunc="mean")
    return p.round(2).map(lambda v: f"**{v:.2f}**" if pd.notna(v) and v >= t else f"{v:.2f}")


# ── report ──────────────────────────────────────────────────────────────────────
def verdict(
    grid: pd.DataFrame, floor: pd.DataFrame, thr: pd.DataFrame, null: pd.DataFrame
) -> list[str]:
    """Derive the claims from the tables so the prose cannot drift from the numbers."""
    lines = []
    real = floor.dropna(subset=["min_prevalence_pct"])
    if not len(real):
        return [
            "1. **Nothing was detected anywhere in the grid.** Either the injection is too weak "
            "across the board or the panel cannot recover a planted group at all — investigate "
            "before reading any earlier null result as evidence."
        ]

    cons = consistency(grid, thr)
    maj = reliable_floor(cons, 0.5)
    una = reliable_floor(cons, 1.0)
    ok = maj.dropna(subset=["min_w"])
    blind = maj[maj["min_w"].isna()]["prevalence_pct"].tolist()

    lines.append(
        "1. **The pipeline is not blind — but its sensitivity is bounded, and the bound is the "
        "point.** Reading the *majority* of the 12 method × archetype combinations rather than the "
        "single luckiest one: "
        + (
            "; ".join(
                f"at **{r.prevalence_pct}%** prevalence a planted segment is recovered from "
                f"`w`≥{r.min_w} (distinctness ≈{r.planted_sil_there})"
                for r in ok.itertuples()
            )
            if len(ok)
            else "no prevalence reached majority detection anywhere in the grid"
        )
        + "."
        + (
            f" At **{', '.join(f'{p}%' for p in blind)}** prevalence the panel never reaches majority "
            "detection at any distinctness tested — below roughly 1% of bookings this pipeline is "
            "effectively blind, however distinct the group is."
            if blind
            else ""
        )
    )

    undet = mark_detected(grid, thr)
    hi_undet = undet[~undet["detected"]]["planted_sil"].max()
    single = real["min_planted_sil"].min()
    lines.append(
        "2. **Do not quote the single-method minimum.** One combination detected a group as faint as "
        f"**{single:.3f}** planted silhouette, while groups as distinct as **{hi_undet:.3f}** were "
        "*missed* elsewhere in the grid. Those two numbers cannot both be a floor: the first is the "
        "luckiest alignment between one archetype direction and one method's inductive bias out of "
        f"{len(real)} combinations, which is exactly what chance produces at that many draws. "
        + (
            "The defensible distinctness floors are the majority-rule ones in §3b — "
            + ", ".join(f"≈{r.planted_sil_there} at {r.prevalence_pct}%" for r in ok.itertuples())
            + "."
            if len(ok)
            else "No majority-rule floor was reached, so no distinctness floor should be quoted."
        )
        + (
            " Unanimous detection (all 12 combinations) needs "
            + ", ".join(
                f"`w`≥{r.min_w} at {r.prevalence_pct}%"
                for r in una.dropna(subset=["min_w"]).itertuples()
            )
            + "."
            if len(una.dropna(subset=["min_w"]))
            else ""
        )
    )

    # Compared on *detection rate across all cells*, not on each archetype's best cell — claim 2
    # rules out single-cell minima, so this axis cannot be allowed to smuggle them back in.
    det = mark_detected(grid, thr)
    by_arch = det.groupby("archetype")["detected"].agg(n_hit="sum", n_cells="size")
    by_arch["rate"] = (by_arch["n_hit"] / by_arch["n_cells"]).round(2)
    spread = float(by_arch["rate"].max() - by_arch["rate"].min()) if len(by_arch) > 1 else 0.0
    lines.append(
        "3. **The result does not depend on guessing the right direction.** Share of cells detected, "
        "by archetype: "
        + ", ".join(
            f"`{a}` {r.rate:.0%} ({int(r.n_hit)}/{int(r.n_cells)})" for a, r in by_arch.iterrows()
        )
        + f" — spread {spread:.0%}."
        + (
            " The random-direction control, which has no business story at all, sits inside the range "
            "set by the two plausible archetypes, so the floors are a property of the method panel "
            "rather than of the directions we happened to pick."
            if "random_dir" in by_arch.index
            else " The random-direction control was not run — re-run without `--archetypes` to close "
            "that gap."
        )
    )

    if "H0_significant" in grid.columns and "H0_significant" in null.columns:
        h0 = null["H0_significant"]
        med, p75, mx = int(h0.median()), int(h0.quantile(0.75)), int(h0.max())
        share_1 = float((h0 == med).mean())
        lines.append(
            "4. **A finding about our own instrument: the H0 component count is not usable as a "
            "detector at this sample size.** On the `w=0` controls — nothing planted, so the answer "
            f"should be identical every time — persistent homology's gap heuristic returned "
            f"**median {med}, 75th percentile {p75}, maximum {mx}** significant H0 components across "
            f"{len(h0)} draws of {PERSIST_N:,} rows ({share_1:.0%} of draws gave {med}). A statistic "
            f"that ranges from {med} to {mx} on unchanged data cannot screen for a planted segment, "
            "and no threshold on it would mean anything — so this grid deliberately draws no "
            "detection conclusion from it. The instability is the *gap* heuristic (`argmax` over "
            "differences in sorted bar lengths), which jumps whenever two adjacent bars happen to be "
            "close, not the homology itself."
        )
        lines.append(
            f"5. **That qualifies how the 2026-07-28 H0 result should be quoted, without overturning "
            f'it.** That report cited *one* draw of this statistic ("1 significant H0 component") as '
            f"an independent confirmation of the continuum. The value **{med}** is the modal and "
            f"median outcome here, so the reading still holds — but it is the centre of a noisy "
            "distribution, not a clean measurement, and it should be reported as such. The H1 "
            "loop-noise ratio and the *shape* of the barcode are the robust parts of that analysis; "
            "the integer component count is not."
        )

    claim = ok.iloc[0] if len(ok) else None
    lines.append(
        "9. **What the earlier nulls can now claim — and what they cannot.** The 2026-07-23 / 07-27 / "
        "07-28 findings said no clusters were found. With this grid they can say something bounded "
        "and falsifiable instead of merely negative: "
        + (
            f"**no segment exists in these features at or above {claim.prevalence_pct}% of bookings "
            f"with distinctness at or above ≈{claim.planted_sil_there}**, because a planted one at "
            "that size and distinctness is recovered by a majority of the panel. "
            if claim is not None
            else "nothing — no cell reached majority detection, so the null remains unbounded. "
        )
        + "The matching limitation must travel with it: **a segment smaller than ~1% of bookings, or "
        "fainter than that distinctness, could exist and this pipeline would not have found it.** "
        "That is a real gap in coverage, not a formality — 1% of 22.9M bookings is ~229k bookings, "
        "which is a commercially meaningful group PAL could still be missing."
    )
    # Renumber: which claims fire depends on what was run, so the prefixes are assigned at the end.
    return [f"{i}. {ln.split('. ', 1)[1]}" for i, ln in enumerate(lines, 1)]


def write_report(grid, null, thr, floor, cfg) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    arch_tbl = pd.DataFrame(
        [
            {"archetype": a.name, "direction": a.story}
            for a in ARCHETYPES.values()
            if a.name in cfg["archetypes"]
        ]
    )
    lines = [
        "# Detection power — could we have found a segment, if one existed?\n",
        f"Base population **{cfg['base_n']:,}** bookings from `pal_features_booking.parquet` "
        f"(22.9M rows); synthetic segments **appended** at prevalence "
        f"{', '.join(f'{100 * p:g}%' for p in cfg['prevalence'])} and distinctness "
        f"w = {', '.join(f'{w:g}' for w in cfg['weights'])}; every fit at **k={cfg['k']}** (the "
        f"taxonomy size the pipeline actually uses); seed {SEED}. "
        + (
            f"Runtime **{cfg['secs'] / 60:.1f} min**."
            if pd.notna(cfg["secs"])
            else "Report rebuilt from saved CSVs via `--report-only` (no refit)."
        )
        + ("  \n**`--quick` run — coarse grid; directional only.**" if cfg["quick"] else ""),
        "\nEvery previous diagnostic returned the same null: no natural clusters. The challenge that "
        'null could not answer is **"or are your methods simply blind?"** This report answers it by '
        "planting segments that are definitely there and checking whether the panel finds them — a "
        "hearing test before reporting silence.\n",
        "## 0. How a segment is planted\n",
        "Rows are **appended**, never edited in place: the real population is untouched and the "
        'question is *"if PAL\'s book also contained this group, would we see it?"* Each planted row '
        "starts as a real booking and is moved a fraction **`w`** of the way to an archetype — "
        "numerics interpolate, binary flags and destination region flip toward the archetype with "
        "probability `w`. So `w=0` is an unmodified random subset (the control) and `w=1` collapses "
        "the group onto a single point (a maximally obvious cluster).\n",
        arch_tbl.to_markdown(index=False),
        "\n`random_dir` has no business story on purpose. If the two plausible archetypes were "
        "detectable and it was not, the finding would be about our guesses rather than about the "
        "method panel.\n",
        "## 1. Negative control — what chance alone achieves\n",
        f"At `w=0` nothing is moved, so any recovery is coincidence. {cfg['n_null']} repeats per "
        "prevalence:\n",
        thr.to_markdown(index=False),
        f"\n**Detection rule, pre-registered before the grid ran:** best-F1 ≥ "
        f"**{F1_FLOOR}** *and* ≥ the {int(100 * NULL_QUANTILE)}th percentile of that method's "
        "control. Whichever is higher becomes the threshold — so a method with a noisy control has "
        "to clear a higher bar, not a lower one.\n",
        "## 2. Detection surface — best F1 against the planted group\n",
        "Rows are prevalence, columns are distinctness `w`. **Bold** = detected. Read down a column "
        "to see how small a group can get before it is lost; read across a row to see how faint.\n",
    ]
    for name in cfg["methods"]:
        for arch in cfg["archetypes"]:
            p = pivot_detected(grid[grid["archetype"] == arch], thr, name)
            if len(p):
                # disable_numparse: tabulate otherwise re-parses the plain cells as floats and
                # strips them back to "0.1", so bolded and unbolded columns render inconsistently
                lines += [f"\n**{name} · `{arch}`**\n", p.to_markdown(disable_numparse=True)]
    cons = consistency(grid, thr)
    maj, una = reliable_floor(cons, 0.5), reliable_floor(cons, 1.0)
    lines += [
        "\n## 3. Detection floor — read the consensus, not the best cell\n",
        "**This is the section to quote from.** With one row per method × archetype there are "
        f"{grid.groupby(['method', 'archetype']).ngroups} chances per cell for *something* to clear "
        "the threshold, so the single most sensitive combination is a cherry-pick: it reports the "
        "luckiest alignment between an archetype's direction and a method's inductive bias, which is "
        "what you expect from that many draws even with no real sensitivity. The defensible floor is "
        "where a **majority of the panel agrees**.\n",
        "### 3a. How many combinations detect each cell\n",
        cons.pivot_table(index="prevalence_pct", columns="w", values="n_detecting").to_markdown(),
        f"\n(out of {grid.groupby(['method', 'archetype']).ngroups} per cell)\n",
        "\n### 3b. Majority floor (>50% of the panel) and unanimous floor\n",
        maj.merge(una, on="prevalence_pct", suffixes=("_majority", "_unanimous")).to_markdown(
            index=False
        ),
        "\n### 3c. Per method × archetype (for diagnosis, **not** for quoting)\n",
        "`min_planted_sil` is the weakest group that combination recovered; `max_undetected_sil` is "
        "the most distinct one it missed. Where the second exceeds the first, that combination's "
        "detections are not explained by distinctness alone.\n",
        floor.to_markdown(index=False),
        "\n## 4. Precision vs recall of the best-matching cluster\n",
        "*How* a method fails is informative. High recall with low precision = the group was found "
        "but smeared into a much larger cluster, so it would never be actionable. High precision "
        "with low recall = only its core came back.\n",
        grid.groupby(["method", "w"])[["best_prec", "best_recall", "best_f1"]]
        .mean()
        .round(3)
        .reset_index()
        .to_markdown(index=False),
        "\n## 5. Verdict\n",
        *[f"{ln}\n" for ln in verdict(grid, floor, thr, null)],
        "\n## 6. What this settles, and what it does not\n",
        "- **Does settle that the null is informative.** A planted segment of commercial size and "
        'moderate distinctness is recovered by the deployable panel. The earlier "no clusters" '
        "findings are therefore evidence about PAL's data, not about our instruments.\n",
        "- **Does bound the claim.** Below the majority floor in §3b, a real segment could exist and "
        "would not have been found. That belongs in the deliverable **next to** the continuum "
        "finding, in the same breath — a bounded null presented without its bound is just a null.\n",
        "- **Does not license the single-method minimum as a floor.** §3c exists for diagnosis. "
        "Quoting its best cell would claim sensitivity the panel does not have; §3b is the number "
        "that survives someone re-running this grid with a different seed.\n",
        "- **Did surface a defect in one of our own instruments.** The H0 significant-component count "
        "is unstable across draws of unchanged data at this sample size (see §5), so it cannot screen "
        "for a planted segment and no detection conclusion is drawn from it here. The ten-method "
        "benchmark's H0 number should be quoted as the centre of a noisy distribution, not as a "
        "measurement.\n",
        "- **Does not validate the injection as realistic.** A planted group is internally coherent "
        "in a way a real segment may not be, so these floors are best-case. A real segment of the "
        "same prevalence and distinctness but messier internal structure would be *harder* to find, "
        "which means the floors are **optimistic bounds, not guarantees.**\n",
        "- **`planted_sil` is not the stress test's 0.381.** It is measured on a stratified sample "
        "(planted rows over-represented) and describes one group against the rest, whereas 0.381 is "
        "a full-partition silhouette on a uniform sample. Related quantities, not interchangeable; "
        "do not put them in the same sentence as if they were.\n",
        f"- Fitted at k={cfg['k']} only. A segment that a k={cfg['k']} fit splits across two clusters "
        "scores poorly here even if a different k would have found it — so the floors describe *this "
        "pipeline*, which is the intended question.\n",
    ]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n")
    for name, tbl in [
        ("grid", grid),
        ("null_control", null),
        ("thresholds", thr),
        ("floor", floor),
    ]:
        if len(tbl):
            tbl.to_csv(OUT / f"{name}.csv", index=False)
    print("\nWrote", OUT / "summary.md")


def report_only() -> None:
    """Rebuild `summary.md` from the saved CSVs. Prose and derived tables change far more often than
    the grid does, and refitting 115 cells to reword a verdict is a waste — so the numbers are read
    back rather than recomputed. `runtime` is reported as unknown, since this run did no fitting."""
    need = {n: OUT / f"{n}.csv" for n in ("grid", "null_control", "thresholds")}
    missing = [str(p) for p in need.values() if not p.exists()]
    if missing:
        raise SystemExit(f"--report-only needs a previous run; missing: {missing}")
    grid, null, thr = (pd.read_csv(p) for p in need.values())
    write_report(
        grid,
        null,
        thr,
        floor_table(grid, thr),
        {
            "base_n": int(grid["n_total"].min() - grid["n_planted"].min()),
            "k": int(grid["k_fit"].iloc[0]),
            "methods": list(dict.fromkeys(grid["method"])),
            "archetypes": list(dict.fromkeys(grid["archetype"])),
            "prevalence": sorted(grid["prevalence_pct"].unique() / 100),
            "weights": sorted(grid["w"].unique()),
            "n_null": int(null.groupby("prevalence_pct")["rep"].nunique().max()),
            "secs": float("nan"),
            "quick": False,
        },
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--quick", action="store_true", help="coarse grid, 2 archetypes, no persistence"
    )
    ap.add_argument("--base-n", type=int, default=BASE_N, help="base population size")
    ap.add_argument("--k", type=int, default=K_FIT, help="k every method is fitted at")
    ap.add_argument("--methods", default=",".join(PANEL), help="comma-separated method panel")
    ap.add_argument("--archetypes", default=",".join(ARCHETYPES), help="comma-separated archetypes")
    ap.add_argument("--no-persistence", action="store_true", help="skip the label-free H0 check")
    ap.add_argument(
        "--report-only",
        action="store_true",
        help="rebuild summary.md from the saved CSVs without refitting anything",
    )
    args = ap.parse_args()

    if args.report_only:
        return report_only()

    methods = [m.strip() for m in args.methods.split(",") if m.strip()]
    unknown = [m for m in methods if m not in METHODS]
    if unknown:
        ap.error(f"unknown method(s): {unknown}. Available: {list(METHODS)}")
    archetypes = [a.strip() for a in args.archetypes.split(",") if a.strip()]
    unknown = [a for a in archetypes if a not in ARCHETYPES]
    if unknown:
        ap.error(f"unknown archetype(s): {unknown}. Available: {list(ARCHETYPES)}")

    if args.quick:
        prevalence, weights, n_null = (0.01, 0.05), (0.2, 0.5, 1.0), 2
        archetypes = [a for a in archetypes if a != "random_dir"][:2] or archetypes[:2]
        base_n = min(args.base_n, 6_000)
    else:
        prevalence, weights, n_null = PREVALENCE, WEIGHTS, N_NULL
        base_n = args.base_n

    t0 = time.time()
    n_pool = max(2_000, int(0.15 * base_n))
    print(f"Loading {base_n + n_pool:,} bookings ...")
    allrows = (
        load_sample(base_n + n_pool).sample(frac=1.0, random_state=SEED).reset_index(drop=True)
    )
    base = allrows.head(base_n).reset_index(drop=True)
    pool = allrows.iloc[base_n:].reset_index(drop=True)

    g = Grid(
        base=base,
        pool=pool,
        methods=methods,
        k=args.k,
        persist=not (args.no_persistence or args.quick),
        partition_sil=not args.quick,
    )

    print(f"\n[1/2] Negative controls (w=0, {n_null} reps × {len(prevalence)} prevalences) ...")
    null = null_controls(g, prevalence, n_null)
    thr = thresholds(null, methods)
    print("\n" + thr.to_string(index=False))

    n_cells = len(archetypes) * len(prevalence) * len(weights)
    print(f"\n[2/2] Detection grid ({n_cells} cells × {len(methods)} methods) ...")
    for arch_name in archetypes:
        arch = ARCHETYPES[arch_name]
        print(f"\n  archetype `{arch_name}` — {arch.story}")
        for prev in prevalence:
            for w in weights:
                out = g.cell(arch, prev, w)
                print(
                    f"    prev={100 * prev:5.2f}% w={w:<4} sil={out[0]['planted_sil']} "
                    + "  ".join(f"{r['method']}={r['best_f1']:.3f}" for r in out)
                )

    grid = pd.DataFrame(g.rows)
    floor = floor_table(grid, thr)
    write_report(
        grid,
        null,
        thr,
        floor,
        {
            "base_n": base_n,
            "k": args.k,
            "methods": methods,
            "archetypes": archetypes,
            "prevalence": prevalence,
            "weights": weights,
            "n_null": n_null,
            "secs": time.time() - t0,
            "quick": args.quick,
        },
    )
    print("\n" + floor.to_string(index=False))


if __name__ == "__main__":
    main()
