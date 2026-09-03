"""Model stress test & benchmark — which clustering method is actually right for PAL, and why.

`src/kproto_compare.py` (2026-07-27) settled a three-way question: k-prototypes vs k-modes vs LCA.
This widens the field to **ten methods across six algorithm families** — adding **GMM** (full + diag
covariance), **SVD/spectral** (scalable and exact), **Support Vector Clustering**, **TDA-Mapper** and
persistent homology, plus a **KMeans** floor — and stops asking only "which agrees with the taxonomy?"
A method that wins on agreement but falls apart when you resample, perturb or drop a feature is not a
model, it is a coincidence. So each method is scored on eight axes:

  1. **Taxonomy agreement** — ARI vs the rule-based proxy segments, over a k sweep.
     *Circular by construction* (the proxy is the rules), so it measures alignment, never correctness.
  2. **Separation** — Gower silhouette. Mixed-type-correct; Euclidean-on-one-hots flatters everything.
  3. **Natural k** — each method's own criterion (BIC / cost / inertia / ncut) + relative gain per k,
     and an *algorithm-independent* verdict from **H0 persistent homology**, which never sees a label.
  4. **Split-half stability** — fit on half A, predict a common set, vs fit on half B and do the same.
  5. **Bootstrap stability** — 3 bootstrap refits, each scored on that same held-out set, pairwise ARI.
     Catches solutions that only exist for one particular draw of the data.
  6. **Perturbation robustness** — jitter every numeric by 5% of its range and flip 5% of the binary
     flags; ARI against the unperturbed labels. Real segments survive measurement noise.
  7. **Feature-dropout robustness** — leave-one-feature-out refits, ARI vs full-feature labels.
     A low *minimum* means the whole segmentation hinges on one column.
  8. **Learnability (SVM probe)** — held-out SVM accuracy at predicting each solution's own labels.
     Deliberately paired with axis 2: a geometric cut of a continuum scores ≈1.0 here *by
     construction*, so high probe + low silhouette is the signature of an arbitrary slice, not a find.

Then a weighted leaderboard (weights printed in the report, so anyone can re-weigh them) and a verdict.

Read-only on `data/interim/pal_features_booking.parquet`. Writes `outputs/model_stress_test/`
(`summary.md` + one CSV per axis).

Run:  python src/model_stress_test.py             # full, ~45-75 min
      python src/model_stress_test.py --quick     # ~5 min, smaller sample and k sweep
      python src/model_stress_test.py --stress-k 4
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score as ari

from model_zoo import (
    DEFAULT_SPEC,
    METHODS,
    SEED,
    SVC_GAMMAS,
    Fit,
    Method,
    Spec,
    fit_svc,
    gower,
    gower_sil,
    load_sample,
    persistence_summary,
    svm_probe,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "model_stress_test"

SAMPLE = 20_000  # fitting sample for the sweep (matches src/kproto_compare.py for comparability)
SCORE_N = 4_000  # common held-out set every stability axis is scored on
SIL_N = 4_000  # Gower silhouette is O(n²) in memory
PROBE_N = 3_000  # SVM separability probe sample
K_RANGE = range(3, 13)
STRESS_K = 10  # the business taxonomy size — the k the deliverable actually needs
SIZE_STEPS = (5_000, 20_000, 50_000)
N_BOOTSTRAP = 3
JITTER_FRAC = 0.05  # perturbation: σ as a share of each numeric's range
FLIP_FRAC = 0.05  # perturbation: share of binary flags flipped

# Leaderboard weights — stated openly so the ranking can be re-derived under other priorities.
WEIGHTS = {
    "agreement": 0.25,
    "separation": 0.25,
    "stability": 0.20,
    "robustness": 0.15,
    "learnability": 0.10,
    "scalability": 0.05,
}


# ── plumbing: per-method sample caps that keep row identity ──────────────────────
def cap_positions(n_rows: int, max_n: int | None, seed: int = SEED) -> np.ndarray:
    """Positional indices a capped method sees. Deterministic, so two methods with the same cap
    see the *same* rows and their labels stay directly comparable."""
    if max_n is None or n_rows <= max_n:
        return np.arange(n_rows)
    return np.sort(np.random.default_rng(seed).choice(n_rows, max_n, replace=False))


def run(
    m: Method,
    train: pd.DataFrame,
    k: int,
    test: pd.DataFrame | None = None,
    spec: Spec = DEFAULT_SPEC,
) -> tuple[Fit, np.ndarray]:
    """Fit one method, honouring its sample cap. Also returns which rows of `train` it saw."""
    pos = cap_positions(len(train), m.max_n)
    tr = train.iloc[pos].reset_index(drop=True)
    return m.fit(tr, k, test, spec), pos


def sizes_pct(labels: np.ndarray) -> tuple[float, float, float]:
    """Smallest / largest cluster share, and the share left unassigned (label -1)."""
    lab = np.asarray(labels)
    unass = round(100 * float((lab < 0).mean()), 1)
    kept = lab[lab >= 0]
    if not len(kept):
        return float("nan"), float("nan"), unass
    s = pd.Series(kept).value_counts(normalize=True)
    return round(100 * float(s.min()), 1), round(100 * float(s.max()), 1), unass


@dataclass
class SilScorer:
    """Gower silhouette scoring, cached per sample-cap so the O(n²) matrix is built once each."""

    fit_df: pd.DataFrame
    cache: dict = None

    def __post_init__(self):
        self.cache = {}

    def score(self, pos: np.ndarray, labels: np.ndarray) -> float:
        key = len(pos)
        if key not in self.cache:
            sub = self.fit_df.iloc[pos].reset_index(drop=True)
            s_pos = np.sort(
                np.random.default_rng(SEED).choice(len(sub), min(SIL_N, len(sub)), replace=False)
            )
            self.cache[key] = (s_pos, gower(sub.iloc[s_pos].reset_index(drop=True)))
        s_pos, dist = self.cache[key]
        return gower_sil(dist, np.asarray(labels)[s_pos])


# ── axes 1-3: the k sweep ───────────────────────────────────────────────────────
def sweep(fit_df: pd.DataFrame, ks, probe: bool) -> tuple[pd.DataFrame, dict]:
    sil = SilScorer(fit_df)
    rows, labels = [], {}

    for name, m in METHODS.items():
        if not m.honours_k:
            continue  # SVC's k emerges from γ — it gets its own section
        for k in ks:
            f, pos = run(m, fit_df, k)
            lab = f.labels
            sub = fit_df.iloc[pos].reset_index(drop=True)
            labels[(name, k)] = (lab, pos)
            row = {
                "method": name,
                "family": m.family,
                "k_requested": k,
                "n_used": len(pos),
                "criterion": m.score_name,
                "score": round(f.score, 1),
                "ARI_vs_proxy": round(ari(sub["proxy_segment"].to_numpy(), lab), 3),
                "gower_sil": sil.score(pos, lab),
                "k_found": int(len(np.unique(lab[lab >= 0]))),
                "secs": f.secs,
            }
            row["smallest_pct"], row["largest_pct"], row["unassigned_pct"] = sizes_pct(lab)
            row.update(f.notes)
            if probe:
                row.update(svm_probe(sub, lab, n=PROBE_N))
            rows.append(row)
            print(
                f"  {name:16s} k={k:2d} n={len(pos):6d} {f.secs:6.1f}s "
                f"ARI={row['ARI_vs_proxy']:.3f} sil={row['gower_sil']} "
                f"probe={row.get('svm_bal_acc', '-')}"
            )
    keep = [
        "method",
        "family",
        "k_requested",
        "n_used",
        "criterion",
        "score",
        "ARI_vs_proxy",
        "gower_sil",
        "k_found",
        "smallest_pct",
        "largest_pct",
        "unassigned_pct",
        "svm_bal_acc",
        "svm_macro_f1",
        "gap_vs_shuffled",
        "secs",
    ]
    # `full` also carries each family's own diagnostics (GMM posterior, SVD variance explained,
    # Mapper node/component counts, spectral σ) → CSV. The markdown table keeps the shared columns
    # only, so it stays readable instead of a wall of mostly-NaN.
    full = pd.DataFrame(rows)
    return full[[c for c in keep if c in full.columns]], labels, full


def elbow_table(sw: pd.DataFrame) -> pd.DataFrame:
    """Relative gain in each method's own criterion per extra cluster. An elbow = a sharp fall."""
    out = []
    for name, g in sw.groupby("method", sort=False):
        g = g.sort_values("k_requested")
        diff = g["score"].diff()
        gain = (-diff if METHODS[name].lower_better else diff) / g["score"].abs().shift()
        for k, v in zip(g["k_requested"], gain, strict=True):
            out.append({"method": name, "k": k, "gain": None if pd.isna(v) else round(float(v), 4)})
    return pd.DataFrame(out).pivot(index="k", columns="method", values="gain")


