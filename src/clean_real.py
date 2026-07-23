"""Stage C — clean the real PAL coupon data → `data/interim/pal_clean/`.

Reads the typed Parquet (`data/interim/pal_parquet/`, ~38M coupon rows) and writes a cleaned,
flagged coupon-level Parquet (partitioned by `iss_year`) plus a data-quality report. Stays at
**coupon grain** — aggregation to booking/customer grain happens in Stage F (feature engineering).

Applies the plan in `docs/real-data-plan.md` §2, grounded in the authoritative V1 dictionary
(`docs/data-dictionary.md`):

  • dedup           — exact duplicates verified ~0 on the natural coupon key → not applied
  • flown/open      — `CurrentCouponStatus` F=flown / O=open  → `flown` flag
  • farebrand       — booking class → farebrand + ordinal `value_tier` (V1 Farebrand_relationship)
  • Mabuhay rule    — date-dependent F/G: `is_award`, `is_group_fare`, `is_nonrev` (flip at 2026-04-01)
  • money           — `rev_missing` (null/zero), `is_refund` (negative) flags; raw kept (winsorize in FE)
  • drops           — `OperatingCarrierCode` (constant), `DaysBeforeMonthEnd` (accounting snapshot);
                      quarantine junk `SoldOperatingCabinClass`
  • missingness     — `age_known` flag; cabin/channel nulls → 'Unknown'
  • parse routes    — `n_legs`, trip/sector origin+dest from the compound path fields
  • derive          — `lead_time_days` (departure − issuance), `foreign_issue`

Run:
    python src/clean_real.py     → data/interim/pal_clean/ + outputs/clean_report/summary.md
"""

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
PARQUET = ROOT / "data" / "interim" / "pal_parquet"
OUT_DIR = ROOT / "data" / "interim" / "pal_clean"
REPORT = ROOT / "outputs" / "clean_report"

APR2026 = "DATE '2026-04-01'"

# V1 Farebrand_relationship → ordinal paid-value tier (7 high … 1 low; NULL = special, see flags).
# F and G are handled separately below (date-dependent), so they are NOT in this static map.
FAREBRAND_ROWS = [
    ("J", "Business Flex", 7),
    ("C", "Business Flex", 7),
    ("D", "Business Flex", 7),
    ("I", "Business Value", 6),
    ("Z", "Business Value", 6),
    ("W", "Premium Economy", 5),
    ("N", "Premium Economy", 5),
    ("Y", "Economy Flex", 4),
    ("S", "Economy Flex", 4),
    ("L", "Economy Flex", 4),
    ("M", "Economy Flex", 4),
    ("H", "Economy Flex", 4),
    ("Q", "Economy Value", 3),
    ("V", "Economy Value", 3),
    ("B", "Economy Value", 3),
    ("X", "Economy Value", 3),
    ("K", "Economy Saver", 2),
    ("E", "Economy Saver", 2),
    ("T", "Economy Saver", 2),
    ("U", "Economy Supersaver", 1),
    ("O", "Economy Supersaver", 1),
    ("A", "Business Non-revenue", None),
    ("R", "Business Non-revenue", None),
    ("P", "Economy Non-revenue", None),
]


def farebrand_values_sql() -> str:
    parts = []
    for bc, brand, tier in FAREBRAND_ROWS:
        t = "CAST(NULL AS INTEGER)" if tier is None else str(tier)
        parts.append(f"('{bc}', '{brand}', {t})")
    return ", ".join(parts)


