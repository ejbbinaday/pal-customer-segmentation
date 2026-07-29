"""Build a Power BI project (PBIP) reproducing the PAL "Passenger Revenue & PAX Performance" mock-up.

**Why PBIP and not a `.pbix` directly.** A `.pbix` is a ZIP whose `DataModel` part is a serialised
Analysis Services tabular database in Microsoft's proprietary binary format. No open-source library
can author one that Power BI will open, and Power BI Desktop — the only thing that can write it — is
Windows-only. So this emits the **supported text format** instead:

    outputs/pbip/PAL Passenger Revenue and PAX.pbip          ← open THIS in Power BI Desktop
                 ...SemanticModel/model.bim                  TMSL model + measures + data
                 ...Report/report.json                       page layout

In Power BI Desktop: **File → Open → the `.pbip`**, then **File → Save As → `.pbix`**. That is the
one manual step, and it is unavoidable outside Windows.

Data is the mock-up's **illustrative** figures, embedded in the model as inline-CSV Power Query
expressions — so the file is self-contained, has no path dependencies, and matches the image. Where
the mock-up's own printed variance disagreed with its printed CY/LY (3 revenue rows do), the model
*computes* the variance, so those cells differ by a few tenths and are internally consistent.

Slicer values (Fareband, Channel, Booking Type) are the **real** distinct values from
`outputs/powerbi_export/`, and the value-tier ladder is the V1 dictionary's, so the controls look
authentic. They are deliberately **not** wired to the static tables — matching the mock-up's "All"
state; only the Travel Month slicer filters. See the generated README.

Run:  python src/build_pbip.py
"""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "pbip"
NAME = "PAL Passenger Revenue and PAX"

# ── brand palette (read off the mock-up) ────────────────────────────────────────
NAVY = "#0B2E5E"
NAVY_DK = "#08234A"
RED = "#E4002B"
RED_SOFT = "#F4707F"
GOLD = "#FFD100"
GREEN = "#0F9D58"
GREY = "#8A94A6"
WHITE = "#FFFFFF"
CANVAS = "#F4F6FA"
CARD_BORDER = "#E3E8F0"

PAGE_W, PAGE_H = 1448, 1086  # matches the mock-up's aspect

# ── illustrative data — reconciled so the columns sum to the mock-up's totals ────
# CY revenue sums to 178.6, LY to 168.2 (→ +6.2%); CY PAX to 20.26, LY to 19.03 (→ +6.5%).
MONTHS = [
    # label,      rev_cy, rev_ly, pax_cy, pax_ly
    ("Jul '25", 13.1, 12.4, 1.51, 1.44),
    ("Aug '25", 13.6, 12.9, 1.55, 1.48),
    ("Sep '25", 14.0, 13.4, 1.58, 1.49),
    ("Oct '25", 14.4, 13.5, 1.63, 1.56),
    ("Nov '25", 14.8, 14.0, 1.69, 1.60),
    ("Dec '25", 16.1, 15.3, 1.82, 1.72),
    ("Jan '26", 14.2, 13.4, 1.62, 1.51),
    ("Feb '26", 14.6, 13.8, 1.66, 1.53),
    ("Mar '26", 15.2, 14.1, 1.71, 1.60),
    ("Apr '26", 15.6, 14.6, 1.77, 1.65),
    ("May '26", 16.1, 15.1, 1.81, 1.69),
    ("Jun '26", 16.9, 15.7, 1.91, 1.76),
]

SEGMENTS = [
    # segment,            rev_cy, rev_ly, pax_cy, pax_ly
    ("Leisure", 59.8, 55.5, 7.06, 6.61),
    ("VFR / Balikbayan", 49.1, 45.8, 6.72, 6.19),
    ("Business", 35.2, 34.3, 3.09, 3.01),
    ("Group", 20.8, 19.8, 2.08, 1.98),
    ("Other / Unassigned", 13.7, 12.8, 1.31, 1.24),
]

# Real values from outputs/powerbi_export/model/fact_dashboard.parquet + the V1 dictionary ladder.
FAREBANDS = [
    "Business Flex",
    "Business Value",
    "Premium Economy",
    "Economy Flex",
    "Economy Value",
    "Economy Saver",
    "Economy Supersaver",
    "Groups",
    "Mabuhay Award",
    "Business Non-revenue",
    "Economy Non-revenue",
]
VALUE_TIERS = [
    "7 - Business Flex",
    "6 - Business Value",
    "5 - Premium Economy",
    "4 - Economy Flex",
    "3 - Economy Value",
    "2 - Economy Saver",
    "1 - Economy Supersaver",
]
CHANNELS = [
    "Ancillary Business Unit",
    "Contact Center",
    "Corporate Web Portal",
    "Franchise Flagship Store",
    "GSA/DSA",
    "NDC",
    "OTA",
    "Sea Crew",
    "TMC",
    "Ticket Office",
    "Traditional Travel Agency",
    "WEB/APP",
    "Unknown",
]
BOOKING_TYPES = ["Group", "Non-Group"]


