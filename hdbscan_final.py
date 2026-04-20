"""HDBSCAN with penalty-weighted feature scaling — PAL customer segmentation.

Pipeline:
  1. Feature engineering + StandardScaler
  2. Penalty-weighted feature re-scaling (high-penalty segments → upweighted dims)
  3. HDBSCAN clustering
  4. Map N micro-clusters → 10 segments via nearest proxy-label centroid
  5. Noise records → annotation queue sorted by penalty risk score
  6. Decision boundary visualisation (KNN on PCA-2D of weighted features)

Outputs (hdbscan_output/):
  fig_h01_feature_weights.png     — penalty-weighted feature importance bar
  fig_h02_hdbscan_raw.png         — HDBSCAN clusters in PCA-2D (weighted space)
  fig_h03_cluster_sizes.png       — cluster size distribution
  fig_h04_mapping_bar.png         — clusters-per-segment + PNR-per-segment
  fig_h05_final_pca.png           — 10 mapped segments + KNN decision boundaries
  fig_h06_noise_queue.png         — annotation queue, top records by penalty risk
  fig_h07_segment_distribution.png — final segment PNR counts vs proxy baseline
  fig_h08_centroid_heatmap.png    — segment centroid feature heatmap
"""

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
from matplotlib.colors import ListedColormap
import seaborn as sns
from pathlib import Path
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.decomposition import PCA
from sklearn.cluster import HDBSCAN
from sklearn.neighbors import KNeighborsClassifier, NearestNeighbors
from pal_colors import SEG_COLORS, SEG_ORDER

OUTPUT = Path("hdbscan_output")
OUTPUT.mkdir(exist_ok=True)

BG, PANEL, BORDER = "#111827", "#1F2937", "#374151"
TEXT, SUBTEXT     = "#F9FAFB", "#9CA3AF"

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
    print(f"  saved → hdbscan_output/{name}.png")

# ══════════════════════════════════════════════════════════════════════════════
# PENALTY MATRIX
# ══════════════════════════════════════════════════════════════════════════════
PENALTY = {
    "Corporate":        10,
    "Mabuhay Loyalist":  8,
    "OFW/Migrant":       5,
    "Premium Bleisure":  4,
    "Pilgrimage":        3,
    "Balikbayan/VFR":    2,
    "Family":            2,
    "Digital Nomad":     2,
    "Last-Minute":       1,
    "Budget/Adventure":  1,
}
TOTAL_PENALTY = sum(PENALTY.values())

# ══════════════════════════════════════════════════════════════════════════════
# 1.  LOAD & ENGINEER
# ══════════════════════════════════════════════════════════════════════════════
print("Loading data ...")
df = pd.read_csv("sample-features.csv")
df["Average Fare"]    = df["Average Fare"].str.replace("$", "", regex=False).astype(float)
df["PNRCreationDate"] = pd.to_datetime(df["PNRCreationDate"], dayfirst=True, errors="coerce")
df["Flight Date"]     = pd.to_datetime(df["Flight Date"],     dayfirst=True, errors="coerce")
df["lead_time"]       = (df["Flight Date"] - df["PNRCreationDate"]).dt.days
df["fare_per_pax"]    = df["Average Fare"] / df["PAX Count"]
df["booking_month"]   = df["PNRCreationDate"].dt.month
df = df.dropna(subset=["lead_time"]).reset_index(drop=True).copy()

cabin_map = {"Y": 0, "W": 1, "J": 2}
df["cabin_ord"] = df["Cabin"].map(cabin_map).fillna(0)
df["is_dom"]    = (df["Entity"] == "DOM").astype(int)

cat_cols = ["Region", "Farebrand", "Itinerary Type", "Ticketing Channel"]
df_enc   = pd.get_dummies(df[cat_cols].fillna("Unknown"),
                          columns=cat_cols, prefix_sep="=", dtype=int)
num_cols = ["lead_time", "Average Fare", "fare_per_pax", "PAX Count",
            "cabin_ord", "is_dom", "booking_month"]

X_raw          = pd.concat([df[num_cols].reset_index(drop=True),
                             df_enc.reset_index(drop=True)], axis=1)
