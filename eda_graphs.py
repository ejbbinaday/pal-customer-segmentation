import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from pathlib import Path

# ── Setup ──────────────────────────────────────────────────────────────────────
OUTPUT = Path("eda_output")
OUTPUT.mkdir(exist_ok=True)

PAL_BLUE   = "#003B8E"
PAL_RED    = "#C0392B"
PAL_GOLD   = "#F0A500"
PAL_LIGHT  = "#5B9BD5"
PAL_GREY   = "#7F8C8D"
PALETTE    = [PAL_BLUE, PAL_RED, PAL_GOLD, PAL_LIGHT, "#27AE60", "#8E44AD", PAL_GREY, "#E67E22"]

sns.set_theme(style="whitegrid", font_scale=1.05)
plt.rcParams.update({"figure.dpi": 150, "savefig.bbox": "tight", "savefig.dpi": 150})

# ── Load & Clean ───────────────────────────────────────────────────────────────
df = pd.read_csv("sample-features.csv")
df["Average Fare"]    = df["Average Fare"].str.replace("$", "", regex=False).astype(float)
df["PNRCreationDate"] = pd.to_datetime(df["PNRCreationDate"], dayfirst=True, errors="coerce")
df["Flight Date"]     = pd.to_datetime(df["Flight Date"],     dayfirst=True, errors="coerce")
df["lead_time"]       = (df["Flight Date"] - df["PNRCreationDate"]).dt.days
df["travel_month"]    = df["Flight Date"].dt.month
df["fare_per_pax"]    = df["Average Fare"] / df["PAX Count"]

bins   = [-1, 0, 3, 7, 14, 30, 60, 9999]
labels = ["Same-day", "1–3d", "4–7d", "8–14d", "15–30d", "31–60d", "60d+"]
df["lead_bucket"] = pd.cut(df["lead_time"], bins=bins, labels=labels)

SEGMENT_PALETTE = {
    "Corporate":        PAL_BLUE,
    "Mabuhay Loyalist": "#8E44AD",
    "OFW Traveler":     PAL_RED,
    "Premium Bleisure": PAL_GOLD,
    "Balikbayan/VFR":   "#27AE60",
    "Budget Leisure":   PAL_LIGHT,
    "Last-Minute":      PAL_GREY,
}

def save(fig, name):
    fig.savefig(OUTPUT / f"{name}.png")
    plt.close(fig)
    print(f"  saved → eda_output/{name}.png")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 1 — Missing-Value Heatmap
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 01 – Missing Values")
null_pct = (df.isnull().sum() / len(df) * 100).sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(10, 6))
colors = [PAL_RED if v > 50 else PAL_GOLD if v > 5 else PAL_LIGHT for v in null_pct]
bars = ax.barh(null_pct.index, null_pct.values, color=colors)
ax.set_xlabel("Missing (%)")
ax.set_title("Missing Value Rate by Feature", fontweight="bold", pad=12)
ax.axvline(10, color=PAL_GREY, ls="--", lw=1, label="10% threshold")
for bar, val in zip(bars, null_pct.values):
    if val > 0:
        ax.text(val + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%", va="center", fontsize=8)
patches = [
    mpatches.Patch(color=PAL_RED,   label="≥ 50% missing"),
    mpatches.Patch(color=PAL_GOLD,  label="5–50% missing"),
    mpatches.Patch(color=PAL_LIGHT, label="< 5% missing"),
]
ax.legend(handles=patches, loc="lower right")
save(fig, "01_missing_values")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 2 — Entity Split (DOM vs INT)
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 02 – Entity Split")
entity_counts = df["Entity"].value_counts()
fig, ax = plt.subplots(figsize=(5, 5))
wedges, texts, autotexts = ax.pie(
    entity_counts, labels=entity_counts.index,
    colors=[PAL_BLUE, PAL_RED], autopct="%1.1f%%",
    startangle=90, wedgeprops=dict(edgecolor="white", linewidth=2)
)
for t in autotexts:
    t.set_fontsize(13); t.set_fontweight("bold"); t.set_color("white")
ax.set_title("Domestic vs International Split\n(Entity)", fontweight="bold")
save(fig, "02_entity_split")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 3 — Region Distribution
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 03 – Region Distribution")
region_counts = df["Region"].value_counts()
fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.bar(region_counts.index, region_counts.values,
              color=PALETTE[:len(region_counts)], edgecolor="white")
ax.set_title("Booking Volume by Region", fontweight="bold")
ax.set_ylabel("PNR Count")
ax.set_xlabel("")
plt.xticks(rotation=30, ha="right")
for bar in bars:
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 50,
            f"{bar.get_height():,}", ha="center", va="bottom", fontsize=8)
