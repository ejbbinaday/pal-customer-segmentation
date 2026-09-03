"""DBSCAN deep-dive visualisation — PAL customer segmentation.

Outputs (dbscan_output/):
  fig_d01_pca_full.png          — PCA scatter: top clusters coloured, micro-clusters grey
  fig_d02_size_distribution.png — power-law cluster size plot (log scale)
  fig_d03_eps_sensitivity.png   — how eps shifts k / noise %
  fig_d04_noise_profile.png     — feature fingerprint of noise vs non-noise
  fig_d05_top_profiles.png      — centroid heatmap for top-15 largest clusters
  fig_d06_segment_mapping.png   — 221 micro-clusters collapsed → 10 segments via nearest KMeans centroid
  fig_d07_segment_pca.png       — PCA scatter re-coloured by mapped segment
  fig_d08_density_kde.png       — KDE density in PCA space, noise overlay
"""

import warnings

warnings.filterwarnings("ignore")

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import DBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from pal_colors import SEG_COLORS

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "dbscan_output"
OUTPUT.mkdir(parents=True, exist_ok=True)

BG, PANEL, BORDER = "#111827", "#1F2937", "#374151"
TEXT, SUBTEXT = "#F9FAFB", "#9CA3AF"
NOISE_C = "#1F2937"
NOISE_EDGE = "#EF4444"

sns.set_theme(style="darkgrid", font_scale=0.9)
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
    print(f"  saved → dbscan_output/{name}.png")


# ══════════════════════════════════════════════════════════════════════════════
# 1. LOAD & FEATURE ENGINEERING  (identical to cluster_compare.py)
# ══════════════════════════════════════════════════════════════════════════════
print("Loading data ...")
df = pd.read_csv(ROOT / "data" / "raw" / "sample-features.csv")
df["Average Fare"] = df["Average Fare"].str.replace("$", "", regex=False).astype(float)
df["PNRCreationDate"] = pd.to_datetime(df["PNRCreationDate"], dayfirst=True, errors="coerce")
df["Flight Date"] = pd.to_datetime(df["Flight Date"], dayfirst=True, errors="coerce")
df["lead_time"] = (df["Flight Date"] - df["PNRCreationDate"]).dt.days
df["fare_per_pax"] = df["Average Fare"] / df["PAX Count"]
df["booking_month"] = df["PNRCreationDate"].dt.month
df = df.dropna(subset=["lead_time"]).copy()

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
feature_names = X_raw.columns.tolist()

scaler = StandardScaler()
X = scaler.fit_transform(X_raw)

pca2 = PCA(n_components=2, random_state=42)
X_pca = pca2.fit_transform(X)
var_exp = pca2.explained_variance_ratio_ * 100

RNG = np.random.default_rng(42)
plot_idx = RNG.choice(len(X), size=min(6000, len(X)), replace=False)

print(f"Feature matrix: {X.shape}")

# ══════════════════════════════════════════════════════════════════════════════
# 2. FIT DBSCAN  (auto eps via 90th-pct of 5-NN distances)
# ══════════════════════════════════════════════════════════════════════════════
print("Computing auto-eps ...")
sil_idx = RNG.choice(len(X), size=8000, replace=False)
nn = NearestNeighbors(n_neighbors=5, algorithm="ball_tree", n_jobs=-1)
nn.fit(X[sil_idx])
dists, _ = nn.kneighbors(X[sil_idx])
k_dists = np.sort(dists[:, -1])  # sorted 5-NN distances for knee plot
eps_auto = float(np.percentile(dists[:, -1], 90))

print(f"eps={eps_auto:.3f}  fitting DBSCAN ...")
db = DBSCAN(eps=eps_auto, min_samples=15, n_jobs=-1)
labels = db.fit_predict(X)

noise_mask = labels == -1
cluster_ids = sorted(set(labels[~noise_mask]))
n_clusters = len(cluster_ids)
n_noise = noise_mask.sum()
noise_pct = noise_mask.mean() * 100

print(f"Clusters: {n_clusters}  |  Noise: {n_noise:,}  ({noise_pct:.1f}%)")

