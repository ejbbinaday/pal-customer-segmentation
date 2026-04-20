"""Clustering algorithm comparison — PAL customer segmentation.

Algorithms:
  1. KMeans            — convex, Euclidean distance (baseline)
  2. MiniBatchKMeans   — scalable KMeans variant
  3. GMM               — soft probabilistic, elliptical boundaries
  4. Agglomerative     — Ward linkage, hierarchical (subsampled for speed)
  5. DBSCAN            — density-based, arbitrary shape, finds noise
  6. HDBSCAN           — hierarchical density, handles varying density
  7. Birch             — scalable tree-based, CF-tree structure

Internal validity metrics:
  • Silhouette Score       (↑ better, -1 to 1)
  • Davies-Bouldin Index   (↓ better, ≥ 0)
  • Calinski-Harabasz      (↑ better)
  • Cluster count          (target ≈ 10)
  • Noise %                (↓ better — DBSCAN/HDBSCAN only)
  • Size std dev           (↓ better — balanced cluster sizes)

Outputs (cluster_compare_output/):
  fig_k01_metrics_radar.png         — multi-metric spider chart
  fig_k02_silhouette_bars.png       — silhouette by algorithm
  fig_k03_db_ch_bars.png            — Davies-Bouldin + Calinski-Harabasz
  fig_k04_pca_grid.png              — PCA-2D scatter, one panel per algorithm
  fig_k05_cluster_sizes.png         — cluster size distribution per algorithm
  fig_k06_leaderboard.png           — ranked table heatmap
  fig_k07_winner_centroid.png       — centroid heatmap of the winner
"""

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from pathlib import Path
from math import pi

from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import (KMeans, MiniBatchKMeans, AgglomerativeClustering,
                             DBSCAN, Birch, HDBSCAN)
from sklearn.mixture import GaussianMixture
from sklearn.metrics import (silhouette_score, davies_bouldin_score,
                             calinski_harabasz_score)

OUTPUT = Path("cluster_compare_output")
OUTPUT.mkdir(exist_ok=True)

# ── theme ──────────────────────────────────────────────────────────────────────
BG, PANEL, BORDER = "#111827", "#1F2937", "#374151"
TEXT, SUBTEXT     = "#F9FAFB", "#9CA3AF"

ALGO_COLORS = {
    "KMeans":         "#3B82F6",
    "MiniBatchKMeans":"#60A5FA",
    "GMM":            "#8B5CF6",
    "Agglomerative":  "#10B981",
    "DBSCAN":         "#EF4444",
    "HDBSCAN":        "#F97316",
    "Birch":          "#F59E0B",
}
ALGO_LIST = list(ALGO_COLORS.keys())

sns.set_theme(style="darkgrid", font_scale=0.9)
plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": PANEL,
    "axes.edgecolor": BORDER, "text.color": TEXT,
    "axes.labelcolor": TEXT, "xtick.color": SUBTEXT,
    "ytick.color": SUBTEXT, "grid.color": BORDER,
    "savefig.bbox": "tight", "savefig.dpi": 150, "figure.dpi": 130,
})

def save(fig, name):
    fig.savefig(OUTPUT / f"{name}.png", facecolor=BG)
    plt.close(fig)
    print(f"  saved → cluster_compare_output/{name}.png")

# ══════════════════════════════════════════════════════════════════════════════
# 1. LOAD & FEATURE ENGINEERING
# ══════════════════════════════════════════════════════════════════════════════
print("Loading data ...")
df = pd.read_csv("sample-features.csv")
df["Average Fare"]    = df["Average Fare"].str.replace("$", "", regex=False).astype(float)
df["PNRCreationDate"] = pd.to_datetime(df["PNRCreationDate"], dayfirst=True, errors="coerce")
df["Flight Date"]     = pd.to_datetime(df["Flight Date"],     dayfirst=True, errors="coerce")
df["lead_time"]       = (df["Flight Date"] - df["PNRCreationDate"]).dt.days
df["fare_per_pax"]    = df["Average Fare"] / df["PAX Count"]
df["booking_month"]   = df["PNRCreationDate"].dt.month
df = df.dropna(subset=["lead_time"]).copy()