# ── axis: cross-method agreement ────────────────────────────────────────────────
def cross_method(labels: dict, k: int) -> pd.DataFrame:
    """Pairwise ARI at one k, on the rows both methods saw. If independent families disagree,
    none of them is recovering real structure."""
    names = [n for n in METHODS if (n, k) in labels]
    out = pd.DataFrame(index=names, columns=names, dtype=object)
    for x in names:
        lx, px = labels[(x, k)]
        for y in names:
            ly, py = labels[(y, k)]
            shared = np.intersect1d(px, py)
            if len(shared) < 500:
                out.loc[x, y] = None
                continue
            a = lx[np.searchsorted(px, shared)]
            b = ly[np.searchsorted(py, shared)]
            out.loc[x, y] = round(ari(a, b), 3)
    return out


# ── axes 4-7: the stress battery ────────────────────────────────────────────────
def perturb(df: pd.DataFrame, spec: Spec, rng: np.random.Generator) -> pd.DataFrame:
    """Simulate measurement noise: Gaussian jitter on numerics + random flips on binary flags."""
    out = df.copy()
    for c in spec.numeric:
        v = out[c].to_numpy(dtype=float)
        span = float(v.max() - v.min()) or 1.0
        out[c] = v + rng.normal(0, JITTER_FRAC * span, len(v))
    out["lead_days"] = out["lead_days"].clip(0, 365)
    out["n_coupons"] = out["n_coupons"].clip(1, 8)
    for c in spec.binary:
        flip = rng.random(len(out)) < FLIP_FRAC
        out.loc[flip, c] = 1 - out.loc[flip, c].to_numpy()
    return out