# Cluster sizes sorted descending
sizes = pd.Series(labels[~noise_mask]).value_counts().sort_values(ascending=False)
top_k = 15  # top N clusters to show individually
top_ids = sizes.index[:top_k].tolist()
micro_ids = sizes.index[top_k:].tolist()

# Build a 40-colour palette cycling for the top clusters
TAB_PAL = list(plt.cm.tab20.colors) + list(plt.cm.tab20b.colors)
top_color = {cid: TAB_PAL[i % len(TAB_PAL)] for i, cid in enumerate(top_ids)}


def point_color(lbl):
    if lbl == -1:
        return NOISE_C
    elif lbl in top_color:
        return top_color[lbl]
    else:
        return "#4B5563"  # micro-cluster grey


# ══════════════════════════════════════════════════════════════════════════════
# FIG D01 — PCA full scatter
# ══════════════════════════════════════════════════════════════════════════════
print("\nGenerating figures ...")
fig, ax = plt.subplots(figsize=(14, 9), facecolor=BG)

# micro-clusters (behind)
micro_mask = np.array([l not in top_ids and l != -1 for l in labels[plot_idx]])
ax.scatter(
    X_pca[plot_idx][micro_mask, 0],
    X_pca[plot_idx][micro_mask, 1],
    c="#4B5563",
    s=5,
    alpha=0.25,
    label=f"Micro-clusters ({len(micro_ids)})",
)

# top clusters
for cid in reversed(top_ids):  # draw largest last (on top)
    mask = labels[plot_idx] == cid
    ax.scatter(
        X_pca[plot_idx][mask, 0],
        X_pca[plot_idx][mask, 1],
        c=top_color[cid],
        s=8,
        alpha=0.55,
        label=f"C{cid} (n={sizes[cid]:,})",
    )

# noise
noise_p = noise_mask[plot_idx]
ax.scatter(
    X_pca[plot_idx][noise_p, 0],
    X_pca[plot_idx][noise_p, 1],
    c=NOISE_C,
    edgecolors=NOISE_EDGE,
    linewidths=0.4,
    s=9,
    alpha=0.7,
    label=f"Noise ({n_noise:,} / {noise_pct:.1f}%)",
)

ax.set_title(
    f"DBSCAN  ·  {n_clusters} clusters  ·  eps={eps_auto:.3f}  min_samples=15\n"
    f"PC1={var_exp[0]:.1f}%  PC2={var_exp[1]:.1f}%  |  "
    f"Top-{top_k} coloured  ·  rest grey  ·  noise red-edged",
    fontsize=11,
    color=TEXT,
    fontweight="bold",
)
ax.set_xlabel(f"PC1  ({var_exp[0]:.1f}%)", fontsize=9)
ax.set_ylabel(f"PC2  ({var_exp[1]:.1f}%)", fontsize=9)
ax.legend(
    fontsize=6.5, loc="upper right", ncol=2, framealpha=0.35, facecolor=PANEL, edgecolor=BORDER
)
fig.tight_layout()
save(fig, "fig_d01_pca_full")

# ══════════════════════════════════════════════════════════════════════════════
# FIG D02 — Cluster size distribution (power law)
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(15, 5), facecolor=BG)
fig.suptitle(
    f"DBSCAN Cluster Size Distribution  ·  {n_clusters} clusters",
    fontsize=12,
    color=TEXT,
    fontweight="bold",
)

ax1, ax2 = axes
# Bar: top 30 clusters
top30 = sizes.head(30)
colors = [top_color.get(cid, "#4B5563") for cid in top30.index]
ax1.bar(range(len(top30)), top30.values, color=colors, width=0.7)
ax1.set_xticks(range(len(top30)))
ax1.set_xticklabels([f"C{c}" for c in top30.index], rotation=45, ha="right", fontsize=7)
ax1.set_title("Top-30 Cluster Sizes", color=TEXT, fontsize=10, fontweight="bold")
ax1.set_ylabel("PNR Count")
for i, (_cid, val) in enumerate(top30.items()):
    ax1.text(i, val + max(top30) * 0.01, f"{val:,}", ha="center", fontsize=6, color=SUBTEXT)

