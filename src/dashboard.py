"""
dashboard.py — PAL Revenue Intelligence Dashboard
Segment Mix · Revenue · Capacity · Advance Bookings · Network Alerts
Run:  streamlit run dashboard.py
"""

import hashlib
from datetime import date

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

# ── Brand ──────────────────────────────────────────────────────────────────────
PAL_BLUE = "#003087"
PAL_LIGHT = "#dce8f5"

SEG_COLORS = {
    "Leisure": "#4e91d9",
    "VFR": "#27ae60",
    "Business": "#003087",
    "OFW": "#e07b39",
    "Labor": "#c0392b",
}

SEGMENTS = ["Leisure", "VFR", "Business", "OFW", "Labor"]
CABINS = {"Y": "Economy", "W": "Premium Economy", "J": "Business"}
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
TODAY = date(2026, 5, 26)

# ── Route config ───────────────────────────────────────────────────────────────
PH_AIRPORTS = {
    "DVO",
    "CEB",
    "ILO",
    "BCD",
    "ZAM",
    "GEN",
    "MNL",
    "KLO",
    "PPS",
    "TUG",
    "LAO",
    "CRM",
    "CYZ",
    "CGY",
    "MPH",
    "BXU",
    "TAG",
}
DOM_SECTORS = [
    "DVOMNL",
    "MNLDVO",
    "CEBMNL",
    "MNLCEB",
    "ILOMNL",
    "MNLILO",
    "BCDMNL",
    "MNLBCD",
    "ZAMMNL",
    "MNLZAM",
    "GENMNL",
    "MNLGEN",
    "CEBDVO",
    "DVOCEB",
    "CEBILO",
    "ILOCEB",
    "CEBPPS",
    "PPSCEB",
]
INT_SECTORS = [
    "MNLBKK",
    "BKKMNL",
    "MNLSYD",
    "SYDMNL",
    "MNLLAX",
    "LAXMNL",
    "MNLHKG",
    "HKGMNL",
    "MNLNRT",
    "NRTMNL",
    "MNLICN",
    "ICNMNL",
    "MNLSIN",
    "SINMNL",
    "MNLDXB",
    "DXBMNL",
    "MNLKUL",
    "KULMNL",
]
BASE_PAX = {
    "DVOMNL": 5200,
    "MNLDVO": 4800,
    "CEBMNL": 8500,
    "MNLCEB": 8200,
    "ILOMNL": 3200,
    "MNLILO": 3000,
    "BCDMNL": 3500,
    "MNLBCD": 3300,
    "ZAMMNL": 2100,
    "MNLZAM": 2000,
    "GENMNL": 1800,
    "MNLGEN": 1700,
    "CEBDVO": 2400,
    "DVOCEB": 2300,
    "CEBILO": 1600,
    "ILOCEB": 1500,
    "CEBPPS": 1200,
    "PPSCEB": 1100,
    "MNLBKK": 4500,
    "BKKMNL": 4300,
    "MNLSYD": 3200,
    "SYDMNL": 3100,
    "MNLLAX": 2800,
    "LAXMNL": 2700,
    "MNLHKG": 5500,
    "HKGMNL": 5300,
    "MNLNRT": 4100,
    "NRTMNL": 4000,
    "MNLICN": 3800,
    "ICNMNL": 3700,
    "MNLSIN": 5200,
    "SINMNL": 5000,
    "MNLDXB": 3600,
    "DXBMNL": 3500,
    "MNLKUL": 4200,
    "KULMNL": 4000,
}
CABIN_SPLIT = {"Y": 0.87, "W": 0.08, "J": 0.05}
SEG_MIX = {
    ("dom", "Y"): {"Leisure": 0.42, "VFR": 0.40, "Business": 0.10, "OFW": 0.02, "Labor": 0.06},
    ("dom", "W"): {"Leisure": 0.28, "VFR": 0.28, "Business": 0.40, "OFW": 0.02, "Labor": 0.02},
    ("dom", "J"): {"Leisure": 0.18, "VFR": 0.15, "Business": 0.65, "OFW": 0.01, "Labor": 0.01},
    ("int", "Y"): {"Leisure": 0.25, "VFR": 0.35, "Business": 0.10, "OFW": 0.20, "Labor": 0.10},
    ("int", "W"): {"Leisure": 0.28, "VFR": 0.22, "Business": 0.45, "OFW": 0.03, "Labor": 0.02},
    ("int", "J"): {"Leisure": 0.20, "VFR": 0.15, "Business": 0.62, "OFW": 0.02, "Labor": 0.01},
}
SEASONALITY = {
    1: 0.85,
    2: 0.80,
    3: 0.90,
    4: 0.95,
    5: 1.00,
    6: 1.05,
    7: 1.15,
    8: 1.20,
    9: 0.90,
    10: 0.85,
    11: 1.00,
    12: 1.25,
}
YOY_RANGE = {
    "Leisure": (-0.05, 0.05),
    "VFR": (0.10, 0.20),
    "Business": (0.00, 0.05),
    "OFW": (-0.60, -0.45),
    "Labor": (-0.88, -0.75),
}

# ── Fare config ────────────────────────────────────────────────────────────────
BASE_FARE = {
    ("dom", "Y"): 3_500,
    ("dom", "W"): 8_500,
    ("dom", "J"): 18_000,
    ("int", "Y"): 12_000,
    ("int", "W"): 28_000,
    ("int", "J"): 65_000,
}
SEG_FARE_MULT = {
    "Business": 1.35,
    "VFR": 0.98,
    "Leisure": 0.90,
    "OFW": 0.87,
    "Labor": 0.80,
}
FARE_YOY_RANGE = {
    "Business": (0.05, 0.12),
    "VFR": (0.02, 0.07),
    "Leisure": (0.03, 0.08),
    "OFW": (-0.05, 0.02),
    "Labor": (-0.10, -0.03),
}

# ── Capacity config ────────────────────────────────────────────────────────────
SEATS_PER_OP = {
    ("dom", "Y"): 140,
    ("dom", "W"): 16,
    ("dom", "J"): 8,
    ("int", "Y"): 240,
    ("int", "W"): 32,
    ("int", "J"): 24,
}
OPS_PER_MONTH = {"dom": 48, "int": 24}  # total monthly ops per route, distributed across 3 flight#s

# ── Advance booking pickup (% of demand booked ≥60 days before departure) ──────
BOOKING_ADV_PCT = {
    "Business": 0.72,
    "VFR": 0.58,
    "Leisure": 0.48,
    "OFW": 0.42,
    "Labor": 0.35,
}


# ── Model performance constants ────────────────────────────────────────────────