cabin_map = {"Y": 0, "W": 1, "J": 2}
df["cabin_ord"] = df["Cabin"].map(cabin_map).fillna(0)
df["is_dom"]    = (df["Entity"] == "DOM").astype(int)

cat_cols = ["Region", "Farebrand", "Itinerary Type", "Ticketing Channel"]
df_enc   = pd.get_dummies(df[cat_cols].fillna("Unknown"),
                          columns=cat_cols, prefix_sep="=", dtype=int)
num_cols = ["lead_time", "Average Fare", "fare_per_pax", "PAX Count",
            "cabin_ord", "is_dom", "booking_month"]

X_raw  = pd.concat([df[num_cols].reset_index(drop=True),
                    df_enc.reset_index(drop=True)], axis=1)
feature_names = X_raw.columns.tolist()

scaler = StandardScaler()
X      = scaler.fit_transform(X_raw)
print(f"Feature matrix: {X.shape}")

# PCA for visualization (fit once, shared across all plots)
pca2 = PCA(n_components=2, random_state=42)
X_pca = pca2.fit_transform(X)
var_exp = pca2.explained_variance_ratio_ * 100

# subsample indices for silhouette (expensive) and agglomerative
RNG       = np.random.default_rng(42)
sil_idx   = RNG.choice(len(X), size=min(8000, len(X)), replace=False)
agg_idx   = RNG.choice(len(X), size=min(6000, len(X)), replace=False)  # agglom subsample
plot_idx  = RNG.choice(len(X), size=min(5000, len(X)), replace=False)

K = 10  # target segment count

# ══════════════════════════════════════════════════════════════════════════════
# 2. RUN ALGORITHMS
# ══════════════════════════════════════════════════════════════════════════════
results = {}   # algo → {labels, metrics, ...}

def compute_metrics(X_full, labels, name, sil_sample=sil_idx):
    """Compute internal validity metrics, handle noise labels (-1)."""
    labels = np.array(labels)
    noise_mask = labels == -1
    noise_pct  = noise_mask.mean() * 100
    unique_k   = len(set(labels[~noise_mask]))

    # Metrics only on non-noise points (need ≥ 2 clusters)
    valid_mask = ~noise_mask
    if unique_k >= 2 and valid_mask.sum() > unique_k:
        # Use sample indices intersected with valid points
        samp = sil_sample[valid_mask[sil_sample]]
        sil  = silhouette_score(X_full[samp], labels[samp]) if len(samp) > unique_k else np.nan
        db   = davies_bouldin_score(X_full[valid_mask], labels[valid_mask])
        ch   = calinski_harabasz_score(X_full[valid_mask], labels[valid_mask])
    else:
        sil, db, ch = np.nan, np.nan, np.nan

    sizes    = pd.Series(labels[~noise_mask]).value_counts().values
    size_std = sizes.std() if len(sizes) > 1 else 0.0

    print(f"  [{name}] k={unique_k}  noise={noise_pct:.1f}%  "
          f"sil={sil:.4f}  DB={db:.4f}  CH={ch:.1f}  size_std={size_std:.0f}")
    return dict(sil=sil, db=db, ch=ch, k=unique_k, noise_pct=noise_pct,
                size_std=size_std, labels=labels)


print(f"\nFitting algorithms (K={K}) ...")

# 1. KMeans
print("  KMeans ...", end=" ", flush=True)
km = KMeans(n_clusters=K, n_init=20, max_iter=400, random_state=42)
lbl = km.fit_predict(X)
results["KMeans"] = compute_metrics(X, lbl, "KMeans")
results["KMeans"]["centers_raw"] = scaler.inverse_transform(km.cluster_centers_)

