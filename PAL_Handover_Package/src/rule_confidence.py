"""Rule-confidence diagnostics — how *determined* is each deterministic label?

The waterfall in `src/features_real.py` assigns a segment with certainty, but certainty is not
confidence: a booking that satisfies four branch predicates is labelled by our chosen **priority
order**, not by the evidence. This script quantifies that, exactly, on the full 22.9M-booking
population (no sampling).

Three measures:

  1. **Rule competition**   how many of the 10 branch predicates each booking satisfies.
                            1 = uncontested · 2 = the priority order broke a tie · 3+ = artefact.
  2. **Runner-up label**    what the booking would have been called one priority step lower —
                            makes overlapping/overlay segments visible (Last-Minute is the big one).
  3. **Boundary fragility** how many labels flip when one threshold moves a notch. Separates the
                            rules that rest on an identity (channel) from those resting on an
                            arbitrary number (lead ≤ 3 days).

**What this does NOT measure.** It is *internal* confidence — how determined a label is by the rule
set. It is not correctness: a booking can be 100% uncontested and still sit in the wrong segment if
the rule itself is wrong. External validity is Stages V1-V4 (`src/validate_*.py`,
`src/detection_power.py`) and, ultimately, SME ground truth.

Run:
    python src/rule_confidence.py    → outputs/rule_confidence/summary.md
"""

from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BOOKING = ROOT / "data" / "interim" / "pal_features_booking.parquet"
REPORT = ROOT / "outputs" / "rule_confidence"

# The 10 branch predicates of the waterfall, in priority order. Must mirror
# `src/features_real.py::build_booking` — if that CASE changes, change this too.
RULES = [
    ("r01_award", "Mabuhay Loyalist", "is_award"),
    ("r02_corp", "Corporate", "(corp_channel OR (any_business AND lead_days <= 7))"),
    ("r03_pilgrim", "Pilgrimage", "pilgrimage"),
    ("r04_seacrew", "OFW/Migrant", "sea_crew"),
    (
        "r05_ofw",
        "OFW/Migrant",
        "(foreign_issue AND is_international AND max_tier <= 4 AND NOT round_trip)",
    ),
    (
        "r06_balik",
        "Balikbayan/VFR",
        "(foreign_issue AND is_international AND max_tier <= 4 AND round_trip)",
    ),
    ("r07_prem", "Premium Bleisure", "(any_premium AND is_international)"),
    ("r08_group", "Family", "is_group"),
    ("r09_last", "Last-Minute", "lead_days <= 3"),
    ("r10_budget", "Budget/Adventure", "(is_domestic AND NOT any_premium)"),
]

# Threshold perturbations. Each moves exactly one arbitrary constant by one notch.
SCENARIOS = [
    ("Last-Minute lead ≤3 → ≤2", {"lm_lead": 2}),
    ("Last-Minute lead ≤3 → ≤4", {"lm_lead": 4}),
    ("Last-Minute lead ≤3 → ≤7", {"lm_lead": 7}),
    ("Corporate lead ≤7 → ≤5", {"corp_lead": 5}),
    ("Corporate lead ≤7 → ≤10", {"corp_lead": 10}),
    ("Value cut tier ≤4 → ≤3", {"tier_cut": 3}),
    ("Value cut tier ≤4 → ≤5", {"tier_cut": 5}),
]


def waterfall(lm_lead: int = 3, corp_lead: int = 7, tier_cut: int = 4) -> str:
    """The Stage F CASE expression with its three arbitrary constants exposed."""
    return f"""
    CASE
        WHEN is_award THEN 'Mabuhay Loyalist'
        WHEN corp_channel OR (any_business AND lead_days <= {corp_lead}) THEN 'Corporate'
        WHEN pilgrimage THEN 'Pilgrimage'
        WHEN sea_crew THEN 'OFW/Migrant'
        WHEN foreign_issue AND is_international AND max_tier <= {tier_cut}
             AND NOT round_trip THEN 'OFW/Migrant'
        WHEN foreign_issue AND is_international AND max_tier <= {tier_cut}
             AND round_trip THEN 'Balikbayan/VFR'
        WHEN any_premium AND is_international THEN 'Premium Bleisure'
        WHEN is_group THEN 'Family'
        WHEN lead_days <= {lm_lead} THEN 'Last-Minute'
        WHEN is_domestic AND NOT any_premium THEN 'Budget/Adventure'
        ELSE 'Unassigned'
    END
    """


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("PRAGMA threads=6")
    con.execute("SET memory_limit='8GB'")
    con.execute("SET preserve_insertion_order=false")
    con.execute(f"CREATE VIEW b AS SELECT * FROM read_parquet('{BOOKING}')")
    # `max_tier` is NULL for award/group/non-revenue fares, so every predicate touching it can be
    # NULL. SQL's CASE treats NULL as not-matched; coalesce here so the *count* agrees with it.
    flags = ",\n           ".join(f"coalesce({e}, FALSE) AS {n}" for n, _s, e in RULES)
    matched = " + ".join(f"coalesce({e}, FALSE)::INT" for _n, _s, e in RULES)
    win_idx = " ".join(f"WHEN {n} THEN {i}" for i, (n, _s, _e) in enumerate(RULES))
    con.execute(f"""
        CREATE TABLE m AS
        SELECT proxy_segment,
               {flags},
               ({matched}) AS n_rules_matched,
               CASE {win_idx} ELSE 99 END AS win_idx
        FROM b
    """)
    return con


