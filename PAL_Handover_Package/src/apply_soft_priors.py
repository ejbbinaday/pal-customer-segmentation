"""Stage P — make the SME's *tendencies* do work, instead of sitting in a file nothing reads.

The problem this solves
-----------------------
`data/constraints/soft_constraints.csv` holds 21 live tendencies from PAL's revenue managers —
"a long stay issued abroad leans Balikbayan/VFR rather than OFW", "premium plus a 5-10 night stay
leans bleisure rather than corporate". Until now **nothing in the codebase opened that file** except
the format checker, so three-quarters of the SME's contribution could not affect anything. Meanwhile
we spent a validation anchor (`stay_nights`) partly to buy one of those rules.

What it does — and deliberately does not do
-------------------------------------------
For every booking it evaluates every live prior and accumulates a **score per segment**:

    a rule that fires adds  +strength  to `leans_toward`
                        and −strength  to `leans_away_from`
    strength: weak 1 · moderate 2 · strong 3

That yields, per booking: the segment the SMEs' tendencies most favour (`prior_top`), how strongly
(`prior_score`), how clear the call was (`prior_margin` — top minus runner-up), and whether it
**agrees with the waterfall's label**.

⚠️ **It changes no label.** This is a *confidence and disagreement* layer, not a labeller. That is a
deliberate architectural choice, for three reasons:

  1. **A tendency is not a rule.** The whole point of the hard/soft split is that soft constraints
     "tilt ambiguous cases, and tell us which boundaries PAL considers soft" — overriding a label with
     a `moderate` lean would collapse that distinction.
  2. **Disagreement is the finding.** `data/constraints/README.md` states that where a soft constraint
     contradicts the data, "that disagreement is the finding — it gets reported back, not silently
     overridden". This stage produces exactly that report.
  3. **It costs no validation anchor.** A score computed *downstream* of the labels is not a rule
     input, so it does not consume anything from `src/validation_anchors.py`. Promoting it to a
     label-changing layer *would* be an anchor decision, and a separate one.

Where the segments disagree most is where SME labelling effort should go first (`data/labels/`).

Outputs (git-ignored):
    data/interim/pal_soft_priors.parquet   one row per booking: top / score / margin / agreement
    outputs/soft_priors/summary.md         agreement by segment, the most-contested populations

Run:
    python src/apply_soft_priors.py
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import duckdb

from pal_colors import SEG_RENAMED

ROOT = Path(__file__).resolve().parents[1]
BOOKING = ROOT / "data" / "interim" / "pal_features_booking.parquet"
CUSTOMER = ROOT / "data" / "interim" / "pal_features_customer.parquet"
SOFT = ROOT / "data" / "constraints" / "soft_constraints.csv"
OUT = ROOT / "data" / "interim" / "pal_soft_priors.parquet"
REPORT = ROOT / "outputs" / "soft_priors"

# Only these statuses are live. `withdrawn` protects a validation anchor, `too_thin` fires on too
# little volume to inform anything, `unconfirmed` is our own guess with no SME behind it, and
# `demoted_from_hard` rules are sweeping vetoes (63% and 33% of the book) that would swamp the score.
LIVE_STATUS = frozenset({"prior", "confirmed"})

STRENGTH = {"weak": 1, "moderate": 2, "strong": 3}

# Segment tokens that are not segments. `Last-Minute (flag)` is a booking attribute now, so a lean
# toward it says nothing about which segment the booking belongs to.
NOT_A_SEGMENT = frozenset({"Last-Minute (flag)", ""})

SQL_WORDS = frozenset({"AND", "OR", "NOT", "IN", "BETWEEN", "IS", "NULL", "TRUE", "FALSE", "LIKE"})
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
STR_LITERAL = re.compile(r"'[^']*'")


def load_priors() -> list[dict]:
    """Live priors only, each with a numeric weight and at least one real segment to point at."""
    out = []
    for r in csv.DictReader(SOFT.open()):
        if r["status"] not in LIVE_STATUS or not r["condition"].strip():
            continue
        toward = r["leans_toward"] if r["leans_toward"] not in NOT_A_SEGMENT else ""
        away = r["leans_away_from"] if r["leans_away_from"] not in NOT_A_SEGMENT else ""
        if not toward and not away:
            continue  # a rule that only tilts toward a flag cannot move a segment score
        out.append(
            {
                "id": r["rule_id"],
                "cond": r["condition"].strip(),
                "toward": toward,
                "away": away,
                "w": STRENGTH[r["strength"]],
            }
        )
    return out


def segments(priors: list[dict]) -> list[str]:
    s = {p["toward"] for p in priors} | {p["away"] for p in priors}
    return sorted(s - {""})


def score_sql(priors: list[dict], seg: str) -> str:
    """Signed sum of the priors that mention `seg`. Zero terms → literal 0, not an empty SUM."""
    terms = []
    for p in priors:
        if p["toward"] == seg:
            terms.append(f"CASE WHEN {p['cond']} THEN {p['w']} ELSE 0 END")
        elif p["away"] == seg:
            terms.append(f"CASE WHEN {p['cond']} THEN {-p['w']} ELSE 0 END")
    return " + ".join(terms) if terms else "0"


def needs_customer(priors: list[dict], cust_only: set[str]) -> bool:
    blob = " ".join(p["cond"] for p in priors)
    idents = {t for t in IDENT.findall(STR_LITERAL.sub("''", blob)) if t.upper() not in SQL_WORDS}
    return bool(idents & cust_only)


def main() -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("PRAGMA threads=6")
    con.execute("SET preserve_insertion_order=false")

    bcols = {
        r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{BOOKING}')").fetchall()
    }
    ccols = {
        r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{CUSTOMER}')").fetchall()
    }

    priors = load_priors()
    segs = segments(priors)
    print(f"{len(priors)} live priors over {len(segs)} segments")

    src = f"read_parquet('{BOOKING}')"
    if needs_customer(priors, ccols - bcols):
        src = (
            f"read_parquet('{BOOKING}') b "
            f"LEFT JOIN read_parquet('{CUSTOMER}') c USING (customer_id)"
        )

    # a list of STRUCTs, not parallel lists: DuckDB lists must be homogeneous, and struct
    # ordering is field-order, so {sc, seg} sorts by score then name — deterministic on ties.
    structs = ", ".join(f"{{'sc': ({score_sql(priors, s)})::INT, 'seg': '{s}'}}" for s in segs)
    # retired labels must be mapped to their current names BEFORE comparing, or a rename reads as a
    # disagreement (see pal_colors.SEG_RENAMED)
    rename_sql = "proxy_segment"
    for old_name, new_name in SEG_RENAMED.items():
        rename_sql = f"replace({rename_sql}, '{old_name}', '{new_name}')"
    con.execute(f"""
        CREATE TABLE sp AS
        WITH r AS (
            SELECT customer_id, issue_date, proxy_segment,
                   list_sort([{structs}], 'DESC') AS ranked
            FROM {src}
        )
        SELECT customer_id, issue_date, {rename_sql} AS proxy_segment,
               -- ⚠️ a tie is not a call. When the top two segments score equally the tendencies are
               -- genuinely ambiguous, which is what PAL asked us to report rather than forcing a
               -- confident label — so prior_top is NULL rather than the alphabetical winner.
               CASE WHEN ranked[1].sc > ranked[2].sc THEN ranked[1].seg END AS prior_top,
               ranked[1].sc                             AS prior_score,
               (ranked[1].sc - ranked[2].sc)::INT        AS prior_margin,
               CASE WHEN ranked[1].sc > ranked[2].sc
                    THEN ranked[1].seg = {rename_sql} END AS prior_agrees
        FROM r
    """)
    n = con.execute("SELECT count(*) FROM sp").fetchone()[0]
    con.execute(f"COPY sp TO '{OUT}' (FORMAT PARQUET, COMPRESSION zstd)")

    # ── report ────────────────────────────────────────────────────────────────
    # A tie is not a call, so it must not sit in the denominator: a booking where two segments score
    # equally tells us nothing about agreement. `called` is margin > 0 only.
    called = con.execute("SELECT count(*) FROM sp WHERE prior_margin > 0").fetchone()[0]
    silent = con.execute(
        "SELECT count(*) FROM sp WHERE prior_score = 0 AND prior_margin = 0"
    ).fetchone()[0]
    agree = con.execute("SELECT count(*) FROM sp WHERE prior_agrees").fetchone()[0]
    L = [
        "# Stage P — SME tendencies scored against the waterfall's labels\n",
        f"- Bookings scored: **{n:,}**",
        f"- Priors applied: **{len(priors)}** live rules over **{len(segs)}** segments "
        f"(`prior`/`confirmed` only — see the module docstring for what is excluded)",
        f"- **No prior fires at all** on **{silent:,}** ({100 * silent / n:.1f}%) — the tendencies are "
        "simply silent there, which is itself a coverage finding: PAL's rules say nothing about "
        "two-fifths of the book",
        f"- **The tendencies make an actual call** (top beats runner-up) on **{called:,}** "
        f"({100 * called / n:.1f}%). Everywhere else they tie, and a tie is reported as ambiguous "
        "rather than resolved alphabetically",
        f"- **Where they do call it, they agree with the waterfall on {100 * agree / called:.1f}%** "
        f"({agree:,} of {called:,})\n",
        "⚠️ **No label is changed by this stage.** Agreement is a diagnostic; disagreement is a "
        "finding to report back, per `data/constraints/README.md`.\n",
        "## Agreement by waterfall segment\n",
        "Low agreement is not necessarily an error — it marks a boundary PAL's own experts describe "
        "differently from our rules, and therefore **where SME labelling effort is worth most**.\n",
        "| waterfall segment | bookings | calls made | agrees | agreement | median margin |",
        "|---|---|---|---|---|---|",
    ]
    for seg, tot, fired, ok, med in con.execute("""
        SELECT proxy_segment, count(*),
               count(*) FILTER (WHERE prior_margin > 0),
               count(*) FILTER (WHERE prior_agrees),
               median(prior_margin)
        FROM sp GROUP BY 1 ORDER BY 2 DESC
    """).fetchall():
        rate = f"{100 * ok / fired:.1f}%" if fired else "—"
        L.append(f"| {seg} | {tot:,} | {fired:,} | {ok:,} | {rate} | {med:.0f} |")

    L += [
        "\n## Where the tendencies most disagree with the label\n",
        "The waterfall says one thing, the weight of SME opinion says another. **These are the "
        "populations to put in front of an SME first** — a hand-labelled sample here is worth more "
        "than one drawn at random.\n",
        "| waterfall says | tendencies say | bookings | median margin |",
        "|---|---|---|---|",
    ]
    for a, b, c, m in con.execute("""
        SELECT proxy_segment, prior_top, count(*) n, median(prior_margin)
        FROM sp WHERE NOT prior_agrees AND prior_margin > 0
        GROUP BY 1, 2 ORDER BY n DESC LIMIT 15
    """).fetchall():
        L.append(f"| {a} | **{b}** | {c:,} | {m:.0f} |")

    L += [
        "\n## Confidence distribution\n",
        "`prior_margin` is the gap between the top segment and the runner-up. **A margin of 0 means "
        "the tendencies split evenly** — the honest reading is 'ambiguous', which is what PAL asked us "
        "to report rather than forcing a confident label.\n",
        "| margin | bookings | share |",
        "|---|---|---|",
    ]
    for m, c in con.execute("""
        SELECT least(prior_margin, 6) m, count(*) FROM sp GROUP BY 1 ORDER BY 1
    """).fetchall():
        label = "0 (ambiguous)" if m == 0 else ("6+" if m == 6 else str(m))
        L.append(f"| {label} | {c:,} | {100 * c / n:.1f}% |")

    (REPORT / "summary.md").write_text("\n".join(L) + "\n")
    print(f"scored {n:,} bookings · {called:,} calls made · agreement {100 * agree / called:.1f}%")
    print(f"Wrote {OUT.name} and {REPORT / 'summary.md'}")


if __name__ == "__main__":
    main()
