"""Resampling strategy comparison — PAL customer segmentation.

Proxy labels (waterfall) → 5 resampling strategies → Random Forest classifier
Evaluation: F1-macro · weighted penalty cost · confusion matrix · PCA boundaries

Outputs (resample_output/):
  fig_r01_class_distribution.png  — original vs each resampled distribution
  fig_r02_confusion_matrices.png  — 6 confusion matrices (baseline + 5 methods)
  fig_r03_metrics_comparison.png  — F1 / precision / recall bar chart
  fig_r04_penalty_cost.png        — weighted misclassification cost (↓ better)
  fig_r05_pca_boundaries.png      — decision regions in PCA-2D
  fig_r06_winner_detail.png       — ROC + per-class F1 for best method
"""

import warnings

warnings.filterwarnings("ignore")

from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from imblearn.over_sampling import ADASYN, SMOTE, RandomOverSampler
from imblearn.under_sampling import RandomUnderSampler, TomekLinks
from matplotlib.colors import ListedColormap
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.preprocessing import LabelEncoder, StandardScaler

from pal_colors import SEG_COLORS

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "resample_output"
OUTPUT.mkdir(parents=True, exist_ok=True)

# ── theme ──────────────────────────────────────────────────────────────────────
BG, PANEL, BORDER = "#111827", "#1F2937", "#374151"
TEXT, SUBTEXT = "#F9FAFB", "#9CA3AF"
ACCENT = "#3B82F6"

METHOD_COLORS = {
    "Baseline": "#94A3B8",
    "Random Oversample": "#3B82F6",
    "Random Undersample": "#F59E0B",
    "SMOTE": "#10B981",
    "ADASYN": "#F97316",
    "Tomek Links": "#8B5CF6",
}
METHODS = list(METHOD_COLORS.keys())

# Penalty weights (misclassification cost per true segment)
PENALTY = {
    "Corporate": 10,
    "Premium Bleisure": 4,
    "OFW/Migrant": 5,
    "Balikbayan/VFR": 2,
    "Pilgrimage": 3,
    "Family": 2,
    "Budget/Adventure": 1,
    "Last-Minute": 1,
    "Digital Nomad": 2,
}

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
    print(f"  saved → resample_output/{name}.png")


# ══════════════════════════════════════════════════════════════════════════════
# 1. LOAD & PREPARE
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


# Proxy waterfall assignment (same as eda_segments.py)
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
labeled = df[df["segment"] != "Unassigned"].copy()
print(f"Labeled records: {len(labeled):,}  ({len(labeled) / len(df) * 100:.1f}% of total)")
print(labeled["segment"].value_counts().to_string())

# ── feature matrix ─────────────────────────────────────────────────────────────
cabin_map = {"Y": 0, "W": 1, "J": 2}
labeled["cabin_ord"] = labeled["Cabin"].map(cabin_map).fillna(0)
labeled["is_dom"] = (labeled["Entity"] == "DOM").astype(int)

cat_cols = ["Region", "Farebrand", "Itinerary Type", "Ticketing Channel"]
df_enc = pd.get_dummies(
    labeled[cat_cols].fillna("Unknown"), columns=cat_cols, prefix_sep="=", dtype=int
)
num_cols = [
    "lead_time",
    "Average Fare",
    "fare_per_pax",
    "PAX Count",
    "cabin_ord",
    "is_dom",
    "booking_month",
]

X_raw = pd.concat([labeled[num_cols].reset_index(drop=True), df_enc.reset_index(drop=True)], axis=1)

le = LabelEncoder()
y_raw = le.fit_transform(labeled["segment"])
class_names = le.classes_

scaler = StandardScaler()
X = scaler.fit_transform(X_raw)
y = y_raw

print(f"\nFeature matrix: {X.shape}  |  Classes: {list(class_names)}")
class_weights = {le.transform([s])[0]: PENALTY.get(s, 1) for s in class_names}
print(f"Class penalty weights: { {class_names[k]: v for k, v in class_weights.items()} }")

# ══════════════════════════════════════════════════════════════════════════════
# 2. RESAMPLING STRATEGIES
# ══════════════════════════════════════════════════════════════════════════════
resamplers = {
    "Baseline": None,
    "Random Oversample": RandomOverSampler(random_state=42),
    "Random Undersample": RandomUnderSampler(random_state=42),
    "SMOTE": SMOTE(random_state=42, k_neighbors=3),
    "ADASYN": ADASYN(random_state=42, n_neighbors=3),
    "Tomek Links": TomekLinks(),
}

