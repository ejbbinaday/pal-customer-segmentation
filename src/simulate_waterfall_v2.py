"""Simulate the proposed waterfall v2 and report exactly what moves — `docs/waterfall-v2-design.md`.

Design-time tool, not part of the pipeline. It exists so the taxonomy change can be argued with
before it is built: it applies the current (v1) and proposed (v2) waterfalls to the same 22.9M
bookings, reports every segment delta and the provenance of each new segment, and re-checks the
six `enforce` hard rules in `data/constraints/hard_constraints.csv` against the result.

That last check is the point. A first draft of v2 satisfied only 4 of 6 — ordering alone does not
enforce a `cannot_be`, and two rules needed explicit branches. See the design doc §4.

Run:
    python src/simulate_waterfall_v2.py                  # recommended ordering (Family first)
    python src/simulate_waterfall_v2.py outbound-first   # the §7 alternative
"""

import csv
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
BOOKING = ROOT / "data" / "interim" / "pal_features_booking.parquet"
HARD = ROOT / "data" / "constraints" / "hard_constraints.csv"

con = duckdb.connect()
con.execute("PRAGMA threads=6")
con.execute(f"CREATE VIEW b AS SELECT * FROM read_parquet('{BOOKING}')")

# ── current (v1), verbatim from features_real.py ──
V1 = """CASE
  WHEN is_award THEN 'Mabuhay Loyalist'
  WHEN corp_channel OR (any_business AND lead_days <= 7) THEN 'Corporate'
  WHEN pilgrimage THEN 'Pilgrimage'
  WHEN sea_crew THEN 'OFW/Migrant'
  WHEN foreign_issue AND is_international AND max_tier <= 4 AND NOT round_trip THEN 'OFW/Migrant'
  WHEN foreign_issue AND is_international AND max_tier <= 4 AND round_trip THEN 'Balikbayan/VFR'
  WHEN any_premium AND is_international THEN 'Premium Bleisure'
  WHEN is_group THEN 'Family'
  WHEN lead_days <= 3 THEN 'Last-Minute'
  WHEN is_domestic AND NOT any_premium THEN 'Budget/Adventure'
  ELSE 'Unassigned' END"""


# ── proposed (v2). Design rule: INSERT new branches, never reorder existing ones,
#    so every delta is attributable to a new branch rather than to churn.
def v2(family_before_outbound: bool) -> str:
    outbound = (
        "  WHEN NOT foreign_issue AND is_international AND NOT any_premium\n"
        "       THEN 'Outbound International Leisure'\n"
    )
    family = "  WHEN is_group THEN 'Family'\n"
    tail = (family + outbound) if family_before_outbound else (outbound + family)
    return f"""CASE
  WHEN is_award THEN 'Mabuhay Loyalist'
  WHEN corp_channel OR (any_business AND lead_days <= 7) THEN 'Corporate'
  WHEN round_trip AND stay_nights <= 1 AND max_tier >= 4 THEN 'Corporate'
  -- the composite fence (intake doc §5.3): four SME rules independently funnel short-turnaround
  -- premium travel to Corporate. Expressing it once satisfies H10 and H12 together.
  WHEN round_trip AND lead_days <= 3 AND stay_nights <= 3 AND any_premium THEN 'Corporate'
  WHEN is_group AND round_trip AND lead_days >= 45 AND stay_nights BETWEEN 3 AND 7 THEN 'MICE'
  WHEN pilgrimage THEN 'Pilgrimage'
  WHEN sea_crew THEN 'OFW/Migrant'
  WHEN is_international AND round_trip AND stay_nights BETWEEN 90 AND 150 THEN 'Intl. Student'
  WHEN foreign_issue AND is_international AND max_tier <= 4 AND NOT round_trip THEN 'OFW/Migrant'
  -- H08 has no lead-time clause, so the fence above does not cover it: it needs an explicit
  -- exclusion here. Without this, 2,934 bookings violated a `certain` cannot_be rule.
  WHEN foreign_issue AND is_international AND max_tier <= 4 AND round_trip
       AND NOT (stay_nights <= 3 AND any_premium) THEN 'Balikbayan/VFR'
  WHEN any_premium AND round_trip AND lead_days >= 30 AND stay_nights >= 7
       THEN 'Ultra Wealthy Leisure'
  WHEN any_premium AND is_international THEN 'Premium Bleisure'
{tail}  WHEN is_domestic AND NOT any_premium THEN 'Budget/Adventure'
  ELSE 'Unassigned' END"""


