"""v3 PNR feature engineering — Stages P1–P3 of the v3 prototype pipeline.

Adapts the baseline pipeline to the PNR/coupon-level `PAL_PNR_Synthetic_Data_1000-v3.csv`
schema (see docs/methodology.md §v3 Prototype Pipeline). Framing: anonymous trip-purpose ×
value segmentation at the booking level.

Pipeline:
    load_raw()          → read CSV, repair malformed headers
    clean()             → P1: fix $-suffix money, M/D/YY dates, split cabin, group flag
    engineer()          → P2: value / timing / product-route / party-demo-channel features
    assign_proxy()      → P3: v3 proxy-label waterfall (low → high priority)
    build_matrix()      → assemble the (unscaled) model matrix; scaling happens in clustering

Run as a script to profile the engineered features on the v3 dataset:

    python src/features_v3.py

Writes outputs/features_v3_output/features_v3.csv and prints a summary.
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw" / "PAL_PNR_Synthetic_Data_1000-v3.csv"

# ── Reference tables ────────────────────────────────────────────────────────────

# RBD (booking-class) → fare-value tier: 0 deep-discount econ … 4 business.
# Cabin map given in the data dictionary (economy / premium N,W / business D,C,J).
FARE_TIER = {
    "O": 0,
    "U": 0,
    "T": 0,
    "E": 0,
    "X": 0,  # economy — deep discount
    "K": 1,
    "L": 1,
    "V": 1,
    "Q": 1,
    "S": 1,  # economy — mid
    "Y": 2,
    "B": 2,
    "M": 2,
    "H": 2,  # economy — full / flex
    "N": 3,
    "W": 3,  # premium economy
    "D": 4,
    "C": 4,
    "J": 4,  # business
}
DEEP_DISCOUNT_RBD = {k for k, v in FARE_TIER.items() if v == 0}
FULL_FARE_RBD = {"Y", "B", "M", "H"}

CABIN_ORD = {"Economy": 0, "Premium Economy": 1, "Business": 2}

# Philippine domestic airports (PAL network — non-exhaustive but covers the common ones).
PH_AIRPORTS = {
    "MNL",
    "CEB",
    "DVO",
    "ILO",
    "KLO",
    "PPS",
    "TAG",
    "BCD",
    "CRK",
    "CGY",
    "ZAM",
    "TAC",
    "DGT",
    "GES",
    "LGP",
    "MPH",
    "USU",
    "TUG",
    "SUG",
    "DPL",
    "CGM",
    "JOL",
    "MBT",
    "RXS",
    "SFE",
    "CYZ",
    "WNP",
    "TWT",
    "IGN",
    "BXU",
    "OZC",
    "CBO",
    "DRP",
    "SJI",
    "MRQ",
    "CYP",
    "CRM",
    "TDG",
    "SWL",
    "BSO",
    "ENI",
    "VRC",
    "CYU",
}
# Foreign airport → world region (for haul-type + diaspora signals).
AIRPORT_REGION = {
    # East / SE Asia
    "HND": "Asia",
    "NRT": "Asia",
    "KIX": "Asia",
    "ICN": "Asia",
    "PUS": "Asia",
    "SIN": "Asia",
    "HKG": "Asia",
    "TPE": "Asia",
    "BKK": "Asia",
    "PVG": "Asia",
    "PEK": "Asia",
    "CAN": "Asia",
    "XMN": "Asia",
    "SGN": "Asia",
    "HAN": "Asia",
    "KUL": "Asia",
    "MFM": "Asia",
    "CTU": "Asia",
    "OKA": "Asia",
    "FUK": "Asia",
    # North America (incl. US Pacific)
    "LAX": "NorthAmerica",
    "SFO": "NorthAmerica",
    "JFK": "NorthAmerica",
    "YVR": "NorthAmerica",
    "YOW": "NorthAmerica",
    "YYZ": "NorthAmerica",
    "ORD": "NorthAmerica",
    "SEA": "NorthAmerica",
    "HNL": "NorthAmerica",
    "GUM": "NorthAmerica",
    "OGG": "NorthAmerica",
    "LAS": "NorthAmerica",
    "SAN": "NorthAmerica",
    "EWR": "NorthAmerica",
    "BOS": "NorthAmerica",
    # Middle East (OFW corridors)
    "DXB": "MiddleEast",
    "AUH": "MiddleEast",
    "DOH": "MiddleEast",
    "RUH": "MiddleEast",
    "DMM": "MiddleEast",
    "JED": "MiddleEast",
    "KWI": "MiddleEast",
    "BAH": "MiddleEast",
    # Oceania
    "SYD": "Oceania",
    "MEL": "Oceania",
    "BNE": "Oceania",
    "PER": "Oceania",
    "AKL": "Oceania",
    # Europe
    "LHR": "Europe",
    "CDG": "Europe",
    "FRA": "Europe",
    "AMS": "Europe",
}
DIASPORA_REGIONS = {"MiddleEast", "NorthAmerica", "Oceania", "Europe"}


# ── P1: load & clean ─────────────────────────────────────────────────────────────
def load_raw(path: Path = DATA) -> pd.DataFrame:
    """Read the v3 CSV and repair malformed column headers (e.g. ``CouponNumber] ``)."""
    df = pd.read_csv(path)
    df.columns = [c.replace("]", "").strip() for c in df.columns]
    return df


def _money(series: pd.Series) -> pd.Series:
    """Parse a ``574$`` style money string (trailing ``$``) to float."""
    return pd.to_numeric(
        series.astype(str).str.replace("$", "", regex=False).str.strip(),
        errors="coerce",
    )


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """P1 — apply the v3-specific cleaning quirks. Returns a new frame."""
    df = df.copy()

    # money: $-SUFFIX (not prefix like the baseline pipeline)
    df["net_revenue"] = _money(df["NetRevenue"])
    df["net_fare"] = _money(df["NetFare"])

    # dates: US-style M/D/YY (dayfirst=False — OPPOSITE of the baseline pipeline)
    df["issue_dt"] = pd.to_datetime(df["DateOfIssuance"], format="%m/%d/%y", errors="coerce")
    df["depart_dt"] = pd.to_datetime(df["DepartureDate"], format="%m/%d/%y", errors="coerce")
    df["depart_ts"] = pd.to_datetime(
        df["DepartureDateTime"], format="%m/%d/%y %H:%M:%S", errors="coerce"
    )

    # Group/Individual is text, not the 1/0 the dictionary claims
    df["is_group"] = (df["Group/Individual"].astype(str).str.strip() == "Group").astype(int)

    # OperatingCabinClass is combined "Economy/X" → keep cabin; RBD comes from BookingClass
    df["cabin"] = df["OperatingCabinClass"].astype(str).str.split("/").str[0].str.strip()

    return df


# ── P2: feature engineering ──────────────────────────────────────────────────────
def _dest_region(row) -> str:
    if row["_orig_ph"] and row["_dest_ph"]:
        return "Domestic"
    return AIRPORT_REGION.get(row["_dest"], "Other")


def engineer(df: pd.DataFrame) -> pd.DataFrame:
    """P2 — derive value / timing / product-route / party-demo-channel features."""
    df = df.copy()

    # value / monetary (M of RFM; R & F are not derivable — no passenger key)
    df["ancillary"] = df["net_revenue"] - df["net_fare"]
    df["ancillary_ratio"] = df["ancillary"] / df["net_fare"].replace(0, np.nan)
    df["fare_tier"] = df["BookingClass"].map(FARE_TIER).fillna(0).astype(int)

    # timing / booking behaviour
    df["lead_time"] = (df["depart_dt"] - df["issue_dt"]).dt.days
    df["dep_hour"] = df["depart_ts"].dt.hour
    df["red_eye"] = df["dep_hour"].isin([22, 23, 0, 1, 2, 3, 4, 5]).astype(int)
    df["dep_dow"] = df["depart_ts"].dt.dayofweek
    df["is_weekend"] = df["dep_dow"].isin([5, 6]).astype(int)
    df["dep_month"] = df["depart_dt"].dt.month
    # PH peak-travel seasons: Christmas/balikbayan (Dec), Holy Week (Mar–Apr), summer (May)
    df["is_peak_season"] = df["dep_month"].isin([12, 3, 4, 5]).astype(int)
    df["changed_itinerary"] = (df["CurrentCouponStatus"].astype(str) == "Exchanged").astype(int)

    # product / routing
    df["cabin_ord"] = df["cabin"].map(CABIN_ORD).fillna(0).astype(int)
    df["is_premium_cabin"] = (df["cabin_ord"] >= 1).astype(int)
    df["is_nonstop"] = pd.to_numeric(df["is_nonstop"], errors="coerce").fillna(1).astype(int)
    df["is_connecting"] = (1 - df["is_nonstop"]).astype(int)
    path_len = df["TripOD_Path"].astype(str).str.len()
    df["n_legs"] = (path_len // 3 - 1).clip(lower=1).astype(int)
    df["is_codeshare"] = (df["TripOD"].astype(str) != df["OnlineOD"].astype(str)).astype(int)

    sector = df["Sector"].astype(str)
    df["_orig"] = sector.str[:3]
    df["_dest"] = sector.str[3:6]
    df["_orig_ph"] = df["_orig"].isin(PH_AIRPORTS)
    df["_dest_ph"] = df["_dest"].isin(PH_AIRPORTS)
    df["is_domestic"] = (df["_orig_ph"] & df["_dest_ph"]).astype(int)
    df["dest_region"] = df.apply(_dest_region, axis=1)
    df["haul_type"] = np.where(
        df["is_domestic"] == 1,
        "Domestic",
        np.where(
            df["dest_region"] == "Asia",
            "Regional",
            np.where(df["dest_region"].isin(DIASPORA_REGIONS), "LongHaul", "Other"),
        ),
    )
    df["is_long_haul"] = (df["haul_type"] == "LongHaul").astype(int)
    # booked in a different country than origin → OFW/VFR/agency signal
    df["pos_mismatch"] = (
        df["CountryCodeOfIssue"].astype(str) != df["PointofOrigin"].astype(str)
    ).astype(int)
    df["is_intl_pos"] = (df["CountryCodeOfIssue"].astype(str) != "PH").astype(int)

    # party / demographics
    df["age"] = pd.to_numeric(df["Age"], errors="coerce")
    df["is_child"] = (df["age"] < 12).astype(int)
    df["is_senior"] = (df["age"] >= 60).astype(int)
    df["age_band"] = pd.cut(
        df["age"],
        bins=[0, 12, 25, 60, 200],
        labels=["child", "youth", "adult", "senior"],
        right=False,
    ).astype(str)
    df["gender_male"] = (df["Gender"].astype(str).str.strip() == "Male").astype(int)

    # channel
    df["channel"] = df["Channel"].astype(str).str.strip()
    df["is_gds"] = (df["channel"] == "GDS").astype(int)
    df["is_ota"] = (df["channel"] == "OTA").astype(int)
    df["is_indirect"] = df["channel"].isin(["GDS", "OTA"]).astype(int)
    df["is_direct"] = (1 - df["is_indirect"]).astype(int)
    df["is_regional_carrier"] = (df["OperatingCarrierCode"].astype(str) == "2P").astype(int)

    return df


# ── P3: v3 proxy-label waterfall ─────────────────────────────────────────────────
def assign_proxy(df: pd.DataFrame) -> pd.Series:
    """P3 — rule-based proxy labels, applied low → high priority (higher overwrites).

    Mabuhay Loyalist has no rule (no loyalty field in v3). Rules re-mapped from the
    baseline waterfall to v3 columns — see docs/methodology.md §Stage P3.
    """
    seg = pd.Series("Unassigned", index=df.index, dtype=object)
    econ = df["cabin_ord"] == 0
    anc_hi = df["ancillary"] > df["ancillary"].median()
    short_lead = df["lead_time"] <= 14
    weekday = df["is_weekend"] == 0

    rules = [  # (label, mask) — evaluated in order; later wins
        (
            "Budget/Adventure",
            df["BookingClass"].isin(DEEP_DISCOUNT_RBD) & econ & (df["is_ota"] == 1),
        ),
        (
            "Digital Nomad",
            (df["is_group"] == 0)
            & (df["dest_region"] == "Asia")
            & (df["is_direct"] == 1)
            & (df["lead_time"] >= 60),
        ),
        ("Last-Minute", df["lead_time"] <= 3),
        (
            "Family",
            (df["is_group"] == 1) & econ & ((df["is_weekend"] == 1) | (df["is_child"] == 1)),
        ),
        (
            "Pilgrimage",
            (df["is_group"] == 1)
            & (df["dest_region"] == "MiddleEast")
            & (df["is_peak_season"] == 1),
        ),
        (
            "Balikbayan/VFR",
            (df["_dest_ph"])
            & (df["PointofOrigin"].astype(str) != "PH")
            & (df["is_long_haul"] == 0)
            & econ,
        ),
        (
            "OFW/Migrant",
            (df["pos_mismatch"] == 1)
            & econ
            & ((df["dest_region"] == "MiddleEast") | (df["PointofOrigin"].astype(str) == "AE")),
        ),
        ("Premium Bleisure", (df["cabin_ord"] >= 1) & (df["is_weekend"] == 1) & anc_hi),
        (
            "Corporate",
            (df["cabin_ord"] == 2)
            | (
                (df["BookingClass"].isin(FULL_FARE_RBD))
                & (df["is_gds"] == 1)
                & short_lead
                & weekday
            ),
        ),
    ]
    for label, mask in rules:
        seg[mask.fillna(False)] = label
    return seg


def apply_negative_learning(df: pd.DataFrame, seg: pd.Series) -> pd.Series:
    """P3b — impossibility filters: send contradictory proxy assignments back to Unassigned.

    Re-mapped to v3 fields (the baseline rules keyed on loyalty/bags/income, absent here).
    See docs/methodology.md §Stage P3b.
    """
    seg = seg.copy()
    anc_lo = df["ancillary"] <= df["ancillary"].quantile(0.25)
    nl = [
        # Corporate booked far ahead in economy → not business travel
        (seg == "Corporate") & (df["lead_time"] > 60) & (df["cabin_ord"] == 0),
        # Corporate via OTA → corporate books through GDS / direct, not an OTA
        (seg == "Corporate") & (df["is_ota"] == 1),
        # Digital Nomad is solo by definition
        (seg == "Digital Nomad") & (df["is_group"] == 1),
        # Premium Bleisure with bottom-quartile ancillary contradicts the "premium spend" signal
        (seg == "Premium Bleisure") & anc_lo,
    ]
    for mask in nl:
        seg[mask.fillna(False)] = "Unassigned"
    return seg


# ── model matrix ─────────────────────────────────────────────────────────────────
NUMERIC_FEATURES = [
    "net_fare",
    "net_revenue",
    "ancillary",
    "ancillary_ratio",
    "fare_tier",
    "lead_time",
    "dep_hour",
    "red_eye",
    "is_weekend",
    "is_peak_season",
    "changed_itinerary",
    "cabin_ord",
    "is_premium_cabin",
    "is_nonstop",
    "is_connecting",
    "n_legs",
    "is_codeshare",
    "is_domestic",
    "is_long_haul",
    "pos_mismatch",
    "is_intl_pos",
    "age",
    "is_child",
    "is_senior",
    "gender_male",
    "is_gds",
    "is_ota",
    "is_indirect",
    "is_direct",
    "is_regional_carrier",
]
CATEGORICAL_FEATURES = ["haul_type", "dest_region", "age_band", "channel", "PointofOrigin"]

# Compact, non-redundant subspace (drops the 19 |corr|>0.9 duplicates/complements found in the
# diagnostic). Split by type so P4 can scale continuous features and leave binaries at {0,1}.
CONTINUOUS_FEATURES = [
    "lead_time",
    "net_fare",
    "ancillary",
    "ancillary_ratio",
    "fare_tier",
    "cabin_ord",
    "age",
    "dep_hour",
    "n_legs",
]
BINARY_FEATURES = [
    "red_eye",
    "is_weekend",
    "is_peak_season",
    "changed_itinerary",
    "is_nonstop",
    "is_codeshare",
    "is_domestic",
    "is_long_haul",
    "pos_mismatch",
    "is_group",
    "gender_male",
    "is_gds",
    "is_ota",
    "is_child",
    "is_senior",
]
COMPACT_FEATURES = CONTINUOUS_FEATURES + BINARY_FEATURES


def build_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Full (58-col) numeric + one-hot matrix — kept for the baseline/diagnostic path."""
    num = df[NUMERIC_FEATURES].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    cat = pd.get_dummies(df[CATEGORICAL_FEATURES], prefix_sep="=", dtype=int)
    X = pd.concat([num.reset_index(drop=True), cat.reset_index(drop=True)], axis=1)
    return X, list(X.columns)


