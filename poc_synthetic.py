"""
poc_synthetic.py — PAL Customer Segmentation Mini PoC
Full 8-stage pipeline on synthetic airline passenger data.
Outputs 8 slide-ready figures to poc_output/.
"""

import os, warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import euclidean_distances
import hdbscan

warnings.filterwarnings("ignore")

import sys
sys.path.insert(0, ".")
from pal_colors import SEG_COLORS, SEG_ORDER

OUTPUT_DIR = "poc_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Segment config ─────────────────────────────────────────────────────────
PENALTY = {
    "Corporate":         10,
    "Mabuhay Loyalist":   8,
    "OFW/Migrant":        5,
    "Premium Bleisure":   4,
    "Pilgrimage":         3,
    "Balikbayan/VFR":     2,
    "Family":             2,
    "Digital Nomad":      2,
    "Last-Minute":        1,
    "Budget/Adventure":   1,
}
SEGMENTS = list(PENALTY.keys())

# Revenue loss per misclassified record (₱) — Corporate anchored to BR-28 (₱40,000)
REV_LOSS = {
    "Corporate": 40_000, "Mabuhay Loyalist": 32_000, "OFW/Migrant": 20_000,
    "Premium Bleisure": 16_000, "Pilgrimage": 12_000, "Balikbayan/VFR": 8_000,
    "Family": 8_000, "Digital Nomad": 8_000, "Last-Minute": 4_000, "Budget/Adventure": 4_000,
}

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150,
    "font.family": "sans-serif", "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
})

def save(fig, name):
    path = os.path.join(OUTPUT_DIR, name)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved → {path}")


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 1 — Load & Clean
# ══════════════════════════════════════════════════════════════════════════════
print("\nStage 1 — Loading data...")
df = pd.read_csv("synthetic_flight_passenger_data.csv")
df["Departure_Time"] = pd.to_datetime(df["Departure_Time"])
df = df[df["Price_USD"] > 0].reset_index(drop=True)
print(f"  {len(df):,} records after cleaning")


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 2 — Feature Engineering
# ══════════════════════════════════════════════════════════════════════════════
print("\nStage 2 — Engineering features...")

df["lead_time"]   = df["Booking_Days_In_Advance"]
df["hour_of_day"] = df["Departure_Time"].dt.hour
df["is_early_am"] = (df["hour_of_day"] < 8).astype(int)
df["price_log"]   = np.log1p(df["Price_USD"])

cabin_map   = {"Economy": 0, "Premium Economy": 1, "Business": 2, "First": 3}
loyalty_map = {"Silver": 1, "Gold": 2, "Platinum": 3}
income_map  = {"Low": 0, "Medium": 1, "High": 2}

df["cabin_ord"]   = df["Seat_Class"].map(cabin_map)
df["loyalty_ord"] = df["Frequent_Flyer_Status"].map(loyalty_map).fillna(0)
df["income_ord"]  = df["Income_Level"].map(income_map)

ohe = pd.get_dummies(df[["Travel_Purpose", "Check_in_Method", "Airline", "Seat_Selected"]])

NUM_COLS = [
    "lead_time", "hour_of_day", "is_early_am", "price_log",
    "cabin_ord", "loyalty_ord", "income_ord", "Age",
    "Bags_Checked", "Flight_Duration_Minutes", "Distance_Miles",
    "Flight_Satisfaction_Score", "Delay_Minutes", "No_Show", "Weather_Impact",
]
X_raw = pd.concat([df[NUM_COLS], ohe], axis=1).fillna(0)

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_raw)
print(f"  Feature matrix: {X_scaled.shape[0]:,} rows × {X_scaled.shape[1]} features")


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 3 — Proxy Label Waterfall
# ══════════════════════════════════════════════════════════════════════════════
print("\nStage 3 — Proxy label waterfall...")
df["proxy_segment"] = "Unassigned"

