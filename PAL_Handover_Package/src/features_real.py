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

from parse_fare_basis import FARE_BASIS_SQL_COLUMNS

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "interim" / "pal_clean"
AIRPORTS = ROOT / "data" / "reference" / "airport_region.csv"
ROUTE_THEMES = ROOT / "data" / "reference" / "route_theme.csv"
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
    con.execute(f"CREATE TABLE theme AS SELECT * FROM read_csv_auto('{ROUTE_THEMES}')")
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


def assert_stay_contract(con: duckdb.DuckDBPyConnection) -> None:
    """`stay_nights` is defined exactly when `round_trip` — enforce it, don't assume it.

    This invariant is the whole reason `stay_nights` is a *conditional* validation anchor rather
    than an unconditional one: its definedness IS `round_trip`, which is the sole bit separating
    OFW/Migrant from Balikbayan/VFR. If a future edit lets it take a value on one-ways (e.g. by
    reading the raw max gap, which on a one-way is a connection layover), a validator could
    silently recover that rule bit from the missingness pattern and score a fake AUC of 1.0.
    """
    bad_oneway, bad_rt, negative = con.execute("""
        SELECT sum((NOT round_trip AND stay_nights IS NOT NULL)::INT),
               sum((round_trip AND n_coupons > 1 AND stay_nights IS NULL)::INT),
               sum((stay_nights < 0)::INT)
        FROM bk
    """).fetchone()
    problems = []
    if bad_oneway:
        problems.append(f"{bad_oneway:,} one-way bookings carry a stay_nights value")
    if bad_rt:
        problems.append(f"{bad_rt:,} multi-coupon round trips have NULL stay_nights")
    if negative:
        problems.append(f"{negative:,} bookings have a negative stay_nights")
    if problems:
        raise AssertionError("stay_nights contract violated — " + "; ".join(problems))