feature_names  = X_raw.columns.tolist()

scaler = StandardScaler()
X      = scaler.fit_transform(X_raw)          # (N, 40), mean≈0, std≈1
print(f"Feature matrix: {X.shape}")

# ══════════════════════════════════════════════════════════════════════════════
# 2.  PROXY WATERFALL LABELS
# ══════════════════════════════════════════════════════════════════════════════
def assign_segment(df):
    seg = pd.Series("Unassigned", index=df.index)
    seg[df["Farebrand"].isin(["Economy Supersaver","Economy Saver"])] = "Budget/Adventure"
    nomad = ((df["PAX Count"]==1) & (df["Region"]=="ASEAN") &
             (df["Ticketing Channel"]=="WEB/APP") &
             (df["Farebrand"].isin(["Economy Flex","Economy Value"])))
    seg[nomad] = "Digital Nomad"
    seg[df["lead_time"] <= 3]                                          = "Last-Minute"
    seg[df["PAX Count"].between(3,5)]                                  = "Family"
    seg[(df["PAX Count"]>=4) &
        (df["Ticketing Channel"]=="Traditional Travel Agency")]         = "Pilgrimage"
    seg[df["Itinerary Type"]=="Beyonds (INT - DOM)"]                   = "Balikbayan/VFR"
    seg[(df["Region"]=="Middle East") |
        (df["Ticketing Channel"]=="Sea Crew")]                          = "OFW/Migrant"
    seg[df["Cabin"]=="W"]                                              = "Premium Bleisure"
    seg[df["Cabin"]=="J"]                                              = "Corporate"
    return seg

df["segment"] = assign_segment(df)
labeled_mask  = df["segment"] != "Unassigned"
print(f"Proxy labels — labelled: {labeled_mask.sum():,}  "
      f"unassigned: {(~labeled_mask).sum():,}")
print(df["segment"].value_counts().to_string())

# ══════════════════════════════════════════════════════════════════════════════
# 3.  PENALTY-WEIGHTED FEATURE SCALING
# ══════════════════════════════════════════════════════════════════════════════
print("\nComputing penalty-weighted feature weights ...")

# X is StandardScaler output → overall mean ≈ 0
# For each high-penalty segment, measure how far its centroid sits from 0 in each feature.
# Upweight features where high-penalty segments deviate strongly.
feature_weights = np.ones(X.shape[1])

for seg, pw in PENALTY.items():
    seg_mask = (df["segment"] == seg).values
    if seg_mask.sum() < 10:
        continue
    seg_mean = X[seg_mask].mean(axis=0)
    # Contribution proportional to penalty share × absolute centroid deviation
    feature_weights += (pw / TOTAL_PENALTY) * np.abs(seg_mean)

# Normalise: mean weight = 1 (preserves overall scale, only changes relative emphasis)
feature_weights /= feature_weights.mean()

X_weighted = X * feature_weights          # (N, 40), penalty-aware distance space

# Top-15 most upweighted features for reporting
top_feat_idx = np.argsort(feature_weights)[::-1][:15]
print("\nTop-15 penalty-upweighted features:")
for i in top_feat_idx:
    print(f"  {feature_names[i]:<45}  weight={feature_weights[i]:.4f}")

# ══════════════════════════════════════════════════════════════════════════════
# FIG H01 — Feature weights bar chart
# ══════════════════════════════════════════════════════════════════════════════
top30_idx    = np.argsort(feature_weights)[::-1][:30]
top30_names  = [feature_names[i].replace("Ticketing Channel=","Chan:")
                                 .replace("Farebrand=","FB:")
                                 .replace("Itinerary Type=","Itin:")
                                 .replace("Region=","Reg:")
                for i in top30_idx]
top30_vals   = feature_weights[top30_idx]
bar_colors   = ["#F59E0B" if v >= np.percentile(feature_weights, 90) else "#3B82F6"
                for v in top30_vals]

fig, ax = plt.subplots(figsize=(14, 7), facecolor=BG)
bars = ax.barh(range(len(top30_vals)), top30_vals[::-1],
               color=bar_colors[::-1], height=0.65)
