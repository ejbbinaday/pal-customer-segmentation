"""EDA graphs for the 10 proposed PAL customer segments."""

from pathlib import Path

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from pal_colors import SEG_COLORS, SEG_ORDER

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "eda_output"
OUTPUT.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="darkgrid", font_scale=1.0)
plt.rcParams.update(
    {
        "figure.facecolor": "#111827",
        "axes.facecolor": "#1F2937",
        "axes.edgecolor": "#374151",
        "text.color": "#F9FAFB",
        "axes.labelcolor": "#F9FAFB",
        "xtick.color": "#9CA3AF",
        "ytick.color": "#9CA3AF",
        "grid.color": "#374151",
        "savefig.bbox": "tight",
        "savefig.dpi": 150,
        "figure.dpi": 130,
    }
)


def save(fig, name):
    fig.savefig(OUTPUT / f"{name}.png", facecolor="#111827")
    plt.close(fig)
    print(f"  saved → eda_output/{name}.png")


# ── load & clean ───────────────────────────────────────────────────────────────
df = pd.read_csv(ROOT / "data" / "raw" / "sample-features.csv")
df["Average Fare"] = df["Average Fare"].str.replace("$", "", regex=False).astype(float)
df["PNRCreationDate"] = pd.to_datetime(df["PNRCreationDate"], dayfirst=True, errors="coerce")
df["Flight Date"] = pd.to_datetime(df["Flight Date"], dayfirst=True, errors="coerce")
df["lead_time"] = (df["Flight Date"] - df["PNRCreationDate"]).dt.days
df["booking_month"] = df["PNRCreationDate"].dt.month
df["fare_per_pax"] = df["Average Fare"] / df["PAX Count"]


# ── assign segment (priority waterfall) ───────────────────────────────────────
def assign_segment(df):
    seg = pd.Series("Unassigned", index=df.index)
    # Priority 10 → 1 (higher overwrites lower)
    budget_mask = df["Farebrand"].isin(["Economy Supersaver", "Economy Saver"])
    seg[budget_mask] = "Budget/Adventure"

    nomad_mask = (
        (df["PAX Count"] == 1)
        & (df["Region"] == "ASEAN")
        & (df["Ticketing Channel"] == "WEB/APP")
        & (df["Farebrand"].isin(["Economy Flex", "Economy Value"]))
    )
    seg[nomad_mask] = "Digital Nomad"

    lm_mask = df["lead_time"] <= 3
    seg[lm_mask] = "Last-Minute"

    fam_mask = df["PAX Count"].between(3, 5)
    seg[fam_mask] = "Family"

    pil_mask = (df["PAX Count"] >= 4) & (df["Ticketing Channel"] == "Traditional Travel Agency")
    seg[pil_mask] = "Pilgrimage"

    bali_mask = df["Itinerary Type"] == "Beyonds (INT - DOM)"
    seg[bali_mask] = "Balikbayan/VFR"

    ofw_mask = (df["Region"] == "Middle East") | (df["Ticketing Channel"] == "Sea Crew")
    seg[ofw_mask] = "OFW/Migrant"

    bleis_mask = df["Cabin"] == "W"
    seg[bleis_mask] = "Premium Bleisure"

    corp_mask = df["Cabin"] == "J"
    seg[corp_mask] = "Corporate"

    return seg


df["segment"] = assign_segment(df)
print("Segment distribution:")
print(df["segment"].value_counts())


# ══════════════════════════════════════════════════════════════════════════════
# FIG 23 — Segment Assignment Distribution
# ══════════════════════════════════════════════════════════════════════════════
print("\nGenerating Fig 23 – Segment Assignment Distribution")
seg_counts = df["segment"].value_counts().reindex(SEG_ORDER).dropna()
colors_bar = [SEG_COLORS[s] for s in seg_counts.index]

fig, ax = plt.subplots(figsize=(12, 6))
fig.patch.set_facecolor("#111827")
bars = ax.barh(
    seg_counts.index[::-1],
    seg_counts.values[::-1],
    color=colors_bar[::-1],
    edgecolor="none",
    height=0.65,
)
ax.set_title(
    "Proposed Segment Assignment — Record Distribution\n"
    "(Priority waterfall: Corporate > OFW > Balikbayan > Pilgrimage > Family > Last-Minute > Bleisure > Nomad > Budget)",
    fontsize=10,
    pad=12,
    color="#F9FAFB",
)
ax.set_xlabel("PNR Count", color="#9CA3AF")
for bar in bars:
    w = bar.get_width()
    pct = w / len(df) * 100
    ax.text(
        w + 60,
        bar.get_y() + bar.get_height() / 2,
        f"{w:,}  ({pct:.1f}%)",
        va="center",
        fontsize=9,
        color="#F9FAFB",
    )