# 2. MiniBatchKMeans
print("  MiniBatchKMeans ...", end=" ", flush=True)
mbkm = MiniBatchKMeans(n_clusters=K, n_init=20, max_iter=400, random_state=42, batch_size=4096)
lbl  = mbkm.fit_predict(X)
results["MiniBatchKMeans"] = compute_metrics(X, lbl, "MiniBatchKMeans")
results["MiniBatchKMeans"]["centers_raw"] = scaler.inverse_transform(mbkm.cluster_centers_)

# 3. GMM
print("  GMM ...", end=" ", flush=True)
gmm = GaussianMixture(n_components=K, covariance_type="full", max_iter=200,
                      n_init=5, random_state=42)
gmm.fit(X)
lbl = gmm.predict(X)
results["GMM"] = compute_metrics(X, lbl, "GMM")
results["GMM"]["centers_raw"] = scaler.inverse_transform(gmm.means_)

# 4. Agglomerative (subsampled — O(n²) memory)
print(f"  Agglomerative (subsample n={len(agg_idx):,}) ...", end=" ", flush=True)
agg   = AgglomerativeClustering(n_clusters=K, linkage="ward")
lbl_s = agg.fit_predict(X[agg_idx])
# Assign full dataset via nearest centroid
from sklearn.neighbors import NearestCentroid
nc = NearestCentroid()
nc.fit(X[agg_idx], lbl_s)
lbl_full = nc.predict(X)
results["Agglomerative"] = compute_metrics(X, lbl_full, "Agglomerative")
results["Agglomerative"]["centers_raw"] = scaler.inverse_transform(nc.centroids_)

# 5. DBSCAN — use k-distance heuristic: eps = 95th pct of 5-NN distances
print("  DBSCAN (finding eps) ...", end=" ", flush=True)
from sklearn.neighbors import NearestNeighbors
nn = NearestNeighbors(n_neighbors=5, algorithm="ball_tree", n_jobs=-1)
nn.fit(X[sil_idx])
dists, _ = nn.kneighbors(X[sil_idx])
eps_auto = float(np.percentile(dists[:, -1], 90))
print(f"eps={eps_auto:.3f} ...", end=" ", flush=True)
dbscan = DBSCAN(eps=eps_auto, min_samples=15, n_jobs=-1)
lbl = dbscan.fit_predict(X)
results["DBSCAN"] = compute_metrics(X, lbl, "DBSCAN")
results["DBSCAN"]["centers_raw"] = None

# 6. HDBSCAN
print("  HDBSCAN ...", end=" ", flush=True)
hdb = HDBSCAN(min_cluster_size=150, min_samples=10, n_jobs=-1)
lbl = hdb.fit_predict(X)
results["HDBSCAN"] = compute_metrics(X, lbl, "HDBSCAN")
results["HDBSCAN"]["centers_raw"] = None

# 7. Birch
print("  Birch ...", end=" ", flush=True)
birch = Birch(n_clusters=K, threshold=0.5)
lbl   = birch.fit_predict(X)
results["Birch"] = compute_metrics(X, lbl, "Birch")
results["Birch"]["centers_raw"] = scaler.inverse_transform(birch.subcluster_centers_[:K])

# ══════════════════════════════════════════════════════════════════════════════
# 3. LEADERBOARD TABLE
# ══════════════════════════════════════════════════════════════════════════════
summary = pd.DataFrame({
    algo: {"Silhouette ↑": r["sil"], "Davies-Bouldin ↓": r["db"],
           "Calinski-Harabasz ↑": r["ch"], "Clusters Found": r["k"],
           "Noise %": r["noise_pct"], "Size Std Dev ↓": r["size_std"]}
    for algo, r in results.items()
}).T

print("\n" + "="*80)
print("CLUSTERING COMPARISON SUMMARY")
print("="*80)
print(summary.round(3).to_string())