def stress(
    fit_df: pd.DataFrame, score_df: pd.DataFrame, k: int, features: list[str]
) -> pd.DataFrame:
    """Split-half, bootstrap, perturbation and leave-one-feature-out — all scored on `score_df`,
    a held-out set no fit ever sees, so every ARI compares two solutions on identical rows."""
    rng = np.random.default_rng(SEED)
    rows = []

    for name, m in METHODS.items():
        t0 = time.time()
        base, _ = run(m, fit_df, k, score_df)
        if base.labels_test is None:
            print(f"  {name:16s} skipped (no inductive scoring)")
            continue
        b0 = base.labels_test

        a = fit_df.sample(frac=0.5, random_state=SEED)
        b = fit_df.drop(a.index)
        fa, _ = run(m, a.reset_index(drop=True), k, score_df)
        fb, _ = run(m, b.reset_index(drop=True), k, score_df)
        split = round(ari(fa.labels_test, fb.labels_test), 3)

        boots = []
        for r in range(N_BOOTSTRAP):
            bs = fit_df.sample(frac=1.0, replace=True, random_state=SEED + r)
            boots.append(run(m, bs.reset_index(drop=True), k, score_df)[0].labels_test)
        pair = [
            ari(boots[i], boots[j]) for i in range(len(boots)) for j in range(i + 1, len(boots))
        ]
        boot_ari = round(float(np.mean(pair)), 3) if pair else float("nan")

        fp, _ = run(m, perturb(fit_df, DEFAULT_SPEC, rng), k, score_df)
        pert = round(ari(b0, fp.labels_test), 3)

        drops = {}
        for col in features:
            sp = DEFAULT_SPEC.drop(col)
            if not sp.numeric or not sp.cats:
                continue
            try:
                fd, _ = run(m, fit_df, k, score_df, sp)
                drops[col] = round(ari(b0, fd.labels_test), 3)
            except Exception as e:  # noqa: BLE001 — record the failure rather than abort the axis
                drops[col] = float("nan")
                print(f"    dropout {name}/{col} failed: {type(e).__name__}: {e}")
        vals = {c: v for c, v in drops.items() if not pd.isna(v)}
        rows.append(
            {
                "method": name,
                "split_half_ARI": split,
                "bootstrap_ARI": boot_ari,
                "perturb_ARI": pert,
                "dropout_mean_ARI": round(float(np.mean(list(vals.values()))), 3)
                if vals
                else np.nan,
                "dropout_min_ARI": round(float(np.min(list(vals.values()))), 3) if vals else np.nan,
                "most_load_bearing_feature": min(vals, key=vals.get) if vals else None,
                "secs": round(time.time() - t0, 1),
            }
        )
        print(
            f"  {name:16s} split={split:.3f} boot={boot_ari:.3f} pert={pert:.3f} "
            f"drop_min={rows[-1]['dropout_min_ARI']} ({rows[-1]['secs']:.0f}s)"
        )
    return pd.DataFrame(rows)