def build_sql() -> str:
    ge_apr = f'(cast("DateOfIssuance" as date) >= {APR2026})'
    # No dedup window: exact duplicates on the natural key are ~0 (verified via a streaming
    # approx-distinct check), so this stays a pure streaming COPY (no 38M-row sort/spill).
    return f"""
    COPY (
        WITH fb(bc, farebrand, tier) AS (VALUES {farebrand_values_sql()}),
        src AS (
            SELECT *,
                   {ge_apr} AS issue_ge_apr2026
            FROM read_parquet('{PARQUET}/**/*.parquet')
            WHERE "SoldOperatingCabinClass" IS NULL
               OR "SoldOperatingCabinClass" IN ('Y', 'J', 'W')   -- drop junk 'K'
        )
        SELECT
            "UniqueID"                                   AS customer_id,
            cast("DateOfIssuance" AS DATE)               AS issue_date,
            "DepartureDate"                              AS departure_date,
            "DepartureDateTime"                          AS departure_dt,
            "ArrivalDateTime"                            AS arrival_dt,
            date_diff('day', cast("DateOfIssuance" AS DATE), cast("DepartureDate" AS DATE))
                                                         AS lead_time_days,
            "CurrentCouponStatus"                        AS coupon_status,
            ("CurrentCouponStatus" = 'F')                AS flown,
            "BookingClass"                               AS booking_class,
            "SoldBookingClass"                           AS sold_booking_class,
            -- farebrand resolved with the date-dependent F/G rule
            CASE
                WHEN "BookingClass" = 'F' AND issue_ge_apr2026 THEN 'Mabuhay Award'
                WHEN "BookingClass" = 'F' AND NOT issue_ge_apr2026 THEN 'Economy Non-revenue'
                WHEN "BookingClass" = 'G' AND issue_ge_apr2026 THEN 'Groups'
                WHEN "BookingClass" = 'G' AND NOT issue_ge_apr2026 THEN 'Mabuhay Award'
                ELSE fb.farebrand
            END                                          AS farebrand,
            fb.tier                                      AS value_tier,
            -- loyalty / product flags (date-dependent, §0a)
            CASE WHEN issue_ge_apr2026
                 THEN ("BookingClass" = 'F' OR "SoldBookingClass" = 'F')
                 ELSE ("BookingClass" = 'G' OR "SoldBookingClass" = 'G')
            END                                          AS is_award,
            (issue_ge_apr2026 AND ("BookingClass" = 'G' OR "SoldBookingClass" = 'G'))
                                                         AS is_group_fare,
            ("BookingClass" IN ('A', 'R', 'P')
             OR (NOT issue_ge_apr2026 AND "BookingClass" = 'F'))
                                                         AS is_nonrev,
            coalesce("OperatingCabinClass", 'Unknown')   AS cabin,
            coalesce("Channel Category", 'Unknown')      AS channel,
            "BookingType"                                AS booking_type,
            ("BookingType" = 'Group')                    AS is_group_booking,
            "Revenues w YQ"                              AS revenue,
            "Net Fare"                                   AS net_fare,
            ("Revenues w YQ" IS NULL OR "Revenues w YQ" = 0) AS rev_missing,
            ("Revenues w YQ" < 0 OR "Net Fare" < 0)      AS is_refund,
            "Age"                                        AS age,
            ("Age" IS NOT NULL)                          AS age_known,
            "Pax Count"                                  AS pax_count,
            "is_nonstop"                                 AS is_nonstop,
            ("is_nonstop" = 0)                           AS is_connecting,
            CASE WHEN "TripOD_Path" IS NULL THEN NULL
                 ELSE len(string_split(trim("TripOD_Path"), ' ')) END AS n_legs,
            "POO"                                        AS origin_poo,
            upper(substr("TripOD_Path", 1, 3))           AS trip_origin,
            upper(right("TripOD_Path", 3))               AS trip_dest,
            upper(substr("Sector", 1, 3))                AS sector_origin,
            upper(substr("Sector", 4, 3))                AS sector_dest,
            "TripOD"                                      AS trip_od,
            "OnlineOD"                                    AS online_od,
            "Sector"                                      AS sector,
            "CountryCodeOfIssue"                          AS issue_country,
            ("CountryCodeOfIssue" <> 'PH')               AS foreign_issue,
            "OperatingFlightNumber"                       AS flight_number,
            src_file,
            iss_year
        FROM src
        LEFT JOIN fb ON src."BookingClass" = fb.bc
    )
    TO '{OUT_DIR}'
    (FORMAT PARQUET, PARTITION_BY (iss_year), OVERWRITE_OR_IGNORE, COMPRESSION zstd)
    """


