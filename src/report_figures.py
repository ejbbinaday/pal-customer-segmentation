"""Generate report figures from the REAL booking features (`pal_features_booking.parquet`).

Produces the EDA charts and the preliminary-cluster diagnostic used in the status report
(`docs/status-report.*`). All figures are drawn from the real 22.9M-booking table — EDA aggregates
run in DuckDB over the full set; the clustering panels use the same 60k stratified sample as
`cluster_diagnostic.py`. Read-only on features; writes PNGs to `outputs/report_real/figs/`.

Run:  python src/report_figures.py
"""

from pathlib import Path

import duckdb
import matplotlib as mpl
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from stepmix.stepmix import StepMix

import sub_segment as ss
from pal_colors import SEG_COLORS

ROOT = Path(__file__).resolve().parents[1]
BOOKING = ROOT / "data" / "interim" / "pal_features_booking.parquet"
FIGS = ROOT / "outputs" / "report_real" / "figs"

SEED = 42
SAMPLE = 60_000
K_RANGE = range(3, 10)

# ---- report palette (matches docs/status-report styling) ----
INK = "#14213A"
INK_SOFT = "#4A5468"
INK_FAINT = "#7A8298"
SKY = "#12608F"
SIGNAL = "#B45309"
RULE = "#D8D8CF"
PAPER = "#FFFFFF"

mpl.rcParams.update(
    {
        "figure.facecolor": PAPER,
        "axes.facecolor": PAPER,
        "savefig.facecolor": PAPER,
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.edgecolor": RULE,
        "axes.linewidth": 1.0,
        "axes.grid": True,
        "grid.color": "#EDEDE6",
        "grid.linewidth": 0.8,
        "axes.titlecolor": INK,
        "axes.labelcolor": INK_SOFT,
        "text.color": INK,
        "xtick.color": INK_SOFT,
        "ytick.color": INK_SOFT,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 150,
    }
)


def save(fig, name: str) -> None:
    fig.tight_layout()
    path = FIGS / name
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print("  wrote", path.name)


# --------------------------------------------------------------------------- EDA (full data)
def fig_segment_distribution(con) -> None:
    df = con.execute(f"""
        SELECT proxy_segment seg, count(*) n, avg(rev_pos) avg_rev
        FROM read_parquet('{BOOKING}') GROUP BY 1 ORDER BY n DESC
    """).fetchdf()
    df["pct"] = 100 * df["n"] / df["n"].sum()
    colors = [SEG_COLORS.get(s, "#888") for s in df["seg"]]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5.2))
    y = np.arange(len(df))[::-1]
    ax1.barh(y, df["pct"], color=colors, edgecolor="white", linewidth=0.6)
    ax1.set_yticks(y)
    ax1.set_yticklabels(df["seg"])
    ax1.set_xlabel("Share of bookings (%)")
    ax1.set_title("Segment volume", fontweight="bold", loc="left")
    for yi, p in zip(y, df["pct"]):
        ax1.text(p + 0.4, yi, f"{p:.1f}%", va="center", fontsize=9, color=INK_SOFT)
    ax1.set_xlim(0, df["pct"].max() * 1.15)

    ax2.barh(y, df["avg_rev"], color=colors, edgecolor="white", linewidth=0.6)
    ax2.set_yticks(y)
    ax2.set_yticklabels([])
    ax2.set_xlabel("Avg revenue per booking (USD)")
    ax2.set_title("Segment value", fontweight="bold", loc="left")
    for yi, r in zip(y, df["avg_rev"]):
        ax2.text(r + 15, yi, f"${r:,.0f}", va="center", fontsize=9, color=INK_SOFT)
    ax2.set_xlim(0, df["avg_rev"].max() * 1.18)
    fig.suptitle(
        "Proxy segment distribution — 22.9M bookings (value rises across the ladder)",
        fontsize=12.5,
        fontweight="bold",
        color=INK,
        x=0.01,
        ha="left",
    )
    save(fig, "eda_01_segments.png")


