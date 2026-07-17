"""Initial KMeans clustering — PAL customer segmentation.

Produces:
  cluster_output/fig_c01_elbow.png         — WCSS elbow (k=2–15)
  cluster_output/fig_c02_cluster_sizes.png — cluster size bar
  cluster_output/fig_c03_centroid_heatmap.png — normalised centroid feature matrix
  cluster_output/fig_c04_pca_scatter.png   — PCA-2D scatter coloured by cluster
  cluster_output/fig_c05_radar.png         — radar fingerprints for each centroid
  cluster_output/fig_c06_centroid_profiles.png — per-cluster top-feature bar strips
"""

import warnings

warnings.filterwarnings("ignore")

from math import pi
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from pal_colors import SEG_PALETTE as CLUSTER_PALETTE

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "cluster_output"
OUTPUT.mkdir(parents=True, exist_ok=True)

# ── theme ──────────────────────────────────────────────────────────────────────
BG = "#111827"
PANEL = "#1F2937"
BORDER = "#374151"
TEXT = "#F9FAFB"
SUBTEXT = "#9CA3AF"
ACCENT = "#3B82F6"

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
    print(f"  saved → cluster_output/{name}.png")


# ── load & engineer ────────────────────────────────────────────────────────────
df = pd.read_csv(ROOT / "data" / "raw" / "sample-features.csv")
df["Average Fare"] = df["Average Fare"].str.replace("$", "", regex=False).astype(float)
df["PNRCreationDate"] = pd.to_datetime(df["PNRCreationDate"], dayfirst=True, errors="coerce")
df["Flight Date"] = pd.to_datetime(df["Flight Date"], dayfirst=True, errors="coerce")
df["lead_time"] = (df["Flight Date"] - df["PNRCreationDate"]).dt.days
df["fare_per_pax"] = df["Average Fare"] / df["PAX Count"]
df["booking_month"] = df["PNRCreationDate"].dt.month

# drop rows missing lead_time (tiny fraction with null PNRCreationDate)
df = df.dropna(subset=["lead_time"]).copy()

# ── feature matrix ─────────────────────────────────────────────────────────────
# Ordinal encode cabin: Y=0, W=1, J=2
cabin_map = {"Y": 0, "W": 1, "J": 2}
df["cabin_ord"] = df["Cabin"].map(cabin_map).fillna(0)

# Binary
df["is_dom"] = (df["Entity"] == "DOM").astype(int)

# One-hot categoricals
cat_cols = ["Region", "Farebrand", "Itinerary Type", "Ticketing Channel"]
df_enc = pd.get_dummies(df[cat_cols].fillna("Unknown"), columns=cat_cols, prefix_sep="=", dtype=int)

# Numeric features
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
X_scaled = scaler.fit_transform(X_raw)
feature_names = X_raw.columns.tolist()

print(f"Feature matrix: {X_scaled.shape[0]} rows × {X_scaled.shape[1]} features")

# ── elbow + silhouette ─────────────────────────────────────────────────────────
print("Running elbow sweep k=2..15 ...")
ks = list(range(2, 16))
inertia = []
sil = []
for k in ks:
    km = KMeans(n_clusters=k, n_init=10, random_state=42)
    labels = km.fit_predict(X_scaled)
    inertia.append(km.inertia_)
    sil.append(silhouette_score(X_scaled, labels, sample_size=5000, random_state=42))
    print(f"  k={k}  inertia={km.inertia_:,.0f}  sil={sil[-1]:.4f}")

# ── FIG C01 — elbow ────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 4.5), facecolor=BG)
fig.suptitle(
    "Elbow Curve & Silhouette Score  ·  PAL Clustering",
    fontsize=13,
    color=TEXT,
    y=1.01,
    fontweight="bold",
)

ax1, ax2 = axes
ax1.plot(ks, inertia, "o-", color=ACCENT, lw=2, ms=6)
ax1.set(title="WCSS (Inertia)", xlabel="k clusters", ylabel="Inertia")
ax1.axvline(10, color="#F59E0B", ls="--", lw=1.4, label="k=10 chosen")
ax1.legend(fontsize=8)
ax1.title.set_color(TEXT)