save(fig, "03_region_distribution")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 4 — Cabin Distribution
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 04 – Cabin Distribution")
cabin_map  = {"Y": "Economy (Y)", "W": "Premium Economy (W)", "J": "Business (J)"}
cabin_data = df["Cabin"].map(cabin_map).value_counts()
fig, ax = plt.subplots(figsize=(6, 5))
bars = ax.bar(cabin_data.index, cabin_data.values,
              color=[PAL_LIGHT, PAL_GOLD, PAL_BLUE], edgecolor="white", width=0.5)
ax.set_title("Cabin Class Distribution", fontweight="bold")
ax.set_ylabel("PNR Count")
for bar in bars:
    pct = bar.get_height() / len(df) * 100
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 100,
            f"{pct:.1f}%", ha="center", fontsize=10, fontweight="bold")
save(fig, "04_cabin_distribution")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 5 — Farebrand Distribution
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 05 – Farebrand Distribution")
fb = df["Farebrand"].value_counts()
fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.barh(fb.index[::-1], fb.values[::-1], color=PALETTE[:len(fb)], edgecolor="white")
ax.set_title("Farebrand Distribution", fontweight="bold")
ax.set_xlabel("PNR Count")
for bar in bars:
    ax.text(bar.get_width() + 50, bar.get_y() + bar.get_height() / 2,
            f"{bar.get_width():,}", va="center", fontsize=9)
save(fig, "05_farebrand_distribution")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 6 — Ticketing Channel Distribution
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 06 – Ticketing Channel")
ch = df["Ticketing Channel"].fillna("Unknown").value_counts()
fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.barh(ch.index[::-1], ch.values[::-1], color=PALETTE[:len(ch)], edgecolor="white")
ax.set_title("Booking Volume by Ticketing Channel", fontweight="bold")
ax.set_xlabel("PNR Count")
for bar in bars:
    ax.text(bar.get_width() + 30, bar.get_y() + bar.get_height() / 2,
            f"{bar.get_width():,}", va="center", fontsize=9)
save(fig, "06_ticketing_channel")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 7 — Itinerary Type Distribution
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 07 – Itinerary Type")
it = df["Itinerary Type"].value_counts()
fig, ax = plt.subplots(figsize=(8, 4))
bars = ax.bar(it.index, it.values, color=PALETTE[:len(it)], edgecolor="white", width=0.55)
ax.set_title("Itinerary Type Distribution", fontweight="bold")
ax.set_ylabel("PNR Count")
plt.xticks(rotation=15, ha="right")
for bar in bars:
    pct = bar.get_height() / len(df) * 100
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 60,
            f"{pct:.1f}%", ha="center", fontsize=9)
save(fig, "07_itinerary_type")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 8 — Average Fare Distribution (log scale)
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 08 – Fare Distribution")
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
axes[0].hist(df["Average Fare"], bins=60, color=PAL_BLUE, edgecolor="white", alpha=0.85)
axes[0].set_title("Average Fare Distribution", fontweight="bold")
axes[0].set_xlabel("Fare (USD)")
axes[0].set_ylabel("Count")
axes[0].axvline(df["Average Fare"].mean(),   color=PAL_RED,  ls="--", label=f"Mean ${df['Average Fare'].mean():.0f}")
axes[0].axvline(df["Average Fare"].median(), color=PAL_GOLD, ls="--", label=f"Median ${df['Average Fare'].median():.0f}")
axes[0].legend()

axes[1].hist(np.log1p(df["Average Fare"]), bins=60, color=PAL_LIGHT, edgecolor="white", alpha=0.85)
axes[1].set_title("Average Fare Distribution (log scale)", fontweight="bold")
axes[1].set_xlabel("log(1 + Fare)")
axes[1].set_ylabel("Count")