def fig_route_region(con) -> None:
    df = con.execute(f"""
        SELECT coalesce(dest_region,'Philippines (domestic)') region, count(*) n
        FROM read_parquet('{BOOKING}') GROUP BY 1 ORDER BY n DESC
    """).fetchdf()
    df["pct"] = 100 * df["n"] / df["n"].sum()
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    x = np.arange(len(df))
    bars = ax.bar(x, df["pct"], color=SKY, edgecolor="white", linewidth=0.6)
    bars[0].set_color(INK)
    ax.set_xticks(x)
    ax.set_xticklabels(df["region"], rotation=25, ha="right", fontsize=9.5)
    ax.set_ylabel("Share of bookings (%)")
    ax.set_title(
        "Route network is domestic-heavy — international split drives segmentation",
        fontweight="bold",
        loc="left",
        fontsize=12,
    )
    for xi, p in zip(x, df["pct"]):
        ax.text(xi, p + 0.6, f"{p:.0f}%", ha="center", fontsize=9, color=INK_SOFT)
    ax.set_ylim(0, df["pct"].max() * 1.15)
    save(fig, "eda_02_region.png")


def fig_lead_and_value(con) -> None:
    lead = con.execute(f"""
        SELECT least(greatest(lead_days,0),120) d, count(*) n
        FROM read_parquet('{BOOKING}') GROUP BY 1 ORDER BY 1
    """).fetchdf()
    tier = con.execute(f"""
        SELECT max_tier t, count(*) n
        FROM read_parquet('{BOOKING}') WHERE max_tier IS NOT NULL GROUP BY 1 ORDER BY 1
    """).fetchdf()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.1))
    ax1.fill_between(lead["d"], lead["n"] / 1e6, color=SKY, alpha=0.25)
    ax1.plot(lead["d"], lead["n"] / 1e6, color=SKY, linewidth=1.8)
    ax1.axvline(3, color=SIGNAL, linestyle="--", linewidth=1.2)
    ax1.text(4, ax1.get_ylim()[1] * 0.9, "Last-Minute ≤3d", color=SIGNAL, fontsize=9)
    ax1.set_xlabel("Booking lead time (days before departure)")
    ax1.set_ylabel("Bookings (millions)")
    ax1.set_title("Booking lead time", fontweight="bold", loc="left")

    tier_names = {
        1: "Supersaver",
        2: "Saver",
        3: "Value",
        4: "Flex",
        5: "Prem Econ",
        6: "Bus Value",
        7: "Bus Flex",
    }
    x = tier["t"].to_numpy()
    ax2.bar(x, tier["n"] / 1e6, color=INK, edgecolor="white", linewidth=0.6)
    ax2.set_xticks(x)
    ax2.set_xticklabels(
        [tier_names.get(int(t), str(t)) for t in x], rotation=25, ha="right", fontsize=9
    )
    ax2.set_ylabel("Bookings (millions)")
    ax2.set_title("Farebrand value tier (top tier per booking)", fontweight="bold", loc="left")
    fig.suptitle(
        "Timing and value: most travel is economy booked weeks ahead",
        fontsize=12.5,
        fontweight="bold",
        color=INK,
        x=0.01,
        ha="left",
    )
    save(fig, "eda_03_lead_value.png")


# ------------------------------------------------------ preliminary clusters (60k sample)
def load_sample(con) -> pd.DataFrame:
    df = con.execute(f"""
        SELECT lead_days, max_tier value_tier, rev_pos, n_coupons,
               coalesce(dest_region,'Domestic') dest_region,
               round_trip::INT round_trip, foreign_issue::INT foreign_issue,
               is_group::INT is_group, connecting::INT connecting,
               peak_month::INT peak_month, corp_channel::INT corp_channel, proxy_segment
        FROM read_parquet('{BOOKING}') USING SAMPLE {SAMPLE} ROWS (reservoir, {SEED})
    """).fetchdf()
    df["lead_days"] = df["lead_days"].clip(0, 365)
    df["value_tier"] = df["value_tier"].fillna(df["value_tier"].median())
    df["log_rev"] = np.log1p(df["rev_pos"].clip(lower=0))
    df["n_coupons"] = df["n_coupons"].clip(1, 8)
    return df