# Score each algorithm: rank on sil (↑), DB (↓), CH (↑), noise (↓), size_std (↓)
def rank_col(col, ascending):
    return col.rank(ascending=ascending, na_option="bottom")

score_df = pd.DataFrame(index=summary.index)
score_df["sil_rank"]  = rank_col(summary["Silhouette ↑"],      ascending=False)
score_df["db_rank"]   = rank_col(summary["Davies-Bouldin ↓"],  ascending=True)
score_df["ch_rank"]   = rank_col(summary["Calinski-Harabasz ↑"], ascending=False)
score_df["noise_rank"]= rank_col(summary["Noise %"],            ascending=True)
score_df["std_rank"]  = rank_col(summary["Size Std Dev ↓"],     ascending=True)
# Weighted: sil × 3, DB × 2, CH × 2, noise × 2, std × 1
score_df["composite"] = (score_df["sil_rank"]   * 3 +
                         score_df["db_rank"]    * 2 +
                         score_df["ch_rank"]    * 2 +
                         score_df["noise_rank"] * 2 +
                         score_df["std_rank"]   * 1)
ranked = score_df.sort_values("composite")
winner = ranked.index[0]
print(f"\n★ Best algorithm (composite rank): {winner}")

# ══════════════════════════════════════════════════════════════════════════════
# FIG K01 — Metric radar spider
# ══════════════════════════════════════════════════════════════════════════════
RADAR_METRICS = ["Silhouette ↑", "Davies-Bouldin ↓", "Calinski-Harabasz ↑",
                 "Noise %", "Size Std Dev ↓"]
radar_lbl = ["Silhouette\n(↑)", "Davies-Bouldin\n(↓ inverted)", "Calinski-Harabasz\n(↑)",
             "Noise %\n(↓ inverted)", "Size Balance\n(↓ inverted)"]

# Normalise: for ↓ metrics, invert so that "higher = better" for the radar
norm = summary[RADAR_METRICS].copy().astype(float)
for col in ["Davies-Bouldin ↓", "Noise %", "Size Std Dev ↓"]:
    col_range = norm[col].max() - norm[col].min() + 1e-9
    norm[col] = 1 - (norm[col] - norm[col].min()) / col_range  # invert
for col in ["Silhouette ↑", "Calinski-Harabasz ↑"]:
    col_range = norm[col].max() - norm[col].min() + 1e-9
    norm[col] = (norm[col] - norm[col].min()) / col_range

N = len(RADAR_METRICS)
angles = np.linspace(0, 2*pi, N, endpoint=False).tolist() + [0]

fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={"polar": True}, facecolor=BG)
ax.set_facecolor(PANEL)
ax.set_xticks(angles[:-1])
ax.set_xticklabels(radar_lbl, size=9, color=SUBTEXT)
ax.set_ylim(0, 1)
ax.set_yticks([0.25, 0.5, 0.75, 1.0])
ax.set_yticklabels(["0.25","0.5","0.75","1.0"], size=7, color=SUBTEXT)
ax.grid(color=BORDER, alpha=0.7)
ax.spines["polar"].set_color(BORDER)

for algo in ALGO_LIST:
    if algo not in results:
        continue
    vals = norm.loc[algo, RADAR_METRICS].tolist() + [norm.loc[algo, RADAR_METRICS[0]]]
    ax.plot(angles, vals, color=ALGO_COLORS[algo], lw=2.2, label=algo)
    ax.fill(angles, vals, color=ALGO_COLORS[algo], alpha=0.10)

ax.set_title("Clustering Algorithm Comparison  ·  Multi-Metric Radar\n"
             "(all axes: higher = better; ↓ metrics are inverted)",
             fontsize=12, color=TEXT, pad=20, fontweight="bold")
ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.1), fontsize=9,
          facecolor=PANEL, edgecolor=BORDER, framealpha=0.6)