def build_compact_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Compact 24-feature matrix (Tier-3 pruning). Unscaled — P4 scales continuous cols only."""
    return (
        df[COMPACT_FEATURES]
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0.0)
        .reset_index(drop=True)
    )


def build(path: Path = DATA, negative_learning: bool = True) -> pd.DataFrame:
    """Full P1–P3(+P3b): load → clean → engineer → proxy label → negative learning."""
    df = engineer(clean(load_raw(path)))
    seg = assign_proxy(df)
    if negative_learning:
        seg = apply_negative_learning(df, seg)
    df["proxy_segment"] = seg
    return df


# ── profiling entry point ────────────────────────────────────────────────────────
def _profile(df: pd.DataFrame, X: pd.DataFrame) -> None:
    print(f"\nrows: {len(df)}   engineered feature matrix: {X.shape[0]} × {X.shape[1]}")

    print("\n=== proxy-label distribution (P3 waterfall) ===")
    vc = df["proxy_segment"].value_counts()
    for seg, n in vc.items():
        print(f"  {seg:20s} {n:4d}  ({n / len(df) * 100:4.1f}%)")
    labelled = (df["proxy_segment"] != "Unassigned").sum()
    print(f"  {'—' * 34}\n  {'labelled':20s} {labelled:4d}  ({labelled / len(df) * 100:4.1f}%)")

    print("\n=== key engineered features (describe) ===")
    cols = [
        "net_revenue",
        "net_fare",
        "ancillary",
        "lead_time",
        "cabin_ord",
        "is_group",
        "is_domestic",
        "is_codeshare",
        "pos_mismatch",
        "age",
    ]
    print(df[cols].describe().round(1).T[["mean", "min", "50%", "max"]].to_string())

    print("\n=== sanity checks ===")
    print(f"  lead_time < 0 (should be 0): {(df['lead_time'] < 0).sum()}")
    print(f"  ancillary < 0 (should be 0): {(df['ancillary'] < 0).sum()}")
    print(f"  NaNs in model matrix (should be 0): {int(X.isna().sum().sum())}")
    print(f"  haul_type mix: {df['haul_type'].value_counts().to_dict()}")


def main() -> None:
    out = ROOT / "outputs" / "features_v3_output"
    out.mkdir(parents=True, exist_ok=True)

    df = build()
    X, _ = build_matrix(df)
    _profile(df, X)

    keep = [c for c in df.columns if not c.startswith("_")]
    df[keep].to_csv(out / "features_v3.csv", index=False)
    X.to_csv(out / "model_matrix_v3.csv", index=False)
    print(f"\nsaved → {out / 'features_v3.csv'}")
    print(f"saved → {out / 'model_matrix_v3.csv'}")


if __name__ == "__main__":
    main()