def codes_for_lca(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    out["lead_bucket"] = pd.cut(df["lead_days"], [-1, 3, 14, 45, 120, 999], labels=False)
    out["value_tier"] = df["value_tier"].round().astype(int) - 1
    out["rev_bucket"] = pd.qcut(df["log_rev"].rank(method="first"), 5, labels=False)
    out["n_coupons_b"] = np.clip(df["n_coupons"] - 1, 0, 3)
    out["dest_region"] = df["dest_region"].astype("category").cat.codes
    for b in [
        "round_trip",
        "foreign_issue",
        "is_group",
        "connecting",
        "peak_month",
        "corp_channel",
    ]:
        out[b] = df[b].astype(int)
    return out.astype(int)


def fig_lca_bic(bic_tbl: pd.DataFrame) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.1))
    ax1.plot(bic_tbl["k"], bic_tbl["BIC"] / 1e6, "o-", color=SKY, linewidth=2, markersize=6)
    ax1.set_xlabel("Number of latent classes (k)")
    ax1.set_ylabel("BIC (millions, lower = better)")
    ax1.set_title("No elbow → no natural k", fontweight="bold", loc="left", pad=10)
    lo, hi = bic_tbl["BIC"].min() / 1e6, bic_tbl["BIC"].max() / 1e6
    ax1.annotate(
        "BIC keeps falling —\nthe base is a continuum",
        xy=(9, lo),
        xytext=(5.2, lo + 0.55 * (hi - lo)),
        color=SIGNAL,
        fontsize=9.5,
        arrowprops=dict(arrowstyle="->", color=SIGNAL),
    )

    ax2.plot(bic_tbl["k"], bic_tbl["ARI_vs_proxy"], "s-", color=INK, linewidth=2, markersize=6)
    ax2.set_xlabel("Number of latent classes (k)")
    ax2.set_ylabel("ARI vs. rule-based segments")
    ax2.set_ylim(0, 1)
    ax2.axhspan(0, 0.4, color=SIGNAL, alpha=0.07)
    ax2.set_title("Only moderate agreement (ARI ≤ 0.34)", fontweight="bold", loc="left")
    fig.suptitle(
        "Why clustering is a refinement layer, not the labeller",
        fontsize=12.5,
        fontweight="bold",
        color=INK,
        x=0.01,
        ha="left",
    )
    save(fig, "clust_01_bic_ari.png")


def fig_pca(df: pd.DataFrame, labels: np.ndarray, k_star: int) -> None:
    num = ["lead_days", "value_tier", "log_rev", "n_coupons"]
    bincols = [
        "round_trip",
        "foreign_issue",
        "is_group",
        "connecting",
        "peak_month",
        "corp_channel",
    ]
    region_oh = pd.get_dummies(df["dest_region"], prefix="r")
    x = np.hstack(
        [StandardScaler().fit_transform(df[num]), df[bincols].to_numpy(), region_oh.to_numpy()]
    )
    coords = PCA(n_components=2, random_state=SEED).fit_transform(x)

    rng = np.random.default_rng(SEED)
    idx = rng.choice(len(df), size=min(9000, len(df)), replace=False)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5.0))

    cl_colors = plt.cm.tab10(np.linspace(0, 1, k_star))
    for c in range(k_star):
        m = idx[labels[idx] == c]
        ax1.scatter(coords[m, 0], coords[m, 1], s=5, color=cl_colors[c], alpha=0.5, linewidths=0)
    ax1.set_title(f"LCA classes (k={k_star}) — no clean gaps", fontweight="bold", loc="left")

    for seg, col in SEG_COLORS.items():
        m = idx[df["proxy_segment"].to_numpy()[idx] == seg]
        if len(m):
            ax1_lbl = seg if seg != "Unassigned" else None
            ax2.scatter(
                coords[m, 0], coords[m, 1], s=5, color=col, alpha=0.5, linewidths=0, label=ax1_lbl
            )
    ax2.set_title("Same points, coloured by rule segment", fontweight="bold", loc="left")
    ax2.legend(markerscale=3, fontsize=7.5, loc="upper right", framealpha=0.9, ncol=1)

    for ax in (ax1, ax2):
        ax.set_xlabel("PC 1")
        ax.set_ylabel("PC 2")
        ax.grid(False)
    fig.suptitle(
        "Preliminary clusters (60k stratified sample, PCA projection)",
        fontsize=12.5,
        fontweight="bold",
        color=INK,
        x=0.01,
        ha="left",
    )
    save(fig, "clust_02_pca.png")