# Log-log rank-size (Zipf-like)
rank = np.arange(1, len(sizes) + 1)
ax2.scatter(
    rank, sizes.values, c=[top_color.get(cid, "#4B5563") for cid in sizes.index], s=18, alpha=0.75
)
ax2.set_xscale("log")
ax2.set_yscale("log")
ax2.set_title(
    "Rank–Size Plot  (log–log)  ·  Power-law signature", color=TEXT, fontsize=10, fontweight="bold"
)
ax2.set_xlabel("Cluster Rank")
ax2.set_ylabel("Cluster Size")
ax2.axhline(15, color=NOISE_EDGE, ls="--", lw=1, alpha=0.6, label="min_samples=15")
ax2.legend(fontsize=8, facecolor=PANEL, edgecolor=BORDER)
ax2.text(
    0.98,
    0.95,
    f"Noise: {n_noise:,}\n({noise_pct:.1f}%)",
    transform=ax2.transAxes,
    ha="right",
    va="top",
    fontsize=8,
    color=NOISE_EDGE,
)

fig.tight_layout()
save(fig, "fig_d02_size_distribution")

# ══════════════════════════════════════════════════════════════════════════════
# FIG D03 — eps sensitivity  (k and noise % across eps range)
# ══════════════════════════════════════════════════════════════════════════════
eps_vals = np.percentile(dists[:, -1], [50, 60, 70, 75, 80, 85, 88, 90, 92, 95])
eps_labels = [f"p{p}" for p in [50, 60, 70, 75, 80, 85, 88, 90, 92, 95]]
k_list, noise_list = [], []

print("  eps sensitivity sweep ...")
for ep in eps_vals:
    d = DBSCAN(eps=ep, min_samples=15, n_jobs=-1).fit_predict(X)
    k_list.append(len(set(d[d != -1])))
    noise_list.append((d == -1).mean() * 100)
    print(f"    eps={ep:.3f}  k={k_list[-1]}  noise={noise_list[-1]:.1f}%")

fig, axes = plt.subplots(1, 2, figsize=(14, 5), facecolor=BG)
fig.suptitle(
    "DBSCAN  ·  eps Sensitivity  (min_samples=15 fixed)", fontsize=12, color=TEXT, fontweight="bold"
)

ax1, ax2 = axes
ax1.plot(range(len(eps_vals)), k_list, "o-", color="#3B82F6", lw=2, ms=7)
ax1.axvline(
    list(eps_vals).index(eps_auto)
    if eps_auto in eps_vals
    else np.argmin(np.abs(eps_vals - eps_auto)),
    color="#F59E0B",
    ls="--",
    lw=1.4,
    label=f"chosen eps={eps_auto:.3f}",
)
ax1.set_xticks(range(len(eps_vals)))
ax1.set_xticklabels([f"{e:.2f}\n({l})" for e, l in zip(eps_vals, eps_labels)], fontsize=7)
ax1.set_title("Number of Clusters vs eps", color=TEXT, fontsize=10, fontweight="bold")
ax1.set_ylabel("Clusters (k)")
ax1.set_yscale("log")
ax1.legend(fontsize=8, facecolor=PANEL, edgecolor=BORDER)

ax2.plot(range(len(eps_vals)), noise_list, "o-", color="#EF4444", lw=2, ms=7)
ax2.axvline(
    list(eps_vals).index(eps_auto)
    if eps_auto in eps_vals
    else np.argmin(np.abs(eps_vals - eps_auto)),
    color="#F59E0B",
    ls="--",
    lw=1.4,
    label=f"chosen eps={eps_auto:.3f}",
)
ax2.set_xticks(range(len(eps_vals)))
ax2.set_xticklabels([f"{e:.2f}\n({l})" for e, l in zip(eps_vals, eps_labels)], fontsize=7)
ax2.set_title("Noise % vs eps", color=TEXT, fontsize=10, fontweight="bold")
ax2.set_ylabel("Noise %")
ax2.legend(fontsize=8, facecolor=PANEL, edgecolor=BORDER)

fig.tight_layout()
save(fig, "fig_d03_eps_sensitivity")

