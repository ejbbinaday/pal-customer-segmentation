"""Manuscript Chapter-4 figures — rendered from SAVED stage outputs only (no refits).

Fills the figure placeholders in `docs/manuscript-ch4-draft.md` that no existing PNG covers:

  ms_fig1_separation_ceiling.png   Gower silhouette by method x k (the 0.381 ceiling)
  ms_fig2_cross_method_ari.png     pairwise ARI between methods at k=10
  ms_fig4_construct_auc.png        segment-distinguishability AUC matrix (strict anchors)
  ms_fig5_detection_floor.png      detection-power consensus grid (n of 12 combos)
  ms_fig6_temporal_stability.png   booking vs revenue share, earlier vs later window

(Figures 3 and 7 of the draft are covered by `eda_01_segments.png` / `sub_01_subtypes.png`
from `report_figures.py`.) Inputs: `outputs/model_stress_test/`, `outputs/validate_construct/`,
`outputs/detection_power/`, `outputs/validate_temporal/`. Writes PNGs to
`outputs/report_real/figs/`.

Run:  python src/manuscript_figures.py
"""

from pathlib import Path

import matplotlib as mpl
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

from pal_colors import SEG_COLORS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
FIGS = OUT / "report_real" / "figs"

# ---- report palette (matches report_figures.py / docs/status-report styling) ----
INK = "#14213A"
INK_SOFT = "#4A5468"
INK_FAINT = "#7A8298"
SKY = "#12608F"
SIGNAL = "#B45309"
TEAL = "#0D9488"  # third categorical slot; trio validated CVD-safe on light surface
RULE = "#D8D8CF"
PAPER = "#FFFFFF"

# single-hue sequential ramp for heatmaps (light -> dark, lightness monotone)
BLUES = LinearSegmentedColormap.from_list("pal_blues", ["#F4F8FB", "#CBDDEA", SKY, "#092F47"])

mpl.rcParams.update(
    {
        "figure.facecolor": PAPER,
        "axes.facecolor": PAPER,
        "savefig.facecolor": PAPER,
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.edgecolor": RULE,
        "axes.linewidth": 1.0,
        "axes.grid": True,
        "grid.color": "#EDEDE6",
        "grid.linewidth": 0.8,
        "axes.titlecolor": INK,
        "axes.labelcolor": INK_SOFT,
        "text.color": INK,
        "xtick.color": INK_SOFT,
        "ytick.color": INK_SOFT,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 200,
    }
)


def save(fig, name: str) -> None:
    fig.tight_layout()
    path = FIGS / name
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print("  wrote", path.name)


def annotated_heatmap(ax, mat, labels_x, labels_y, vmin, vmax, fmt="{:.2f}"):
    """Sequential heatmap with per-cell values; diagonal/NaN cells drawn neutral."""
    shown = np.ma.masked_invalid(mat)
    ax.imshow(shown, cmap=BLUES, vmin=vmin, vmax=vmax, aspect="auto")
    ax.set_xticks(range(len(labels_x)))
    ax.set_xticklabels(labels_x, rotation=40, ha="right", fontsize=8.5)
    ax.set_yticks(range(len(labels_y)))
    ax.set_yticklabels(labels_y, fontsize=8.5)
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    mid = vmin + 0.55 * (vmax - vmin)
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat[i, j]
            if np.isnan(v):
                ax.text(j, i, "—", ha="center", va="center", fontsize=8, color=INK_FAINT)
            else:
                ax.text(
                    j,
                    i,
                    fmt.format(v),
                    ha="center",
                    va="center",
                    fontsize=8,
                    color=PAPER if v > mid else INK,
                )


# ------------------------------------------------------------------ Fig 1: separation ceiling
def fig1_separation_ceiling() -> None:
    df = pd.read_csv(OUT / "model_stress_test" / "sweep.csv")
    highlight = {"Spectral(Gower)": SKY, "GMM(full)": SIGNAL, "LCA": TEAL}

    fig, ax = plt.subplots(figsize=(9, 5.4))
    ax.axhspan(0.5, 1.0, color="#F1F4EE", zorder=0)
    ax.axhspan(0.25, 0.5, color="#FAF7EF", zorder=0)
    for y, txt in [(0.52, "strong structure (>0.5)"), (0.44, "weak but real (0.25-0.5)")]:
        ax.text(12.35, y, txt, fontsize=8.5, color=INK_FAINT, va="center")
    ax.axhline(0.25, color=RULE, linewidth=1)
    ax.axhline(0.5, color=RULE, linewidth=1)

    for method, g in df.groupby("method"):
        g = g.sort_values("k_requested")
        if method in highlight:
            c = highlight[method]
            ax.plot(g["k_requested"], g["gower_sil"], color=c, linewidth=2, zorder=3)
            last = g.iloc[-1]
            ax.text(
                12.15,
                last["gower_sil"],
                method,
                color=c,
                fontsize=9.5,
                fontweight="bold",
                va="center",
            )
        else:
            ax.plot(g["k_requested"], g["gower_sil"], color=INK_FAINT, linewidth=1, alpha=0.45)

    best = df.loc[df["gower_sil"].idxmax()]
    ax.scatter(best["k_requested"], best["gower_sil"], color=SKY, s=48, zorder=4)
    ax.annotate(
        f"ceiling: {best['gower_sil']:.3f}\n({best['method']}, k={int(best['k_requested'])})",
        (best["k_requested"], best["gower_sil"]),
        xytext=(3.6, 0.56),
        fontsize=9,
        color=INK,
        arrowprops={"arrowstyle": "-", "color": INK_FAINT, "linewidth": 0.8},
    )
    ax.set_xlim(2.7, 14.6)
    ax.set_ylim(-0.12, 0.68)
    ax.set_xticks(range(3, 13))
    ax.set_xlabel("k requested")
    ax.set_ylabel("Gower silhouette (held-out sample)")
    ax.set_title(
        "Separation never reaches the strong band — ten methods, k = 3–12",
        fontweight="bold",
        loc="left",
    )
    ax.text(
        0,
        -0.14,
        "Unlabelled grey lines: the other seven methods. Source: outputs/model_stress_test/sweep.csv",
        transform=ax.transAxes,
        fontsize=8,
        color=INK_FAINT,
        va="top",
    )
    save(fig, "ms_fig1_separation_ceiling.png")