ax.axvline(1.0, color="white", ls="--", lw=1.1, alpha=0.5, label="baseline weight=1")
ax.set_yticks(range(len(top30_vals)))
ax.set_yticklabels(top30_names[::-1], fontsize=8)
ax.set_xlabel("Feature Weight (>1 = upweighted by penalty matrix)")
ax.set_title("Penalty-Weighted Feature Scaling\n"
             "Features that discriminate Corporate / OFW / Premium Bleisure receive higher weight",
             fontsize=11, color=TEXT, fontweight="bold")
ax.legend(fontsize=8, facecolor=PANEL, edgecolor=BORDER)
fig.tight_layout()
save(fig, "fig_h01_feature_weights")

# ══════════════════════════════════════════════════════════════════════════════
# 4.  FIT HDBSCAN ON WEIGHTED FEATURES
# ══════════════════════════════════════════════════════════════════════════════
print("\nFitting HDBSCAN on penalty-weighted feature space ...")
hdb = HDBSCAN(min_cluster_size=150, min_samples=10, n_jobs=-1)
hdb_labels = hdb.fit_predict(X_weighted)

noise_mask   = hdb_labels == -1
cluster_ids  = sorted(set(hdb_labels[~noise_mask]))
n_clusters   = len(cluster_ids)
n_noise      = noise_mask.sum()
noise_pct    = noise_mask.mean() * 100

print(f"HDBSCAN result: {n_clusters} clusters  |  "
      f"noise: {n_noise:,} ({noise_pct:.1f}%)")

sizes = pd.Series(hdb_labels[~noise_mask]).value_counts().sort_values(ascending=False)

# PCA on weighted space for visualisation
pca2    = PCA(n_components=2, random_state=42)
X_pca   = pca2.fit_transform(X_weighted)
var_exp = pca2.explained_variance_ratio_ * 100
df["pc1"] = X_pca[:, 0]
df["pc2"] = X_pca[:, 1]

# ══════════════════════════════════════════════════════════════════════════════
# FIG H02 — HDBSCAN raw clusters in PCA-2D
# ══════════════════════════════════════════════════════════════════════════════
TAB_PAL  = list(plt.cm.tab20.colors) + list(plt.cm.tab20b.colors)
RNG      = np.random.default_rng(42)
plot_idx = RNG.choice(len(X_pca), size=min(6000, len(X_pca)), replace=False)

fig, ax = plt.subplots(figsize=(14, 9), facecolor=BG)

# noise
nz = noise_mask[plot_idx]
ax.scatter(X_pca[plot_idx][nz, 0], X_pca[plot_idx][nz, 1],
           c="#1F2937", edgecolors="#EF4444", linewidths=0.4,
           s=9, alpha=0.7, label=f"Noise ({n_noise:,}  {noise_pct:.1f}%)", zorder=2)

# top clusters (largest 20 coloured individually, rest grey)
top20_ids = sizes.index[:20].tolist()
for cid in reversed(top20_ids):
    m = hdb_labels[plot_idx] == cid
    ax.scatter(X_pca[plot_idx][m, 0], X_pca[plot_idx][m, 1],
               c=TAB_PAL[top20_ids.index(cid) % len(TAB_PAL)],
               s=8, alpha=0.55, zorder=3)

micro = np.array([l not in top20_ids and l != -1 for l in hdb_labels[plot_idx]])
ax.scatter(X_pca[plot_idx][micro, 0], X_pca[plot_idx][micro, 1],
           c="#4B5563", s=5, alpha=0.25, label=f"Micro-clusters", zorder=1)

ax.set_title(f"HDBSCAN  ·  Penalty-Weighted Feature Space  ·  {n_clusters} clusters\n"
             f"PC1={var_exp[0]:.1f}%  PC2={var_exp[1]:.1f}%  |  "
             f"Red-edged = noise ({noise_pct:.1f}%)",
             fontsize=11, color=TEXT, fontweight="bold")
ax.set_xlabel(f"PC1 ({var_exp[0]:.1f}%)", fontsize=9)
ax.set_ylabel(f"PC2 ({var_exp[1]:.1f}%)", fontsize=9)
ax.legend(fontsize=7.5, framealpha=0.3, facecolor=PANEL, edgecolor=BORDER)
fig.tight_layout()
save(fig, "fig_h02_hdbscan_raw")