NFR_TARGET = 91.0
POC_ACC = 77.7
POC_REV_RISK = 18_090_000
POC_RECORDS = 10_000

SEG_10 = [
    "Corporate",
    "Mabuhay Loyalist",
    "OFW/Migrant",
    "Premium Bleisure",
    "Pilgrimage",
    "Balikbayan/VFR",
    "Family",
    "Digital Nomad",
    "Last-Minute",
    "Budget/Adventure",
]
RECALL_10 = {
    "Corporate": 100,
    "Mabuhay Loyalist": 63,
    "OFW/Migrant": 18,
    "Premium Bleisure": 38,
    "Pilgrimage": 54,
    "Balikbayan/VFR": 73,
    "Family": 99,
    "Digital Nomad": 95,
    "Last-Minute": 91,
    "Budget/Adventure": 22,
}
PENALTY_10 = {
    "Corporate": 10,
    "Mabuhay Loyalist": 8,
    "OFW/Migrant": 5,
    "Premium Bleisure": 4,
    "Pilgrimage": 3,
    "Balikbayan/VFR": 2,
    "Family": 2,
    "Digital Nomad": 2,
    "Last-Minute": 1,
    "Budget/Adventure": 1,
}
REV_LOSS_10 = {
    "Corporate": 40_000,
    "Mabuhay Loyalist": 32_000,
    "OFW/Migrant": 20_000,
    "Premium Bleisure": 16_000,
    "Pilgrimage": 12_000,
    "Balikbayan/VFR": 8_000,
    "Family": 8_000,
    "Digital Nomad": 8_000,
    "Last-Minute": 4_000,
    "Budget/Adventure": 4_000,
}
SUPPORT_10 = {
    "Corporate": 500,
    "Mabuhay Loyalist": 500,
    "OFW/Migrant": 1_500,
    "Premium Bleisure": 800,
    "Pilgrimage": 800,
    "Balikbayan/VFR": 2_000,
    "Family": 1_000,
    "Digital Nomad": 800,
    "Last-Minute": 800,
    "Budget/Adventure": 1_300,
}

# 5-segment confusion matrix simulated from POC 10-segment recall values (10k records)
# Rows = true segment, cols = predicted (Business, VFR, OFW, Labor, Leisure)
_CM_COUNTS = np.array(
    [
        [1350, 110, 30, 12, 298],  # Business (1800 total, ~75% after rollup)
        [150, 2610, 100, 35, 105],  # VFR      (3000, ~87%)
        [30, 780, 375, 105, 210],  # OFW      (1500, ~25%)
        [20, 110, 70, 480, 120],  # Labor    ( 800, ~60%)
        [195, 420, 145, 52, 2088],  # Leisure  (2900, ~72%)
    ],
    dtype=float,
)


# ── Data generation ────────────────────────────────────────────────────────────


def _flight_base(sector: str) -> int:
    return int(hashlib.md5(sector.encode(), usedforsecurity=False).hexdigest()[:5], 16) % 600 + 100


@st.cache_data
def build_summary() -> pd.DataFrame:
    """Pax + revenue per year/month/od/flight/cabin/segment."""
    rng = np.random.default_rng(42)
    rows = []
    for sector in DOM_SECTORS + INT_SECTORS:
        orig, dest = sector[:3], sector[3:]
        is_int = (orig not in PH_AIRPORTS) or (dest not in PH_AIRPORTS)
        rt = "int" if is_int else "dom"
        base = BASE_PAX.get(sector, 2000)
        base_n = _flight_base(sector)
        flights = [f"PR{base_n}", f"PR{base_n + 2}", f"PR{base_n + 4}"]
        fl_shares = [0.45, 0.35, 0.20]

        # Fixed growth rates per sector so 2026 derives consistently from 2025
        seg_growth = {seg: rng.uniform(*YOY_RANGE[seg]) for seg in SEGMENTS}
        fare_growth = {seg: rng.uniform(*FARE_YOY_RANGE[seg]) for seg in SEGMENTS}

        # Fixed base fare per (cabin, segment) for this sector
        base_fares = {
            (cb, seg): BASE_FARE.get((rt, cb), 5000) * SEG_FARE_MULT[seg] * rng.uniform(0.95, 1.05)
            for cb in CABIN_SPLIT
            for seg in SEGMENTS
        }

        for year in [2025, 2026]:
            for month in range(1, 13):
                monthly_total = int(base * SEASONALITY[month] * rng.uniform(0.97, 1.03))
                for cabin_code, cab_share in CABIN_SPLIT.items():
                    cabin_total = int(monthly_total * cab_share)
                    mix = SEG_MIX[(rt, cabin_code)]
                    for seg in SEGMENTS:
                        base_seg_pax = int(cabin_total * mix[seg])
                        seg_pax = (
                            base_seg_pax
                            if year == 2025
                            else max(
                                0,
                                int(base_seg_pax * (1 + seg_growth[seg]) * rng.uniform(0.97, 1.03)),
                            )
                        )
                        if seg_pax == 0:
                            continue
                        avg_fare = base_fares[(cabin_code, seg)]
                        if year == 2026:
                            avg_fare *= 1 + fare_growth[seg]
                        for fi, flight in enumerate(flights):
                            fp = max(0, int(seg_pax * fl_shares[fi] * rng.uniform(0.94, 1.06)))
                            if fp > 0:
                                rows.append(
                                    {
                                        "year": year,
                                        "month": month,
                                        "od": f"{orig}-{dest}",
                                        "flight": flight,
                                        "cabin_code": cabin_code,
                                        "cabin_name": CABINS[cabin_code],
                                        "segment": seg,
                                        "pax": fp,
                                        "revenue": fp * avg_fare,
                                        "avg_fare": avg_fare,
                                        "rt": rt,
                                    }
                                )
    return pd.DataFrame(rows)


@st.cache_data
def build_capacity() -> pd.DataFrame:
    """Available seats per year/month/od/flight/cabin."""
    rows = []
    for sector in DOM_SECTORS + INT_SECTORS:
        orig, dest = sector[:3], sector[3:]
        is_int = (orig not in PH_AIRPORTS) or (dest not in PH_AIRPORTS)
        rt = "int" if is_int else "dom"
        base_n = _flight_base(sector)
        flights = [f"PR{base_n}", f"PR{base_n + 2}", f"PR{base_n + 4}"]
        fl_shares = [0.45, 0.35, 0.20]
        for year in [2025, 2026]:
            for month in range(1, 13):
                for cabin_code, _ in CABIN_SPLIT.items():
                    spop = SEATS_PER_OP.get((rt, cabin_code), 50)
                    ops = OPS_PER_MONTH[rt]
                    for fi, flight in enumerate(flights):
                        rows.append(
                            {
                                "year": year,
                                "month": month,
                                "od": f"{orig}-{dest}",
                                "flight": flight,
                                "cabin_code": cabin_code,
                                "cabin_name": CABINS[cabin_code],
                                "seats": int(spop * ops * fl_shares[fi]),
                            }
                        )
    return pd.DataFrame(rows)


