from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
EXTRACT = ROOT / "docs/new-pal-data/newQuery2026Jun_to_2027May.txt.gz"
BOOKING_FEATURES = ROOT / "data/interim/pal_features_booking.parquet"

con = duckdb.connect()
print(con.execute(f"DESCRIBE SELECT * FROM read_csv_auto('{EXTRACT}')").df())
print(con.execute(f"DESCRIBE SELECT * FROM read_parquet('{BOOKING_FEATURES}')").df())
