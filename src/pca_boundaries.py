"""Decision boundary visualisation + per-segment zoom grid — PAL segmentation.

Classifier: KNN-15 trained on proxy-labelled PCA-2D points (fast, smooth boundaries).

Outputs (boundary_output/):
  fig_b01_overview.png       — full PCA space + filled decision regions + boundary lines
  fig_b02_zoom_grid.png      — 10-panel per-segment zoom (bounding box of each cluster)
  fig_b03_overview_boxes.png — overview with coloured zoom rectangles annotated
  fig_b04_boundary_lines.png — boundary contour lines only (no fill) for clarity
"""

import warnings

warnings.filterwarnings("ignore")

from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap
from sklearn.decomposition import PCA
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler

from pal_colors import SEG_COLORS, SEG_ORDER

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "boundary_output"
OUTPUT.mkdir(parents=True, exist_ok=True)

BG, PANEL, BORDER = "#111827", "#1F2937", "#374151"
TEXT, SUBTEXT = "#F9FAFB", "#9CA3AF"

plt.rcParams.update(
    {
        "figure.facecolor": BG,
        "axes.facecolor": PANEL,
        "axes.edgecolor": BORDER,
        "text.color": TEXT,
        "axes.labelcolor": TEXT,
        "xtick.color": SUBTEXT,
        "ytick.color": SUBTEXT,
        "grid.color": BORDER,
        "savefig.bbox": "tight",
        "savefig.dpi": 150,
        "figure.dpi": 130,
    }
)


def save(fig, name):
    fig.savefig(OUTPUT / f"{name}.png", facecolor=BG)
    plt.close(fig)
    print(f"  saved → boundary_output/{name}.png")


# ══════════════════════════════════════════════════════════════════════════════
# 1.  LOAD, ENGINEER, PROXY-LABEL
# ══════════════════════════════════════════════════════════════════════════════
print("Loading data ...")
df = pd.read_csv(ROOT / "data" / "raw" / "sample-features.csv")
df["Average Fare"] = df["Average Fare"].str.replace("$", "", regex=False).astype(float)
df["PNRCreationDate"] = pd.to_datetime(df["PNRCreationDate"], dayfirst=True, errors="coerce")
df["Flight Date"] = pd.to_datetime(df["Flight Date"], dayfirst=True, errors="coerce")
df["lead_time"] = (df["Flight Date"] - df["PNRCreationDate"]).dt.days
df["fare_per_pax"] = df["Average Fare"] / df["PAX Count"]
df["booking_month"] = df["PNRCreationDate"].dt.month
df = df.dropna(subset=["lead_time"]).reset_index(drop=True).copy()

cabin_map = {"Y": 0, "W": 1, "J": 2}
df["cabin_ord"] = df["Cabin"].map(cabin_map).fillna(0)
df["is_dom"] = (df["Entity"] == "DOM").astype(int)

cat_cols = ["Region", "Farebrand", "Itinerary Type", "Ticketing Channel"]
df_enc = pd.get_dummies(df[cat_cols].fillna("Unknown"), columns=cat_cols, prefix_sep="=", dtype=int)
num_cols = [
    "lead_time",
    "Average Fare",
    "fare_per_pax",
    "PAX Count",
    "cabin_ord",
    "is_dom",
    "booking_month",
]

X_raw = pd.concat([df[num_cols].reset_index(drop=True), df_enc.reset_index(drop=True)], axis=1)
scaler = StandardScaler()
X = scaler.fit_transform(X_raw)


# Proxy waterfall labels
def assign_segment(df):
    seg = pd.Series("Unassigned", index=df.index)
    seg[df["Farebrand"].isin(["Economy Supersaver", "Economy Saver"])] = "Budget/Adventure"
    nomad = (
        (df["PAX Count"] == 1)
        & (df["Region"] == "ASEAN")
        & (df["Ticketing Channel"] == "WEB/APP")
        & (df["Farebrand"].isin(["Economy Flex", "Economy Value"]))
    )
    seg[nomad] = "Digital Nomad"
    seg[df["lead_time"] <= 3] = "Last-Minute"
    seg[df["PAX Count"].between(3, 5)] = "Family"
    seg[(df["PAX Count"] >= 4) & (df["Ticketing Channel"] == "Traditional Travel Agency")] = (
        "Pilgrimage"
    )
    seg[df["Itinerary Type"] == "Beyonds (INT - DOM)"] = "Balikbayan/VFR"
    seg[(df["Region"] == "Middle East") | (df["Ticketing Channel"] == "Sea Crew")] = "OFW/Migrant"
    seg[df["Cabin"] == "W"] = "Premium Bleisure"
    seg[df["Cabin"] == "J"] = "Corporate"
    return seg


