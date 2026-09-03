from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from scipy.stats import chi2_contingency, ks_2samp

ROOT = Path(__file__).resolve().parents[1]
EXTRACT = ROOT / "docs/new-pal-data/newQuery2026Jun_to_2027May.txt.gz"
BOOKING_FEATURES = ROOT / "data/interim/pal_features_booking.parquet"
OUTPUT_DIR = ROOT / "outputs/gulf_confound"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Dark theme configuration
BG = "#111827"
PANEL = "#1F2937"
TEXT = "#F9FAFB"
plt.rcParams.update(
    {
        "figure.facecolor": BG,
        "axes.facecolor": PANEL,
        "axes.edgecolor": TEXT,
        "axes.labelcolor": TEXT,
        "text.color": TEXT,
        "xtick.color": TEXT,
        "ytick.color": TEXT,
        "grid.color": "#374151",
        "figure.dpi": 300,
    }
)


def main():
    print("Connecting to DuckDB...")
    con = duckdb.connect()

    # We will import FARE_BASIS_SQL_COLUMNS from src/parse_fare_basis.py
    import sys

    sys.path.append(str(ROOT / "src"))
    from parse_fare_basis import FARE_BASIS_SQL_COLUMNS

    # We need to build a query that handles the BOM in the CSV. DuckDB read_csv handles it mostly,
    # but we can query by positional or pattern if needed. `read_csv_auto` usually handles it.

    print("Running query...")
    # Get the raw fare basis codes and join with booking features
    # Note: Extract might have multiple coupons per UniqueID, we just need the booking-level fare info.
    # We'll take the first FareBasisCode for each UniqueID.

    query = f"""
    WITH extract_data AS (
        SELECT
            "UniqueID" as customer_id,
            TRY_CAST(REPLACE("DateOfIssuance", '\xef\xbb\xbf', '') AS DATE) as issue_date,
            first("FareBasisCode") as fare_basis_code,
            string_agg("Sector", ',') as sector,
            string_agg("TripOD", ',') as trip_od
        FROM read_csv_auto('{EXTRACT}', all_varchar=true, ignore_errors=true)
        GROUP BY "UniqueID", TRY_CAST(REPLACE("DateOfIssuance", '\xef\xbb\xbf', '') AS DATE)
    ),
    booking_data AS (
        SELECT *
        FROM read_parquet('{BOOKING_FEATURES}')
    ),
    joined AS (
        SELECT
            e.customer_id,
            e.fare_basis_code as fare_basis,
            e.sector,
            e.trip_od,
            b.round_trip,
            b.stay_nights,
            b.is_international
        FROM extract_data e
        JOIN booking_data b ON e.customer_id = b.customer_id AND e.issue_date = b.issue_date
    ),
    parsed AS (
        SELECT
            j.*,
            {FARE_BASIS_SQL_COLUMNS},
            left(fare_basis, 4) as fare_family,
            -- Check if Gulf airport is in Sector or TripOD
            (regexp_matches(sector, 'DXB|RUH|DMM|DOH|JED|MED|BAH|KWI|MCT|AUH') OR
             regexp_matches(trip_od, 'DXB|RUH|DMM|DOH|JED|MED|BAH|KWI|MCT|AUH')) as is_gulf
        FROM joined j
        WHERE j.fare_basis IS NOT NULL
          AND j.stay_nights IS NOT NULL
          AND j.round_trip = true
    )
    SELECT * FROM parsed
    """

    df = con.execute(query).df()
    print(f"Total round-trip bookings with stay_nights and fare basis: {len(df):,}")

    df_gulf = df[df["is_gulf"]].copy()
    df_non_gulf = df[~df["is_gulf"]].copy()

    print(f"Gulf bookings: {len(df_gulf):,}")
    print(f"Non-Gulf bookings: {len(df_non_gulf):,}")

    if len(df_gulf) == 0:
        print("No Gulf bookings found! Exiting.")
        return

    # a. Fare family clustering
    top_families = df_gulf["fare_family"].value_counts().head(10).index.tolist()

    # e. The 28-32 day spike
    df_gulf["is_28_32_days"] = df_gulf["stay_nights"].between(28, 32)

    # Save markdown report
    report = []
    report.append("# Gulf Confound Resolution")
    report.append(
        "## Objective: Is the 28-32 night stay pattern driven by fare rules or worker leave?"
    )

    report.append("### Fare Families in Gulf Routes")
    fam_counts = df_gulf["fare_family"].value_counts().head(10)
    report.append(fam_counts.to_markdown())

    report.append("### Advance Purchase vs Stay Length")
    ap_stay = df_gulf.groupby("fb_has_ap")["stay_nights"].mean()
    report.append(ap_stay.to_markdown())

    report.append("### Promo vs Published (28-32 days)")
    promo_spike = df_gulf.groupby("fb_is_promo")["is_28_32_days"].mean() * 100
    report.append(promo_spike.to_markdown())

    # Statistical Tests
    # Chi-squared
    top_5_gulf = df_gulf[df_gulf["fare_family"].isin(top_families[:5])]
    contingency = pd.crosstab(top_5_gulf["fare_family"], top_5_gulf["is_28_32_days"])
    chi2, p_chi2, _, _ = chi2_contingency(contingency)

    report.append("### Statistical Tests")
    report.append(f"- **Chi-squared test (Fare Family vs 28-32 days)**: p-value = {p_chi2:.4e}")
    if p_chi2 < 0.05:
        report.append(
            "  - Result: Significant dependence between fare family and the 28-32 day spike."
        )
    else:
        report.append(
            "  - Result: The 28-32 day spike is consistent across top fare families (likely behavioral)."
        )

    # Compare top two families with KS test
    if len(top_families) >= 2:
        f1, f2 = top_families[0], top_families[1]
        dist1 = df_gulf[df_gulf["fare_family"] == f1]["stay_nights"]
        dist2 = df_gulf[df_gulf["fare_family"] == f2]["stay_nights"]
        ks_stat, p_ks = ks_2samp(dist1, dist2)
        report.append(f"- **KS test ({f1} vs {f2})**: p-value = {p_ks:.4e}")

    with open(OUTPUT_DIR / "resolution.md", "w") as f:
        f.write("\\n".join(report))

    # Figures
    # 1. Stay distribution histogram by fare family (Gulf routes)
    plt.figure(figsize=(10, 6))
    for fam in top_families[:5]:
        sns.kdeplot(
            data=df_gulf[df_gulf["fare_family"] == fam],
            x="stay_nights",
            label=fam,
            common_norm=False,
            fill=True,
            alpha=0.3,
        )
    plt.xlim(0, 90)
    plt.title("Stay Distribution by Top Fare Families (Gulf Routes)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "gulf_stay_dist.png")
    plt.close()

    # 2. Heatmap: fare family x stay_nights buckets
    plt.figure(figsize=(12, 8))
    bins = [0, 7, 14, 21, 28, 32, 45, 60, 90, 180, 365]
    df_gulf_top = df_gulf[df_gulf["fare_family"].isin(top_families[:10])].copy()
    df_gulf_top["stay_bucket"] = pd.cut(df_gulf_top["stay_nights"], bins)
    heatmap_data = (
        pd.crosstab(df_gulf_top["fare_family"], df_gulf_top["stay_bucket"], normalize="index") * 100
    )
    sns.heatmap(heatmap_data, annot=True, fmt=".1f", cmap="magma")
    plt.title("Stay Night Buckets by Fare Family (%)")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fare_family_heatmap.png")
    plt.close()

    # 3. Comparison: Gulf vs non-Gulf for the same fare families
    plt.figure(figsize=(10, 6))
    shared_families = set(top_families[:5]).intersection(set(df_non_gulf["fare_family"].unique()))
    if shared_families:
        fam = list(shared_families)[0]
        sns.kdeplot(
            data=df_gulf[df_gulf["fare_family"] == fam],
            x="stay_nights",
            label=f"Gulf ({fam})",
            fill=True,
            alpha=0.5,
        )
        sns.kdeplot(
            data=df_non_gulf[df_non_gulf["fare_family"] == fam],
            x="stay_nights",
            label=f"Non-Gulf ({fam})",
            fill=True,
            alpha=0.5,
        )
        plt.xlim(0, 90)
        plt.title(f"Gulf vs Non-Gulf Stay Distribution: {fam}")
        plt.legend()
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / "gulf_vs_nongulf.png")
    plt.close()


if __name__ == "__main__":
    main()