clf_params = dict(
    n_estimators=200, max_depth=12, class_weight=class_weights, n_jobs=-1, random_state=42
)

results = {}  # method → {f1, precision, recall, cost, cm, y_true, y_pred}
X_resamp = {}  # method → (X_r, y_r) for distribution plot

print("\nRunning cross-validated evaluation (stratified 5-fold) ...")
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

for name, sampler in resamplers.items():
    print(f"  [{name}] ", end="", flush=True)

    if sampler is None:
        X_r, y_r = X, y
    else:
        try:
            X_r, y_r = sampler.fit_resample(X, y)
        except Exception as e:
            print(f"FAILED: {e}")
            continue

    X_resamp[name] = (X_r, y_r)
    print(f"n={len(y_r):,}  dist={pd.Series(y_r).value_counts().to_dict()} ", end="")

    clf = RandomForestClassifier(**clf_params)
    y_pred = cross_val_predict(clf, X_r, y_r, cv=cv, n_jobs=-1)

    cm = confusion_matrix(y_r, y_pred, labels=range(len(class_names)))
    f1 = f1_score(y_r, y_pred, average="macro", zero_division=0)
    prec = precision_score(y_r, y_pred, average="macro", zero_division=0)
    rec = recall_score(y_r, y_pred, average="macro", zero_division=0)
    f1_w = f1_score(y_r, y_pred, average="weighted", zero_division=0)
    f1_per = f1_score(y_r, y_pred, average=None, labels=range(len(class_names)), zero_division=0)

    # Weighted penalty cost: sum over misclassified rows of penalty[true_class]
    wrong_mask = y_r != y_pred
    pen_cost = sum(class_weights.get(int(t), 1) for t in y_r[wrong_mask])
    pen_cost_pct = pen_cost / len(y_r)

    print(f"→ F1={f1:.4f}  cost={pen_cost:,}")
    results[name] = dict(
        f1=f1,
        precision=prec,
        recall=rec,
        f1_weighted=f1_w,
        f1_per_class=f1_per,
        penalty_cost=pen_cost,
        penalty_cost_pct=pen_cost_pct,
        cm=cm,
        y_true=y_r,
        y_pred=y_pred,
        n=len(y_r),
    )

# ══════════════════════════════════════════════════════════════════════════════
# 3. SUMMARY TABLE
# ══════════════════════════════════════════════════════════════════════════════
summary = pd.DataFrame(
    {
        m: {
            "F1 (macro)": r["f1"],
            "F1 (weighted)": r["f1_weighted"],
            "Precision": r["precision"],
            "Recall": r["recall"],
            "Penalty Cost": r["penalty_cost"],
            "n (resampled)": r["n"],
        }
        for m, r in results.items()
    }
).T

print("\n" + "=" * 72)
print("RESAMPLING COMPARISON SUMMARY")
print("=" * 72)
print(summary.round(4).to_string())

best_method = min(results, key=lambda m: results[m]["penalty_cost"])
best_f1 = max(results, key=lambda m: results[m]["f1"])
print(f"\n★ Lowest penalty cost : {best_method}")
print(f"★ Highest F1 (macro)  : {best_f1}")

# ══════════════════════════════════════════════════════════════════════════════
# FIG R01 — Class distribution comparison
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(2, 3, figsize=(18, 9), facecolor=BG)
fig.suptitle(
    "Class Distribution Before & After Resampling",
    fontsize=13,
    color=TEXT,
    fontweight="bold",
    y=1.01,
)

cmap_seg = [SEG_COLORS.get(c, "#60A5FA") for c in class_names]

for ax, (name, (_X_r, y_r)) in zip(axes.flat, X_resamp.items()):
    counts = pd.Series(y_r).value_counts().sort_index()
    bars = ax.bar(
        [class_names[i] for i in counts.index],
        counts.values,
        color=[cmap_seg[i] for i in counts.index],
        width=0.65,
    )
    for bar, val in zip(bars, counts.values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(counts) * 0.01,
            f"{val:,}",
            ha="center",
            va="bottom",
            fontsize=6.5,
            color=SUBTEXT,
        )
    ax.set_title(
        f"{name}  (n={len(y_r):,})",
        fontsize=10,
        color=METHOD_COLORS.get(name, TEXT),
        fontweight="bold",
    )
    ax.set_xlabel("")
    ax.set_ylabel("Count")
    ax.title.set_color(METHOD_COLORS.get(name, TEXT))
    plt.setp(ax.get_xticklabels(), rotation=35, ha="right", fontsize=7)

