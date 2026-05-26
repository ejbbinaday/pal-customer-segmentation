"""
generate_dark_slides.py
Runs the POC pipeline on synthetic data and outputs 3 dark-themed PNGs
matching the PAL pitch deck navy/gold aesthetic.

Outputs → poc_output/dark/
  poc_kpi_card.png        — KPI summary (accuracy, revenue risk, records)
  poc_recall_dark.png     — Per-segment recall bar chart
  poc_scatter_dark.png    — PCA cluster separation scatter
"""

import os, sys, warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import euclidean_distances
import hdbscan

warnings.filterwarnings("ignore")
np.random.seed(42)

sys.path.insert(0, ".")
from pal_colors import SEG_COLORS, SEG_ORDER

# ── Deck theme ─────────────────────────────────────────────────────────────
BG      = "#0A1628"
CARD    = "#0F1E38"
BORDER  = "#1E3A5F"
GOLD    = "#F0A500"
BLUE    = "#1E5BAD"
SKY     = "#38BDF8"
WHITE   = "#F8FAFF"
GREY    = "#64748B"
RED     = "#EF4444"
GREEN   = "#22C55E"

OUT_DIR = "poc_output/dark"
os.makedirs(OUT_DIR, exist_ok=True)

def savefig(fig, name):
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, bbox_inches="tight", facecolor=BG, dpi=180)
    plt.close(fig)
    print(f"  Saved → {path}")

# ── Pipeline config ─────────────────────────────────────────────────────────
PENALTY = {
    "Corporate": 10, "Mabuhay Loyalist": 8, "OFW/Migrant": 5,
    "Premium Bleisure": 4, "Pilgrimage": 3, "Balikbayan/VFR": 2,
    "Family": 2, "Digital Nomad": 2, "Last-Minute": 1, "Budget/Adventure": 1,
}
SEGMENTS = list(PENALTY.keys())
REV_LOSS = {
    "Corporate": 40_000, "Mabuhay Loyalist": 32_000, "OFW/Migrant": 20_000,
    "Premium Bleisure": 16_000, "Pilgrimage": 12_000, "Balikbayan/VFR": 8_000,
    "Family": 8_000, "Digital Nomad": 8_000, "Last-Minute": 4_000, "Budget/Adventure": 4_000,
}

# ══════════════════════════════════════════════════════════════════════════════
# Pipeline (mirrored from poc_synthetic.py)
# ══════════════════════════════════════════════════════════════════════════════
print("Running POC pipeline for dark slide generation...")

df = pd.read_csv("synthetic_flight_passenger_data.csv")
df["Departure_Time"] = pd.to_datetime(df["Departure_Time"])
df = df[df["Price_USD"] > 0].reset_index(drop=True)

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
X_raw  = pd.concat([df[NUM_COLS], ohe], axis=1).fillna(0)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_raw)

