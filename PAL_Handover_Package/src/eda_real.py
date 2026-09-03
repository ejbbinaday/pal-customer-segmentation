"""Stage E (confirmation pass) — validate the plan's assumptions on the cleaned data.

Answers the "Part A" questions we wanted to confirm before feature engineering, on
`data/interim/pal_clean/` (~38M coupons):

  A1  booking grain — is (customer_id, issue_date) a sound round-trip/PNR proxy?
  A2  heavy tail    — who are the 100+-coupon customers (non-rev / crew / agency)?
  A3  non-revenue   — how many customers are essentially all staff/comp?
  A4  lead time     — negatives (reissues) and distribution sanity
  A5  loyalty       — distinct customers with award / premium / repeat behaviour
  A6  proxy seeds   — rough booking-level magnitudes for the 10 target segments

Read-only. Writes `outputs/eda_real/confirmations.md`.

Run:
    python src/eda_real.py
"""

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "interim" / "pal_clean"
OUT = ROOT / "outputs" / "eda_real"
TMP = Path("/Users/joshbinaday/.claude/jobs/e24f9c28/tmp")


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("PRAGMA threads=6")
    con.execute("SET memory_limit='8GB'")
    con.execute("SET preserve_insertion_order=false")
    if TMP.exists():
        con.execute(f"SET temp_directory='{TMP}'")
    con.execute(f"CREATE VIEW clean AS SELECT * FROM read_parquet('{CLEAN}/**/*.parquet')")

    # Booking grain = (customer_id, issue_date). Round-trip = journey returns to its origin.
    con.execute("""
        CREATE TABLE bookings AS
        SELECT
            customer_id, issue_date,
            count(*)                               AS n_coupons,
            count(DISTINCT trip_od)                AS n_directions,
            arg_min(trip_origin, departure_dt)     AS origin_first,
            arg_max(trip_dest,   departure_dt)     AS dest_last,
            min(lead_time_days)                    AS lead_days,
            max(is_award::INT)      = 1            AS any_award,
            max(is_group_booking::INT) = 1         AS any_group,
            max((cabin IN ('J','W'))::INT) = 1     AS any_premium,
            max((value_tier >= 6)::INT) = 1        AS any_business,
            max((channel = 'Sea Crew')::INT) = 1   AS any_sea_crew,
            max(foreign_issue::INT) = 1            AS foreign_issue,
            min(value_tier)                        AS min_tier,
            sum(CASE WHEN NOT is_refund THEN revenue ELSE 0 END) AS rev_pos,
            bool_and(is_nonrev)                    AS all_nonrev
        FROM clean GROUP BY customer_id, issue_date
    """)
    con.execute("""
        CREATE TABLE customers AS
        SELECT
            customer_id,
            count(DISTINCT issue_date)             AS n_bookings,
            sum(n_coupons)                         AS n_coupons,
            max(any_award::INT) = 1                AS any_award,
            max(any_premium::INT) = 1              AS any_premium,
            max(any_sea_crew::INT) = 1             AS any_sea_crew,
            bool_and(all_nonrev)                   AS all_nonrev,
            date_diff('day', min(issue_date), max(issue_date)) AS tenure_days
        FROM bookings GROUP BY customer_id
    """)
    return con


def one(con, sql: str):
    return con.execute(sql).fetchdf().iloc[0]


