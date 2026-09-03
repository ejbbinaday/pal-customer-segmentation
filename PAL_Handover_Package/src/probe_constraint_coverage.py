"""Usability triage for the RM-Domestic constraint sheet (39 new rules).

"Can we use this rule?" is three questions, not one:

  1. **Evaluable?**  Do we hold every field it names? A rule citing PNR party size
     is dead on arrival — we do not have it and cannot derive it.
  2. **Evaluable on how much of the book?**  A rule conditioning on stay length can
     only ever fire on round trips (42.7%). A rule conditioning on age can only fire
     on international bookings, where age is populated. This is the number that gets
     missed: a rule can be perfectly sound and still be *inapplicable* to most of the
     population it was written for.
  3. **Does it fire, and on enough volume to matter?**  A rule matching 400 bookings
     out of 22.9M is a curiosity, not a segmentation input.

Reports all three per rule, plus the pairwise contradictions between `must_be`/
`cannot_be` verdicts that would make the rule set inconsistent if enforced as written.

Output: `outputs/constraint_coverage/summary.md` + `rules.csv`.

Source workbook: `wishlist/PALxMAIDA_Constraints&Wishlist.xlsx`
Companion analysis: `docs/sme-constraints-intake.md`
"""

from __future__ import annotations

import csv
from pathlib import Path

from probe_stay_length import build, connect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "constraint_coverage"

# Farebrand ladder (src/clean_real.py): 1 Supersaver · 2 Saver · 3 Value · 4 Econ Flex
#                                       5 Prem Econ · 6 Business Value · 7 Business Flex
GULF = "('DXB','RUH','DMM','DOH')"
EAST_ASIA = "('HKG','TPE')"
TOURIST = "('BKK','SIN','ICN','NRT')"
CATHOLIC = "('FCO','TLV','CDG','LIS')"
ISLAMIC = "('JED','MED')"
DOM_LEISURE = "('MPH','PPS','USU','IAO')"
PREM_HOLIDAY = "('HNL','SYD','CTS','MEL')"
MICE_HUB = "('SIN','NRT','BKK')"

RT = "round_trip AND stay_gap IS NOT NULL"  # stay length only exists here