ax.set_xlim(0, seg_counts.max() * 1.2)
note = (
    "Note: 'Mabuhay Loyalist' segment not assignable — Loyalty status is 100% null in sample.\n"
    "'Unassigned' records are candidates across multiple segments, requiring additional features to classify."
)
fig.text(0.5, -0.04, note, ha="center", fontsize=8, color="#6B7280", style="italic")
save(fig, "23_segment_distribution")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 24 — Lead Time KDE: All 10 Segments
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 24 – Lead Time KDE All Segments")
fig, ax = plt.subplots(figsize=(13, 6))
fig.patch.set_facecolor("#111827")
for seg, color in SEG_COLORS.items():
    if seg in ("Mabuhay Loyalist", "Unassigned"):
        continue
    sub = df[df["segment"] == seg]["lead_time"].dropna().clip(0, 180)
    if len(sub) > 10:
        sns.kdeplot(sub, ax=ax, label=seg, color=color, linewidth=2, fill=True, alpha=0.08)
ax.set_title(
    "Booking Lead Time Distribution by Proposed Segment (0–180 days)",
    fontweight="bold",
    pad=12,
    color="#F9FAFB",
)
ax.set_xlabel("Days Before Departure")
ax.set_ylabel("Density")
ax.legend(
    fontsize=8, loc="upper right", facecolor="#1F2937", edgecolor="#374151", labelcolor="#F9FAFB"
)
ax.axvline(3, color="#EF4444", ls=":", lw=1.2, alpha=0.5)
ax.axvline(14, color="#F59E0B", ls=":", lw=1.2, alpha=0.5)
ax.axvline(60, color="#10B981", ls=":", lw=1.2, alpha=0.5)
ax.text(3, ax.get_ylim()[1] * 0.95, "3d", color="#EF4444", fontsize=7, ha="center")
ax.text(14, ax.get_ylim()[1] * 0.95, "14d", color="#F59E0B", fontsize=7, ha="center")
ax.text(60, ax.get_ylim()[1] * 0.95, "60d", color="#10B981", fontsize=7, ha="center")
save(fig, "24_lead_time_all_segments")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 25 — Fare per PAX Boxplot: All 10 Segments
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 25 – Fare per PAX All Segments")
plot_segs = [s for s in SEG_ORDER if s not in ("Mabuhay Loyalist",)]
order = (
    df[df["segment"].isin(plot_segs)]
    .groupby("segment")["fare_per_pax"]
    .median()
    .sort_values(ascending=False)
    .index.tolist()
)
pal = {s: SEG_COLORS[s] for s in order}

fig, ax = plt.subplots(figsize=(14, 6))
fig.patch.set_facecolor("#111827")
bp_data = [df[df["segment"] == s]["fare_per_pax"].dropna().clip(0, 1500) for s in order]
bp = ax.boxplot(
    bp_data,
    patch_artist=True,
    showfliers=False,
    medianprops=dict(color="white", linewidth=2),
    whiskerprops=dict(color="#6B7280"),
    capprops=dict(color="#6B7280"),
    boxprops=dict(linewidth=0),
)
for patch, seg in zip(bp["boxes"], order):
    patch.set_facecolor(SEG_COLORS[seg])
    patch.set_alpha(0.75)
ax.set_xticks(range(1, len(order) + 1))
ax.set_xticklabels(order, rotation=25, ha="right", fontsize=8.5)
ax.set_title(
    "Fare per PAX by Proposed Segment (USD, excl. outliers)",
    fontweight="bold",
    pad=12,
    color="#F9FAFB",
)
ax.set_ylabel("Fare per PAX (USD)")
for i, (_seg, data) in enumerate(zip(order, bp_data)):
    med = data.median()
    ax.text(
        i + 1, med + 5, f"${med:.0f}", ha="center", fontsize=8, color="white", fontweight="bold"
    )
save(fig, "25_fare_per_pax_all_segments")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 26 — Segment × Ticketing Channel Heatmap
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 26 – Segment × Channel Heatmap")
ch_top = df["Ticketing Channel"].fillna("Unknown").value_counts().head(8).index
ct = pd.crosstab(df["segment"], df["Ticketing Channel"].fillna("Unknown"))
ct = ct[[c for c in ch_top if c in ct.columns]]
ct_pct = ct.div(ct.sum(axis=1), axis=0) * 100
ct_pct = ct_pct.reindex([s for s in SEG_ORDER if s in ct_pct.index])

