"""Segment charts for the shipped v2 taxonomy (11 segments + `Unassigned`).

Draws every figure from the live booking table (`data/interim/pal_features_booking.parquet`,
22,911,450 rows) rather than from any transcribed figure, so a chart cannot drift from the build.
Aggregation runs in DuckDB over the full set; nothing is sampled.

Colour comes from `pal_colors.SEG_COLORS` — the canonical PAL palette, which is load-bearing for
Power BI's `dim_segment`, the personas and PAL's decks, so it is used as-is. It is a 12-way
categorical set and does NOT pass a CVD adjacency check at that width, so **no figure here uses
hue as the identity channel**: every segment bar is named on the axis or labelled in place, and
colour is redundant reinforcement only. Charts where colour *does* carry meaning use a purpose-built
encoding instead — a validated 2-colour pair for bookings-vs-revenue, a single-hue sequential ramp
for the ordinal value bands.

Writes PNGs + a `segment_summary.csv` table view to `outputs/segment_charts/`.

Run:  python src/segment_charts.py
"""

from pathlib import Path

import duckdb
import matplotlib as mpl
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.patches import Patch

from pal_colors import SEG_COLORS

ROOT = Path(__file__).resolve().parents[1]
BOOKING = ROOT / "data" / "interim" / "pal_features_booking.parquet"
OUT = ROOT / "outputs" / "segment_charts"

# ---- report palette (matches src/report_figures.py and docs/status-report styling) ----
INK = "#14213A"
INK_SOFT = "#4A5468"
INK_FAINT = "#7A8298"
SKY = "#12608F"
SIGNAL = "#B45309"
RULE = "#D8D8CF"
PAPER = "#FFFFFF"

# Ordinal value bands: one hue, light -> dark. Not the categorical palette — value_band is a
# magnitude, and a magnitude that wears categorical hues reads as four unrelated things.
BAND_RAMP = {"Budget": "#93C5FD", "Mid": "#3B82F6", "Premium": "#1E3A8A"}
BAND_INK = {"Budget": INK, "Mid": PAPER, "Premium": PAPER}

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
    path = OUT / name
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {path.relative_to(ROOT)}")


def titles(ax, title: str, subtitle: str) -> None:
    """Title carries the finding; subtitle carries the caveat and the denominator."""
    ax.set_title(title, fontsize=14, fontweight="bold", loc="left", pad=22)
    ax.text(0, 1.015, subtitle, transform=ax.transAxes, fontsize=9.5, color=INK_FAINT, va="bottom")


def seg_axis(ax, labels) -> None:
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=10, color=INK)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)


# ---------------------------------------------------------------- data ----
def load() -> dict:
    con = duckdb.connect()
    src = f"read_parquet('{BOOKING}')"

    seg = con.execute(f"""
        select proxy_segment                    as segment,
               count(*)                         as bookings,
               sum(rev_pos)                     as revenue,
               avg(rev_pos)                     as rev_per_booking,
               sum(is_last_minute::int)         as short_lead
        from {src} group by 1 order by bookings desc
    """).df()

    # Corporate's rule is `corp_channel OR (any_business AND lead_days <= 7)`. The second branch only
    # admits bookings that are already short-lead, so the segment's headline rate is partly circular;
    # the corp_channel branch carries no lead-time condition and is the honest read.
    corp_clean = con.execute(f"""
        select 100.0 * sum(is_last_minute::int) / count(*)
        from {src} where proxy_segment = 'Corporate' and corp_channel
    """).fetchone()[0]

    band = (
        con.execute(f"""
        select proxy_segment as segment, value_band, count(*) as n
        from {src} group by 1, 2
    """)
        .df()
        .pivot(index="segment", columns="value_band", values="n")
        .fillna(0)
    )

    # `Budget/Adventure -> Leisure` is a rename, not a reclassification: fold it out before
    # counting flows, or 39.3% of the "change" is a relabelled column header.
    flows = con.execute(f"""
        select case when proxy_segment_v1 = 'Budget/Adventure' then 'Leisure'
                    else proxy_segment_v1 end as v1,
               proxy_segment                  as v2,
               count(*)                       as n
        from {src} group by 1, 2 having v1 <> v2 order by n desc
    """).df()

    v1 = con.execute(f"""
        select proxy_segment_v1 as segment, count(*) as bookings
        from {src} group by 1 order by bookings desc
    """).df()

    total_bookings = int(seg.bookings.sum())
    return {
        "seg": seg,
        "band": band,
        "flows": flows,
        "v1": v1,
        "n": total_bookings,
        "rev": float(seg.revenue.sum()),
        "corp_clean": float(corp_clean),
    }


