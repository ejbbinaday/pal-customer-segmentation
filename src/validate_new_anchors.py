import argparse
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OrdinalEncoder

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "validate_new_anchors"
OUT.mkdir(parents=True, exist_ok=True)

# Colors
BG = "#111827"
PANEL = "#1F2937"
TEXT = "#F9FAFB"


def load_data(quick=False):
    con = duckdb.connect()
    limit_clause = "LIMIT 100000" if quick else ""

    query = f"""
    WITH booking AS (
        SELECT
            customer_id,
            issue_date,
            proxy_segment,
            dep_month,
            COUNT(*) OVER(PARTITION BY customer_id) AS n_bookings
        FROM '{ROOT}/data/interim/pal_features_booking.parquet'
        WHERE proxy_segment != 'OFW/Migrant' OR channel != 'Sea Crew'
    ),
    new_data AS (
        SELECT
            UniqueID,
            TRY_CAST(DateOfIssuance AS DATE) AS DateOfIssuance,
            MAX(FF_Ind) AS FF_Ind,
            MAX(TourCode) AS TourCode,
            MAX(FareBasisCode) AS FareBasisCode,
            MAX(ItinType) AS ItinType
        FROM read_csv_auto('{ROOT}/docs/new-pal-data/newQuery2026Jun_to_2027May.txt.gz', header=True, ignore_errors=True)
        GROUP BY UniqueID, DateOfIssuance
    )
    SELECT
        b.proxy_segment,
        b.dep_month,
        b.n_bookings,
        (n.FF_Ind > 0)::INT AS ff_any,
        (n.FF_Ind = 1)::INT AS ff_mabuhay,
        (n.FF_Ind = 2)::INT AS ff_partner,
        (n.TourCode IS NOT NULL AND n.TourCode != '')::INT AS has_tour_code,
        (SUBSTRING(n.FareBasisCode, 2, 1) = '9')::INT AS fb_is_promo,
        (n.FareBasisCode LIKE '%AP%')::INT AS fb_has_ap,
        (n.FareBasisCode LIKE '%/CH%')::INT AS fb_is_child,
        (n.FareBasisCode LIKE '%/CD%' OR n.FareBasisCode LIKE '%/CS%')::INT AS fb_is_corporate,
        n.ItinType AS itin_type
    FROM booking b
    INNER JOIN new_data n
        ON b.customer_id = n.UniqueID
        AND b.issue_date = n.DateOfIssuance
    {limit_clause}
    """
    df = con.execute(query).df()
    return df


def train_eval_pair(df_pair, features, target_col="target"):
    X = df_pair[features].copy()
    y = df_pair[target_col]

    # Handle categorical — check for any non-numeric dtype or known categoricals
    KNOWN_CAT = {"dep_month", "itin_type", "channel", "issue_country", "dest_region"}
    cat_features = [
        c for c in features if c in KNOWN_CAT or not pd.api.types.is_numeric_dtype(X[c])
    ]
    if cat_features:
        X[cat_features] = X[cat_features].fillna("__MISSING__").astype(str)
        oe = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
        X[cat_features] = oe.fit_transform(X[cat_features])

    X = X.fillna(-999).astype(float)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    clf = HistGradientBoostingClassifier(max_iter=200, max_depth=4, random_state=42)
    clf.fit(X_train, y_train)

    y_pred = clf.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_pred)
    return auc