fig, ax = plt.subplots(figsize=(13, 7))
fig.patch.set_facecolor("#111827")
sns.heatmap(
    ct_pct.round(1),
    annot=True,
    fmt=".1f",
    cmap=sns.color_palette("Blues", as_cmap=True),
    ax=ax,
    linewidths=0.5,
    linecolor="#111827",
    cbar_kws={"label": "% within segment", "shrink": 0.7},
)
ax.set_title(
    "Ticketing Channel Mix by Proposed Segment (%)", fontweight="bold", pad=12, color="#F9FAFB"
)
ax.set_xlabel("Ticketing Channel")
ax.set_ylabel("")
plt.xticks(rotation=30, ha="right")
save(fig, "26_segment_channel_heatmap")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 27 — Segment × Region Heatmap
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 27 – Segment × Region Heatmap")
rt = pd.crosstab(df["segment"], df["Region"])
rt_pct = rt.div(rt.sum(axis=1), axis=0) * 100
rt_pct = rt_pct.reindex([s for s in SEG_ORDER if s in rt_pct.index])

fig, ax = plt.subplots(figsize=(13, 7))
fig.patch.set_facecolor("#111827")
sns.heatmap(
    rt_pct.round(1),
    annot=True,
    fmt=".1f",
    cmap=sns.color_palette("YlOrRd", as_cmap=True),
    ax=ax,
    linewidths=0.5,
    linecolor="#111827",
    cbar_kws={"label": "% within segment", "shrink": 0.7},
)
ax.set_title(
    "Geographic Region Mix by Proposed Segment (%)", fontweight="bold", pad=12, color="#F9FAFB"
)
ax.set_xlabel("Region")
ax.set_ylabel("")
plt.xticks(rotation=30, ha="right")
save(fig, "27_segment_region_heatmap")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 28 — Segment × Farebrand Heatmap
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 28 – Segment × Farebrand Heatmap")
fb_order = [
    "Economy Supersaver",
    "Economy Saver",
    "Economy Value",
    "Economy Flex",
    "Premium Economy",
    "Business Value",
    "Business Flex",
    "Non-Rev",
]
ft = pd.crosstab(df["segment"], df["Farebrand"])
ft_pct = ft.div(ft.sum(axis=1), axis=0) * 100
ft_pct = ft_pct.reindex([s for s in SEG_ORDER if s in ft_pct.index])
ft_pct = ft_pct[[c for c in fb_order if c in ft_pct.columns]]

fig, ax = plt.subplots(figsize=(13, 7))
fig.patch.set_facecolor("#111827")
sns.heatmap(
    ft_pct.round(1),
    annot=True,
    fmt=".1f",
    cmap=sns.color_palette("Greens", as_cmap=True),
    ax=ax,
    linewidths=0.5,
    linecolor="#111827",
    cbar_kws={"label": "% within segment", "shrink": 0.7},
)
ax.set_title("Farebrand Mix by Proposed Segment (%)", fontweight="bold", pad=12, color="#F9FAFB")
ax.set_xlabel("Farebrand")
ax.set_ylabel("")
plt.xticks(rotation=25, ha="right")
save(fig, "28_segment_farebrand_heatmap")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 29 — Booking Month by Segment (Stacked / Grouped Bar)
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 29 – Booking Month by Segment")
month_names = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}
plot_segs_bm = [s for s in SEG_ORDER if s not in ("Mabuhay Loyalist", "Unassigned")]

fig, axes = plt.subplots(2, 5, figsize=(16, 7), sharey=False)
fig.patch.set_facecolor("#111827")
fig.suptitle(
    "PNR Booking Month Distribution by Segment\n(All flights: January 2025; booking dates span Jan 2024–Jan 2025)",
    fontsize=10,
    color="#F9FAFB",
    y=1.01,
)

