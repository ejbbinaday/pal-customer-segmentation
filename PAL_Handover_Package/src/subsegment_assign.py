"""Sub-segment assignment — score every booking with its level-2 sub-type, for Power BI.

`sub_segment.py` *characterises* sub-types on a 40,000-booking sample per parent and writes
`outputs/sub_segments/summary.md`. It never assigns: no row-level sub-type exists, so the Power BI
export has only the level-1 `CustomerSegment`. This script closes that gap and is deliberately a
**separate** entrypoint — `summary.md` feeds the defence deck and `sankey_subsegment.py`, so nothing
here overwrites it.

Method (see `docs/subsegment-scoring-plan.md`):

  1. The LCA feature vector is fully discrete, so the input domain is enumerable — **17,847 distinct
     cells cover all 21.7M bookings** in the five parents. Build that cell table with one GROUP BY.
  2. Fit StepMix on the cell table with `sample_weight=count`, which *is* fitting every booking
     exactly (verified: `score(cells, sample_weight=w)` == `score(rows replicated by w)`). No sample.
  3. ⚠️ `m.bic(X)` is wrong here — it uses an unweighted score and N = number of *cells*. Weighted BIC
     is computed by hand below, because `K_RANGE` selection depends on it.
  4. `predict` the cells, join back to the bookings → one sub-type per booking.

Every encoding decision (region map, tier fill, kept columns, level maps) is frozen into
`model_meta.json`, because a sample-derived encoder cannot score a population: the 40k sample for
OFW/Migrant sees 6 destination regions where the population has 7.

Writes  outputs/sub_segments/lookup/*.csv, model_meta.json, population_profiles.md
        data/interim/pal_subsegment.parquet   (customer_id, issue_date, sub_segment)
Run:    python src/subsegment_assign.py
"""

import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from stepmix.stepmix import StepMix

ROOT = Path(__file__).resolve().parents[1]
BOOKING = ROOT / "data" / "interim" / "pal_features_booking.parquet"
OUT = ROOT / "outputs" / "sub_segments"
LOOKUP_DIR = OUT / "lookup"
META = OUT / "model_meta.json"
PROFILES = OUT / "population_profiles.md"
ASSIGN = ROOT / "data" / "interim" / "pal_subsegment.parquet"

# Same five parents, same search range and seed as `sub_segment.py` — this is the same model, fitted on
# the population instead of a sample.
PARENTS = [
    "Leisure",
    "OFW/Migrant",
    "Balikbayan/VFR",
    "Outbound International Leisure",
    "Corporate",
]
K_RANGE = range(2, 5)
SEED = 42

# The cell columns, in `code()`'s order. `dest_region` is the only non-integer one.
CELL_COLS = [
    "lead_bucket",
    "value_tier",
    "n_coupons_b",
    "dest_region",
    "round_trip",
    "connecting",
    "peak_month",
    "foreign_issue",
]

# Mirrors `code()` exactly: pd.cut(lead_days.clip(0,365), [-1,3,14,45,120,999], labels=False) and
# n_coupons.clip(1,8) - 1 clipped to 0..3. NULLs: only `max_tier` (46,467 of 22.9M) and `dest_region`
# (NULL *is* Domestic); the four booleans and lead_days/n_coupons are non-null by construction.
CELL_SQL = """
    CASE WHEN least(lead_days, 365) <= 3   THEN 0
         WHEN least(lead_days, 365) <= 14  THEN 1
         WHEN least(lead_days, 365) <= 45  THEN 2
         WHEN least(lead_days, 365) <= 120 THEN 3
         ELSE 4 END                                        AS lead_bucket,
    cast(round(coalesce(max_tier, {med})) AS INTEGER)       AS value_tier,
    least(greatest(least(n_coupons, 8) - 1, 0), 3)          AS n_coupons_b,
    coalesce(dest_region, 'Domestic')                       AS dest_region,
    cast(round_trip AS INTEGER)                             AS round_trip,
    cast(connecting AS INTEGER)                             AS connecting,
    cast(peak_month AS INTEGER)                             AS peak_month,
    cast(foreign_issue AS INTEGER)                          AS foreign_issue
"""


def cell_table(con: duckdb.DuckDBPyConnection, seg: str, med: float) -> pd.DataFrame:
    """One row per distinct feature cell, with its booking count as the weight.

    `ORDER BY ALL` is load-bearing, not cosmetic: under `PRAGMA threads=6` a bare `GROUP BY` returns the
    cells in a different order on every run, which changes the order StepMix sees and therefore which EM
    local optimum it settles in. Measured 21 Aug 2026 — two consecutive runs gave OFW/Migrant different
    sub-type boundaries. `random_state` alone does not buy reproducibility here.
    """
    return con.execute(
        f"""
        SELECT {CELL_SQL.format(med=med)}, count(*) AS w
        FROM read_parquet('{BOOKING}')
        WHERE proxy_segment = ?
        GROUP BY ALL
        ORDER BY ALL
    """,
        [seg],
    ).fetchdf()