# ══════════════════════════════════════════════════════════════════════════════
# FIG D04 — Noise point profile vs non-noise
# ══════════════════════════════════════════════════════════════════════════════
PROFILE_FEATURES = {
    "lead_time": "Lead Time (days)",
    "fare_per_pax": "Fare per PAX ($)",
    "PAX Count": "PAX Count",
    "cabin_ord": "Cabin (0=Y,1=W,2=J)",
    "is_dom": "Is Domestic",
    "booking_month": "Booking Month",
}
PF_KEYS = [k for k in PROFILE_FEATURES if k in feature_names]

noise_df = X_raw.iloc[noise_mask.nonzero()[0]][PF_KEYS]
signal_df = X_raw.iloc[(~noise_mask).nonzero()[0]][PF_KEYS]
means = pd.DataFrame({"Noise": noise_df.mean(), "Non-Noise": signal_df.mean()})

fig, axes = plt.subplots(2, 3, figsize=(15, 8), facecolor=BG)
fig.suptitle(
    f"Noise Point Profile  ·  {n_noise:,} noise vs {(~noise_mask).sum():,} clustered",
    fontsize=12,
    color=TEXT,
    fontweight="bold",
)

for ax, key in zip(axes.flat, PF_KEYS):
    ax.hist(signal_df[key], bins=40, color="#3B82F6", alpha=0.55, density=True, label="Clustered")
    ax.hist(noise_df[key], bins=40, color=NOISE_EDGE, alpha=0.65, density=True, label="Noise")
    ax.axvline(signal_df[key].mean(), color="#3B82F6", ls="--", lw=1.3)
    ax.axvline(noise_df[key].mean(), color=NOISE_EDGE, ls="--", lw=1.3)
    ax.set_title(PROFILE_FEATURES[key], color=TEXT, fontsize=9, fontweight="bold")
    ax.set_ylabel("Density")
    ax.legend(fontsize=7.5, facecolor=PANEL, edgecolor=BORDER)

fig.tight_layout()
save(fig, "fig_d04_noise_profile")

# ══════════════════════════════════════════════════════════════════════════════
# FIG D05 — Top-15 cluster centroid heatmap
# ══════════════════════════════════════════════════════════════════════════════
KEY_FEAT = [
    "lead_time",
    "fare_per_pax",
    "PAX Count",
    "cabin_ord",
    "is_dom",
    "Region=Middle East",
    "Region=ASEAN",
    "Region=North America",
    "Region=MNL HUB",
    "Farebrand=Economy Supersaver",
    "Farebrand=Economy Saver",
    "Farebrand=Economy Flex",
    "Farebrand=Business Flex",
    "Itinerary Type=Beyonds (INT - DOM)",
    "Itinerary Type=Point to Point",
    "Ticketing Channel=Traditional Travel Agency",
    "Ticketing Channel=WEB/APP",
    "Ticketing Channel=TMC",
    "Ticketing Channel=Sea Crew",
]
KEY_FEAT = [f for f in KEY_FEAT if f in feature_names]

top_centroids = {}
for cid in top_ids:
    mask = labels == cid
    top_centroids[f"C{cid}\n(n={sizes[cid]:,})"] = X_raw[mask][KEY_FEAT].mean()

cent_df = pd.DataFrame(top_centroids).T
cent_norm = (cent_df - cent_df.min()) / (cent_df.max() - cent_df.min() + 1e-9)

pretty = [
    c.replace("Ticketing Channel=", "Chan:")
    .replace("Farebrand=", "FB:")
    .replace("Itinerary Type=", "Itin:")
    .replace("Region=", "Reg:")
    for c in KEY_FEAT
]

fig, ax = plt.subplots(figsize=(20, 7), facecolor=BG)
sns.heatmap(
    cent_norm,
    ax=ax,
    cmap="YlOrRd",
    annot=False,
    linewidths=0.4,
    linecolor=BG,
    xticklabels=pretty,
    yticklabels=cent_norm.index,
    cbar_kws={"shrink": 0.5, "label": "Normalised (0=low, 1=high)"},
)
ax.set_title(
    f"DBSCAN  ·  Top-{top_k} Cluster Centroids  (feature heatmap, normalised per feature)",
    fontsize=12,
    color=TEXT,
    pad=10,
    fontweight="bold",
)
plt.xticks(rotation=45, ha="right", fontsize=8)
plt.yticks(rotation=0, fontsize=8)
fig.tight_layout()
save(fig, "fig_d05_top_profiles")