fig.suptitle("Fare Analysis", fontsize=14, fontweight="bold", y=1.01)
save(fig, "08_fare_distribution")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 9 — Fare by Cabin (Boxplot)
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 09 – Fare by Cabin")
cabin_order  = ["Economy (Y)", "Premium Economy (W)", "Business (J)"]
df["Cabin Label"] = df["Cabin"].map({"Y": "Economy (Y)", "W": "Premium Economy (W)", "J": "Business (J)"})
fig, ax = plt.subplots(figsize=(8, 5))
sns.boxplot(data=df, x="Cabin Label", y="Average Fare", order=cabin_order,
            palette=[PAL_LIGHT, PAL_GOLD, PAL_BLUE], ax=ax,
            showfliers=False, width=0.45)
ax.set_title("Average Fare by Cabin Class", fontweight="bold")
ax.set_xlabel(""); ax.set_ylabel("Fare (USD)")
means = df.groupby("Cabin Label")["Average Fare"].mean()
for i, cab in enumerate(cabin_order):
    if cab in means.index:
        ax.text(i, means[cab] + 10, f"μ=${means[cab]:.0f}", ha="center",
                fontsize=9, color="black", fontweight="bold")
save(fig, "09_fare_by_cabin")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 10 — Fare by Region (Boxplot)
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 10 – Fare by Region")
region_order = df.groupby("Region")["Average Fare"].median().sort_values(ascending=False).index
fig, ax = plt.subplots(figsize=(12, 5))
sns.boxplot(data=df, x="Region", y="Average Fare", order=region_order,
            palette=PALETTE[:len(region_order)], ax=ax, showfliers=False, width=0.5)
ax.set_title("Average Fare by Region (excl. outliers)", fontweight="bold")
ax.set_ylabel("Fare (USD)"); ax.set_xlabel("")
plt.xticks(rotation=30, ha="right")
save(fig, "10_fare_by_region")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 11 — Booking Lead Time Distribution
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 11 – Lead Time Distribution")
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

axes[0].hist(df["lead_time"].dropna().clip(0, 200), bins=60,
             color=PAL_BLUE, edgecolor="white", alpha=0.85)
axes[0].set_title("Lead Time Distribution (0–200 days)", fontweight="bold")
axes[0].set_xlabel("Days Before Departure"); axes[0].set_ylabel("Count")
axes[0].axvline(df["lead_time"].mean(),   color=PAL_RED,  ls="--", label=f"Mean {df['lead_time'].mean():.0f}d")
axes[0].axvline(df["lead_time"].median(), color=PAL_GOLD, ls="--", label=f"Median {df['lead_time'].median():.0f}d")
axes[0].legend()

bucket_counts = df["lead_bucket"].value_counts().reindex(labels)
colors_lb = [PAL_GREY, PAL_LIGHT, PAL_BLUE, PAL_BLUE, PAL_GOLD, PAL_RED, PAL_RED]
bars = axes[1].bar(bucket_counts.index, bucket_counts.values, color=colors_lb, edgecolor="white")
axes[1].set_title("Lead Time Bucket Breakdown", fontweight="bold")
axes[1].set_xlabel("Booking Window"); axes[1].set_ylabel("PNR Count")
for bar in bars:
    pct = bar.get_height() / len(df) * 100
    axes[1].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 50,
                 f"{pct:.1f}%", ha="center", fontsize=8.5)

fig.suptitle("Booking Lead Time Analysis", fontsize=14, fontweight="bold", y=1.01)
save(fig, "11_lead_time_distribution")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 12 — Lead Time by Farebrand (Boxplot)
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 12 – Lead Time by Farebrand")
fb_order = df.groupby("Farebrand")["lead_time"].median().sort_values().index
fig, ax = plt.subplots(figsize=(11, 5))
sns.boxplot(data=df, x="Farebrand", y="lead_time", order=fb_order,
            palette=PALETTE[:len(fb_order)], ax=ax, showfliers=False, width=0.5)
ax.set_title("Booking Lead Time by Farebrand", fontweight="bold")
ax.set_ylabel("Lead Time (days)"); ax.set_xlabel("")
plt.xticks(rotation=20, ha="right")
save(fig, "12_lead_time_by_farebrand")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 13 — PAX Count Distribution
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 13 – PAX Count")
pax = df["PAX Count"].clip(0, 10).value_counts().sort_index()
fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(pax.index.astype(str).tolist()[:-1] + ["10+"],
              pax.values,
              color=[PAL_BLUE if i == 1 else PAL_LIGHT if i <= 4 else PAL_GOLD
                     for i in pax.index],
              edgecolor="white")