# ── helpers ─────────────────────────────────────────────────────────────────────
def gid(seed: str) -> str:
    """Stable GUID per logical object, so regenerating does not churn the diff."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "pal-pbip/" + seed))


def m_csv(rows: list[tuple], headers: list[str], types: list[str]) -> str:
    """Inline-CSV Power Query expression — embeds the data with no external file dependency."""
    body = "#(lf)".join(",".join(str(v) for v in r) for r in rows)
    csv = ",".join(headers) + "#(lf)" + body
    cols = ", ".join(f'{{"{h}", {t}}}' for h, t in zip(headers, types, strict=True))
    return (
        f'let Source = Csv.Document("{csv}", [Delimiter=",", Columns={len(headers)}, '
        "Encoding=65001, QuoteStyle=QuoteStyle.None]), "
        "Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]), "
        f"Typed = Table.TransformColumnTypes(Promoted, {{{cols}}}) in Typed"
    )


def column(
    name: str,
    dtype: str,
    fmt: str | None = None,
    hidden: bool = False,
    sort_by: str | None = None,
    summarize: bool = False,
) -> dict:
    c = {
        "name": name,
        "dataType": dtype,
        "sourceColumn": name,
        "lineageTag": gid("col/" + name),
        "summarizeBy": "sum" if summarize else "none",
        "annotations": [{"name": "SummarizationSetBy", "value": "Automatic"}],
    }
    if fmt:
        c["formatString"] = fmt
    if hidden:
        c["isHidden"] = True
    if sort_by:
        c["sortByColumn"] = sort_by
    return c


def measure(name: str, expr: str, fmt: str = "") -> dict:
    m = {
        "name": name,
        "expression": expr,
        "lineageTag": gid("msr/" + name),
    }
    if fmt:  # a text-returning measure must not carry a numeric format string
        m["formatString"] = fmt
        m["annotations"] = [{"name": "PBI_FormatHint", "value": '{"isGeneralNumber":false}'}]
    return m


def table(
    name: str,
    cols: list[dict],
    rows: list[tuple],
    headers: list[str],
    types: list[str],
    measures: list[dict] | None = None,
    hidden: bool = False,
) -> dict:
    t = {
        "name": name,
        "lineageTag": gid("tbl/" + name),
        "columns": cols,
        "partitions": [
            {
                "name": f"{name}-partition",
                "mode": "import",
                "source": {"type": "m", "expression": m_csv(rows, headers, types)},
            }
        ],
        "annotations": [{"name": "PBI_ResultType", "value": "Table"}],
    }
    if measures:
        t["measures"] = measures
    if hidden:
        t["isHidden"] = True
    return t


# ── semantic model ──────────────────────────────────────────────────────────────
PESO_B = '"₱"#,0.0"B"'
PESO_B0 = '"₱"#,0"B"'
PAX_M = '#,0.00"M"'
PAX_M1 = '#,0.0"M"'
VAR_PCT = "+0.0%;-0.0%;0.0%"


def build_model() -> dict:
    monthly = table(
        "Monthly",
        [
            column("MonthSort", "int64", hidden=True),
            column("Month", "string", sort_by="MonthSort"),
            column("RevenueCY", "double", PESO_B, summarize=True),
            column("RevenueLY", "double", PESO_B, summarize=True),
            column("PaxCY", "double", PAX_M, summarize=True),
            column("PaxLY", "double", PAX_M, summarize=True),
        ],
        [(i + 1, m[0], m[1], m[2], m[3], m[4]) for i, m in enumerate(MONTHS)],
        ["MonthSort", "Month", "RevenueCY", "RevenueLY", "PaxCY", "PaxLY"],
        ["Int64.Type", "type text", "type number", "type number", "type number", "type number"],
        measures=[
            measure("Net Revenue CY", "SUM(Monthly[RevenueCY])", PESO_B0),
            measure("Net Revenue LY", "SUM(Monthly[RevenueLY])", PESO_B0),
            measure("Net PAX CY", "SUM(Monthly[PaxCY])", PAX_M1),
            measure("Net PAX LY", "SUM(Monthly[PaxLY])", PAX_M1),
            measure("12M Net Revenue", "SUM(Monthly[RevenueCY])", PESO_B),
            measure("12M Net PAX", "SUM(Monthly[PaxCY])", PAX_M1),
            measure(
                "Revenue Variance %",
                "DIVIDE([Net Revenue CY] - [Net Revenue LY], [Net Revenue LY])",
                VAR_PCT,
            ),
            measure("PAX Variance %", "DIVIDE([Net PAX CY] - [Net PAX LY], [Net PAX LY])", VAR_PCT),
            measure(
                "Months Selected",
                'VAR n = DISTINCTCOUNT(Monthly[Month]) RETURN n & " MONTHS"',
                "",
            ),
        ],
    )
    segments = table(
        "Segment Performance",
        [
            column("SegmentSort", "int64", hidden=True),
            column("Segment", "string", sort_by="SegmentSort"),
            column("SegRevenueCY", "double", PESO_B, hidden=True, summarize=True),
            column("SegRevenueLY", "double", PESO_B, hidden=True, summarize=True),
            column("SegPaxCY", "double", PAX_M, hidden=True, summarize=True),
            column("SegPaxLY", "double", PAX_M, hidden=True, summarize=True),
        ],
        [(i + 1, s[0], s[1], s[2], s[3], s[4]) for i, s in enumerate(SEGMENTS)],
        ["SegmentSort", "Segment", "SegRevenueCY", "SegRevenueLY", "SegPaxCY", "SegPaxLY"],
        ["Int64.Type", "type text", "type number", "type number", "type number", "type number"],
        measures=[
            measure("Segment Revenue CY", "SUM('Segment Performance'[SegRevenueCY])", PESO_B),
            measure("Segment Revenue LY", "SUM('Segment Performance'[SegRevenueLY])", PESO_B),
            measure("Segment PAX CY", "SUM('Segment Performance'[SegPaxCY])", PAX_M),
            measure("Segment PAX LY", "SUM('Segment Performance'[SegPaxLY])", PAX_M),
            measure(
                "Segment Revenue Variance %",
                "DIVIDE([Segment Revenue CY] - [Segment Revenue LY], [Segment Revenue LY])",
                VAR_PCT,
            ),
            measure(
                "Segment PAX Variance %",
                "DIVIDE([Segment PAX CY] - [Segment PAX LY], [Segment PAX LY])",
                VAR_PCT,
            ),
        ],
    )
    dims = [
        ("Fareband", "Fareband", FAREBANDS),
        ("Fareband Value Tier", "Value Tier", VALUE_TIERS),
        ("Channel", "Channel", CHANNELS),
        ("Booking Type", "Booking Type", BOOKING_TYPES),
    ]
    dim_tables = [
        table(
            tname,
            [column("Sort", "int64", hidden=True), column(cname, "string", sort_by="Sort")],
            [(i + 1, v) for i, v in enumerate(vals)],
            ["Sort", cname],
            ["Int64.Type", "type text"],
        )
        for tname, cname, vals in dims
    ]
    return {
        "name": "SemanticModel",
        "compatibilityLevel": 1567,
        "model": {
            "culture": "en-US",
            "dataAccessOptions": {
                "legacyRedirects": True,
                "returnErrorValuesAsNull": True,
            },
            "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "sourceQueryCulture": "en-US",
            "tables": [monthly, segments, *dim_tables],
            "annotations": [
                {
                    "name": "PBI_QueryOrder",
                    "value": json.dumps(["Monthly", "Segment Performance", *[d[0] for d in dims]]),
                },
                {"name": "__PBI_TimeIntelligenceEnabled", "value": "0"},
            ],
        },
    }


# ── report layout ───────────────────────────────────────────────────────────────
def _sel(table_: str, col: str, alias: str = "c") -> dict:
    return {"Column": {"Expression": {"SourceRef": {"Source": alias}}, "Property": col}}


def _msr(name: str, alias: str = "c") -> dict:
    return {"Measure": {"Expression": {"SourceRef": {"Source": alias}}, "Property": name}}


def container(x, y, w, h, z, cfg: dict) -> dict:
    cfg["layouts"] = [{"id": 0, "position": {"x": x, "y": y, "z": z, "width": w, "height": h}}]
    return {
        "x": x,
        "y": y,
        "z": z,
        "width": w,
        "height": h,
        "config": json.dumps(cfg, ensure_ascii=False),
    }


def solid(color: str) -> dict:
    return {"solid": {"color": {"expr": {"Literal": {"Value": f"'{color}'"}}}}}


def lit(v) -> dict:
    if isinstance(v, bool):
        return {"expr": {"Literal": {"Value": "true" if v else "false"}}}
    if isinstance(v, (int, float)):
        return {"expr": {"Literal": {"Value": f"{v}D"}}}
    return {"expr": {"Literal": {"Value": f"'{v}'"}}}


def shape(name, x, y, w, h, z, fill, radius=8, border=None) -> dict:
    # NB: colours must be {"solid":{"color":{"expr":{"Literal":...}}}} — dropping the "expr"
    # wrapper (as an earlier revision did) silently produces an unreadable visual.
    obj = {
        "shape": [{"properties": {"tileShape": lit("rectangle"), "roundEdge": lit(radius)}}],
        "fill": [
            {
                "properties": {
                    "fillColor": solid(fill),
                    "show": lit(True),
                    "transparency": lit(0),
                }
            }
        ],
    }
    if border:
        obj["outline"] = [
            {
                "properties": {
                    "show": lit(True),
                    "lineColor": solid(border),
                    "weight": lit(1),
                }
            }
        ]
    else:
        obj["outline"] = [{"properties": {"show": lit(False)}}]
    return container(
        x,
        y,
        w,
        h,
        z,
        {
            "name": gid("shape/" + name),
            "singleVisual": {
                "visualType": "shape",
                "objects": obj,
                "drillFilterOtherVisuals": True,
            },
        },
    )


def textbox(name, x, y, w, h, z, runs: list[dict], align="left") -> dict:
    paragraphs = [{"horizontalTextAlignment": align, "textRuns": runs}]
    return container(
        x,
        y,
        w,
        h,
        z,
        {
            "name": gid("text/" + name),
            "singleVisual": {
                "visualType": "textbox",
                "objects": {"general": [{"properties": {"paragraphs": paragraphs}}]},
                "vcObjects": {
                    "background": [{"properties": {"show": lit(False)}}],
                    "border": [{"properties": {"show": lit(False)}}],
                },
                "drillFilterOtherVisuals": True,
            },
        },
    )


def run(text, size=11, color="#1B2A41", bold=False, italic=False) -> dict:
    style = f"font-size:{size}pt;color:{color};"
    if bold:
        style += "font-weight:bold;"
    if italic:
        style += "font-style:italic;"
    return {
        "value": text,
        "textStyle": {
            "fontSize": f"{size}pt",
            "color": color,
            "fontWeight": "bold" if bold else "normal",
            "fontStyle": "italic" if italic else "normal",
        },
        "_style": style,  # ignored by Power BI; kept only to make generated JSON readable
    }


def card(name, x, y, w, h, z, measure_name, tbl, label=None, color=NAVY, size=28) -> dict:
    cfg = {
        "name": gid("card/" + name),
        "singleVisual": {
            "visualType": "card",
            "projections": {"Values": [{"queryRef": f"{tbl}.{measure_name}"}]},
            "prototypeQuery": {
                "Version": 2,
                "From": [{"Name": "c", "Entity": tbl, "Type": 0}],
                "Select": [dict(_msr(measure_name), Name=f"{tbl}.{measure_name}")],
            },
            "objects": {
                "labels": [
                    {
                        "properties": {
                            "fontSize": lit(size),
                            "color": solid(color),
                            "fontFamily": lit("Segoe UI Bold"),
                        }
                    }
                ],
                "categoryLabels": [{"properties": {"show": lit(bool(label))}}],
            },
            "vcObjects": {
                "background": [{"properties": {"show": lit(False)}}],
                "border": [{"properties": {"show": lit(False)}}],
                "title": [
                    {
                        "properties": {
                            "show": lit(bool(label)),
                            "text": lit(label or ""),
                            "fontSize": lit(8),
                            "fontColor": solid(GREY),
                        }
                    }
                ],
            },
            "drillFilterOtherVisuals": True,
        },
    }
    return container(x, y, w, h, z, cfg)


def line_chart(name, x, y, w, h, z, tbl, cat, ly_measure, cy_measure, y_format_max=None) -> dict:
    sel = [
        dict(_sel(tbl, cat), Name=f"{tbl}.{cat}"),
        dict(_msr(ly_measure), Name=f"{tbl}.{ly_measure}"),
        dict(_msr(cy_measure), Name=f"{tbl}.{cy_measure}"),
    ]
    cfg = {
        "name": gid("line/" + name),
        "singleVisual": {
            "visualType": "lineChart",
            "projections": {
                "Category": [{"queryRef": f"{tbl}.{cat}"}],
                "Y": [{"queryRef": f"{tbl}.{ly_measure}"}, {"queryRef": f"{tbl}.{cy_measure}"}],
            },
            "prototypeQuery": {
                "Version": 2,
                "From": [{"Name": "c", "Entity": tbl, "Type": 0}],
                "Select": sel,
                "OrderBy": [{"Direction": 1, "Expression": _sel(tbl, cat)}],
            },
            "objects": {
                "legend": [
                    {
                        "properties": {
                            "show": lit(True),
                            "position": lit("Top"),
                            "fontSize": lit(9),
                            "labelColor": solid("#54617A"),
                            "showTitle": lit(False),
                        }
                    }
                ],
                "categoryAxis": [
                    {
                        "properties": {
                            "show": lit(True),
                            "fontSize": lit(8),
                            "labelColor": solid(GREY),
                            "showAxisTitle": lit(False),
                            "gridlineShow": lit(False),
                        }
                    }
                ],
                "valueAxis": [
                    {
                        "properties": {
                            "show": lit(True),
                            "fontSize": lit(8),
                            "labelColor": solid(GREY),
                            "showAxisTitle": lit(False),
                            "gridlineColor": solid("#EDF0F5"),
                        }
                    }
                ],
                "labels": [{"properties": {"show": lit(False)}}],
                "dataPoint": [
                    {
                        "properties": {"fill": solid(NAVY)},
                        "selector": {"metadata": f"{tbl}.{ly_measure}"},
                    },
                    {
                        "properties": {"fill": solid(RED)},
                        "selector": {"metadata": f"{tbl}.{cy_measure}"},
                    },
                ],
                "lineStyles": [
                    {
                        "properties": {
                            "strokeWidth": lit(2),
                            "showMarker": lit(True),
                            "markerShape": lit("circle"),
                            "markerSize": lit(4),
                        },
                        "selector": {"metadata": f"{tbl}.{ly_measure}"},
                    },
                    {
                        "properties": {
                            "strokeWidth": lit(2),
                            "lineStyle": lit("dashed"),
                            "showMarker": lit(False),
                        },
                        "selector": {"metadata": f"{tbl}.{cy_measure}"},
                    },
                ],
            },
            "vcObjects": {
                "background": [{"properties": {"show": lit(False)}}],
                "border": [{"properties": {"show": lit(False)}}],
                "title": [{"properties": {"show": lit(False)}}],
            },
            "drillFilterOtherVisuals": True,
        },
    }
    if y_format_max:
        cfg["singleVisual"]["objects"]["valueAxis"][0]["properties"]["start"] = lit(y_format_max)
    return container(x, y, w, h, z, cfg)


def segment_table(name, x, y, w, h, z, cy, ly, var) -> dict:
    tbl = "Segment Performance"
    sel = [
        dict(_sel(tbl, "Segment"), Name=f"{tbl}.Segment"),
        dict(_msr(cy), Name=f"{tbl}.{cy}"),
        dict(_msr(ly), Name=f"{tbl}.{ly}"),
        dict(_msr(var), Name=f"{tbl}.{var}"),
    ]
    cfg = {
        "name": gid("table/" + name),
        "singleVisual": {
            "visualType": "tableEx",
            "projections": {
                "Values": [
                    {"queryRef": f"{tbl}.Segment"},
                    {"queryRef": f"{tbl}.{cy}"},
                    {"queryRef": f"{tbl}.{ly}"},
                    {"queryRef": f"{tbl}.{var}"},
                ]
            },
            "prototypeQuery": {
                "Version": 2,
                "From": [{"Name": "c", "Entity": tbl, "Type": 0}],
                "Select": sel,
                "OrderBy": [{"Direction": 1, "Expression": _sel(tbl, "Segment")}],
            },
            "objects": {
                "grid": [
                    {
                        "properties": {
                            "gridVertical": lit(False),
                            "gridHorizontalColor": solid("#EDF0F5"),
                            "rowPadding": lit(6),
                            "outlineColor": solid("#FFFFFF"),
                        }
                    }
                ],
                "columnHeaders": [
                    {
                        "properties": {
                            "fontColor": solid("#54617A"),
                            "backColor": solid("#F7F9FC"),
                            "fontSize": lit(9),
                            "bold": lit(True),
                            "alignment": lit("Left"),
                        }
                    }
                ],
                "values": [
                    {
                        "properties": {
                            "fontSize": lit(10),
                            "fontColor": solid("#1B2A41"),
                            "backColor": solid(WHITE),
                        }
                    }
                ],
                "total": [
                    {
                        "properties": {
                            "totals": lit(True),
                            "fontColor": solid(WHITE),
                            "backColor": solid(NAVY),
                            "fontSize": lit(10),
                            "bold": lit(True),
                        }
                    }
                ],
            },
            "vcObjects": {
                "background": [{"properties": {"show": lit(False)}}],
                "border": [{"properties": {"show": lit(False)}}],
                "title": [{"properties": {"show": lit(False)}}],
            },
            "drillFilterOtherVisuals": True,
        },
    }
    return container(x, y, w, h, z, cfg)


def slicer(name, x, y, w, h, z, tbl, col, mode="Dropdown", header=True) -> dict:
    cfg = {
        "name": gid("slicer/" + name),
        "singleVisual": {
            "visualType": "slicer",
            "projections": {"Values": [{"queryRef": f"{tbl}.{col}"}]},
            "prototypeQuery": {
                "Version": 2,
                "From": [{"Name": "c", "Entity": tbl, "Type": 0}],
                "Select": [dict(_sel(tbl, col), Name=f"{tbl}.{col}")],
            },
            "objects": {
                "data": [{"properties": {"mode": lit(mode)}}],
                "header": [
                    {
                        "properties": {
                            "show": lit(header),
                            "fontColor": solid(NAVY),
                            "fontSize": lit(11),
                            "bold": lit(True),
                            "background": solid(WHITE),
                            "outline": lit("None"),
                        }
                    }
                ],
                "items": [
                    {
                        "properties": {
                            "fontColor": solid("#1B2A41"),
                            "fontSize": lit(10),
                            "background": solid(WHITE),
                        }
                    }
                ],
                "selection": [
                    {
                        "properties": {
                            "selectAllCheckboxEnabled": lit(True),
                            "singleSelect": lit(False),
                        }
                    }
                ],
            },
            "vcObjects": {
                "background": [{"properties": {"show": lit(False)}}],
                "border": [{"properties": {"show": lit(False)}}],
                "title": [{"properties": {"show": lit(False)}}],
            },
            "drillFilterOtherVisuals": True,
        },
    }
    return container(x, y, w, h, z, cfg)


def build_report() -> dict:
    v: list[dict] = []
    z = 0

    def nz():
        nonlocal z
        z += 1
        return z

    # ── header band ──
    v.append(shape("hdr", 0, 0, PAGE_W, 118, nz(), NAVY, radius=0))
    v.append(shape("hdr-rule", 0, 112, PAGE_W, 6, nz(), RED, radius=0))
    v.append(
        textbox("brand", 118, 14, 480, 44, nz(), [run("Philippine Airlines", 26, WHITE, bold=True)])
    )
    v.append(
        textbox(
            "tagline",
            120,
            54,
            400,
            22,
            nz(),
            [run("The Heart of the Filipino", 10, "#C7D4E8", italic=True)],
        )
    )
    v.append(
        textbox(
            "unit",
            120,
            78,
            520,
            20,
            nz(),
            [run("COMMERCIAL ANALYTICS  •  POWER BI REPORT MOCK-UP", 8, "#9FB4D4")],
        )
    )
    # flag-mark stand-in (no PAL logo asset in the repo — see README)
    v.append(shape("mark", 20, 20, 84, 58, nz(), "#123A70", radius=4, border="#2C5A9A"))
    v.append(
        textbox(
            "mark-txt", 24, 34, 76, 30, nz(), [run("PAL", 20, WHITE, bold=True)], align="center"
        )
    )
    v.append(
        textbox(
            "title",
            900,
            20,
            528,
            34,
            nz(),
            [run("Passenger Revenue & PAX Performance", 19, WHITE, bold=True)],
            align="right",
        )
    )
    v.append(
        textbox(
            "subtitle",
            900,
            58,
            528,
            22,
            nz(),
            [run("Illustrative data  |  Latest complete travel month: Jun 2026", 9, "#C7D4E8")],
            align="right",
        )
    )

    # ── left slicer rail ──
    rail = [
        ("Fareband", "Fareband", "Fareband", 148),
        ("Fareband Value Tier", "Fareband Value Tier", "Value Tier", 347),
        ("Channel", "Channel", "Channel", 546),
        ("Booking Type", "Booking Type", "Booking Type", 745),
    ]
    for label, tbl, col, top in rail:
        v.append(shape("card-" + label, 18, top, 228, 178, nz(), WHITE, border=CARD_BORDER))
        v.append(slicer("sl-" + label, 34, top + 14, 196, 96, nz(), tbl, col))

    # ── timeline card ──
    v.append(shape("card-timeline", 262, 148, 1166, 84, nz(), WHITE, border=CARD_BORDER))
    v.append(textbox("tl-kicker", 282, 158, 260, 16, nz(), [run("TRAVEL MONTH", 8, GREY)]))
    v.append(
        textbox(
            "tl-title",
            282,
            172,
            300,
            26,
            nz(),
            [run("Rolling 12-Month Timeline", 14, NAVY, bold=True)],
        )
    )
    v.append(
        textbox(
            "tl-note",
            282,
            200,
            320,
            18,
            nz(),
            [run("Maximum window: last 12 complete months", 8, GREY)],
        )
    )
    v.append(
        slicer("sl-month", 612, 156, 664, 68, nz(), "Monthly", "Month", mode="Basic", header=False)
    )
    v.append(shape("card-selected", 1284, 156, 136, 68, nz(), NAVY))
    v.append(
        textbox(
            "sel-kicker", 1294, 164, 120, 14, nz(), [run("SELECTED", 7, "#9FB4D4")], align="center"
        )
    )
    v.append(
        card(
            "sel-count",
            1284,
            178,
            136,
            40,
            nz(),
            "Months Selected",
            "Monthly",
            color=WHITE,
            size=15,
        )
    )

    # ── section 1 ──
    v.append(
        textbox(
            "s1",
            268,
            246,
            600,
            22,
            nz(),
            [run("SECTION 1  •  MONTHLY PERFORMANCE", 9, NAVY, bold=True)],
        )
    )
    for i, (key, title, sub, ly, cy, tot, delta, endlbl) in enumerate(
        [
            (
                "rev",
                "Net Revenue: CY vs LY",
                "Monthly net revenue - rolling 12 months - ₱ billions",
                "Net Revenue LY",
                "Net Revenue CY",
                "12M Net Revenue",
                "Revenue Variance %",
                "₱16.9B",
            ),
            (
                "pax",
                "Net PAX: CY vs LY",
                "Monthly flown passenger count - rolling 12 months - millions",
                "Net PAX LY",
                "Net PAX CY",
                "12M Net PAX",
                "PAX Variance %",
                "1.91M",
            ),
        ]
    ):
        x0 = 262 + i * 592
        accent = RED if key == "rev" else NAVY
        v.append(shape(f"card-{key}", x0, 276, 574, 348, nz(), WHITE, border=CARD_BORDER))
        v.append(shape(f"tick-{key}", x0 + 20, 294, 5, 20, nz(), accent, radius=2))
        v.append(
            textbox(f"t-{key}", x0 + 34, 292, 320, 24, nz(), [run(title, 13, NAVY, bold=True)])
        )
        v.append(textbox(f"st-{key}", x0 + 34, 316, 380, 18, nz(), [run(sub, 8, GREY)]))
        v.append(shape(f"kpi-{key}", x0 + 372, 292, 186, 50, nz(), "#F7F9FC", border=CARD_BORDER))
        v.append(
            textbox(
                f"kpi-lbl-{key}",
                x0 + 382,
                296,
                170,
                14,
                nz(),
                [run(("12M NET REVENUE" if key == "rev" else "12M NET PAX"), 7, GREY)],
            )
        )
        v.append(card(f"kpi-val-{key}", x0 + 378, 310, 108, 30, nz(), tot, "Monthly", size=15))
        v.append(
            card(
                f"kpi-var-{key}",
                x0 + 486,
                310,
                70,
                26,
                nz(),
                delta,
                "Monthly",
                color=GREEN,
                size=11,
            )
        )
        v.append(
            textbox(
                f"endlbl-{key}",
                x0 + 470,
                344,
                90,
                18,
                nz(),
                [run(endlbl, 9, RED, bold=True)],
                align="right",
            )
        )
        v.append(
            line_chart(f"chart-{key}", x0 + 20, 360, 538, 250, nz(), "Monthly", "Month", ly, cy)
        )

    # ── section 2 ──
    v.append(
        textbox(
            "s2",
            268,
            634,
            600,
            22,
            nz(),
            [run("SECTION 2  •  SEGMENT PERFORMANCE", 9, NAVY, bold=True)],
        )
    )
    for i, (key, title, cy, ly, var) in enumerate(
        [
            (
                "rev",
                "Net Revenue by Segment",
                "Segment Revenue CY",
                "Segment Revenue LY",
                "Segment Revenue Variance %",
            ),
            (
                "pax",
                "Net PAX by Segment",
                "Segment PAX CY",
                "Segment PAX LY",
                "Segment PAX Variance %",
            ),
        ]
    ):
        x0 = 262 + i * 592
        accent = RED if key == "rev" else NAVY
        v.append(shape(f"scard-{key}", x0, 660, 574, 320, nz(), WHITE, border=CARD_BORDER))
        v.append(shape(f"stick-{key}", x0 + 20, 678, 5, 20, nz(), accent, radius=2))
        v.append(
            textbox(f"s2t-{key}", x0 + 34, 676, 340, 24, nz(), [run(title, 13, NAVY, bold=True)])
        )
        v.append(
            textbox(
                f"s2st-{key}",
                x0 + 34,
                700,
                400,
                18,
                nz(),
                [run("Selected timeline total - CY vs LY - variance %", 8, GREY)],
            )
        )
        v.append(segment_table(f"stbl-{key}", x0 + 20, 726, 538, 238, nz(), cy, ly, var))

    # ── footer ──
    v.append(shape("footer", 0, 998, PAGE_W, 88, nz(), NAVY, radius=0))
    v.append(
        textbox(
            "foot-l",
            24,
            1024,
            760,
            22,
            nz(),
            [
                run(
                    "Data basis: TravelMonth  |  Measures: NetRevenue, PaxCount  |  "
                    "Comparison: same month prior year",
                    9,
                    "#C7D4E8",
                )
            ],
        )
    )
    v.append(
        textbox(
            "foot-r",
            900,
            1024,
            528,
            22,
            nz(),
            [run("STATIC POWER BI MOCK-UP  •  VALUES ARE ILLUSTRATIVE", 9, GOLD, bold=True)],
            align="right",
        )
    )

    return {
        "id": 0,
        "resourcePackages": [
            {
                "resourcePackage": {
                    "disabled": False,
                    "items": [{"name": "PALTheme", "path": "PALTheme.json", "type": 202}],
                    "name": "SharedResources",
                    "type": 2,
                }
            }
        ],
        "sections": [
            {
                "id": 0,
                "name": gid("section/main"),
                "displayName": "Revenue & PAX",
                "filters": "[]",
                "ordinal": 0,
                "visualContainers": v,
                "config": json.dumps(
                    {
                        "relationships": [],
                        "objects": {
                            "background": [
                                {"properties": {"color": solid(CANVAS), "transparency": lit(0)}}
                            ],
                            "outspace": [{"properties": {"color": solid(CANVAS)}}],
                        },
                    }
                ),
                "width": PAGE_W,
                "height": PAGE_H,
                "displayOption": 1,
            }
        ],
        "config": json.dumps(
            {
                "version": "5.55",
                "themeCollection": {
                    "customTheme": {"name": "PALTheme", "version": "5.55", "type": 2}
                },
                "activeSectionIndex": 0,
                "defaultDrillFilterOtherVisuals": True,
                "settings": {"useStylableVisualContainerHeader": True},
            }
        ),
        "layoutOptimization": 0,
        "publicCustomVisuals": [],
    }


THEME = {
    "name": "PALTheme",
    "dataColors": [NAVY, RED, "#2C5A9A", RED_SOFT, GOLD, GREEN, GREY, "#123A70"],
    "background": CANVAS,
    "foreground": "#1B2A41",
    "tableAccent": RED,
    "textClasses": {
        "title": {"fontFace": "Segoe UI Bold", "fontSize": 13, "color": NAVY},
        "label": {"fontFace": "Segoe UI", "fontSize": 9, "color": "#54617A"},
        "callout": {"fontFace": "Segoe UI Bold", "fontSize": 24, "color": NAVY},
    },
    # Deliberately minimal: the layout draws its own white cards as shapes, so forcing a background
    # on every visual here would double up and put white boxes behind the textboxes.
    "visualStyles": {"*": {"*": {"border": [{"show": False}]}}},
}


# ── emit ────────────────────────────────────────────────────────────────────────
def write(path: Path, obj, raw: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = raw if raw is not None else json.dumps(obj, indent=2, ensure_ascii=False)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    sm = OUT / f"{NAME}.SemanticModel"
    rp = OUT / f"{NAME}.Report"

    write(
        OUT / f"{NAME}.pbip",
        {
            "version": "1.0",
            "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
            "settings": {"enableAutoRecovery": True},
        },
    )
    write(sm / "definition.pbism", {"version": "1.0", "settings": {}})
    write(sm / "model.bim", build_model())
    write(
        sm / ".platform",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": "SemanticModel", "displayName": NAME},
            "config": {"version": "2.0", "logicalId": gid("logical/semanticmodel")},
        },
    )
    write(
        rp / "definition.pbir",
        {
            "version": "1.0",
            "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}},
        },
    )
    write(rp / "report.json", build_report())
    write(rp / "StaticResources" / "SharedResources" / "PALTheme.json", THEME)
    write(
        rp / ".platform",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": "Report", "displayName": NAME},
            "config": {"version": "2.0", "logicalId": gid("logical/report")},
        },
    )

    # CSV fallback — guaranteed usable even if a Desktop version rejects the project
    data = OUT / "data"
    write(
        data / "Monthly.csv",
        None,
        raw="Month,RevenueCY,RevenueLY,PaxCY,PaxLY\n"
        + "\n".join(f"{m[0]},{m[1]},{m[2]},{m[3]},{m[4]}" for m in MONTHS)
        + "\n",
    )
    write(
        data / "SegmentPerformance.csv",
        None,
        raw="Segment,SegRevenueCY,SegRevenueLY,SegPaxCY,SegPaxLY\n"
        + "\n".join(f"{s[0]},{s[1]},{s[2]},{s[3]},{s[4]}" for s in SEGMENTS)
        + "\n",
    )
    for fname, header, vals in [
        ("Fareband.csv", "Fareband", FAREBANDS),
        ("ValueTier.csv", "Value Tier", VALUE_TIERS),
        ("Channel.csv", "Channel", CHANNELS),
        ("BookingType.csv", "Booking Type", BOOKING_TYPES),
    ]:
        write(data / fname, None, raw=header + "\n" + "\n".join(vals) + "\n")

    write(OUT / "README.md", None, raw=README)
    n_vis = len(build_report()["sections"][0]["visualContainers"])
    print(f"Wrote {OUT}")
    print(f"  {NAME}.pbip  ← open this in Power BI Desktop, then File > Save As > .pbix")
    print(f"  model.bim: {len(build_model()['model']['tables'])} tables")
    print(f"  report.json: {n_vis} visual containers, page {PAGE_W}x{PAGE_H}")
    print("  data/: 6 CSVs (fallback)")


README = f"""# PAL "Passenger Revenue & PAX Performance" — Power BI project