for ax, seg in zip(axes.flat, plot_segs_bm):
    sub = (
        df[df["segment"] == seg]["booking_month"].value_counts().reindex(range(1, 13), fill_value=0)
    )
    ax.bar(sub.index, sub.values, color=SEG_COLORS[seg], alpha=0.85, edgecolor="none")
    ax.set_title(seg, fontsize=8.5, fontweight="bold", color=SEG_COLORS[seg], pad=4)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels([month_names[m][0] for m in range(1, 13)], fontsize=7)
    ax.tick_params(axis="y", labelsize=7)
    total = sub.sum()
    ax.set_xlabel(f"n={total:,}", fontsize=7, color="#9CA3AF")
    peak = sub.idxmax()
    ax.axvline(peak, color="white", ls="--", lw=1, alpha=0.5)

plt.tight_layout()
save(fig, "29_booking_month_by_segment")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 30 — PAX Count Distribution by Segment
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 30 – PAX Count by Segment")
fig, axes = plt.subplots(2, 5, figsize=(16, 7), sharey=False)
fig.patch.set_facecolor("#111827")
fig.suptitle(
    "PAX Count Distribution by Segment  (clipped at 10+)", fontsize=10, color="#F9FAFB", y=1.01
)

for ax, seg in zip(axes.flat, plot_segs_bm):
    sub = df[df["segment"] == seg]["PAX Count"].clip(1, 10)
    counts = sub.value_counts().reindex(range(1, 11), fill_value=0)
    ax.bar(counts.index, counts.values, color=SEG_COLORS[seg], alpha=0.85, edgecolor="none")
    ax.set_title(seg, fontsize=8.5, fontweight="bold", color=SEG_COLORS[seg], pad=4)
    ax.set_xticks(range(1, 11))
    ax.set_xticklabels([str(i) if i < 10 else "10+" for i in range(1, 11)], fontsize=7)
    ax.tick_params(axis="y", labelsize=7)
    med = sub.median()
    ax.set_xlabel(f"median={med:.0f} pax", fontsize=7, color="#9CA3AF")

plt.tight_layout()
save(fig, "30_pax_count_by_segment")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 31 — New Segment Deep Dive: Pilgrimage
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 31 – Pilgrimage Deep Dive")
pil = df[df["segment"] == "Pilgrimage"]

fig = plt.figure(figsize=(14, 5))
fig.patch.set_facecolor("#111827")
fig.suptitle(
    "Pilgrimage / Religious Traveler — Segment Deep Dive\n"
    f"(Proxy: PAX ≥ 4 + Traditional Travel Agency, n={len(pil):,})",
    fontsize=10,
    color="#F9FAFB",
    y=1.01,
)
gs = gridspec.GridSpec(1, 3, figure=fig, wspace=0.35)

ax1 = fig.add_subplot(gs[0])
bm = pil["booking_month"].value_counts().reindex(range(1, 13), fill_value=0)
ax1.bar(bm.index, bm.values, color="#F97316", alpha=0.85, edgecolor="none")
ax1.set_title("Booking Month", fontsize=9, color="#F97316")
ax1.set_xticks(range(1, 13))
ax1.set_xticklabels(["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"], fontsize=7)
ax1.set_ylabel("PNR Count")
ax1.axvspan(2.5, 4.5, alpha=0.12, color="#F97316", label="Holy Week window")
ax1.legend(fontsize=7, facecolor="#1F2937", edgecolor="#374151", labelcolor="#F9FAFB")

ax2 = fig.add_subplot(gs[1])
top_routes = pil["Sector"].value_counts().head(8)
ax2.barh(
    top_routes.index[::-1], top_routes.values[::-1], color="#F97316", alpha=0.85, edgecolor="none"
)
ax2.set_title("Top O&D Sectors", fontsize=9, color="#F97316")
ax2.set_xlabel("Count")

ax3 = fig.add_subplot(gs[2])
pax_dist = pil["PAX Count"].clip(1, 15).value_counts().sort_index()
ax3.bar(pax_dist.index, pax_dist.values, color="#F97316", alpha=0.85, edgecolor="none")
ax3.set_title("Group Size (PAX Count)", fontsize=9, color="#F97316")
ax3.set_xlabel("Passengers per Booking")
ax3.set_ylabel("Count")

save(fig, "31_pilgrimage_deep_dive")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 32 — New Segment Deep Dive: Family
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 32 – Family Deep Dive")
fam = df[df["segment"] == "Family"]

fig = plt.figure(figsize=(14, 5))
fig.patch.set_facecolor("#111827")
fig.suptitle(
    f"Family Vacation Traveler — Segment Deep Dive\n(Proxy: PAX 3–5, n={len(fam):,})",
    fontsize=10,
    color="#F9FAFB",
    y=1.01,
)
gs = gridspec.GridSpec(1, 3, figure=fig, wspace=0.35)

