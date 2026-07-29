"""The circularity contract — which fields may be used to *validate* the proxy segments, and why.

Every validation number this project has produced so far is circular: agreement is measured against
`proxy_segment`, which is the rule waterfall's own output (`src/features_real.py`, the CASE block).
Plan A fixes that with SME labels. This module underpins **Plan B**, which asks a question that needs
no labels at all:

    Do the segments differ on evidence the rules never saw?

That only works if "never saw" is enforced rather than assumed, so the audit lives here — in **one
place**, imported by every validation script. Duplicating these lists across scripts is the easiest
possible way to silently publish a circular result.

Three tiers:

  • `RULE_FIELDS` — consumed by the waterfall. **Validates nothing.** Note in particular the three
    fields that look like perfect independent markers and are not: `sea_crew` *is* the OFW/Migrant
    rule, `is_award` *is* the Mabuhay Loyalist rule, `pilgrimage` *is* the Pilgrimage rule. Using any
    of them would "confirm" a segment with the very field that defined it.
  • `TRIP_MECHANICAL` — absent from the rules, but *mechanically determined by trip type*. A round
    trip costs more and has more coupons than a one-way, so revenue and coupon count leak
    `round_trip` — which is the single bit separating OFW/Migrant from Balikbayan/VFR. Admitting them
    would let a classifier "distinguish" those two segments by rediscovering the rule.
  • `ANCHORS` — admissible. Absent from the rules and not a proxy for trip type.

**`dest_region` carries a caveat:** it is admissible for validating the *rules* (they never use it),
but it *is* in the clustering feature set (`model_zoo.NOMINAL`). Use it to validate the rule-based
segments, never to validate a clustering result.

**Sea-crew rows are excluded from the whole analysis** (`BASE_WHERE`). `channel` is an anchor and one
of its levels is literally `Sea Crew`, so keeping those rows would hand the classifier the OFW rule
through an anchor. That drops OFW/Migrant from 3.92M to 2.82M bookings — deliberately: a booking whose
channel field says "Sea Crew" is identified **by definition** and needs no validating. The open
question is the other 72%.

Read-only. Run via the validators, not directly.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BOOKING = ROOT / "data" / "interim" / "pal_features_booking.parquet"
CUSTOMER = ROOT / "data" / "interim" / "pal_features_customer.parquet"

SEED = 42

# ── tier 1: consumed by the proxy waterfall → circular, unusable for validation ──
RULE_FIELDS = frozenset(
    {
        "is_award",  # → Mabuhay Loyalist
        "corp_channel",  # → Corporate
        "any_business",  # → Corporate (with lead_days)
        "lead_days",  # → Corporate, Last-Minute
        "pilgrimage",  # → Pilgrimage
        "sea_crew",  # → OFW/Migrant
        "foreign_issue",  # → OFW/Migrant, Balikbayan/VFR
        "is_international",  # → OFW/Migrant, Balikbayan/VFR, Premium Bleisure
        "max_tier",  # → OFW/Migrant, Balikbayan/VFR
        "round_trip",  # → the *only* bit splitting OFW/Migrant from Balikbayan/VFR
        "any_premium",  # → Premium Bleisure, Budget/Adventure
        "is_group",  # → Family
        "is_domestic",  # → Budget/Adventure
        "proxy_segment",  # the label itself
    }
)

# ── tier 2: not in the rules, but a proxy for trip type → leaks `round_trip` ─────
TRIP_MECHANICAL = frozenset({"rev_pos", "n_coupons", "connecting", "n_directions", "min_tier"})

# ── tier 3: admissible anchors, with the reason each one is independent ──────────
ANCHORS: dict[str, str] = {
    "age": "passenger demographics — never referenced by any rule",
    "age_known": "whether age was captured; its own signal, and makes MNAR visible in importances",
    "issue_country": "country *identity* — the rules use only the foreign/domestic bit",
    "channel": "channel *identity* — the rules use only corp_channel and sea_crew",
    "dep_month": "departure timing — the rules use no month at all",
    "dest_region": "destination region — not in the rules (but IS a clustering feature; see docstring)",
    "n_bookings": "customer's lifetime booking count — no rule references purchase frequency",
}

CATEGORICAL = ("issue_country", "channel", "dep_month", "dest_region")
NUMERIC = ("age", "age_known", "n_bookings")

# ── the subtle leak: *semantic* overlap that a name-based guard cannot see ────────
# Three anchors are finer-grained versions of fields the rules DO use, so coarsening them recovers a
# rule bit exactly. `dest_region == 'Domestic'` **is** `is_domestic`; `issue_country != 'PH'` **is**
# `foreign_issue`; `channel IN ('TMC','Corporate Web Portal')` **is** `corp_channel`. Handing these to
# a classifier comparing two segments that the rules split on that very bit yields AUC ≈ 1.0 and
# proves nothing except that the rule was applied consistently.
#
# So admissibility is **per comparison**, not global:
#   • TIER_A  — independent of every rule field. Always usable, so a TIER_A-only matrix is directly
#               comparable across all pairs.
#   • the rest — usable only when the rule bit they encode is (near-)constant across both groups
#               being compared, i.e. it is not what separates them.
TIER_A = ("age", "age_known", "dep_month", "n_bookings")

ANCHOR_LEAKS: dict[str, tuple[str, ...]] = {
    "channel": ("corp_channel",),
    "dest_region": ("is_domestic", "is_international"),
    "issue_country": ("foreign_issue",),
}

# Loaded as *metadata* so leak checks can be measured. Never passed to a model — they are in
# RULE_FIELDS, so `assert_admissible` rejects them if anyone tries.
AUDIT_BITS = ("corp_channel", "is_domestic", "is_international", "foreign_issue")

LEAK_TOLERANCE = 0.20  # max allowed gap in a rule bit's rate between two groups

# Sea-crew rows excluded — see the module docstring for why this is deliberate, not a data cut.
BASE_WHERE = "NOT sea_crew"

# The OFW-vs-Balikbayan question, isolated: only bookings the foreign-issue economy branch labelled,
# with every earlier (higher-priority) branch of the waterfall excluded, so the *sole* difference
# between the two groups is round_trip.
CLEAN_PAIR_WHERE = (
    "NOT sea_crew AND NOT is_award AND NOT corp_channel AND NOT pilgrimage "
    "AND foreign_issue AND is_international AND max_tier <= 4"
)

TOP_CATEGORY_LEVELS = 30  # rarer issue_country / channel values collapse into 'Other'


class CircularityError(AssertionError):
    """Raised when a validation script asks for a field that would make its result circular."""


def assert_admissible(cols) -> None:
    """Guard: refuse any column that would make a validation circular.

    Called by every validator before fitting. It exists so that a future edit adding a convenient
    feature cannot quietly reintroduce the circularity this whole module is built to prevent.
    """
    bad_rule = sorted(set(cols) & RULE_FIELDS)
    bad_mech = sorted(set(cols) & TRIP_MECHANICAL)
    if bad_rule or bad_mech:
        parts = []
        if bad_rule:
            parts.append(f"consumed by the proxy waterfall (circular): {bad_rule}")
        if bad_mech:
            parts.append(f"mechanically determined by trip type (leaks round_trip): {bad_mech}")
        raise CircularityError("Inadmissible validation features — " + "; ".join(parts))


def _connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("PRAGMA threads=6")
    return con


def load_anchors(
    per_segment: int,
    where: str = BASE_WHERE,
    segments: list[str] | None = None,
    seed: int = SEED,
    extra: tuple[str, ...] = (),
) -> pd.DataFrame:
    """Stratified sample of anchors: up to `per_segment` bookings per `proxy_segment`.

    One query for every segment at once — the pairwise tests then slice this frame in pandas, so the
    22.9M-row Parquet and the customer rollup are each scanned once rather than once per pair.
    Ordering is by a hash of the booking key, so the sample is deterministic without global seed state.

    `extra` admits outcome columns (`flown_any`, `refund_any`) for the criterion validator — they are
    outcomes, not features, and are never handed to a classifier as input.
    """
    seg_filter = ""
    if segments:
        quoted = ", ".join("'" + s.replace("'", "") + "'" for s in segments)
        seg_filter = f" AND proxy_segment IN ({quoted})"
    extra_cols = "".join(f", {c}" for c in extra)
    con = _connect()
    df = con.execute(f"""
        WITH b AS (
            SELECT customer_id, issue_date, proxy_segment,
                   age, age_known::INT AS age_known,
                   coalesce(issue_country, 'Unknown') AS issue_country,
                   coalesce(channel, 'Unknown')       AS channel,
                   dep_month::VARCHAR                 AS dep_month,
                   coalesce(dest_region, 'Domestic')  AS dest_region,
                   corp_channel::INT AS corp_channel, is_domestic::INT AS is_domestic,
                   is_international::INT AS is_international,
                   foreign_issue::INT AS foreign_issue
                   {extra_cols}
            FROM read_parquet('{BOOKING}')
            WHERE {where}{seg_filter}
        ),
        j AS (
            SELECT b.*, c.n_bookings
            FROM b LEFT JOIN read_parquet('{CUSTOMER}') c USING (customer_id)
        ),
        r AS (
            -- hash the *booking* key, not just the customer: hashing customer_id alone would
            -- cluster the sample by customer and let one frequent flyer dominate a stratum
            SELECT *, row_number() OVER (
                PARTITION BY proxy_segment
                ORDER BY hash(customer_id || '|' || issue_date::VARCHAR || '|' || {seed})
            ) AS rn
            FROM j
        )
        SELECT * EXCLUDE (rn, customer_id) FROM r WHERE rn <= {per_segment}
    """).fetchdf()
    return prepare(df)


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse rare categorical levels and set dtypes for native categorical/NaN handling."""
    out = df.copy()
    for c in ("issue_country", "channel"):
        if c in out.columns:
            top = out[c].value_counts().head(TOP_CATEGORY_LEVELS).index
            out[c] = out[c].where(out[c].isin(top), "Other")
    for c in CATEGORICAL:
        if c in out.columns:
            out[c] = out[c].astype("category")
    for c in NUMERIC:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").astype("float64")
    return out