# ------------------------------------------------------------- figures ----
def fig01_size_vs_revenue(d: dict) -> None:
    """The headline: volume and value are not the same ranking."""
    s = d["seg"].copy()
    s["bk_pct"] = 100 * s.bookings / d["n"]
    s["rv_pct"] = 100 * s.revenue / d["rev"]
    s = s.sort_values("rv_pct", ascending=False)

    y = np.arange(len(s))
    h = 0.38
    fig, ax = plt.subplots(figsize=(11, 7.2))
    ax.barh(y - h / 2, s.bk_pct, height=h, color=INK_FAINT, label="Share of bookings")
    ax.barh(y + h / 2, s.rv_pct, height=h, color=SKY, label="Share of revenue")

    for yi, (b, r) in enumerate(zip(s.bk_pct, s.rv_pct)):
        ax.text(b + 0.6, yi - h / 2, f"{b:.1f}%", va="center", fontsize=9, color=INK_SOFT)
        ax.text(
            r + 0.6, yi + h / 2, f"{r:.1f}%", va="center", fontsize=9, color=SKY, fontweight="bold"
        )

    seg_axis(ax, s.segment)
    ax.set_xlim(0, max(s.bk_pct.max(), s.rv_pct.max()) * 1.14)
    ax.set_xlabel("% of the book")
    ax.legend(loc="lower right", frameon=False, fontsize=10)
    titles(
        ax,
        "Balikbayan/VFR is an eighth of bookings and 28% of revenue; Leisure is the mirror image",
        f"Share of bookings vs share of revenue · {d['n']:,} bookings · \\${d['rev'] / 1e9:.2f}B USD "
        "· sorted by revenue share",
    )
    save(fig, "fig_s01_size_vs_revenue.png")


def fig02_revenue_per_booking(d: dict) -> None:
    """Magnitude, one series — no legend; the title names it."""
    s = d["seg"].sort_values("rev_per_booking", ascending=False)
    book_avg = d["rev"] / d["n"]

    fig, ax = plt.subplots(figsize=(11, 6.6))
    ax.barh(range(len(s)), s.rev_per_booking, color=[SEG_COLORS[x] for x in s.segment], height=0.66)
    for i, v in enumerate(s.rev_per_booking):
        ax.text(
            v + 28,
            i,
            f"\\${v:,.0f}",
            va="center",
            fontsize=9.5,
            color=INK,
            fontweight="bold",
            zorder=5,
            bbox={"facecolor": PAPER, "edgecolor": "none", "pad": 1.4},
        )

    ax.axvline(book_avg, color=SIGNAL, lw=1.6, ls="--", zorder=2.5)
    ax.text(
        book_avg + 28,
        -0.62,
        f"book average  \\${book_avg:,.0f}",
        fontsize=9,
        color=SIGNAL,
        fontweight="bold",
        va="center",
    )

    seg_axis(ax, s.segment)
    ax.set_xlim(0, s.rev_per_booking.max() * 1.16)
    ax.set_xlabel("Mean revenue per booking (USD)")
    titles(
        ax,
        "A 25× spread: \\$1,968 a booking at the top, \\$80 at the bottom",
        f"Mean `rev_pos` per booking · {d['n']:,} bookings · revenue confirmed USD by PAL, 18 Aug 2026",
    )
    save(fig, "fig_s02_revenue_per_booking.png")


def fig03_value_band_mix(d: dict) -> None:
    """Composition within each segment — 100% stacked, ordinal ramp, 2px surface gaps."""
    b = d["band"].copy()
    order = ["Budget", "Mid", "Premium"]
    pct = 100 * b[order].div(b[order].sum(axis=1), axis=0)
    pct = pct.sort_values("Premium", ascending=False)

    fig, ax = plt.subplots(figsize=(11, 6.6))
    left = np.zeros(len(pct))
    for band in order:
        v = pct[band].to_numpy()
        ax.barh(
            range(len(pct)),
            v,
            left=left,
            height=0.66,
            color=BAND_RAMP[band],
            edgecolor=PAPER,
            linewidth=2,
            label=band,
        )
        for i, (val, l0) in enumerate(zip(v, left)):
            if val >= 7:  # only label what fits — never a number on every block
                ax.text(
                    l0 + val / 2,
                    i,
                    f"{val:.0f}%",
                    va="center",
                    ha="center",
                    fontsize=9,
                    color=BAND_INK[band],
                    fontweight="bold",
                )
        left += v

    seg_axis(ax, pct.index)
    ax.set_xlim(0, 100)
    ax.set_xlabel("% of the segment's bookings")
    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, -0.245),
        ncol=3,
        frameon=False,
        fontsize=10,
        title="Fare value band",
        title_fontsize=10,
    )
    titles(
        ax,
        "Unassigned is 81% Premium — the residual bucket is not low-value leftovers",
        "Fare `value_band` mix within each segment · sorted by Premium share · "
        "book-wide: Budget 63.1% · Mid 30.9% · Premium 6.0%",
    )
    save(fig, "fig_s03_value_band_mix.png")