def competition(con: duckdb.DuckDBPyConnection) -> list[str]:
    per_seg = con.execute("""
        SELECT proxy_segment,
               count(*) AS bookings,
               round(100.0*avg((n_rules_matched = 1)::INT), 1) AS pct_uncontested,
               round(100.0*avg((n_rules_matched = 2)::INT), 1) AS pct_2_rules,
               round(100.0*avg((n_rules_matched >= 3)::INT), 1) AS pct_3plus,
               round(avg(n_rules_matched), 2) AS mean_rules
        FROM m GROUP BY 1 ORDER BY pct_uncontested DESC
    """).fetchdf()
    overall = con.execute("""
        SELECT round(100.0*avg((n_rules_matched = 1)::INT), 1) AS pct_exactly_1,
               round(100.0*avg((n_rules_matched >= 2)::INT), 1) AS pct_2_or_more,
               round(100.0*avg((n_rules_matched = 0)::INT), 1) AS pct_none
        FROM m
    """).fetchdf()
    return [
        "## 1. Rule competition — how contested is each label?\n",
        "How many of the 10 branch predicates each booking satisfies. **1 = uncontested** · "
        "**2 = the priority order broke a tie** · **3+ = the label is a priority artefact.**\n",
        per_seg.to_markdown(index=False),
        "\n**Overall**\n",
        overall.to_markdown(index=False),
        "\n`Unassigned` matches zero rules by definition — it is a coverage gap, not a tie.\n",
        "\n> Read `Budget/Adventure` at 100% uncontested with care: it is the terminal catch-all, so "
        "'nothing else claimed it' is close to true by construction.\n",
    ]


def runner_up(con: duckdb.DuckDBPyConnection) -> list[str]:
    """What the booking would have been called if its winning rule did not exist."""
    expr = (
        "CASE "
        + " ".join(
            f"WHEN win_idx < {i} AND {n} THEN '{seg}'" for i, (n, seg, _e) in enumerate(RULES)
        )
        + " ELSE 'Unassigned' END"
    )
    df = con.execute(f"""
        WITH r AS (SELECT proxy_segment, {expr} AS runner_up FROM m),
        sizes AS (SELECT proxy_segment, count(*) AS seg_n FROM r GROUP BY 1),
        g AS (
            SELECT proxy_segment, runner_up, count(*) AS bookings
            FROM r
            WHERE runner_up <> 'Unassigned' AND runner_up <> proxy_segment
            GROUP BY 1, 2
        )
        SELECT g.proxy_segment, g.runner_up, g.bookings,
               round(100.0*g.bookings/s.seg_n, 1) AS pct_of_segment
        FROM g JOIN sizes s USING (proxy_segment)
        QUALIFY row_number() OVER (PARTITION BY g.proxy_segment ORDER BY g.bookings DESC) <= 2
        ORDER BY pct_of_segment DESC
    """).fetchdf()
    return [
        "\n## 2. Runner-up — what the booking would be called one priority step lower\n",
        "Top two alternatives per segment. A very high share means the two segments overlap heavily "
        "and the boundary between them is our priority order, not the data.\n",
        df.to_markdown(index=False),
    ]


def fragility(con: duckdb.DuckDBPyConnection) -> list[str]:
    rows = []
    for label, kw in SCENARIOS:
        alt = waterfall(**kw)
        r = (
            con.execute(f"""
            SELECT sum((proxy_segment <> alt)::INT) AS n_flipped,
                   round(100.0*avg((proxy_segment <> alt)::INT), 2) AS pct_flipped
            FROM (SELECT proxy_segment, {alt} AS alt FROM b)
        """)
            .fetchdf()
            .iloc[0]
        )
        rows.append(
            {
                "scenario": label,
                "n_flipped": int(r["n_flipped"]),
                "pct_of_book_flipped": r["pct_flipped"],
            }
        )
        print(f"  {label}: {r['pct_flipped']}%")

    out = [
        "\n\n## 3. Boundary fragility — label flips when one threshold moves a notch\n",
        "Separates rules resting on an **identity** (channel, destination) from rules resting on an "
        "**arbitrary number** (lead ≤ 3 days, tier ≤ 4).\n",
        pd.DataFrame(rows)
        .sort_values("pct_of_book_flipped", ascending=False)
        .to_markdown(index=False),
        "\n\n### Per-segment retention under each perturbation\n",
    ]
    for label, kw in SCENARIOS:
        alt = waterfall(**kw)
        df = con.execute(f"""
            SELECT proxy_segment, round(100.0*avg((proxy_segment = alt)::INT), 2) AS pct_kept
            FROM (SELECT proxy_segment, {alt} AS alt FROM b)
            GROUP BY 1 HAVING pct_kept < 100 ORDER BY pct_kept
        """).fetchdf()
        body = (
            df.to_markdown(index=False)
            if len(df)
            else "_no segment loses a single booking under this move._"
        )
        out += [f"\n**{label}**\n", body]
    return out


def main() -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    con = connect()
    n = con.execute("SELECT count(*) FROM m").fetchone()[0]
    print(f"Bookings: {n:,}")

    lines = [
        "# Rule-confidence diagnostics — the deterministic waterfall\n",
        f"Full population: **{n:,}** bookings, no sampling. Source: "
        "`data/interim/pal_features_booking.parquet`.\n",
        "> **These measure how *determined* a label is by the rule set — not whether it is right.** "
        "A booking can be 100% uncontested and still sit in the wrong segment if the rule itself is "
        "wrong. External validity is Stages V1-V4 and, ultimately, SME ground truth.\n",
    ]
    lines += competition(con)
    lines += runner_up(con)
    lines += fragility(con)

    (REPORT / "summary.md").write_text("\n".join(lines) + "\n")
    print(f"Wrote {REPORT / 'summary.md'}")


if __name__ == "__main__":
    main()