rules = [
    # (priority_label, condition)
    ("Budget/Adventure",
     (df["Seat_Class"] == "Economy") & (df["Income_Level"] == "Low") & (df["Travel_Purpose"] == "Leisure")),
    ("Last-Minute",
     (df["lead_time"] <= 3) | (df["Travel_Purpose"] == "Emergency")),
    ("Digital Nomad",
     (df["Travel_Purpose"] == "Leisure") &
     (df["Check_in_Method"].isin(["Mobile App", "Online"])) &
     (df["Age"] < 40) & (df["Income_Level"] != "Low")),
    ("Family",
     (df["Travel_Purpose"] == "Family") & (df["Bags_Checked"] >= 2) & (df["Income_Level"] == "Medium")),
    ("Pilgrimage",
     (df["Age"] >= 55) & (df["Income_Level"] == "Low") &
     (df["Bags_Checked"] >= 2) & (df["Travel_Purpose"] == "Leisure")),
    ("Balikbayan/VFR",
     (df["Travel_Purpose"] == "Family") & (df["Bags_Checked"] >= 2) & (df["Income_Level"] == "High")),
    ("OFW/Migrant",
     (df["Seat_Class"] == "Economy") & (df["Bags_Checked"] >= 2) &
     (df["Income_Level"] == "Low") & (df["Travel_Purpose"] != "Business")),
    ("Premium Bleisure",
     (df["Seat_Class"].isin(["Premium Economy", "Business"])) &
     (df["Travel_Purpose"] == "Leisure") & (df["Income_Level"] == "High")),
    ("Mabuhay Loyalist",
     (df["loyalty_ord"] == 3) & (df["Travel_Purpose"].isin(["Leisure", "Family", "Emergency"]))),
    ("Corporate",
     (df["Travel_Purpose"] == "Business") & (df["Seat_Class"].isin(["Business", "First"]))),
]

for label, mask in rules:
    df.loc[mask, "proxy_segment"] = label

before_nl = df["proxy_segment"].value_counts()
print(f"  Pre-NL: {(df['proxy_segment'] != 'Unassigned').sum():,} labelled "
      f"({(df['proxy_segment'] != 'Unassigned').mean()*100:.1f}%)")


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 4 — Negative Learning (impossibility filters)
# ══════════════════════════════════════════════════════════════════════════════
print("\nStage 4 — Negative learning rules...")

nl_rules = [
    # Corporate booked 60+ days out in economy with no loyalty card → impossible
    (df["proxy_segment"] == "Corporate") &
    (df["lead_time"] > 60) & (df["cabin_ord"] == 0) & (df["loyalty_ord"] == 0),
    # Mabuhay Loyalist with no loyalty card on file → impossible
    (df["proxy_segment"] == "Mabuhay Loyalist") & (df["loyalty_ord"] == 0),
    # OFW/Migrant with zero bags → contradictory
    (df["proxy_segment"] == "OFW/Migrant") & (df["Bags_Checked"] == 0),
    # Premium Bleisure with Low income → contradictory
    (df["proxy_segment"] == "Premium Bleisure") & (df["income_ord"] == 0),
]

nl_total = 0
for mask in nl_rules:
    df.loc[mask, "proxy_segment"] = "Unassigned"
    nl_total += mask.sum()

after_nl = df["proxy_segment"].value_counts()
labelled_pct = (df["proxy_segment"] != "Unassigned").mean() * 100
print(f"  NL invalidated {nl_total:,} assignments → {labelled_pct:.1f}% still labelled")


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 5 — Penalty-Weighted Feature Scaling
# ══════════════════════════════════════════════════════════════════════════════
print("\nStage 5 — Penalty-weighted feature scaling...")
X_df = pd.DataFrame(X_scaled, columns=X_raw.columns)
total_pen = sum(PENALTY.values())
weights = np.ones(X_df.shape[1])

for seg, pw in PENALTY.items():
    mask = df["proxy_segment"] == seg
    if mask.sum() < 10:
        continue
    centroid = X_df[mask].mean().values
    weights += (pw / total_pen) * np.abs(centroid)

weights /= weights.mean()
X_weighted = X_df.values * weights

top5 = X_raw.columns[np.argsort(weights)[-5:][::-1]].tolist()
print(f"  Top 5 penalty-weighted features: {top5}")


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 6 — HDBSCAN Clustering
# ══════════════════════════════════════════════════════════════════════════════
print("\nStage 6 — HDBSCAN clustering...")
clusterer = hdbscan.HDBSCAN(min_cluster_size=80, min_samples=10, metric="euclidean")
cluster_labels = clusterer.fit_predict(X_weighted)