def get_feature_importances(df_pair, features, target_col="target"):
    X = df_pair[features].copy()
    y = df_pair[target_col]

    cat_features = [
        c
        for c in features
        if c in {"dep_month", "itin_type", "channel", "issue_country", "dest_region"}
        or not pd.api.types.is_numeric_dtype(X[c])
    ]
    if cat_features:
        X[cat_features] = X[cat_features].fillna("__MISSING__").astype(str)
        oe = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
        X[cat_features] = oe.fit_transform(X[cat_features])

    X = X.fillna(-999).astype(float)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    clf = HistGradientBoostingClassifier(max_iter=200, max_depth=4, random_state=42)
    clf.fit(X_train, y_train)

    # Simple permutation importance
    from sklearn.inspection import permutation_importance

    r = permutation_importance(clf, X_test, y_test, n_repeats=5, random_state=42)
    return dict(zip(features, r.importances_mean))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()

    print("Loading data...")
    df = load_data(quick=args.quick)
    print(f"Loaded {len(df)} rows.")

    segments = df["proxy_segment"].dropna().unique()

    old_anchors = ["dep_month", "n_bookings"]
    new_anchors = [
        "ff_any",
        "ff_partner",
        "has_tour_code",
        "fb_is_promo",
        "fb_has_ap",
        "fb_is_child",
        "fb_is_corporate",
        "itin_type",
    ]
    all_anchors = old_anchors + new_anchors

    results = []

    # 7. Negative control
    print("Running negative control...")
    df_neg = df.dropna(subset=["proxy_segment"]).copy()

    # Ensure there are samples
    if len(df_neg) > 0:
        # Sample per segment down to 30000
        parts = []
        for seg in df_neg["proxy_segment"].unique():
            seg_df = df_neg[df_neg["proxy_segment"] == seg]
            parts.append(seg_df.sample(min(len(seg_df), 30000), random_state=42))
        df_neg = pd.concat(parts, ignore_index=True)
        df_neg["target"] = np.random.randint(0, 2, size=len(df_neg))
        neg_auc = train_eval_pair(df_neg, all_anchors, "target")
        print(f"Negative control AUC: {neg_auc:.3f}")
    else:
        neg_auc = 0.5

    print("Running pairwise segment comparisons...")
    import itertools

    feature_imp_records = {}

    for seg1, seg2 in itertools.combinations(segments, 2):
        df_pair = df[df["proxy_segment"].isin([seg1, seg2])].copy()

        # sample down to 30,000 per segment
        parts = []
        for seg in [seg1, seg2]:
            seg_df = df_pair[df_pair["proxy_segment"] == seg]
            parts.append(seg_df.sample(min(len(seg_df), 30000), random_state=42))
        df_pair = pd.concat(parts, ignore_index=True)

        c1 = sum(df_pair["proxy_segment"] == seg1)
        c2 = sum(df_pair["proxy_segment"] == seg2)

        if c1 < 400 or c2 < 400:
            continue

        df_pair["target"] = (df_pair["proxy_segment"] == seg2).astype(int)

        auc_old = train_eval_pair(df_pair, old_anchors)
        auc_new = train_eval_pair(df_pair, all_anchors)

        results.append(
            {
                "seg1": seg1,
                "seg2": seg2,
                "auc_old": auc_old,
                "auc_new": auc_new,
                "improvement": auc_new - auc_old,
            }
        )

        key_pairs = [
            {"OFW/Migrant", "Balikbayan/VFR"},
            {"Corporate", "Leisure"},
            {"Corporate", "Premium Bleisure"},
            {"Pilgrimage", "Balikbayan/VFR"},
        ]

        if {seg1, seg2} in key_pairs:
            print(f"Key pair {seg1} vs {seg2} -> Old: {auc_old:.3f}, New: {auc_new:.3f}")
            imp = get_feature_importances(df_pair, all_anchors)
            feature_imp_records[f"{seg1} vs {seg2}"] = imp

    res_df = pd.DataFrame(results)
    if len(res_df) > 0:
        res_df = res_df.sort_values("improvement", ascending=False)

        # Reporting
        md = [
            "# Construct Validity with New Anchors",
            f"\n**Negative control AUC**: {neg_auc:.3f} (Expected ~0.50)",
            "\n## Pairwise Results",
            res_df.to_markdown(index=False),
            "\n## Key Pair Feature Importances",
        ]

        for pair, imps in feature_imp_records.items():
            md.append(f"\n### {pair}")
            imp_df = pd.DataFrame(
                list(imps.items()), columns=["Feature", "Importance"]
            ).sort_values("Importance", ascending=False)
            md.append(imp_df.to_markdown(index=False))

        (OUT / "summary.md").write_text("\n".join(md))
        print(f"Wrote report to {OUT / 'summary.md'}")

        # Heatmaps
        plt.style.use("dark_background")
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
        fig.patch.set_facecolor(BG)

        # Pivot
        pivot_old = res_df.pivot(index="seg1", columns="seg2", values="auc_old").fillna(0)
        pivot_new = res_df.pivot(index="seg1", columns="seg2", values="auc_new").fillna(0)

        sns.heatmap(pivot_old, ax=ax1, cmap="viridis", annot=True, fmt=".2f")
        ax1.set_title("AUC (Old Anchors)")

        sns.heatmap(pivot_new, ax=ax2, cmap="viridis", annot=True, fmt=".2f")
        ax2.set_title("AUC (Old + New Anchors)")

        plt.tight_layout()
        plt.savefig(OUT / "heatmap.png", facecolor=BG)
        plt.close()

        # Bar chart
        plt.figure(figsize=(12, 8))
        plt.gcf().patch.set_facecolor(BG)
        res_df_sorted = res_df.sort_values("improvement", ascending=True)
        labels = res_df_sorted["seg1"] + " vs " + res_df_sorted["seg2"]
        plt.barh(labels, res_df_sorted["improvement"], color="skyblue")
        plt.title("AUC Improvement with New Anchors")
        plt.tight_layout()
        plt.savefig(OUT / "improvement_bar.png", facecolor=BG)
        plt.close()

    print("Finished.")


if __name__ == "__main__":
    main()