def encode(cells: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, list]]:
    """0-indexed contiguous codes over the levels this parent actually has, plus the map that made them.

    `code()` used `astype("category").cat.codes` for `dest_region`, which learns its alphabet from the
    rows it is given — the defect that makes a sample-fitted model unable to score the population. Here
    the alphabet comes from the population and is written to `model_meta.json`, so scoring is
    reproducible. Within-parent constant columns carry no information and are dropped (as before), but
    the kept list is recorded rather than re-derived.
    """
    codes, maps = pd.DataFrame(index=cells.index), {}
    for c in CELL_COLS:
        levels = sorted(cells[c].unique().tolist())
        if len(levels) == 1:  # constant within this parent — no information
            continue
        maps[c] = levels
        codes[c] = cells[c].map({v: i for i, v in enumerate(levels)}).astype(int)
    return codes, maps


def weighted_bic(m: StepMix, codes: pd.DataFrame, w: np.ndarray) -> float:
    """BIC on the population the weights represent.

    `m.bic(X)` computes `-2 * score(X) * X.shape[0] + n_parameters * log(X.shape[0])` — an *unweighted*
    average log-likelihood and N = the number of cells (17,847), not the number of bookings (21.7M).
    Both terms are wrong on a weighted cell table, and nothing raises.
    """
    total = float(w.sum())
    return -2.0 * m.score(codes, sample_weight=w) * total + m.n_parameters * np.log(total)


def best_lca(codes: pd.DataFrame, w: np.ndarray) -> tuple[int, np.ndarray, dict[int, float]]:
    best, bics = None, {}
    for k in K_RANGE:
        m = StepMix(
            n_components=k,
            measurement="categorical",
            n_init=2,
            random_state=SEED,
            verbose=0,
            progress_bar=False,
        )
        m.fit(codes, sample_weight=w)
        bics[k] = weighted_bic(m, codes, w)
        if best is None or bics[k] < bics[best[0]]:
            best = (k, m)
    k, m = best
    return k, m.predict(codes), bics


def name_sub(row) -> str:
    """Unchanged from `sub_segment.py` — the deck's sub-type vocabulary."""
    dirn = "round-trip" if row["pct_rt"] >= 50 else "one-way"
    if row["med_lead"] <= 3:
        timing = "last-minute"
    elif row["med_lead"] <= 14:
        timing = "short-lead"
    elif row["med_lead"] <= 45:
        timing = "advance"
    else:
        timing = "far-advance"
    tier = {1: "supersaver", 2: "saver", 3: "value", 4: "flex"}.get(int(row["med_tier"]), "premium")
    return f"{dirn} · {timing} · {tier}"


def disambiguate(prof: pd.DataFrame) -> pd.Series:
    """Make sub-type names unique within a parent without changing the deck's vocabulary.

    `name_sub()` is three rounded statistics glued together, so nothing stops two LCA classes landing on
    the same string — and on the population fit, OFW/Migrant's does: two classes are both
    `one-way · advance · saver`, separated by connectivity (0% vs 97% connecting), which the name never
    mentions. Colliding names get that qualifier appended; an ordinal is the last resort.
    """
    names = prof.apply(name_sub, axis=1)
    dup = names.duplicated(keep=False)
    if dup.any():
        qual = prof["pct_conn"].map(lambda v: "connecting" if v >= 50 else "nonstop")
        names = names.where(~dup, names + " · " + qual)
    for nm in names[names.duplicated(keep=False)].unique():
        for i, ix in enumerate(names.index[names == nm], 1):
            names.at[ix] = f"{nm} #{i}"
    return names


def slug(seg: str) -> str:
    return seg.lower().replace("/", "-").replace(" ", "_")


def profile(con: duckdb.DuckDBPyConnection, seg: str, med: float) -> pd.DataFrame:
    """Sub-type profiles on the whole parent — exact medians, not sample medians."""
    return con.execute(
        f"""
        WITH b AS (
            SELECT lead_days, max_tier, rev_pos, {CELL_SQL.format(med=med)}
            FROM read_parquet('{BOOKING}')
            WHERE proxy_segment = ?
        )
        SELECT sub_index,
               count(*)                          AS n,
               median(lead_days)                 AS med_lead,
               median(coalesce(max_tier, {med})) AS med_tier,
               median(rev_pos)                   AS med_rev,
               round(100 * avg(round_trip))      AS pct_rt,
               round(100 * avg(connecting))      AS pct_conn
        FROM b JOIN lk USING ({", ".join(CELL_COLS)})
        GROUP BY sub_index ORDER BY sub_index
    """,
        [seg],
    ).fetchdf()