ax1 = fig.add_subplot(gs[0])
bm = fam["booking_month"].value_counts().reindex(range(1, 13), fill_value=0)
ax1.bar(bm.index, bm.values, color="#06B6D4", alpha=0.85, edgecolor="none")
ax1.set_title("Booking Month", fontsize=9, color="#06B6D4")
ax1.set_xticks(range(1, 13))
ax1.set_xticklabels(["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"], fontsize=7)
ax1.set_ylabel("PNR Count")
ax1.axvspan(10.5, 12.5, alpha=0.12, color="#06B6D4", label="Christmas season")
ax1.legend(fontsize=7, facecolor="#1F2937", edgecolor="#374151", labelcolor="#F9FAFB")

ax2 = fig.add_subplot(gs[1])
reg = fam["Region"].value_counts().head(7)
ax2.barh(reg.index[::-1], reg.values[::-1], color="#06B6D4", alpha=0.85, edgecolor="none")
ax2.set_title("Region Distribution", fontsize=9, color="#06B6D4")
ax2.set_xlabel("PNR Count")

ax3 = fig.add_subplot(gs[2])
ch = fam["Ticketing Channel"].fillna("Unknown").value_counts().head(6)
ax3.barh(ch.index[::-1], ch.values[::-1], color="#06B6D4", alpha=0.85, edgecolor="none")
ax3.set_title("Booking Channel", fontsize=9, color="#06B6D4")
ax3.set_xlabel("PNR Count")

save(fig, "32_family_deep_dive")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 33 — New Segment Deep Dive: Digital Nomad
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 33 – Digital Nomad Deep Dive")
dn = df[df["segment"] == "Digital Nomad"]

fig = plt.figure(figsize=(14, 5))
fig.patch.set_facecolor("#111827")
fig.suptitle(
    "Digital Nomad / Remote Worker — Segment Deep Dive\n"
    f"(Proxy: Solo + ASEAN + WEB/APP + Economy Flex/Value, n={len(dn):,})",
    fontsize=10,
    color="#F9FAFB",
    y=1.01,
)
gs = gridspec.GridSpec(1, 3, figure=fig, wspace=0.35)

ax1 = fig.add_subplot(gs[0])
bm = dn["booking_month"].value_counts().reindex(range(1, 13), fill_value=0)
ax1.bar(bm.index, bm.values, color="#A78BFA", alpha=0.85, edgecolor="none")
ax1.set_title("Booking Month", fontsize=9, color="#A78BFA")
ax1.set_xticks(range(1, 13))
ax1.set_xticklabels(["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"], fontsize=7)
ax1.set_ylabel("PNR Count")

ax2 = fig.add_subplot(gs[1])
top_s = dn["Sector"].value_counts().head(8)
ax2.barh(top_s.index[::-1], top_s.values[::-1], color="#A78BFA", alpha=0.85, edgecolor="none")
ax2.set_title("Top ASEAN O&D Sectors", fontsize=9, color="#A78BFA")
ax2.set_xlabel("PNR Count")

ax3 = fig.add_subplot(gs[2])
lt = dn["lead_time"].dropna().clip(0, 120)
ax3.hist(lt, bins=30, color="#A78BFA", alpha=0.85, edgecolor="none")
ax3.axvline(lt.mean(), color="white", ls="--", lw=1.5, label=f"Mean {lt.mean():.0f}d")
ax3.axvline(lt.median(), color="#F59E0B", ls="--", lw=1.5, label=f"Median {lt.median():.0f}d")
ax3.set_title("Lead Time Distribution", fontsize=9, color="#A78BFA")
ax3.set_xlabel("Days Before Departure")
ax3.set_ylabel("Count")
ax3.legend(fontsize=7, facecolor="#1F2937", edgecolor="#374151", labelcolor="#F9FAFB")

save(fig, "33_digital_nomad_deep_dive")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 34 — Radar Chart: 5-Feature Segment Fingerprints
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 34 – Segment Radar Fingerprints")


def norm(series, lo=None, hi=None):
    lo = lo or series.min()
    hi = hi or series.max()
    return ((series - lo) / (hi - lo)).clip(0, 1)