# ══════════════════════════════════════════════════════════════════════════════
# FIG H03 — Cluster size distribution
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(15, 5), facecolor=BG)
fig.suptitle(f"HDBSCAN Cluster Size Distribution  ·  {n_clusters} clusters  "
             f"(penalty-weighted features)", fontsize=11, color=TEXT, fontweight="bold")

ax1, ax2 = axes
top30s   = sizes.head(30)
ax1.bar(range(len(top30s)), top30s.values,
        color=[TAB_PAL[i % len(TAB_PAL)] for i in range(len(top30s))], width=0.7)
ax1.set_title("Top-30 Cluster Sizes", color=TEXT, fontsize=9, fontweight="bold")
ax1.set_xlabel("Cluster rank")
ax1.set_ylabel("PNR Count")
for i, val in enumerate(top30s.values):
    ax1.text(i, val + max(top30s)*0.01, f"{val:,}", ha="center", fontsize=5.5, color=SUBTEXT)

rank = np.arange(1, len(sizes)+1)
ax2.scatter(rank, sizes.values,
            c=[TAB_PAL[i % len(TAB_PAL)] for i in range(len(sizes))], s=15, alpha=0.75)
ax2.set_xscale("log"); ax2.set_yscale("log")
ax2.axhline(150, color="#F59E0B", ls="--", lw=1.1, alpha=0.7, label="min_cluster_size=150")
ax2.set_title("Rank–Size  (log–log)", color=TEXT, fontsize=9, fontweight="bold")
ax2.set_xlabel("Cluster rank"); ax2.set_ylabel("Size")
ax2.legend(fontsize=8, facecolor=PANEL, edgecolor=BORDER)
ax2.text(0.98, 0.95, f"Noise: {n_noise:,} ({noise_pct:.1f}%)",
         transform=ax2.transAxes, ha="right", va="top", fontsize=8, color="#EF4444")
fig.tight_layout()
save(fig, "fig_h03_cluster_sizes")

# ══════════════════════════════════════════════════════════════════════════════
# 5.  MAP CLUSTERS → 10 SEGMENTS  (nearest proxy-label centroid)
# ══════════════════════════════════════════════════════════════════════════════
print("\nMapping clusters → 10 segments via nearest proxy-label centroid ...")

# Compute proxy-segment centroids in weighted feature space
seg_names_present  = [s for s in SEG_ORDER
                      if s in df["segment"].unique() and s != "Unassigned"]
seg_centroids      = {}
for seg in seg_names_present:
    mask = (df["segment"] == seg).values
    seg_centroids[seg] = X_weighted[mask].mean(axis=0)

seg_cent_matrix = np.array([seg_centroids[s] for s in seg_names_present])

# For each HDBSCAN cluster, find nearest segment centroid
cluster_centroids = {}
for cid in cluster_ids:
    mask = hdb_labels == cid
    cluster_centroids[cid] = X_weighted[mask].mean(axis=0)

clust_cent_matrix = np.array([cluster_centroids[cid] for cid in cluster_ids])
nn = NearestNeighbors(n_neighbors=1, algorithm="brute").fit(seg_cent_matrix)
_, nn_idx = nn.kneighbors(clust_cent_matrix)
cluster_to_seg = {cid: seg_names_present[nn_idx[i, 0]]
                  for i, cid in enumerate(cluster_ids)}
cluster_to_seg[-1] = "Unassigned"   # noise stays unassigned for now

df["hdb_cluster"]  = hdb_labels
df["hdb_segment"]  = df["hdb_cluster"].map(cluster_to_seg)

print("\nMapped segment distribution (HDBSCAN):")
hdb_seg_counts = df["hdb_segment"].value_counts()
print(hdb_seg_counts.to_string())

# ══════════════════════════════════════════════════════════════════════════════
# 6.  NOISE → ANNOTATION QUEUE  (sorted by penalty risk score)
# ══════════════════════════════════════════════════════════════════════════════
print("\nBuilding annotation queue from noise records ...")