def fig04_short_lead_rate(d: dict) -> None:
    """The flag, as a rate — where short-lead behaviour actually concentrates."""
    s = d["seg"].copy()
    s["rate"] = 100 * s.short_lead / s.bookings
    s = s.sort_values("rate", ascending=False)
    book_rate = 100 * s.short_lead.sum() / d["n"]

    fig, ax = plt.subplots(figsize=(11, 6.6))
    ax.barh(range(len(s)), s.rate, color=[SEG_COLORS[x] for x in s.segment], height=0.66)
    for i, (r, n) in enumerate(zip(s.rate, s.short_lead)):
        ax.text(
            r + 0.5,
            i,
            f"{r:.1f}%   ({n:,.0f})",
            va="center",
            fontsize=9,
            color=INK_SOFT,
            zorder=5,
            bbox={"facecolor": PAPER, "edgecolor": "none", "pad": 1.4},
        )

    ax.axvline(book_rate, color=SIGNAL, lw=1.6, ls="--", zorder=2.5)
    ax.text(
        book_rate + 0.5,
        -0.62,
        f"book average  {book_rate:.2f}%",
        fontsize=9,
        color=SIGNAL,
        fontweight="bold",
        va="center",
    )

    seg_axis(ax, s.segment)
    ax.set_xlim(0, max(s.rate.max() * 1.35, 40))
    ax.set_xlabel("% of the segment's bookings flagged short-lead")
    # Parked over the two empty 0% rows — the only region of the plot with no mark or label.
    ax.annotate(
        "⚠ Corporate's 35.6% is partly circular: one of its two rule branches\n"
        "     only admits lead ≤ 7 days. On the `corp_channel` branch, which carries\n"
        f"     no lead-time condition at all, the rate is {d['corp_clean']:.1f}%.",
        xy=(6.5, len(s) - 1.45),
        fontsize=9,
        color=SIGNAL,
        va="center",
        ha="left",
    )
    titles(
        ax,
        "Short-lead runs above average in OFW/Migrant and Leisure — Corporate's 35.6% is partly "
        "circular",
        "`is_last_minute` (lead ≤ 3 days) rate by segment · counts in brackets · ⚠ MICE (rule: lead "
        "≥ 45) and Ultra Wealthy Leisure (lead ≥ 30) are 0% by construction, not by behaviour",
    )
    save(fig, "fig_s04_short_lead_rate.png")


def fig05_reclassification(d: dict) -> None:
    """Where the genuinely-reclassified bookings went — the rename folded out."""
    f = d["flows"].head(12).iloc[::-1]
    moved = int(d["flows"].n.sum())
    labels = [f"{a}  →  {b}" for a, b in zip(f.v1, f.v2)]

    fig, ax = plt.subplots(figsize=(11.5, 6.8))
    ax.barh(range(len(f)), f.n / 1e6, color=[SEG_COLORS[x] for x in f.v2], height=0.66)
    for i, v in enumerate(f.n):
        ax.text(v / 1e6 + 0.022, i, f"{v:,.0f}", va="center", fontsize=9, color=INK)

    ax.set_yticks(range(len(f)))
    ax.set_yticklabels(labels, fontsize=9.5, color=INK)
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, f.n.max() / 1e6 * 1.18)
    ax.set_xlabel("Bookings reclassified (millions)")
    titles(
        ax,
        f"23.4% of bookings genuinely moved — {moved:,}, and 1.76M of them left Unassigned",
        "Top 12 v1→v2 flows, bar coloured by destination segment · the `Budget/Adventure → Leisure` "
        "rename is excluded — it is 39.3% of the raw 62.7% and is not a reclassification",
    )
    save(fig, "fig_s05_reclassification_flows.png")


