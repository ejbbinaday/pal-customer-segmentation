"""Power BI export — the preliminary segmented fact table.

Joins the **booking-grain** segmentation (`proxy_segment` from Stage F) back down onto the
**coupon-grain** cleaned data, so every field the dashboards need is present at its native grain
(`Sector`, `OperatingFlightNumber`, `OperatingCabinClass`, `CurrentCouponStatus`, `is_nonstop` are
coupon attributes; the segment is a property of the booking that owns the coupon).

Outputs — pick per dashboard:

    START-HERE.md                  5-min starter guide (copied from docs/powerbi-guide.md)
    summary.md                     field dictionary, reconciliation, caveats
    model/dim_date.csv             Date dimension for DAX time intelligence
    model/fact_dashboard.parquet   headline grain (~2.1M rows) — bind the summary visuals here
    model/fact_flight/             flight-level rollup (~20.6M) — full dashboard incl. flight no.
    detail/fact_coupons/           coupon grain (38.1M) — only for Age / UniqueID
    qa/sample_100k.csv             build + validate DAX before moving GBs

`CustomerSegment` is the **rule-based proxy segment** (preliminary — see docs/methodology.md).
Coupons whose customer was excluded from Stage F (every coupon non-revenue) get the explicit label
`Excluded (non-revenue)` rather than NULL, so Power BI totals still reconcile to the full extract.

Run:  python src/export_powerbi.py            (~3-6 min)
      python src/export_powerbi.py --no-agg   (skip both aggregate builds)
"""

import argparse
import shutil
from datetime import date, timedelta
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "interim" / "pal_clean"
BOOKING = ROOT / "data" / "interim" / "pal_features_booking.parquet"
CUSTOMER = ROOT / "data" / "interim" / "pal_features_customer.parquet"
GUIDE_SRC = ROOT / "docs" / "powerbi-guide.md"
OUT = ROOT / "outputs" / "powerbi_export"

# Handoff layout — one folder, self-explanatory to someone who has never seen the project.
#   START-HERE.md / summary.md   docs, read in that order
#   model/                       the three things you actually load into Power BI
#   detail/                      full coupon grain; only needed for Age / UniqueID
#   qa/                          sample for building + validating DAX before moving GBs
MODEL = OUT / "model"
DETAIL = OUT / "detail"
QA = OUT / "qa"

COUPONS = DETAIL / "fact_coupons"
AGG = MODEL / "fact_flight"
AGG_DASH = MODEL / "fact_dashboard.parquet"
DIM_DATE = MODEL / "dim_date.csv"
SAMPLE = QA / "sample_100k.csv"
GUIDE_OUT = OUT / "START-HERE.md"
TMP = OUT / ".duckdb_tmp"

EXCLUDED = "Excluded (non-revenue)"

# Deterministic leg order within a booking — drives IsPrimaryCoupon.
LEG_ORDER = "cl.coupon_number, cl.departure_date, cl.sector, cl.flight_number"

