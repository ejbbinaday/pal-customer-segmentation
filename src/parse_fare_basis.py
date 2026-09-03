"""Parse PAL fare basis codes per the Fare Filing nomenclature.

Structure (from PAL's fare filing guide):
  1st char      — RBD (booking class letter, A-Z)
  2nd char      — Seasonal Indicator (H=High/Peak, K=Shoulder, L=Basic/Low; 9=Promo)
  3rd char      — Mid Week/Weekend Indicator
  4th–5th char  — OW Indicator (OW=O, RT=blank) OR Special fare indicator (AP, SC)
  6th char      — Direction (F=From, T=To)
  7th–8th char  — Nation Code (2-letter country)

Suffix after '/' — discount modifiers (CH25=child 25%, CD00=corporate, ID90=industry, etc.)

Reusable: import FARE_BASIS_SQL_COLUMNS for DuckDB SQL, or parse() for Python.
Run standalone for a quick profile:  python src/parse_fare_basis.py
"""

from __future__ import annotations

import re
from dataclasses import dataclass

VALID_RBD = set("JCDIZARWNYSMLHQVBXKETUOGPF")

KNOWN_NATIONS = {
    "PH",
    "US",
    "AU",
    "JP",
    "MY",
    "TH",
    "VN",
    "HK",
    "TW",
    "CA",
    "SG",
    "KR",
    "NZ",
    "GB",
    "DE",
    "FR",
    "IN",
    "AE",
    "SA",
    "QA",
    "BH",
    "KW",
    "CN",
    "ID",
    "DO",
    "GU",
}

SEASON_MAP = {"H": "high", "K": "shoulder", "L": "low", "9": "promo"}


@dataclass
class FareBasis:
    raw: str
    rbd: str = ""
    season: str = "unknown"
    is_promo: bool = False
    midweek_ind: str = ""
    is_oneway: bool = False
    special_fare: str | None = None
    ap_days: int | None = None
    direction: str | None = None
    nation_code: str = ""
    suffix: str | None = None
    is_child: bool = False
    is_corporate_fare: bool = False
    is_industry: bool = False
    is_seaman_fare: bool = False
    is_interline: bool = False


def parse(code: str) -> FareBasis:
    """Parse a single fare basis code."""
    fb = FareBasis(raw=code)
    if not code or len(code) < 2:
        fb.is_interline = True
        if code:
            fb.rbd = code[0].upper()
        return fb

    base = code
    if "/" in code:
        base, fb.suffix = code.split("/", 1)
        s = fb.suffix.upper()
        fb.is_child = s.startswith("CH")
        fb.is_corporate_fare = s.startswith(("CD", "CS"))
        fb.is_industry = s.startswith(("ID", "IN"))

    fb.rbd = base[0].upper()
    if len(base) >= 2:
        c2 = base[1].upper()
        fb.season = SEASON_MAP.get(c2, "unknown")
        fb.is_promo = c2 == "9"

    last2 = base[-2:].upper() if len(base) >= 3 else ""
    if fb.rbd not in VALID_RBD:
        fb.is_interline = True
    elif last2 in KNOWN_NATIONS:
        fb.nation_code = last2

    ap_match = re.search(r"AP(\d+)?", base, re.IGNORECASE)
    if ap_match:
        fb.special_fare = "AP"
        if ap_match.group(1):
            fb.ap_days = int(ap_match.group(1))

    if re.search(r"(?<!^)SC", base, re.IGNORECASE):
        fb.special_fare = "SC"
        fb.is_seaman_fare = True

    if len(base) >= 3 and not fb.is_interline:
        fb.midweek_ind = base[2]
    if len(base) >= 6 and not fb.is_interline:
        c6 = base[5].upper()
        if c6 == "F":
            fb.direction = "from"
        elif c6 == "T":
            fb.direction = "to"

    return fb


# ── DuckDB SQL helpers ───────────────────────────────────────────────────────

FARE_BASIS_SQL_COLUMNS = """
    -- Parsed fare basis columns (pure SQL, no UDF)
    fare_basis                                                  AS fare_basis_raw,
    upper(left(fare_basis, 1))                                  AS fb_rbd,
    CASE upper(substr(fare_basis, 2, 1))
        WHEN 'H' THEN 'high' WHEN 'K' THEN 'shoulder'
        WHEN 'L' THEN 'low'  WHEN '9' THEN 'promo'
        ELSE 'unknown' END                                      AS fb_season,
    (substr(fare_basis, 2, 1) = '9')                            AS fb_is_promo,
    (fare_basis ILIKE '%AP%')                                   AS fb_has_ap,
    CASE WHEN regexp_matches(fare_basis, 'AP(\\d+)')
         THEN cast(regexp_extract(fare_basis, 'AP(\\d+)', 1) AS INTEGER)
         END                                                    AS fb_ap_days,
    (fare_basis ILIKE '%SC%' AND left(fare_basis, 1) != 'S')   AS fb_is_seaman,
    (fare_basis LIKE '%/%')                                     AS fb_has_suffix,
    CASE WHEN fare_basis LIKE '%/%'
         THEN split_part(fare_basis, '/', 2) END                AS fb_suffix,
    (fare_basis LIKE '%/CH%')                                   AS fb_is_child,
    (fare_basis LIKE '%/CD%' OR fare_basis LIKE '%/CS%')        AS fb_is_corporate,
    (fare_basis LIKE '%/ID%' OR fare_basis LIKE '%/IN%')        AS fb_is_industry
"""


if __name__ == "__main__":
    from pathlib import Path

    import duckdb

    ROOT = Path(__file__).resolve().parents[1]
    NEW_EXTRACT = ROOT / "docs" / "new-pal-data" / "newQuery2026Jun_to_2027May.txt.gz"

    con = duckdb.connect()
    print("Profiling fare basis codes ...")
    df = con.execute(f"""
        WITH raw AS (
            SELECT "FareBasisCode" AS fare_basis
            FROM read_csv_auto('{NEW_EXTRACT}', ignore_errors=true)
            WHERE "FareBasisCode" IS NOT NULL AND "FareBasisCode" != ''
        )
        SELECT {FARE_BASIS_SQL_COLUMNS}
        FROM raw
        LIMIT 200000
    """).fetchdf()

    print(f"Rows: {len(df):,}")
    print(f"\nSeason distribution:\n{df['fb_season'].value_counts().to_string()}")
    print(f"\nPromo fares: {df['fb_is_promo'].sum():,} ({100 * df['fb_is_promo'].mean():.1f}%)")
    print(f"\nAP codes: {df['fb_has_ap'].sum():,} ({100 * df['fb_has_ap'].mean():.1f}%)")
    ap = df.loc[df["fb_ap_days"].notna(), "fb_ap_days"]
    if len(ap):
        print(f"  AP values: {ap.value_counts().head(10).to_dict()}")
    print(f"\nSeaman fares: {df['fb_is_seaman'].sum():,}")
    print(
        f"\nSuffix modifiers: {df['fb_has_suffix'].sum():,} ({100 * df['fb_has_suffix'].mean():.1f}%)"
    )
    print(f"  Child: {df['fb_is_child'].sum():,}")
    print(f"  Corporate: {df['fb_is_corporate'].sum():,}")
    print(f"  Industry: {df['fb_is_industry'].sum():,}")