ax.set_title("PAX Count per Booking", fontweight="bold")
ax.set_xlabel("Passenger Count"); ax.set_ylabel("PNR Count")
for bar in bars:
    pct = bar.get_height() / len(df) * 100
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 30,
            f"{pct:.1f}%", ha="center", fontsize=8.5)
save(fig, "13_pax_count")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 14 — Day of Week Distribution
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 14 – Day of Week")
dow_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
dow = df["DOW"].value_counts().reindex(dow_order)
fig, ax = plt.subplots(figsize=(8, 4))
bars = ax.bar(dow.index, dow.values,
              color=[PAL_RED if d in ["Sat", "Sun"] else PAL_BLUE for d in dow.index],
              edgecolor="white")
ax.set_title("Departure Day of Week", fontweight="bold")
ax.set_ylabel("PNR Count")
weekend = mpatches.Patch(color=PAL_RED, label="Weekend")
weekday = mpatches.Patch(color=PAL_BLUE, label="Weekday")
ax.legend(handles=[weekday, weekend])
for bar in bars:
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 30,
            f"{bar.get_height():,}", ha="center", fontsize=8.5)
save(fig, "14_day_of_week")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 15 — Channel × Entity Heatmap
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 15 – Channel × Entity Heatmap")
ct = pd.crosstab(df["Ticketing Channel"].fillna("Unknown"), df["Entity"])
ct = ct.loc[ct.sum(axis=1).sort_values(ascending=False).index]
fig, ax = plt.subplots(figsize=(7, 7))
sns.heatmap(ct, annot=True, fmt="d", cmap="Blues", ax=ax,
            linewidths=0.5, linecolor="white", cbar_kws={"label": "PNR Count"})
ax.set_title("Ticketing Channel × Entity Heatmap", fontweight="bold")
ax.set_xlabel("Entity"); ax.set_ylabel("Ticketing Channel")
save(fig, "15_channel_entity_heatmap")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 16 — Segment Proxy Volume Summary
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 16 – Segment Proxy Volumes")
proxies = {
    "Corporate\n(Cabin J)":            (df["Cabin"] == "J").sum(),
    "OFW Traveler\n(Middle East)":     (df["Region"] == "Middle East").sum(),
    "Premium Bleisure\n(Cabin W)":     (df["Cabin"] == "W").sum(),
    "Balikbayan/VFR\n(INT→DOM Beyond)":(df["Itinerary Type"] == "Beyonds (INT - DOM)").sum(),
    "Budget Leisure\n(Eco Supersaver)":(df["Farebrand"] == "Economy Supersaver").sum(),
    "Last-Minute\n(lead ≤ 3d)":        (df["lead_time"] <= 3).sum(),
    "Sea Crew\n(OFW sub-type)":        (df["Ticketing Channel"] == "Sea Crew").sum(),
    "Corporate TMC\n(channel proxy)":  (df["Ticketing Channel"] == "TMC").sum(),
}
proxy_df = pd.Series(proxies).sort_values(ascending=True)
colors_p = [list(SEGMENT_PALETTE.values())[i % len(SEGMENT_PALETTE)]
            for i in range(len(proxy_df))]
fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.barh(proxy_df.index, proxy_df.values, color=colors_p[::-1], edgecolor="white")
ax.set_title("Segment Proxy Record Counts in Sample Data", fontweight="bold")
ax.set_xlabel("PNR Count")
for bar in bars:
    pct = bar.get_width() / len(df) * 100
    ax.text(bar.get_width() + 20, bar.get_y() + bar.get_height() / 2,
            f"{bar.get_width():,}  ({pct:.1f}%)", va="center", fontsize=9)
save(fig, "16_segment_proxy_volumes")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 17 — Lead Time by Segment Proxy (KDE)
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 17 – Lead Time KDE by Segment Proxy")
proxies_kde = {
    "Corporate (Cabin J)":          df.loc[df["Cabin"] == "J",              "lead_time"].dropna(),
    "OFW Traveler (Mid East)":      df.loc[df["Region"] == "Middle East",   "lead_time"].dropna(),
    "Premium Bleisure (Cabin W)":   df.loc[df["Cabin"] == "W",              "lead_time"].dropna(),
    "Balikbayan (INT→DOM Beyond)":  df.loc[df["Itinerary Type"] == "Beyonds (INT - DOM)", "lead_time"].dropna(),
    "Budget Leisure (Eco SS)":      df.loc[df["Farebrand"] == "Economy Supersaver", "lead_time"].dropna(),
    "Last-Minute (lead ≤ 3d)":      df.loc[df["lead_time"] <= 3,           "lead_time"].dropna(),
}
pal_kde = [PAL_BLUE, PAL_RED, PAL_GOLD, "#27AE60", PAL_LIGHT, PAL_GREY]
fig, ax = plt.subplots(figsize=(11, 5))
for (label, series), color in zip(proxies_kde.items(), pal_kde):
    clipped = series.clip(0, 180)
    if len(clipped) > 5:
        sns.kdeplot(clipped, ax=ax, label=label, color=color, linewidth=2.2, fill=True, alpha=0.12)
