"""Stage F — feature engineering on the real PAL data.

Aggregates `data/interim/pal_clean/` (coupon grain) up to **booking** grain
(`customer_id`, `issue_date` — the purpose unit, per `docs/real-data-plan.md` §1), joins the
airport→region reference, excludes all-non-revenue customers, engineers the four feature families
+ loyalty, applies a prioritized **proxy-label waterfall**, and rolls up to **customer** grain.

Outputs (all git-ignored under data/interim + outputs):
    data/interim/pal_features_booking.parquet    one row per booking (+ proxy_segment)
    data/interim/pal_features_customer.parquet   one row per customer (rollup + dominant_segment)
    outputs/features_real/summary.md             feature + proxy-label profile

Stages (functions below): guards() · build_booking() · add_customer() · profile().
Clustering (sampling / HDBSCAN / inductive labelling) is the next stage, not here.

Run:
    python src/features_real.py
"""

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "interim" / "pal_clean"
AIRPORTS = ROOT / "data" / "reference" / "airport_region.csv"
BOOKING_OUT = ROOT / "data" / "interim" / "pal_features_booking.parquet"
CUSTOMER_OUT = ROOT / "data" / "interim" / "pal_features_customer.parquet"
REPORT = ROOT / "outputs" / "features_real"
TMP = Path("/Users/joshbinaday/.claude/jobs/e24f9c28/tmp")

# Corporate-managed channels. NDC is a distribution *tech standard*, not a corporate signal
# (review 2026-07-23), so it is excluded; TMC (travel-management co.) + the corporate self-booking
# portal are the real corporate cues.
CORP_CHANNELS = ("TMC", "Corporate Web Portal")
PILGRIMAGE_DEST = ("JED", "MED")  # Jeddah / Medina — Hajj/Umrah


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("PRAGMA threads=6")
    con.execute("SET memory_limit='8GB'")
    con.execute("SET preserve_insertion_order=false")
    if TMP.exists():
        con.execute(f"SET temp_directory='{TMP}'")
    con.execute(f"CREATE VIEW clean AS SELECT * FROM read_parquet('{CLEAN}/**/*.parquet')")
    con.execute(f"CREATE TABLE ref AS SELECT * FROM read_csv_auto('{AIRPORTS}')")
    return con


def guards(con: duckdb.DuckDBPyConnection) -> list[str]:
    """Cheap correctness checks flagged to PAL (currency, UniqueID persistence)."""
    notes = []
    # UniqueID persistence: a real customer key should recur across source files/years.
    xf = con.execute("""
        SELECT round(100*avg((nf > 1)::INT), 2) pct_multi_file
        FROM (SELECT customer_id, count(DISTINCT src_file) nf FROM clean GROUP BY 1)
    """).fetchone()[0]
    ok_id = xf > 1.0
    notes.append(
        f"- **UniqueID persistence:** {xf}% of customers appear in >1 source file → "
        + (
            "consistent across files (customer rollup valid)."
            if ok_id
            else "**WARNING: ids may be per-file — customer rollup unreliable.**"
        )
    )
    # Currency sanity: median revenue shouldn't swing wildly across issue countries.
    cur = (
        con.execute("""
        WITH m AS (
            SELECT issue_country, median(revenue) med, count(*) n
            FROM clean WHERE revenue > 0 GROUP BY 1 HAVING count(*) > 50000
        )
        SELECT round(max(med)/nullif(min(med),0), 1) spread, count(*) n_countries FROM m
    """)
        .fetchdf()
        .iloc[0]
    )
    ok_cur = cur["spread"] is not None and cur["spread"] < 20
    notes.append(
        f"- **Currency sanity:** median-revenue spread across major issue countries = "
        f"{cur['spread']}× ({int(cur['n_countries'])} countries) → "
        + (
            "plausibly single-currency."
            if ok_cur
            else "**WARNING: wide spread — possible mixed/unconverted currency.**"
        )
    )
    return notes