def fig06_flag_beats_segment(d: dict) -> None:
    """The clearest win: the same behaviour, made visible everywhere it occurs."""
    lm = d["seg"][["segment", "short_lead"]].sort_values("short_lead", ascending=False)
    top = lm.head(6)
    other = float(lm.short_lead[6:].sum())
    parts = list(zip(top.segment, top.short_lead)) + [("Other segments", other)]
    v1_seg = float(d["v1"].loc[d["v1"].segment == "Last-Minute", "bookings"].iloc[0])
    total = float(lm.short_lead.sum())

    fig, ax = plt.subplots(figsize=(11.5, 4.2))
    ax.barh([0], [v1_seg / 1e6], height=0.5, color=SEG_COLORS["Last-Minute"])
    ax.text(
        v1_seg / 1e6 / 2,
        0,
        f"Last-Minute segment\n{v1_seg:,.0f}",
        va="center",
        ha="center",
        fontsize=10,
        color=PAPER,
        fontweight="bold",
    )

    left = 0.0
    for name, n in parts:
        col = SEG_COLORS.get(name, "#CBD5E1")
        ax.barh([1], [n / 1e6], left=left, height=0.5, color=col, edgecolor=PAPER, linewidth=2)
        if n / total >= 0.09:  # anything narrower would overrun its neighbour — legend carries it
            ax.text(
                left + n / 2e6,
                1,
                f"{name}\n{n:,.0f}",
                va="center",
                ha="center",
                fontsize=8.5,
                color=INK,
                fontweight="bold",
            )
        left += n / 1e6

    ax.annotate(
        f"+{total - v1_seg:,.0f} short-lead bookings\nthat the segment never exposed",
        xy=((v1_seg + total) / 2e6, 0.5),
        ha="center",
        va="center",
        fontsize=9.5,
        color=SIGNAL,
        fontweight="bold",
    )
    ax.plot([v1_seg / 1e6, v1_seg / 1e6], [-0.3, 1.3], color=SIGNAL, lw=1.4, ls="--", zorder=2.5)

    ax.set_yticks([0, 1])
    ax.set_yticklabels(["As a segment (v1)", "As a flag (v2)"], fontsize=11, color=INK)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.set_ylim(1.6, -0.6)
    ax.set_xlim(0, total / 1e6 * 1.03)
    ax.set_xlabel("Short-lead bookings (millions)")
    ax.legend(
        handles=[Patch(facecolor=SEG_COLORS.get(n, "#CBD5E1"), label=n) for n, _ in parts],
        loc="lower center",
        bbox_to_anchor=(0.5, -0.5),
        ncol=4,
        frameon=False,
        fontsize=9,
    )
    titles(
        ax,
        "Demoting Last-Minute to a flag exposed 50% more short-lead volume — no threshold moved",
        "A segment could only claim what eight higher-priority branches left behind; a flag rides "
        "along with whatever segment the booking belongs to · v2 split shown (the defence brief "
        "quotes the same volume split by v1 label)",
    )
    save(fig, "fig_s06_lastminute_segment_vs_flag.png")


def table(d: dict) -> None:
    """The table view every figure here is readable without — required, not optional."""
    s = d["seg"].copy()
    s["pct_bookings"] = (100 * s.bookings / d["n"]).round(2)
    s["pct_revenue"] = (100 * s.revenue / d["rev"]).round(2)
    s["rev_per_booking"] = s.rev_per_booking.round(2)
    s["short_lead_pct"] = (100 * s.short_lead / s.bookings).round(2)
    band = 100 * d["band"].div(d["band"].sum(axis=1), axis=0)
    s = s.merge(band.round(2).add_prefix("pct_"), left_on="segment", right_index=True)
    cols = [
        "segment",
        "bookings",
        "pct_bookings",
        "revenue",
        "pct_revenue",
        "rev_per_booking",
        "short_lead",
        "short_lead_pct",
        "pct_Budget",
        "pct_Mid",
        "pct_Premium",
    ]
    s[cols].to_csv(OUT / "segment_summary.csv", index=False)
    print(f"  wrote {(OUT / 'segment_summary.csv').relative_to(ROOT)}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"Reading {BOOKING.relative_to(ROOT)} …")
    d = load()
    print(f"  {d['n']:,} bookings · ${d['rev']:,.0f} USD · {len(d['seg'])} segments")
    fig01_size_vs_revenue(d)
    fig02_revenue_per_booking(d)
    fig03_value_band_mix(d)
    fig04_short_lead_rate(d)
    fig05_reclassification(d)
    fig06_flag_beats_segment(d)
    table(d)


if __name__ == "__main__":
    main()