noise_df  = df[noise_mask].copy()
noise_X   = X_weighted[noise_mask]

# Distance from each noise record to each segment centroid
dists = np.array([
    np.linalg.norm(noise_X - seg_centroids[s], axis=1)
    for s in seg_names_present
]).T   # (n_noise, n_segments)

nearest_seg_idx   = dists.argmin(axis=1)
nearest_seg       = [seg_names_present[i] for i in nearest_seg_idx]
nearest_dist      = dists[np.arange(len(dists)), nearest_seg_idx]
nearest_penalty   = [PENALTY.get(s, 1) for s in nearest_seg]

# Risk score: high penalty AND close to centroid → annotate first
# risk = penalty / (distance + ε) — but normalise distance first
dist_norm         = (nearest_dist - nearest_dist.min()) / (nearest_dist.max() - nearest_dist.min() + 1e-9)
risk_score        = np.array(nearest_penalty) / (dist_norm + 0.1)

noise_df["nearest_segment"] = nearest_seg
noise_df["nearest_penalty"] = nearest_penalty
noise_df["dist_to_centroid"]= nearest_dist
noise_df["risk_score"]      = risk_score
noise_df = noise_df.sort_values("risk_score", ascending=False).reset_index(drop=True)
noise_df["queue_rank"]      = range(1, len(noise_df)+1)

print(f"Annotation queue: {len(noise_df):,} records")
print("Top-10 records:")
print(noise_df[["queue_rank","nearest_segment","nearest_penalty",
                "dist_to_centroid","risk_score","lead_time","fare_per_pax","PAX Count",
                "Cabin","Region","Ticketing Channel"]].head(10).to_string(index=False))

# Save queue to CSV
queue_path = OUTPUT / "annotation_queue.csv"
noise_df[["queue_rank","nearest_segment","nearest_penalty","risk_score",
          "dist_to_centroid","lead_time","Average Fare","fare_per_pax",
          "PAX Count","Cabin","Region","Farebrand","Ticketing Channel",
          "Itinerary Type","Sector","DOW","booking_month"]].to_csv(queue_path, index=False)
print(f"  saved → hdbscan_output/annotation_queue.csv")

# ══════════════════════════════════════════════════════════════════════════════
# FIG H04 — Mapping bar (clusters per segment + PNRs per segment)
# ══════════════════════════════════════════════════════════════════════════════
seg_cluster_counts = (pd.Series(cluster_to_seg)
                      .drop(-1, errors="ignore")
                      .value_counts()
                      .reindex(seg_names_present, fill_value=0))
seg_pnr_counts     = (df[~noise_mask]["hdb_segment"]
                      .value_counts()
                      .reindex(seg_names_present, fill_value=0))

fig, axes = plt.subplots(1, 2, figsize=(16, 6), facecolor=BG)
fig.suptitle(f"HDBSCAN {n_clusters} Micro-Clusters → 10 Segments  "
             f"(nearest penalty-weighted centroid)",
             fontsize=11, color=TEXT, fontweight="bold")

colors_seg = [SEG_COLORS.get(s, "#60A5FA") for s in seg_names_present]

ax1 = axes[0]
bars = ax1.bar(seg_names_present, seg_cluster_counts.values,
               color=colors_seg, width=0.65)
for bar, val in zip(bars, seg_cluster_counts.values):
    ax1.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.2,
             str(val), ha="center", va="bottom", fontsize=9, color=SUBTEXT)
ax1.set_title("HDBSCAN Clusters per Segment", color=TEXT, fontsize=10, fontweight="bold")
ax1.set_ylabel("# Micro-Clusters")
plt.setp(ax1.get_xticklabels(), rotation=30, ha="right", fontsize=8)

ax2 = axes[1]
bars2 = ax2.bar(seg_names_present, seg_pnr_counts.values,
                color=colors_seg, width=0.65)
for bar, val in zip(bars2, seg_pnr_counts.values):
    ax2.text(bar.get_x()+bar.get_width()/2, bar.get_height()+max(seg_pnr_counts)*0.01,
             f"{val:,}\n({val/len(df)*100:.1f}%)",
             ha="center", va="bottom", fontsize=7, color=SUBTEXT)