def main() -> None:  # noqa: PLR0915 — one linear build, kept readable by section comments
    LOOKUP_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("PRAGMA threads=6")
    con.execute("SET memory_limit='8GB'")

    meta: dict = {"parents": {}, "seed": SEED, "k_range": [K_RANGE.start, K_RANGE.stop - 1]}
    lookups, lines = (
        [],
        [
            "# Sub-type profiles on the full population (level-2 assignment)\n",
            "Same model as `summary.md`, fitted on **every** booking in each parent via a count-weighted "
            "cell table rather than a 40,000-row sample. `summary.md` is left untouched: it is what the "
            "defence deck and `sankey_subsegment.py` quote. Shares and medians here are exact, so they "
            "will not match the sampled ones — that is the point.\n",
        ],
    )

    for seg in PARENTS:
        med = con.execute(
            f"SELECT median(max_tier) FROM read_parquet('{BOOKING}') WHERE proxy_segment = ?", [seg]
        ).fetchone()[0]
        cells = cell_table(con, seg, med)
        w = cells["w"].to_numpy(dtype=float)
        codes, maps = encode(cells)
        k, labels, bics = best_lca(codes, w)

        lk = cells[CELL_COLS].copy()
        lk["sub_index"] = labels
        con.register("lk", lk)
        prof = profile(con, seg, med)
        con.unregister("lk")

        prof["pct"] = (100 * prof["n"] / prof["n"].sum()).round(1)
        prof["sub_name"] = disambiguate(prof)
        if prof["sub_name"].duplicated().any():  # pragma: no cover — disambiguate() guarantees this
            raise AssertionError(f"{seg}: sub-type names still collide — {list(prof.sub_name)}")

        names = dict(zip(prof["sub_index"], prof["sub_name"], strict=True))
        lk["sub_name"] = lk["sub_index"].map(names)
        # Composite key: `name_sub` collides ACROSS parents — `one-way · advance · saver` is emitted by
        # Leisure, OFW/Migrant and Outbound alike, so the bare name cannot key a Power BI dimension.
        lk["sub_segment"] = seg + " — " + lk["sub_name"]
        lk["parent"] = seg
        lk.to_csv(LOOKUP_DIR / f"{slug(seg)}.csv", index=False)
        lookups.append(lk)

        meta["parents"][seg] = {
            "bookings": int(w.sum()),
            "cells": int(len(cells)),
            "k": k,
            "weighted_bic": {str(kk): round(v, 1) for kk, v in bics.items()},
            "value_tier_fill": float(med),
            "kept_columns": list(codes.columns),
            "dropped_constant": [c for c in CELL_COLS if c not in codes.columns],
            "level_maps": {c: list(map(_json_safe, v)) for c, v in maps.items()},
            "sub_types": names,
        }
        lines += [
            f"\n## {seg} — {int(w.sum()):,} bookings · {len(cells):,} cells → "
            f"**{k} sub-types** (weighted BIC)\n",
            prof[
                ["sub_name", "n", "pct", "med_lead", "med_tier", "med_rev", "pct_rt", "pct_conn"]
            ].to_markdown(index=False),
            "",
        ]
        print(f"{seg}: {len(cells):,} cells → {k} sub-types ({int(w.sum()):,} bookings)")

    # ── the assignment table ──────────────────────────────────────────────────────────────────────
    allk = pd.concat(lookups, ignore_index=True)
    con.register("lookup_all", allk[["parent", *CELL_COLS, "sub_segment"]])
    fills = " ".join(f"WHEN '{s}' THEN {meta['parents'][s]['value_tier_fill']}" for s in PARENTS)
    ASSIGN.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"""
        COPY (
            WITH b AS (
                SELECT customer_id, issue_date, proxy_segment AS parent,
                       {CELL_SQL.format(med=f"CASE proxy_segment {fills} ELSE 2 END")}
                FROM read_parquet('{BOOKING}')
                WHERE proxy_segment IN ({", ".join(f"'{s}'" for s in PARENTS)})
            )
            SELECT b.customer_id, b.issue_date, l.sub_segment
            FROM b JOIN lookup_all l USING (parent, {", ".join(CELL_COLS)})
        ) TO '{ASSIGN}' (FORMAT PARQUET, COMPRESSION zstd)
    """)
    n_assigned = con.execute(f"SELECT count(*) FROM read_parquet('{ASSIGN}')").fetchone()[0]
    n_parents = int(sum(m["bookings"] for m in meta["parents"].values()))
    if n_assigned != n_parents:
        raise AssertionError(
            f"assigned {n_assigned:,} != {n_parents:,} parent bookings — join fanned out"
        )
    meta["assigned_bookings"] = n_assigned
    meta["sub_segment_count"] = int(allk["sub_segment"].nunique())

    META.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    lines += [
        f"\n---\n\n**{n_assigned:,} bookings assigned** across "
        f"**{meta['sub_segment_count']} sub-segments**; every booking in the five parents gets exactly "
        "one. Segments outside the five parents carry no sub-type and take their own name as the "
        "level-2 value in the export.\n",
    ]
    PROFILES.write_text("\n".join(lines) + "\n")
    print(f"\nWrote {ASSIGN} ({n_assigned:,} rows), {META.name}, {PROFILES.name}")


def _json_safe(v):
    return v.item() if hasattr(v, "item") else v


if __name__ == "__main__":
    main()