# ------------------------------------------------------------- Fig 2: cross-method agreement
def fig2_cross_method_ari() -> None:
    df = pd.read_csv(OUT / "model_stress_test" / "cross_method.csv", index_col=0)
    order = [  # grouped by family: mixtures, centroid, spectral, topological
        "LCA",
        "GMM(full)",
        "GMM(diag)",
        "k-prototypes",
        "k-modes",
        "KMeans",
        "SVD+KMeans",
        "Spectral(Gower)",
        "TDA-Mapper",
    ]
    mat = df.loc[order, order].to_numpy(dtype=float)
    np.fill_diagonal(mat, np.nan)
    off = mat[~np.isnan(mat)]

    fig, ax = plt.subplots(figsize=(7.6, 6.4))
    annotated_heatmap(ax, mat, order, order, vmin=0, vmax=1)
    ax.set_title(
        f"Methods agree only weakly on where the boundaries are\n"
        f"pairwise ARI at k = 10 · median off-diagonal {np.median(off):.2f}",
        fontweight="bold",
        loc="left",
    )
    fig.text(
        0.01,
        -0.02,
        "ARI 1.0 = identical partitions, 0 = chance. High agreement appears only within "
        "algorithmic families.\nSource: outputs/model_stress_test/cross_method.csv",
        fontsize=8,
        color=INK_FAINT,
        va="top",
    )
    save(fig, "ms_fig2_cross_method_ari.png")


# ------------------------------------------------------- Fig 4: construct-validity AUC matrix
def fig4_construct_auc() -> None:
    pairs = pd.read_csv(OUT / "validate_construct" / "pairs.csv")
    segs = [  # order follows outputs/validate_construct/summary.md §2
        "Family",
        "Premium Bleisure",
        "Balikbayan/VFR",
        "Pilgrimage",
        "Last-Minute",
        "Budget/Adventure",
        "OFW/Migrant",
        "Corporate",
        "Mabuhay Loyalist",
    ]
    idx = {s: i for i, s in enumerate(segs)}
    mat = np.full((len(segs), len(segs)), np.nan)
    for _, r in pairs.iterrows():
        i, j = idx[r["segment_a"]], idx[r["segment_b"]]
        mat[i, j] = mat[j, i] = r["auc_strict"]

    fig, ax = plt.subplots(figsize=(7.8, 6.6))
    annotated_heatmap(ax, mat, segs, segs, vmin=0.5, vmax=1.0)
    weakest = pairs.loc[pairs["auc_strict"].idxmin()]
    i, j = idx[weakest["segment_a"]], idx[weakest["segment_b"]]
    for a, b in [(i, j), (j, i)]:
        ax.add_patch(
            plt.Rectangle((b - 0.5, a - 0.5), 1, 1, fill=False, edgecolor=SIGNAL, linewidth=2)
        )
    ax.set_title(
        "Segments are distinguishable on evidence the rules never saw\n"
        "held-out AUC, strict anchors (age, age-known, departure month, booking count)",
        fontweight="bold",
        loc="left",
    )
    fig.text(
        0.01,
        -0.02,
        "Bands: <0.60 not distinguishable · 0.60-0.75 weakly · >0.75 clearly distinct. "
        f"Outlined: weakest boundary ({weakest['segment_a']} vs {weakest['segment_b']}, "
        f"{weakest['auc_strict']:.3f}).\n"
        "Negative control 0.494-0.506 (pass). Source: outputs/validate_construct/pairs.csv",
        fontsize=8,
        color=INK_FAINT,
        va="top",
    )
    save(fig, "ms_fig4_construct_auc.png")