ax2.set_title(f"PNRs per Segment  (noise={n_noise:,} excluded → annotation queue)",
              color=TEXT, fontsize=10, fontweight="bold")
ax2.set_ylabel("PNR Count")
plt.setp(ax2.get_xticklabels(), rotation=30, ha="right", fontsize=8)

fig.tight_layout()
save(fig, "fig_h04_mapping_bar")

# ══════════════════════════════════════════════════════════════════════════════
# FIG H05 — Final 10-segment PCA + KNN decision boundaries
# ══════════════════════════════════════════════════════════════════════════════
print("\nBuilding decision boundaries (KNN-15 on PCA-2D) ...")

# Train KNN on mapped (non-noise) records
mapped_df   = df[~noise_mask].copy()
le          = LabelEncoder()
le.fit(seg_names_present)
y_mapped    = le.transform(mapped_df["hdb_segment"].values)
X_pca_mapped = X_pca[~noise_mask]

knn = KNeighborsClassifier(n_neighbors=15, weights="distance", n_jobs=-1)
knn.fit(X_pca_mapped, y_mapped)

PAD  = 0.6;  STEP = 0.04
x1_min = X_pca[:,0].min()-PAD;  x1_max = X_pca[:,0].max()+PAD
x2_min = X_pca[:,1].min()-PAD;  x2_max = X_pca[:,1].max()+PAD
xx, yy = np.meshgrid(np.arange(x1_min, x1_max, STEP),
                     np.arange(x2_min, x2_max, STEP))
Z = knn.predict(np.c_[xx.ravel(), yy.ravel()]).reshape(xx.shape)
levels = np.arange(-0.5, len(le.classes_)+0.5, 1)
cmap_fill = ListedColormap([SEG_COLORS[c] for c in le.classes_])

fig, axes = plt.subplots(1, 2, figsize=(20, 9), facecolor=BG)
fig.suptitle("Final 10-Segment Assignment  ·  HDBSCAN + Penalty-Weighted Features  "
             "·  KNN-15 Decision Boundaries",
             fontsize=12, color=TEXT, fontweight="bold")

for ax, show_boundaries in zip(axes, [True, False]):
    ax.set_facecolor(PANEL)

    if show_boundaries:
        ax.contourf(xx, yy, Z, levels=levels, cmap=cmap_fill, alpha=0.20, zorder=1)
        ax.contour(xx, yy, Z, levels=levels, colors="white",
                   linewidths=0.9, alpha=0.55, zorder=2)

    # Noise (grey, small)
    noise_pca = X_pca[noise_mask]
    ax.scatter(noise_pca[::3, 0], noise_pca[::3, 1],
               c="#4B5563", s=5, alpha=0.25, zorder=3, label="Noise (queue)")

    # Mapped segments
    for seg in seg_names_present:
        m = mapped_df["hdb_segment"] == seg
        ax.scatter(X_pca_mapped[m, 0], X_pca_mapped[m, 1],
                   c=SEG_COLORS.get(seg, "#60A5FA"), s=8, alpha=0.55, zorder=4,
                   label=f"{seg} ({m.sum():,})")

    title = ("With Decision Boundaries" if show_boundaries else "Scatter Only")
    ax.set_title(title, color=TEXT, fontsize=10, fontweight="bold")
    ax.set_xlabel(f"PC1 ({var_exp[0]:.1f}%)", fontsize=8)
    ax.set_ylabel(f"PC2 ({var_exp[1]:.1f}%)", fontsize=8)
    ax.set_xlim(x1_min, x1_max)
    ax.set_ylim(x2_min, x2_max)

patches = [mpatches.Patch(color=SEG_COLORS.get(s,"#60A5FA"), label=s)
           for s in seg_names_present]
patches.append(mpatches.Patch(color="#4B5563", label=f"Noise → queue ({n_noise:,})"))
fig.legend(handles=patches, fontsize=7.5, loc="lower center", ncol=5,
           framealpha=0.35, facecolor=PANEL, edgecolor=BORDER,
           bbox_to_anchor=(0.5, -0.03))