# ── Conditional formatting ─────────────────────────────────────────────────────


def _yoy_style(pct: float) -> tuple[str, str]:
    """Unified red-to-green scale used on every % column."""
    if pct >= 10:
        return "#27ae60", "white"
    elif pct >= 1:
        return "#f1c40f", "#333"
    elif pct > -1:
        return "transparent", "#333"
    elif pct >= -10:
        return "#e8c547", "#333"
    elif pct >= -30:
        return "#e07b39", "white"
    elif pct >= -60:
        return "#e74c3c", "white"
    else:
        return "#c0392b", "white"


def _lf_style(lf: float) -> tuple[str, str]:
    if lf >= 85:
        return "#27ae60", "white"
    elif lf >= 75:
        return "#f1c40f", "#333"
    elif lf >= 65:
        return "#e07b39", "white"
    else:
        return "#e74c3c", "white"


# ── Model performance charts ───────────────────────────────────────────────────


def _recall_bar() -> go.Figure:
    segs = sorted(SEG_10, key=lambda s: RECALL_10[s])
    vals = [RECALL_10[s] for s in segs]
    colors = ["#27ae60" if v >= NFR_TARGET else "#e74c3c" for v in vals]
    fig = go.Figure(
        go.Bar(
            y=segs,
            x=vals,
            orientation="h",
            marker_color=colors,
            text=[f"{v}%" for v in vals],
            textposition="outside",
            textfont=dict(size=11, color="#333"),
            cliponaxis=False,
        )
    )
    fig.add_vline(
        x=NFR_TARGET,
        line_dash="dash",
        line_color=PAL_BLUE,
        line_width=2,
        annotation_text="NFR-01 (91%)",
        annotation_position="top right",
        annotation_font=dict(color=PAL_BLUE, size=11),
    )
    fig.update_layout(
        title=dict(
            text="<b>Per-Segment Recall</b>",
            font=dict(size=13, color=PAL_BLUE),
            x=0,
            xanchor="left",
        ),
        xaxis=dict(range=[0, 125], visible=False, showgrid=False, zeroline=False),
        yaxis=dict(showgrid=False, zeroline=False, tickfont=dict(size=11, color="#333")),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=0, r=60, t=36, b=4),
        height=360,
        showlegend=False,
    )
    return fig


def _confusion_heatmap() -> go.Figure:
    cm_labels = ["Business", "VFR", "OFW", "Labor", "Leisure"]
    row_sums = _CM_COUNTS.sum(axis=1, keepdims=True)
    cm_pct = (_CM_COUNTS / row_sums * 100).round(1)
    cm_plot = cm_pct[::-1]
    y_labels = cm_labels[::-1]
    colorscale = [[0.0, "#ffffff"], [0.2, "#dce8f5"], [0.6, "#5a9fd4"], [1.0, "#003087"]]
    text_colors = [["white" if v > 60 else "#333" for v in row] for row in cm_plot]
    annotations = []
    for i, row in enumerate(cm_plot):
        for j, val in enumerate(row):
            annotations.append(
                dict(
                    x=cm_labels[j],
                    y=y_labels[i],
                    text=f"<b>{val:.0f}%</b>",
                    showarrow=False,
                    font=dict(size=12, color=text_colors[i][j]),
                )
            )
    fig = go.Figure(
        go.Heatmap(
            z=cm_plot,
            x=cm_labels,
            y=y_labels,
            colorscale=colorscale,
            showscale=False,
            hoverongaps=False,
        )
    )
    fig.update_layout(
        title=dict(
            text="<b>Confusion Matrix</b><br><sup>Row = True Segment · Col = Predicted</sup>",
            font=dict(size=13, color=PAL_BLUE),
            x=0,
            xanchor="left",
        ),
        xaxis=dict(title="Predicted", tickfont=dict(size=11), side="bottom"),
        yaxis=dict(title="True", tickfont=dict(size=11)),
        annotations=annotations,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=60, r=10, t=60, b=50),
        height=360,
    )
    return fig


# ── Sparkline ──────────────────────────────────────────────────────────────────


def _sparkline(monthly_vals: list, color: str, highlight: int) -> str:
    """Inline SVG line chart. highlight = 1-based month index."""
    if not monthly_vals or max(monthly_vals) == 0:
        return '<svg width="84" height="22"></svg>'
    W, H, pad = 84, 22, 2
    mn, mx = min(monthly_vals), max(monthly_vals)
    span = mx - mn or 1
    pts = [
        (pad + i / 11 * (W - 2 * pad), H - pad - (v - mn) / span * (H - 2 * pad))
        for i, v in enumerate(monthly_vals)
    ]
    pts_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    hx, hy = pts[highlight - 1]
    return (
        f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
        f'<polyline points="{pts_str}" fill="none" stroke="{color}" '
        f'stroke-width="1.5" stroke-linejoin="round"/>'
        f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="3" fill="{color}"/>'
        f"</svg>"
    )


# ── Table renderers ────────────────────────────────────────────────────────────

_TABLE_CSS = f"""
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 12.5px; background: transparent; }}
  .wrap {{ overflow-x: auto; }}
  table {{
    border-collapse: separate; border-spacing: 0;
    width: 100%; min-width: 860px;
    border: 1px solid #b8cfe8; border-radius: 4px; overflow: hidden;
  }}
  th, td {{
    padding: 7px 12px;
    border-right: 1px solid #c8d8e8;
    border-bottom: 1px solid #c8d8e8;
    white-space: nowrap;
  }}
  th:last-child, td:last-child {{ border-right: none; }}
  tr:last-child td {{ border-bottom: none; }}
  th {{ background: {PAL_LIGHT}; color: {PAL_BLUE}; text-align: center; font-weight: 700; }}
  .lbl {{ font-weight: 700; background: {PAL_LIGHT}; color: {PAL_BLUE}; text-align: left; }}
  .num {{ text-align: right; }}
  .grp {{ border-left: 2px solid #8aafd4 !important; }}
</style>
"""