df["segment"] = assign_segment(df)

# ══════════════════════════════════════════════════════════════════════════════
# 2.  PCA  →  2-D
# ══════════════════════════════════════════════════════════════════════════════
pca2 = PCA(n_components=2, random_state=42)
X_pca = pca2.fit_transform(X)
var_exp = pca2.explained_variance_ratio_ * 100
df["pc1"] = X_pca[:, 0]
df["pc2"] = X_pca[:, 1]

# Labelled subset only for classifier training
labeled = df[df["segment"] != "Unassigned"].copy()
le = LabelEncoder()
seg_order = [s for s in SEG_ORDER if s in labeled["segment"].unique()]
le.fit(seg_order)
y_labeled = le.transform(labeled["segment"])
X_pca_lab = X_pca[labeled.index]

print(f"Labeled: {len(labeled):,}  |  Classes: {list(le.classes_)}")

# ══════════════════════════════════════════════════════════════════════════════
# 3.  TRAIN 2-D KNN CLASSIFIER
# ══════════════════════════════════════════════════════════════════════════════
print("Training KNN-15 on PCA-2D space ...")
knn = KNeighborsClassifier(n_neighbors=15, weights="distance", n_jobs=-1)
knn.fit(X_pca_lab, y_labeled)

# ── mesh grid ──────────────────────────────────────────────────────────────────
PAD = 0.8  # padding around data extent
STEP = 0.04  # mesh resolution — finer = sharper lines (slower)
x1_min = X_pca[:, 0].min() - PAD
x1_max = X_pca[:, 0].max() + PAD
x2_min = X_pca[:, 1].min() - PAD
x2_max = X_pca[:, 1].max() + PAD
xx, yy = np.meshgrid(np.arange(x1_min, x1_max, STEP), np.arange(x2_min, x2_max, STEP))
Z_num = knn.predict(np.c_[xx.ravel(), yy.ravel()]).reshape(xx.shape)
# Z_num contains integer class indices — map to level numbers for contourf
levels = np.arange(-0.5, len(le.classes_) + 0.5, 1)

# colour maps
seg_hex = [SEG_COLORS[c] for c in le.classes_]
cmap_fill = ListedColormap(seg_hex)
cmap_line = ListedColormap(seg_hex)


def _scatter_all(ax, alpha_lab=0.55, alpha_unlab=0.15, s_lab=12, s_unlab=6):
    """Plot labelled + unlabelled points on ax using canonical palette."""
    # unlabelled (grey, behind)
    unlab = df[df["segment"] == "Unassigned"]
    ax.scatter(
        unlab["pc1"],
        unlab["pc2"],
        c=SEG_COLORS["Unassigned"],
        s=s_unlab,
        alpha=alpha_unlab,
        zorder=2,
    )
    # labelled
    for seg in seg_order:
        sub = labeled[labeled["segment"] == seg]
        ax.scatter(
            sub["pc1"],
            sub["pc2"],
            c=SEG_COLORS[seg],
            s=s_lab,
            alpha=alpha_lab,
            zorder=3,
            label=f"{seg} ({len(sub):,})",
        )


def _legend(ax, ncol=2, fontsize=7.5):
    patches = [mpatches.Patch(color=SEG_COLORS[s], label=s) for s in seg_order]
    ax.legend(
        handles=patches,
        fontsize=fontsize,
        ncol=ncol,
        framealpha=0.35,
        facecolor=PANEL,
        edgecolor=BORDER,
        loc="upper right",
    )


def _axis_labels(ax):
    ax.set_xlabel(f"PC1  ({var_exp[0]:.1f}% variance)", fontsize=8)
    ax.set_ylabel(f"PC2  ({var_exp[1]:.1f}% variance)", fontsize=8)


# ══════════════════════════════════════════════════════════════════════════════
# FIG B01 — Full overview with filled decision regions + boundary lines
# ══════════════════════════════════════════════════════════════════════════════
print("Generating fig_b01_overview ...")
fig, ax = plt.subplots(figsize=(15, 10), facecolor=BG)

# filled decision regions (light fill)
cf = ax.contourf(xx, yy, Z_num, levels=levels, cmap=cmap_fill, alpha=0.22, zorder=1)