fig.tight_layout()
save(fig, "fig_h05_final_pca")

# ══════════════════════════════════════════════════════════════════════════════
# FIG H06 — Annotation queue visualisation
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 3, figsize=(18, 6), facecolor=BG)
fig.suptitle(f"Annotation Queue  ·  {n_noise:,} Noise Records Sorted by Penalty Risk Score",
             fontsize=11, color=TEXT, fontweight="bold")

# Left: queue distribution by nearest segment
ax1 = axes[0]
q_counts = noise_df["nearest_segment"].value_counts()
colors_q  = [SEG_COLORS.get(s,"#60A5FA") for s in q_counts.index]
bars = ax1.bar(q_counts.index, q_counts.values, color=colors_q, width=0.65)
for bar, val in zip(bars, q_counts.values):
    ax1.text(bar.get_x()+bar.get_width()/2, bar.get_height()+5,
             f"{val:,}", ha="center", va="bottom", fontsize=8, color=SUBTEXT)
ax1.set_title("Noise Records by\nNearest Segment", color=TEXT, fontsize=9, fontweight="bold")
ax1.set_ylabel("Count")
plt.setp(ax1.get_xticklabels(), rotation=35, ha="right", fontsize=7.5)

# Middle: risk score distribution
ax2 = axes[1]
for seg in q_counts.index:
    sub = noise_df[noise_df["nearest_segment"]==seg]["risk_score"]
    ax2.scatter(np.full(len(sub), seg), sub,
                c=SEG_COLORS.get(seg,"#60A5FA"), s=6, alpha=0.4)
ax2.set_title("Risk Score Distribution\nby Nearest Segment", color=TEXT, fontsize=9, fontweight="bold")
ax2.set_ylabel("Risk Score (↑ = annotate first)")
plt.setp(ax2.get_xticklabels(), rotation=35, ha="right", fontsize=7.5)

# Right: PCA scatter of noise coloured by nearest segment + penalty
ax3 = axes[2]
for seg in q_counts.index:
    m = noise_df["nearest_segment"] == seg
    sub_idx = noise_df[m].index
    ax3.scatter(noise_df.loc[m, "pc1"], noise_df.loc[m, "pc2"],
                c=SEG_COLORS.get(seg,"#60A5FA"), s=8, alpha=0.6,
                label=f"{seg} (×{PENALTY.get(seg,1)})")
ax3.set_title("Noise Records in PCA Space\n(colour = nearest segment, priority = ×penalty)",
              color=TEXT, fontsize=9, fontweight="bold")
ax3.set_xlabel(f"PC1 ({var_exp[0]:.1f}%)", fontsize=8)
ax3.set_ylabel(f"PC2 ({var_exp[1]:.1f}%)", fontsize=8)
ax3.legend(fontsize=6.5, framealpha=0.3, facecolor=PANEL, edgecolor=BORDER, ncol=2)

fig.tight_layout()
save(fig, "fig_h06_noise_queue")

# ══════════════════════════════════════════════════════════════════════════════
# FIG H07 — Proxy baseline vs HDBSCAN segment distribution comparison
# ══════════════════════════════════════════════════════════════════════════════
proxy_counts = (df["segment"].value_counts()
                .reindex(seg_names_present + ["Unassigned"], fill_value=0))
hdb_counts   = (df["hdb_segment"].value_counts()
                .reindex(seg_names_present + ["Unassigned"], fill_value=0))

x     = np.arange(len(seg_names_present)+1)
w     = 0.38
segs  = seg_names_present + ["Unassigned"]
cols  = [SEG_COLORS.get(s,"#4B5563") for s in segs]

fig, ax = plt.subplots(figsize=(16, 6), facecolor=BG)
bars1 = ax.bar(x - w/2, [proxy_counts[s] for s in segs], width=w,
               color=cols, alpha=0.55, label="Proxy waterfall", edgecolor=BORDER)
bars2 = ax.bar(x + w/2, [hdb_counts[s]  for s in segs], width=w,
               color=cols, alpha=0.95, label="HDBSCAN mapped",  edgecolor="white", linewidth=0.5)