fig.tight_layout()
save(fig, "fig_r01_class_distribution")

# ══════════════════════════════════════════════════════════════════════════════
# FIG R02 — Confusion matrices
# ══════════════════════════════════════════════════════════════════════════════
short_names = [c[:8] for c in class_names]
fig, axes = plt.subplots(2, 3, figsize=(20, 12), facecolor=BG)
fig.suptitle(
    "Confusion Matrices  ·  5-Fold Cross-Validation",
    fontsize=13,
    color=TEXT,
    fontweight="bold",
    y=1.01,
)

for ax, (name, res) in zip(axes.flat, results.items()):
    cm_norm = res["cm"].astype(float)
    row_sum = cm_norm.sum(axis=1, keepdims=True)
    cm_norm = np.where(row_sum > 0, cm_norm / row_sum, 0)  # row-normalize

    sns.heatmap(
        cm_norm,
        ax=ax,
        cmap="Blues",
        annot=True,
        fmt=".2f",
        xticklabels=short_names,
        yticklabels=short_names,
        linewidths=0.3,
        linecolor=BG,
        cbar=False,
        annot_kws={"size": 6.5},
    )
    ax.set_title(
        f"{name}\nF1={res['f1']:.3f}  cost={res['penalty_cost']:,}",
        fontsize=9,
        color=METHOD_COLORS.get(name, TEXT),
        fontweight="bold",
    )
    ax.set_xlabel("Predicted", fontsize=8)
    ax.set_ylabel("Actual", fontsize=8)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=7)
    plt.setp(ax.get_yticklabels(), rotation=0, fontsize=7)

fig.tight_layout()
save(fig, "fig_r02_confusion_matrices")

# ══════════════════════════════════════════════════════════════════════════════
# FIG R03 — Metrics comparison bar chart
# ══════════════════════════════════════════════════════════════════════════════
metrics_df = pd.DataFrame(
    {
        m: {
            "F1 Macro": r["f1"],
            "F1 Weighted": r["f1_weighted"],
            "Precision": r["precision"],
            "Recall": r["recall"],
        }
        for m, r in results.items()
    }
).T

x = np.arange(len(metrics_df.columns))
w = 0.13
fig, ax = plt.subplots(figsize=(14, 6), facecolor=BG)

for i, (method, row) in enumerate(metrics_df.iterrows()):
    offset = (i - len(metrics_df) / 2 + 0.5) * w
    bars = ax.bar(
        x + offset,
        row.values,
        width=w,
        color=METHOD_COLORS.get(method, ACCENT),
        label=method,
        alpha=0.9,
    )

ax.set_xticks(x)
ax.set_xticklabels(metrics_df.columns, fontsize=10)
ax.set_ylim(0, 1.05)
ax.set_ylabel("Score")
ax.set_title(
    "Classification Metrics by Resampling Strategy", fontsize=12, color=TEXT, fontweight="bold"
)
ax.axhline(0.5, color=BORDER, ls="--", lw=0.8, alpha=0.6)
ax.legend(fontsize=8, loc="upper right", framealpha=0.3, facecolor=PANEL, edgecolor=BORDER)
ax.title.set_color(TEXT)
fig.tight_layout()
save(fig, "fig_r03_metrics_comparison")

# ══════════════════════════════════════════════════════════════════════════════
# FIG R04 — Penalty cost comparison
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(14, 5), facecolor=BG)

costs = [results[m]["penalty_cost"] for m in METHODS if m in results]
costs_pct = [results[m]["penalty_cost_pct"] * 100 for m in METHODS if m in results]
labels = [m for m in METHODS if m in results]
colors = [METHOD_COLORS[m] for m in labels]

# highlight winner
win_idx = costs.index(min(costs))
edge_w = [2.5 if i == win_idx else 0.5 for i in range(len(labels))]

