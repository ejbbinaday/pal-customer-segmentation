"""Profile the real PAL coupon-level data in `data/PAL-data/*.txt.gz`.

The four gzipped CSVs total ~38M coupon/segment-level rows (2024–2027, identical
40-col schema). This script uses DuckDB to stream them directly (no full in-memory
load) and characterise the data BEFORE we design cleaning / EDA / feature engineering:

    • per-column: dtype, null rate, distinct count, min / max
    • grain check: coupons per `UniqueID`, so we know how far it is from PNR/customer level
    • money sanity: negative / zero fares, revenue vs net-fare spread
    • coverage: rows per issuance & departure month, per source file
    • top categories for the key low-cardinality dimensions

Run:
    python src/profile_raw.py    → outputs/profile_raw/{column_profile.csv, summary.md}

Read-only: touches nothing under data/, writes only under outputs/.
"""

from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PARQUET = ROOT / "data" / "interim" / "pal_parquet"
GZ_GLOB = str(ROOT / "data" / "PAL-data" / "*.txt.gz")
OUTPUT = ROOT / "outputs" / "profile_raw"

# Columns we treat as numeric / temporal for min-max + money checks.
NUMERIC_COLS = [
    "CouponNumber",
    "DaysBeforeMonthEnd",
    "Age",
    "Revenues w YQ",
    "Net Fare",
    "Pax Count",
    "is_nonstop",
]
DATE_COLS = [
    "DateOfIssuance",
    "DepartureDate",
    "DepartureDateTime",
    "ArrivalDateTime",
    "TripOD_DepartureDate",
    "OnlineOD_DepartureDate",
]
# Low-cardinality dimensions worth a top-N breakdown.
TOP_N_COLS = [
    "POO",
    "CountryCodeOfIssue",
    "CurrentCouponStatus",
    "BookingClass",
    "SoldOperatingCabinClass",
    "OperatingCabinClass",
    "OperatingCarrierCode",
    "Channel Category",
    "BookingType",
    "is_nonstop",
]


def q(name: str) -> str:
    """Double-quote an identifier (columns have spaces / mixed case)."""
    return '"' + name.replace('"', '""') + '"'


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("PRAGMA threads=4")
    con.execute("SET memory_limit='6GB'")
    # Prefer the typed Parquet built by build_parquet.py; fall back to raw gz.
    if PARQUET.exists():
        src = f"read_parquet('{PARQUET}/**/*.parquet')"
    else:
        src = (
            f"read_csv_auto('{GZ_GLOB}', header=true, union_by_name=true, "
            f"filename=true, sample_size=200000)"
        )
    con.execute(f"CREATE VIEW pal AS SELECT * FROM {src}")
    return con


def column_profile(con: duckdb.DuckDBPyConnection, cols: list[str]) -> pd.DataFrame:
    """One scan: null count + approx distinct + min + max for every column."""
    parts = []
    for c in cols:
        qc = q(c)
        parts.append(f"count({qc}) AS {q('nn_' + c)}")
        parts.append(f"approx_count_distinct({qc}) AS {q('nd_' + c)}")
        parts.append(f"min({qc})::VARCHAR AS {q('mn_' + c)}")
        parts.append(f"max({qc})::VARCHAR AS {q('mx_' + c)}")
    row = con.execute(f"SELECT count(*) AS total, {', '.join(parts)} FROM pal").fetchdf().iloc[0]

    total = int(row["total"])
    recs = []
    for c in cols:
        nn = int(row[f"nn_{c}"])
        recs.append(
            {
                "column": c,
                "non_null": nn,
                "nulls": total - nn,
                "null_pct": round(100 * (total - nn) / total, 3),
                "distinct_approx": int(row[f"nd_{c}"]),
                "min": row[f"mn_{c}"],
                "max": row[f"mx_{c}"],
            }
        )
    return total, pd.DataFrame(recs)


def grain_stats(con: duckdb.DuckDBPyConnection) -> dict:
    """How far the coupon grain is from a customer/PNR grain."""
    d = (
        con.execute(
            """
        WITH per_id AS (
            SELECT "UniqueID" AS uid,
                   count(*) AS coupons,
                   count(DISTINCT "TripOD_DepartureDate" || '|' || "TripOD_Path") AS trips,
                   sum("Pax Count") AS pax
            FROM pal
            GROUP BY 1
        )
        SELECT count(*)                         AS n_unique_ids,
               sum(coupons)                     AS total_coupons,
               avg(coupons)                     AS avg_coupons_per_id,
               median(coupons)                  AS median_coupons_per_id,
               max(coupons)                     AS max_coupons_per_id,
               quantile_cont(coupons, 0.95)     AS p95_coupons_per_id,
               avg(trips)                       AS avg_trips_per_id,
               sum(CASE WHEN uid IS NULL THEN coupons ELSE 0 END) AS coupons_null_id
        FROM per_id
        """
        )
        .fetchdf()
        .iloc[0]
    )
    return d.to_dict()