_SMALL_TABLE_CSS = f"""
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 12.5px; background: transparent; }}
  table {{
    border-collapse: separate; border-spacing: 0; width: 100%;
    border: 1px solid #b8cfe8; border-radius: 4px; overflow: hidden;
  }}
  th, td {{ padding: 7px 12px; border-right: 1px solid #c8d8e8; border-bottom: 1px solid #c8d8e8; white-space: nowrap; }}
  th:last-child, td:last-child {{ border-right: none; }}
  tr:last-child td {{ border-bottom: none; }}
  th {{ background: {PAL_LIGHT}; color: {PAL_BLUE}; text-align: center; font-weight: 700; }}
  .lbl {{ font-weight: 700; background: {PAL_LIGHT}; color: {PAL_BLUE}; text-align: left; }}
  .num {{ text-align: right; }}
  .grp {{ border-left: 2px solid #8aafd4 !important; }}
</style>
"""


def render_table(
    summary: pd.DataFrame,
    network: pd.DataFrame,
    monthly: dict,
    year1: int,
    year2: int,
    month_label: str,
    month_num: int,
    show_vs_net: bool = True,
) -> str:
    def pct(v, t):
        return round(v / t * 100) if t else 0

    def yoy(v1, v2):
        return round((v2 - v1) / v1 * 100) if v1 else 0

    def fare_fmt(f):
        return f"&#8369;{f:,.0f}"

    t1p = int(summary["y1_pax"].sum())
    t2p = int(summary["y2_pax"].sum())
    t1r = summary["y1_rev"].sum()
    t2r = summary["y2_rev"].sum()

    vs_net_col = (
        """<th rowspan="2" class="grp" style="border-bottom:1px solid #c8d8e8">vs.<br>Network</th>"""
        if show_vs_net
        else ""
    )

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">{_TABLE_CSS}</head>
    <body><div class="wrap"><table>
      <thead>
        <tr>
          <th rowspan="2" style="text-align:left;min-width:80px;border-bottom:1px solid #c8d8e8">Segment</th>
          <th colspan="3" style="border-bottom:1px solid #c8d8e8">{year1}-{month_label}</th>
          <th colspan="3" class="grp" style="border-bottom:1px solid #c8d8e8">{year2}-{month_label}</th>
          <th colspan="3" class="grp" style="border-bottom:1px solid #c8d8e8">YoY Var</th>
          {vs_net_col}
          <th rowspan="2" style="border-bottom:1px solid #c8d8e8;min-width:88px">12-Mo<br>Trend</th>
        </tr>
        <tr>
          <th>Pax</th><th>%</th><th>Avg Fare</th>
          <th class="grp">Pax</th><th>%</th><th>Avg Fare</th>
          <th class="grp">Pax</th><th>%</th><th>Rev %</th>
        </tr>
      </thead><tbody>"""

    for seg in SEGMENTS:
        y1p = int(summary.loc[seg, "y1_pax"]) if seg in summary.index else 0
        y2p = int(summary.loc[seg, "y2_pax"]) if seg in summary.index else 0
        y1r = summary.loc[seg, "y1_rev"] if seg in summary.index else 0
        y2r = summary.loc[seg, "y2_rev"] if seg in summary.index else 0
        y1f = summary.loc[seg, "y1_fare"] if seg in summary.index else 0
        y2f = summary.loc[seg, "y2_fare"] if seg in summary.index else 0

        p1, p2 = pct(y1p, t1p), pct(y2p, t2p)
        yoy_pax = yoy(y1p, y2p)
        yoy_rev = yoy(y1r, y2r)
        dpax = y2p - y1p

        b1, f1 = _yoy_style(p1)
        b2, f2 = _yoy_style(p2)
        by, fy = _yoy_style(yoy_pax)
        byr, fyr = _yoy_style(yoy_rev)
        sign_p = "+" if yoy_pax > 0 else ""
        sign_r = "+" if yoy_rev > 0 else ""

        # vs. Network
        vs_net_td = ""
        if show_vs_net:
            n1 = int(network.loc[seg, "y1_pax"]) if seg in network.index else 0
            n2 = int(network.loc[seg, "y2_pax"]) if seg in network.index else 0
            net_yoy = yoy(n1, n2)
            delta = yoy_pax - net_yoy
            bvn = "#27ae60" if delta >= 2 else ("#e74c3c" if delta <= -2 else "transparent")
            fvn = "white" if abs(delta) >= 2 else "#333"
            sign_vn = "+" if delta > 0 else ""
            vs_net_td = f'<td style="background:{bvn};color:{fvn};font-weight:700;text-align:right" class="grp">{sign_vn}{delta}pp</td>'

        spark = _sparkline(monthly.get(seg, [0] * 12), SEG_COLORS.get(seg, PAL_BLUE), month_num)

        html += f"""
        <tr>
          <td class="lbl">{seg}</td>
          <td class="num">{y1p:,}</td>
          <td style="background:{b1};color:{f1};text-align:right;font-weight:600">{p1}%</td>
          <td class="num">{fare_fmt(y1f)}</td>
          <td class="num grp">{y2p:,}</td>
          <td style="background:{b2};color:{f2};text-align:right;font-weight:600">{p2}%</td>
          <td class="num">{fare_fmt(y2f)}</td>
          <td style="background:{by};color:{fy};font-weight:700;text-align:right" class="grp">{dpax:+,}</td>
          <td style="background:{by};color:{fy};font-weight:700;text-align:right">{sign_p}{yoy_pax}%</td>
          <td style="background:{byr};color:{fyr};font-weight:700;text-align:right">{sign_r}{yoy_rev}%</td>
          {vs_net_td}
          <td style="padding:4px 8px">{spark}</td>
        </tr>"""

    # Totals row
    yoy_tp = yoy(t1p, t2p)
    yoy_tr = yoy(t1r, t2r)
    btp, ftp = _yoy_style(yoy_tp)
    btr, ftr = _yoy_style(yoy_tr)
    stp = "+" if yoy_tp > 0 else ""
    str_ = "+" if yoy_tr > 0 else ""
    vs_net_total = '<td class="grp" style="background:#f0f4f8">—</td>' if show_vs_net else ""

    html += f"""
        <tr>
          <td class="lbl" style="background:#c4d8f0">Total</td>
          <td class="num" style="font-weight:700;background:#f0f4f8">{t1p:,}</td>
          <td style="background:#27ae60;color:white;text-align:right;font-weight:700">100%</td>
          <td class="num" style="background:#f0f4f8;font-weight:700">—</td>
          <td class="num grp" style="font-weight:700;background:#f0f4f8">{t2p:,}</td>
          <td style="background:#27ae60;color:white;text-align:right;font-weight:700">100%</td>
          <td class="num" style="background:#f0f4f8;font-weight:700">—</td>
          <td style="background:{btp};color:{ftp};font-weight:700;text-align:right" class="grp">{t2p - t1p:+,}</td>
          <td style="background:{btp};color:{ftp};font-weight:700;text-align:right">{stp}{yoy_tp}%</td>
          <td style="background:{btr};color:{ftr};font-weight:700;text-align:right">{str_}{yoy_tr}%</td>
          {vs_net_total}
          <td></td>
        </tr>
      </tbody></table></div></body></html>"""
    return html


def render_lf_table(lf: pd.DataFrame, year1: int, year2: int, month_label: str) -> str:
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">{_SMALL_TABLE_CSS}</head><body>
    <table>
      <thead>
        <tr>
          <th rowspan="2" style="text-align:left;border-bottom:1px solid #c8d8e8">Flight</th>
          <th colspan="3" style="border-bottom:1px solid #c8d8e8">{year1}-{month_label}</th>
          <th colspan="3" class="grp" style="border-bottom:1px solid #c8d8e8">{year2}-{month_label}</th>
          <th rowspan="2" class="grp" style="border-bottom:1px solid #c8d8e8">LF YoY</th>
        </tr>
        <tr>
          <th>Seats</th><th>Pax</th><th>LF %</th>
          <th class="grp">Seats</th><th>Pax</th><th>LF %</th>
        </tr>
      </thead><tbody>"""

    for _, row in lf.iterrows():
        s1, p1, lf1 = int(row["seats_y1"]), int(row["pax_y1"]), float(row["lf_y1"])
        s2, p2, lf2 = int(row["seats_y2"]), int(row["pax_y2"]), float(row["lf_y2"])
        b1, f1 = _lf_style(lf1)
        b2, f2 = _lf_style(lf2)
        dlf = lf2 - lf1
        bdlf = "#27ae60" if dlf >= 1 else ("#e74c3c" if dlf <= -1 else "transparent")
        fdlf = "white" if abs(dlf) >= 1 else "#333"
        sign = "+" if dlf > 0 else ""
        html += f"""
        <tr>
          <td class="lbl">{row["flight"]}</td>
          <td class="num">{s1:,}</td><td class="num">{p1:,}</td>
          <td style="background:{b1};color:{f1};font-weight:700;text-align:right">{lf1:.1f}%</td>
          <td class="num grp">{s2:,}</td><td class="num">{p2:,}</td>
          <td style="background:{b2};color:{f2};font-weight:700;text-align:right">{lf2:.1f}%</td>
          <td style="background:{bdlf};color:{fdlf};font-weight:700;text-align:right" class="grp">{sign}{dlf:.1f}pp</td>
        </tr>"""

    html += "</tbody></table></body></html>"
    return html