# boundary lines (solid, slightly thicker)
cl = ax.contour(xx, yy, Z_num, levels=levels, colors="white", linewidths=0.9, alpha=0.55, zorder=2)

_scatter_all(ax)
_legend(ax, ncol=2)
_axis_labels(ax)
ax.set_title(
    "PCA-2D  ·  Decision Boundaries  ·  KNN-15 classifier on proxy labels\n"
    "Filled regions = predicted territory  ·  White lines = boundary edges",
    fontsize=11,
    color=TEXT,
    fontweight="bold",
)
ax.set_xlim(x1_min, x1_max)
ax.set_ylim(x2_min, x2_max)
fig.tight_layout()
save(fig, "fig_b01_overview")

# ══════════════════════════════════════════════════════════════════════════════
# FIG B04 — Boundary lines only (no fill, cleaner read)
# ══════════════════════════════════════════════════════════════════════════════
print("Generating fig_b04_boundary_lines ...")
fig, ax = plt.subplots(figsize=(15, 10), facecolor=BG)

cl = ax.contour(
    xx,
    yy,
    Z_num,
    levels=levels,
    colors=[SEG_COLORS[c] for c in le.classes_],
    linewidths=1.4,
    alpha=0.85,
    zorder=2,
)

_scatter_all(ax, alpha_lab=0.60, alpha_unlab=0.12)
_legend(ax, ncol=2)
_axis_labels(ax)
ax.set_title(
    "PCA-2D  ·  Decision Boundary Lines Only  ·  KNN-15\n"
    "Lines coloured by the segment whose territory begins there",
    fontsize=11,
    color=TEXT,
    fontweight="bold",
)
ax.set_xlim(x1_min, x1_max)
ax.set_ylim(x2_min, x2_max)
fig.tight_layout()
save(fig, "fig_b04_boundary_lines")

# ══════════════════════════════════════════════════════════════════════════════
# FIG B02 — Per-segment zoom grid
# ══════════════════════════════════════════════════════════════════════════════
print("Generating fig_b02_zoom_grid ...")

ZOOM_PAD = 0.55  # padding around each cluster's bounding box (PCA units)
ZOOM_STEP = 0.025  # finer mesh inside zoom panels

n_segs = len(seg_order)
ncols = 5
nrows = (n_segs + ncols - 1) // ncols  # ceil

fig, axes = plt.subplots(nrows, ncols, figsize=(ncols * 5, nrows * 4.2), facecolor=BG)
fig.suptitle(
    "Per-Segment Zoom  ·  Decision Boundaries  ·  KNN-15 (PCA-2D)",
    fontsize=14,
    color=TEXT,
    fontweight="bold",
    y=1.01,
)

axes_flat = axes.flat

for _i, seg in enumerate(seg_order):
    ax = next(axes_flat)
    ax.set_facecolor(PANEL)

    sub = labeled[labeled["segment"] == seg]

    # bounding box with padding
    if len(sub) == 0:
        ax.set_visible(False)
        continue

    zx1 = sub["pc1"].quantile(0.02) - ZOOM_PAD
    zx2 = sub["pc1"].quantile(0.98) + ZOOM_PAD
    zy1 = sub["pc2"].quantile(0.02) - ZOOM_PAD
    zy2 = sub["pc2"].quantile(0.98) + ZOOM_PAD

    # clamp to global extent
    zx1 = max(zx1, x1_min)
    zx2 = min(zx2, x1_max)
    zy1 = max(zy1, x2_min)
    zy2 = min(zy2, x2_max)

    # fine mesh for this window
    xx_z, yy_z = np.meshgrid(np.arange(zx1, zx2, ZOOM_STEP), np.arange(zy1, zy2, ZOOM_STEP))
    if xx_z.size == 0 or yy_z.size == 0:
        ax.set_visible(False)
        continue
    Z_z = knn.predict(np.c_[xx_z.ravel(), yy_z.ravel()]).reshape(xx_z.shape)

    # filled decision region
    ax.contourf(xx_z, yy_z, Z_z, levels=levels, cmap=cmap_fill, alpha=0.25, zorder=1)

    # boundary lines — thicker inside zoom panels
    ax.contour(xx_z, yy_z, Z_z, levels=levels, colors="white", linewidths=1.1, alpha=0.70, zorder=2)

    # all other segment points in window (faint grey)
    others = labeled[
        (labeled["segment"] != seg)
        & (labeled["pc1"].between(zx1, zx2))
        & (labeled["pc2"].between(zy1, zy2))
    ]
    ax.scatter(others["pc1"], others["pc2"], c="#374151", s=8, alpha=0.35, zorder=3)

    # unassigned in window
    unlab_win = df[
        (df["segment"] == "Unassigned")
        & (df["pc1"].between(zx1, zx2))
        & (df["pc2"].between(zy1, zy2))
    ]
    ax.scatter(unlab_win["pc1"], unlab_win["pc2"], c="#4B5563", s=6, alpha=0.25, zorder=3)

    # focal segment (bright, on top)
    ax.scatter(
        sub["pc1"],
        sub["pc2"],
        c=SEG_COLORS[seg],
        s=18,
        alpha=0.75,
        edgecolors="white",
        linewidths=0.3,
        zorder=5,
    )

    # centroid cross-hair
    cx, cy = sub["pc1"].mean(), sub["pc2"].mean()
    ax.plot(cx, cy, marker="+", color="white", ms=14, mew=1.8, zorder=6)

    ax.set_xlim(zx1, zx2)
    ax.set_ylim(zy1, zy2)

    # coloured border for the focal segment
    for spine in ax.spines.values():
        spine.set_edgecolor(SEG_COLORS[seg])
        spine.set_linewidth(2.2)

    ax.set_title(
        f"{seg}\n(n={len(sub):,})", fontsize=9, color=SEG_COLORS[seg], fontweight="bold", pad=6
    )
    ax.set_xlabel("PC1", fontsize=7)
    ax.set_ylabel("PC2", fontsize=7)
    ax.tick_params(labelsize=6.5)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(4))
    ax.yaxis.set_major_locator(ticker.MaxNLocator(4))