def money_stats(con: duckdb.DuckDBPyConnection) -> dict:
    d = (
        con.execute(
            """
        SELECT
          sum(CASE WHEN "Revenues w YQ" < 0 THEN 1 ELSE 0 END) AS rev_negative,
          sum(CASE WHEN "Revenues w YQ" = 0 THEN 1 ELSE 0 END) AS rev_zero,
          sum(CASE WHEN "Net Fare" < 0 THEN 1 ELSE 0 END)      AS net_negative,
          sum(CASE WHEN "Net Fare" > "Revenues w YQ" THEN 1 ELSE 0 END) AS net_gt_rev,
          avg("Revenues w YQ")  AS rev_mean,
          median("Revenues w YQ") AS rev_median,
          quantile_cont("Revenues w YQ", 0.99) AS rev_p99,
          max("Revenues w YQ")  AS rev_max,
          sum(CASE WHEN "Age" IS NULL THEN 1 ELSE 0 END) AS age_null,
          sum(CASE WHEN "Age" < 0 OR "Age" > 120 THEN 1 ELSE 0 END) AS age_outlier
        FROM pal
        """
        )
        .fetchdf()
        .iloc[0]
    )
    return d.to_dict()


def coverage(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return con.execute(
        """
        SELECT src_file,
               count(*)                       AS rows,
               min("DepartureDate")::DATE     AS dep_min,
               max("DepartureDate")::DATE     AS dep_max,
               min("DateOfIssuance")::DATE    AS iss_min,
               max("DateOfIssuance")::DATE    AS iss_max
        FROM pal GROUP BY src_file ORDER BY src_file
        """
    ).fetchdf()


def top_values(con: duckdb.DuckDBPyConnection, col: str, n: int = 8) -> pd.DataFrame:
    qc = q(col)
    return con.execute(
        f"""SELECT {qc} AS value, count(*) AS rows
            FROM pal GROUP BY 1 ORDER BY rows DESC LIMIT {n}"""
    ).fetchdf()


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    con = connect()

    schema = con.execute("DESCRIBE pal").fetchdf()
    cols = [c for c in schema["column_name"].tolist() if c != "filename"]
    print(f"Schema: {len(cols)} columns\n")

    print("[1/5] Column profile (nulls / distinct / range) ...")
    total, prof = column_profile(con, cols)
    prof.to_csv(OUTPUT / "column_profile.csv", index=False)

    print("[2/5] Coverage by source file ...")
    cov = coverage(con)

    print("[3/5] Grain: coupons per UniqueID ...")
    grain = grain_stats(con)

    print("[4/5] Money & age sanity ...")
    money = money_stats(con)

    print("[5/5] Top categories ...")
    tops = {c: top_values(con, c) for c in TOP_N_COLS if c in cols}

    # ── write markdown summary ───────────────────────────────────────────────
    lines = [
        "# Raw data profile — data/PAL-data/*.txt.gz\n",
        f"**Total coupon rows:** {total:,}  ·  **Columns:** {len(cols)}\n",
        "\n## Coverage by source file\n",
        cov.to_markdown(index=False),
        "\n\n## Grain (coupon → customer)\n",
        f"- Distinct `UniqueID`: **{int(grain['n_unique_ids']):,}**",
        f"- Coupons per ID: mean **{grain['avg_coupons_per_id']:.2f}**, "
        f"median **{grain['median_coupons_per_id']:.0f}**, "
        f"p95 **{grain['p95_coupons_per_id']:.0f}**, max **{int(grain['max_coupons_per_id']):,}**",
        f"- Avg distinct trips per ID: **{grain['avg_trips_per_id']:.2f}**",
        f"- Coupons with NULL `UniqueID`: **{int(grain['coupons_null_id']):,}**",
        "\n## Money & age sanity\n",
        f"- `Revenues w YQ`: mean {money['rev_mean']:.1f}, median {money['rev_median']:.1f}, "
        f"p99 {money['rev_p99']:.1f}, max {money['rev_max']:.1f}",
        f"- Negative revenue rows: **{int(money['rev_negative']):,}**  ·  "
        f"zero revenue: **{int(money['rev_zero']):,}**",
        f"- Negative `Net Fare` rows: **{int(money['net_negative']):,}**  ·  "
        f"`Net Fare` > `Revenues w YQ`: **{int(money['net_gt_rev']):,}**",
        f"- NULL age: **{int(money['age_null']):,}**  ·  "
        f"age <0 or >120: **{int(money['age_outlier']):,}**",
        "\n## Column profile\n",
        prof.to_markdown(index=False),
        "\n## Top categories\n",
    ]
    for c, df in tops.items():
        lines.append(f"\n**{c}**\n")
        lines.append(df.to_markdown(index=False))
    (OUTPUT / "summary.md").write_text("\n".join(lines) + "\n")

    # ── console recap ─────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print(f"TOTAL ROWS: {total:,}   COLUMNS: {len(cols)}")
    print(
        f"DISTINCT UniqueID: {int(grain['n_unique_ids']):,}  "
        f"(avg {grain['avg_coupons_per_id']:.1f} coupons/id)"
    )
    print("=" * 70)
    print(prof.to_string(index=False))
    print(f"\nWrote {OUTPUT / 'summary.md'} and column_profile.csv")


if __name__ == "__main__":
    main()