Generated by `src/build_pbip.py`. Regenerate with `python src/build_pbip.py`.

## Open it, then save as .pbix

1. **Power BI Desktop → File → Open → `{NAME}.pbip`**
2. **File → Save As → `{NAME}.pbix`**

That second step is the only way to get a `.pbix`. A `.pbix`'s `DataModel` part is a serialised
Analysis Services database in Microsoft's proprietary binary format — no tool outside Power BI
Desktop can write one, and Desktop is Windows-only, so it could not be produced on macOS.

**This project was not test-opened.** There is no Power BI Desktop on macOS to open it with, so the
JSON is structurally valid and schema-shaped but unverified against a real Desktop build. If Desktop
reports an error, paste the message and it can be corrected quickly — or use the CSV fallback below,
which cannot fail.

## What's in it

| Table | Rows | Purpose |
|---|---|---|
| `Monthly` | 12 | CY/LY revenue + PAX by travel month; drives both line charts and the KPI cards |
| `Segment Performance` | 5 | CY/LY revenue + PAX by segment; drives both variance tables |
| `Fareband`, `Fareband Value Tier`, `Channel`, `Booking Type` | 11/7/13/2 | slicer dimensions |

Data is embedded as inline-CSV Power Query expressions, so the file is self-contained — no external
paths, nothing to refresh.