# The requested field list → where each one comes from. Drives both the SELECT and the summary doc.
# (name, expression, note).  {as_of}/{last_month}/{years} are substituted from the data.
FIELDS = [
    # ── core requested ────────────────────────────────────────────────────────────
    ("CustomerSegment", f"coalesce(b.proxy_segment, '{EXCLUDED}')", "model output (booking grain)"),
    ("PaxCount", "cl.pax_count", "passthrough — ⚠️ *sectoral* count, ≈always 1, NOT party size"),
    ("NetRevenue", "cl.revenue", "passthrough — V1 `Revenues w YQ` = base fare + YQ surcharge"),
    ("NetFare", "cl.net_fare", "passthrough — V1 `Net Fare` = total base fare, EXCLUDES YQ"),
    ("DepartureDate", "cast(cl.departure_date AS DATE)", "passthrough"),
    ("DateOfIssuance", "cl.issue_date", "passthrough"),
    ("CurrentCouponStatus", "cl.coupon_status", "passthrough — F = flown, O = open"),
    (
        "DaysBeforeMonthEnd",
        "cl.days_before_month_end",
        "passthrough — ⚠️ departure-month metadata, NOT a snapshot; cannot drive pickup",
    ),
    ("OnlineOD", "cl.online_od", "passthrough — PR-operated O&D"),
    ("TripOD", "cl.trip_od", "passthrough — full journey incl. interline"),
    ("Sector", "cl.sector", "passthrough — the single flown leg"),
    ("OperatingFlightNumber", "cl.flight_number", "passthrough"),
    ("OperatingCabinClass", "cl.cabin", "passthrough (nulls → 'Unknown')"),
    ("OperatingCarrierCode", "cl.carrier_code", "passthrough — ⚠️ constant 'PR'; dead filter"),
    ("is_nonstop", "cl.is_nonstop", "passthrough — 1 nonstop / 0 connecting"),
    ("BookingType", "cl.booking_type", "passthrough — Group / Non-Group"),
    ("Channel", "cl.channel", "passthrough — V1 `Channel Category` (nulls → 'Unknown')"),
    ("Age", "cl.age", "passthrough — 57% NULL by design (international ops only)"),
    ("UniqueID", "cl.customer_id", "passthrough — customer key (anonymised)"),
    ("CountryCodeOfIssue", "cl.issue_country", "passthrough"),
    ("POO", "cl.origin_poo", "passthrough — point of origin (airport)"),
    ("Farebrand", "cl.farebrand", "**derived** — V1 ladder + date-dependent F/G award rule"),
    # ── booking identity (fixes booking counts + the Route double-count) ──────────
    (
        "BookingID",
        "(hash(cl.customer_id || '|' || cl.issue_date::VARCHAR) >> 1)::BIGINT",
        "**added** — surrogate booking key = hash(UniqueID, DateOfIssuance)",
    ),
    (
        "CouponNumber",
        "cl.coupon_number",
        "**added** — leg identity within the booking (Stage C passthrough)",
    ),
    (
        "IsPrimaryCoupon",
        f"(row_number() OVER (PARTITION BY cl.customer_id, cl.issue_date ORDER BY {LEG_ORDER}) = 1)",
        "**added** — exactly one TRUE per booking; filter on it for booking-level measures",
    ),
    ("BookingCoupons", "b.n_coupons", "**added** — legs in this booking (Stage F)"),
    # ── data-completeness guards (stop the trend line lying) ─────────────────────
    ("DataAsOfDate", "DATE '{as_of}'", "**added** — extract boundary: last flown departure"),
    (
        "IsCompleteTravelMonth",
        "(cast(date_trunc('month', cl.departure_date) AS DATE) <= DATE '{last_month}')",
        "**added** — FALSE = still-filling forward book; default every trend visual to TRUE",
    ),
    (
        "IsCompleteTravelYear",
        "(year(cl.departure_date) IN ({years}))",
        "**added** — FALSE for the partial 2024 start and the 2026/2027 forward tail",
    ),
    # ── added dimensions (already computed upstream, previously dropped) ─────────
    (
        "CustomerDominantSegment",
        f"coalesce(c.dominant_segment, '{EXCLUDED}')",
        "added — customer grain",
    ),
    ("DestRegion", "b.dest_region", "**added** — route region (Stage F)"),
    ("RoundTrip", "b.round_trip", "**added** — booking returns to origin (Stage F)"),
    ("IsInternational", "b.is_international", "**added** — Stage F"),
    (
        "TravelMonth",
        "cast(date_trunc('month', cl.departure_date) AS DATE)",
        "added — Travel Month filter",
    ),
    ("IssueMonth", "cast(date_trunc('month', cl.issue_date) AS DATE)", "added — on-hand timing"),
    ("LeadTimeDays", "cl.lead_time_days", "added — departure − issuance; **use this for pickup**"),
    ("Route", "coalesce(cl.online_od, cl.trip_od, cl.sector)", "added — resolved per your rule"),
    ("NLegs", "cl.n_legs", "**added** — legs on the ticketed journey"),
    ("IsConnecting", "cl.is_connecting", "**added** — complement of is_nonstop"),
    ("IsFlown", "cl.flown", "**added** — boolean form of CurrentCouponStatus"),
    (
        "FarebrandValueTier",
        "cl.value_tier",
        "added — 7 Business Flex … 1 Supersaver; NULL = award/group/non-rev",
    ),
    # ── exclusion flags for clean commercial measures ────────────────────────────
    ("IsRefund", "cl.is_refund", "added — negative money; exclude or net out in measures"),
    ("RevMissing", "cl.rev_missing", "**added** — revenue null or zero"),
    ("IsAward", "cl.is_award", "**added** — Mabuhay award redemption; exclude from revenue"),
    ("IsNonRev", "cl.is_nonrev", "**added** — staff/industry/comp; exclude from revenue"),
    ("IsGroupFare", "cl.is_group_fare", "**added** — group-fare inventory"),
    ("AgeKnown", "cl.age_known", "**added** — filter age visuals on this instead of null-handling"),
    (
        "IsReissue",
        "(cl.lead_time_days < 0)",
        "**added** — issued after departure; negative lead time",
    ),
]

