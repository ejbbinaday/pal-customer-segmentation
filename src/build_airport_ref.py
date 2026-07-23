"""Build the airport → country/region reference → `data/reference/airport_region.csv`.

Curated lookup covering the **97 airport codes** present in the real PAL data (both `Sector`
endpoints), needed for the domestic-vs-international split that Stage F relies on (EDA A6:
value is non-discriminative, so route separates domestic-budget from international-OFW/diaspora).

Classification is by each airport's own country (not its PAL partner). Region buckets follow
OFW/diaspora corridors. A handful of low-volume PH strips (BPA/BSI/KTI) pair only with PH hubs
and have no plausible international identity → treated as domestic (provisional; refine if PAL
supplies a canonical airport table). Codes not listed here resolve to region 'Unknown' downstream.

Run:
    python src/build_airport_ref.py     → data/reference/airport_region.csv (tracked)
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "reference" / "airport_region.csv"

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


if __name__ == "__main__":
    main()