## Honest notes on fidelity

- **The four left-hand slicers are not wired to the data.** They exist for layout fidelity and carry
  the *real* distinct values from `outputs/powerbi_export/` (and the V1 dictionary's value-tier
  ladder), but the static tables have no fareband/channel breakdown to filter, so they behave like
  the mock-up's "All" state. **The Travel Month slicer does filter** both charts and both tables.
- **Three revenue variance cells differ from the mock-up by a few tenths.** The mock-up's printed
  variances don't all tie to its own printed CY/LY values (Business +2.7% vs 2.6% computed, Group
  +4.6% vs 5.1%, Other +7.4% vs 7.0%). The model *computes* variance, so it is internally
  consistent instead. PAX variances match exactly.
- **No PAL flag logo** — the repo has no logo asset, so the header uses a "PAL" mark as a
  placeholder. Drop a PNG/SVG in and swap the shape for an image visual.
- Fonts, exact paddings and the timeline's chip styling approximate the mock-up; Power BI's slicer
  and card chrome cannot be styled to arbitrary pixel positions.

## Values are illustrative — and the real data disagrees

The mock-up is labelled illustrative, and it is. Against the real extract for the same window
(Jul 2025 – Jun 2026 vs prior year):

| | This mock-up | Real data |
|---|---|---|
| Net Revenue | ₱178.6B, **+6.2%** | ₱2.6B, **flat** |
| Net PAX | 20.3M, **+6.5%** | 15.94M, **−1.1%** |

Two things follow. The growth story shown here is **not** what the data currently supports. And
**revenue per passenger in the real extract is ₱163** (net fare ₱137), which is not a credible
airline fare — `NetRevenue`'s units/currency need confirming with PAL before any revenue figure is
presented. See `docs/knowledge-base.md`.

The mock-up does get one thing exactly right: "Latest complete travel month: Jun 2026" matches
`IsCompleteTravelMonth` in the export.

## CSV fallback (cannot fail)

If the project won't open, build it manually in ~10 minutes: **Get Data → Text/CSV** for each file
in `data/`, then add the measures listed in `model.bim` (`Net Revenue CY`, `Revenue Variance %`, …).
`PALTheme.json` under `{NAME}.Report/StaticResources/SharedResources/` can be applied via
**View → Themes → Browse for themes**.
"""


if __name__ == "__main__":
    main()