def write_report(con: duckdb.DuckDBPyConnection, rows_in: int) -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    con.execute(f"CREATE VIEW clean AS SELECT * FROM read_parquet('{OUT_DIR}/**/*.parquet')")
    rows_out = con.execute("SELECT count(*) FROM clean").fetchone()[0]

    flags = (
        con.execute("""
        SELECT
          round(100*avg(flown::INT), 2)          AS flown_pct,
          round(100*avg(is_award::INT), 4)        AS award_pct,
          round(100*avg(is_group_fare::INT), 3)   AS group_fare_pct,
          round(100*avg(is_nonrev::INT), 4)       AS nonrev_pct,
          round(100*avg(rev_missing::INT), 3)     AS rev_missing_pct,
          round(100*avg(is_refund::INT), 3)       AS refund_pct,
          round(100*avg(age_known::INT), 2)       AS age_known_pct,
          round(100*avg(foreign_issue::INT), 2)   AS foreign_issue_pct,
          round(100*avg(is_connecting::INT), 2)   AS connecting_pct,
          round(avg(lead_time_days), 1)           AS avg_lead_days,
          round(100*avg((value_tier IS NULL)::INT), 3) AS null_tier_pct
        FROM clean
    """)
        .fetchdf()
        .iloc[0]
    )

    farebrand = con.execute("""
        SELECT farebrand, count(*) AS coupons,
               round(100.0*count(*)/sum(count(*)) OVER (), 3) AS pct
        FROM clean GROUP BY 1 ORDER BY coupons DESC
    """).fetchdf()

    tier = con.execute("""
        SELECT coalesce(value_tier::VARCHAR, 'NULL (award/group/non-rev)') AS value_tier,
               count(*) AS coupons
        FROM clean GROUP BY 1 ORDER BY value_tier
    """).fetchdf()

    removed = rows_in - rows_out
    lines = [
        "# Stage C — data-quality report (`data/interim/pal_clean/`)\n",
        f"- Rows in (raw Parquet): **{rows_in:,}**",
        f"- Rows out (cleaned): **{rows_out:,}**",
        f"- Removed (junk `SoldOperatingCabinClass`): **{removed:,}** "
        f"({100 * removed / rows_in:.4f}%). Exact duplicates on the natural coupon key "
        "were verified ~0 (streaming approx-distinct check), so no dedup was applied.\n",
        "## Flag rates (of cleaned rows)\n",
        f"- flown: {flags['flown_pct']}%  ·  open: {round(100 - flags['flown_pct'], 2)}%",
        f"- award (Mabuhay): {flags['award_pct']}%  ·  group-fare: {flags['group_fare_pct']}%  ·  "
        f"non-revenue: {flags['nonrev_pct']}%",
        f"- revenue missing/zero: {flags['rev_missing_pct']}%  ·  refund (negative): {flags['refund_pct']}%",
        f"- age known: {flags['age_known_pct']}%  ·  foreign-issued: {flags['foreign_issue_pct']}%  ·  "
        f"connecting: {flags['connecting_pct']}%",
        f"- avg lead time: {flags['avg_lead_days']} days  ·  "
        f"NULL value_tier (special classes): {flags['null_tier_pct']}%\n",
        "## Farebrand distribution\n",
        farebrand.to_markdown(index=False),
        "\n## Value-tier distribution (7 Business Flex … 1 Supersaver)\n",
        tier.to_markdown(index=False),
        "",
    ]
    (REPORT / "summary.md").write_text("\n".join(lines) + "\n")
    print(f"\nRows in {rows_in:,} → out {rows_out:,} (removed {removed:,})")
    print(f"Wrote {REPORT / 'summary.md'}")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("PRAGMA threads=6")
    con.execute("SET memory_limit='8GB'")
    con.execute("SET preserve_insertion_order=false")

    rows_in = con.execute(
        f"SELECT count(*) FROM read_parquet('{PARQUET}/**/*.parquet')"
    ).fetchone()[0]

    print("Cleaning coupons → Parquet ...")
    con.execute(build_sql())
    write_report(con, rows_in)


if __name__ == "__main__":
    main()