# ══════════════════════════════════════════════════════════════════════════════
# 3. MAP 221 MICRO-CLUSTERS → 10 SEGMENTS via KMeans nearest centroid
# ══════════════════════════════════════════════════════════════════════════════
print("\nMapping DBSCAN micro-clusters → 10 segments via KMeans ...")
km10 = KMeans(n_clusters=10, n_init=20, max_iter=400, random_state=42)
km10.fit(X)
seg_labels_km = km10.labels_
km_centroids = km10.cluster_centers_  # (10, n_feat)

# Auto-name KMeans clusters (same heuristic as cluster_initial.py)
km_cents_raw = scaler.inverse_transform(km_centroids)
km_cents_df = pd.DataFrame(km_cents_raw, columns=feature_names)

SEG_NAMES = [
    "Corporate",
    "OFW/Migrant",
    "Balikbayan/VFR",
    "Premium Bleisure",
    "Last-Minute",
    "Pilgrimage",
    "Family",
    "Budget/Adventure",
    "Digital Nomad",
    "Unassigned",
]


def auto_label(row):
    lt = row["lead_time"]
    row["fare_per_pax"]
    pax = row["PAX Count"]
    cab = row["cabin_ord"]
    dom = row["is_dom"]
    tta = row.get("Ticketing Channel=Traditional Travel Agency", 0)
    web = row.get("Ticketing Channel=WEB/APP", 0)
    row.get("Ticketing Channel=TMC", 0)
    crew = row.get("Ticketing Channel=Sea Crew", 0)
    me = row.get("Region=Middle East", 0)
    asean = row.get("Region=ASEAN", 0)
    bey = row.get("Itinerary Type=Beyonds (INT - DOM)", 0)
    sav = row.get("Farebrand=Economy Saver", 0) + row.get("Farebrand=Economy Supersaver", 0)
    flex = row.get("Farebrand=Economy Flex", 0)
    if cab >= 1.8:
        return "Corporate"
    if crew > 0.3 or (me > 0.4 and tta > 0.35):
        return "OFW/Migrant"
    if bey > 0.4:
        return "Balikbayan/VFR"
    if cab >= 0.8:
        return "Premium Bleisure"
    if lt <= 3 and flex > 0.2:
        return "Last-Minute"
    if pax >= 3.5:
        return "Family"
    if me > 0.25 or tta > 0.55:
        return "OFW/Migrant"
    if bey > 0.2 and pax >= 2:
        return "Balikbayan/VFR"
    if web > 0.35 and asean > 0.15 and pax < 1.5:
        return "Digital Nomad"
    if sav > 0.5 and dom > 0.6:
        return "Budget/Adventure"
    return "Budget/Adventure"


km_seg_names = [auto_label(km_cents_df.iloc[i]) for i in range(10)]

# Compute centroid for each DBSCAN cluster → find nearest KMeans centroid → inherit segment name
db_centroids = {}
for cid in cluster_ids:
    mask = labels == cid
    db_centroids[cid] = X[mask].mean(axis=0)

db_cent_matrix = np.array([db_centroids[cid] for cid in cluster_ids])
nn_km = NearestNeighbors(n_neighbors=1).fit(km_centroids)
_, nn_idx = nn_km.kneighbors(db_cent_matrix)
db_to_seg = {cid: km_seg_names[nn_idx[i, 0]] for i, cid in enumerate(cluster_ids)}
# noise → "Unassigned"
db_to_seg[-1] = "Unassigned"

mapped_labels = np.array([db_to_seg.get(l, "Unassigned") for l in labels])
print("\nMapped segment distribution:")
seg_counts = pd.Series(mapped_labels).value_counts()
print(seg_counts.to_string())