def build_booking(con: duckdb.DuckDBPyConnection) -> None:
    """coupon → booking, join route ref, exclude all-non-rev customers, engineer + proxy-label."""
    # customers to exclude: every coupon non-revenue (settled 2026-07-23)
    con.execute("""
        CREATE TABLE excluded AS
        SELECT customer_id FROM clean GROUP BY 1 HAVING bool_and(is_nonrev)
    """)

    # coupon-level route enrichment
    con.execute("""
        CREATE VIEW coup AS
        SELECT c.*,
               (o.is_domestic = 1 AND d.is_domestic = 1)                    AS dom_coupon,
               CASE WHEN d.is_domestic = 0 THEN d.region
                    WHEN o.is_domestic = 0 THEN o.region END                AS intl_region,
               (c.sector_dest IN ('JED','MED') OR c.trip_dest IN ('JED','MED')) AS pilgrimage_dest
        FROM clean c
        LEFT JOIN ref o ON c.sector_origin = o.airport
        LEFT JOIN ref d ON c.sector_dest   = d.airport
        WHERE c.customer_id NOT IN (SELECT customer_id FROM excluded)
    """)

    # booking aggregation. NB: dominant channel/region/country use max() not mode() — a booking
    # averages 1.66 coupons so the value is ~always constant, and mode() spilled catastrophically
    # (34 GB) over 22.9M groups; max() is equivalent here and cheap.
    con.execute("""
        CREATE TABLE bk AS
        SELECT
            customer_id, issue_date,
            count(*)                                   AS n_coupons,
            count(DISTINCT trip_od)                    AS n_directions,
            arg_min(trip_origin, departure_dt)         AS origin_first,
            arg_max(trip_dest,   departure_dt)         AS dest_last,
            (arg_min(trip_origin, departure_dt) = arg_max(trip_dest, departure_dt)) AS round_trip,
            greatest(min(lead_time_days), 0)           AS lead_days,
            max((NOT dom_coupon)::INT) = 1             AS is_international,
            bool_and(dom_coupon)                       AS is_domestic,
            max(intl_region)                           AS dest_region,
            max(pilgrimage_dest::INT) = 1              AS pilgrimage,
            max(value_tier)                            AS max_tier,
            min(value_tier)                            AS min_tier,
            max((cabin IN ('J','W'))::INT) = 1         AS any_premium,
            max((value_tier >= 6)::INT) = 1            AS any_business,
            max(is_award::INT) = 1                     AS is_award,
            max((is_group_booking OR is_group_fare)::INT) = 1 AS is_group,
            max(foreign_issue::INT) = 1                AS foreign_issue,
            max(issue_country)                         AS issue_country,
            max(channel)                               AS channel,
            max((channel IN ('TMC','Corporate Web Portal'))::INT) = 1 AS corp_channel,
            max((channel = 'Sea Crew')::INT) = 1       AS sea_crew,
            max(is_connecting::INT) = 1                AS connecting,
            sum(CASE WHEN NOT is_refund AND revenue > 0 THEN revenue ELSE 0 END) AS rev_pos,
            max(is_refund::INT) = 1                    AS refund_any,
            max(flown::INT) = 1                        AS flown_any,
            max(age)                                   AS age,
            max(age_known::INT) = 1                    AS age_known,
            month(arg_min(departure_date, departure_dt)) AS dep_month
        FROM coup GROUP BY customer_id, issue_date
    """)

    # prioritized proxy-label waterfall (first match wins) — seeds, not final labels
    con.execute("""
        CREATE TABLE booking AS
        SELECT *,
            (dep_month IN (4, 5, 12)) AS peak_month,
            -- refined 2026-07-23: Corporate broadened (corp channel OR business+short-lead),
            -- Budget broadened to domestic-non-premium. Outbound PH-issued intl economy is a known
            -- taxonomy gap (#4) → intentionally left Unassigned, flagged to PAL.
            CASE
                WHEN is_award                                              THEN 'Mabuhay Loyalist'
                WHEN corp_channel OR (any_business AND lead_days <= 7)      THEN 'Corporate'
                WHEN pilgrimage                                            THEN 'Pilgrimage'
                WHEN sea_crew                                              THEN 'OFW/Migrant'
                WHEN foreign_issue AND is_international AND max_tier <= 4
                     AND NOT round_trip                                    THEN 'OFW/Migrant'
                WHEN foreign_issue AND is_international AND max_tier <= 4
                     AND round_trip                                       THEN 'Balikbayan/VFR'
                WHEN any_premium AND is_international                       THEN 'Premium Bleisure'
                WHEN is_group                                              THEN 'Family'
                WHEN lead_days <= 3                                        THEN 'Last-Minute'
                WHEN is_domestic AND NOT any_premium                       THEN 'Budget/Adventure'
                ELSE 'Unassigned'
            END AS proxy_segment
        FROM bk
    """)
    con.execute(f"COPY booking TO '{BOOKING_OUT}' (FORMAT PARQUET, COMPRESSION zstd)")