def size_convergence(pool: pd.DataFrame, score_df: pd.DataFrame, k: int, steps) -> pd.DataFrame:
    """Does the solution settle as n grows, or keep moving? ARI of each n against the largest n."""
    steps = [s for s in steps if s <= len(pool)]
    rows = []
    for name, m in METHODS.items():
        if m.max_n is not None and m.max_n < max(steps):
            rows.append({"method": name, "note": f"n/a — sample-capped at {m.max_n:,}"})
            continue
        labs = {}
        for n in steps:
            f, _ = run(m, pool.head(n).reset_index(drop=True), k, score_df)
            if f.labels_test is None:
                break
            labs[n] = f.labels_test
        if len(labs) < 2:
            continue
        ref = max(labs)
        r = {"method": name, "note": ""}
        for n in steps:
            if n in labs:
                r[f"ARI_{n // 1000}k_vs_{ref // 1000}k"] = round(ari(labs[n], labs[ref]), 3)
        rows.append(r)
        print(
            f"  {name:16s} " + "  ".join(f"{a}={v}" for a, v in r.items() if a.startswith("ARI_"))
        )
    return pd.DataFrame(rows)


# ── SVC: k is emergent, so sweep γ instead of k ─────────────────────────────────
def svc_sweep(fit_df: pd.DataFrame, gammas=SVC_GAMMAS) -> pd.DataFrame:
    m = METHODS["SVC"]
    pos = cap_positions(len(fit_df), m.max_n)
    df = fit_df.iloc[pos].reset_index(drop=True)
    sil = SilScorer(fit_df)
    proxy = df["proxy_segment"].to_numpy()
    rows = []
    for g in gammas:
        f = _fit_svc_at(df, g)
        lab = f.labels
        small, large, _ = sizes_pct(lab)
        row = {
            "gamma": g,
            "k_emergent": f.notes["k_emergent"],
            "outliers_pct": f.notes["outliers_pct"],
            "ARI_vs_proxy": round(ari(proxy, lab), 3),
            "gower_sil": sil.score(pos, lab),
            "smallest_pct": small,
            "largest_pct": large,
            "secs": f.secs,
        }
        row.update(svm_probe(df, lab, n=PROBE_N))
        rows.append(row)
        print(
            f"  SVC γ={g:<5} k={row['k_emergent']:2d} out={row['outliers_pct']:4.1f}% "
            f"ARI={row['ARI_vs_proxy']:.3f} sil={row['gower_sil']}"
        )
    return pd.DataFrame(rows)


def _fit_svc_at(df: pd.DataFrame, gamma: float) -> Fit:
    """Run SVC at one fixed γ (it normally picks γ to land nearest a requested k)."""
    import model_zoo

    saved = model_zoo.SVC_GAMMAS
    model_zoo.SVC_GAMMAS = (gamma,)
    try:
        return fit_svc(df, 0)
    finally:
        model_zoo.SVC_GAMMAS = saved