# ══════════════════════════════════════════════════════════════════════════════
# FIG D06 — Segment mapping sankey-style bar
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(17, 6), facecolor=BG)
fig.suptitle(
    "DBSCAN Micro-Clusters  →  10 Segment Mapping  (nearest KMeans centroid)",
    fontsize=12,
    color=TEXT,
    fontweight="bold",
)

# Left: how many DBSCAN clusters map to each segment
ax1 = axes[0]
cluster_per_seg = pd.Series(db_to_seg).value_counts()
cluster_per_seg = cluster_per_seg.drop("Unassigned", errors="ignore")
colors_cs = [SEG_COLORS.get(s, "#60A5FA") for s in cluster_per_seg.index]
bars = ax1.bar(cluster_per_seg.index, cluster_per_seg.values, color=colors_cs, width=0.6)
for bar, val in zip(bars, cluster_per_seg.values):
    ax1.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 0.3,
        f"{val}",
        ha="center",
        va="bottom",
        fontsize=9,
        color=SUBTEXT,
    )
ax1.set_title("DBSCAN Clusters per Segment", color=TEXT, fontsize=10, fontweight="bold")
ax1.set_ylabel("# DBSCAN Micro-Clusters")
plt.setp(ax1.get_xticklabels(), rotation=30, ha="right", fontsize=8)

# Right: PNR count per mapped segment
ax2 = axes[1]
pnr_per_seg = seg_counts.drop("Unassigned", errors="ignore")
colors_ps = [SEG_COLORS.get(s, "#60A5FA") for s in pnr_per_seg.index]
bars2 = ax2.bar(pnr_per_seg.index, pnr_per_seg.values, color=colors_ps, width=0.6)
for bar, val in zip(bars2, pnr_per_seg.values):
    ax2.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + max(pnr_per_seg) * 0.01,
        f"{val:,}\n({val / len(labels) * 100:.1f}%)",
        ha="center",
        va="bottom",
        fontsize=7.5,
        color=SUBTEXT,
    )
unassigned_n = (mapped_labels == "Unassigned").sum()
ax2.set_title(
    f"PNRs per Mapped Segment  (noise=Unassigned: {unassigned_n:,})",
    color=TEXT,
    fontsize=10,
    fontweight="bold",
)
ax2.set_ylabel("PNR Count")
plt.setp(ax2.get_xticklabels(), rotation=30, ha="right", fontsize=8)

fig.tight_layout()
save(fig, "fig_d06_segment_mapping")

# ══════════════════════════════════════════════════════════════════════════════
# FIG D07 — PCA re-coloured by mapped segment
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(18, 8), facecolor=BG)
fig.suptitle(
    "DBSCAN Output  ·  PCA Coloured by Mapped Segment", fontsize=12, color=TEXT, fontweight="bold"
)

# Left: raw DBSCAN (top clusters coloured)
ax1 = axes[0]
micro_m = np.array([l not in top_ids and l != -1 for l in labels[plot_idx]])
ax1.scatter(X_pca[plot_idx][micro_m, 0], X_pca[plot_idx][micro_m, 1], c="#4B5563", s=5, alpha=0.2)
for cid in reversed(top_ids):
    mask = labels[plot_idx] == cid
    ax1.scatter(
        X_pca[plot_idx][mask, 0], X_pca[plot_idx][mask, 1], c=top_color[cid], s=7, alpha=0.5
    )
noise_p = noise_mask[plot_idx]
ax1.scatter(
    X_pca[plot_idx][noise_p, 0],
    X_pca[plot_idx][noise_p, 1],
    c=NOISE_C,
    edgecolors=NOISE_EDGE,
    linewidths=0.35,
    s=8,
    alpha=0.6,
)
ax1.set_title(f"Raw DBSCAN  ({n_clusters} clusters)", color=TEXT, fontsize=10, fontweight="bold")
ax1.set_xlabel(f"PC1 ({var_exp[0]:.1f}%)", fontsize=8)
ax1.set_ylabel(f"PC2 ({var_exp[1]:.1f}%)", fontsize=8)