def add_customer(con: duckdb.DuckDBPyConnection) -> None:
    """booking → customer rollup (frequency, tenure, value, loyalty, dominant segment)."""
    con.execute("""
        CREATE TABLE customer AS
        WITH ranked AS (  -- dominant (most frequent, then most valuable) segment per customer
            SELECT customer_id, proxy_segment,
                   count(*) n_seg, sum(rev_pos) seg_rev,
                   row_number() OVER (PARTITION BY customer_id
                                      ORDER BY count(*) DESC, sum(rev_pos) DESC) rk
            FROM booking GROUP BY customer_id, proxy_segment
        ),
        agg AS (
            SELECT
                customer_id,
                count(*)                                AS n_bookings,
                sum(n_coupons)                          AS n_coupons,
                date_diff('day', min(issue_date), max(issue_date)) AS tenure_days,
                max(issue_date)                         AS last_issue,
                sum(rev_pos)                            AS total_rev,
                round(avg(rev_pos), 2)                  AS mean_rev_per_booking,
                round(100*avg(is_international::INT), 1) AS pct_international,
                round(100*avg(round_trip::INT), 1)      AS pct_round_trip,
                round(100*avg(any_premium::INT), 1)     AS pct_premium,
                max(is_award::INT) = 1                  AS ever_award,
                max(any_business::INT) = 1              AS ever_business,
                max(dest_region)                        AS top_region,
                count(DISTINCT proxy_segment)           AS segment_diversity
            FROM booking GROUP BY customer_id
        )
        SELECT a.*, r.proxy_segment AS dominant_segment
        FROM agg a
        LEFT JOIN (SELECT customer_id, proxy_segment FROM ranked WHERE rk = 1) r
               USING (customer_id)
    """)
    con.execute(f"COPY customer TO '{CUSTOMER_OUT}' (FORMAT PARQUET, COMPRESSION zstd)")


def profile(con: duckdb.DuckDBPyConnection, guard_notes: list[str]) -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    n_excl = con.execute("SELECT count(*) FROM excluded").fetchone()[0]
    n_bk = con.execute("SELECT count(*) FROM booking").fetchone()[0]
    n_cust = con.execute("SELECT count(*) FROM customer").fetchone()[0]

    seg_bk = con.execute("""
        SELECT proxy_segment, count(*) bookings,
               round(100.0*count(*)/sum(count(*)) OVER (), 2) pct,
               round(avg(rev_pos), 0) avg_rev
        FROM booking GROUP BY 1 ORDER BY bookings DESC
    """).fetchdf()
    seg_cust = con.execute("""
        SELECT dominant_segment, count(*) customers,
               round(100.0*count(*)/sum(count(*)) OVER (), 2) pct
        FROM customer GROUP BY 1 ORDER BY customers DESC
    """).fetchdf()
    route = con.execute("""
        SELECT coalesce(dest_region, 'Philippines (domestic)') region,
               count(*) bookings, round(100.0*count(*)/sum(count(*)) OVER (), 2) pct
        FROM booking GROUP BY 1 ORDER BY bookings DESC
    """).fetchdf()

    lines = [
        "# Stage F — feature + proxy-label profile\n",
        f"- Excluded all-non-revenue customers: **{n_excl:,}**",
        f"- Booking feature rows: **{n_bk:,}**  ·  Customer feature rows: **{n_cust:,}**\n",
        "## Data guards\n",
        *guard_notes,
        "\n## Proxy segment — bookings\n",
        seg_bk.to_markdown(index=False),
        "\n## Dominant segment — customers\n",
        seg_cust.to_markdown(index=False),
        "\n## Route region — bookings\n",
        route.to_markdown(index=False),
        "",
    ]
    (REPORT / "summary.md").write_text("\n".join(lines) + "\n")
    print(f"\nbookings={n_bk:,}  customers={n_cust:,}  excluded={n_excl:,}")
    print(f"Wrote {REPORT / 'summary.md'}, {BOOKING_OUT.name}, {CUSTOMER_OUT.name}")


def main() -> None:
    con = connect()
    print("Guards ...")
    guard_notes = guards(con)
    for n in guard_notes:
        print("  " + n)
    print("Building booking features ...")
    build_booking(con)
    print("Building customer rollup ...")
    add_customer(con)
    print("Profiling ...")
    profile(con, guard_notes)


if __name__ == "__main__":
    main()