def render_advance_table(adv: pd.DataFrame, window_label: str) -> str:
    def yoy(v1, v2):
        return round((v2 - v1) / v1 * 100) if v1 else 0

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">{_SMALL_TABLE_CSS}</head><body>
    <table>
      <thead>
        <tr>
          <th style="text-align:left;border-bottom:1px solid #c8d8e8">Segment</th>
          <th style="border-bottom:1px solid #c8d8e8">LY On-Hand<br><small style="font-weight:400">same window, LY</small></th>
          <th style="border-bottom:1px solid #c8d8e8">CY On-Hand<br><small style="font-weight:400">booked so far</small></th>
          <th style="border-bottom:1px solid #c8d8e8">Pickup YoY %</th>
          <th style="border-bottom:1px solid #c8d8e8">Advance %<br><small style="font-weight:400">at {window_label}</small></th>
          <th style="border-bottom:1px solid #c8d8e8">Projected Total</th>
        </tr>
      </thead><tbody>"""

    t_ly, t_cy = 0, 0
    for seg in SEGMENTS:
        if seg not in adv.index:
            continue
        ly = int(adv.loc[seg, "ly_onhand"])
        cy = int(adv.loc[seg, "cy_onhand"])
        t_ly += ly
        t_cy += cy
        adv_p = BOOKING_ADV_PCT.get(seg, 0.5)
        proj = int(cy / adv_p) if adv_p else 0
        yp = yoy(ly, cy)
        bg, fg = _yoy_style(yp)
        sign = "+" if yp > 0 else ""
        html += f"""
        <tr>
          <td class="lbl">{seg}</td>
          <td class="num">{ly:,}</td>
          <td class="num">{cy:,}</td>
          <td style="background:{bg};color:{fg};font-weight:700;text-align:right">{sign}{yp}%</td>
          <td class="num">{adv_p * 100:.0f}%</td>
          <td class="num" style="font-weight:600">{proj:,}</td>
        </tr>"""

    html += f"""
        <tr>
          <td class="lbl" style="background:#c4d8f0">Total</td>
          <td class="num" style="font-weight:700;background:#f0f4f8">{t_ly:,}</td>
          <td class="num" style="font-weight:700;background:#f0f4f8">{t_cy:,}</td>
          <td style="background:#f0f4f8;font-weight:700;text-align:right">—</td>
          <td style="background:#f0f4f8">—</td>
          <td style="background:#f0f4f8">—</td>
        </tr>
      </tbody></table></body></html>"""
    return html


def render_alerts_table(alerts: pd.DataFrame) -> str:
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">{_SMALL_TABLE_CSS}</head><body>
    <table>
      <thead>
        <tr>
          <th style="text-align:left;border-bottom:1px solid #c8d8e8">Route</th>
          <th style="border-bottom:1px solid #c8d8e8">Segment</th>
          <th style="border-bottom:1px solid #c8d8e8">2025 Pax</th>
          <th style="border-bottom:1px solid #c8d8e8">2026 Pax</th>
          <th style="border-bottom:1px solid #c8d8e8">YoY %</th>
        </tr>
      </thead><tbody>"""

    for _, row in alerts.iterrows():
        bg, fg = _yoy_style(int(row["yoy"]))
        sign = "+" if row["yoy"] > 0 else ""
        html += f"""
        <tr>
          <td class="lbl">{row["od"]}</td>
          <td style="padding:6px 12px;border-bottom:1px solid #eee">{row["segment"]}</td>
          <td class="num">{int(row["y1"]):,}</td>
          <td class="num">{int(row["y2"]):,}</td>
          <td style="background:{bg};color:{fg};font-weight:700;text-align:right">{sign}{int(row["yoy"])}%</td>
        </tr>"""

    html += "</tbody></table></body></html>"
    return html