def assert_hard_constraints(con: duckdb.DuckDBPyConnection) -> None:
    """Every `enforce` rule in hard_constraints.csv must hold — checked in code, not in review.

    Ordering alone does NOT implement a `cannot_be`: a first draft of this waterfall satisfied only
    4 of 6, and the two failures (H08, H10) each needed an explicit branch. This assertion is what
    stops that regressing silently, and it reads the CSV rather than a copy of it so the rules and
    the code cannot drift apart.
    """
    import csv as _csv

    rules = ROOT / "data" / "constraints" / "hard_constraints.csv"
    problems = []
    for r in _csv.DictReader(rules.open()):
        if r["status"] != "enforce" or not r["condition"].strip():
            continue
        op = "<>" if r["verdict"] == "must_be" else "="
        n = con.execute(
            f"SELECT count(*) FROM booking WHERE ({r['condition']}) "
            f"AND proxy_segment {op} '{r['segments']}'"
        ).fetchone()[0]
        if n:
            verb = "must be" if r["verdict"] == "must_be" else "cannot be"
            problems.append(f"{r['rule_id']} ({verb} {r['segments']}): {n:,} bookings violate it")
    if problems:
        raise AssertionError(
            "waterfall violates enforce-status hard constraints — " + "; ".join(problems)
        )
    print("  hard-constraint check: all enforce rules satisfied")


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
               (c.sector_dest IN ('JED','MED') OR c.trip_dest IN ('JED','MED')) AS pilgrimage_dest,
               -- trip-purpose theme, keyed on the *trip* endpoint so OAL codeshare beyond-points
               -- (FCO/TLV/CDG/LIS) resolve. Descriptive only — no waterfall branch reads it.
               t.theme                                                          AS dest_theme
        FROM clean c
        LEFT JOIN ref o ON c.sector_origin = o.airport
        LEFT JOIN ref d ON c.sector_dest   = d.airport
        LEFT JOIN theme t ON c.trip_dest   = t.airport
        WHERE c.customer_id NOT IN (SELECT customer_id FROM excluded)
    """)

    # booking aggregation. NB: dominant channel/region/country use max() not mode() — a booking
    # averages 1.66 coupons so the value is ~always constant, and mode() spilled catastrophically
    # (34 GB) over 22.9M groups; max() is equivalent here and cheap.
    con.execute("""
        CREATE TABLE bk AS
        WITH g AS (
            -- ⚠️ `ord_key` fixes a pre-existing non-determinism (found 2026-08-17). Ordering coupons
            -- by `departure_dt` alone leaves ties: 8,014 bookings have two coupons departing at the
            -- same timestamp, and on 3,205 of them the two coupons have *different* trip_origins.
            -- arg_min/arg_max then pick arbitrarily, so `round_trip` — the sole bit splitting
            -- OFW/Migrant from Balikbayan/VFR — flipped on ~20 bookings between identical runs.
            -- Immaterial in size, fatal to reproducibility: two runs of the same code produced
            -- different Parquet. `coupon_number` orders legs within a ticket and breaks most ties.
            -- ⚠️ RESIDUAL, measured 2026-08-18: **1,830 bookings still have a duplicate
            -- (departure_dt, coupon_number) pair**, so the ordering is not total and the build still
            -- moves by ±1 booking between runs. Immaterial numerically (1 in 22.9M) but it drifts the
            -- `fires` counts in data/constraints/*.csv, which check_constraints.py then flags. Fix is
            -- a third key (sector, flight_number) — deferred, not forgotten.
            SELECT *, (departure_dt, coupon_number) AS ord_key,
                   -- Gap to the previous coupon, in departure order. For a round trip the largest
                   -- gap IS the stay; max-gap (rather than last-minus-first) is robust to
                   -- outbound/inbound connections, which inflate the naive span — the two disagree
                   -- on 9.60% of round trips. See src/probe_stay_length.py §0.
                   date_diff('day', lag(departure_date) OVER (
                       PARTITION BY customer_id, issue_date
                       ORDER BY departure_dt, coupon_number
                   ), departure_date) AS gap_days
            FROM coup
        )
        SELECT
            customer_id, issue_date,
            count(*)                                   AS n_coupons,
            count(DISTINCT trip_od)                    AS n_directions,
            arg_min(trip_origin, ord_key)              AS origin_first,
            arg_max(trip_dest,   ord_key)              AS dest_last,
            (arg_min(trip_origin, ord_key) = arg_max(trip_dest, ord_key)) AS round_trip,
            greatest(min(lead_time_days), 0)           AS lead_days,
            max((NOT dom_coupon)::INT) = 1             AS is_international,
            bool_and(dom_coupon)                       AS is_domestic,
            max(intl_region)                           AS dest_region,
            max(pilgrimage_dest::INT) = 1              AS pilgrimage,
            max(value_tier)                            AS max_tier,
            min(value_tier)                            AS min_tier,
            max((cabin IN ('J','W'))::INT) = 1         AS any_premium,
            -- business *cabin*, distinct from `any_business` which is a business *fare*
            -- (value_tier >= 6). SME rows 24/33 turn on cabin 'J' specifically.
            max((cabin = 'J')::INT) = 1                AS any_cabin_j,
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
            month(arg_min(departure_date, ord_key))    AS dep_month,
            -- ── added 2026-08-17 for the RM-Domestic constraint sheet. Descriptive fields only:
            -- no waterfall branch reads any of them, which is what keeps them admissible as
            -- validation anchors. See docs/sme-constraints-intake.md §6 before wiring any in.
            dayofweek(arg_min(departure_date, ord_key)) AS dep_dow,        -- 0=Sun … 6=Sat
            arg_min(trip_dest, ord_key)                AS turn_dest,       -- outbound destination
            -- Theme of the outbound endpoint. max() picks the sole non-NULL: the return leg lands
            -- back at an untagged home airport, so there is only ever one themed endpoint.
            max(dest_theme)                            AS route_theme,
            -- Nights at the destination. NULL for one-ways *by definition*, not by missingness —
            -- there is no stay to measure. Multi-city trips report the longest single stop.
            CASE WHEN arg_min(trip_origin, ord_key) = arg_max(trip_dest, ord_key)
                 THEN max(gap_days) END               AS stay_nights,
            arg_min(fare_basis, ord_key)              AS fare_basis,
            max(tour_code)                            AS tour_code,
            max(rev_pax_ind)                          AS rev_pax_ind,
            max(itin_type)                            AS itin_type,
            max(ff_ind)                               AS ff_ind
        FROM g GROUP BY customer_id, issue_date
    """)

    assert_stay_contract(con)

    # ── proxy-label waterfall v2 (first match wins) — seeds, not final labels ──────────
    # Taxonomy settled by PAL 17-18 Aug 2026 (`wishlist/pal-questions-answered-2026-08-18.csv`);
    # designed and simulated in `docs/waterfall-v2-design.md`; every `enforce` hard rule in
    # `data/constraints/hard_constraints.csv` is asserted below by assert_hard_constraints().
    #
    # Design rule: new branches were INSERTED, existing ones never reordered, so each delta is
    # attributable to a new branch rather than to churn. `proxy_segment_v1` is kept alongside so the
    # before/after is reproducible and so a regression can be diagnosed rather than guessed at.
    con.execute(f"""
        CREATE TABLE booking AS
        SELECT *,
            {FARE_BASIS_SQL_COLUMNS},
            (dep_month IN (4, 5, 12)) AS peak_month,
            -- Last-Minute is a FLAG, not a segment (PAL 17 Aug): it describes a booking, not a
            -- traveller. As a segment it only caught what fell through 8 higher branches (2.95M);
            -- as a flag it covers every short-lead booking (4.41M), including ones labelled
            -- Corporate/OFW/VFR that were short-lead all along and invisible as such.
            (lead_days <= 3) AS is_last_minute,
            -- the value half of "trip-purpose x value": an attribute, never a segment. A price
            -- difference is not a customer type — tested and rejected 17 Aug.
            CASE WHEN max_tier <= 2 THEN 'Budget'
                 WHEN max_tier <= 4 THEN 'Mid'
                 ELSE 'Premium' END AS value_band,
            CASE
                WHEN corp_channel OR (any_business AND lead_days <= 7)      THEN 'Corporate'
                -- H11 must_be: same-day/next-day turnaround on a flexible or premium fare
                WHEN round_trip AND stay_nights <= 1 AND max_tier >= 4      THEN 'Corporate'
                -- the composite fence: four SME rules independently funnel short-turnaround premium
                -- travel to Corporate, so one branch satisfies H10 and H12 together (design §4)
                WHEN round_trip AND lead_days <= 3 AND stay_nights <= 3
                     AND any_premium                                       THEN 'Corporate'
                WHEN is_award                                              THEN 'Mabuhay Loyalist'
                WHEN ff_ind = 1                                            THEN 'Mabuhay Loyalist'
                -- MICE before Family-was: a positive definition beats a residual. `NOT any_cabin_j`
                -- is H13 in the weaker form PAL accepted (B3) — party size is still unavailable.
                WHEN is_group AND round_trip AND lead_days >= 45
                     AND stay_nights BETWEEN 3 AND 7 AND NOT any_cabin_j    THEN 'MICE'
                WHEN pilgrimage                                            THEN 'Pilgrimage'
                WHEN sea_crew                                              THEN 'OFW/Migrant'
                WHEN is_international AND round_trip
                     AND stay_nights BETWEEN 90 AND 150                    THEN 'Intl. Student'
                WHEN foreign_issue AND is_international AND max_tier <= 4
                     AND NOT round_trip                                    THEN 'OFW/Migrant'
                -- H08 carries no lead-time clause, so the fence above misses it: without this
                -- exclusion 2,934 bookings violated a `certain` cannot_be rule
                WHEN foreign_issue AND is_international AND max_tier <= 4
                     AND round_trip
                     AND NOT (stay_nights <= 3 AND any_premium)            THEN 'Balikbayan/VFR'
                -- specific before general: Ultra Wealthy is a premium subset, so it must precede
                -- Premium Bleisure or it can never fire
                WHEN any_premium AND round_trip AND lead_days >= 30
                     AND stay_nights >= 7                                  THEN 'Ultra Wealthy Leisure'
                WHEN any_premium AND is_international                       THEN 'Premium Bleisure'
                -- closes taxonomy gap #4: PH-issued international economy, 75% of the old
                -- Unassigned bucket. `Family` is gone (PAL 18 Aug), so its international group
                -- bookings land here.
                WHEN NOT foreign_issue AND is_international
                     AND NOT any_premium                    THEN 'Outbound International Leisure'
                WHEN is_domestic AND NOT any_premium                        THEN 'Leisure'
                ELSE 'Unassigned'
            END AS proxy_segment,
            -- v1, retained for before/after comparison and regression diagnosis only. Nothing
            -- downstream should read this.
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
            END AS proxy_segment_v1
        FROM bk
    """)
    assert_hard_constraints(con)
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

    # descriptive fields added 2026-08-17 — reported so their coverage is visible, not assumed
    # formatted server-side: pandas renders large BIGINT counts in scientific notation otherwise
    stay = con.execute("""
        SELECT format('{:,}', count(*) FILTER (WHERE round_trip))              AS round_trips,
               format('{:,}', count(*) FILTER (WHERE stay_nights IS NOT NULL)) AS with_stay,
               round(100.0*count(*) FILTER (WHERE stay_nights IS NOT NULL)
                     / nullif(count(*) FILTER (WHERE round_trip), 0), 2)       AS pct_of_rt,
               round(100.0*count(*) FILTER (WHERE stay_nights IS NOT NULL)
                     / count(*), 2)                                            AS pct_of_book,
               median(stay_nights)                                             AS median_nights,
               count(*) FILTER (WHERE stay_nights > 365)                       AS over_365
        FROM booking
    """).fetchdf()
    theme = con.execute("""
        SELECT coalesce(route_theme, '(untagged)') theme, count(*) bookings,
               round(100.0*count(*)/sum(count(*)) OVER (), 2) pct
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
        "\n## Descriptive fields added 2026-08-17 (not read by the waterfall)\n",
        "`stay_nights` — NULL on one-ways by definition, so its coverage ceiling is the round-trip",
        "share. Any rule or anchor built on it is silent on the rest of the book.\n",
        stay.to_markdown(index=False),
        "\n### Route theme — bookings\n",
        theme.to_markdown(index=False),
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
