from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import mutual_info_score, roc_auc_score, roc_curve
from sklearn.model_selection import train_test_split

# Styling
BG = "#111827"
PANEL = "#1F2937"
TEXT = "#F9FAFB"
plt.rcParams.update(
    {
        "figure.facecolor": BG,
        "axes.facecolor": PANEL,
        "text.color": TEXT,
        "axes.labelcolor": TEXT,
        "xtick.color": TEXT,
        "ytick.color": TEXT,
        "axes.edgecolor": TEXT,
    }
)

ROOT = Path(__file__).resolve().parents[1]
NEW_EXTRACT = ROOT / "docs/new-pal-data/newQuery2026Jun_to_2027May.txt.gz"
BOOKING_FEATURES = ROOT / "data/interim/pal_features_booking.parquet"
OUTPUT_DIR = ROOT / "outputs/ff_boundary"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

GULF_AIRPORTS = ["DXB", "RUH", "DMM", "DOH", "JED", "MED", "BAH", "KWI", "MCT", "AUH"]


def compute_cohens_h(p1, p2):
    return 2 * np.arcsin(np.sqrt(p1)) - 2 * np.arcsin(np.sqrt(p2))


def main():
    conn = duckdb.connect()
    headers = conn.execute(
        f"DESCRIBE SELECT * FROM read_csv_auto('{NEW_EXTRACT}', ignore_errors=true) LIMIT 1"
    ).df()
    date_col = headers.iloc[0]["column_name"]

    query = f"""
    SELECT
        n.UniqueID as customer_id,
        TRY_CAST(n.FF_Ind AS INTEGER) as FF_Ind,
        n.ItinType,
        n.TourCode,
        n.TripOD,
        TRY_CAST(n."Net Fare" AS DOUBLE) as net_fare,
        TRY_CAST(n."Revenues w YQ" AS DOUBLE) as rev_yq,
        TRY_CAST(n."Pax Count" AS INTEGER) as pax_count,
        b.proxy_segment,
        CAST(b.round_trip AS INTEGER) as round_trip,
        b.dest_last,
        b.origin_first
    FROM read_csv_auto('{NEW_EXTRACT}', ignore_errors=true) n
    INNER JOIN '{BOOKING_FEATURES}' b
        ON n.UniqueID = b.customer_id
        AND TRY_CAST(REPLACE(CAST(n."{date_col}" AS VARCHAR), chr(65279), '') AS DATE) = b.issue_date
    WHERE b.proxy_segment IN ('OFW/Migrant', 'Balikbayan/VFR')
    """
    print("Executing query...")
    df = conn.execute(query).df()
    print(f"Loaded {len(df)} rows.")

    if len(df) == 0:
        print("No data loaded. Check join conditions.")
        return

    # Data prep
    df["is_ofw"] = (df["proxy_segment"] == "OFW/Migrant").astype(int)
    df["has_ff"] = (df["FF_Ind"] > 0).astype(int)
    df["has_tour"] = df["TourCode"].notna().astype(int)
    df["is_gulf"] = df["dest_last"].isin(GULF_AIRPORTS) | df["origin_first"].isin(GULF_AIRPORTS)

    report = ["# FF_Ind Boundary Probe: OFW/Migrant vs Balikbayan/VFR\n"]

    # a. FF_Ind distribution by segment
    ofw_ff_rate = df[df["is_ofw"] == 1]["has_ff"].mean()
    balik_ff_rate = df[df["is_ofw"] == 0]["has_ff"].mean()
    report.append("## A. FF_Ind Distribution by Segment")
    report.append(f"- **OFW/Migrant FF Enrollment Rate:** {ofw_ff_rate:.2%}")
    report.append(f"- **Balikbayan/VFR FF Enrollment Rate:** {balik_ff_rate:.2%}\n")

    # b. Effect size (Cohen's h and Odds Ratio)
    cohens_h = compute_cohens_h(ofw_ff_rate, balik_ff_rate)

    # Odds ratio
    a = df[(df["is_ofw"] == 1) & (df["has_ff"] == 1)].shape[0]
    b = df[(df["is_ofw"] == 1) & (df["has_ff"] == 0)].shape[0]
    c = df[(df["is_ofw"] == 0) & (df["has_ff"] == 1)].shape[0]
    d = df[(df["is_ofw"] == 0) & (df["has_ff"] == 0)].shape[0]

    odds_ratio, p_value = (
        stats.fisher_exact([[a, b], [c, d]]) if (a * b * c * d) > 0 else (np.nan, np.nan)
    )

    report.append("## B. Effect Size")
    report.append(f"- **Cohen's h:** {cohens_h:.3f} (Small: 0.2, Medium: 0.5, Large: 0.8)")
    report.append(f"- **Odds Ratio:** {odds_ratio:.3f} (p-value: {p_value:.4e})\n")

    # c. Cross-tabulation: FF_Ind x round_trip x proxy_segment
    report.append("## C. Cross-tabulation (FF_Ind x Round Trip)")
    crosstab = pd.crosstab(df["proxy_segment"], [df["has_ff"], df["round_trip"]], normalize="index")
    report.append("```\n" + crosstab.to_string() + "\n```\n")

    # d. Mutual information
    mi = mutual_info_score(df["has_ff"], df["round_trip"])
    report.append("## D. Mutual Information")
    report.append(f"- **MI between FF_Ind and round_trip:** {mi:.5f}\n")

    # e. ItinType x FF_Ind interaction
    itin_ff = df[df["is_ofw"] == 1].groupby("ItinType")["has_ff"].mean()
    report.append("## E. ItinType Interaction (OFW only)")
    for itin, rate in itin_ff.items():
        report.append(f"- {itin}: {rate:.2%}")
    report.append("\n")

    # f. Gulf vs Non-Gulf
    gulf_ofw_ff = df[(df["is_ofw"] == 1) & df["is_gulf"]]["has_ff"].mean()
    nongulf_ofw_ff = df[(df["is_ofw"] == 1) & ~df["is_gulf"]]["has_ff"].mean()
    report.append("## F. Gulf vs Non-Gulf (OFW only)")
    report.append(f"- **Gulf OFW FF Rate:** {gulf_ofw_ff:.2%}")
    report.append(f"- **Non-Gulf OFW FF Rate:** {nongulf_ofw_ff:.2%}\n")

    # g. Revenue correlation
    rev_ff = df[(df["is_ofw"] == 1) & (df["has_ff"] == 1)]["rev_yq"].mean()
    rev_noff = df[(df["is_ofw"] == 1) & (df["has_ff"] == 0)]["rev_yq"].mean()
    report.append("## G. Revenue Correlation (OFW only)")
    report.append(f"- **Avg Revenue (FF Enrolled):** {rev_ff:.2f}")
    report.append(f"- **Avg Revenue (Not Enrolled):** {rev_noff:.2f}\n")

    # h. Predictive power
    features = ["has_ff", "has_tour"]
    itin_dummies = pd.get_dummies(df["ItinType"], drop_first=True)

    # Ensure column names are strings
    itin_dummies.columns = [str(c) for c in itin_dummies.columns]

    X = pd.concat([df[features], itin_dummies], axis=1)
    y = df["is_ofw"]

    # Downsample if too large
    if len(X) > 100000:
        X_sample, _, y_sample, _ = train_test_split(
            X, y, train_size=100000, random_state=42, stratify=y
        )
    else:
        X_sample, y_sample = X, y

    X_train, X_test, y_train, y_test = train_test_split(
        X_sample, y_sample, test_size=0.3, random_state=42
    )
    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_pred_proba)

    report.append("## H. Predictive Power")
    report.append(f"- **Logistic Regression AUC (FF_Ind + ItinType + TourCode):** {auc:.4f}\n")

    with open(OUTPUT_DIR / "summary.md", "w") as f:
        f.write("\n".join(report))

    # Figures
    # 1. Grouped bar chart
    fig, ax = plt.subplots(figsize=(8, 6))
    rates = [ofw_ff_rate, balik_ff_rate]
    bars = ax.bar(["OFW/Migrant", "Balikbayan/VFR"], rates, color=["#3b82f6", "#10b981"])
    ax.set_ylabel("FF Enrollment Rate")
    ax.set_title("FF_Ind Distribution by Segment")
    for bar in bars:
        height = bar.get_height()
        ax.annotate(
            f"{height:.2%}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            color=TEXT,
        )
    fig.savefig(OUTPUT_DIR / "ff_distribution.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # 2. Mosaic / Contingency heatmap
    contingency = pd.crosstab(df["proxy_segment"], df["has_ff"], normalize="index")
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(
        contingency,
        annot=True,
        fmt=".2%",
        cmap="Blues",
        cbar=False,
        annot_kws={"color": "black"},
        ax=ax,
    )  # Forced color for visibility
    ax.set_title("FF_Ind x Proxy Segment (Row %)")
    ax.set_xlabel("Has FF")
    ax.set_ylabel("Segment")
    fig.savefig(OUTPUT_DIR / "ff_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # 3. AUC curve
    fpr, tpr, _ = roc_curve(y_test, y_pred_proba)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(fpr, tpr, color="#3b82f6", lw=2, label=f"AUC = {auc:.3f}")
    ax.plot([0, 1], [0, 1], color="#9ca3af", lw=1, linestyle="--")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curve (OFW vs Balikbayan)")
    ax.legend()
    fig.savefig(OUTPUT_DIR / "roc_curve.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    print("Analysis complete. Outputs saved to", OUTPUT_DIR)


if __name__ == "__main__":
    main()