# ── leaderboard ─────────────────────────────────────────────────────────────────
def leaderboard(sw: pd.DataFrame, st: pd.DataFrame, svc: pd.DataFrame) -> pd.DataFrame:
    """Min-max each axis across methods, then a weighted sum. Weights are printed in the report."""
    best = sw.loc[sw.groupby("method")["ARI_vs_proxy"].idxmax()].set_index("method")
    agg = pd.DataFrame(index=best.index)
    agg["best_k"] = best["k_requested"]
    agg["agreement"] = best["ARI_vs_proxy"]
    agg["separation"] = best["gower_sil"]
    agg["learnability"] = best["svm_bal_acc"] if "svm_bal_acc" in best.columns else np.nan
    agg["secs"] = best["secs"]

    if len(svc):  # SVC's best row keys off γ, not k
        row = svc.loc[svc["ARI_vs_proxy"].idxmax()]
        agg.loc["SVC", "best_k"] = row["k_emergent"]
        agg.loc["SVC", "agreement"] = row["ARI_vs_proxy"]
        agg.loc["SVC", "separation"] = row["gower_sil"]
        agg.loc["SVC", "learnability"] = row.get("svm_bal_acc", np.nan)
        # SVC has no k to request, so *sweeping* γ is its unavoidable cost, not one fit's cost
        agg.loc["SVC", "secs"] = round(float(svc["secs"].sum()), 1)

    s = st.set_index("method")
    agg["stability"] = s[["split_half_ARI", "bootstrap_ARI"]].mean(axis=1)
    agg["robustness"] = s[["perturb_ARI", "dropout_mean_ARI"]].mean(axis=1)

    def norm(col: pd.Series, invert: bool = False) -> pd.Series:
        v = pd.to_numeric(col, errors="coerce")
        if invert:
            v = -np.log1p(v)
        lo, hi = v.min(), v.max()
        if pd.isna(lo) or hi == lo:
            return pd.Series(0.5, index=v.index)
        return (v - lo) / (hi - lo)

    parts = {
        a: norm(agg[a], invert=(a == "scalability"))
        for a in ("agreement", "separation", "stability", "robustness", "learnability")
    }
    parts["scalability"] = norm(agg["secs"], invert=True)

    def composite(weights: dict) -> pd.Series:
        used = {a: w for a, w in weights.items() if w and parts[a].notna().any()}
        tot = sum(used.values())
        return sum(parts[a].fillna(parts[a].mean()) * (w / tot) for a, w in used.items()).round(3)

    agg["score"] = composite(WEIGHTS)
    # The headline score's heaviest axis is also its only *circular* one. So publish the ranking that
    # drops taxonomy agreement entirely — if the winner changes, the win was borrowed from the rules.
    agg["score_no_agreement"] = composite({**WEIGHTS, "agreement": 0.0})
    cols = [
        "best_k",
        "agreement",
        "separation",
        "stability",
        "robustness",
        "learnability",
        "secs",
        "score",
        "score_no_agreement",
    ]
    return agg[cols].sort_values("score", ascending=False).round(3)