def _sub_label(row) -> str:
    name = ss.name_sub(row)
    if row["pct_conn"] >= 50:  # disambiguate same-named sibling sub-types
        name += " · connecting"
    return name


def fig_sub_segments(con) -> None:
    """LCA sub-types within the largest rule segments (mirrors sub_segment.py)."""
    parents = ["Budget/Adventure", "OFW/Migrant", "Balikbayan/VFR", "Last-Minute"]
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.4))
    for ax, seg in zip(axes.ravel(), parents):
        df = ss.load_parent(con, seg)
        k, labels = ss.best_lca(ss.code(df))
        df = df.assign(sub=labels)
        prof = (
            df.groupby("sub")
            .agg(
                n=("sub", "size"),
                med_lead=("lead_days", "median"),
                med_tier=("value_tier", "median"),
                med_rev=("rev_pos", "median"),
                pct_rt=("round_trip", lambda s: round(100 * s.mean())),
                pct_conn=("connecting", lambda s: round(100 * s.mean())),
            )
            .reset_index()
        )
        prof["pct"] = 100 * prof["n"] / prof["n"].sum()
        prof["label"] = prof.apply(_sub_label, axis=1)
        prof = prof.sort_values("pct").reset_index(drop=True)

        y = np.arange(len(prof))
        ax.barh(y, prof["pct"], color=SEG_COLORS[seg], edgecolor="white", linewidth=0.8)
        ax.set_yticks(y)
        ax.set_yticklabels(prof["label"], fontsize=8)
        ax.set_xlim(0, prof["pct"].max() * 1.28)
        ax.set_xlabel("Share of segment (%)", fontsize=8.5)
        ax.tick_params(axis="x", labelsize=8)
        ax.set_title(f"{seg}  →  {k} sub-types", fontweight="bold", loc="left", fontsize=10.5)
        ax.grid(True, axis="x")
        ax.grid(False, axis="y")
        for yi, (p, r, lead) in enumerate(zip(prof["pct"], prof["med_rev"], prof["med_lead"])):
            ax.text(
                p + prof["pct"].max() * 0.03,
                yi,
                f"${r:,.0f} · {int(lead)}d",
                va="center",
                fontsize=7.5,
                color=INK_SOFT,
            )
    fig.suptitle(
        "Sub-segmentation — LCA sub-types inside the four largest segments",
        fontsize=12.5,
        fontweight="bold",
        color=INK,
        x=0.01,
        ha="left",
    )
    fig.text(
        0.01,
        0.005,
        "Bar label = direction · timing · value tier;  annotation = median revenue · median lead time.",
        fontsize=7.5,
        color=INK_FAINT,
        family="monospace",
    )
    save(fig, "sub_01_subtypes.png")


def main() -> None:
    FIGS.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("PRAGMA threads=6")

    print("EDA figures (full data) ...")
    fig_segment_distribution(con)
    fig_route_region(con)
    fig_lead_and_value(con)

    print("Preliminary-cluster figures (60k sample) ...")
    df = load_sample(con)
    codes = codes_for_lca(df)
    rows, labels = [], {}
    for k in K_RANGE:
        m = StepMix(
            n_components=k,
            measurement="categorical",
            n_init=2,
            random_state=SEED,
            verbose=0,
            progress_bar=False,
        )
        m.fit(codes)
        rows.append({"k": k, "BIC": m.bic(codes)})
        labels[k] = m.predict(codes)
        print(f"  LCA k={k} done")
    from sklearn.metrics import adjusted_rand_score

    bic_tbl = pd.DataFrame(rows)
    bic_tbl["ARI_vs_proxy"] = [adjusted_rand_score(df["proxy_segment"], labels[k]) for k in K_RANGE]
    k_star = int(bic_tbl.loc[bic_tbl["BIC"].idxmin(), "k"])
    fig_lca_bic(bic_tbl)
    fig_pca(df, labels[k_star], k_star)

    print("Sub-segment figure ...")
    fig_sub_segments(con)
    print("Done. k* =", k_star)


if __name__ == "__main__":
    main()