# (row, segment, verdict, sql | None, scope-note, blocked-reason | None)
RULES: list[tuple] = [
    (
        14,
        "VFR",
        "leans",
        f"{RT} AND foreign_issue AND stay_gap >= 14 AND max_tier <= 4",
        "round trips",
        None,
    ),
    (
        15,
        "VFR",
        "leans",
        f"{RT} AND lead_days <= 7 AND max_tier <= 4 AND stay_gap >= 7",
        "round trips",
        None,
    ),
    (
        16,
        "VFR",
        "leans",
        f"{RT} AND dep_month IN (11,12,1) AND stay_gap >= 21",
        "round trips",
        None,
    ),
    (17, "VFR", "cannot", f"{RT} AND stay_gap <= 3 AND any_premium", "round trips", None),
    (
        18,
        "OFW",
        "leans",
        f"NOT round_trip AND turn_dest IN {GULF[:-1]},'HKG','TPE') AND max_tier <= 4 AND age_known AND age BETWEEN 21 AND 60",
        "one-ways w/ known age",
        None,
    ),
    (19, "OFW", "away", f"dep_month IN (4,5) AND turn_dest IN {TOURIST}", "all", None),
    (
        20,
        "OFW",
        "leans",
        "sea_crew AND connecting",
        "all",
        "OAL leg unverifiable — OperatingCarrierCode is constant 'PR' in the extract",
    ),
    # ⚠ row 21 written as `TripOD IN (...)` i.e. MNL→Gulf. But the population it describes —
    # a worker based abroad flying home — travels Gulf→MNL. Matching the sheet's direction
    # literally costs 20× the volume. Corrected to a direction-agnostic corridor match; the
    # literal reading is reported alongside in §"Direction".
    (
        21,
        "OFW",
        "leans",
        f"{RT} AND stay_gap BETWEEN 28 AND 45 AND foreign_issue AND corridor IN ('gulf_labour','east_asia_labour')",
        "round trips",
        None,
    ),
    (
        22,
        "Pilgrimage",
        "leans",
        f"turn_dest IN {CATHOLIC} AND is_group AND age_known AND age >= 50",
        "intl w/ known age",
        None,
    ),
    (23, "Pilgrimage", "leans", "dep_month IN (3,4) AND turn_dest IN ('FCO','TLV')", "all", None),
    (
        24,
        "Pilgrimage",
        "cannot",
        f"{RT} AND any_j AND stay_gap <= 4 AND turn_dest IN ('JED','MED','TLV')",
        "round trips",
        None,
    ),
    (
        25,
        "Pilgrimage",
        "leans",
        f"{RT} AND lead_days >= 90 AND max_tier IN (2,3) AND turn_dest IN {ISLAMIC[:-1]},'FCO','TLV','CDG','LIS')",
        "round trips",
        None,
    ),
    (26, "Leisure", "leans", f"{RT} AND lead_days >= 60 AND max_tier = 1", "round trips", None),
    (
        27,
        "Leisure",
        "leans",
        f"{RT} AND stay_gap BETWEEN 2 AND 4 AND turn_dest IN {DOM_LEISURE} AND max_tier <= 3",
        "round trips",
        None,
    ),
    (
        28,
        "Leisure",
        "away",
        f"{RT} AND dep_month NOT IN (3,4,5,12) AND stay_gap >= 21",
        "round trips",
        None,
    ),
    (
        29,
        "Prem Bleisure",
        "leans",
        f"{RT} AND any_premium AND stay_gap BETWEEN 5 AND 14 AND turn_dest IN {PREM_HOLIDAY}",
        "round trips",
        None,
    ),
    (
        30,
        "Prem Bleisure",
        "leans",
        f"{RT} AND any_premium AND stay_gap BETWEEN 5 AND 10",
        "round trips",
        None,
    ),
    (31, "Prem Bleisure", "leans", "any_premium AND is_group", "all", None),
    (32, "Prem Bleisure", "leans", "any_premium AND lead_days BETWEEN 14 AND 45", "all", None),
    (
        33,
        "Prem Bleisure",
        "cannot",
        f"{RT} AND lead_days <= 3 AND stay_gap <= 3 AND any_j",
        "round trips",
        None,
    ),
    (34, "Prem Bleisure", "cannot", "max_tier <= 2", "all", None),
    (35, "Corporate", "MUST", f"{RT} AND stay_gap <= 1 AND max_tier >= 4", "round trips", None),
    (
        36,
        "Corporate",
        "leans",
        f"{RT} AND lead_days <= 7 AND stay_gap BETWEEN 2 AND 4 AND NOT is_group AND any_premium",
        "round trips",
        None,
    ),
    (
        37,
        "Corporate",
        "leans",
        f"{RT} AND lead_days <= 14 AND stay_gap BETWEEN 2 AND 4 AND max_tier = 4",
        "round trips",
        None,
    ),
    (38, "Corporate", "cannot", f"{RT} AND stay_gap >= 8", "round trips", None),
    (39, "Corporate", "away", f"{RT} AND dep_dow IN (0,6) AND stay_gap >= 3", "round trips", None),
    (
        40,
        "Last-Min (Distressed)",
        "leans",
        "NOT round_trip AND lead_days <= 2 AND max_tier IN (3,4)",
        "one-ways",
        None,
    ),
    (
        41,
        "Last-Min (Sp. Group)",
        "leans",
        f"{RT} AND lead_days <= 5 AND is_group",
        "round trips",
        None,
    ),
    (
        42,
        "Last-Min (Weekender)",
        "leans",
        f"{RT} AND lead_days <= 3 AND stay_gap BETWEEN 2 AND 4 AND dep_dow IN (5,6)",
        "round trips",
        None,
    ),
    (
        43,
        "Last-Minute",
        "cannot",
        f"{RT} AND lead_days <= 3 AND stay_gap <= 3 AND any_premium",
        "round trips",
        None,
    ),
    (
        44,
        "MICE",
        "leans",
        f"{RT} AND is_group AND lead_days >= 45 AND stay_gap BETWEEN 3 AND 7",
        "round trips",
        None,
    ),
    (
        45,
        "MICE",
        "leans",
        f"is_group AND max_tier IN (3,4) AND turn_dest IN {MICE_HUB}",
        "all",
        None,
    ),
    (46, "MICE", "cannot", None, "—", "needs PNR party size; sectoral pax count is always 1"),
    (
        47,
        "Ultra Wealthy",
        "leans",
        f"{RT} AND any_premium AND lead_days >= 30 AND stay_gap >= 7",
        "round trips",
        None,
    ),
    (48, "Ultra Wealthy", "leans", "any_premium AND is_group AND round_trip", "all", None),
    (
        49,
        "Ultra Wealthy",
        "cannot",
        f"{RT} AND lead_days <= 5 AND stay_gap <= 3",
        "round trips",
        None,
    ),
    (
        50,
        "Intl. Student",
        "leans",
        f"{RT} AND stay_gap BETWEEN 90 AND 150 AND dep_month IN (1,5,8,9)",
        "round trips",
        None,
    ),
    (
        51,
        "Intl. Student",
        "leans",
        f"{RT} AND age_known AND age BETWEEN 18 AND 26 AND stay_gap >= 90",
        "round trips w/ known age",
        None,
    ),
    (52, "Intl. Student", "cannot", "sea_crew", "all", None),
]