ax2.plot(ks, sil, "o-", color="#10B981", lw=2, ms=6)
ax2.set(title="Silhouette Score", xlabel="k clusters", ylabel="Score (higher=better)")
ax2.axvline(10, color="#F59E0B", ls="--", lw=1.4, label="k=10 chosen")
ax2.legend(fontsize=8)
ax2.title.set_color(TEXT)

fig.tight_layout()
save(fig, "fig_c01_elbow")

# ── fit final k=10 model ───────────────────────────────────────────────────────
K = 10
print(f"\nFitting KMeans k={K} (final model)...")
km_final = KMeans(n_clusters=K, n_init=20, max_iter=400, random_state=42)
cluster_labels = km_final.fit_predict(X_scaled)
df["cluster"] = cluster_labels

centroids_scaled = km_final.cluster_centers_  # shape (K, n_features)
centroids_raw = scaler.inverse_transform(centroids_scaled)  # back to original scale
centroids_df = pd.DataFrame(centroids_raw, columns=feature_names)

print("\nCluster sizes:")
sizes = df["cluster"].value_counts().sort_index()
for c, n in sizes.items():
    print(f"  C{c}: {n:,}  ({n / len(df) * 100:.1f}%)")


# ── auto-label clusters from centroid signature ────────────────────────────────
def auto_label(row):
    """Heuristic mapping from centroid values to proposed segment names."""
    lt = row["lead_time"]
    fp = row["fare_per_pax"]
    pax = row["PAX Count"]
    cab = row["cabin_ord"]  # 0=Y, 1=W, 2=J
    dom = row["is_dom"]
    chan_tta = row.get("Ticketing Channel=Traditional Travel Agency", 0)
    chan_web = row.get("Ticketing Channel=WEB/APP", 0)
    chan_tmc = row.get("Ticketing Channel=TMC", 0)
    chan_crew = row.get("Ticketing Channel=Sea Crew", 0)
    reg_me = row.get("Region=Middle East", 0)
    reg_asean = row.get("Region=ASEAN", 0)
    reg_aus = row.get("Region=Australasia", 0)
    itin_bey = row.get("Itinerary Type=Beyonds (INT - DOM)", 0)
    fb_saver = row.get("Farebrand=Economy Saver", 0) + row.get("Farebrand=Economy Supersaver", 0)
    fb_flex = row.get("Farebrand=Economy Flex", 0)

    if cab >= 1.8:
        return "Corporate"
    if chan_crew > 0.3 or (reg_me > 0.4 and chan_tta > 0.35):
        return "OFW/Migrant"
    if itin_bey > 0.4:
        return "Balikbayan/VFR"
    if cab >= 0.8:
        return "Premium Bleisure"
    if (chan_tmc > 0.1 or fp > 300) and lt < 15 and pax < 2:
        return "Corporate"
    if lt <= 3 and fb_flex > 0.2:
        return "Last-Minute"
    if pax >= 3.5:
        return "Pilgrimage / Family"
    if reg_me > 0.25 or chan_tta > 0.55:
        return "OFW/Migrant"
    if itin_bey > 0.2 and pax >= 2:
        return "Balikbayan/VFR"
    if chan_web > 0.35 and reg_asean > 0.15 and pax < 1.5:
        return "Digital Nomad"
    if fb_saver > 0.5 and dom > 0.6:
        return "Budget/Adventure"
    if reg_aus > 0.15 or (fp > 180 and lt > 14):
        return "Premium Bleisure"
    return "Budget/Adventure"


centroid_labels = [auto_label(centroids_df.iloc[i]) for i in range(K)]
df["cluster_label"] = df["cluster"].map(dict(enumerate(centroid_labels)))

print("\nCluster auto-labels:")
for i, lbl in enumerate(centroid_labels):
    print(f"  C{i}: {lbl}")