n_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
noise_pct  = (cluster_labels == -1).mean() * 100
print(f"  {n_clusters} micro-clusters | {noise_pct:.1f}% noise records")


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 7 — Cluster → Segment Mapping + Noise Auto-Assignment
# ══════════════════════════════════════════════════════════════════════════════
print("\nStage 7 — Cluster → segment mapping...")

seg_centroids = {}
for seg in SEGMENTS:
    mask = df["proxy_segment"] == seg
    if mask.sum() >= 10:
        seg_centroids[seg] = (X_df[mask].values * weights).mean(axis=0)

seg_names   = list(seg_centroids.keys())
seg_mat     = np.vstack(list(seg_centroids.values()))

def nearest_seg(vec):
    dists = euclidean_distances(vec.reshape(1, -1), seg_mat)[0]
    return seg_names[int(np.argmin(dists))]

# Map each micro-cluster
cluster_to_seg = {}
for c in set(cluster_labels):
    if c == -1:
        continue
    c_vec = (X_df[cluster_labels == c].values * weights).mean(axis=0)
    cluster_to_seg[c] = nearest_seg(c_vec)

# Assign noise records individually
model_segs = []
for i, c in enumerate(cluster_labels):
    if c != -1:
        model_segs.append(cluster_to_seg[c])
    else:
        model_segs.append(nearest_seg(X_df.iloc[i].values * weights))

df["model_segment"] = model_segs

dist_final = df["model_segment"].value_counts()
print("  Final segment distribution:")
for seg in SEGMENTS:
    n = (df["model_segment"] == seg).sum()
    print(f"    {seg:<22} {n:>5,}  ({n/len(df)*100:.1f}%)")


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 8 — Validate: Asymmetric Cost Matrix
# ══════════════════════════════════════════════════════════════════════════════
print("\nStage 8 — Asymmetric cost matrix validation...")

labelled_mask = df["proxy_segment"] != "Unassigned"
df_val = df[labelled_mask].copy()

correct_mask = df_val["proxy_segment"] == df_val["model_segment"]
raw_accuracy = correct_mask.mean()

# Weighted cost: penalty of TRUE segment for each misclassified record
misclassified = df_val[~correct_mask]
weighted_cost = misclassified["proxy_segment"].map(PENALTY).sum()
total_records = len(df_val)
cost_per_record = weighted_cost / total_records

# Per-segment recall
seg_recall = {}
for seg in SEGMENTS:
    true_mask = df_val["proxy_segment"] == seg
    if true_mask.sum() == 0:
        seg_recall[seg] = None
        continue
    correct = (df_val.loc[true_mask, "model_segment"] == seg).sum()
    seg_recall[seg] = correct / true_mask.sum()

print(f"  Raw accuracy (labelled records):  {raw_accuracy:.1%}")
print(f"  Total weighted misclassif. cost:  {weighted_cost:,}")
print(f"  Weighted cost per record:         {cost_per_record:.4f}")
print("\n  Per-segment recall:")
for seg, rec in seg_recall.items():
    flag = " ★" if PENALTY[seg] >= 5 else ""
    val  = f"{rec:.1%}" if rec is not None else "N/A (no proxy seed)"
    print(f"    {seg:<22} {val}{flag}")


# ══════════════════════════════════════════════════════════════════════════════
# FIGURES
# ══════════════════════════════════════════════════════════════════════════════
print("\nGenerating figures...")

# ── Fig 01: Segment Distribution ──────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5))
seg_counts = df["model_segment"].value_counts()
ordered    = [s for s in SEGMENTS if s in seg_counts.index]
counts     = [seg_counts[s] for s in ordered]
colors     = [SEG_COLORS[s] for s in ordered]
pct        = [c / len(df) * 100 for c in counts]

bars = ax.barh(ordered[::-1], counts[::-1], color=colors[::-1], edgecolor="white", height=0.7)
for bar, p, c in zip(bars, pct[::-1], counts[::-1]):
    ax.text(bar.get_width() + 30, bar.get_y() + bar.get_height() / 2,
            f"{c:,}  ({p:.1f}%)", va="center", fontsize=9)

