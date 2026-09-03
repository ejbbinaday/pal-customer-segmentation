from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs" / "loyalist_expansion"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Dark theme configuration
BG = "#111827"
PANEL = "#1F2937"
TEXT = "#F9FAFB"
plt.rcParams.update(
    {
        "figure.facecolor": BG,
        "axes.facecolor": PANEL,
        "text.color": TEXT,
        "axes.labelcolor": TEXT,
        "axes.edgecolor": TEXT,
        "xtick.color": TEXT,
        "ytick.color": TEXT,
        "grid.color": "#374151",
        "figure.dpi": 150,
    }
)


def main():
    con = duckdb.connect()

    extract_path = ROOT / "docs" / "new-pal-data" / "newQuery2026Jun_to_2027May.txt.gz"
    parquet_path = ROOT / "data" / "interim" / "pal_features_booking.parquet"

    # We will compute the expanded segments in DuckDB
    # Note: duckdb's read_csv auto_detect handles the BOM in headers.
    # But just in case, we'll try to address UniqueID or "ï»¿DateOfIssuance"

    query = f"""
    WITH extract_data AS (
        SELECT
            *,
            cast("DateOfIssuance" AS DATE) AS issue_date_clean
        FROM read_csv_auto('{extract_path}', header=True, ignore_errors=True)
    ),
    joined AS (
        SELECT
            e.*,
            b.*
        FROM extract_data e
        JOIN '{parquet_path}' b
          ON e.UniqueID = b.customer_id
         AND e.issue_date_clean = b.issue_date
    ),
    waterfall_base AS (
        SELECT
            *,
            -- conditions for rules
            (corp_channel OR (any_business AND lead_days<=7) OR (round_trip AND stay_nights<=1 AND max_tier>=4) OR (round_trip AND lead_days<=3 AND stay_nights<=3 AND any_premium)) AS rule_corp,
            (is_group AND round_trip AND lead_days>=45 AND stay_nights BETWEEN 3 AND 7 AND NOT any_cabin_j) AS rule_mice,
            pilgrimage AS rule_pilgrimage,
            sea_crew AS rule_seacrew,
            (is_international AND round_trip AND stay_nights BETWEEN 90 AND 150) AS rule_intl_student,
            (foreign_issue AND is_international AND max_tier<=4 AND NOT round_trip) AS rule_ofw_1,
            (foreign_issue AND is_international AND max_tier<=4 AND round_trip AND NOT (stay_nights<=3 AND any_premium)) AS rule_balikbayan,
            (any_premium AND round_trip AND lead_days>=30 AND stay_nights>=7) AS rule_ultra_wealthy,
            (any_premium AND is_international) AS rule_premium_bleisure,
            (NOT foreign_issue AND is_international AND NOT any_premium) AS rule_outbound,
            (is_domestic AND NOT any_premium) AS rule_leisure
        FROM joined
    ),
    segments AS (
        SELECT
            *,
            -- Expanded POS 1
            CASE
                WHEN FF_Ind = 1 OR is_award THEN 'Mabuhay Loyalist'
                WHEN rule_corp THEN 'Corporate'
                WHEN rule_mice THEN 'MICE'
                WHEN rule_pilgrimage THEN 'Pilgrimage'
                WHEN rule_seacrew THEN 'OFW/Migrant'
                WHEN rule_intl_student THEN 'Intl. Student'
                WHEN rule_ofw_1 THEN 'OFW/Migrant'
                WHEN rule_balikbayan THEN 'Balikbayan/VFR'
                WHEN rule_ultra_wealthy THEN 'Ultra Wealthy Leisure'
                WHEN rule_premium_bleisure THEN 'Premium Bleisure'
                WHEN rule_outbound THEN 'Outbound International Leisure'
                WHEN rule_leisure THEN 'Leisure'
                ELSE 'Unassigned'
            END AS expanded_pos1_segment,

            -- Expanded POS 3
            CASE
                WHEN rule_corp THEN 'Corporate'
                WHEN rule_mice THEN 'MICE'
                WHEN FF_Ind = 1 OR is_award THEN 'Mabuhay Loyalist'
                WHEN rule_pilgrimage THEN 'Pilgrimage'
                WHEN rule_seacrew THEN 'OFW/Migrant'
                WHEN rule_intl_student THEN 'Intl. Student'
                WHEN rule_ofw_1 THEN 'OFW/Migrant'
                WHEN rule_balikbayan THEN 'Balikbayan/VFR'
                WHEN rule_ultra_wealthy THEN 'Ultra Wealthy Leisure'
                WHEN rule_premium_bleisure THEN 'Premium Bleisure'
                WHEN rule_outbound THEN 'Outbound International Leisure'
                WHEN rule_leisure THEN 'Leisure'
                ELSE 'Unassigned'
            END AS expanded_pos3_segment
        FROM waterfall_base
    )
    SELECT * FROM segments;
    """

    print("Executing DuckDB query...")
    df = con.execute(query).df()
    print(f"Data loaded: {len(df)} rows")

    # 1. Segment size redistribution
    # from proxy_segment to expanded_pos1_segment
    # We want to see who moved TO Mabuhay Loyalist
    shifted_to_loyalist = df[
        (df["expanded_pos1_segment"] == "Mabuhay Loyalist")
        & (df["proxy_segment"] != "Mabuhay Loyalist")
    ]
    original_loyalist = df[df["proxy_segment"] == "Mabuhay Loyalist"]

    from_counts = shifted_to_loyalist["proxy_segment"].value_counts()

    # 2. Mean revenue comparison
    # Parse revenue correctly. Assume 'Revenues w YQ' is float-ish
    df["Revenues_numeric"] = pd.to_numeric(df["Revenues w YQ"], errors="coerce").fillna(0)

    rev_shifted = df.loc[shifted_to_loyalist.index, "Revenues_numeric"].mean()
    rev_original = df.loc[original_loyalist.index, "Revenues_numeric"].mean()

    cv_shifted = (
        df.loc[shifted_to_loyalist.index, "Revenues_numeric"].std() / rev_shifted
        if rev_shifted
        else 0
    )
    cv_original = (
        df.loc[original_loyalist.index, "Revenues_numeric"].std() / rev_original
        if rev_original
        else 0
    )

    rev_expanded_total = df.loc[
        df["expanded_pos1_segment"] == "Mabuhay Loyalist", "Revenues_numeric"
    ].mean()
    cv_expanded_total = (
        df.loc[df["expanded_pos1_segment"] == "Mabuhay Loyalist", "Revenues_numeric"].std()
        / rev_expanded_total
    )

    # 3. Route mix of shifted
    # check is_domestic, is_international
    dom_pct = shifted_to_loyalist["is_domestic"].mean() * 100
    intl_pct = shifted_to_loyalist["is_international"].mean() * 100

    # 4. Profile of shifted
    # already done via from_counts

    # 5. Alternative placement comparison
    sizes_orig = df["proxy_segment"].value_counts()
    sizes_pos1 = df["expanded_pos1_segment"].value_counts()
    sizes_pos3 = df["expanded_pos3_segment"].value_counts()

    sizes_df = (
        pd.DataFrame({"Original": sizes_orig, "Pos1": sizes_pos1, "Pos3": sizes_pos3})
        .fillna(0)
        .astype(int)
    )

    # Write Markdown
    md_content = f"""# Mabuhay Loyalist Expansion Simulation

## 1. Segment Size Redistribution (To Pos 1)
Total newly shifted to Mabuhay Loyalist: {len(shifted_to_loyalist):,}

Where they came from:
"""
    for seg, count in from_counts.items():
        md_content += f"- **{seg}**: {count:,} ({(count / len(shifted_to_loyalist)) * 100:.1f}%)\n"

    md_content += f"""
## 2. Revenue Comparison
| Group | Mean Revenue | Coefficient of Variation (CV) |
|---|---|---|
| Original Loyalist (Award) | ₱{rev_original:,.2f} | {cv_original:.2f} |
| Shifted (FF_Ind=1) | ₱{rev_shifted:,.2f} | {cv_shifted:.2f} |
| Expanded Loyalist Total | ₱{rev_expanded_total:,.2f} | {cv_expanded_total:.2f} |

## 3. Route Mix of Shifted Bookings
- **Domestic**: {dom_pct:.1f}%
- **International**: {intl_pct:.1f}%

## 4. Alternative Placement (Pos 3 vs Pos 1)
If placed at Position 3 (after Corporate and MICE), how do the segment sizes look?

| Segment | Original | Pos 1 Expansion | Pos 3 Expansion |
|---|---|---|---|
"""
    for seg in sizes_df.index:
        md_content += f"| {seg} | {sizes_df.loc[seg, 'Original']:,} | {sizes_df.loc[seg, 'Pos1']:,} | {sizes_df.loc[seg, 'Pos3']:,} |\n"

    with open(OUTPUT_DIR / "summary.md", "w", encoding="utf-8") as f:
        f.write(md_content)

    # Plot 1: Segment Distribution
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(sizes_df))
    width = 0.25
    ax.bar(x - width, sizes_df["Original"], width, label="Original", color="#3b82f6")
    ax.bar(x, sizes_df["Pos1"], width, label="Expanded Pos1", color="#10b981")
    ax.bar(x + width, sizes_df["Pos3"], width, label="Expanded Pos3", color="#f59e0b")
    ax.set_xticks(x)
    ax.set_xticklabels(sizes_df.index, rotation=45, ha="right")
    ax.legend(facecolor=PANEL, edgecolor=TEXT, labelcolor=TEXT)
    ax.set_title("Segment Size Comparison")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "segment_distribution.png", bbox_inches="tight")
    plt.close()

    # Plot 2: Rev Distribution
    fig, ax = plt.subplots(figsize=(10, 5))
    # Just plot log revenue to handle scale
    # Clip to avoid log(0) issues and extreme outliers
    v_orig = np.log1p(df.loc[original_loyalist.index, "Revenues_numeric"].clip(0, 100000))
    v_shift = np.log1p(df.loc[shifted_to_loyalist.index, "Revenues_numeric"].clip(0, 100000))
    sns.kdeplot(v_orig, ax=ax, label="Original (Award)", color="#3b82f6", fill=True, alpha=0.3)
    sns.kdeplot(v_shift, ax=ax, label="Shifted (FF_Ind=1)", color="#10b981", fill=True, alpha=0.3)
    ax.legend(facecolor=PANEL, edgecolor=TEXT, labelcolor=TEXT)
    ax.set_title("Log Revenue Distribution: Original vs Shifted")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "revenue_distribution.png", bbox_inches="tight")
    plt.close()


if __name__ == "__main__":
    main()