ax1 = axes[0]
bars = ax1.bar(
    labels,
    costs,
    color=colors,
    width=0.6,
    edgecolor=["white" if i == win_idx else BORDER for i in range(len(labels))],
    linewidth=edge_w,
)
for bar, val in zip(bars, costs):
    ax1.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + max(costs) * 0.01,
        f"{val:,}",
        ha="center",
        va="bottom",
        fontsize=8,
        color=SUBTEXT,
    )
ax1.set_title("Total Weighted Penalty Cost  (↓ better)", color=TEXT, fontsize=10, fontweight="bold")
ax1.set_ylabel("Cumulative Penalty Score")
plt.setp(ax1.get_xticklabels(), rotation=20, ha="right")

# annotate winner
ax1.annotate(
    f"★ Best\n{labels[win_idx]}",
    xy=(win_idx, costs[win_idx]),
    xytext=(win_idx + 0.8, costs[win_idx] * 0.85),
    arrowprops=dict(arrowstyle="->", color="white", lw=1.2),
    fontsize=8,
    color="white",
    ha="center",
)

ax2 = axes[1]
ax2.bar(
    labels,
    costs_pct,
    color=colors,
    width=0.6,
    edgecolor=["white" if i == win_idx else BORDER for i in range(len(labels))],
    linewidth=edge_w,
)
ax2.set_title("Penalty Cost per Record  (%)", color=TEXT, fontsize=10, fontweight="bold")
ax2.set_ylabel("Avg Penalty per Record")
plt.setp(ax2.get_xticklabels(), rotation=20, ha="right")

fig.suptitle(
    "Asymmetric Misclassification Penalty Cost by Resampling Strategy",
    fontsize=12,
    color=TEXT,
    fontweight="bold",
    y=1.02,
)
fig.tight_layout()
save(fig, "fig_r04_penalty_cost")

# ══════════════════════════════════════════════════════════════════════════════
# FIG R05 — PCA decision boundaries
# ══════════════════════════════════════════════════════════════════════════════
print("\nBuilding PCA decision boundary plots (this takes a moment) ...")

pca2 = PCA(n_components=2, random_state=42)
X_pca_base = pca2.fit_transform(X)

seg_palette_list = [SEG_COLORS.get(c, "#60A5FA") for c in class_names]
cmap_discrete = ListedColormap(seg_palette_list)

fig, axes = plt.subplots(2, 3, figsize=(21, 12), facecolor=BG)
fig.suptitle(
    "Decision Boundaries in PCA Space  ·  Random Forest Classifier",
    fontsize=13,
    color=TEXT,
    fontweight="bold",
    y=1.01,
)

h = 0.08  # mesh step
for ax, (name, (X_r, y_r)) in zip(axes.flat, X_resamp.items()):
    # Project resampled data to PCA space (fit on baseline, transform all)
    X_r_pca = pca2.transform(X_r)

    # Fit RF on full resampled set
    clf_viz = RandomForestClassifier(
        n_estimators=100, max_depth=8, class_weight=class_weights, n_jobs=-1, random_state=42
    )
    clf_viz.fit(X_r, y_r)

    # Mesh grid in PCA-2D (approximate by projecting mesh back — use PCA inverse)
    x_min, x_max = X_pca_base[:, 0].min() - 0.5, X_pca_base[:, 0].max() + 0.5
    y_min, y_max = X_pca_base[:, 1].min() - 0.5, X_pca_base[:, 1].max() + 0.5
    xx, yy = np.meshgrid(np.arange(x_min, x_max, h), np.arange(y_min, y_max, h))
    grid_pca = np.c_[xx.ravel(), yy.ravel()]
    grid_orig = pca2.inverse_transform(grid_pca)
    Z = clf_viz.predict(grid_orig).reshape(xx.shape)

    ax.contourf(
        xx, yy, Z, alpha=0.35, cmap=cmap_discrete, levels=np.arange(-0.5, len(class_names) + 0.5, 1)
    )

    # Scatter sample points
    idx_s = np.random.default_rng(42).choice(
        len(X_pca_base), size=min(3000, len(X_pca_base)), replace=False
    )
    for ci, cname in enumerate(class_names):
        mask = y[idx_s] == ci
        ax.scatter(
            X_pca_base[idx_s][mask, 0],
            X_pca_base[idx_s][mask, 1],
            c=SEG_COLORS.get(cname, "#60A5FA"),
            s=5,
            alpha=0.6,
            label=cname if i == 0 else "",
        )

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_title(
        f"{name}  |  F1={results[name]['f1']:.3f}  cost={results[name]['penalty_cost']:,}",
        fontsize=9,
        color=METHOD_COLORS.get(name, TEXT),
        fontweight="bold",
    )
    ax.set_xlabel("PC1", fontsize=8)
    ax.set_ylabel("PC2", fontsize=8)