def feature_columns(df: pd.DataFrame) -> list[str]:
    """The anchor columns present in `df`, guarded. Order is stable for reproducible fits."""
    cols = [c for c in ANCHORS if c in df.columns]
    assert_admissible(cols)
    return cols


def admissible_for_groups(
    df: pd.DataFrame, mask_a: pd.Series, mask_b: pd.Series, cols: list[str]
) -> tuple[list[str], dict[str, str]]:
    """Per-comparison admissibility: drop anchors whose encoded rule bit is what separates the groups.

    For each leaky anchor, compare the rate of the rule bit it encodes in group A vs group B. If the
    gap exceeds `LEAK_TOLERANCE`, that bit is (part of) the rule boundary being tested, so the anchor
    would recover the rule rather than corroborate it — drop it and record why.

    Returns `(usable_cols, {dropped_anchor: reason})` so every report can state what it withheld.
    """
    usable, dropped = [], {}
    for c in cols:
        leaks = ANCHOR_LEAKS.get(c, ())
        offending = []
        for bit in leaks:
            if bit not in df.columns:
                continue
            ra, rb = float(df.loc[mask_a, bit].mean()), float(df.loc[mask_b, bit].mean())
            if abs(ra - rb) > LEAK_TOLERANCE:
                offending.append(f"{bit} {ra:.2f} vs {rb:.2f}")
        if offending:
            dropped[c] = "encodes " + "; ".join(offending)
        else:
            usable.append(c)
    return usable, dropped


def categorical_mask(cols: list[str]) -> list[bool]:
    """`categorical_features` mask for HistGradientBoosting, aligned to `cols`."""
    return [c in CATEGORICAL for c in cols]


def segment_counts(where: str = BASE_WHERE) -> pd.DataFrame:
    """Population sizes under a filter — so every report states what was actually analysed."""
    con = _connect()
    return con.execute(f"""
        SELECT proxy_segment, count(*) AS n
        FROM read_parquet('{BOOKING}') WHERE {where}
        GROUP BY 1 ORDER BY 2 DESC
    """).fetchdf()