fig.tight_layout()
save(fig, "fig_k01_metrics_radar")

# ══════════════════════════════════════════════════════════════════════════════
# FIG K02 — Silhouette + composite score bars
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(15, 5), facecolor=BG)
fig.suptitle("Silhouette Score & Composite Rank by Algorithm",
             fontsize=12, color=TEXT, fontweight="bold")

algos  = list(results.keys())
colors = [ALGO_COLORS[a] for a in algos]
sil_vals  = [results[a]["sil"] if not np.isnan(results[a]["sil"]) else 0 for a in algos]
comp_vals = [score_df.loc[a, "composite"] for a in algos]

# Silhouette
ax1 = axes[0]
bars = ax1.bar(algos, sil_vals, color=colors, width=0.6)
for bar, val in zip(bars, sil_vals):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.002,
             f"{val:.4f}", ha="center", va="bottom", fontsize=8, color=SUBTEXT)
win_s = algos[np.argmax(sil_vals)]
ax1.get_children()[algos.index(win_s)].set_edgecolor("white")
ax1.get_children()[algos.index(win_s)].set_linewidth(2.2)
ax1.set_title("Silhouette Score  (↑ better)", color=TEXT, fontsize=10, fontweight="bold")
ax1.set_ylabel("Score")
plt.setp(ax1.get_xticklabels(), rotation=25, ha="right")

# Composite rank (lower = better → invert for bar)
ax2 = axes[1]
inv_comp = [max(comp_vals) + 1 - v for v in comp_vals]
bars2 = ax2.bar(algos, inv_comp, color=colors, width=0.6)
win_c = algos[np.argmax(inv_comp)]
bars2[algos.index(win_c)].set_edgecolor("white")
bars2[algos.index(win_c)].set_linewidth(2.2)
for bar, val, orig in zip(bars2, inv_comp, comp_vals):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
             f"#{int(score_df.loc[algos[list(inv_comp).index(val)], 'composite'])}", # rank number display
             ha="center", va="bottom", fontsize=8, color=SUBTEXT)
ax2.set_title("Composite Score  (↑ = better overall rank)", color=TEXT, fontsize=10, fontweight="bold")
ax2.set_ylabel("Composite (inverted rank)")
plt.setp(ax2.get_xticklabels(), rotation=25, ha="right")
ax2.annotate(f"★ {winner}", xy=(algos.index(winner), inv_comp[algos.index(winner)]),
             xytext=(algos.index(winner) + 0.8, max(inv_comp)*0.85),
             arrowprops=dict(arrowstyle="->", color="white", lw=1.2),
             fontsize=9, color="white", fontweight="bold")

fig.tight_layout()
save(fig, "fig_k02_silhouette_bars")

# ══════════════════════════════════════════════════════════════════════════════
# FIG K03 — Davies-Bouldin & Calinski-Harabasz
# ══════════════════════════════════════════════════════════════════════════════
db_vals  = [results[a]["db"]  if not np.isnan(results[a]["db"]) else 0  for a in algos]
ch_vals  = [results[a]["ch"]  if not np.isnan(results[a]["ch"]) else 0  for a in algos]

fig, axes = plt.subplots(1, 2, figsize=(15, 5), facecolor=BG)
fig.suptitle("Davies-Bouldin  &  Calinski-Harabasz  by Algorithm",
             fontsize=12, color=TEXT, fontweight="bold")

ax1, ax2 = axes
bars = ax1.bar(algos, db_vals, color=colors, width=0.6)
for bar, val in zip(bars, db_vals):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(db_vals)*0.01,
             f"{val:.3f}", ha="center", va="bottom", fontsize=8, color=SUBTEXT)
win_db = algos[np.argmin(db_vals)]
bars[algos.index(win_db)].set_edgecolor("white")
bars[algos.index(win_db)].set_linewidth(2.2)
ax1.set_title("Davies-Bouldin  (↓ better)", color=TEXT, fontsize=10, fontweight="bold")
ax1.set_ylabel("DB Index")
plt.setp(ax1.get_xticklabels(), rotation=25, ha="right")