# hide any leftover empty axes
for ax in axes_flat:
    ax.set_visible(False)

fig.tight_layout()
save(fig, "fig_b02_zoom_grid")

# ══════════════════════════════════════════════════════════════════════════════
# FIG B03 — Overview annotated with coloured zoom rectangles
# ══════════════════════════════════════════════════════════════════════════════
print("Generating fig_b03_overview_boxes ...")
fig, ax = plt.subplots(figsize=(16, 10), facecolor=BG)

ax.contourf(xx, yy, Z_num, levels=levels, cmap=cmap_fill, alpha=0.18, zorder=1)
ax.contour(xx, yy, Z_num, levels=levels, colors="white", linewidths=0.7, alpha=0.45, zorder=2)
_scatter_all(ax, alpha_lab=0.45, alpha_unlab=0.10, s_lab=8)

for seg in seg_order:
    sub = labeled[labeled["segment"] == seg]
    if len(sub) == 0:
        continue

    zx1 = sub["pc1"].quantile(0.02) - ZOOM_PAD
    zx2 = sub["pc1"].quantile(0.98) + ZOOM_PAD
    zy1 = sub["pc2"].quantile(0.02) - ZOOM_PAD
    zy2 = sub["pc2"].quantile(0.98) + ZOOM_PAD
    zx1 = max(zx1, x1_min)
    zx2 = min(zx2, x1_max)
    zy1 = max(zy1, x2_min)
    zy2 = min(zy2, x2_max)

    rect = mpatches.FancyBboxPatch(
        (zx1, zy1),
        zx2 - zx1,
        zy2 - zy1,
        boxstyle="round,pad=0.05",
        linewidth=1.8,
        edgecolor=SEG_COLORS[seg],
        facecolor="none",
        zorder=6,
        alpha=0.9,
    )
    ax.add_patch(rect)

    # label near top-right corner of box
    ax.text(
        zx2,
        zy2 + 0.05,
        seg,
        fontsize=6.5,
        color=SEG_COLORS[seg],
        fontweight="bold",
        ha="right",
        va="bottom",
        zorder=7,
        bbox=dict(fc=BG, ec="none", alpha=0.6, pad=1),
    )

_legend(ax, ncol=2)
_axis_labels(ax)
ax.set_title(
    "PCA-2D  ·  Zoom Regions per Segment  (coloured rectangles)\n"
    "Each box shows the 2–98 percentile boundary of that segment's cluster",
    fontsize=11,
    color=TEXT,
    fontweight="bold",
)
ax.set_xlim(x1_min, x1_max)
ax.set_ylim(x2_min, x2_max)
fig.tight_layout()
save(fig, "fig_b03_overview_boxes")

print("\nDone — all 4 charts saved to boundary_output/")