def render_recall_table() -> str:
    """HTML table: all 10 segments sorted by recall ascending, with risk estimate."""
    rows_html = ""
    for seg in sorted(SEG_10, key=lambda s: RECALL_10[s]):
        rec = RECALL_10[seg]
        ok = rec >= NFR_TARGET
        bg_rec = "#27ae60" if ok else "#e74c3c"
        bg_st = "#d4f0dc" if ok else "#fde8e8"
        status = "&#10003; Met" if ok else "&#10007; Below"
        missed = int(SUPPORT_10[seg] * (1 - rec / 100))
        risk = missed * REV_LOSS_10[seg]
        risk_s = f"&#8369;{risk / 1_000_000:.1f}M"
        rows_html += f"""
        <tr>
          <td class="lbl">{seg}</td>
          <td class="num">{SUPPORT_10[seg]:,}</td>
          <td class="num">&#215;{PENALTY_10[seg]}</td>
          <td style="background:{bg_rec};color:white;font-weight:700;text-align:right">{rec}%</td>
          <td style="background:{bg_st};text-align:center;font-weight:600;color:#333">{status}</td>
          <td class="num">&#8369;{REV_LOSS_10[seg]:,}</td>
          <td class="num" style="font-weight:{"700" if risk > 1_000_000 else "400"};color:{"#c0392b" if risk > 1_000_000 else "#333"}">{risk_s}</td>
        </tr>"""
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">{_SMALL_TABLE_CSS}</head>
    <body><table>
      <thead>
        <tr>
          <th style="text-align:left;border-bottom:1px solid #c8d8e8">Segment</th>
          <th style="border-bottom:1px solid #c8d8e8">Support<br><small style="font-weight:400">POC records</small></th>
          <th style="border-bottom:1px solid #c8d8e8">Penalty</th>
          <th style="border-bottom:1px solid #c8d8e8">Recall</th>
          <th style="border-bottom:1px solid #c8d8e8">vs. NFR&#8209;01<br><small style="font-weight:400">&#8805;91% target</small></th>
          <th style="border-bottom:1px solid #c8d8e8">Cost / Error</th>
          <th style="border-bottom:1px solid #c8d8e8">Est. Revenue Risk</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table></body></html>"""
    return html


# ── Chart ──────────────────────────────────────────────────────────────────────


def _hbar(values: pd.Series, title: str) -> go.Figure:
    values = values.sort_values(ascending=True)
    segs = list(values.index)
    vals = [int(v) for v in values.values]
    colors = [SEG_COLORS.get(s, PAL_BLUE) for s in segs]
    max_v = max(vals) if vals else 1
    fig = go.Figure(
        go.Bar(
            y=segs,
            x=vals,
            orientation="h",
            marker_color=colors,
            text=[f"{v:,}" for v in vals],
            textposition="outside",
            textfont=dict(size=12, color="#333"),
            cliponaxis=False,
        )
    )
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=13, color=PAL_BLUE), x=0, xanchor="left"),
        xaxis=dict(visible=False, showgrid=False, zeroline=False, range=[0, max_v * 1.28]),
        yaxis=dict(showgrid=False, zeroline=False, tickfont=dict(size=12, color="#333")),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=0, r=60, t=36, b=4),
        height=220,
        showlegend=False,
    )
    return fig


# ── Data helpers ───────────────────────────────────────────────────────────────


def _pivot(filt: pd.DataFrame) -> pd.DataFrame:
    """Segment-level summary: y1/y2 pax, revenue, weighted avg fare."""
    out = {}
    for yr, prefix in [(2025, "y1"), (2026, "y2")]:
        g = filt[filt["year"] == yr].groupby("segment")
        pax = g["pax"].sum()
        rev = g["revenue"].sum()
        fare = (rev / pax.replace(0, np.nan)).fillna(0)
        out[f"{prefix}_pax"] = pax
        out[f"{prefix}_rev"] = rev
        out[f"{prefix}_fare"] = fare
    return pd.DataFrame(out).reindex(SEGMENTS).fillna(0)


def _monthly_pax(filt_all: pd.DataFrame, year: int) -> dict:
    """12-month pax per segment for sparklines."""
    fy = filt_all[filt_all["year"] == year]
    return {
        seg: [
            int(fy[fy["segment"] == seg].groupby("month")["pax"].sum().get(m, 0))
            for m in range(1, 13)
        ]
        for seg in SEGMENTS
    }


def _load_factor(
    df: pd.DataFrame,
    cap: pd.DataFrame,
    month_num: int,
    od_sel: str,
    flight_sel: str,
    cabin_sel: str,
) -> pd.DataFrame:
    def flt(frame):
        f = frame[frame["month"] == month_num]
        if od_sel != "All":
            f = f[f["od"] == od_sel]
        if flight_sel != "All":
            f = f[f["flight"] == flight_sel]
        if cabin_sel != "All":
            f = f[f["cabin_name"] == cabin_sel]
        return f

    pax_m = flt(df).groupby(["year", "flight"])["pax"].sum().reset_index()
    cap_m = flt(cap).groupby(["year", "flight"])["seats"].sum().reset_index()
    merged = pax_m.merge(cap_m, on=["year", "flight"], how="left").fillna(0)
    merged["lf"] = np.where(merged["seats"] > 0, merged["pax"] / merged["seats"] * 100, 0)

    piv = merged.pivot(index="flight", columns="year", values=["pax", "seats", "lf"])
    piv.columns = [f"{c[0]}_y{c[1] - 2024}" for c in piv.columns]
    piv = piv.fillna(0).reset_index()
    for col in ["pax_y1", "pax_y2", "seats_y1", "seats_y2", "lf_y1", "lf_y2"]:
        if col not in piv.columns:
            piv[col] = 0
    return piv


def _advance(filt_all: pd.DataFrame, fwd_months: list) -> pd.DataFrame:
    rows = []
    for seg in SEGMENTS:
        sf = filt_all[filt_all["segment"] == seg]
        adv = BOOKING_ADV_PCT.get(seg, 0.5)
        ly = int(sf[(sf["year"] == 2025) & (sf["month"].isin(fwd_months))]["pax"].sum() * adv)
        cy = int(sf[(sf["year"] == 2026) & (sf["month"].isin(fwd_months))]["pax"].sum() * adv)
        rows.append({"segment": seg, "ly_onhand": ly, "cy_onhand": cy})
    return pd.DataFrame(rows).set_index("segment")


def _behavioral_stats(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Avg fare (₱) and DOM % per 5-segment from 2026 data."""
    recent = df[df["year"] == 2026]
    fare_d, dom_d = {}, {}
    for seg in SEGMENTS:
        s = recent[recent["segment"] == seg]
        pax = s["pax"].sum()
        fare_d[seg] = int(s["revenue"].sum() / pax) if pax else 0
        dom_d[seg] = int(s[s["rt"] == "dom"]["pax"].sum() / pax * 100) if pax else 0
    return pd.Series(fare_d), pd.Series(dom_d)