# 5 dimensions, all 0–1 normalised
dims = ["Avg Fare/PAX", "Lead Time", "Group Size", "Intl Route %", "Flex Fare %"]
seg_radar = {}
for seg in SEG_ORDER:
    if seg in ("Mabuhay Loyalist",):
        continue
    sub = df[df["segment"] == seg]
    if len(sub) < 10:
        continue
    fare_n = sub["fare_per_pax"].median() / 1000
    lead_n = sub["lead_time"].median() / 90
    grp_n = (sub["PAX Count"].median() - 1) / 9
    intl_n = (sub["Entity"] == "INT").mean()
    flex_n = sub["Farebrand"].isin(["Economy Flex", "Business Flex"]).mean()
    seg_radar[seg] = [min(fare_n, 1), min(lead_n, 1), min(grp_n, 1), intl_n, flex_n]

categories = dims
N = len(categories)
angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
angles += angles[:1]

fig = plt.figure(figsize=(14, 10))
fig.patch.set_facecolor("#111827")
fig.suptitle(
    "Segment Fingerprints — 5-Dimension Radar\n"
    "(Avg Fare/PAX · Lead Time · Group Size · International % · Flex Fare %)",
    fontsize=10,
    color="#F9FAFB",
    y=1.01,
)

n_segs = len(seg_radar)
cols = 5
rows = (n_segs + cols - 1) // cols
for idx, (seg, values) in enumerate(seg_radar.items()):
    ax = fig.add_subplot(rows, cols, idx + 1, polar=True)
    ax.set_facecolor("#1F2937")
    vals = values + values[:1]
    color = SEG_COLORS[seg]
    ax.fill(angles, vals, color=color, alpha=0.25)
    ax.plot(angles, vals, color=color, linewidth=2)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(["Fare", "Lead", "Group", "Intl", "Flex"], fontsize=7, color="#9CA3AF")
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75])
    ax.set_yticklabels([])
    ax.grid(color="#374151", linewidth=0.5)
    ax.set_title(seg, fontsize=8.5, fontweight="bold", color=color, pad=8)
    # Add dot on each axis tip
    for angle, val in zip(angles[:-1], values):
        ax.plot(angle, val, "o", color=color, markersize=4)

plt.tight_layout()
save(fig, "34_segment_radar_fingerprints")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 35 — Segment Overlap / Ambiguity Analysis
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 35 – Unassigned Record Analysis")
unassigned = df[df["segment"] == "Unassigned"]

fig, axes = plt.subplots(1, 3, figsize=(14, 5))
fig.patch.set_facecolor("#111827")
fig.suptitle(
    f"Unassigned Records Analysis  (n={len(unassigned):,}, {len(unassigned) / len(df) * 100:.1f}% of dataset)\n"
    "These records require additional features (Loyalty, Length of Stay) to classify",
    fontsize=10,
    color="#F9FAFB",
    y=1.02,
)

# Farebrand of unassigned
fb = unassigned["Farebrand"].value_counts().head(8)
axes[0].barh(fb.index[::-1], fb.values[::-1], color="#374151", edgecolor="none")
axes[0].set_title("Farebrand Distribution", fontsize=9, color="#9CA3AF")
axes[0].set_xlabel("Count")
for bar in axes[0].patches:
    axes[0].text(
        bar.get_width() + 10,
        bar.get_y() + bar.get_height() / 2,
        f"{bar.get_width():,}",
        va="center",
        fontsize=7,
        color="#9CA3AF",
    )

# Region of unassigned
rg = unassigned["Region"].value_counts().head(8)
axes[1].barh(rg.index[::-1], rg.values[::-1], color="#374151", edgecolor="none")
axes[1].set_title("Region Distribution", fontsize=9, color="#9CA3AF")
axes[1].set_xlabel("Count")

# Lead time of unassigned
lt = unassigned["lead_time"].dropna().clip(0, 150)
axes[2].hist(lt, bins=40, color="#374151", edgecolor="none", alpha=0.9)
axes[2].axvline(lt.mean(), color="#F59E0B", ls="--", lw=1.5, label=f"Mean {lt.mean():.0f}d")
axes[2].axvline(lt.median(), color="#60A5FA", ls="--", lw=1.5, label=f"Median {lt.median():.0f}d")
axes[2].set_title("Lead Time Distribution", fontsize=9, color="#9CA3AF")
axes[2].set_xlabel("Days Before Departure")
axes[2].set_ylabel("Count")
axes[2].legend(fontsize=7, facecolor="#1F2937", edgecolor="#374151", labelcolor="#F9FAFB")

plt.tight_layout()
save(fig, "35_unassigned_analysis")


print("\nAll segment EDA graphs saved to ./eda_output/")
print("New files: 23 through 35")