def df(con, sql: str):
    return con.execute(sql).fetchdf()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    con = connect()
    L: list[str] = ["# Stage E — plan-assumption confirmations (`data/interim/pal_clean/`)\n"]

    # ---- A1 booking grain ----
    b = one(
        con,
        """
        SELECT count(*) n_bookings,
               round(avg(n_coupons),2) avg_coupons,
               round(100*avg((is_round_trip)::INT),1) pct_round_trip,
               round(100*avg((n_directions=1)::INT),1) pct_one_direction,
               round(100*avg((n_directions>2)::INT),1) pct_gt2_dir
        FROM (SELECT *, (origin_first = dest_last) AS is_round_trip FROM bookings)
    """,
    )
    L += [
        "## A1 — Booking grain `(customer_id, issue_date)`\n",
        f"- Bookings: **{int(b.n_bookings):,}** (from 38.1M coupons), avg **{b.avg_coupons}** coupons each",
        f"- **Round-trip (returns to origin): {b.pct_round_trip}%**  ·  single-direction: {b.pct_one_direction}%",
        f"- Bookings with >2 directions (possible multi-PNR/multi-city same day): {b.pct_gt2_dir}%",
        "- *Read:* a booking cleanly captures the out+return journey for the round-trip share; "
        "one-direction bookings are true one-ways or separately-issued returns.\n",
    ]

    # ---- A2 heavy tail ----
    tail = df(
        con,
        """
        SELECT CASE WHEN n_coupons>=100 THEN '100+' WHEN n_coupons>=20 THEN '20-99'
                    WHEN n_coupons>=8 THEN '8-19' ELSE '<8' END bucket,
               count(*) n_customers,
               round(100*avg(any_sea_crew::INT),1) pct_sea_crew,
               round(100*avg(all_nonrev::INT),2) pct_all_nonrev
        FROM customers GROUP BY 1 ORDER BY min(n_coupons)
    """,
    )
    # channel mix of the 100+ tail
    tailchan = df(
        con,
        """
        SELECT channel, count(*) coupons
        FROM clean
        WHERE customer_id IN (SELECT customer_id FROM customers WHERE n_coupons>=100)
        GROUP BY 1 ORDER BY coupons DESC LIMIT 6
    """,
    )
    L += [
        "## A2 — Heavy tail (customers by coupon count)\n",
        tail.to_markdown(index=False),
        "\n**Top channels of the 100+-coupon customers:**\n",
        tailchan.to_markdown(index=False),
        "",
    ]

    # ---- A3 non-revenue population ----
    nr = one(
        con,
        """
        SELECT
          sum(all_nonrev::INT) n_all_nonrev_customers,
          count(*) n_customers,
          round(100*avg(all_nonrev::INT),3) pct_all_nonrev
        FROM customers
    """,
    )
    L += [
        "## A3 — Non-revenue (staff/comp) population\n",
        f"- Customers whose **every** coupon is non-revenue: **{int(nr.n_all_nonrev_customers):,}** "
        f"({nr.pct_all_nonrev}% of {int(nr.n_customers):,}) — clean exclusion candidates.\n",
    ]

    # ---- A4 lead time ----
    lt = one(
        con,
        """
        SELECT count(*) n,
               sum((lead_time_days<0)::INT) n_negative,
               round(100*avg((lead_time_days<0)::INT),3) pct_negative,
               min(lead_time_days) min_d, median(lead_time_days) med_d,
               round(avg(lead_time_days),1) avg_d, max(lead_time_days) max_d,
               round(100*avg((lead_time_days BETWEEN 0 AND 3)::INT),2) pct_last_minute
        FROM clean
    """,
    )
    L += [
        "## A4 — Booking lead time (departure − issuance)\n",
        f"- min {int(lt.min_d)}, median {int(lt.med_d)}, mean {lt.avg_d}, max {int(lt.max_d)} days",
        f"- **Negative (issued after departure = reissues): {int(lt.n_negative):,} ({lt.pct_negative}%)** "
        "→ clamp/flag in FE",
        f"- Last-minute (0–3 days): {lt.pct_last_minute}%\n",
    ]

    # ---- A5 loyalty coverage ----
    ly = one(
        con,
        """
        SELECT
          sum(any_award::INT) award_customers,
          sum((n_bookings>=2)::INT) repeat_customers,
          sum(any_premium::INT) premium_customers,
          count(*) n_customers,
          round(avg(tenure_days),1) avg_tenure_days
        FROM customers
    """,
    )
    L += [
        "## A5 — Loyalty signal coverage (distinct customers)\n",
        f"- With ≥1 **award** ticket: **{int(ly.award_customers):,}** "
        f"({100 * ly.award_customers / ly.n_customers:.3f}%)",
        f"- **Repeat** (≥2 bookings): **{int(ly.repeat_customers):,}** "
        f"({100 * ly.repeat_customers / ly.n_customers:.1f}%)",
        f"- Ever flew **premium** (J/W): {int(ly.premium_customers):,} "
        f"({100 * ly.premium_customers / ly.n_customers:.1f}%)",
        f"- Avg tenure (first→last issuance): {ly.avg_tenure_days} days\n",
    ]

    # ---- A6 rough proxy-seed magnitudes (booking grain) ----
    seed = one(
        con,
        """
        SELECT count(*) n_bookings,
          sum((lead_days BETWEEN 0 AND 3)::INT)                         last_minute,
          sum(any_award::INT)                                           mabuhay_award,
          sum((any_business AND lead_days<=7)::INT)                     corporate_like,
          sum((min_tier<=2)::INT)                                       budget_econ,
          sum((foreign_issue AND min_tier<=4)::INT)                     ofw_diaspora_econ,
          sum((any_group)::INT)                                         family_group,
          sum((any_premium AND NOT any_business)::INT)                  prem_econ_leisure
        FROM bookings
    """,
    )
    nb = int(seed.n_bookings)

    def pct(x):
        return f"{int(x):,} ({100 * x / nb:.2f}%)"

    seedtbl = [
        "| Segment (rough proxy) | Bookings matched |",
        "|---|---|",
        f"| Last-Minute (lead 0–3d) | {pct(seed.last_minute)} |",
        f"| Mabuhay Loyalist (award) | {pct(seed.mabuhay_award)} |",
        f"| Corporate-like (business + lead ≤7d) | {pct(seed.corporate_like)} |",
        f"| Budget/Adventure (tier ≤2 econ) | {pct(seed.budget_econ)} |",
        f"| OFW/diaspora (foreign-issued econ) | {pct(seed.ofw_diaspora_econ)} |",
        f"| Family/group | {pct(seed.family_group)} |",
        f"| Premium-econ leisure | {pct(seed.prem_econ_leisure)} |",
    ]
    L += [
        "## A6 — Rough proxy-seed magnitudes (booking grain — indicative, not final labels)\n",
        f"Total bookings: **{nb:,}**\n",
        "\n".join(seedtbl),
        "\n> Coarse rules to gauge signal size only. Domestic-vs-international refinement "
        "(for Budget/Balikbayan/Pilgrimage) needs the airport→region lookup — Part B item 6.\n",
    ]

    (OUT / "confirmations.md").write_text("\n".join(L) + "\n")
    print("Wrote", OUT / "confirmations.md")
    print(
        f"\nbookings={nb:,}  round_trip={b.pct_round_trip}%  "
        f"neg_lead={int(lt.n_negative):,}  award_customers={int(ly.award_customers):,}  "
        f"repeat={100 * ly.repeat_customers / ly.n_customers:.1f}%"
    )


if __name__ == "__main__":
    main()