# ── FIG C02 — cluster sizes ────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 4.5), facecolor=BG)
counts = df["cluster"].value_counts().sort_index()
labels_for_bar = [f"C{i}\n{centroid_labels[i]}" for i in counts.index]
bars = ax.bar(
    labels_for_bar, counts.values, color=[CLUSTER_PALETTE[i] for i in counts.index], width=0.65
)
for bar, val in zip(bars, counts.values):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 50,
        f"{val:,}\n({val / len(df) * 100:.1f}%)",
        ha="center",
        va="bottom",
        fontsize=8,
        color=SUBTEXT,
    )
ax.set(title="Initial Cluster Sizes  (KMeans k=10)", xlabel="Cluster", ylabel="PNR Count")
ax.title.set_color(TEXT)
fig.tight_layout()
save(fig, "fig_c02_cluster_sizes")

# ── FIG C03 — centroid heatmap ─────────────────────────────────────────────────
# Select interpretable features only (not every dummy — pick most informative)
KEY_FEATURES = [
    "lead_time",
    "fare_per_pax",
    "PAX Count",
    "cabin_ord",
    "is_dom",
    "booking_month",
    "Region=Middle East",
    "Region=ASEAN",
    "Region=Australasia",
    "Region=North America",
    "Region=Japan",
    "Region=MNL HUB",
    "Region=CEB HUB",
    "Farebrand=Economy Supersaver",
    "Farebrand=Economy Saver",
    "Farebrand=Economy Flex",
    "Farebrand=Economy Value",
    "Farebrand=Business Flex",
    "Itinerary Type=Beyonds (INT - DOM)",
    "Itinerary Type=Point to Point",
    "Itinerary Type=Round Trip",
    "Ticketing Channel=Traditional Travel Agency",
    "Ticketing Channel=WEB/APP",
    "Ticketing Channel=TMC",
    "Ticketing Channel=Sea Crew",
    "Ticketing Channel=OTA",
]
KEY_FEATURES = [f for f in KEY_FEATURES if f in feature_names]

# Normalise each feature across clusters to [0,1] for display contrast
heat_raw = centroids_df[KEY_FEATURES].copy()
heat_norm = (heat_raw - heat_raw.min()) / (heat_raw.max() - heat_raw.min() + 1e-9)
heat_norm.index = [f"C{i}  {centroid_labels[i]}" for i in range(K)]

pretty_cols = [
    c.replace("Ticketing Channel=", "Chan: ")
    .replace("Farebrand=", "FB: ")
    .replace("Itinerary Type=", "Itin: ")
    .replace("Region=", "Reg: ")
    for c in KEY_FEATURES
]

fig, ax = plt.subplots(figsize=(18, 6), facecolor=BG)
sns.heatmap(
    heat_norm,
    ax=ax,
    cmap="YlOrRd",
    annot=False,
    linewidths=0.4,
    linecolor=BG,
    xticklabels=pretty_cols,
    yticklabels=heat_norm.index,
    cbar_kws={"shrink": 0.6, "label": "Normalised Value (0=low, 1=high)"},
)
ax.set_title(
    "Initial KMeans Centroids  ·  Feature Heatmap  (normalised per feature)",
    fontsize=12,
    color=TEXT,
    pad=10,
    fontweight="bold",
)
ax.set_xlabel("")
ax.set_ylabel("")
plt.xticks(rotation=45, ha="right", fontsize=8)
plt.yticks(rotation=0, fontsize=9)
ax.tick_params(colors=SUBTEXT)
fig.tight_layout()
save(fig, "fig_c03_centroid_heatmap")

# ── FIG C04 — PCA scatter ─────────────────────────────────────────────────────
print("Running PCA ...")
pca = PCA(n_components=2, random_state=42)
X_pca = pca.fit_transform(X_scaled)
centroids_pca = pca.transform(centroids_scaled)
var_exp = pca.explained_variance_ratio_ * 100

# sample for speed
sample_idx = np.random.default_rng(42).choice(len(X_pca), size=min(8000, len(X_pca)), replace=False)

fig, ax = plt.subplots(figsize=(12, 8), facecolor=BG)
for ci in range(K):
    mask = cluster_labels[sample_idx] == ci
    ax.scatter(
        X_pca[sample_idx][mask, 0],
        X_pca[sample_idx][mask, 1],
        c=CLUSTER_PALETTE[ci],
        alpha=0.35,
        s=8,
        label=f"C{ci} {centroid_labels[ci]}",
    )