# Flight-level agg: drop the per-passenger identifiers and the measures.
AGG_DROP = {
    "UniqueID",
    "Age",
    "PaxCount",
    "NetRevenue",
    "NetFare",
    "CustomerDominantSegment",
    "BookingID",
    "CouponNumber",
    "IsPrimaryCoupon",
    "BookingCoupons",
    "AgeKnown",
}

# Headline dashboard grain — no flight number, no day-level dates, no high-cardinality TripOD.
DASH_KEYS = [
    "CustomerSegment",
    "TravelMonth",
    "DestRegion",
    "Route",
    "OperatingCabinClass",
    "Channel",
    "Farebrand",
    "BookingType",
    "is_nonstop",
    "CurrentCouponStatus",
    "IsCompleteTravelMonth",
    "IsCompleteTravelYear",
    "RoundTrip",
    "IsInternational",
    "IsRefund",
    "IsAward",
    "IsNonRev",
]


def connect() -> duckdb.DuckDBPyConnection:
    TMP.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("PRAGMA threads=6")
    con.execute("SET memory_limit='8GB'")
    con.execute("SET preserve_insertion_order=false")
    con.execute(f"SET temp_directory='{TMP}'")
    con.execute(f"CREATE VIEW clean AS SELECT * FROM read_parquet('{CLEAN}/**/*.parquet')")
    con.execute(
        f"CREATE VIEW bk AS SELECT customer_id, issue_date, proxy_segment, dest_region, "
        f"round_trip, is_international, n_coupons FROM read_parquet('{BOOKING}')"
    )
    con.execute(
        f"CREATE VIEW cust AS SELECT customer_id, dominant_segment FROM read_parquet('{CUSTOMER}')"
    )
    return con


def calendar_bounds(con: duckdb.DuckDBPyConnection) -> tuple[date, date, list[int]]:
    """Extract boundary + which travel months/years are actually settled.

    `as_of`        last flown departure — everything after it is still-filling forward book.
    `last_month`   last fully-settled travel month (the month before as_of's month).
    `years`        travel years fully covered by [first flown departure, last_month].
    """
    as_of, first_dep = con.execute(
        "SELECT max(departure_date)::DATE, min(departure_date)::DATE FROM clean WHERE flown"
    ).fetchone()
    last_month = (as_of.replace(day=1) - timedelta(days=1)).replace(day=1)
    years = [
        y
        for y in range(first_dep.year, last_month.year + 1)
        if date(y, 1, 1) >= first_dep.replace(day=1) and date(y, 12, 1) <= last_month
    ]
    return as_of, last_month, years


def select_sql(as_of: date, last_month: date, years: list[int]) -> str:
    subs = {"as_of": as_of, "last_month": last_month, "years": ", ".join(str(y) for y in years)}
    cols = ",\n            ".join(f'{expr.format(**subs)} AS "{name}"' for name, expr, _ in FIELDS)
    return f"""
        SELECT
            {cols},
            year(cl.departure_date) AS dep_year
        FROM clean cl
        LEFT JOIN bk   b ON cl.customer_id = b.customer_id AND cl.issue_date = b.issue_date
        LEFT JOIN cust c ON cl.customer_id = c.customer_id
    """


def build_coupons(con: duckdb.DuckDBPyConnection, bounds: tuple) -> None:
    if COUPONS.exists():
        shutil.rmtree(COUPONS)
    COUPONS.mkdir(parents=True, exist_ok=True)
    con.execute(f"""
        COPY ({select_sql(*bounds)}) TO '{COUPONS}'
        (FORMAT PARQUET, PARTITION_BY (dep_year), OVERWRITE_OR_IGNORE, COMPRESSION zstd)
    """)
    con.execute(f"CREATE VIEW fact AS SELECT * FROM read_parquet('{COUPONS}/**/*.parquet')")