# shared legend
legend_patches = [mpatches.Patch(color=SEG_COLORS.get(c, "#60A5FA"), label=c) for c in class_names]
fig.legend(
    handles=legend_patches,
    fontsize=7.5,
    loc="lower center",
    ncol=len(class_names),
    framealpha=0.3,
    facecolor=PANEL,
    edgecolor=BORDER,
    bbox_to_anchor=(0.5, -0.02),
)

fig.tight_layout()
save(fig, "fig_r05_pca_boundaries")

# ══════════════════════════════════════════════════════════════════════════════
# FIG R06 — Winner deep-dive: per-class F1
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(16, 6), facecolor=BG)
fig.suptitle(
    f"Winner Deep-Dive: {best_method}  ·  Per-Class F1 & Cost Breakdown",
    fontsize=12,
    color=TEXT,
    fontweight="bold",
)

# Per-class F1
ax1 = axes[0]
f1_per = results[best_method]["f1_per_class"]
bar_colors = [SEG_COLORS.get(c, "#60A5FA") for c in class_names]
bars = ax1.barh(class_names, f1_per, color=bar_colors, height=0.6)
for bar, val in zip(bars, f1_per):
    ax1.text(
        val + 0.005,
        bar.get_y() + bar.get_height() / 2,
        f"{val:.3f}",
        va="center",
        fontsize=8,
        color=TEXT,
    )
ax1.axvline(
    results[best_method]["f1"],
    color="white",
    ls="--",
    lw=1.2,
    label=f"Macro avg = {results[best_method]['f1']:.3f}",
)
ax1.set_xlim(0, 1.05)
ax1.set_title(f"Per-Class F1  ({best_method})", color=TEXT, fontsize=10)
ax1.legend(fontsize=8, facecolor=PANEL, edgecolor=BORDER)

# Cost breakdown vs baseline
ax2 = axes[1]
cost_vals = [results[m]["penalty_cost"] for m in labels]
cost_delta = [c - results["Baseline"]["penalty_cost"] for c in cost_vals]
delta_colors = ["#10B981" if d < 0 else "#EF4444" for d in cost_delta]
bars2 = ax2.barh(labels, cost_delta, color=delta_colors, height=0.6)
for bar, val in zip(bars2, cost_delta):
    x_pos = (
        val + (max(cost_delta) - min(cost_delta)) * 0.01
        if val >= 0
        else val - (max(cost_delta) - min(cost_delta)) * 0.01
    )
    ax2.text(
        x_pos,
        bar.get_y() + bar.get_height() / 2,
        f"{val:+,}",
        va="center",
        ha="left" if val >= 0 else "right",
        fontsize=8,
        color=TEXT,
    )
ax2.axvline(0, color="white", lw=1.0, ls="--", alpha=0.5)
ax2.set_title("Penalty Cost Δ vs Baseline  (green=improvement)", color=TEXT, fontsize=10)
ax2.set_xlabel("Δ Penalty Cost  (↓ better)")

fig.tight_layout()
save(fig, "fig_r06_winner_detail")

# ══════════════════════════════════════════════════════════════════════════════
# FINAL LEADERBOARD
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 72)
print("LEADERBOARD")
print("=" * 72)
ranked = sorted(results.items(), key=lambda x: x[1]["penalty_cost"])
print(f"{'Rank':<6}{'Method':<24}{'F1 Macro':<12}{'F1 Weighted':<14}{'Penalty Cost':<15}{'n'}")
print("-" * 72)
for rank, (m, r) in enumerate(ranked, 1):
    flag = " ★" if rank == 1 else ""
    print(
        f"{rank:<6}{m:<24}{r['f1']:<12.4f}{r['f1_weighted']:<14.4f}{r['penalty_cost']:<15,}{r['n']:,}{flag}"
    )
print()