ax.set_xlabel("Number of Passengers", fontsize=10)
ax.set_title("PAL Customer Segment Distribution\n(ML-Assigned — Synthetic PoC Data)", fontsize=12, fontweight="bold")
ax.set_xlim(0, max(counts) * 1.25)
ax.tick_params(axis="y", labelsize=9)
fig.tight_layout()
save(fig, "fig01_segment_distribution.png")

# ── Fig 02: PCA Scatter ────────────────────────────────────────────────────
print("  Computing PCA...")
pca   = PCA(n_components=2, random_state=42)
X_pca = pca.fit_transform(X_weighted)

fig, ax = plt.subplots(figsize=(10, 7))
for seg in SEGMENTS:
    mask = df["model_segment"] == seg
    if mask.sum() == 0:
        continue
    ax.scatter(X_pca[mask, 0], X_pca[mask, 1],
               c=SEG_COLORS[seg], label=seg, alpha=0.35, s=10, linewidths=0)

ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% variance)", fontsize=10)
ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}% variance)", fontsize=10)
ax.set_title("Segment Cluster Separation — Penalty-Weighted PCA\n(Synthetic PoC Data)", fontsize=12, fontweight="bold")
legend = ax.legend(loc="upper right", fontsize=8, markerscale=2, framealpha=0.9)
fig.tight_layout()
save(fig, "fig02_pca_scatter.png")

# ── Fig 03: Negative Learning Impact ──────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
for ax, (data, title) in zip(axes, [
    (before_nl, "Before Negative Learning"),
    (after_nl,  "After Negative Learning"),
]):
    ordered_segs = [s for s in (SEGMENTS + ["Unassigned"]) if s in data.index]
    vals   = [data[s] for s in ordered_segs]
    clrs   = [SEG_COLORS.get(s, "#4B5563") for s in ordered_segs]
    bars   = ax.bar(range(len(ordered_segs)), vals, color=clrs, edgecolor="white")
    ax.set_xticks(range(len(ordered_segs)))
    ax.set_xticklabels(ordered_segs, rotation=40, ha="right", fontsize=8)
    ax.set_ylabel("Record Count")
    ax.set_title(title, fontsize=11, fontweight="bold")
    for bar, v in zip(bars, vals):
        if v > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 10,
                    str(v), ha="center", va="bottom", fontsize=7)

fig.suptitle("Negative Learning: Impossible Assignment Removal", fontsize=13, fontweight="bold")
fig.tight_layout()
save(fig, "fig03_negative_learning_impact.png")

# ── Fig 04: Asymmetric Penalty Weight Matrix ───────────────────────────────
pen_segs = SEGMENTS
pen_mat  = np.zeros((len(pen_segs), len(pen_segs)))
for i, true_seg in enumerate(pen_segs):
    for j, pred_seg in enumerate(pen_segs):
        if i != j:
            pen_mat[i, j] = PENALTY[true_seg]

fig, ax = plt.subplots(figsize=(11, 8))
im = ax.imshow(pen_mat, cmap="Reds", aspect="auto")
plt.colorbar(im, ax=ax, label="Misclassification Penalty Weight")
ax.set_xticks(range(len(pen_segs)))
ax.set_yticks(range(len(pen_segs)))
ax.set_xticklabels(pen_segs, rotation=40, ha="right", fontsize=8)
ax.set_yticklabels(pen_segs, fontsize=8)
ax.set_xlabel("Predicted Segment", fontsize=10)
ax.set_ylabel("True Segment", fontsize=10)
ax.set_title("Asymmetric Cost Matrix — Misclassification Penalty Weights\n"
             "Diagonal = correct classification (zero cost)",
             fontsize=11, fontweight="bold")
for i in range(len(pen_segs)):
    for j in range(len(pen_segs)):
        val = int(pen_mat[i, j])
        color = "white" if val >= 6 else "black"
        ax.text(j, i, f"×{val}" if val > 0 else "✓", ha="center", va="center",
                fontsize=8, color=color, fontweight="bold" if val >= 8 else "normal")
fig.tight_layout()
save(fig, "fig04_cost_matrix.png")

