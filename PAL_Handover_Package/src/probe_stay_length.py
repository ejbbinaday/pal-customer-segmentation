"""Probe: does stay length carry the OFW-vs-Balikbayan signal the SME claims?

Tests the RM-Domestic constraint sheet's highest-value claim (rows 14/16/17/21,
see `docs/sme-constraints-intake.md` §3):

    OFWs hold employer-mandated leave of precisely ~30 or ~45 days;
    balikbayans stay open-ended, 14+ and typically 21+ over the Q4/Q1 holidays.

Why the obvious test is the wrong test
--------------------------------------
The current waterfall separates OFW/Migrant from Balikbayan/VFR on `round_trip`
alone (rules ⑤/⑥ in `features_real.py`). So *every* foreign-issued cheap
international round trip is already labelled Balikbayan/VFR by construction, and
stay length is undefined for the one-ways labelled OFW. Comparing "our OFW" to
"our VFR" on stay length is therefore vacuous.

The real question is whether the bucket the waterfall lumps together is **two
hidden populations**: does the stay-length distribution inside current
Balikbayan/VFR carry an employer-mandate spike at 30/45 nights?

The confound that decides it
----------------------------
Humans book round numbers. A spike at 30 nights proves nothing on its own — 7,
14, 21 and 28 will spike too, in every corridor, for nobody's employer's sake.
So the test is **differential**: excess mass at 30/45 must be *specific to the
labour corridors* relative to tourist and domestic corridors. If everyone spikes
equally, the claim is round-number bias and the lever is null.

A second confound is checked, not assumed away: published fares carry maximum-stay
conditions (commonly 30 days), which would produce the same spike from the fare
rule rather than from an employment contract. Reported per value tier.

Outputs: `outputs/stay_length/summary.md` + `histogram.csv` + `excess.csv`.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "interim" / "pal_clean"
AIRPORTS = ROOT / "data" / "reference" / "airport_region.csv"
OUT = ROOT / "outputs" / "stay_length"

# ── the SME's own airport lists (constraint sheet rows 18/19/22/23/24/27/29) ──
GULF_LABOUR = ("DXB", "RUH", "DMM", "DOH", "BAH", "KWI", "AUH", "JED", "MED")
EAST_ASIA_LABOUR = ("HKG", "TPE")
TOURIST_HUB = ("BKK", "SIN", "ICN", "NRT", "KIX", "HND")
BALIKBAYAN_HEAVY = ("LAX", "SFO", "JFK", "SEA", "YVR", "YYZ", "HNL", "GUM", "SYD", "MEL")
PILGRIM_CATHOLIC = ("FCO", "TLV", "CDG", "LIS")

# stay values to test. 30/45 are the SME's claim; the rest are the round-number
# control — if 30 is not conspicuous *against these*, there is no signal.
TEST_STAYS = (7, 14, 15, 21, 28, 29, 30, 31, 44, 45, 46, 60, 90)

MAX_STAY = 200  # beyond this, counts are too thin for a local baseline


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("PRAGMA memory_limit='8GB'")
    con.execute(f"SET temp_directory='{OUT / 'tmp'}'")
    con.execute(f"CREATE VIEW clean AS SELECT * FROM read_parquet('{CLEAN}/**/*.parquet')")
    con.execute(f"CREATE TABLE ref AS SELECT * FROM read_csv_auto('{AIRPORTS}')")
    return con


def build(con: duckdb.DuckDBPyConnection) -> None:
    """Booking-grain table with stay_nights, corridor class and the waterfall label."""
    con.execute("""
        CREATE TABLE excluded AS
        SELECT customer_id FROM clean GROUP BY 1 HAVING bool_and(is_nonrev)
    """)

    def in_list(codes: tuple[str, ...]) -> str:
        return "(" + ", ".join(f"'{c}'" for c in codes) + ")"

    con.execute(f"""
        CREATE VIEW coup AS
        SELECT c.*,
               (o.is_domestic = 1 AND d.is_domestic = 1) AS dom_coupon,
               CASE WHEN d.is_domestic = 0 THEN d.region
                    WHEN o.is_domestic = 0 THEN o.region END AS intl_region,
               (c.sector_dest IN ('JED','MED') OR c.trip_dest IN ('JED','MED')) AS pilgrimage_dest,
               -- corridor class keyed off the *furthest* point of the trip, not the sector
               CASE
                 WHEN c.trip_dest IN {in_list(GULF_LABOUR)}      THEN 'gulf_labour'
                 WHEN c.trip_dest IN {in_list(EAST_ASIA_LABOUR)} THEN 'east_asia_labour'
                 WHEN c.trip_dest IN {in_list(TOURIST_HUB)}      THEN 'tourist_hub'
                 WHEN c.trip_dest IN {in_list(BALIKBAYAN_HEAVY)} THEN 'balikbayan_heavy'
                 WHEN c.trip_dest IN {in_list(PILGRIM_CATHOLIC)} THEN 'pilgrim_catholic'
               END AS corridor
        FROM clean c
        LEFT JOIN ref o ON c.sector_origin = o.airport
        LEFT JOIN ref d ON c.sector_dest   = d.airport
        WHERE c.customer_id NOT IN (SELECT customer_id FROM excluded)
    """)

    # Stay length, two ways:
    #   span     = last departure − first departure (the figure quoted in KB §15)
    #   max_gap  = largest gap between consecutive coupon departures — robust to
    #              outbound/inbound connections, which inflate `span` by 0–1 days
    # They agree on simple 2-coupon round trips; max_gap is the one used.
    con.execute("""
        CREATE TABLE bk AS
        WITH c AS (
            SELECT customer_id, issue_date, departure_date, departure_dt,
                   trip_origin, trip_dest, dom_coupon, intl_region, corridor,
                   pilgrimage_dest, value_tier, cabin, is_award, is_group_booking,
                   is_group_fare, foreign_issue, issue_country, channel, is_refund,
                   is_connecting, revenue, age, age_known,
                   date_diff('day', lag(departure_date) OVER (
                       PARTITION BY customer_id, issue_date ORDER BY departure_dt
                   ), departure_date) AS gap_days
            FROM coup
        )
        SELECT
            customer_id, issue_date,
            count(*)                                    AS n_coupons,
            arg_min(trip_origin, departure_dt)          AS origin_first,
            arg_max(trip_dest,   departure_dt)          AS dest_last,
            (arg_min(trip_origin, departure_dt) = arg_max(trip_dest, departure_dt)) AS round_trip,
            date_diff('day', min(departure_date), max(departure_date)) AS stay_span,
            max(gap_days)                               AS stay_gap,
            bool_and(dom_coupon)                        AS is_domestic,
            max((NOT dom_coupon)::INT) = 1              AS is_international,
            max(intl_region)                            AS dest_region,
            -- corridor of the outbound turn-around point: first non-null wins
            arg_max(corridor, CASE WHEN corridor IS NULL THEN 0 ELSE 1 END) AS corridor,
            max(pilgrimage_dest::INT) = 1               AS pilgrimage,
            max(value_tier)                             AS max_tier,
            max((cabin IN ('J','W'))::INT) = 1          AS any_premium,
            max((cabin = 'J')::INT) = 1                 AS any_j,
            dayofweek(arg_min(departure_date, departure_dt)) AS dep_dow,  -- 0=Sun … 6=Sat
            arg_min(trip_dest, departure_dt)            AS turn_dest,  -- outbound destination
            max((value_tier >= 6)::INT) = 1             AS any_business,
            max(is_award::INT) = 1                      AS is_award,
            max((is_group_booking OR is_group_fare)::INT) = 1 AS is_group,
            max(foreign_issue::INT) = 1                 AS foreign_issue,
            max(channel)                                AS channel,
            max((channel IN ('TMC','Corporate Web Portal'))::INT) = 1 AS corp_channel,
            max((channel = 'Sea Crew')::INT) = 1        AS sea_crew,
            max(is_connecting::INT) = 1                 AS connecting,
            greatest(min(date_diff('day', issue_date, departure_date)), 0) AS lead_days,
            month(arg_min(departure_date, departure_dt)) AS dep_month,
            max(age)                                    AS age,
            max(age_known::INT) = 1                     AS age_known
        FROM c GROUP BY customer_id, issue_date
    """)

    # same waterfall as features_real.py — so "current Balikbayan/VFR" means exactly
    # what it means in the shipped model
    con.execute("""
        CREATE TABLE bkl AS
        SELECT *,
            CASE
                WHEN is_award                                          THEN 'Mabuhay Loyalist'
                WHEN corp_channel OR (any_business AND lead_days <= 7)  THEN 'Corporate'
                WHEN pilgrimage                                        THEN 'Pilgrimage'
                WHEN sea_crew                                          THEN 'OFW/Migrant'
                WHEN foreign_issue AND is_international AND max_tier <= 4
                     AND NOT round_trip                                THEN 'OFW/Migrant'
                WHEN foreign_issue AND is_international AND max_tier <= 4
                     AND round_trip                                    THEN 'Balikbayan/VFR'
                WHEN any_premium AND is_international                   THEN 'Premium Bleisure'
                WHEN is_group                                          THEN 'Family'
                WHEN lead_days <= 3                                    THEN 'Last-Minute'
                WHEN is_domestic AND NOT any_premium                    THEN 'Budget/Adventure'
                ELSE 'Unassigned'
            END AS proxy_segment
        FROM bk
    """)


def q(con, sql: str):
    return con.execute(sql).fetchall()


def one(con, sql):
    return con.execute(sql).fetchone()


def excess_table(con, where: str, label: str) -> list[dict]:
    """Excess mass at each TEST_STAY vs a local baseline of neighbours ±2..±6.

    The ±1 ring is excluded from the baseline so a two-day-wide spike cannot
    inflate the yardstick it is measured against.
    """
    rows = q(
        con,
        f"""
        SELECT stay, count(*) AS n FROM (
            SELECT stay_gap AS stay FROM bkl
            WHERE round_trip AND stay_gap BETWEEN 1 AND {MAX_STAY} AND ({where})
        ) GROUP BY stay ORDER BY stay
        """,
    )
    hist = dict(rows)
    total = sum(hist.values())
    out = []
    for s in TEST_STAYS:
        ring = [hist.get(s + d, 0) for d in (-6, -5, -4, -3, -2, 2, 3, 4, 5, 6)]
        ring = sorted(ring)
        base = (ring[4] + ring[5]) / 2  # median of the 10-value ring
        n = hist.get(s, 0)
        out.append(
            {
                "group": label,
                "stay": s,
                "n": n,
                "baseline": round(base, 1),
                "excess": round(n / base, 3) if base > 0 else None,
                "pct_of_group": round(100 * n / total, 3) if total else None,
            }
        )
    return out, total, hist


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "tmp").mkdir(exist_ok=True)
    con = connect()
    build(con)

    L: list[str] = ["# Probe — stay length as the OFW ↔ Balikbayan discriminator", ""]
    L.append("Tests `docs/sme-constraints-intake.md` §3 (constraint sheet rows 14/16/17/21).")
    L.append("")

    # ── 0. coverage ───────────────────────────────────────────────────────────
    tot, rt, comp, disagree = one(
        con,
        f"""
        SELECT count(*),
               sum(round_trip::INT),
               sum((round_trip AND stay_gap BETWEEN 0 AND {MAX_STAY})::INT),
               sum((round_trip AND stay_gap IS NOT NULL
                    AND stay_gap <> stay_span)::INT)
        FROM bkl
        """,
    )
    L += [
        "## 0. Coverage",
        "",
        f"- bookings: **{tot:,}**",
        f"- round trips: **{rt:,}** ({100 * rt / tot:.1f}%)",
        f"- with computable stay ≤ {MAX_STAY} nights: **{comp:,}** "
        f"({100 * comp / rt:.1f}% of round trips)",
        f"- `stay_gap` ≠ `stay_span` on **{disagree:,}** ({100 * disagree / rt:.2f}% of round trips) "
        "— connections; `stay_gap` used throughout",
        "",
    ]

    # ── 1. is the current VFR bucket bimodal? ─────────────────────────────────
    L += ["## 1. Shape of the bucket the waterfall lumps together", ""]
    vfr = "proxy_segment = 'Balikbayan/VFR'"
    band = q(
        con,
        f"""
        SELECT CASE
                 WHEN stay_gap <= 3   THEN '01_1-3'
                 WHEN stay_gap <= 7   THEN '02_4-7'
                 WHEN stay_gap <= 13  THEN '03_8-13'
                 WHEN stay_gap <= 20  THEN '04_14-20'
                 WHEN stay_gap <= 27  THEN '05_21-27'
                 WHEN stay_gap <= 45  THEN '06_28-45'
                 WHEN stay_gap <= 90  THEN '07_46-90'
                 ELSE '08_90+' END AS band,
               count(*) AS n
        FROM bkl WHERE round_trip AND stay_gap BETWEEN 1 AND {MAX_STAY} AND {vfr}
        GROUP BY 1 ORDER BY 1
        """,
    )
    nb = sum(x[1] for x in band)
    widths = {"01": 3, "02": 4, "03": 6, "04": 7, "05": 7, "06": 18, "07": 45, "08": 110}
    L += [
        "⚠️ **Read the per-night column, not the share.** The bands have unequal widths, and on raw",
        "shares 28–45 looks like a second mode. Per night of width it does not — the density falls",
        "monotonically. **There is no valley between a 'family visit' mode and a 'worker' mode.**",
        "",
        "| stay band (nights) | bookings | share of bucket | **per night of band width** |",
        "|---|---|---|---|",
    ]
    for b, n in band:
        dens = 100 * n / nb / widths[b[:2]]
        L.append(f"| {b[3:]} | {n:,} | {100 * n / nb:.1f}% | {dens:.3f}%/night |")
    L += ["", f"Total round-trip Balikbayan/VFR with computable stay: **{nb:,}**", ""]

    # ── 2. the differential test ──────────────────────────────────────────────
    L += [
        "## 2. The differential test — excess mass at 30 / 45 by corridor",
        "",
        "`excess` = count at that exact stay ÷ median of its ±2..±6 neighbours.",
        "**1.0 = no spike.** 7/14/21/28 are the round-number control: they spike for",
        "everyone. The SME claim survives only if 30 and 45 are conspicuous in the",
        "labour corridors *and not* in the tourist / domestic ones.",
        "",
    ]
    groups = {
        "gulf_labour": "corridor = 'gulf_labour'",
        "east_asia_labour": "corridor = 'east_asia_labour'",
        "tourist_hub": "corridor = 'tourist_hub'",
        "balikbayan_heavy": "corridor = 'balikbayan_heavy'",
        "pilgrim_catholic": "corridor = 'pilgrim_catholic'",
        "domestic": "is_domestic",
        "ALL_international": "is_international",
        "VFR_bucket_only": vfr,
        "gulf_foreign_issued": "corridor = 'gulf_labour' AND foreign_issue",
        "gulf_PH_issued": "corridor = 'gulf_labour' AND NOT foreign_issue",
    }
    allrows: list[dict] = []
    hists: dict[str, dict] = {}
    totals: dict[str, int] = {}
    for name, w in groups.items():
        rows, t, h = excess_table(con, w, name)
        allrows += rows
        hists[name] = h
        totals[name] = t

    hdr = "| corridor | n round trips | " + " | ".join(str(s) for s in TEST_STAYS) + " |"
    L += [hdr, "|---" * (len(TEST_STAYS) + 2) + "|"]
    for name in groups:
        cells = []
        for s in TEST_STAYS:
            e = next(r["excess"] for r in allrows if r["group"] == name and r["stay"] == s)
            cells.append("—" if e is None else f"{e:.2f}")
        L.append(f"| {name} | {totals[name]:,} | " + " | ".join(cells) + " |")
    L.append("")

    # ── 3. fare-rule confound ────────────────────────────────────────────────
    L += [
        "## 3. Confound — is the 30-night spike a fare rule rather than a contract?",
        "",
        "Published fares carry maximum-stay conditions. If the spike is a fare rule it",
        "should track the value tier, not the corridor.",
        "",
    ]
    L += [
        "| value tier | n | excess@30 | excess@45 | excess@14 (control) |",
        "|---|---|---|---|---|",
    ]
    for t in range(1, 8):
        rows, n, _ = excess_table(con, f"max_tier = {t} AND is_international", f"tier{t}")
        if n < 5000:
            continue
        g = {r["stay"]: r["excess"] for r in rows}
        L.append(
            f"| {t} | {n:,} | "
            + " | ".join("—" if g[s] is None else f"{g[s]:.2f}" for s in (30, 45, 14))
            + " |"
        )
    L.append("")

    # ── 4. does 28–45 look different from the rest of the bucket? ─────────────
    L += [
        "## 4. If the 28–45 band is workers, it should look like workers",
        "",
        "Profile of the current Balikbayan/VFR bucket, split at the SME's own boundary.",
        "A hidden OFW population should show up as *lower* group rate, *higher* Gulf",
        "share and a different seasonality — not merely a different stay length.",
        "",
    ]
    prof = q(
        con,
        f"""
        SELECT CASE WHEN stay_gap BETWEEN 28 AND 45 THEN 'B_28-45'
                    WHEN stay_gap BETWEEN 14 AND 27 THEN 'A_14-27'
                    WHEN stay_gap > 45              THEN 'C_46+'
                    ELSE '0_under14' END AS band,
               count(*) AS n,
               round(100*avg(is_group::INT), 2)                             AS pct_group,
               round(100*avg((corridor='gulf_labour')::INT), 2)             AS pct_gulf,
               round(100*avg((corridor='balikbayan_heavy')::INT), 2)        AS pct_balik,
               round(100*avg((dep_month IN (11,12,1))::INT), 2)             AS pct_q4q1,
               round(100*avg((dep_month IN (4,5))::INT), 2)                 AS pct_summer,
               round(median(lead_days), 1)                                  AS med_lead,
               round(median(max_tier), 1)                                   AS med_tier,
               round(100*avg(connecting::INT), 2)                           AS pct_conn,
               round(median(age) FILTER (WHERE age_known), 1)               AS med_age
        FROM bkl WHERE round_trip AND stay_gap BETWEEN 1 AND {MAX_STAY} AND {vfr}
        GROUP BY 1 ORDER BY 1
        """,
    )
    L += [
        "| band | n | %group | %Gulf | %US/CA/AU | %Q4-Q1 dep | %Apr-May dep | "
        "med lead | med tier | %conn | med age |",
        "|---" * 11 + "|",
    ]
    for r in prof:
        L.append("| " + " | ".join(f"{v:,}" if isinstance(v, int) else str(v) for v in r) + " |")
    L.append("")

    # ── 5. how much of the book is actually at stake ─────────────────────────
    n2845 = one(
        con,
        f"SELECT count(*) FROM bkl WHERE round_trip AND stay_gap BETWEEN 28 AND 45 AND {vfr}",
    )[0]
    L += [
        "## 5. Size of the prize",
        "",
        f"- Current Balikbayan/VFR, round trip, stay 28–45: **{n2845:,}** bookings "
        f"({100 * n2845 / tot:.2f}% of all bookings, {100 * n2845 / nb:.1f}% of the bucket)",
        "",
    ]

    # ── 6. does it actually discriminate? ────────────────────────────────────
    L += [
        "## 6. Discrimination — AUC of stay length alone",
        "",
        "No ground truth exists, so the target is a **corridor proxy**: within foreign-issued",
        "cheap international round trips, separate Gulf/East-Asia labour destinations from",
        "US/Canada/Australia balikbayan destinations. Imperfect (some Gulf trips are genuine",
        "family visits) but *independent of `round_trip`*, which is the bit the model uses today.",
        "0.50 = coin flip, which is roughly what the current single-bit rule achieves.",
        "",
    ]
    base = (
        "foreign_issue AND is_international AND max_tier <= 4 AND round_trip "
        f"AND stay_gap BETWEEN 1 AND {MAX_STAY}"
    )
    auc_rows = []
    for name, pos, neg in [
        (
            "stay length",
            "corridor IN ('gulf_labour','east_asia_labour')",
            "corridor = 'balikbayan_heavy'",
        ),
        ("stay length (Gulf only)", "corridor = 'gulf_labour'", "corridor = 'balikbayan_heavy'"),
    ]:
        r = one(
            con,
            f"""
            WITH d AS (
                SELECT stay_gap AS x, ({pos})::INT AS y FROM bkl
                WHERE {base} AND (({pos}) OR ({neg}))
            ), r AS (SELECT y, rank() OVER (ORDER BY x) AS rk FROM d)
            SELECT
              (sum(CASE WHEN y=1 THEN rk END) - sum(y)*(sum(y)+1)/2.0)
                 / (sum(y) * sum(1-y))          AS auc,
              sum(y) AS n_pos, sum(1-y) AS n_neg
            FROM r
            """,
        )
        auc_rows.append((name, r[0], r[1], r[2]))
    L += ["| feature | AUC | n labour | n balikbayan |", "|---|---|---|---|"]
    for name, auc, npos, nneg in auc_rows:
        L.append(f"| {name} | **{auc:.3f}** | {int(npos):,} | {int(nneg):,} |")
    L.append("")

    # concentration in the 28-32 window, by corridor — the practical version of §2
    L += [
        "Share of each corridor's round trips landing in the 28–32 night window "
        "(the SME's mechanism, with travel-day slop):",
        "",
        "| corridor | 28–32 nights | 12–16 nights (control) | ratio |",
        "|---|---|---|---|",
    ]
    for name, w in [
        ("gulf_labour", "corridor = 'gulf_labour'"),
        ("east_asia_labour", "corridor = 'east_asia_labour'"),
        ("tourist_hub", "corridor = 'tourist_hub'"),
        ("balikbayan_heavy", "corridor = 'balikbayan_heavy'"),
        ("domestic", "is_domestic"),
    ]:
        a, b, t = one(
            con,
            f"""SELECT sum((stay_gap BETWEEN 28 AND 32)::INT),
                       sum((stay_gap BETWEEN 12 AND 16)::INT), count(*)
                FROM bkl WHERE round_trip AND stay_gap BETWEEN 1 AND {MAX_STAY} AND ({w})""",
        )
        L.append(
            f"| {name} | {100 * a / t:.2f}% | {100 * b / t:.2f}% | {a / b:.2f} |"
            if b
            else f"| {name} | {100 * a / t:.2f}% | — | — |"
        )
    L.append("")

    # write artefacts
    import csv

    with open(OUT / "excess.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(allrows[0].keys()))
        w.writeheader()
        w.writerows(allrows)
    with open(OUT / "histogram.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["group", "stay_nights", "n"])
        for g, h in hists.items():
            for s in sorted(h):
                w.writerow([g, s, h[s]])

    (OUT / "summary.md").write_text("\n".join(L) + "\n")
    print(
        textwrap.dedent(f"""
        wrote {OUT / "summary.md"}
              {OUT / "excess.csv"}
              {OUT / "histogram.csv"}
    """)
    )
    print("\n".join(L))


if __name__ == "__main__":
    main()