bars2 = ax2.bar(algos, ch_vals, color=colors, width=0.6)
for bar, val in zip(bars2, ch_vals):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(ch_vals)*0.01,
             f"{val:,.0f}", ha="center", va="bottom", fontsize=8, color=SUBTEXT)
win_ch = algos[np.argmax(ch_vals)]
bars2[algos.index(win_ch)].set_edgecolor("white")
bars2[algos.index(win_ch)].set_linewidth(2.2)
ax2.set_title("Calinski-Harabasz  (↑ better)", color=TEXT, fontsize=10, fontweight="bold")
ax2.set_ylabel("CH Score")
plt.setp(ax2.get_xticklabels(), rotation=25, ha="right")

fig.tight_layout()
save(fig, "fig_k03_db_ch_bars")

# ══════════════════════════════════════════════════════════════════════════════
# FIG K04 — PCA scatter grid
# ══════════════════════════════════════════════════════════════════════════════
# Use a fixed 40-color palette cycling for up to 40 clusters
CLUSTER_PAL = plt.cm.tab20.colors + plt.cm.tab20b.colors
NOISE_COLOR = "#374151"

fig, axes = plt.subplots(2, 4, figsize=(24, 11), facecolor=BG)
fig.suptitle(f"PCA-2D Cluster Scatter  ·  PC1={var_exp[0]:.1f}%  PC2={var_exp[1]:.1f}%",
             fontsize=13, color=TEXT, fontweight="bold", y=1.01)

for ax, algo in zip(axes.flat, list(results.keys()) + [None]):
    if algo is None:
        ax.set_visible(False)
        continue
    lbl   = results[algo]["labels"]
    k_val = results[algo]["k"]
    sil_v = results[algo]["sil"]
    unique_clusters = sorted(set(lbl[lbl != -1]))

    # Plot noise first (grey)
    noise = lbl[plot_idx] == -1
    if noise.any():
        ax.scatter(X_pca[plot_idx][noise, 0], X_pca[plot_idx][noise, 1],
                   c=NOISE_COLOR, s=4, alpha=0.3, label="Noise")

    for ci in unique_clusters:
        mask = lbl[plot_idx] == ci
        ax.scatter(X_pca[plot_idx][mask, 0], X_pca[plot_idx][mask, 1],
                   c=CLUSTER_PAL[ci % len(CLUSTER_PAL)], s=5, alpha=0.45)

    sil_str = f"{sil_v:.4f}" if not np.isnan(sil_v) else "N/A"
    noise_s = f"  noise={results[algo]['noise_pct']:.1f}%" if results[algo]["noise_pct"] > 0 else ""
    win_tag = "  ★" if algo == winner else ""
    ax.set_title(f"{algo}{win_tag}\nk={k_val}  sil={sil_str}{noise_s}",
                 fontsize=9, color=ALGO_COLORS.get(algo, TEXT), fontweight="bold")
    ax.set_xlabel("PC1", fontsize=7)
    ax.set_ylabel("PC2", fontsize=7)
    ax.tick_params(labelsize=7)

fig.tight_layout()
save(fig, "fig_k04_pca_grid")

# ══════════════════════════════════════════════════════════════════════════════
# FIG K05 — Cluster size distributions
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(2, 4, figsize=(22, 9), facecolor=BG)
fig.suptitle("Cluster Size Distributions by Algorithm",
             fontsize=12, color=TEXT, fontweight="bold", y=1.01)