ax.set_xticks(x)
ax.set_xticklabels(segs, rotation=30, ha="right", fontsize=8)
ax.set_title("Segment Distribution: Proxy Waterfall  vs  HDBSCAN Mapped",
             fontsize=11, color=TEXT, fontweight="bold")
ax.set_ylabel("PNR Count")
ax.legend(fontsize=9, facecolor=PANEL, edgecolor=BORDER)
fig.tight_layout()
save(fig, "fig_h07_segment_distribution")

# ══════════════════════════════════════════════════════════════════════════════
# FIG H08 — Segment centroid heatmap (HDBSCAN-mapped centroids)
# ══════════════════════════════════════════════════════════════════════════════
KEY_FEAT = [
    "lead_time","fare_per_pax","PAX Count","cabin_ord","is_dom","booking_month",
    "Region=Middle East","Region=ASEAN","Region=Australasia","Region=North America","Region=MNL HUB",
    "Farebrand=Economy Supersaver","Farebrand=Economy Saver",
    "Farebrand=Economy Flex","Farebrand=Business Flex",
    "Itinerary Type=Beyonds (INT - DOM)","Itinerary Type=Point to Point",
    "Ticketing Channel=Traditional Travel Agency","Ticketing Channel=WEB/APP",
    "Ticketing Channel=TMC","Ticketing Channel=Sea Crew",
]
KEY_FEAT = [f for f in KEY_FEAT if f in feature_names]

cents = {}
for seg in seg_names_present:
    m = (df["hdb_segment"] == seg).values & ~noise_mask
    if m.sum() == 0:
        m = (df["segment"] == seg).values
    cents[seg] = X_raw.values[m].mean(axis=0) if m.sum() > 0 else np.zeros(len(feature_names))

cent_df   = pd.DataFrame(cents, index=feature_names).T[KEY_FEAT]
cent_norm = (cent_df - cent_df.min()) / (cent_df.max() - cent_df.min() + 1e-9)
cent_norm.index = [f"{s}  (×{PENALTY.get(s,1)})" for s in cent_norm.index]

pretty = [c.replace("Ticketing Channel=","Chan:")
           .replace("Farebrand=","FB:")
           .replace("Itinerary Type=","Itin:")
           .replace("Region=","Reg:")
          for c in KEY_FEAT]

fig, ax = plt.subplots(figsize=(20, 6), facecolor=BG)
sns.heatmap(cent_norm, ax=ax, cmap="YlOrRd", annot=False,
            linewidths=0.4, linecolor=BG,
            xticklabels=pretty, yticklabels=cent_norm.index,
            cbar_kws={"shrink":0.5,"label":"Normalised (0=low, 1=high)"})
ax.set_title("Segment Centroids  ·  HDBSCAN + Penalty-Weighted Features  "
             "(penalty weight shown in row label)",
             fontsize=11, color=TEXT, pad=10, fontweight="bold")
plt.xticks(rotation=45, ha="right", fontsize=8)
plt.yticks(rotation=0, fontsize=8.5)
fig.tight_layout()
save(fig, "fig_h08_centroid_heatmap")

# ══════════════════════════════════════════════════════════════════════════════
# CONSOLE SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("HDBSCAN FINAL SUMMARY  (penalty-weighted features)")
print("="*70)
print(f"Total records       : {len(df):,}")
print(f"Clusters found      : {n_clusters}")
print(f"Noise → queue       : {n_noise:,}  ({noise_pct:.2f}%)")
print(f"\nFinal segment distribution:")
for seg in seg_names_present:
    n   = (df["hdb_segment"]==seg).sum()
    pct = n / len(df) * 100
    pw  = PENALTY.get(seg, 1)
    print(f"  {seg:<22} n={n:>6,}  ({pct:4.1f}%)  penalty=×{pw}")
print(f"\n  {'Noise (annotation queue)':<22} n={n_noise:>6,}  ({noise_pct:4.1f}%)")
print(f"\nTop-5 annotation queue (annotate these first):")
print(noise_df[["queue_rank","nearest_segment","nearest_penalty","risk_score"]].head(5).to_string(index=False))
print("\nAll outputs saved to hdbscan_output/")