def _rollup(con: duckdb.DuckDBPyConnection, target: Path, keys: list[str], partition: bool) -> int:
    """Pre-summed rollup.

    `Bookings` is `sum(IsPrimaryCoupon)`, **not** `count(DISTINCT BookingID)`. A pre-aggregated
    distinct count is not re-aggregatable — summing it across groups in Power BI would double-count
    any booking spanning two groups. Counting primary coupons is additive and exact: each booking
    contributes 1 to exactly one group, so the measure sums correctly at every level of the report.
    """
    if partition:
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)
        dest, opts, read = (
            target,
            "PARTITION_BY (dep_year), OVERWRITE_OR_IGNORE, ",
            f"{target}/**/*.parquet",
        )
    else:
        # A non-partitioned COPY writes a single file — the target must not be a directory.
        if target.is_dir():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        dest, opts, read = target, "OVERWRITE_OR_IGNORE, ", str(target)

    quoted = [f'"{k}"' for k in keys]
    extra = ", dep_year" if partition else ""
    con.execute(f"""
        COPY (
            SELECT {", ".join(quoted)},
                   count(*)                                  AS Coupons,
                   sum("IsPrimaryCoupon"::INT)               AS Bookings,
                   sum("PaxCount")                           AS PaxCount,
                   sum("NetRevenue")                         AS NetRevenue,
                   sum("NetFare")                            AS NetFare
                   {extra}
            FROM fact GROUP BY {", ".join(quoted)}{extra}
        ) TO '{dest}'
        (FORMAT PARQUET, {opts}COMPRESSION zstd)
    """)
    return con.execute(f"SELECT count(*) FROM read_parquet('{read}')").fetchone()[0]


def build_agg(con: duckdb.DuckDBPyConnection) -> int:
    """Flight-level rollup — keeps flight number and day-level dates for detail pages."""
    keys = [n for n, _, _ in FIELDS if n not in AGG_DROP]
    return _rollup(con, AGG, keys, partition=True)


def build_agg_dashboard(con: duckdb.DuckDBPyConnection) -> int:
    """Headline grain — what the summary visuals should actually bind to."""
    return _rollup(con, AGG_DASH, DASH_KEYS, partition=False)


def build_dim_date(con: duckdb.DuckDBPyConnection, last_month: date) -> int:
    """Date dimension for DAX time intelligence (YoY, 12-mo trend)."""
    lo, hi = con.execute("""
        SELECT least(min("DateOfIssuance"), min("DepartureDate")),
               greatest(max("DateOfIssuance"), max("DepartureDate")) FROM fact
    """).fetchone()
    lo = date(lo.year, 1, 1)
    hi = date(hi.year, 12, 31)
    con.execute(f"""
        COPY (
            SELECT d::DATE                                        AS "Date",
                   year(d)                                        AS "Year",
                   quarter(d)                                     AS "Quarter",
                   'Q' || quarter(d)                              AS "QuarterName",
                   month(d)                                       AS "MonthNumber",
                   cast(date_trunc('month', d) AS DATE)           AS "MonthStart",
                   strftime(d, '%b')                              AS "MonthName",
                   strftime(d, '%Y-%m')                           AS "YearMonth",
                   dayofmonth(d)                                  AS "DayOfMonth",
                   isodow(d)                                      AS "DayOfWeek",
                   strftime(d, '%a')                              AS "DayName",
                   (isodow(d) >= 6)                               AS "IsWeekend",
                   (cast(date_trunc('month', d) AS DATE) <= DATE '{last_month}')
                                                                  AS "IsCompleteTravelMonth"
            FROM generate_series(DATE '{lo}', DATE '{hi}', INTERVAL 1 DAY) t(d)
        ) TO '{DIM_DATE}' (FORMAT CSV, HEADER)
    """)
    return (hi - lo).days + 1


def dir_mb(p: Path) -> float:
    if p.is_file():
        return round(p.stat().st_size / 1e6, 1)
    return round(sum(f.stat().st_size for f in p.rglob("*.parquet")) / 1e6, 1)


