"""Build the airport references → `data/reference/airport_region.csv` + `route_theme.csv`.

**Two files, two jobs — deliberately kept apart.**

`airport_region.csv` — country/region/`is_domestic` for the **97 airport codes present as `Sector`
endpoints** in the real PAL data, i.e. the PR-operated network. This is load-bearing: Stage F joins
it to split domestic from international (EDA A6: value is non-discriminative, so route separates
domestic-budget from international-OFW/diaspora). Classification is by each airport's own country
(not its PAL partner). A handful of low-volume PH strips (BPA/BSI/KTI) pair only with PH hubs and
have no plausible international identity → treated as domestic (provisional; refine if PAL supplies
a canonical airport table). Codes not listed resolve to region 'Unknown' downstream.

`route_theme.csv` — airport → **trip-purpose theme**, added 2026-08-17 for the RM-Domestic constraint
sheet (`docs/sme-constraints-intake.md` §4). Descriptive only: nothing in the proxy waterfall reads
it. Kept in its own file for two reasons:

  1. **It is keyed on trip endpoints, not sectors.** `TripOD` includes OAL codeshare beyond-points,
     so FCO/TLV/CDG/LIS appear as trip destinations while never being PR sector endpoints — they are
     absent from `airport_region.csv` by design and must not be added there, where a new row could
     perturb the domestic/international split.
  2. **`is_domestic` is in the model; themes are not.** Separating them keeps an experimental,
     SME-supplied taxonomy from silently entering a load-bearing join.

⚠️ **One theme per airport is a simplification, and the SME's own lists overlap.** SYD and MEL are
premium-holiday destinations *and* major Filipino diaspora hubs; HNL is both a US point and a
holiday endpoint; JED/MED are Gulf points *and* the Hajj/Umrah hubs. Where the SME named an airport
under a theme, their assignment wins; the most *specific* purpose wins otherwise (JED/MED are
pilgrimage, not labour). Any analysis turning on one of these dual-identity airports must say which
reading it took. Volumes for every theme are in `outputs/constraint_coverage/summary.md`.

Run:
    python src/build_airport_ref.py     → data/reference/{airport_region,route_theme}.csv (tracked)
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "reference" / "airport_region.csv"
THEME_OUT = ROOT / "data" / "reference" / "route_theme.csv"

# ── trip-purpose themes (see module docstring for the overlap caveat) ────────────────
# Provenance per theme:
#   SME     — named explicitly in the RM-Domestic constraint sheet
#   ours    — our own grouping, not asserted by an SME
# `in_network` = 0 marks a trip endpoint PAL reaches only via OAL codeshare, so it is
# absent from airport_region.csv. Those carry very little traffic — measured, not assumed:
# FCO 4,379 · TLV 16,990 · CDG 5,408 · LIS 1,447 trip endpoints, against 70,650 for JED+MED.
ROUTE_THEMES: dict[str, tuple[str, list[str]]] = {
    # theme: (provenance, airports)
    "gulf_labour": ("SME", ["DXB", "DOH", "RUH", "DMM"]),
    "islamic_pilgrimage": ("SME", ["JED", "MED"]),
    "catholic_pilgrimage": ("SME", ["FCO", "TLV", "CDG", "LIS"]),
    # SME grouped HKG/TPE with the Gulf as "labour". Our probe refuted that — only 1.93% of
    # their round trips sit in the 28–32 night window vs 19.11% for the Gulf, and pooling them
    # drops discrimination below chance (AUC 0.375 vs 0.676 Gulf-only). Named neutrally and
    # kept separate so nobody re-pools them by accident. See knowledge-base §15, 2026-08-17.
    "east_asia_hub": ("ours (SME grouping refuted)", ["HKG", "TPE"]),
    "asian_tourist_hub": ("SME", ["BKK", "SIN", "ICN", "NRT"]),
    "domestic_leisure": ("SME", ["MPH", "PPS", "USU", "IAO"]),
    "premium_holiday": ("SME", ["HNL", "SYD", "CTS", "MEL"]),
    "diaspora_north_america": ("ours", ["LAX", "SFO", "JFK", "SEA", "ORD", "YVR", "YYZ", "GUM"]),
}

# Endpoints PAL reaches only through codeshare — present in TripOD, absent from the sector network.
OUT_OF_NETWORK = frozenset({"FCO", "TLV", "CDG", "LIS"})

# region → list of (airport_code, country_code)
REGIONS: dict[str, list[tuple[str, str]]] = {
    "Philippines": [  # domestic
        ("MNL", "PH"),
        ("CEB", "PH"),
        ("DVO", "PH"),
        ("MPH", "PH"),
        ("CGY", "PH"),
        ("ILO", "PH"),
        ("BCD", "PH"),
        ("PPS", "PH"),
        ("TAC", "PH"),
        ("GES", "PH"),
        ("TAG", "PH"),
        ("DRP", "PH"),
        ("ZAM", "PH"),
        ("USU", "PH"),
        ("DGT", "PH"),
        ("IAO", "PH"),
        ("CBO", "PH"),
        ("LAO", "PH"),
        ("OZC", "PH"),
        ("CRK", "PH"),
        ("RXS", "PH"),
        ("DPL", "PH"),
        ("BXU", "PH"),
        ("KLO", "PH"),
        ("TWT", "PH"),
        ("BSO", "PH"),
        ("TUG", "PH"),
        ("EUQ", "PH"),
        ("BAG", "PH"),
        ("BQA", "PH"),
        ("CRM", "PH"),
        ("CYP", "PH"),
        ("CYZ", "PH"),
        ("CGM", "PH"),
        ("MRQ", "PH"),
        ("PAG", "PH"),
        ("BPA", "PH"),
        ("BSI", "PH"),
        ("KTI", "PH"),
    ],
    "North America": [
        ("LAX", "US"),
        ("SFO", "US"),
        ("JFK", "US"),
        ("ORD", "US"),
        ("SEA", "US"),
        ("HNL", "US"),
        ("LIH", "US"),
        ("ANC", "US"),
        ("YVR", "CA"),
        ("YYZ", "CA"),
    ],
    "Oceania": [
        ("SYD", "AU"),
        ("MEL", "AU"),
        ("BNE", "AU"),
        ("PER", "AU"),
        ("POM", "PG"),
        ("ROR", "PW"),
        ("GUM", "US"),
        ("SPN", "US"),
    ],
    "East Asia": [
        ("HKG", "HK"),
        ("MFM", "MO"),
        ("TPE", "TW"),
        ("ICN", "KR"),
        ("PUS", "KR"),
        ("CJU", "KR"),
        ("YNY", "KR"),
        ("NRT", "JP"),
        ("HND", "JP"),
        ("KIX", "JP"),
        ("NGO", "JP"),
        ("FUK", "JP"),
        ("CTS", "JP"),
        ("PVG", "CN"),
        ("PEK", "CN"),
        ("CAN", "CN"),
        ("XMN", "CN"),
        ("JJN", "CN"),
        ("XIY", "CN"),
    ],
    "Southeast Asia": [
        ("BKK", "TH"),
        ("SIN", "SG"),
        ("KUL", "MY"),
        ("CGK", "ID"),
        ("DPS", "ID"),
        ("SGN", "VN"),
        ("HAN", "VN"),
        ("DAD", "VN"),
        ("PNH", "KH"),
        ("VTE", "LA"),
        ("BWN", "BN"),
    ],
    "South Asia": [("DEL", "IN"), ("BLR", "IN")],
    "Middle East": [
        ("DXB", "AE"),
        ("DOH", "QA"),
        ("RUH", "SA"),
        ("DMM", "SA"),
        ("JED", "SA"),
        ("MED", "SA"),
    ],
    "Europe": [("CPH", "DK"), ("IST", "TR")],
}


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    seen = set()
    for region, airports in REGIONS.items():
        for code, country in airports:
            if code in seen:
                raise ValueError(f"duplicate airport code {code}")
            seen.add(code)
            rows.append(
                {
                    "airport": code,
                    "country": country,
                    "region": region,
                    "is_domestic": int(country == "PH"),
                }
            )
    rows.sort(key=lambda r: r["airport"])
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["airport", "country", "region", "is_domestic"])
        w.writeheader()
        w.writerows(rows)

    n_dom = sum(r["is_domestic"] for r in rows)
    print(
        f"Wrote {OUT}  ({len(rows)} airports: {n_dom} PH-domestic, {len(rows) - n_dom} international)"
    )
    write_themes(seen)


def write_themes(sector_airports: set[str]) -> None:
    """Emit route_theme.csv, asserting the one-theme-per-airport invariant."""
    trows, assigned = [], {}
    for theme, (provenance, airports) in ROUTE_THEMES.items():
        for code in airports:
            if code in assigned:
                raise ValueError(
                    f"{code} claimed by both '{assigned[code]}' and '{theme}' — themes must be "
                    "mutually exclusive; resolve in ROUTE_THEMES, not downstream"
                )
            assigned[code] = theme
            trows.append(
                {
                    "airport": code,
                    "theme": theme,
                    "provenance": provenance,
                    # 1 = also a PR sector endpoint; 0 = reachable only as an OAL codeshare
                    # beyond-point, so it appears in TripOD but not in airport_region.csv
                    "in_network": int(code in sector_airports),
                }
            )
    # Guard: anything we flagged as out-of-network must genuinely be absent from the sector list,
    # otherwise the two references have drifted apart.
    for code in sorted(OUT_OF_NETWORK):
        if code in sector_airports:
            raise ValueError(
                f"{code} is marked OUT_OF_NETWORK but is a sector endpoint in airport_region.csv"
            )
    trows.sort(key=lambda r: (r["theme"], r["airport"]))
    with THEME_OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["airport", "theme", "provenance", "in_network"])
        w.writeheader()
        w.writerows(trows)
    n_oon = sum(1 for r in trows if not r["in_network"])
    print(
        f"Wrote {THEME_OUT}  ({len(trows)} airports across {len(ROUTE_THEMES)} themes; "
        f"{n_oon} reachable only via codeshare)"
    )


if __name__ == "__main__":
    main()