for ax, algo in zip(axes.flat, list(results.keys()) + [None]):
    if algo is None:
        ax.set_visible(False)
        continue
    lbl     = results[algo]["labels"]
    counts  = pd.Series(lbl[lbl != -1]).value_counts().sort_index()
    noise_n = (lbl == -1).sum()

    bar_colors = [CLUSTER_PAL[i % len(CLUSTER_PAL)] for i in counts.index]
    ax.bar(range(len(counts)), counts.values, color=bar_colors, width=0.7)
    ax.set_title(f"{algo}  (k={len(counts)})",
                 fontsize=9, color=ALGO_COLORS.get(algo, TEXT), fontweight="bold")
    ax.set_xlabel("Cluster ID", fontsize=7)
    ax.set_ylabel("Count", fontsize=7)
    ax.tick_params(labelsize=7)
    if noise_n > 0:
        ax.text(0.98, 0.95, f"Noise: {noise_n:,}\n({noise_n/len(lbl)*100:.1f}%)",
                transform=ax.transAxes, ha="right", va="top",
                fontsize=7, color="#EF4444")

fig.tight_layout()
save(fig, "fig_k05_cluster_sizes")

# ══════════════════════════════════════════════════════════════════════════════
# FIG K06 — Leaderboard heatmap table
# ══════════════════════════════════════════════════════════════════════════════
display_cols = ["Silhouette ↑", "Davies-Bouldin ↓", "Calinski-Harabasz ↑",
                "Clusters Found", "Noise %", "Size Std Dev ↓"]
disp_short   = ["Silhouette\n(↑)", "Davies-Bouldin\n(↓)", "Calinski-H\n(↑)",
                "Clusters\nFound", "Noise %\n(↓)", "Size Std\n(↓)"]

heat = summary[display_cols].astype(float)
# Normalise for color: always higher = better visually (invert ↓ metrics)
heat_norm = heat.copy()
for col in ["Davies-Bouldin ↓", "Noise %", "Size Std Dev ↓"]:
    col_r = heat_norm[col].max() - heat_norm[col].min() + 1e-9
    heat_norm[col] = 1 - (heat_norm[col] - heat_norm[col].min()) / col_r
for col in ["Silhouette ↑", "Calinski-Harabasz ↑"]:
    col_r = heat_norm[col].max() - heat_norm[col].min() + 1e-9
    heat_norm[col] = (heat_norm[col] - heat_norm[col].min()) / col_r
heat_norm["Clusters Found"] = 1 - abs(heat_norm["Clusters Found"] - K) / K  # closest to K=10

# Sort by composite rank
heat_norm = heat_norm.loc[ranked.index]
heat_raw_sorted = heat.loc[ranked.index]

fig, ax = plt.subplots(figsize=(14, 5.5), facecolor=BG)
sns.heatmap(heat_norm, ax=ax, cmap="RdYlGn", annot=heat_raw_sorted.round(3),
            fmt="g", linewidths=0.5, linecolor=BG, cbar=False,
            xticklabels=disp_short, yticklabels=heat_norm.index,
            annot_kws={"size": 8.5})

# Star the winner row
ytlabels = [t.get_text() for t in ax.get_yticklabels()]
for i, lbl in enumerate(ytlabels):
    if lbl == winner:
        ax.get_yticklabels()[i].set_color("#F59E0B")
        ax.get_yticklabels()[i].set_fontweight("bold")

ax.set_title(f"Algorithm Leaderboard  ·  Composite Ranking  (★ winner: {winner})",
             fontsize=12, color=TEXT, fontweight="bold", pad=10)
ax.set_xlabel("")
ax.set_ylabel("")
plt.xticks(rotation=0, fontsize=8.5)
plt.yticks(rotation=0, fontsize=9)
fig.tight_layout()
save(fig, "fig_k06_leaderboard")

