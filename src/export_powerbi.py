"""Power BI export — the preliminary segmented fact table.

Joins the **booking-grain** segmentation (`proxy_segment` from Stage F) back down onto the
**coupon-grain** cleaned data, so every field the dashboards need is present at its native grain
(`Sector`, `OperatingFlightNumber`, `OperatingCabinClass`, `CurrentCouponStatus`, `is_nonstop` are
coupon attributes; the segment is a property of the booking that owns the coupon).

Outputs — pick per dashboard:

    START-HERE.md                  5-min starter guide (copied from docs/powerbi-guide.md)
    summary.md                     field dictionary, reconciliation, caveats
    model/dim_date.csv             Date dimension for DAX time intelligence
    model/dim_segment.csv          Segment persona dimension — drives the persona-card visuals
    model/scorecard_segment_month.csv  Per-segment scorecard source (segment × travel month)
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
DIM_SEGMENT = MODEL / "dim_segment.csv"
SCORECARD = MODEL / "scorecard_segment_month.csv"
SAMPLE = QA / "sample_100k.csv"
GUIDE_OUT = OUT / "START-HERE.md"
TMP = OUT / ".duckdb_tmp"

EXCLUDED = "Excluded (non-revenue)"

# ── Persona dimension ────────────────────────────────────────────────────────────
# One row per segment, so Power BI can render **persona cards** natively (a card/table visual
# bound to dim_segment, cross-filtered by the same slicers as the fact table) instead of the
# narrative living only in docs/stakeholder-report.md §8.
#
# Two kinds of column, kept deliberately separate — a reader must be able to tell what is measured
# from what is asserted:
#   • QUALITATIVE (here)  — editorial. Motivation, service priorities, caveats. Written by us.
#   • QUANTITATIVE (SQL)  — recomputed from pal_features_booking.parquet on every build, so the
#     cards cannot silently drift from the data the way a hardcoded snapshot would.
#
# `Trust`/`DataCaveat` exist because persona cards are persuasive: a card reading
# "Mabuhay Loyalist — 0.03% of bookings" invites the reader to conclude the loyalty programme is
# irrelevant, when the truth is that we cannot see it. The caveat must travel *with* the card, so it
# ships as a column rather than as a footnote someone can crop out.
#
# (name, sort, tier, penalty, rev_at_risk, persona, headline, why, wants, avoid, trust, caveat)
PERSONA = [
    (
        "Corporate",
        1,
        "Critical",
        10,
        40_000,
        "The Deadline Traveller",
        "Short notice, expensive seat, someone else's booking system.",
        "A meeting with a fixed date. Schedule beats price — the trip cannot move.",
        "Reliability, lounge access, change flexibility, fast rebooking when disrupted.",
        "Do not send promo fares. Do not read a cancelled meeting as churn.",
        "Diluted",
        "No loyalty or company identifier, so 'business cabin + short notice' also catches the "
        "wealthy last-minute leisure traveller. Most likely rule to change after SME review.",
    ),
    (
        "Mabuhay Loyalist",
        2,
        "Critical",
        8,
        32_000,
        "The Miles Spender",
        "Paid in miles, so the cash line is only taxes — revenue is not value here.",
        "Years of accumulated flying, now being spent. Often the trip they saved for.",
        "Award availability on routes they actually want, tier recognition, upgrade paths.",
        "Do not judge this segment by revenue per booking — it is structurally near zero.",
        "Not trustworthy",
        "0.03% of bookings cannot be true. With no loyalty-tier field the only signal is award "
        "redemption. The segment is real; our ability to see it is not. Needs Mabuhay tier data.",
    ),
    (
        "OFW/Migrant",
        3,
        "High",
        5,
        20_000,
        "The Overseas Worker",
        "One-way, bought abroad, economy, often connecting. Relocation, not a holiday.",
        "Work abroad. The trip is a life event planned around a contract, not a calendar.",
        "Generous baggage, agency support in-language, payment options, reliable connections.",
        "Do not optimise on fare alone — baggage and connection reliability likely matter more.",
        "Partly definitional",
        "1.1M of these are Sea Crew, identified by channel with certainty. The open question is "
        "the other 72%, and the boundary against Balikbayan/VFR is a single bit (round trip).",
    ),
    (
        "Premium Bleisure",
        4,
        "Moderate",
        4,
        16_000,
        "The Voluntary Upgrader",
        "Highest revenue per booking of any segment, and they plan ahead.",
        "Blending work and leisure, or simply affluent leisure — they chose to pay up.",
        "Seat comfort, lounge, an experience worth the premium they volunteered.",
        "Do not deprioritise on headcount — 2.1% of bookings, far more of the revenue.",
        "Measured",
        "Premium cabin on an international route with no corporate signal. A clean rule, though "
        "it inherits whatever Corporate fails to catch.",
    ),
    (
        "Pilgrimage",
        5,
        "Moderate",
        3,
        12_000,
        "The Pilgrim",
        "Jeddah or Medina, and almost always connecting — no direct service exists.",
        "Religious obligation. Timing is fixed by the calendar, not by price or convenience.",
        "Group handling, baggage for gifts, connection reliability above all else.",
        "Do not treat a missed connection as a reschedulable inconvenience here.",
        "Measured",
        "The most cleanly defined segment in the taxonomy — destination alone settles it. Also the "
        "smallest, so per-segment rates are volatile.",
    ),
    (
        "Balikbayan/VFR",
        6,
        "Low",
        2,
        8_000,
        "The One Coming Home",
        "Books furthest ahead of anyone, most complex itinerary, always returns.",
        "Coming home to family. Emotional, seasonal, price-aware but not price-driven.",
        "Baggage allowance for pasalubong, family seating, peak-season availability.",
        "Do not assume stable size means stable value — see the caveat.",
        "Watch",
        "Held its passenger share while falling 29.35% → 26.64% of revenue year on year. A segment "
        "holding its size is not evidence its value held. Boundary vs OFW/Migrant is one bit.",
    ),
    (
        "Family",
        7,
        "Low",
        2,
        8_000,
        "The Travelling Party",
        "Ticketed as a group, and books late for a leisure trip.",
        "Travelling together — reunions, holidays, group events.",
        "Seating together, simple group changes, baggage, kid-friendly handling.",
        "Do not read this as a count of families travelling — see the caveat.",
        "Under-counted",
        "This segment means 'ticketed as a group', not 'is a family'. Pax Count is always 1 by "
        "design, so a family of four booking individually is invisible here.",
    ),
    (
        "Last-Minute",
        8,
        "Baseline",
        1,
        4_000,
        "The Sudden Traveller",
        "Booked a day out, domestic, one-way — but they come back often.",
        "Something happened: a family emergency, a sudden work need, a plan that changed.",
        "Availability, a booking flow that works on a phone under stress, easy changes.",
        "Do not treat low value per booking as low lifetime value — repeat rate is high.",
        "Measured",
        "Behavioural rather than demographic: it cuts across the other segments, catching anyone "
        "who books inside 3 days once the higher-priority rules have passed.",
    ),
    (
        "Budget/Adventure",
        9,
        "Baseline",
        1,
        4_000,
        "The Domestic Explorer",
        "The largest segment by far and the cheapest per booking. Where the LCC fight happens.",
        "Leisure within the Philippines. Price-led, flexible on timing.",
        "Price transparency, promos, no surprises at check-in.",
        "Do not dismiss on unit value — collectively this is 4 in 10 bookings.",
        "Measured",
        "The catch-all for domestic non-premium travel, so it absorbs anything the earlier rules "
        "did not claim. Broad by construction.",
    ),
    (
        "Unassigned",
        10,
        "Undefined",
        0,
        0,
        "The Gap In The Taxonomy",
        "Not junk: out-earns OFW/Migrant per booking, and 18.6% fly premium.",
        "Mostly one identifiable group — an ordinary Filipino, ticket issued in PH, flying abroad "
        "in economy — who matches none of the ten rules.",
        "A segment definition from PAL. This is a commercial decision, not a modelling problem.",
        "Do not fold these into the nearest segment to make the chart tidy.",
        "Open ask",
        "The single largest actionable gap in the deliverable. Left deliberately blank rather than "
        "guessed. Needs a PAL definition before it can be acted on.",
    ),
    (
        EXCLUDED,
        11,
        "Not a customer",
        0,
        0,
        "Not A Customer",
        "Staff, industry and complimentary travel — every coupon non-revenue.",
        "Not commercial travel.",
        "Nothing — exclude from all commercial measures.",
        "Do not include in revenue, share or per-passenger measures.",
        "By definition",
        "Present only so Power BI totals reconcile to the full 38.1M-row extract. Filter it out of "
        "every commercial visual.",
    ),
]

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


# Scorecard grain — segment × travel month, plus only the flags a scorecard must filter on.
# Deliberately excludes Route / Cabin / Channel / Farebrand: those explode the row count and belong to
# `fact_dashboard`. This table exists so a per-segment scorecard is a few hundred rows, not 2.1M.
#
# Every flag is coalesced to FALSE below and `RevMissing` is carried explicitly. In the raw fact,
# `IsRefund` and `IsInternational` are NULL on a small number of coupons (167 scorecard rows / ~542
# bookings, all of them revenue-missing). A NULL in a Power BI filter column is a silent data-loss
# trap: `IsRefund = FALSE` evaluates NULL as *not matching*, so those rows vanish from a scorecard
# with nothing visibly wrong and totals that quietly fail to reconcile. Coalescing makes the filter
# behave, and `RevMissing = TRUE` keeps the affected rows identifiable rather than disguised as clean.
SCORECARD_KEYS = [
    "CustomerSegment",
    "TravelMonth",
    "IsInternational",
    "IsCompleteTravelMonth",
    "IsCompleteTravelYear",
    "IsRefund",
    "IsAward",
    "IsNonRev",
    "RevMissing",
]
# Flags that need the NULL→FALSE coalesce (the rest are non-null by construction).
SCORECARD_COALESCE = {"IsInternational", "IsRefund", "IsAward", "IsNonRev", "RevMissing"}


def build_scorecard(con: duckdb.DuckDBPyConnection) -> int:
    """Per-segment scorecard source — small enough to open in Excel, additive at every level.

    CSV rather than Parquet on purpose: it is a few hundred rows, so the BI developer can eyeball it
    and sanity-check totals before wiring a single measure.

    **No percentages, shares or ratios are stored here, and that is deliberate.** A stored
    `share_of_bookings` is correct only for the filter context it was computed in — the moment the
    report slices to one region or one month it silently becomes wrong, and nothing visibly breaks.
    Shares must be DAX measures over these additive columns. Same reason `Bookings` is
    `sum(IsPrimaryCoupon)` rather than a stored distinct count: everything in this table sums.
    """

    def _expr(k: str) -> str:
        return f'coalesce("{k}", FALSE)' if k in SCORECARD_COALESCE else f'"{k}"'

    # GROUP BY takes the bare expressions; SELECT aliases them back to the original column names.
    sel = [f'{_expr(k)} AS "{k}"' for k in SCORECARD_KEYS]
    grp = [_expr(k) for k in SCORECARD_KEYS]
    con.execute(f"""
        COPY (
            SELECT {", ".join(sel)},
                   count(*)                             AS Coupons,
                   sum("IsPrimaryCoupon"::INT)          AS Bookings,
                   coalesce(sum("PaxCount"), 0)         AS PaxCount,
                   round(coalesce(sum("NetRevenue"), 0), 2) AS NetRevenue,
                   round(coalesce(sum("NetFare"), 0), 2)    AS NetFare
            FROM fact
            GROUP BY {", ".join(grp)}
            ORDER BY 1, 2
        ) TO '{SCORECARD}' (FORMAT CSV, HEADER)
    """)
    n = sum(1 for _ in SCORECARD.open()) - 1
    # A scorecard that does not reconcile to the fact table is worse than no scorecard — assert it here
    # rather than letting the BI developer discover it against a 38M-row table.
    tot = con.execute(f"""
        SELECT sum(Coupons), sum(Bookings) FROM read_csv_auto('{SCORECARD}')
    """).fetchone()
    ref = con.execute('SELECT count(*), sum("IsPrimaryCoupon"::INT) FROM fact').fetchone()
    if tuple(tot) != tuple(ref):
        raise AssertionError(f"scorecard does not reconcile: {tot} vs fact {ref}")
    return n


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


def _sql_str(s: str) -> str:
    """Quote a Python str as a SQL literal. Persona text is ours, but apostrophes are inevitable."""
    return "'" + s.replace("'", "''") + "'"


def build_dim_segment(con: duckdb.DuckDBPyConnection) -> int:
    """Segment persona dimension — editorial fields joined to freshly-measured behaviour.

    One row per segment. Joins to the fact tables on `CustomerSegment` = `Segment`, so a card visual
    bound here cross-filters with every other visual on the page.

    The behavioural columns are **recomputed from the booking table on every build** rather than
    hardcoded, so a card claiming "books 48 days ahead" cannot outlive the number that justified it.
    Revenue columns carry no currency symbol: the extract's revenue unit is undocumented (plausibly
    single-currency, magnitudes look like USD), so ratios are safe and absolutes are not.
    """
    from pal_colors import SEG_COLORS  # noqa: PLC0415 — optional dep of this stage only

    rows = ",\n".join(
        "("
        + ", ".join(
            [
                _sql_str(name),
                str(sort),
                _sql_str(tier),
                str(pen),
                str(risk),
                _sql_str(SEG_COLORS.get(name, "#4B5563")),
                _sql_str(persona),
                _sql_str(head),
                _sql_str(why),
                _sql_str(wants),
                _sql_str(avoid),
                _sql_str(trust),
                _sql_str(caveat),
            ]
        )
        + ")"
        for (
            name,
            sort,
            tier,
            pen,
            risk,
            persona,
            head,
            why,
            wants,
            avoid,
            trust,
            caveat,
        ) in PERSONA
    )
    # Behaviour is measured at BOOKING grain — the purpose unit. Measuring lead time or round-trip
    # share at coupon grain would weight every booking by its leg count and quietly favour
    # multi-coupon segments (Balikbayan/VFR averages 2.61 coupons against Last-Minute's 1.32).
    con.execute(f"""
        CREATE OR REPLACE TEMP VIEW seg_stats AS
        WITH b AS (SELECT * FROM read_parquet('{BOOKING}')),
        agg AS (
            SELECT proxy_segment                              AS seg,
                   count(*)                                   AS bookings,
                   round(100.0*count(*)/sum(count(*)) OVER (), 2) AS share_pct,
                   round(median(lead_days))::INT              AS med_lead,
                   round(100*avg(round_trip::INT), 1)         AS rt_pct,
                   round(100*avg(is_international::INT), 1)   AS intl_pct,
                   round(100*avg(any_premium::INT), 1)        AS prem_pct,
                   round(100*avg(connecting::INT), 1)         AS conn_pct,
                   round(100*avg(is_group::INT), 1)           AS group_pct,
                   round(median(rev_pos))::INT                AS med_rev,
                   round(avg(rev_pos))::INT                   AS avg_rev,
                   round(avg(n_coupons), 2)                   AS avg_coupons,
                   mode(channel)                              AS modal_channel,
                   mode(issue_country)                        AS modal_country
            FROM b GROUP BY 1
        ),
        reg AS (  -- top three destination regions, as one display string per segment
            SELECT seg, string_agg(label, ' · ' ORDER BY rk) AS top_regions FROM (
                SELECT proxy_segment AS seg,
                       coalesce(dest_region, 'Domestic') || ' '
                         || round(100.0*count(*)/sum(count(*)) OVER (PARTITION BY proxy_segment), 0)
                         || '%' AS label,
                       row_number() OVER (PARTITION BY proxy_segment ORDER BY count(*) DESC) AS rk
                FROM b GROUP BY proxy_segment, coalesce(dest_region, 'Domestic')
            ) WHERE rk <= 3 GROUP BY seg
        )
        SELECT agg.*, reg.top_regions FROM agg LEFT JOIN reg USING (seg)
    """)
    con.execute(f"""
        COPY (
            SELECT
                p.seg                     AS "Segment",
                p.sort                    AS "SegmentSortOrder",
                p.tier                    AS "PriorityTier",
                p.pen                     AS "PenaltyWeight",
                p.risk                    AS "RevenueAtRiskPerError",
                p.color                   AS "SegmentColorHex",
                (p.pen > 0)               AS "IsModelledSegment",
                p.persona                 AS "PersonaName",
                p.headline                AS "PersonaHeadline",
                p.why                     AS "WhyTheyFly",
                p.wants                   AS "WhatTheyWant",
                p.avoid                   AS "WhatNotToDo",
                p.trust                   AS "Trust",
                p.caveat                  AS "DataCaveat",
                -- Every measured column is prefixed `Profile` on purpose. These are **whole-population,
                -- whole-period** values baked in at build time: they do NOT respond to report slicers,
                -- unlike the additive measures over `scorecard_segment_month`. Without the prefix,
                -- `Bookings` would exist in both tables — one static, one filter-aware — and a card
                -- mixing them would show a filtered booking count beside an unfiltered lead time with
                -- no visual cue that only half the card reacted to the slicer.
                s.bookings                AS "ProfileBookings",
                s.share_pct               AS "ProfileBookingSharePct",
                s.med_lead                AS "ProfileMedianLeadDays",
                s.rt_pct                  AS "ProfileRoundTripPct",
                s.intl_pct                AS "ProfileInternationalPct",
                s.prem_pct                AS "ProfilePremiumCabinPct",
                s.conn_pct                AS "ProfileConnectingPct",
                s.group_pct               AS "ProfileGroupBookingPct",
                s.med_rev                 AS "ProfileMedianRevenuePerBooking",
                s.avg_rev                 AS "ProfileAvgRevenuePerBooking",
                s.avg_coupons             AS "ProfileAvgCouponsPerBooking",
                s.top_regions             AS "ProfileTopDestinationRegions",
                s.modal_channel           AS "ProfileModalChannel",
                s.modal_country           AS "ProfileModalIssueCountry",
                -- Renders on the card as a caption, so a reader can never mistake the profile block
                -- for something the slicer filtered.
                'All bookings, all periods — not filtered by report slicers' AS "ProfileScope"
            FROM (VALUES\n{rows}
            ) AS p(seg, sort, tier, pen, risk, color, persona, headline, why, wants, avoid,
                   trust, caveat)
            LEFT JOIN seg_stats s ON s.seg = p.seg
            ORDER BY p.sort
        ) TO '{DIM_SEGMENT}' (FORMAT CSV, HEADER)
    """)
    return len(PERSONA)


def dir_mb(p: Path) -> float:
    if p.is_file():
        return round(p.stat().st_size / 1e6, 1)
    return round(sum(f.stat().st_size for f in p.rglob("*.parquet")) / 1e6, 1)


def _csv_rows(p: Path) -> int:
    """Data-row count of a written CSV (header excluded); 0 if it was skipped."""
    return (sum(1 for _ in p.open()) - 1) if p.exists() else 0


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
        f"| `model/dim_segment.csv` | {len(PERSONA)} | — | **persona cards** + segment colours, "
        "penalty weights, caveats |",
        f"| `model/scorecard_segment_month.csv` | {_csv_rows(SCORECARD):,} | — | "
        "**per-segment scorecards** — segment × travel month, additive |",
        "| `qa/sample_100k.csv` | 100,000 | — | build + validate DAX first |",
        "| `START-HERE.md` | — | — | **read this first** |",
        "",
        "## Per-segment scorecards — `model/scorecard_segment_month.csv`\n",
        "Built for exactly this job. Grain is **segment × travel month**, plus only the flags a "
        "scorecard has to filter on (`IsInternational`, the two completeness flags, and the "
        "`IsRefund` / `IsAward` / `IsNonRev` exclusions). A few hundred rows, so you can open it in "
        "Excel and check totals before writing a single measure. Relate "
        "`scorecard_segment_month[CustomerSegment]` → `dim_segment[Segment]` and "
        "`[TravelMonth]` → `dim_date[Date]`.\n",
        "**Every numeric column is additive: `Coupons`, `Bookings`, `PaxCount`, `NetRevenue`, "
        "`NetFare`.** Sum them at any level and the answer is right.\n",
        "**⚠️ There are no percentages, shares or ratios in this file, and that is deliberate — do not "
        "add any.** A stored share is only correct for the filter context it was computed in; the "
        "moment the report slices to one region or one month it is silently wrong and nothing visibly "
        "breaks. Write them as measures instead:\n",
        "```dax\nBookings = SUM ( scorecard_segment_month[Bookings] )\n"
        "Net Revenue = SUM ( scorecard_segment_month[NetRevenue] )\n"
        "Rev per Booking = DIVIDE ( [Net Revenue], [Bookings] )\n"
        "Segment Share of Bookings =\n"
        "    DIVIDE ( [Bookings], CALCULATE ( [Bookings], REMOVEFILTERS ( dim_segment ) ) )\n"
        "Bookings LY = CALCULATE ( [Bookings], SAMEPERIODLASTYEAR ( dim_date[Date] ) )\n```\n",
        "**Three things that will otherwise produce a wrong scorecard:**\n",
        "1. **`Bookings` is `sum(IsPrimaryCoupon)`, not a distinct count** — so it stays additive. Never "
        "replace it with `DISTINCTCOUNT`.",
        "2. **Filter `IsCompleteTravelMonth = TRUE` on every trend and YoY tile.** Travel months past "
        "the extract boundary are still-filling forward book, not demand — an unfiltered trend draws a "
        "**fake cliff**. For full-year comparisons use `IsCompleteTravelYear`.",
        "3. **Exclude `IsRefund` / `IsNonRev` / `RevMissing` from commercial tiles** (and usually "
        "`IsAward`, whose revenue is taxes only). They ship as flags rather than being pre-filtered so "
        "your totals can still reconcile to the full extract. **Every flag in this file is guaranteed "
        "non-NULL** — they are coalesced to FALSE on write, because a NULL would make `IsRefund = FALSE` "
        "silently drop those rows and quietly break reconciliation. The ~542 bookings whose refund "
        "status is genuinely unknown are all `RevMissing = TRUE`, so they stay identifiable.\n",
        "This file is **asserted to reconcile to the fact table on every build** — coupons and bookings "
        "must match exactly or the export fails. Verified this run.\n",
        "**There is no model-accuracy or recall KPI in this export, on purpose.** Per-segment recall "
        "needs SME ground-truth labels, which have not landed yet; every accuracy figure computable "
        "today is measured against the rules that produced the labels, i.e. circular. `dim_segment` "
        "carries `PenaltyWeight` and `RevenueAtRiskPerError` if you want to build a *cost-weighted risk* "
        "tile, but **do not build an accuracy gauge** — there is no honest number to put in it.\n",
        "## Persona cards — `model/dim_segment.csv`\n",
        "One row per segment, joined on `Segment` = `CustomerSegment`. **Step-by-step build recipe for "
        "the cards — which visual, which fields, in what order — is in `START-HERE.md` §3b.**\n",
        "⚠️ **The `Profile*` columns are whole-population and whole-period: they do NOT respond to report "
        "slicers.** Live, filter-aware numbers come from measures over `scorecard_segment_month` instead. "
        "Never put the two side by side unlabelled — a card showing a filtered `[Bookings]` next to an "
        "unfiltered `ProfileMedianLeadDays` gives the reader no cue that only half of it moved when they "
        "sliced. Every row carries a `ProfileScope` caption for exactly this purpose, and the `Profile` "
        "prefix also keeps `Bookings` meaning one unambiguous thing in the model.\n",
        "Three kinds of column, and the distinction matters when someone asks *how do you know*:\n",
        "- **Measured** (`Profile` prefix: `ProfileMedianLeadDays`, `ProfileRoundTripPct`, "
        "`ProfileInternationalPct`, `ProfilePremiumCabinPct`, `ProfileConnectingPct`, "
        "`ProfileGroupBookingPct`, `ProfileMedian`/`ProfileAvgRevenuePerBooking`, "
        "`ProfileAvgCouponsPerBooking`, `ProfileTopDestinationRegions`, `ProfileModalChannel`, "
        "`ProfileModalIssueCountry`, `ProfileBookings`, `ProfileBookingSharePct`) "
        "— recomputed from the booking table on every build, at **booking grain** so multi-coupon "
        "segments are not over-weighted.",
        "- **Editorial** (`PersonaName`, `PersonaHeadline`, `WhyTheyFly`, `WhatTheyWant`, "
        "`WhatNotToDo`) — written by the project team. Motivation cannot be measured from a booking "
        "extract; these are informed inference and must not be presented as findings.\n",
        "**`Trust` and `DataCaveat` are not optional decoration — put them on the card.** Persona "
        "cards persuade, so a card reading *Mabuhay Loyalist · 0.03% of bookings* invites the "
        "conclusion that the loyalty programme is irrelevant, when the truth is that we cannot see "
        "it (no loyalty-tier field; award redemption is the only signal). Same for `Family`, which "
        "means *ticketed as a group*, not *is a family*.\n",
        "`SegmentColorHex` carries the project palette (`src/pal_colors.py`) so Power BI, the "
        "Python figures and the slide deck all colour a segment identically. `PenaltyWeight` and "
        "`RevenueAtRiskPerError` are **PAL's own estimates** from the requirements document, in "
        "pesos — unlike the extract's revenue columns, whose unit is undocumented.\n",
        "Filter `IsModelledSegment = FALSE` out of commercial visuals — it flags `Unassigned` (a "
        "real gap awaiting a PAL definition) and `Excluded (non-revenue)` (staff/industry travel, "
        "present only so totals reconcile).\n",
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
        # Cheap and behaviour-only — rebuild both even in --report-only so neither the personas nor
        # the scorecard can go stale relative to a summary that describes them.
        build_dim_segment(con)
        build_scorecard(con)
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

        print("Building segment persona dimension ...")
        n_seg = build_dim_segment(con)
        print(f"  wrote {n_seg} segment rows → {DIM_SEGMENT.name}")

        print("Building per-segment scorecard ...")
        n_score = build_scorecard(con)
        print(f"  wrote {n_score:,} rows → {SCORECARD.name}")

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