# Right: mapped to 10 segments
ax2 = axes[1]
seg_order = list(SEG_COLORS.keys())
for seg in seg_order:
    seg_mask = mapped_labels[plot_idx] == seg
    if not seg_mask.any():
        continue
    alpha = 0.25 if seg == "Unassigned" else 0.55
    size = 6 if seg == "Unassigned" else 9
    ax2.scatter(
        X_pca[plot_idx][seg_mask, 0],
        X_pca[plot_idx][seg_mask, 1],
        c=SEG_COLORS.get(seg, "#60A5FA"),
        s=size,
        alpha=alpha,
        label=seg,
    )

ax2.set_title("Mapped to 10 Segments", color=TEXT, fontsize=10, fontweight="bold")
ax2.set_xlabel(f"PC1 ({var_exp[0]:.1f}%)", fontsize=8)
ax2.set_ylabel(f"PC2 ({var_exp[1]:.1f}%)", fontsize=8)
ax2.legend(
    fontsize=7.5,
    loc="upper right",
    framealpha=0.35,
    facecolor=PANEL,
    edgecolor=BORDER,
    ncol=2,
    markerscale=2,
)

fig.tight_layout()
save(fig, "fig_d07_segment_pca")

# ══════════════════════════════════════════════════════════════════════════════
# FIG D08 — KDE density map + noise overlay
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(16, 7), facecolor=BG)
fig.suptitle(
    "DBSCAN  ·  Density Map & Noise Distribution in PCA Space",
    fontsize=12,
    color=TEXT,
    fontweight="bold",
)

ax1, ax2 = axes

# KDE of all non-noise points
non_noise_pca = X_pca[~noise_mask]
sns.kdeplot(
    x=non_noise_pca[:, 0],
    y=non_noise_pca[:, 1],
    ax=ax1,
    cmap="Blues",
    fill=True,
    thresh=0.02,
    levels=15,
    alpha=0.85,
)
ax1.scatter(
    X_pca[plot_idx][noise_mask[plot_idx], 0],
    X_pca[plot_idx][noise_mask[plot_idx], 1],
    c=NOISE_EDGE,
    s=7,
    alpha=0.5,
    label="Noise points",
)
ax1.set_title("Density (KDE)  +  Noise Overlay", color=TEXT, fontsize=10, fontweight="bold")
ax1.set_xlabel(f"PC1 ({var_exp[0]:.1f}%)", fontsize=8)
ax1.set_ylabel(f"PC2 ({var_exp[1]:.1f}%)", fontsize=8)
ax1.legend(fontsize=8, facecolor=PANEL, edgecolor=BORDER)

# KDE of noise-only points
if noise_mask.sum() > 50:
    noise_pca = X_pca[noise_mask]
    sns.kdeplot(
        x=noise_pca[:, 0],
        y=noise_pca[:, 1],
        ax=ax2,
        cmap="Reds",
        fill=True,
        thresh=0.05,
        levels=12,
        alpha=0.8,
    )
ax2.set_title(f"Noise-Only KDE  ({n_noise:,} pts)", color=TEXT, fontsize=10, fontweight="bold")
ax2.set_xlabel(f"PC1 ({var_exp[0]:.1f}%)", fontsize=8)
ax2.set_ylabel(f"PC2 ({var_exp[1]:.1f}%)", fontsize=8)

fig.tight_layout()
save(fig, "fig_d08_density_kde")

# ══════════════════════════════════════════════════════════════════════════════
# CONSOLE SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print(f"DBSCAN SUMMARY  eps={eps_auto:.3f}  min_samples=15")
print("=" * 70)
print(f"Total records  : {len(labels):,}")
print(f"Clusters found : {n_clusters}")
print(f"Noise points   : {n_noise:,}  ({noise_pct:.2f}%)")
print(f"Largest cluster: {sizes.values[0]:,}  (C{sizes.index[0]})")
print(f"Smallest cluster: {sizes.values[-1]:,}  (C{sizes.index[-1]})")
print("\nTop-10 clusters:")
for cid, sz in sizes.head(10).items():
    print(f"  C{cid:<5}  n={sz:>6,}  ({sz / len(labels) * 100:.1f}%)  → {db_to_seg.get(cid, '?')}")
print(f"\nMapped segment distribution (all {n_clusters} clusters):")
print(seg_counts.to_string())
print("\nAll charts saved to dbscan_output/")