ax.set_title("Lead Time Distribution by Segment Proxy", fontweight="bold")
ax.set_xlabel("Days Before Departure (clipped at 180)")
ax.set_ylabel("Density")
ax.legend(fontsize=8.5, loc="upper right")
save(fig, "17_lead_time_kde_by_proxy")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 18 — Fare per PAX by Segment Proxy (Boxplot)
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 18 – Fare per PAX by Segment Proxy")
df["segment_proxy"] = "Other"
df.loc[df["Cabin"] == "J",                             "segment_proxy"] = "Corporate (J)"
df.loc[df["Cabin"] == "W",                             "segment_proxy"] = "Prem Bleisure (W)"
df.loc[df["Region"] == "Middle East",                  "segment_proxy"] = "OFW (Mid East)"
df.loc[df["Itinerary Type"] == "Beyonds (INT - DOM)",  "segment_proxy"] = "Balikbayan"
df.loc[df["Farebrand"] == "Economy Supersaver",        "segment_proxy"] = "Budget Leisure"
df.loc[df["lead_time"] <= 3,                           "segment_proxy"] = "Last-Minute"

proxy_order = (df.groupby("segment_proxy")["fare_per_pax"]
               .median().sort_values(ascending=False).index)
proxy_colors = [PAL_BLUE, PAL_GOLD, PAL_RED, "#27AE60", PAL_LIGHT, PAL_GREY, "#E67E22"]
fig, ax = plt.subplots(figsize=(12, 5))
sns.boxplot(data=df, x="segment_proxy", y="fare_per_pax", order=proxy_order,
            palette=proxy_colors[:len(proxy_order)], ax=ax, showfliers=False, width=0.5)
ax.set_title("Fare per PAX by Segment Proxy", fontweight="bold")
ax.set_ylabel("Fare per PAX (USD)"); ax.set_xlabel("")
plt.xticks(rotation=20, ha="right")
save(fig, "18_fare_per_pax_by_proxy")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 19 — Ticketing Channel by Segment Proxy (Stacked Bar)
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 19 – Channel × Segment Proxy Heatmap")
ch_proxy = pd.crosstab(
    df["segment_proxy"],
    df["Ticketing Channel"].fillna("Unknown")
)
ch_proxy_pct = ch_proxy.div(ch_proxy.sum(axis=1), axis=0) * 100
fig, ax = plt.subplots(figsize=(13, 6))
sns.heatmap(ch_proxy_pct.round(1), annot=True, fmt=".1f", cmap="YlOrRd",
            ax=ax, linewidths=0.4, linecolor="white",
            cbar_kws={"label": "% of Segment"})
ax.set_title("Ticketing Channel Mix by Segment Proxy (%)", fontweight="bold")
ax.set_xlabel("Ticketing Channel"); ax.set_ylabel("Segment Proxy")
plt.xticks(rotation=30, ha="right")
save(fig, "19_channel_by_proxy_heatmap")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 20 — Top 15 O&D Sectors by Booking Volume
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 20 – Top 15 O&D Sectors")
top_sectors = df["Sector"].value_counts().head(15)
fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.bar(top_sectors.index, top_sectors.values,
              color=PALETTE * 3, edgecolor="white")
ax.set_title("Top 15 O&D Sectors by Booking Volume", fontweight="bold")
ax.set_ylabel("PNR Count"); ax.set_xlabel("Sector")
plt.xticks(rotation=35, ha="right")
for bar in bars:
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 30,
            f"{bar.get_height():,}", ha="center", fontsize=7.5)