def _alerts(df: pd.DataFrame, month_num: int, cabin_sel: str, threshold: int) -> pd.DataFrame:
    m = df[df["month"] == month_num]
    if cabin_sel != "All":
        m = m[m["cabin_name"] == cabin_sel]
    y1 = m[m["year"] == 2025].groupby(["od", "segment"])["pax"].sum()
    y2 = m[m["year"] == 2026].groupby(["od", "segment"])["pax"].sum()
    comb = pd.DataFrame({"y1": y1, "y2": y2}).fillna(0).astype(int)
    comb["yoy"] = ((comb["y2"] - comb["y1"]) / comb["y1"].replace(0, 1) * 100).round(0).astype(int)
    return comb[comb["yoy"].abs() >= threshold].sort_values(["od", "segment"]).reset_index()


# ── App ────────────────────────────────────────────────────────────────────────


def main():
    st.set_page_config(
        page_title="PAL Revenue Intelligence",
        page_icon="✈",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # CSS — isolated call so it never leaks as text
    st.markdown(
        """
    <style>
    .pal-header {
        background: #003087; color: white;
        padding: 16px 24px; border-radius: 4px; margin-bottom: 18px;
    }
    .filter-bar {
        background: #dce8f5; border: 1px solid #aac4e0; border-radius: 4px;
        padding: 10px 18px; margin-bottom: 16px; font-size: 14px;
        display: flex; gap: 32px; flex-wrap: wrap;
    }
    .fl { color: #003087; font-weight: 700; margin-right: 6px; }
    div[data-testid="stSelectbox"] label  { font-weight: 600; color: #003087; }
    div[data-testid="stSlider"]    label  { font-weight: 600; color: #003087; }
    div[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 4px !important; }
    </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
    <div class="pal-header">
      <span style="font-size:20px;font-weight:700">Philippine Airlines — Revenue Intelligence Dashboard</span><br>
      <span style="font-size:13px;opacity:0.85">
        Segment Mix &nbsp;·&nbsp; Revenue &nbsp;·&nbsp; Capacity &nbsp;·&nbsp;
        Advance Demand &nbsp;·&nbsp; Network Alerts
      </span>
    </div>
    """,
        unsafe_allow_html=True,
    )

    df = build_summary()
    cap = build_capacity()

    # ── Sidebar ────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### Filters")
        all_ods = sorted(df["od"].unique())
        od_sel = st.selectbox(
            "O&D",
            ["All"] + all_ods,
            index=all_ods.index("DVO-MNL") + 1 if "DVO-MNL" in all_ods else 0,
        )
        flight_pool = df if od_sel == "All" else df[df["od"] == od_sel]
        flight_sel = st.selectbox("Flight #", ["All"] + sorted(flight_pool["flight"].unique()))
        month_sel = st.selectbox("Travel Month", MONTH_NAMES, index=7)
        cabin_sel = st.selectbox("Cabin", ["All"] + list(CABINS.values()), index=1)

        st.markdown("---")
        st.markdown("### Alert Settings")
        alert_thr = st.slider(
            "Alert threshold (%)",
            10,
            50,
            20,
            step=5,
            help=(
                "Flags any route × segment combination whose year-on-year passenger "
                "change exceeds this value in either direction. "
                "Lower = more alerts (broader scan); higher = only significant shifts. "
                "Use this to quickly surface routes that need pricing, capacity, or "
                "marketing action without reading every table manually."
            ),
        )

        st.markdown("---")
        st.markdown("### Advance Bookings")
        adv_window = st.radio("Window", ["30 days", "60 days", "90 days"], index=1)

    month_num = MONTH_NAMES.index(month_sel) + 1

    # ── Filter bar ─────────────────────────────────────────────────────────
    st.markdown(
        f"""
    <div class="filter-bar">
      <span><span class="fl">O&amp;D:</span>{od_sel}</span>
      <span><span class="fl">Travel Month:</span>{month_sel}</span>
      <span><span class="fl">Flight #:</span>{flight_sel}</span>
      <span><span class="fl">Cabin:</span>{cabin_sel}</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ── Alerts — scans full network ─────────────────────────────────────────
    alert_df = _alerts(df, month_num, cabin_sel, alert_thr)
    if not alert_df.empty:
        with st.expander(
            f"⚠  Segment Alerts — {len(alert_df)} route × segment combinations beyond ±{alert_thr}%",
            expanded=True,
        ):
            h = min(60 + len(alert_df) * 35, 320)
            components.html(render_alerts_table(alert_df), height=h, scrolling=len(alert_df) > 7)

    # ── Route-level data ───────────────────────────────────────────────────
    filt = df[df["month"] == month_num].copy()
    if od_sel != "All":
        filt = filt[filt["od"] == od_sel]
    if flight_sel != "All":
        filt = filt[filt["flight"] == flight_sel]
    if cabin_sel != "All":
        filt = filt[filt["cabin_name"] == cabin_sel]

    # All months for sparklines & advance (same od/flight/cabin, all months)
    filt_all = df.copy()
    if od_sel != "All":
        filt_all = filt_all[filt_all["od"] == od_sel]
    if flight_sel != "All":
        filt_all = filt_all[filt_all["flight"] == flight_sel]
    if cabin_sel != "All":
        filt_all = filt_all[filt_all["cabin_name"] == cabin_sel]

    if filt.empty:
        st.warning("No data for the selected filters.")
        return

    summary = _pivot(filt)
    network = _pivot(
        df[df["month"] == month_num]
        if cabin_sel == "All"
        else df[(df["month"] == month_num) & (df["cabin_name"] == cabin_sel)]
    )
    monthly = _monthly_pax(filt_all, 2026)
    lf_data = _load_factor(df, cap, month_num, od_sel, flight_sel, cabin_sel)

    # Forward months for advance tab
    n_mo = {"30 days": 1, "60 days": 2, "90 days": 3}[adv_window]
    fwd_mo = [(TODAY.month + i - 1) % 12 + 1 for i in range(1, n_mo + 1)]
    adv_data = _advance(filt_all, fwd_mo)

    show_vs_net = od_sel != "All"

    # ── Tabs ───────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Historical YoY",
            "Advance Bookings",
            "Capacity & Load Factor",
            "Model Performance",
        ]
    )

    # ── Tab 1: Historical YoY ──────────────────────────────────────────────
    with tab1:
        st.caption(
            "Compares passenger volume and average fare per segment between the same travel month "
            "in 2025 and 2026. Use the **%** columns to see each segment's share of total traffic, "
            "**Rev %** to check whether revenue moved in line with volume, and **vs. Network** to "
            "spot whether this route is outperforming or lagging the broader PAL network."
        )
        components.html(
            render_table(summary, network, monthly, 2025, 2026, month_sel, month_num, show_vs_net),
            height=360,
            scrolling=False,
        )
        st.write("")
        cc1, cc2 = st.columns(2)
        with cc1:
            with st.container(border=True):
                st.plotly_chart(
                    _hbar(
                        summary["y1_pax"][summary["y1_pax"] > 0], f"Segment Mix · 2025-{month_sel}"
                    ),
                    use_container_width=True,
                    config={"displayModeBar": False},
                )
        with cc2:
            with st.container(border=True):
                st.plotly_chart(
                    _hbar(
                        summary["y2_pax"][summary["y2_pax"] > 0], f"Segment Mix · 2026-{month_sel}"
                    ),
                    use_container_width=True,
                    config={"displayModeBar": False},
                )

    # ── Tab 2: Advance Bookings ────────────────────────────────────────────
    with tab2:
        mo_range = (
            MONTH_NAMES[fwd_mo[0] - 1]
            if len(fwd_mo) == 1
            else f"{MONTH_NAMES[fwd_mo[0] - 1]}–{MONTH_NAMES[fwd_mo[-1] - 1]}"
        )
        st.caption(
            "Shows how much demand has already been captured (booked) for upcoming departures, "
            "compared to the same booking pace at this point last year. "
            "**CY On-Hand** is what is in the system today; **LY On-Hand** is the equivalent "
            "position 12 months ago. A negative Pickup YoY % means demand is coming in slower "
            "than last year — an early warning signal for pricing or promotional action. "
            "**Projected Total** estimates final demand by dividing current on-hand by the "
            "segment's typical advance-booking rate."
        )
        st.markdown(
            f"**On-hand bookings for flights departing {mo_range} 2026** "
            f"— compared to the same forward window as of {TODAY.strftime('%b %d, %Y')} last year."
        )
        components.html(render_advance_table(adv_data, adv_window), height=310, scrolling=False)
        st.caption(
            "Advance % = share of demand typically booked this far in advance. "
            "Projected Total = CY On-Hand ÷ Advance %. "
            "Treat as indicative; actual pickup curves vary by market condition."
        )

    # ── Tab 3: Capacity & Load Factor ─────────────────────────────────────
    with tab3:
        if lf_data.empty:
            st.info("No capacity data for this filter combination.")
        else:
            st.caption(
                "Shows how efficiently seats are being filled on each flight for the selected "
                "month. **Load Factor (LF %)** is passengers ÷ available seats — the primary "
                "capacity utilisation metric. A high LF (green) means the flight is nearly full; "
                "a low LF (red) means unsold inventory that represents lost revenue. "
                "Compare LF YoY to see whether capacity and demand are growing at the same rate: "
                "rising LF suggests demand is outpacing supply; falling LF may indicate "
                "over-scheduling or weakening demand."
            )
            st.markdown(f"**Seats operated vs. passengers carried — {month_sel}**")
            h = 90 + len(lf_data) * 36
            components.html(
                render_lf_table(lf_data, 2025, 2026, month_sel), height=h, scrolling=False
            )
            st.caption(
                "LF %: passengers ÷ available seats.  Green ≥85% · Yellow 75–84% · Orange 65–74% · Red <65%"
            )

    # ── Tab 4: Model Performance ───────────────────────────────────────────
    with tab4:
        st.caption(
            "Model performance metrics from the PAL POC run on 10,000 synthetic records. "
            "**Recall** measures how well the model captures each segment — a low recall means "
            "real passengers of that type are being mislabelled as something else, "
            "costing estimated revenue equal to missed passengers × per-segment error cost. "
            "**NFR-01** is the project target: ≥91% recall on every segment before production deployment."
        )

        mc1, mc2, mc3, mc4 = st.columns(4)
        n_met = sum(1 for v in RECALL_10.values() if v >= NFR_TARGET)
        with mc1:
            st.metric(
                "Overall Accuracy",
                f"{POC_ACC}%",
                help="Share of all 10,000 POC records correctly classified across 10 segments.",
            )
        with mc2:
            st.metric(
                "Segments Meeting NFR-01",
                f"{n_met} / 10",
                help="Number of segments at or above the ≥91% recall requirement.",
            )
        with mc3:
            st.metric(
                "Est. Revenue Risk",
                f"₱{POC_REV_RISK / 1_000_000:.2f}M",
                help="Conservative misclassification cost on the POC evaluated records.",
            )
        with mc4:
            st.metric(
                "Records Processed",
                f"{POC_RECORDS:,}",
                help="Synthetic records run through the full 8-stage pipeline.",
            )

        pc1, pc2 = st.columns([1.2, 1])
        with pc1:
            with st.container(border=True):
                st.plotly_chart(
                    _recall_bar(), use_container_width=True, config={"displayModeBar": False}
                )
        with pc2:
            with st.container(border=True):
                st.plotly_chart(
                    _confusion_heatmap(), use_container_width=True, config={"displayModeBar": False}
                )

        st.write("")
        st.markdown(
            "**Per-segment breakdown — all 10 model segments sorted by recall (lowest first)**"
        )
        components.html(render_recall_table(), height=420, scrolling=False)

        fare_s, dom_s = _behavioral_stats(df)
        st.write("")
        st.markdown("**Behavioral validation — 2026 segment averages**")
        st.caption(
            "Cross-checks that each segment's observed booking behaviour matches its definition. "
            "Business should show the highest avg fare; OFW and Labor should skew heavily international."
        )
        bv1, bv2 = st.columns(2)
        with bv1:
            with st.container(border=True):
                st.plotly_chart(
                    _hbar(fare_s, "Avg Fare by Segment (₱)"),
                    use_container_width=True,
                    config={"displayModeBar": False},
                )
        with bv2:
            with st.container(border=True):
                st.plotly_chart(
                    _hbar(dom_s, "Domestic Traffic % by Segment"),
                    use_container_width=True,
                    config={"displayModeBar": False},
                )
        st.caption(
            "Recall & revenue risk from POC on 10,000 synthetic records. "
            "Confusion matrix: 5-segment rollup derived from 10-segment POC recall rates. "
            "Revenue risk = support × (1 − recall) × cost per misclassification."
        )

    # ── Footer ─────────────────────────────────────────────────────────────
    st.caption(
        "Segments via PAL ML pipeline (HDBSCAN + penalty-weighted proxy labels). "
        "10-model segments rolled up to 5 reporting categories (Leisure · VFR · Business · OFW · Labor). "
        "Demo uses synthetic data — replace build_summary() / build_capacity() with live model output for production."
    )


if __name__ == "__main__":
    main()