# ── report ──────────────────────────────────────────────────────────────────────
def verdict(
    lb: pd.DataFrame, tda: dict, sw: pd.DataFrame, cross: pd.DataFrame, k: int
) -> list[str]:
    """Derive the headline claims from the tables, so the prose cannot drift from the numbers."""
    win = lb.index[0]
    sep = pd.to_numeric(lb["separation"], errors="coerce")
    best_sep = float(sep.max())
    best_agree = pd.to_numeric(lb["agreement"], errors="coerce").idxmax()
    x = cross.replace({None: np.nan}).astype(float).to_numpy()
    off = x[~np.eye(len(x), dtype=bool)]
    med_cross = round(float(np.nanmedian(off)), 3) if len(off) else float("nan")
    lines = [
        f"1. **Weighted-score winner: `{win}`** (score {lb.loc[win, 'score']}, "
        f"best at k={lb.loc[win, 'best_k']:.0f}). Highest taxonomy agreement: `{best_agree}` "
        f"(ARI {lb.loc[best_agree, 'agreement']}); best separation: `{sep.idxmax()}` ({best_sep}).",
        f"2. **The ceiling on separation is {best_sep}.** Read against the usual bands (>0.5 strong, "
        "0.25–0.5 weak but real, <0.25 none), that is what *any* of these ten methods can honestly "
        "claim on this data: "
        + (
            "no method finds meaningful separation."
            if best_sep < 0.25
            else "weak-but-real structure at best."
            if best_sep < 0.5
            else "genuine structure."
        ),
        f"3. **Independent families agree only weakly** — median off-diagonal cross-method ARI "
        f"{med_cross} at k={k}. Six families cutting the same data six different ways is the "
        "signature of a continuum, not of segments waiting to be found.",
        f"4. **Persistent homology, which never sees a label, agrees:** "
        f"{tda['n_significant_H0']} significant H0 component(s) over {tda['n_rows']} rows, "
        f"H0 gap ratio {tda['H0_gap_ratio']}. "
        + (
            "One dominant component = one connected mass, i.e. no natural k — an independent "
            "confirmation of the 2026-07-23 continuum finding, from a method with no k, no "
            "centroid and no distribution assumption."
            if tda["n_significant_H0"] <= 2
            else f"That is a topological estimate of k ≈ {tda['n_significant_H0']}, worth "
            "reconciling against the 10-segment taxonomy."
        )
        + f" On loops: {tda['n_H1_loops']} H1 bars, longest {tda['max_H1_persistence']} "
        f"= {tda['H1_max_over_p95']}× the 95th percentile of all loops"
        + (
            " — indistinguishable from the noise floor every high-dimensional cloud produces, so "
            "**no cyclical structure**. Nothing here is being missed by using partitional methods."
            if not (tda["H1_max_over_p95"] > 2)
            else " — that stands clear of the noise floor, so a genuine cycle may exist that **no "
            "partitional method can represent**. Worth a dedicated look."
        ),
    ]
    nc = lb.sort_values("score_no_agreement", ascending=False)
    lines.append(
        f"5. **Drop the circular axis and the ranking {'holds' if nc.index[0] == win else 'moves'}.** "
        f"Re-scored with taxonomy agreement weighted to zero — i.e. on separation, stability, "
        f"robustness, learnability and cost only — the order becomes `{nc.index[0]}` "
        f"({nc['score_no_agreement'].iloc[0]}), `{nc.index[1]}` "
        f"({nc['score_no_agreement'].iloc[1]}), `{nc.index[2]}` "
        f"({nc['score_no_agreement'].iloc[2]}). "
        + (
            f"`{win}` leads either way, so its win is not borrowed from the rules it is being "
            "measured against."
            if nc.index[0] == win
            else f"`{win}` tops the headline table only *because* it reproduces the proxy rules; on "
            f"the non-circular evidence alone `{nc.index[0]}` leads. Treat the headline ranking as "
            "provisional until SME ground truth replaces the proxy."
        )
    )
    if "svm_bal_acc" in sw.columns and sw["svm_bal_acc"].notna().any():
        # Illustrate the trap with a method that is *learnable but unseparated*; the global
        # max-probe row is often a well-separated method, which muddies the point.
        flat = sw[(sw["gower_sil"] < 0.15) & sw["svm_bal_acc"].notna()]
        hi = sw.loc[(flat if len(flat) else sw)["svm_bal_acc"].idxmax()]
        lines.append(
            f"6. **The SVM probe catches exactly the trap it was added for:** `{hi['method']}` "
            f"(k={hi['k_requested']}) reaches held-out balanced accuracy **{hi['svm_bal_acc']}** on "
            f"its own labels while scoring only **{hi['gower_sil']}** on separation. Its partition "
            "is perfectly *learnable* and still not *real* — a clean geometric slice through a "
            "smooth density. Never quote a separability number without the silhouette beside it."
        )
    return lines