# ── Fig 05: Revenue Impact Projection ─────────────────────────────────────
# Simulate: baseline (rule-based) vs model for top-3 penalty segments
target_segs = ["Corporate", "OFW/Migrant", "Mabuhay Loyalist"]
scenarios   = {"Conservative\n(1% improvement)": 0.01,
               "Base\n(5% improvement)": 0.05,
               "Optimistic\n(10% improvement)": 0.10}
uplift_data = {}

for seg in target_segs:
    n_seg = (df["model_segment"] == seg).sum()
    uplift_data[seg] = {
        sc: n_seg * REV_LOSS[seg] * pct_improve
        for sc, pct_improve in scenarios.items()
    }

x = np.arange(len(target_segs))
width = 0.22
sc_colors = ["#93C5FD", "#3B82F6", "#1D4ED8"]

fig, ax = plt.subplots(figsize=(10, 5))
for k, (sc, clr) in enumerate(zip(scenarios, sc_colors)):
    vals = [uplift_data[seg][sc] / 1_000_000 for seg in target_segs]
    bars = ax.bar(x + k * width, vals, width, label=sc.replace("\n", " "),
                  color=clr, edgecolor="white")
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                f"₱{v:.2f}M", ha="center", va="bottom", fontsize=7.5)

ax.set_xticks(x + width)
ax.set_xticklabels([f"{s}\n(×{PENALTY[s]} penalty)" for s in target_segs], fontsize=9)
ax.set_ylabel("Incremental Revenue Uplift (₱ Million)", fontsize=10)
ax.set_title("Projected Revenue Uplift from Reduced Misclassification\n"
             "Top 3 High-Penalty Segments — 3-Scenario Analysis",
             fontsize=11, fontweight="bold")
ax.legend(fontsize=9, framealpha=0.9)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"₱{v:.1f}M"))
fig.tight_layout()
save(fig, "fig05_revenue_impact.png")

# ── Fig 06: Per-Segment Recall ─────────────────────────────────────────────
valid_segs  = [(s, r) for s, r in seg_recall.items() if r is not None]
seg_names_r = [s for s, _ in valid_segs]
recall_vals = [r for _, r in valid_segs]
bar_colors  = [SEG_COLORS[s] for s in seg_names_r]
pen_labels  = [f"×{PENALTY[s]}" for s in seg_names_r]

fig, ax = plt.subplots(figsize=(10, 5))
bars = ax.bar(range(len(seg_names_r)), recall_vals, color=bar_colors, edgecolor="white")
ax.axhline(0.91, color="#EF4444", linestyle="--", linewidth=1.5, label="NFR-01 target (91%)")
ax.set_xticks(range(len(seg_names_r)))
ax.set_xticklabels(seg_names_r, rotation=35, ha="right", fontsize=8)
ax.set_ylabel("Recall", fontsize=10)
ax.set_ylim(0, 1.12)
ax.set_title("Per-Segment Recall — Asymmetric Validation\n"
             "★ = high-penalty segments requiring maximum recall",
             fontsize=11, fontweight="bold")
ax.legend(fontsize=9)

for bar, r, pl, seg in zip(bars, recall_vals, pen_labels, seg_names_r):
    star = " ★" if PENALTY[seg] >= 5 else ""
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
            f"{r:.0%}\n{pl}{star}", ha="center", va="bottom", fontsize=7.5,
            fontweight="bold" if PENALTY[seg] >= 5 else "normal")
fig.tight_layout()
save(fig, "fig06_per_segment_recall.png")

# ── Fig 07: Segment Behavior Profiles ─────────────────────────────────────
profile_segs = ["Corporate", "OFW/Migrant", "Premium Bleisure",
                "Budget/Adventure", "Mabuhay Loyalist", "Family"]
profile_feats = {
    "Lead Time\n(days)":       ("lead_time",   0, 120),
    "Cabin Class\n(0–3)":      ("cabin_ord",   0, 3),
    "Loyalty Score\n(0–3)":    ("loyalty_ord", 0, 3),
    "Income Level\n(0–2)":     ("income_ord",  0, 2),
    "Bags Checked":             ("Bags_Checked", 0, 4),
    "Price USD\n(log-norm)":   ("price_log",   4, 7),
}