# ══════════════════════════════════════════════════════════════════════════════
# FIG K07 — Winner centroid heatmap
# ══════════════════════════════════════════════════════════════════════════════
KEY_FEATURES = [
    "lead_time", "fare_per_pax", "PAX Count", "cabin_ord", "is_dom", "booking_month",
    "Region=Middle East", "Region=ASEAN", "Region=Australasia",
    "Region=North America", "Region=MNL HUB",
    "Farebrand=Economy Supersaver", "Farebrand=Economy Saver",
    "Farebrand=Economy Flex", "Farebrand=Business Flex",
    "Itinerary Type=Beyonds (INT - DOM)", "Itinerary Type=Point to Point",
    "Ticketing Channel=Traditional Travel Agency", "Ticketing Channel=WEB/APP",
    "Ticketing Channel=TMC", "Ticketing Channel=Sea Crew",
]
KEY_FEATURES = [f for f in KEY_FEATURES if f in feature_names]

win_lbl   = results[winner]["labels"]
win_cents = results[winner].get("centers_raw")

if win_cents is None:
    # Compute centroids from label assignments for density-based algorithms
    centers_list = []
    for ci in sorted(set(win_lbl[win_lbl != -1])):
        mask = win_lbl == ci
        centers_list.append(X_raw.values[mask].mean(axis=0))
    win_cents = np.array(centers_list)

win_df = pd.DataFrame(win_cents[:, :len(feature_names)], columns=feature_names)
if len(win_df) > 12:
    win_df = win_df.iloc[:12]  # cap display at 12 clusters

heat_raw   = win_df[KEY_FEATURES]
heat_dn    = (heat_raw - heat_raw.min()) / (heat_raw.max() - heat_raw.min() + 1e-9)
heat_dn.index = [f"C{i}" for i in range(len(heat_dn))]

pretty_cols = [c.replace("Ticketing Channel=","Chan: ")
                .replace("Farebrand=","FB: ")
                .replace("Itinerary Type=","Itin: ")
                .replace("Region=","Reg: ")
               for c in KEY_FEATURES]

fig, ax = plt.subplots(figsize=(20, max(4, len(heat_dn)*0.55 + 1.5)), facecolor=BG)
sns.heatmap(heat_dn, ax=ax, cmap="YlOrRd", annot=False,
            linewidths=0.4, linecolor=BG,
            xticklabels=pretty_cols, yticklabels=heat_dn.index,
            cbar_kws={"shrink": 0.5, "label": "Normalised (0=low, 1=high)"})
ax.set_title(f"★ {winner}  ·  Centroid Feature Heatmap  (normalised per feature)",
             fontsize=12, color=TEXT, pad=10, fontweight="bold")
ax.set_xlabel("")
ax.set_ylabel("Cluster")
plt.xticks(rotation=45, ha="right", fontsize=8)
plt.yticks(rotation=0, fontsize=9)
fig.tight_layout()
save(fig, "fig_k07_winner_centroid")

# ══════════════════════════════════════════════════════════════════════════════
# FINAL CONSOLE SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*80)
print("FINAL LEADERBOARD  (composite rank: sil×3 + DB×2 + CH×2 + noise×2 + std×1)")
print("="*80)
print(f"{'Rank':<6}{'Algorithm':<20}{'Silhouette':<14}{'DB Index':<12}"
      f"{'CH Score':<14}{'k':<8}{'Noise%':<10}{'Size Std'}")
print("-"*80)
for rank, (algo, _) in enumerate(ranked.iterrows(), 1):
    r   = results[algo]
    sil = f"{r['sil']:.4f}" if not np.isnan(r['sil']) else "  N/A"
    db  = f"{r['db']:.4f}"  if not np.isnan(r['db'])  else "  N/A"
    ch  = f"{r['ch']:.1f}"  if not np.isnan(r['ch'])  else "  N/A"
    tag = "  ★" if algo == winner else ""
    print(f"{rank:<6}{algo:<20}{sil:<14}{db:<12}{ch:<14}"
          f"{r['k']:<8}{r['noise_pct']:<10.1f}{r['size_std']:.0f}{tag}")
print()
print(f"Winner: {winner}")
print("All charts saved to cluster_compare_output/")