df["proxy_segment"] = "Unassigned"
rules = [
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

nl_rules = [
    (df["proxy_segment"] == "Corporate") &
    (df["lead_time"] > 60) & (df["cabin_ord"] == 0) & (df["loyalty_ord"] == 0),
    (df["proxy_segment"] == "Mabuhay Loyalist") & (df["loyalty_ord"] == 0),
    (df["proxy_segment"] == "OFW/Migrant") & (df["Bags_Checked"] == 0),
    (df["proxy_segment"] == "Premium Bleisure") & (df["income_ord"] == 0),
]
for mask in nl_rules:
    df.loc[mask, "proxy_segment"] = "Unassigned"

X_df      = pd.DataFrame(X_scaled, columns=X_raw.columns)
total_pen = sum(PENALTY.values())
weights   = np.ones(X_df.shape[1])
for seg, pw in PENALTY.items():
    mask = df["proxy_segment"] == seg
    if mask.sum() < 10:
        continue
    centroid = X_df[mask].mean().values
    weights += (pw / total_pen) * np.abs(centroid)
weights   /= weights.mean()
X_weighted = X_df.values * weights

clusterer     = hdbscan.HDBSCAN(min_cluster_size=80, min_samples=10, metric="euclidean")
cluster_labels = clusterer.fit_predict(X_weighted)

seg_centroids = {}
for seg in SEGMENTS:
    mask = df["proxy_segment"] == seg
    if mask.sum() >= 10:
        seg_centroids[seg] = (X_df[mask].values * weights).mean(axis=0)

seg_names = list(seg_centroids.keys())
seg_mat   = np.vstack(list(seg_centroids.values()))

def nearest_seg(vec):
    dists = euclidean_distances(vec.reshape(1, -1), seg_mat)[0]
    return seg_names[int(np.argmin(dists))]

cluster_to_seg = {}
for c in set(cluster_labels):
    if c == -1:
        continue
    c_vec = (X_df[cluster_labels == c].values * weights).mean(axis=0)
    cluster_to_seg[c] = nearest_seg(c_vec)

model_segs = []
for i, c in enumerate(cluster_labels):
    if c != -1:
        model_segs.append(cluster_to_seg[c])
    else:
        model_segs.append(nearest_seg(X_df.iloc[i].values * weights))
df["model_segment"] = model_segs

labelled_mask = df["proxy_segment"] != "Unassigned"
df_val        = df[labelled_mask].copy()
correct_mask  = df_val["proxy_segment"] == df_val["model_segment"]
raw_accuracy  = correct_mask.mean()

misclassified = df_val[~correct_mask]
total_rev_risk = sum(
    REV_LOSS.get(row["proxy_segment"], 0)
    for _, row in misclassified.iterrows()
)

seg_recall = {}
for seg in SEGMENTS:
    true_mask = df_val["proxy_segment"] == seg
    if true_mask.sum() == 0:
        seg_recall[seg] = None
        continue
    correct = (df_val.loc[true_mask, "model_segment"] == seg).sum()
    seg_recall[seg] = correct / true_mask.sum()

n_labelled = labelled_mask.sum()
print(f"\n  Accuracy:      {raw_accuracy:.1%}")
print(f"  Revenue risk:  ₱{total_rev_risk/1_000_000:.2f}M")
print(f"  Records eval:  {n_labelled:,}")
print(f"  Per-segment recall:")
for seg, r in seg_recall.items():
    v = f"{r:.1%}" if r is not None else "N/A"
    print(f"    {seg:<22} {v}")

# ══════════════════════════════════════════════════════════════════════════════
# FIG 1 — KPI Summary Card
# ══════════════════════════════════════════════════════════════════════════════
print("\nGenerating KPI card...")

fig, ax = plt.subplots(figsize=(14, 4.2))
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)
ax.axis("off")

kpis = [
    {
        "value":    f"{raw_accuracy:.1%}",
        "label":    "Model Accuracy",
        "sublabel": "Labelled records · asymmetric scoring",
        "icon":     "✓",
        "color":    GREEN,
    },
    {
        "value":    f"₱{total_rev_risk/1_000_000:.2f}M",
        "label":    "Estimated Revenue Risk",
        "sublabel": f"Conservative misclassification cost · {n_labelled:,} records",
        "icon":     "₱",
        "color":    GOLD,
    },
    {
        "value":    f"{len(df):,}",
        "label":    "Synthetic Records Processed",
        "sublabel": "Full 8-stage pipeline · zero manual steps",
        "icon":     "▶",
        "color":    SKY,
    },
]

card_w = 0.30
gap    = 0.035
start  = 0.015

for i, kpi in enumerate(kpis):
    x = start + i * (card_w + gap)

    # card box
    rect = FancyBboxPatch(
        (x, 0.06), card_w, 0.88,
        boxstyle="round,pad=0.015",
        linewidth=1.2,
        edgecolor=kpi["color"] + "55",
        facecolor=CARD,
        transform=ax.transAxes,
        clip_on=False,
    )
    ax.add_patch(rect)

    # top accent bar
    bar = FancyBboxPatch(
        (x, 0.88), card_w, 0.06,
        boxstyle="round,pad=0.015",
        linewidth=0,
        facecolor=kpi["color"],
        alpha=0.18,
        transform=ax.transAxes,
        clip_on=False,
    )
    ax.add_patch(bar)

    # icon
    ax.text(x + 0.022, 0.82, kpi["icon"],
            transform=ax.transAxes,
            fontsize=18, color=kpi["color"],
            fontweight="bold", va="top", ha="left")

    # big value
    ax.text(x + card_w / 2, 0.57, kpi["value"],
            transform=ax.transAxes,
            fontsize=30, color=WHITE,
            fontweight="bold", va="center", ha="center",
            fontfamily="DejaVu Sans")

    # label
    ax.text(x + card_w / 2, 0.36, kpi["label"],
            transform=ax.transAxes,
            fontsize=10.5, color=kpi["color"],
            fontweight="bold", va="center", ha="center",
            fontfamily="DejaVu Sans")

    # sub-label
    ax.text(x + card_w / 2, 0.19, kpi["sublabel"],
            transform=ax.transAxes,
            fontsize=7.8, color=GREY,
            va="center", ha="center",
            fontfamily="DejaVu Sans", wrap=True)


savefig(fig, "poc_kpi_card.png")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 2 — Per-Segment Recall (dark)
# ══════════════════════════════════════════════════════════════════════════════
print("Generating recall chart...")