def write_report(con, n_clean, n_fact, n_agg, n_dash, n_dates, bounds) -> None:  # noqa: PLR0913
    as_of, last_month, years = bounds

    seg = con.execute("""
        SELECT "CustomerSegment" AS segment, count(*) AS coupons,
               round(100.0*count(*)/sum(count(*)) OVER (), 2) AS pct,
               count(DISTINCT "BookingID") AS bookings,
               round(sum("NetRevenue"), 0) AS net_revenue,
               round(100.0*sum("NetRevenue")/sum(sum("NetRevenue")) OVER (), 2) AS rev_pct,
               round(avg("NetFare"), 2) AS avg_fare
        FROM fact GROUP BY 1 ORDER BY coupons DESC
    """).fetchdf()

    completeness = con.execute("""
        SELECT "IsCompleteTravelMonth" AS complete_month, count(*) AS coupons,
               round(100.0*count(*)/sum(count(*)) OVER (), 2) AS pct,
               min("TravelMonth") AS first_month, max("TravelMonth") AS last_month,
               round(sum("NetRevenue")/1e6, 1) AS rev_musd
        FROM fact GROUP BY 1 ORDER BY 1 DESC
    """).fetchdf()

    grain = (
        con.execute("""
        SELECT count(*) AS coupons, count(DISTINCT "BookingID") AS bookings,
               sum("IsPrimaryCoupon"::INT) AS primary_coupons,
               round(count(*)::DOUBLE/count(DISTINCT "BookingID"), 2) AS coupons_per_booking
        FROM fact
    """)
        .fetchdf()
        .iloc[0]
    )

    fare = (
        con.execute("""
        SELECT round(median("NetFare"), 2) med_fare, round(median("NetRevenue"), 2) med_rev,
               round(median("NetRevenue" - "NetFare"), 2) med_yq,
               round(100.0*avg(("NetRevenue" >= "NetFare")::INT), 2) pct_rev_ge_fare,
               round(100.0*avg(("NetFare" < 0)::INT), 3) pct_fare_neg
        FROM fact WHERE "NetFare" IS NOT NULL AND "NetRevenue" IS NOT NULL
    """)
        .fetchdf()
        .iloc[0]
    )

    excl = con.execute("""
        SELECT round(100.0*avg("IsRefund"::INT), 3)   AS refund_pct,
               round(100.0*avg("RevMissing"::INT), 3) AS rev_missing_pct,
               round(100.0*avg("IsAward"::INT), 3)    AS award_pct,
               round(100.0*avg("IsNonRev"::INT), 3)   AS nonrev_pct,
               round(100.0*avg("IsGroupFare"::INT), 3) AS group_fare_pct,
               round(100.0*avg("IsReissue"::INT), 3)  AS reissue_pct
        FROM fact
    """).fetchdf()

    fields_tbl = "\n".join(f"| `{n}` | {note} |" for n, _, note in FIELDS)

    lines = [
        "# Power BI export — preliminary segmented fact table\n",
        "## What this is\n",
        "Coupon-grain fact table with the rule-based `CustomerSegment` joined on from booking grain. "
        "`CustomerSegment` is the **preliminary proxy segmentation** — validated against the proxy "
        "rules themselves (circular) until SME labels land. See `docs/methodology.md`.\n",
        "## Outputs\n",
        "| Output | Rows | Size | Use for |",
        "|---|---|---|---|",
        f"| `detail/fact_coupons/` | {n_fact:,} | {dir_mb(COUPONS)} MB | only for Age / UniqueID |",
        f"| `model/fact_flight/` | {n_agg:,} | {dir_mb(AGG)} MB | **full dashboard — load this** |"
        if n_agg
        else "| `model/fact_flight/` | skipped | — | — |",
        f"| `model/fact_dashboard.parquet` | {n_dash:,} | {dir_mb(AGG_DASH)} MB | fast summary visuals |"
        if n_dash
        else "| `model/fact_dashboard.parquet` | skipped | — | — |",
        f"| `model/dim_date.csv` | {n_dates:,} | — | mark as Date table for YoY / 12-mo trend |",
        "| `qa/sample_100k.csv` | 100,000 | — | build + validate DAX first |",
        "| `START-HERE.md` | — | — | **read this first** |",
        "",
        f"**Reconciliation:** cleaned coupons **{n_clean:,}** → exported **{n_fact:,}** "
        f"({'match ✅' if n_clean == n_fact else '**MISMATCH ⚠️**'}). "
        "The join adds no rows and drops none.\n",
        "## ⚠️ Data completeness — read before building any trend visual\n",
        f"The extract has a hard boundary at **{as_of}** (last flown departure). Travel months after "
        f"**{last_month:%B %Y}** are still-filling forward book, not demand: Sep-2026 holds ~22% of a "
        "mature month's coupons purely because those bookings have not been made yet. A 12-month trend "
        "that includes them shows a **fake cliff**.\n",
        "- **Default every trend/YoY visual to `IsCompleteTravelMonth = TRUE`.**",
        f"- **`IsCompleteTravelYear = TRUE` only for {', '.join(str(y) for y in years)}** — 2024 starts "
        "in May (8 months) and 2026/2027 are partial, so an unfiltered full-year YoY compares 12 months "
        "against 8.",
        f"- `DataAsOfDate` carries **{as_of}** on every row so the boundary is visible in the model.\n",
        completeness.to_markdown(index=False),
        "\n## Grain & booking identity\n",
        f"- **{int(grain['coupons']):,}** coupons across **{int(grain['bookings']):,}** bookings "
        f"({grain['coupons_per_booking']} coupons per booking).",
        f"- `IsPrimaryCoupon` is TRUE on exactly **{int(grain['primary_coupons']):,}** rows — one per "
        f"booking ({'✅ matches the booking count — no hash collisions' if grain['primary_coupons'] == grain['bookings'] else '⚠️ MISMATCH'}).",
        "- **Booking-level measures:** filter `IsPrimaryCoupon = TRUE` rather than DISTINCTCOUNT over a "
        "composite key. **Coupon/sector measures:** use all rows.",
        "- `Route` repeats per leg, so counting coupons by `Route` double-counts connecting journeys — "
        "use `BookingID` to dedupe.",
        "- In both aggregates, **`Bookings` = `sum(IsPrimaryCoupon)`, not a distinct count.** A "
        "pre-aggregated DISTINCTCOUNT cannot be re-aggregated — summing it across groups would "
        "double-count bookings that span groups. Counting primary coupons is additive and exact: each "
        "booking contributes 1 to exactly one group, so the measure totals correctly at every level.\n",
        "## Field dictionary\n",
        "| Field | Source |",
        "|---|---|",
        fields_tbl,
        "\n## Segment mix (the model output)\n",
        seg.to_markdown(index=False),
        "\n## `NetFare` vs `NetRevenue` — the fare-basis confirmation you asked for\n",
        f"- Median `NetFare` **{fare['med_fare']}** · median `NetRevenue` **{fare['med_rev']}** · "
        f"median difference (the YQ fuel surcharge) **{fare['med_yq']}**.",
        f"- `NetRevenue >= NetFare` on **{fare['pct_rev_ge_fare']}%** of coupons.",
        "- **Confirmed:** `NetFare` is the base-fare basis (**excludes** the YQ surcharge); "
        "`NetRevenue` = base fare + YQ. Use `NetFare` for **Avg Fare** and `NetRevenue` for revenue "
        "share / YoY — that matches your field mapping.",
        f"- **Caveat:** `NetFare` is negative on **{fare['pct_fare_neg']}%** of coupons (refunds/ADMs).\n",
        "## Exclusion flags — build commercial measures on these\n",
        "A clean revenue measure filters `IsRefund = FALSE AND RevMissing = FALSE AND IsAward = FALSE "
        "AND IsNonRev = FALSE`.\n",
        excl.to_markdown(index=False),
        "\n## Date dimension\n",
        f"`model/dim_date.csv` covers **{n_dates:,}** days. Mark it as the Date table in Power BI. There are "
        "**two date roles** — `DepartureDate` (travel) and `DateOfIssuance` (sales). Model one active "
        "relationship (travel) and reach the other with `USERELATIONSHIP`, or load a second copy as a "
        "sales-date table. `IsCompleteTravelMonth` is repeated here so the filter works from either side.\n",
        "## Known limitations\n",
        "- **⚠️ `DaysBeforeMonthEnd` cannot drive LY-vs-CY pickup.** Verified: across all 37 departure "
        "months it takes exactly **one** distinct value per departure month, even though each month is "
        "sold across 13–15 different issue months. It is a deterministic function of the departure month "
        "against a *single* extract date — constant `-7` through Jun-2026, then stepping by month length. "
        "It carries **zero booking-timing information**. Use **`LeadTimeDays`** for booking-curve pickup "
        "('on hand at ≤N days before departure'), which *is* LY-vs-CY comparable. A true snapshot anchor "
        "needs repeated dated extracts of the same departure months; this is one extract.",
        "- **`PaxCount` is a *sectoral* count** (1 sector = 1 pax) — ≈always 1, **not party size**. "
        "Segment pax = coupon count; for party size use `BookingType = 'Group'`.",
        "- **`OperatingCarrierCode` is constant `PR`** — the PR-operated filter is a no-op on this "
        "extract. Kept because it was requested; interline surfaces as `TripOD` ≠ `OnlineOD`.",
        "- **`Age` is 57% NULL by design** (international operations only) — filter on `AgeKnown`; never "
        "show an unqualified average age, it is not missing at random.",
        "- **Currency is undocumented.** Stage F established only that revenue is *plausibly* "
        "single-currency (7.3× median spread across 26 issue countries). Confirm with PAL before summing "
        "revenue across countries.",
        "- **`is_nonstop`** is the one snake_case column (it was requested that way); everything else is "
        "PascalCase.",
        f"- **`{EXCLUDED}`** rows are coupons whose customer had *every* coupon non-revenue. Kept so "
        "totals tie to the full extract — filter them out of commercial measures.",
        "- **`Unassigned`** is a real model state (no proxy rule matched), mostly PH-issued *outbound* "
        "international economy — a known taxonomy gap raised with PAL, not a data error.",
        "- **`Mabuhay Loyalist` is 0.03% and `Digital Nomad` is absent** — both blocked on the missing "
        "`Loyalty status` field. Do not present them as populated segments.",
        "",
    ]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n")
    print(f"\nWrote {OUT / 'summary.md'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-agg", action="store_true", help="skip both aggregate builds")
    ap.add_argument(
        "--report-only",
        action="store_true",
        help="rebuild summary.md from the existing parquet (no 38M-row rebuild)",
    )
    args = ap.parse_args()

    for d in (OUT, MODEL, DETAIL, QA):
        d.mkdir(parents=True, exist_ok=True)
    con = connect()
    n_clean = con.execute("SELECT count(*) FROM clean").fetchone()[0]

    bounds = calendar_bounds(con)
    as_of, last_month, years = bounds
    print(
        f"Extract boundary: as-of {as_of} · last settled travel month {last_month} · "
        f"complete travel years {years}"
    )

    def count_of(path: Path, glob: bool) -> int | None:
        src = f"{path}/**/*.parquet" if glob else str(path)
        if not path.exists():
            return None
        return con.execute(f"SELECT count(*) FROM read_parquet('{src}')").fetchone()[0]

    if args.report_only:
        con.execute(f"CREATE VIEW fact AS SELECT * FROM read_parquet('{COUPONS}/**/*.parquet')")
        n_fact = con.execute("SELECT count(*) FROM fact").fetchone()[0]
        n_agg, n_dash = count_of(AGG, True), count_of(AGG_DASH, False)
        n_dates = sum(1 for _ in DIM_DATE.open()) - 1
        print(f"Report-only: reusing {n_fact:,} exported coupons")
    else:
        print(f"Joining segments onto {n_clean:,} coupons → {COUPONS} ...")
        build_coupons(con, bounds)
        n_fact = con.execute("SELECT count(*) FROM fact").fetchone()[0]
        print(f"  wrote {n_fact:,} rows ({dir_mb(COUPONS)} MB)")

        n_agg = n_dash = None
        if not args.no_agg:
            print("Building flight-level aggregate ...")
            n_agg = build_agg(con)
            print(f"  wrote {n_agg:,} rows ({dir_mb(AGG)} MB)")
            print("Building dashboard-grain aggregate ...")
            n_dash = build_agg_dashboard(con)
            print(f"  wrote {n_dash:,} rows ({dir_mb(AGG_DASH)} MB)")

        print("Building date dimension ...")
        n_dates = build_dim_date(con, last_month)
        print(f"  wrote {n_dates:,} days")

        print("Writing QA sample ...")
        con.execute(f"""
            COPY (SELECT * EXCLUDE (dep_year) FROM fact USING SAMPLE 100000 ROWS (reservoir, 42))
            TO '{SAMPLE}' (FORMAT CSV, HEADER)
        """)

    # Ship the hand-written starter guide next to the data. Canonical copy lives in docs/
    # (tracked); outputs/ is git-ignored, so it must be re-copied on every build.
    if GUIDE_SRC.exists():
        shutil.copyfile(GUIDE_SRC, GUIDE_OUT)
        print(f"Copied {GUIDE_SRC.name} → {GUIDE_OUT}")

    print("Writing summary ...")
    write_report(con, n_clean, n_fact, n_agg, n_dash, n_dates, bounds)
    con.close()
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    main()
