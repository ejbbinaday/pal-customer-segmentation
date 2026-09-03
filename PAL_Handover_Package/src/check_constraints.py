"""Validate `data/constraints/*.csv` against the real feature table.

The constraint files are hand-authored — SMEs and we both edit them — so nothing guarantees a
`condition` still parses, still names real columns, or still fires on the volume its `fires` column
claims. A rule that silently stopped matching anything is worse than a missing rule: it reads as
covered. This script is the guard.

Checks per row:
  • schema     — expected columns present, `rule_id` unique across both files
  • vocabulary — every identifier in `condition` is a real column of pal_features_booking.parquet
  • executes   — DuckDB can evaluate the condition (catches typos and bad operators)
  • fires      — recorded count matches the live count, so a stale number cannot pass unnoticed
  • enum       — verdict / strength / status values are from the allowed sets

Rows with an empty `condition` are placeholders (unanswered SME asks, blocked rules) and are
skipped for the last three checks but still schema- and enum-checked.

Exit code is non-zero if anything fails, so this is usable as a pre-commit or CI gate.

Run:
    python src/check_constraints.py
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
BOOKING = ROOT / "data" / "interim" / "pal_features_booking.parquet"
CUSTOMER = ROOT / "data" / "interim" / "pal_features_customer.parquet"
HARD = ROOT / "data" / "constraints" / "hard_constraints.csv"
SOFT = ROOT / "data" / "constraints" / "soft_constraints.csv"

HARD_COLS = [
    "rule_id",
    "condition",
    "verdict",
    "segments",
    "owner",
    "confidence",
    "status",
    "scope",
    "fires",
    "sme_row",
    "notes",
]
SOFT_COLS = [
    "rule_id",
    "condition",
    "leans_toward",
    "leans_away_from",
    "strength",
    "owner",
    "status",
    "scope",
    "fires",
    "sme_row",
    "notes",
]

VERDICTS = {"must_be", "cannot_be", "narrow_to"}
STRENGTHS = {"weak", "moderate", "strong"}
CONFIDENCES = {"certain", "likely", "moderate"}  # moderate only on rows marked `demoted`
STATUSES = {
    "enforce",  # certain + evaluable + fires → auto-enforce
    "test",  # likely → check against data, return to SME if contradicted
    "prior",  # soft tilt, usable now
    "confirmed",  # our seed, SME agreed
    "unconfirmed",  # our seed, SME did not respond
    "partial",  # transcribed with part of the condition dropped (unevaluable)
    "contested",  # multiple segments claim the same predicate
    "demoted",  # hard verdict at soft confidence → moved to the soft file
    "demoted_from_hard",  # the soft-file counterpart of `demoted`
    "query",  # blocked on an SME/PAL decision
    "too_thin",  # evaluable but fires on too little volume to act on
    "blocked",  # not evaluable at all
    "unanswered",  # placeholder — SME ask came back empty
    "withdrawn",  # deliberately set aside (see notes); kept for the audit trail, never enforced
}

# A withdrawn rule is inert, so the volume/status consistency checks below do not apply to it.
INERT = {"withdrawn", "blocked", "unanswered", "too_thin", "query", "demoted", "contested"}

# SQL keywords and literals that appear in conditions but are not column names
SQL_WORDS = {
    "AND",
    "OR",
    "NOT",
    "IN",
    "BETWEEN",
    "IS",
    "NULL",
    "TRUE",
    "FALSE",
    "LIKE",
    "CASE",
    "WHEN",
    "THEN",
    "ELSE",
    "END",
}
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# Single-quoted string literals must be stripped before looking for column names, or every
# value ('Sea Crew', 'Middle East', 'gulf_labour') is misread as an identifier.
STR_LITERAL = re.compile(r"'[^']*'")

# Volume below which a rule is not worth acting on: 0.05% of the book (~11k bookings)
THIN_THRESHOLD = 11_000


def columns(con: duckdb.DuckDBPyConnection, path: Path) -> set[str]:
    return {r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{path}')").fetchall()}


def relation(cond_cols: set[str], cust_cols: set[str]) -> str:
    """Booking grain by default; join the customer rollup only if the condition needs it.

    Some rules are written at customer grain (`n_bookings`). Evaluating them needs the join, but
    paying for it on every rule would be wasteful, so it is conditional.
    """
    if cond_cols & cust_cols:
        return (
            f"read_parquet('{BOOKING}') b "
            f"LEFT JOIN read_parquet('{CUSTOMER}') c USING (customer_id)"
        )
    return f"read_parquet('{BOOKING}')"


def check_file(
    con: duckdb.DuckDBPyConnection,
    path: Path,
    expected: list[str],
    cols: set[str],
    cust_only: set[str],
) -> tuple[list[str], list[str], set[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    with path.open() as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return [f"{path.name}: no rows"], [], set()

    got = list(rows[0].keys())
    if got != expected:
        errors.append(f"{path.name}: columns are {got}, expected {expected}")
        return errors, warnings, set()

    ids: set[str] = set()
    for r in rows:
        rid = r["rule_id"]
        tag = f"{path.name}:{rid}"
        if rid in ids:
            errors.append(f"{tag}: duplicate rule_id")
        ids.add(rid)

        if r["status"] not in STATUSES:
            errors.append(f"{tag}: status '{r['status']}' not in {sorted(STATUSES)}")
        if "verdict" in r and r["verdict"] and r["verdict"] not in VERDICTS:
            errors.append(f"{tag}: verdict '{r['verdict']}' not in {sorted(VERDICTS)}")
        if r.get("confidence") and r["confidence"] not in CONFIDENCES:
            errors.append(f"{tag}: confidence '{r['confidence']}' not in {sorted(CONFIDENCES)}")
        if r.get("strength") and r["strength"] not in STRENGTHS:
            errors.append(f"{tag}: strength '{r['strength']}' not in {sorted(STRENGTHS)}")
        if not r["notes"].strip():
            errors.append(f"{tag}: empty notes — the *why* is the part that survives a revision")

        cond = r["condition"].strip()
        if not cond:
            # `withdrawn` joins these because a placeholder that never had a condition can still be
            # withdrawn — S42 (Digital Nomad) was an unanswered ask that PAL then deleted outright.
            if r["status"] not in {"blocked", "unanswered", "withdrawn"}:
                errors.append(f"{tag}: empty condition but status is '{r['status']}'")
            continue

        bare = STR_LITERAL.sub("''", cond)  # drop literal values before hunting for columns
        idents = {t for t in IDENT.findall(bare) if t.upper() not in SQL_WORDS}
        unknown = sorted(t for t in idents if t not in cols)
        if unknown:
            errors.append(f"{tag}: condition names non-existent columns {unknown}")
            continue

        try:
            n = con.execute(
                f"SELECT count(*) FROM {relation(idents, cust_only)} WHERE {cond}"
            ).fetchone()[0]
        except Exception as e:  # noqa: BLE001 — report any DuckDB parse/type failure verbatim
            errors.append(f"{tag}: condition failed to execute — {type(e).__name__}: {e}")
            continue

        recorded = r["fires"].strip()
        if recorded:
            if int(recorded) != n:
                errors.append(f"{tag}: fires recorded {int(recorded):,} but live count is {n:,}")
        else:
            warnings.append(f"{tag}: no recorded `fires` (live: {n:,})")

        if r["status"] in {"enforce", "prior"} and n < THIN_THRESHOLD:
            errors.append(
                f"{tag}: status '{r['status']}' but fires on only {n:,} "
                f"(< {THIN_THRESHOLD:,}) — should be 'too_thin'"
            )
        if r["status"] == "too_thin" and n >= THIN_THRESHOLD:
            errors.append(f"{tag}: marked 'too_thin' but fires on {n:,} — promote it")
        # decision 1 (17 Aug 2026): `dep_month` is retained as a validation anchor, so no ACTIVE
        # rule may read it. Withdrawn rules keep their condition for the audit trail, hence the
        # status check rather than a blanket ban.
        if "dep_month" in idents and r["status"] not in INERT:
            errors.append(
                f"{tag}: active rule (status '{r['status']}') reads `dep_month`, which is a "
                "reserved validation anchor — withdraw the rule or drop the clause"
            )

    return errors, warnings, ids


def main() -> int:
    con = duckdb.connect()
    con.execute("PRAGMA threads=6")
    bcols = columns(con, BOOKING)
    ccols = columns(con, CUSTOMER)
    cols = bcols | ccols
    cust_only = ccols - bcols  # names that force the customer join

    e1, w1, ids1 = check_file(con, HARD, HARD_COLS, cols, cust_only)
    e2, w2, ids2 = check_file(con, SOFT, SOFT_COLS, cols, cust_only)
    errors, warnings = e1 + e2, w1 + w2

    clash = sorted(ids1 & ids2)
    if clash:
        errors.append(f"rule_id used in BOTH files: {clash}")

    for w in warnings:
        print(f"  warn  {w}")
    for e in errors:
        print(f"  FAIL  {e}")

    print(
        f"\n{len(ids1)} hard + {len(ids2)} soft rules checked against {BOOKING.name} — "
        f"{len(errors)} error(s), {len(warnings)} warning(s)"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