# Scope denominators — "of the bookings this rule *can* be evaluated on"
SCOPES = {
    "all": "TRUE",
    "round trips": RT,
    "one-ways": "NOT round_trip",
    "one-ways w/ known age": "NOT round_trip AND age_known",
    "intl w/ known age": "is_international AND age_known",
    "round trips w/ known age": f"{RT} AND age_known",
    "—": "TRUE",
}

# Hard verdicts that would contradict each other if both enforced on the same booking.
CONTRADICTIONS = [
    (
        "35 Corporate MUST_BE vs 43/33 Last-Min/Bleisure CANNOT_BE",
        f"{RT} AND stay_gap <= 1 AND max_tier >= 4 AND lead_days <= 3 AND any_premium",
        "compatible by design — both funnel to Corporate. Counted to confirm.",
    ),
    (
        "35 Corporate MUST_BE vs 49 Ultra-Wealthy CANNOT_BE",
        f"{RT} AND stay_gap <= 1 AND max_tier >= 4 AND lead_days <= 5",
        "compatible — both exclude the same population from leisure.",
    ),
    (
        "35 Corporate MUST_BE vs 38 Corporate CANNOT_BE",
        f"{RT} AND stay_gap <= 1 AND max_tier >= 4 AND stay_gap >= 8",
        "must be 0 — a segment cannot both require and forbid the same booking.",
    ),
    (
        "⚠ 35 Corporate MUST_BE vs 17 VFR CANNOT_BE",
        f"{RT} AND stay_gap <= 1 AND max_tier >= 4 AND stay_gap <= 3 AND any_premium",
        "compatible — VFR excluded, Corporate asserted.",
    ),
    (
        "⚠⚠ 9 Family MUST_BE(group) vs every other group claim",
        "is_group",
        "row 9 is `must_be` — this entire population is claimed by Family, pre-empting rows 22/31/41/44/45/48.",
    ),
    (
        "⚠⚠ 47 Ultra-Wealthy vs 30 Prem-Bleisure — undecidable overlap",
        f"{RT} AND any_premium AND lead_days >= 30 AND stay_gap BETWEEN 7 AND 10",
        "both leans fire; no tie-break given (see intake §5.2).",
    ),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "tmp").mkdir(exist_ok=True)
    con = connect()
    build(con)

    total = con.execute("SELECT count(*) FROM bkl").fetchone()[0]

    L = [
        "# Usability triage — 39 SME constraints from RM Domestic",
        "",
        f"Population: **{total:,} bookings** (`data/interim/pal_clean`, same grain as the model).",
        "",
        "- **scope** — the sub-population the rule can even be evaluated on. Rules citing stay",
        "  length are undefined for one-ways; rules citing age need international bookings.",
        "- **fires** — bookings matching the condition.",
        "- **% of scope** — hit rate within the population the rule can address.",
        "- **% of book** — the number that decides whether it is worth encoding at all.",
        "",
        "| row | segment | verdict | scope | scope size | fires | % of scope | % of book |",
        "|---|---|---|---|---|---|---|---|",
    ]

    out_rows = []
    blocked = []
    for row, seg, verdict, sql, scope, block in RULES:
        if sql is None:
            blocked.append((row, seg, block))
            L.append(f"| {row} | {seg} | {verdict} | — | — | **BLOCKED** | — | — |")
            out_rows.append(
                dict(
                    row=row,
                    segment=seg,
                    verdict=verdict,
                    scope=scope,
                    scope_n=0,
                    fires=0,
                    pct_scope=None,
                    pct_book=None,
                    status="blocked",
                    note=block,
                )
            )
            continue
        sn = con.execute(f"SELECT count(*) FROM bkl WHERE {SCOPES[scope]}").fetchone()[0]
        n = con.execute(f"SELECT count(*) FROM bkl WHERE {sql}").fetchone()[0]
        pcs, pcb = 100 * n / sn if sn else 0, 100 * n / total
        flag = " ⚠" if pcb < 0.05 else ""
        L.append(
            f"| {row} | {seg} | {verdict} | {scope} | {sn:,} | {n:,}{flag} | "
            f"{pcs:.2f}% | {pcb:.3f}% |"
        )
        out_rows.append(
            dict(
                row=row,
                segment=seg,
                verdict=verdict,
                scope=scope,
                scope_n=sn,
                fires=n,
                pct_scope=round(pcs, 3),
                pct_book=round(pcb, 4),
                status="too_small" if pcb < 0.05 else "usable",
                note=block or "",
            )
        )

    L += ["", "⚠ = fires on under 0.05% of the book (~11k bookings) — too thin to act on.", ""]

    # ── scope loss ────────────────────────────────────────────────────────────
    n_rt = con.execute(f"SELECT count(*) FROM bkl WHERE {RT}").fetchone()[0]
    n_age = con.execute("SELECT count(*) FROM bkl WHERE age_known").fetchone()[0]
    n_dom_age = con.execute("SELECT count(*) FROM bkl WHERE is_domestic AND age_known").fetchone()[
        0
    ]
    n_dom = con.execute("SELECT count(*) FROM bkl WHERE is_domestic").fetchone()[0]
    need_stay = sum(1 for r in RULES if r[3] and "stay_gap" in r[3])
    need_age = sum(1 for r in RULES if r[3] and "age" in r[3])
    L += [
        "## The scope ceiling nobody wrote down",
        "",
        f"- **{need_stay} of 39 rules cite stay length.** Stay length exists only for round trips: "
        f"**{n_rt:,} bookings, {100 * n_rt / total:.1f}% of the book.** Those rules are structurally "
        "silent on the other 57%.",
        f"- **{need_age} rules cite age.** `age_known` on **{n_age:,}** ({100 * n_age / total:.1f}%) — "
        f"and on domestic bookings only **{n_dom_age:,}** of {n_dom:,} "
        f"(**{100 * n_dom_age / n_dom:.2f}%** of domestic). Age is an international-only field, so "
        "**every age rule is dead for domestic travel.**",
        "",
    ]

    # ── do the named routes carry traffic? ───────────────────────────────────
    L += [
        "## Do the routes the rules name actually carry traffic?",
        "",
        "Trip endpoints (either direction), counted across all bookings. A rule naming a",
        "route PAL barely serves cannot do work however sound its logic.",
        "",
        "| theme | airports | trip endpoints | verdict |",
        "|---|---|---|---|",
    ]
    themes = [
        ("Gulf labour", GULF),
        ("East-Asia 'labour'", EAST_ASIA),
        ("Asian tourist hub", TOURIST),
        ("Islamic pilgrimage", ISLAMIC),
        ("Catholic pilgrimage", CATHOLIC),
        ("Domestic leisure", DOM_LEISURE),
        ("Premium holiday", PREM_HOLIDAY),
    ]
    for name, codes in themes:
        n = con.execute(
            f"""SELECT count(*) FROM (SELECT turn_dest AS d FROM bkl
                UNION ALL SELECT dest_last FROM bkl) WHERE d IN {codes}"""
        ).fetchone()[0]
        verdict = (
            "✅ substantial"
            if n > 200_000
            else "⚠️ thin"
            if n > 30_000
            else "❌ too small to act on"
        )
        L.append(f"| {name} | {codes.strip('()')} | {n:,} | {verdict} |")
    L.append("")

    # ── direction ────────────────────────────────────────────────────────────
    gulf_dir = con.execute(
        """SELECT sum((origin_first = 'MNL')::INT), sum((origin_first <> 'MNL')::INT)
           FROM bkl WHERE round_trip AND corridor = 'gulf_labour'"""
    ).fetchone()
    lit = con.execute(
        f"""SELECT count(*) FROM bkl WHERE {RT} AND stay_gap BETWEEN 28 AND 45
            AND foreign_issue AND turn_dest IN {GULF[:-1]},'HKG','TPE')"""
    ).fetchone()[0]
    fixed = con.execute(
        f"""SELECT count(*) FROM bkl WHERE {RT} AND stay_gap BETWEEN 28 AND 45
            AND foreign_issue AND corridor IN ('gulf_labour','east_asia_labour')"""
    ).fetchone()[0]
    L += [
        "## ⚠️ Direction — the sheet's `TripOD` notation is backwards for its own population",
        "",
        f"Gulf round trips starting in **Manila: {gulf_dir[0]:,}**. Starting in the **Gulf: "
        f"{gulf_dir[1]:,}** — {gulf_dir[1] / gulf_dir[0]:.1f}× more. A worker based in Riyadh flying",
        "home has `TripOD = RUHMNL`, not `MNLRUH`. Every rule about workers *coming home* that",
        "names `MNLxxx` therefore matches the wrong direction.",
        "",
        f"- Row 21 read literally (`TripOD = MNL→Gulf`): **{lit:,}** bookings",
        f"- Row 21 direction-agnostic: **{fixed:,}** bookings — **{fixed / lit:.0f}× more**",
        "",
        "Transcribing the sheet verbatim would have silently gutted its single best rule.",
        "",
    ]

    # ── contradictions ────────────────────────────────────────────────────────
    L += [
        "## Hard-verdict interactions",
        "",
        "| interaction | bookings | reading |",
        "|---|---|---|",
    ]
    for name, sql, note in CONTRADICTIONS:
        n = con.execute(f"SELECT count(*) FROM bkl WHERE {sql}").fetchone()[0]
        L.append(f"| {name} | {n:,} | {note} |")
    L.append("")

    if blocked:
        L += ["## Cannot be evaluated at all", ""]
        L += [f"- **Row {r} ({s})** — {b}" for r, s, b in blocked]
        L.append("")

    with open(OUT / "rules.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    (OUT / "summary.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