save(fig, "20_top_sectors")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 21 — Negative Learning Rule Feasibility
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 21 – Negative Learning Rule Feasibility")
rules = [
    ("Booked 60+d · Economy\n· No Loyalty ID → Not Corporate",    2, 1),
    ("Cargo add-on · Economy\n· MNL-Riyadh → Not Bleisure",       0, 3),
    ("0–3d · Promo fare\n· No flexibility → Not Last-Minute",     3, 0),
    ("Group 5+ · Dec–Jan\n→ Not Solo Budget Leisure",             3, 0),
    ("Business cabin · Same-day\n· Loyalty → Corp/Bleisure only", 1, 2),
    ("Mid East · No Miles\n· Cargo → OFW/Balikbayan only",        1, 2),
]
labels_r = [r[0] for r in rules]
avail     = [r[1] for r in rules]
missing   = [r[2] for r in rules]
fig, ax = plt.subplots(figsize=(11, 6))
y = np.arange(len(labels_r))
ax.barh(y, [3]*len(y), color="#ECEFF1", edgecolor="white", height=0.6)
ax.barh(y, avail,   color="#27AE60", edgecolor="white", height=0.6, label="Columns Available")
ax.barh(y, missing, left=avail, color=PAL_RED, edgecolor="white", height=0.6, label="Columns Missing")
ax.set_yticks(y); ax.set_yticklabels(labels_r, fontsize=9)
ax.set_xticks([0, 1, 2, 3]); ax.set_xticklabels(["0", "1/3", "2/3", "3/3"])
ax.set_xlabel("Feature Coverage (out of 3 key columns per rule)")
ax.set_title("Negative Learning Rule: Feature Coverage in Sample Data", fontweight="bold")
ax.legend(loc="lower right")
ax.axvline(3, color=PAL_GREY, ls="--", lw=1)
ax.invert_yaxis()
save(fig, "21_negative_learning_feasibility")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 22 — Missing Features Roadmap (Priority Matrix)
# ══════════════════════════════════════════════════════════════════════════════
print("Generating Fig 22 – Missing Features Priority Matrix")
features = {
    "Loyalty status\n(Mabuhay Miles tier)":    (5, 5),
    "Length of stay":                           (5, 4),
    "Departure time":                           (4, 3),
    "Cargo/Baggage\nadd-on flag":               (4, 4),
    "Prior booking\ncount (12mo)":              (3, 3),
    "Meal pref / SSR":                          (3, 2),
    "Seat selection":                           (2, 2),
    "Passenger\nnationality":                   (3, 3),
    "Return ticket\nindicator":                 (3, 2),
    "Booking mod.\ncount":                      (2, 2),
    "Travel season\nholiday flag":              (2, 4),
    "Companion PNR\ncount":                     (2, 2),
}
fig, ax = plt.subplots(figsize=(9, 7))
for label, (impact, feasibility) in features.items():
    jitter = np.random.RandomState(hash(label) % 1000).uniform(-0.12, 0.12, 2)
    color = PAL_RED if impact >= 4 else PAL_GOLD if impact >= 3 else PAL_LIGHT
    ax.scatter(feasibility + jitter[0], impact + jitter[1], s=320, color=color,
               edgecolors="white", zorder=3, linewidth=1.5)
    ax.annotate(label, (feasibility + jitter[0], impact + jitter[1]),
                textcoords="offset points", xytext=(6, 4), fontsize=7.5)
ax.axhline(3.5, color=PAL_GREY, ls="--", lw=1)
ax.axvline(3.5, color=PAL_GREY, ls="--", lw=1)
ax.set_xlim(1, 6); ax.set_ylim(1, 6)
ax.set_xlabel("Feasibility (ease of sourcing from PAL systems)", fontsize=10)
ax.set_ylabel("Segmentation Impact", fontsize=10)
ax.set_title("Recommended Missing Features — Priority Matrix", fontweight="bold")
ax.text(4.8, 5.5, "Quick Wins", color=PAL_BLUE, fontsize=9, fontweight="bold")
ax.text(1.1, 5.5, "High Impact\n(Hard to get)", color=PAL_RED, fontsize=9, fontweight="bold")
patches = [
    mpatches.Patch(color=PAL_RED,   label="High impact (4–5)"),
    mpatches.Patch(color=PAL_GOLD,  label="Medium impact (3)"),
    mpatches.Patch(color=PAL_LIGHT, label="Lower impact (1–2)"),
]
ax.legend(handles=patches, loc="lower right", fontsize=8)
save(fig, "22_missing_features_priority")


print("\nAll 22 graphs saved to ./eda_output/")
