"""Convert the raw PAL gzipped CSVs to a typed, partitioned Parquet dataset.

Single decompression pass over `data/PAL-data/*.txt.gz` (~38M coupon rows) → columnar
Parquet under `data/interim/pal_parquet/`, partitioned by issuance year. Every downstream
step (profiling, EDA, cleaning, feature engineering) reads the Parquet instead of the gz,
turning multi-minute scans into sub-second queries.

Typing notes handled here:
  • the 6 timestamp columns carry SQL-style `.0000000` (100-ns) precision, which exceeds
    DuckDB's microsecond TIMESTAMP → read them as VARCHAR, then cast the first 19 chars.
  • money columns → DOUBLE; `is_nonstop` → BOOLEAN; `Pax Count`/`Age` → integer.
  • a `src_file` column preserves provenance; `iss_year` is the partition key.

Run:
    python src/build_parquet.py    → data/interim/pal_parquet/ (idempotent, overwrites)
"""

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DATA_GLOB = str(ROOT / "data" / "PAL-data" / "*.txt.gz")
OUT_DIR = ROOT / "data" / "interim" / "pal_parquet"

# Columns forced to VARCHAR on read so we can cast them safely below.
TS_COLS = [
    "DateOfIssuance",
    "DepartureDate",
    "DepartureDateTime",
    "ArrivalDateTime",
    "TripOD_DepartureDate",
    "OnlineOD_DepartureDate",
]


def ts(col: str) -> str:
    # first 19 chars = 'YYYY-MM-DD HH:MM:SS'; drops the all-zero fractional part.
    return f'try_cast(substr("{col}", 1, 19) AS TIMESTAMP) AS "{col}"'


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("PRAGMA threads=4")
    con.execute("SET memory_limit='6GB'")
    con.execute("SET preserve_insertion_order=false")

    types = {c: "VARCHAR" for c in TS_COLS}
    types_sql = ", ".join(f"'{k}': '{v}'" for k, v in types.items())

    reader = (
        f"read_csv_auto('{DATA_GLOB}', header=true, union_by_name=true, "
        f"filename=true, sample_size=200000, types={{{types_sql}}})"
    )

    # explicit cast list for the timestamps; everything else passes through via EXCLUDE.
    ts_select = ", ".join(ts(c) for c in TS_COLS)

    print("Converting gz → Parquet (single pass) ...")
    con.execute(
        f"""
        COPY (
            SELECT
                * EXCLUDE ({", ".join(f'"{c}"' for c in TS_COLS)}, filename),
                {ts_select},
                regexp_extract(filename, '[^/]+$') AS src_file,
                coalesce(
                    try_cast(substr("DateOfIssuance", 1, 4) AS INTEGER), 0
                ) AS iss_year
            FROM {reader}
        )
        TO '{OUT_DIR}'
        (FORMAT PARQUET, PARTITION_BY (iss_year), OVERWRITE_OR_IGNORE, COMPRESSION zstd)
        """
    )

    n = con.execute(f"SELECT count(*) FROM read_parquet('{OUT_DIR}/**/*.parquet')").fetchone()[0]
    size = sum(f.stat().st_size for f in OUT_DIR.rglob("*.parquet"))
    print(f"Done: {n:,} rows → {OUT_DIR}  ({size / 1e9:.2f} GB Parquet)")


if __name__ == "__main__":
    main()