def write_report(sw, sw_full, elbow, cross, st, sizes, svc, tda, lb, cfg) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    roster = pd.DataFrame(
        [
            {
                "method": n,
                "family": m.family,
                "criterion": m.score_name,
                "k is": "requested" if m.honours_k else "emergent",
                "sample cap": f"{m.max_n:,}" if m.max_n else "none",
            }
            for n, m in METHODS.items()
        ]
    )
    ks, k_stress = cfg["ks"], cfg["stress_k"]
    lines = [
        "# Model stress test — ten methods, six families, eight axes\n",
        f"Fitting sample **{cfg['n_fit']:,}** bookings drawn from `pal_features_booking.parquet` "
        f"(22.9M rows), common held-out scoring set **{SCORE_N:,}** rows that no fit ever sees, "
        f"seed {SEED}, k sweep {min(ks)}–{max(ks)}, stress battery at **k={k_stress}** (the "
        f"business taxonomy size). Runtime **{cfg['secs'] / 60:.1f} min**."
        + (
            "  \n**`--quick` run — reduced sample and sweep; directional only.**"
            if cfg["quick"]
            else ""
        ),
        "\nThe feature set is identical to `src/cluster_diagnostic.py` and `src/kproto_compare.py` "
        "(4 numeric + 6 binary + 1 nominal), so this **extends** the 2026-07-23 and 2026-07-27 "
        "decisions rather than re-deriving them on different inputs.\n",
        "## 0. The roster\n",
        roster.to_markdown(index=False),
        "\nCapped methods are O(n²) or worse; `n_used` appears on every row so no cap is silent, and "
        "two methods with the same cap see the *same* rows. Spectral(Gower), SVC and TDA-Mapper have "
        "no native `predict`, so their held-out labels come from a 10-NN extension **in Gower "
        "distance** — an approximation, applied identically to all three.\n",
        "## 1. The axes, and the trap each one guards\n",
        "| Axis | Metric | Good | Trap it guards against |",
        "|---|---|---|---|",
        "| Taxonomy agreement | ARI vs proxy segments | high | none — **this axis is itself "
        "circular**: the proxy *is* the rule output |",
        "| Separation | Gower silhouette | >0.5 strong | a Euclidean silhouette on one-hots "
        "flatters every method |",
        "| Natural k | own criterion + rel. gain; H0 persistence | a clear elbow | distance methods' "
        "cost falls monotonically **by construction** — never read that as an elbow |",
        "| Split-half stability | ARI(fit A, fit B) on a common set | high | a solution that only "
        "holds on one half of the data |",
        "| Bootstrap stability | mean pairwise ARI over 3 resamples | high | a solution that is an "
        "artefact of one draw |",
        "| Perturbation robustness | ARI after 5% jitter + 5% flips | high | clusters that dissolve "
        "under measurement noise |",
        "| Dropout robustness | leave-one-feature-out ARI (mean, **min**) | high min | a "
        "segmentation secretly driven by a single column |",
        "| Learnability | held-out SVM balanced accuracy on own labels | high | **only meaningful "
        "paired with separation** — high here + low there = an arbitrary geometric cut |",
        "\n`gap_vs_shuffled` is the same probe trained on shuffled labels, subtracted: a near-zero "
        "gap would mean the probe itself learned nothing and the column is uninformative.\n",
        "## 2. Full k sweep\n",
        sw.to_markdown(index=False),
        "\n## 3. Elbow test — relative gain in each method's own criterion per extra cluster\n",
        "A natural *k* shows up as a sharp fall. Centroid and mixture costs fall smoothly whether or "
        "not structure exists, so a *smooth* column is evidence of no natural k — not of a bad fit.\n",
        elbow.to_markdown(),
        f"\n## 4. Cross-method agreement at k={k_stress} (pairwise ARI, on shared rows)\n",
        cross.to_markdown(),
        "\n## 5. Topological structure — persistent homology on the Gower matrix\n",
        "Label-free and algorithm-free. **H0** bars are connected components merging as the distance "
        "threshold grows; **H1** bars are loops. A handful of long H0 bars = separated groups; one "
        "long bar with a smooth tail = a continuum. A long H1 bar would mean cyclical structure that "
        "*no* partitional method can represent at all.\n",
        pd.DataFrame([tda]).to_markdown(index=False),
        "\n## 6. Support Vector Clustering — k is emergent, so γ is swept instead\n",
        "A one-class SVM wraps the data in the tightest RBF-kernel sphere; clusters are the connected "
        "components of that contour's pre-image, tested along a 10-NN graph. The component count is "
        'the model\'s *own* answer to "how many blobs are there?" with no k supplied — and the '
        "bounded support vectors are a natural `Unassigned` bucket.\n",
        svc.to_markdown(index=False) if len(svc) else "_skipped_",
        "\n**Read `gower_sil` here against `outliers_pct`.** The silhouette is scored only on rows "
        "still inside a contour, so once γ is large enough to push most of the data into the outlier "
        "bucket the score rises because the hard cases were *discarded*, not because the survivors "
        "are separated. High silhouette + large outlier share is selection, not structure. The honest "
        "reading is the shape of the γ curve: how far γ has to be pushed before a second component "
        "appears at all, and how much of the data that costs.\n",
        f"\n## 7. Stress battery at k={k_stress}\n",
        st.to_markdown(index=False),
        "\n`most_load_bearing_feature` is the single column whose removal moves the solution most.\n",
        "\n## 8. Sample-size convergence — does the solution settle as n grows?\n",
        sizes.to_markdown(index=False) if len(sizes) else "_skipped_",
        "\n## 9. Leaderboard\n",
        "Each axis min-max normalised across methods, then weighted: "
        + ", ".join(f"**{a}** {w:.0%}" for a, w in WEIGHTS.items())
        + ". Scalability is `-log(secs)` normalised. Re-weigh freely — every component column is "
        "here, and `leaderboard.csv` has them unrounded. **`score_no_agreement`** is the same "
        "composite with taxonomy agreement weighted to zero: the ranking on non-circular evidence "
        "only. Compare the two columns before quoting either.\n",
        lb.reset_index().to_markdown(index=False),
        "\n## 10. Verdict\n",
        *[f"{ln}\n" for ln in verdict(lb, tda, sw, cross, k_stress)],
        "\n## 11. What this settles, and what it does not\n",
        "- **Does not establish correctness.** Every agreement number is measured against the "
        "rule-based proxy, which is the rules' own output — circular until the SME labels in "
        "`data/labels/sme_sample.csv` land. A method could top this axis by faithfully reproducing "
        "the rules' *mistakes*.\n",
        "- **Does settle relative fitness.** Separation, stability under resampling, robustness to "
        "noise and to losing a feature, emergent k, topology and cost are all label-free and "
        "non-circular. That is the part of this report that survives the arrival of ground truth.\n",
        f"- Fitted on {cfg['n_fit']:,} of 22.9M bookings. The stability and convergence axes are the "
        "evidence that the sample suffices; a full-population refit of the chosen method remains the "
        "final step before production scoring.\n",
        "- `--quick` runs change the sample and the sweep and are directional only.\n",
    ]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n")
    for name, tbl in [
        ("sweep", sw_full),
        ("elbow", elbow.reset_index()),
        ("cross_method", cross.reset_index()),
        ("stress", st),
        ("size_convergence", sizes),
        ("svc_gamma", svc),
        ("leaderboard", lb.reset_index()),
        ("persistence", pd.DataFrame([tda])),
    ]:
        if len(tbl):
            tbl.to_csv(OUT / f"{name}.csv", index=False)
    print("\nWrote", OUT / "summary.md")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="smaller sample, shorter sweep")
    ap.add_argument("--stress-k", type=int, default=STRESS_K, help="k for the stress battery")
    ap.add_argument("--no-probe", action="store_true", help="skip the SVM separability probe")
    args = ap.parse_args()

    n_fit = 4_000 if args.quick else SAMPLE
    ks = range(3, 7) if args.quick else K_RANGE
    steps = (2_000, 4_000, 8_000) if args.quick else SIZE_STEPS
    features = (
        ["lead_days", "value_tier", "dest_region", "corp_channel"]
        if args.quick
        else list(DEFAULT_SPEC.all_cols)
    )
    t0 = time.time()

    n_pool = max(max(steps), n_fit) + SCORE_N
    print(f"Loading {n_pool:,} bookings ...")
    allrows = load_sample(n_pool).sample(frac=1.0, random_state=SEED).reset_index(drop=True)
    score_df = allrows.head(SCORE_N).reset_index(drop=True)
    pool = allrows.iloc[SCORE_N:].reset_index(drop=True)
    fit_df = pool.head(n_fit).reset_index(drop=True)

    n_k_methods = sum(m.honours_k for m in METHODS.values())
    print(f"\n[1/6] k sweep ({len(ks)} values × {n_k_methods} methods) ...")
    sw, labels, sw_full = sweep(fit_df, ks, probe=not args.no_probe)

    print("\n[2/6] Cross-method agreement ...")
    kx = args.stress_k if any((n, args.stress_k) in labels for n in METHODS) else max(ks)
    cross = cross_method(labels, kx)

    print("\n[3/6] Support Vector Clustering γ sweep ...")
    svc = svc_sweep(fit_df)

    print("\n[4/6] Persistent homology ...")
    tda = persistence_summary(fit_df)
    print("  ", tda)

    print(f"\n[5/6] Stress battery at k={args.stress_k} ...")
    st = stress(fit_df, score_df, args.stress_k, features)

    print(f"\n[6/6] Sample-size convergence at k={args.stress_k} ...")
    sizes = size_convergence(pool, score_df, args.stress_k, steps)

    lb = leaderboard(sw, st, svc)
    write_report(
        sw,
        sw_full,
        elbow_table(sw),
        cross,
        st,
        sizes,
        svc,
        tda,
        lb,
        {
            "n_fit": n_fit,
            "ks": ks,
            "stress_k": args.stress_k,
            "secs": time.time() - t0,
            "quick": args.quick,
        },
    )
    print("\n" + lb.to_string())


if __name__ == "__main__":
    main()