fam_first = sys.argv[1] == "family-first" if len(sys.argv) > 1 else True
con.execute(f"""CREATE VIEW s AS SELECT *, {V1} AS v1, {v2(fam_first)} AS v2,
                (lead_days <= 3) AS f_last_minute,
                CASE WHEN max_tier <= 2 THEN 'Budget' WHEN max_tier <= 4 THEN 'Mid'
                     ELSE 'Premium' END AS value_band
             FROM b""")
tot = con.execute("SELECT count(*) FROM s").fetchone()[0]
print(
    f"ordering: {'Family before Outbound' if fam_first else 'Outbound before Family'}   "
    f"({tot:,} bookings)\n"
)
print(f"{'segment':<32}{'v1':>11}{'v2':>11}{'delta':>11}{'%':>8}")
segs = con.execute(
    """SELECT s FROM (SELECT v1 AS s FROM s UNION SELECT v2 FROM s) ORDER BY s"""
).fetchall()
for (seg,) in segs:
    a = con.execute(f"SELECT count(*) FROM s WHERE v1='{seg}'").fetchone()[0]
    z = con.execute(f"SELECT count(*) FROM s WHERE v2='{seg}'").fetchone()[0]
    pct = f"{100 * (z - a) / a:+.0f}%" if a else ("new" if z else "")
    print(f"  {seg:<30}{a:>11,}{z:>11,}{z - a:>+11,}{pct:>8}")

print("\nWhere each NEW segment's population comes from:")
for seg in ("MICE", "Intl. Student", "Ultra Wealthy Leisure", "Outbound International Leisure"):
    rows = con.execute(
        f"SELECT v1, count(*) n FROM s WHERE v2='{seg}' GROUP BY 1 ORDER BY n DESC"
    ).fetchall()
    print(f"  {seg}:")
    for src, n in rows:
        print(f"     from {src:<28}{n:>10,}")

mv = con.execute("SELECT count(*) FROM s WHERE v1 <> v2").fetchone()[0]
print(f"\nBookings whose label changes: {mv:,} ({100 * mv / tot:.1f}%)")
fl = con.execute("SELECT count(*) FROM s WHERE f_last_minute").fetchone()[0]
print(f"Last-minute flag: {fl:,} ({100 * fl / tot:.2f}%)")
print("\nValue band (an attribute, not a segment):")
for band, n in con.execute(
    "SELECT value_band, count(*) FROM s GROUP BY 1 ORDER BY 2 DESC"
).fetchall():
    print(f"  {band:<10}{n:>11,}  {100 * n / tot:5.1f}%")

# ── the check that matters: does v2 satisfy the hard rules it is supposed to enforce? ──
print("\nEnforce-rule verification (data/constraints/hard_constraints.csv):")
bad = 0
for r in csv.DictReader(HARD.open()):
    if r["status"] != "enforce" or not r["condition"].strip():
        continue
    op = "<>" if r["verdict"] == "must_be" else "="
    n = con.execute(
        f"SELECT count(*) FROM s WHERE ({r['condition']}) AND v2 {op} '{r['segments']}'"
    ).fetchone()[0]
    bad += bool(n)
    verb = "must be" if r["verdict"] == "must_be" else "cannot be"
    print(f"  {r['rule_id']}  {verb} {r['segments']:<32}" + ("OK" if not n else f"VIOLATED {n:,}"))
if bad:
    raise SystemExit(
        f"\n{bad} enforce rule(s) violated — the ordering does not implement the contract"
    )
print("  all enforce rules satisfied")