# ------------------------------------------------------------- Fig 5: detection consensus grid
def fig5_detection_floor() -> None:
    grid = pd.read_csv(OUT / "detection_power" / "grid.csv")
    thr = pd.read_csv(OUT / "detection_power" / "thresholds.csv")
    tmap = dict(zip(thr["method"], thr["threshold"], strict=True))
    grid["detected"] = grid.apply(lambda r: r["best_f1"] >= tmap[r["method"]], axis=1)

    counts = (
        grid.groupby(["prevalence_pct", "w"])["detected"]
        .sum()
        .unstack("w")
        .sort_index(ascending=True)
    )
    prevs, ws = list(counts.index), list(counts.columns)
    mat = counts.to_numpy(dtype=float)
    n_combos = int(grid.groupby(["prevalence_pct", "w"]).size().iloc[0])
    majority = n_combos // 2 + 1

    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    annotated_heatmap(
        ax,
        mat,
        [f"{w:g}" for w in ws],
        [f"{p:.1f}%" for p in prevs],
        vmin=0,
        vmax=n_combos,
        fmt="{:.0f}",
    )
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            if mat[i, j] >= majority:
                ax.add_patch(
                    plt.Rectangle(
                        (j - 0.5, i - 0.5), 1, 1, fill=False, edgecolor=SIGNAL, linewidth=2
                    )
                )
    ax.set_xlabel("Planted distinctness w (0 = unmodified, 1 = archetype)")
    ax.set_ylabel("Planted prevalence")
    ax.set_title(
        f"Where a planted segment is recovered — combinations detecting, of {n_combos}\n"
        f"outlined = majority of the panel (>= {majority}); below ~1% prevalence: never",
        fontweight="bold",
        loc="left",
    )
    ax.text(
        0,
        -0.22,
        "Detection = best F1 >= max(0.5, method's w=0 control p95), pre-registered. "
        "4 methods x 3 archetypes per cell.\nSource: outputs/detection_power/grid.csv, "
        "thresholds.csv",
        transform=ax.transAxes,
        fontsize=8,
        color=INK_FAINT,
        va="top",
    )
    save(fig, "ms_fig5_detection_floor.png")


# ------------------------------------------------------ Fig 6: out-of-time share stability
def fig6_temporal_stability() -> None:
    df = pd.read_csv(OUT / "validate_temporal" / "shares.csv")
    df = df.sort_values("share_earlier_pct", ascending=True).reset_index(drop=True)

    fig, axes = plt.subplots(1, 2, figsize=(11, 5.6), sharey=True)
    panels = [
        ("share_earlier_pct", "share_later_pct", "Share of bookings (%)", "TVD 1.93 pp"),
        ("rev_share_earlier_pct", "rev_share_later_pct", "Share of revenue (%)", "TVD 3.21 pp"),
    ]
    y = np.arange(len(df))
    for ax, (c_early, c_late, xlabel, tvd) in zip(axes, panels, strict=True):
        for yi, r in df.iterrows():
            color = SEG_COLORS.get(r["proxy_segment"], "#888")
            e, late = r[c_early], r[c_late]
            ax.plot([e, late], [yi, yi], color=color, linewidth=1.6, zorder=2)
            ax.scatter([e], [yi], s=34, facecolor=PAPER, edgecolor=color, linewidth=1.6, zorder=3)
            ax.scatter([late], [yi], s=34, color=color, zorder=3)
            delta = late - e
            if abs(delta) >= 1:
                ax.text(
                    max(e, late) + 0.7,
                    yi,
                    f"{delta:+.1f} pp",
                    va="center",
                    fontsize=8.5,
                    color=SIGNAL if delta < 0 else INK_SOFT,
                )
        ax.set_yticks(y)
        ax.set_yticklabels(df["proxy_segment"], fontsize=9)
        ax.set_xlabel(xlabel)
        ax.set_xlim(0, max(df[c_early].max(), df[c_late].max()) * 1.22)
        ax.set_title(tvd, loc="right", fontsize=9.5, color=INK_FAINT)
    axes[0].scatter([], [], facecolor=PAPER, edgecolor=INK_SOFT, s=34, label="2024-05 → 2025-04")
    axes[0].scatter([], [], color=INK_SOFT, s=34, label="2025-05 → 2026-04")
    axes[0].legend(loc="lower right", fontsize=8.5, frameon=False)
    fig.suptitle(
        "Segment sizes hold across a twelve-month step; revenue mix moves more than headcount",
        fontsize=12.5,
        fontweight="bold",
        color=INK,
        x=0.01,
        ha="left",
    )
    fig.text(
        0.01,
        -0.015,
        "Full-population counts (9.77M vs 10.08M bookings), issuance windows chosen inside the "
        "censoring-free region. Deltas annotated where >= 1 pp.\n"
        "Source: outputs/validate_temporal/shares.csv",
        fontsize=8,
        color=INK_FAINT,
    )
    save(fig, "ms_fig6_temporal_stability.png")


def main() -> None:
    FIGS.mkdir(parents=True, exist_ok=True)
    fig1_separation_ceiling()
    fig2_cross_method_ari()
    fig4_construct_auc()
    fig5_detection_floor()
    fig6_temporal_stability()


if __name__ == "__main__":
    main()