valid_segs  = [(s, r) for s, r in seg_recall.items() if r is not None]
seg_names_r = [s for s, _ in valid_segs]
recall_vals = [r for _, r in valid_segs]
bar_colors  = [SEG_COLORS[s] for s in seg_names_r]
penalties   = [PENALTY[s] for s in seg_names_r]

fig, ax = plt.subplots(figsize=(13, 5.5))
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

bars = ax.bar(
    range(len(seg_names_r)), recall_vals,
    color=bar_colors, edgecolor=BG, linewidth=0.8, width=0.65
)

# NFR threshold line
ax.axhline(0.91, color=RED, linestyle="--", linewidth=1.5,
           label="NFR-01 target  91%", alpha=0.85)

# Annotate each bar
for bar, r, pen, seg in zip(bars, recall_vals, penalties, seg_names_r):
    star  = " ★" if pen >= 5 else ""
    label = f"{r:.0%}\n×{pen}{star}"
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 0.012,
        label,
        ha="center", va="bottom",
        fontsize=7.8, color=WHITE,
        fontweight="bold" if pen >= 5 else "normal",
        fontfamily="DejaVu Sans",
    )

# x-axis segment names
ax.set_xticks(range(len(seg_names_r)))
ax.set_xticklabels(seg_names_r, rotation=30, ha="right",
                   fontsize=8.5, color=WHITE, fontfamily="DejaVu Sans")

ax.set_ylabel("Recall", fontsize=10, color=GREY, fontfamily="DejaVu Sans")
ax.set_ylim(0, 1.18)
ax.tick_params(axis="y", colors=GREY)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))

for spine in ax.spines.values():
    spine.set_visible(False)
ax.tick_params(axis="x", length=0)
ax.yaxis.set_tick_params(color=GREY)

# horizontal grid
ax.yaxis.grid(True, color=BORDER, linewidth=0.6, linestyle="-")
ax.set_axisbelow(True)


legend = ax.legend(fontsize=8.5, framealpha=0, labelcolor=RED)
for text in legend.get_texts():
    text.set_color(RED)

fig.tight_layout(pad=1.5)
savefig(fig, "poc_recall_dark.png")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 3 — PCA Cluster Scatter (dark)
# ══════════════════════════════════════════════════════════════════════════════
print("Generating PCA scatter...")

pca   = PCA(n_components=2, random_state=42)
X_pca = pca.fit_transform(X_weighted)

fig, ax = plt.subplots(figsize=(11, 7))
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

for seg in SEGMENTS:
    mask = df["model_segment"] == seg
    if mask.sum() == 0:
        continue
    ax.scatter(
        X_pca[mask, 0], X_pca[mask, 1],
        c=SEG_COLORS[seg], label=seg,
        alpha=0.38, s=9, linewidths=0,
    )

# Centroid markers
for seg in SEGMENTS:
    mask = df["model_segment"] == seg
    if mask.sum() == 0:
        continue
    cx = X_pca[mask, 0].mean()
    cy = X_pca[mask, 1].mean()
    ax.scatter(cx, cy, c=SEG_COLORS[seg],
               s=90, marker="D", edgecolors=WHITE,
               linewidths=0.8, zorder=5)
    ax.text(cx, cy + 0.18, seg.split("/")[0],
            fontsize=6.5, color=SEG_COLORS[seg],
            ha="center", va="bottom",
            fontweight="bold", fontfamily="DejaVu Sans")

ax.set_xlabel(
    f"PC1  ({pca.explained_variance_ratio_[0]*100:.1f}% variance)",
    fontsize=9, color=GREY, fontfamily="DejaVu Sans",
)
ax.set_ylabel(
    f"PC2  ({pca.explained_variance_ratio_[1]*100:.1f}% variance)",
    fontsize=9, color=GREY, fontfamily="DejaVu Sans",
)

ax.tick_params(colors=GREY)
for spine in ax.spines.values():
    spine.set_color(BORDER)

ax.xaxis.grid(True, color=BORDER, linewidth=0.4, linestyle="-")
ax.yaxis.grid(True, color=BORDER, linewidth=0.4, linestyle="-")
ax.set_axisbelow(True)


handles = [
    mpatches.Patch(color=SEG_COLORS[s], label=s)
    for s in SEGMENTS
    if (df["model_segment"] == s).sum() > 0
]
legend = ax.legend(
    handles=handles,
    fontsize=7.5, framealpha=0.15,
    facecolor=CARD, edgecolor=BORDER,
    loc="lower right", ncol=2,
)
for text in legend.get_texts():
    text.set_color(WHITE)
    text.set_fontfamily("DejaVu Sans")

fig.tight_layout(pad=1.5)
savefig(fig, "poc_scatter_dark.png")

print("\nDone. All 3 dark-themed PNGs saved to poc_output/dark/")
