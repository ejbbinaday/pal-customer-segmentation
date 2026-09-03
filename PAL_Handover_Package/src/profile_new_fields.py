from pathlib import Path

import duckdb

from parse_fare_basis import FARE_BASIS_SQL_COLUMNS


def main():
    ROOT = Path(__file__).resolve().parents[1]
    NEW_EXTRACT = ROOT / "docs" / "new-pal-data" / "newQuery2026Jun_to_2027May.txt.gz"
    FEATURES = ROOT / "data" / "interim" / "pal_features_booking.parquet"
    OUTPUT_DIR = ROOT / "outputs" / "new_fields_profile"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.execute("PRAGMA threads=6")
    con.execute("SET memory_limit='8GB'")

    print("Loading data into DuckDB...")

    # We use normalize_names to safely handle BOM and avoid exact case mismatches
    con.execute(f"""
        CREATE VIEW new_extract AS
        SELECT
            uniqueid AS customer_id,
            cast(dateofissuance AS DATE) AS issue_date,
            farebasiscode AS fare_basis,
            tourcode,
            revpaxind,
            itintype,
            ff_ind
        FROM read_csv_auto('{NEW_EXTRACT}', normalize_names=True, ignore_errors=True)
    """)

    con.execute(f"""
        CREATE VIEW features AS
        SELECT *
        FROM read_parquet('{FEATURES}')
    """)

    # Check if is_nonrev exists, else fallback to is_award
    cols = [r[0] for r in con.execute("DESCRIBE features").fetchall()]
    nonrev_col = "is_nonrev" if "is_nonrev" in cols else "is_award"

    print("Joining data...")
    # Join new_extract with features
    con.execute(f"""
        CREATE TABLE joined_data AS
        SELECT
            n.*,
            f.proxy_segment,
            f.is_international,
            f.is_domestic,
            f.is_group,
            f.corp_channel,
            f.{nonrev_col} AS derived_nonrev
        FROM new_extract n
        LEFT JOIN features f
            ON n.customer_id = f.customer_id
            AND n.issue_date = f.issue_date
    """)

    print("Executing queries...")

    out_md = []
    out_md.append("# New Fields Profile Report")

    total_rows = con.execute("SELECT COUNT(*) FROM joined_data").fetchone()[0]
    out_md.append(f"**Total rows analyzed:** {total_rows:,}\n")

    # 1. FF_Ind
    out_md.append("## 1. Frequent Flyer Indicator (`FF_Ind`)")
    ff_dist = con.execute("""
        SELECT
            proxy_segment,
            COUNT(*) as total,
            SUM(CASE WHEN CAST(ff_ind AS VARCHAR) = '0' THEN 1 ELSE 0 END) as ff_0,
            SUM(CASE WHEN CAST(ff_ind AS VARCHAR) = '1' THEN 1 ELSE 0 END) as ff_1,
            SUM(CASE WHEN CAST(ff_ind AS VARCHAR) = '2' THEN 1 ELSE 0 END) as ff_2,
            ROUND(SUM(CASE WHEN CAST(ff_ind AS VARCHAR) = '1' THEN 1 ELSE 0 END)*100.0 / NULLIF(COUNT(*), 0), 2) as enroll_rate_pct
        FROM joined_data
        GROUP BY proxy_segment
        ORDER BY enroll_rate_pct DESC
    """).fetchdf()
    out_md.append(ff_dist.to_markdown(index=False))

    # Hypothesis test: OFW vs Balikbayan
    ofw_rate = ff_dist.loc[ff_dist["proxy_segment"] == "OFW/Migrant", "enroll_rate_pct"].values
    bb_rate = ff_dist.loc[ff_dist["proxy_segment"] == "Balikbayan/VFR", "enroll_rate_pct"].values
    if len(ofw_rate) > 0 and len(bb_rate) > 0:
        out_md.append(
            f"\n**Hypothesis Test:** OFW enroll rate ({ofw_rate[0]}%) vs Balikbayan enroll rate ({bb_rate[0]}%)"
        )
        if ofw_rate[0] < bb_rate[0]:
            out_md.append("-> True: OFW has a lower FF_Ind=1 rate than Balikbayan.")
        else:
            out_md.append("-> False: OFW does NOT have a lower FF_Ind=1 rate than Balikbayan.")

    # 2. FareBasisCode
    out_md.append("\n## 2. Fare Basis Code (`FareBasisCode`)")
    con.execute(f"""
        CREATE VIEW fb_parsed AS
        SELECT
            proxy_segment,
            fare_basis,
            {FARE_BASIS_SQL_COLUMNS}
        FROM joined_data
        WHERE fare_basis IS NOT NULL
    """)

    top_fb = con.execute("""
        WITH ranked AS (
            SELECT
                proxy_segment,
                fare_basis_raw,
                COUNT(*) as cnt,
                ROW_NUMBER() OVER(PARTITION BY proxy_segment ORDER BY COUNT(*) DESC) as rn
            FROM fb_parsed
            GROUP BY proxy_segment, fare_basis_raw
        )
        SELECT proxy_segment, fare_basis_raw, cnt
        FROM ranked
        WHERE rn <= 3
        ORDER BY proxy_segment, cnt DESC
    """).fetchdf()
    out_md.append("### Top 3 Fare Basis Codes per Segment")
    out_md.append(top_fb.to_markdown(index=False))

    fb_dist = con.execute("""
        SELECT
            proxy_segment,
            COUNT(*) as total_valid,
            SUM(CASE WHEN fb_season = 'high' THEN 1 ELSE 0 END)*100.0/COUNT(*) as high_pct,
            SUM(CASE WHEN fb_season = 'low' THEN 1 ELSE 0 END)*100.0/COUNT(*) as low_pct,
            SUM(CASE WHEN fb_is_promo THEN 1 ELSE 0 END)*100.0/COUNT(*) as promo_pct,
            SUM(CASE WHEN fb_has_ap THEN 1 ELSE 0 END)*100.0/COUNT(*) as ap_pct
        FROM fb_parsed
        GROUP BY proxy_segment
    """).fetchdf()
    out_md.append("\n### Season/Promo/AP Distributions by Segment")
    out_md.append(fb_dist.to_markdown(index=False))

    # 3. TourCode
    out_md.append("\n## 3. Tour Code (`TourCode`)")
    tc_cov = con.execute("""
        SELECT
            proxy_segment,
            COUNT(*) as total,
            SUM(CASE WHEN tourcode IS NOT NULL AND tourcode != '' THEN 1 ELSE 0 END) as has_tourcode,
            ROUND(SUM(CASE WHEN tourcode IS NOT NULL AND tourcode != '' THEN 1 ELSE 0 END)*100.0/COUNT(*), 2) as coverage_pct
        FROM joined_data
        GROUP BY proxy_segment
        ORDER BY coverage_pct DESC
    """).fetchdf()
    out_md.append("### Coverage Rate by Segment")
    out_md.append(tc_cov.to_markdown(index=False))

    tc_cross = con.execute("""
        SELECT
            is_group,
            corp_channel,
            SUM(CASE WHEN tourcode IS NOT NULL AND tourcode != '' THEN 1 ELSE 0 END) as has_tourcode,
            COUNT(*) as total,
            ROUND(SUM(CASE WHEN tourcode IS NOT NULL AND tourcode != '' THEN 1 ELSE 0 END)*100.0/COUNT(*), 2) as coverage_pct
        FROM joined_data
        GROUP BY is_group, corp_channel
        ORDER BY is_group, corp_channel
    """).fetchdf()
    out_md.append("\n### Cross-tab with is_group and corp_channel")
    out_md.append(tc_cross.to_markdown(index=False))

    # 4. ItinType
    out_md.append("\n## 4. Itinerary Type (`ItinType`)")
    itin_dist = con.execute("""
        SELECT
            proxy_segment,
            itintype,
            COUNT(*) as cnt
        FROM joined_data
        GROUP BY proxy_segment, itintype
        ORDER BY proxy_segment, cnt DESC
    """).fetchdf()
    out_md.append("### Distribution by Segment")
    out_md.append(itin_dist.to_markdown(index=False))

    itin_agree = con.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN
                (itintype = 'Pt-to-Pt' AND is_domestic) OR
                (itintype != 'Pt-to-Pt' AND is_international) -- basic heuristic assumption
                THEN 1 ELSE 0 END) as basic_agreement,
            -- actually let's just see how it aligns
            SUM(CASE WHEN is_domestic AND itintype = 'Pt-to-Pt' THEN 1 ELSE 0 END) as dom_pt_to_pt,
            SUM(CASE WHEN is_international AND itintype != 'Pt-to-Pt' THEN 1 ELSE 0 END) as intl_non_pt_to_pt
        FROM joined_data
        WHERE is_domestic IS NOT NULL OR is_international IS NOT NULL
    """).fetchdf()
    out_md.append("\n### Agreement with Derived Intl/Dom Flags")
    out_md.append(itin_agree.to_markdown(index=False))

    # 5. RevPaxInd
    out_md.append("\n## 5. Revenue Passenger Indicator (`RevPaxInd`)")
    # Note: If is_nonrev wasn't found, we're using is_award as a proxy for derived nonrev
    rev_disc = con.execute("""
        WITH stats AS (
            SELECT
                COUNT(*) as total_rows,
                SUM(CASE WHEN CAST(revpaxind AS VARCHAR) = '0' THEN 1 ELSE 0 END) as new_nonrev,
                SUM(CASE WHEN derived_nonrev THEN 1 ELSE 0 END) as derived_nonrev_flag,
                SUM(CASE WHEN
                    (CAST(revpaxind AS VARCHAR) = '0' AND derived_nonrev) OR
                    (CAST(revpaxind AS VARCHAR) = '1' AND NOT derived_nonrev)
                    THEN 1 ELSE 0 END) as agreement_cnt,
                SUM(CASE WHEN
                    (CAST(revpaxind AS VARCHAR) = '0' AND NOT derived_nonrev) OR
                    (CAST(revpaxind AS VARCHAR) = '1' AND derived_nonrev)
                    THEN 1 ELSE 0 END) as discrepancy_cnt
            FROM joined_data
            WHERE revpaxind IS NOT NULL AND derived_nonrev IS NOT NULL
        )
        SELECT
            *,
            ROUND(discrepancy_cnt*100.0/total_rows, 2) as discrepancy_pct
        FROM stats
    """).fetchdf()
    out_md.append(f"### Discrepancy Rate (vs `{nonrev_col}` flag)")
    out_md.append(rev_disc.to_markdown(index=False))

    out_file = OUTPUT_DIR / "summary.md"
    out_file.write_text("\n".join(out_md))
    print(f"Report written to {out_file}")


if __name__ == "__main__":
    main()