feat_labels = list(profile_feats.keys())
x = np.arange(len(feat_labels))
width = 0.13

fig, ax = plt.subplots(figsize=(13, 5))
for k, seg in enumerate(profile_segs):
    mask = df["model_segment"] == seg
    vals = []
    for feat_label, (col, lo, hi) in profile_feats.items():
        raw = df.loc[mask, col].mean()
        vals.append((raw - lo) / (hi - lo))  # normalize 0–1
    offset = (k - len(profile_segs) / 2) * width + width / 2
    bars = ax.bar(x + offset, vals, width, label=seg,
                  color=SEG_COLORS[seg], edgecolor="white", alpha=0.88)

ax.set_xticks(x)
ax.set_xticklabels(feat_labels, fontsize=9)
ax.set_ylabel("Normalized Score (0–1)", fontsize=10)
ax.set_ylim(0, 1.15)
ax.set_title("Segment Behavior Profiles — Key Discriminating Features\n"
             "(Normalized to 0–1 for comparison)",
             fontsize=11, fontweight="bold")
ax.legend(loc="upper right", fontsize=8, ncol=2, framealpha=0.9)
fig.tight_layout()
save(fig, "fig07_segment_profiles.png")

# ── Fig 08: Booking Lead Time Distribution by Segment ────────────────────
top_segs   = ["Corporate", "OFW/Migrant", "Premium Bleisure",
               "Budget/Adventure", "Last-Minute", "Family"]
lt_data    = [df.loc[df["model_segment"] == s, "lead_time"].values for s in top_segs]
lt_colors  = [SEG_COLORS[s] for s in top_segs]

fig, ax = plt.subplots(figsize=(11, 5))
vp = ax.violinplot(lt_data, positions=range(len(top_segs)),
                   showmedians=True, showextrema=False)
for body, clr in zip(vp["bodies"], lt_colors):
    body.set_facecolor(clr)
    body.set_alpha(0.75)
vp["cmedians"].set_color("white")
vp["cmedians"].set_linewidth(2)

ax.set_xticks(range(len(top_segs)))
ax.set_xticklabels([f"{s}\n(×{PENALTY[s]})" for s in top_segs], fontsize=8.5)
ax.set_ylabel("Booking Lead Time (days)", fontsize=10)
ax.set_title("Booking Lead Time Distribution by Segment\n"
             "White line = median | Width = density of passengers",
             fontsize=11, fontweight="bold")

for i, (seg, vals) in enumerate(zip(top_segs, lt_data)):
    ax.text(i, np.median(vals) + 2, f"{np.median(vals):.0f}d",
            ha="center", va="bottom", fontsize=8, fontweight="bold")

fig.tight_layout()
save(fig, "fig08_lead_time_distribution.png")


# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
total_rev_risk = sum(
    (df["model_segment"] == seg).sum() * REV_LOSS[seg] * 0.01
    for seg in SEGMENTS
)

print("\n" + "═" * 60)
print("  POC SUMMARY")
print("═" * 60)
print(f"  Records processed:       {len(df):,}")
print(f"  Features:                {X_raw.shape[1]}")
print(f"  HDBSCAN micro-clusters:  {n_clusters}")
print(f"  Noise auto-assigned:     {noise_pct:.1f}%")
print(f"  Labelled (post-NL):      {labelled_pct:.1f}%")
print(f"  Raw accuracy (val set):  {raw_accuracy:.1%}")
print(f"  Conservative rev. risk:  ₱{total_rev_risk/1e6:.2f}M (1% misclassif.)")
print("═" * 60)
print("\n  Figures saved to poc_output/:")
for i in range(1, 9):
    labels = [
        "Segment Distribution",
        "PCA Cluster Scatter",
        "Negative Learning Impact",
        "Asymmetric Cost Matrix",
        "Revenue Impact Projection",
        "Per-Segment Recall",
        "Segment Behavior Profiles",
        "Booking Lead Time by Segment",
    ]
    print(f"    fig0{i}_  →  Slide {[3,3,3,5,5,7,6,4][i-1]}: {labels[i-1]}")
print()