# centroid markers
for ci in range(K):
    ax.scatter(
        centroids_pca[ci, 0],
        centroids_pca[ci, 1],
        c=CLUSTER_PALETTE[ci],
        s=220,
        marker="*",
        edgecolors="white",
        linewidths=0.8,
        zorder=10,
    )
    ax.annotate(
        f"C{ci}",
        (centroids_pca[ci, 0], centroids_pca[ci, 1]),
        textcoords="offset points",
        xytext=(6, 4),
        fontsize=8,
        color="white",
        fontweight="bold",
    )

ax.set(
    title=f"PCA Projection  ·  KMeans k=10  (PC1={var_exp[0]:.1f}%  PC2={var_exp[1]:.1f}%)",
    xlabel=f"PC1  ({var_exp[0]:.1f}% variance)",
    ylabel=f"PC2  ({var_exp[1]:.1f}% variance)",
)
ax.title.set_color(TEXT)
ax.legend(
    fontsize=7.5, loc="upper right", framealpha=0.3, facecolor=PANEL, edgecolor=BORDER, ncol=2
)
fig.tight_layout()
save(fig, "fig_c04_pca_scatter")

# ── FIG C05 — radar fingerprints ──────────────────────────────────────────────
RADAR_FEATURES = [
    "lead_time",
    "fare_per_pax",
    "PAX Count",
    "cabin_ord",
    "Region=Middle East",
    "Itinerary Type=Beyonds (INT - DOM)",
    "Ticketing Channel=Traditional Travel Agency",
    "Ticketing Channel=WEB/APP",
    "Farebrand=Economy Supersaver",
    "Farebrand=Economy Flex",
]
RADAR_FEATURES = [f for f in RADAR_FEATURES if f in feature_names]
N_RADAR = len(RADAR_FEATURES)
radar_labels = [
    "Lead Time",
    "Fare/PAX",
    "PAX Count",
    "Cabin Class",
    "Middle East",
    "Beyond Itin",
    "TTA Chan",
    "WEB Chan",
    "Eco Supersaver",
    "Eco Flex",
][:N_RADAR]

# Normalise centroids on these features
radar_raw = centroids_df[RADAR_FEATURES].values.astype(float)
radar_norm = (radar_raw - radar_raw.min(axis=0)) / (
    radar_raw.max(axis=0) - radar_raw.min(axis=0) + 1e-9
)

angles = np.linspace(0, 2 * pi, N_RADAR, endpoint=False).tolist()
angles += angles[:1]

rows, cols = 2, 5
fig, axes = plt.subplots(rows, cols, figsize=(18, 8), subplot_kw={"polar": True}, facecolor=BG)
fig.suptitle(
    "Cluster Centroid Radar Fingerprints  ·  KMeans k=10",
    fontsize=13,
    color=TEXT,
    y=1.01,
    fontweight="bold",
)

for i, ax in enumerate(axes.flat):
    ax.set_facecolor(PANEL)
    if i >= K:
        ax.set_visible(False)
        continue
    vals = radar_norm[i].tolist()
    vals += vals[:1]
    ax.plot(angles, vals, color=CLUSTER_PALETTE[i], lw=1.8)
    ax.fill(angles, vals, color=CLUSTER_PALETTE[i], alpha=0.28)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(radar_labels, size=6.5, color=SUBTEXT)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75])
    ax.set_yticklabels(["", "", ""], size=6)
    ax.tick_params(colors=SUBTEXT)
    ax.set_title(
        f"C{i}  {centroid_labels[i]}",
        fontsize=8.5,
        color=CLUSTER_PALETTE[i],
        pad=8,
        fontweight="bold",
    )
    ax.spines["polar"].set_color(BORDER)
    ax.grid(color=BORDER, alpha=0.6)

fig.tight_layout()
save(fig, "fig_c05_radar")

# ── FIG C06 — per-cluster top feature strips ───────────────────────────────────
PROFILE_FEATURES = {
    "lead_time": "Lead Time (days)",
    "fare_per_pax": "Fare per PAX ($)",
    "PAX Count": "PAX Count",
    "cabin_ord": "Cabin (0=Y,1=W,2=J)",
    "is_dom": "Domestic (%)",
    "Region=Middle East": "Middle East route",
    "Region=ASEAN": "ASEAN route",
    "Region=North America": "North America route",
    "Itinerary Type=Beyonds (INT - DOM)": "Beyond Itin",
    "Ticketing Channel=Traditional Travel Agency": "TTA Channel",
    "Ticketing Channel=WEB/APP": "WEB/APP Channel",
    "Ticketing Channel=Sea Crew": "Sea Crew Channel",
    "Ticketing Channel=TMC": "TMC Channel",
    "Farebrand=Economy Supersaver": "Eco Supersaver",
    "Farebrand=Economy Flex": "Eco Flex",
}
PF = {k: v for k, v in PROFILE_FEATURES.items() if k in feature_names}
pf_keys = list(PF.keys())
pf_lbls = list(PF.values())

centroid_profile = centroids_df[pf_keys].copy()
profile_norm = (centroid_profile - centroid_profile.min()) / (
    centroid_profile.max() - centroid_profile.min() + 1e-9
)

fig, axes = plt.subplots(K, 1, figsize=(16, K * 1.3), facecolor=BG, sharex=True)
fig.suptitle(
    "Centroid Feature Profiles  ·  KMeans k=10  (bar = relative prominence)",
    fontsize=12,
    color=TEXT,
    y=1.005,
    fontweight="bold",
)

for i, ax in enumerate(axes):
    ax.set_facecolor(PANEL)
    vals = profile_norm.iloc[i].values
    colors = [CLUSTER_PALETTE[i] if v >= 0.55 else BORDER for v in vals]
    bars = ax.barh(pf_lbls, vals, color=colors, height=0.55)
    ax.set_xlim(0, 1)
    ax.set_ylabel(
        f"C{i}  {centroid_labels[i]}",
        rotation=0,
        labelpad=130,
        fontsize=8,
        color=CLUSTER_PALETTE[i],
        fontweight="bold",
        va="center",
    )
    ax.set_yticks([])
    ax.tick_params(left=False, bottom=False)
    ax.spines[:].set_visible(False)
    # annotate raw centroid values on top bars
    for bar, key, val in zip(bars, pf_keys, centroid_profile.iloc[i]):
        if profile_norm.iloc[i][key] >= 0.55:
            raw_disp = f"{val:.1f}" if isinstance(val, float) else str(int(val))
            ax.text(
                profile_norm.iloc[i][key] + 0.01,
                bar.get_y() + bar.get_height() / 2,
                raw_disp,
                va="center",
                fontsize=6.5,
                color=TEXT,
            )

# shared x-axis label
axes[-1].set_xticks([0, 0.25, 0.5, 0.75, 1.0])
axes[-1].set_xticklabels(["0%", "25%", "50%", "75%", "100%"], fontsize=7, color=SUBTEXT)
# feature labels on top
ax0 = axes[0]
ax0.set_xticks(np.linspace(0, 1, len(pf_lbls)))

fig.tight_layout(rect=[0.08, 0, 1, 1])
save(fig, "fig_c06_centroid_profiles")

# ── print centroid summary table ───────────────────────────────────────────────
print("\n" + "=" * 72)
print("CENTROID SUMMARY  (raw scale, key features)")
print("=" * 72)
summary_keys = [
    "lead_time",
    "fare_per_pax",
    "PAX Count",
    "cabin_ord",
    "is_dom",
    "Region=Middle East",
    "Itinerary Type=Beyonds (INT - DOM)",
    "Ticketing Channel=Traditional Travel Agency",
    "Ticketing Channel=WEB/APP",
]
summary_keys = [k for k in summary_keys if k in feature_names]
summary = centroids_df[summary_keys].copy()
summary.index = [f"C{i} {centroid_labels[i]}" for i in range(K)]
summary.columns = ["LT(d)", "Fare/PAX", "PAX", "Cabin", "DOM%", "ME%", "Beyond%", "TTA%", "WEB%"][
    : len(summary_keys)
]
print(summary.round(2).to_string())
print("\nAll charts saved to cluster_output/")
