"""Leak audit — measure, for every admissible anchor, how much of every rule field it can recover.

`src/validation_anchors.py` declares which fields may validate the proxy segments. Two of its
declarations turned out to be wrong, and both were found by accident rather than by test:

  • **`age_known` encoded `is_international`** (0.86% of domestic bookings capture age vs 87.62% of
    international ones) while sitting in Tier A, i.e. asserted independent of every rule field. It
    inflated the strict `Premium Bleisure vs Budget/Adventure` positive control from 0.553 to 0.948.
  • **`dest_region` encoded `pilgrimage`** — that rule fires on `trip_dest IN ('JED','MED')`, both
    Middle East, so 76.4% of Pilgrimage bookings are Middle East against 3.7% elsewhere.

Finding leaks one at a time, by noticing an implausibly high AUC, is not a method. This script replaces
it with a measurement: fit **one single-feature model per (anchor, rule bit) pair** and report the
held-out AUC. Any cell at or above `LEAK_AUC` means that anchor substantially recovers that rule bit
and **must** appear in `ANCHOR_LEAKS`, or a validation using it is partly circular.

Two layers, and they do different jobs:

  • **this audit is global** — it flags which anchor/bit combinations are capable of leaking anywhere,
    and is the justification for each `ANCHOR_LEAKS` entry.
  • **`admissible_for_groups` is per comparison** — an anchor flagged here is still usable for a pair
    whose two sides do not differ on the bit it encodes. OFW/Migrant vs Balikbayan/VFR are 85.19% vs
    89.18% `age_known`, so the age anchors are legitimately admissible *there*.

**Missingness is audited as its own feature.** A field can be innocent in what it records and still
encode a rule bit in *whether* it was recorded — that is exactly how `age` leaked. So every anchor with
nulls contributes a second row, `<anchor>__isnull`, tested on the null-indicator alone.

The audit also asserts the contract is **self-consistent**: every bit named in `ANCHOR_LEAKS` must be
loaded in `AUDIT_BITS`, or `admissible_for_groups` skips the check (missing column → `continue`) and the
leak ships silently. That check is cheap and would have caught the `pilgrimage` entry being unusable.

Read-only on `data/interim/pal_features_*.parquet`. Writes `outputs/audit_leaks/`.

Run:  python src/audit_leaks.py            # ~3-5 min
      python src/audit_leaks.py --quick    # ~1 min
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from validation_anchors import (
    ANCHOR_LEAKS,
    ANCHORS,
    AUDIT_BITS,
    BASE_WHERE,
    BOOKING,
    CATEGORICAL,
    CUSTOMER,
    SEED,
    TIER_A,
    TOP_CATEGORY_LEVELS,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "audit_leaks"

SAMPLE = 400_000
TEST_FRAC = 0.3
MIN_MINORITY = 500  # below this a bit is too rare to audit reliably

# An anchor at or above this AUC on a single rule bit is recovering it, not corroborating it.
LEAK_AUC = 0.75
# Between these two it is a partial leak: not disqualifying on its own, but it must not be the only
# evidence behind a boundary that turns on that bit.
WATCH_AUC = 0.65

# The rule waterfall's actual decision bits (`src/features_real.py`). Continuous rule inputs are
# binarised at the thresholds the waterfall really uses, not at convenient quantiles — the question is
# whether an anchor recovers *the decision*, not whether it correlates with the raw field.
RULE_BITS: dict[str, str] = {
    "is_award": "is_award::INT",
    "corp_channel": "corp_channel::INT",
    "any_business": "any_business::INT",
    "pilgrimage": "pilgrimage::INT",
    "foreign_issue": "foreign_issue::INT",
    "is_international": "is_international::INT",
    "is_domestic": "is_domestic::INT",
    "round_trip": "round_trip::INT",
    "any_premium": "any_premium::INT",
    "is_group": "is_group::INT",
    "lead_le_3": "(lead_days <= 3)::INT",  # → Last-Minute
    "lead_le_7": "(lead_days <= 7)::INT",  # → Corporate (with any_business)
    "tier_le_4": "(max_tier <= 4)::INT",  # → OFW/Migrant, Balikbayan/VFR
}


def contract_self_check() -> list[str]:
    """Every bit named in ANCHOR_LEAKS must be loaded, and must be a real rule bit.

    A name in ANCHOR_LEAKS that is not in AUDIT_BITS is worse than no entry at all: it reads as a
    guard in the source while `admissible_for_groups` skips it at runtime.
    """
    problems = []
    named = {bit for bits in ANCHOR_LEAKS.values() for bit in bits}
    unloaded = sorted(named - set(AUDIT_BITS))
    if unloaded:
        problems.append(
            f"ANCHOR_LEAKS names {unloaded} but AUDIT_BITS does not load them — "
            "admissible_for_groups will silently skip these checks"
        )
    unknown = sorted(named - set(RULE_BITS))
    if unknown:
        problems.append(f"ANCHOR_LEAKS names {unknown}, which are not rule bits audited here")
    overlap = sorted(set(TIER_A) & set(ANCHOR_LEAKS))
    if overlap:
        problems.append(
            f"{overlap} are in TIER_A (asserted unconditionally independent) *and* in "
            "ANCHOR_LEAKS (known to encode a rule bit) — contradictory"
        )
    return problems


def load(n: int, seed: int = SEED) -> pd.DataFrame:
    """Anchors plus every rule bit, one row per booking, deterministic hash-ordered sample."""
    bits = ", ".join(f"{expr} AS {name}" for name, expr in RULE_BITS.items())
    con = duckdb.connect()
    con.execute("PRAGMA threads=6")
    df = con.execute(f"""
        WITH b AS (
            SELECT customer_id, proxy_segment,
                   age, age_known::INT AS age_known,
                   coalesce(issue_country, 'Unknown') AS issue_country,
                   coalesce(channel, 'Unknown')       AS channel,
                   dep_month::VARCHAR                 AS dep_month,
                   dest_region,
                   {bits}
            FROM read_parquet('{BOOKING}')
            WHERE {BASE_WHERE}
        ),
        j AS (
            SELECT b.*, c.n_bookings
            FROM b LEFT JOIN read_parquet('{CUSTOMER}') c USING (customer_id)
        ),
        r AS (
            SELECT *, row_number() OVER (ORDER BY hash(customer_id || '|' || {seed})) AS rn
            FROM j
        )
        SELECT * EXCLUDE (rn, customer_id) FROM r WHERE rn <= {n}
    """).fetchdf()
    # `dest_region` is left as real NULL for domestic here (not coalesced to 'Domestic' as the
    # validators do) so its missingness can be audited as its own signal — coalescing would fold the
    # null-indicator into a level and hide exactly the kind of leak this script exists to find.
    for c in ("issue_country", "channel"):
        top = df[c].value_counts().head(TOP_CATEGORY_LEVELS).index
        df[c] = df[c].where(df[c].isin(top), "Other")
    return df


def anchor_variants(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """One single-column frame per anchor, plus a `__isnull` variant wherever nulls exist.

    The null variant is the point: `age` leaked `is_international` purely through *whether* it was
    recorded, and no test on its values would ever have shown that.
    """
    out: dict[str, pd.DataFrame] = {}
    for a in ANCHORS:
        if a not in df.columns:
            continue
        col = df[a]
        frame = pd.DataFrame({a: col})
        if a in CATEGORICAL:
            frame[a] = frame[a].astype("category")
        else:
            frame[a] = pd.to_numeric(frame[a], errors="coerce").astype("float64")
        out[a] = frame
        n_null = int(col.isna().sum())
        if 0 < n_null < len(col):
            out[f"{a}__isnull"] = pd.DataFrame({f"{a}__isnull": col.isna().astype(int)})
    return out


def single_feature_auc(X: pd.DataFrame, y: np.ndarray, seed: int = SEED) -> float:
    """Held-out AUC from one feature alone. Direction-free: 1 - auc if it predicts inversely."""
    if len(np.unique(y)) < 2 or min(np.bincount(y)) < MIN_MINORITY:
        return float("nan")
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=TEST_FRAC, random_state=seed, stratify=y)
    is_cat = [str(X[c].dtype) == "category" for c in X.columns]
    m = HistGradientBoostingClassifier(
        categorical_features=is_cat, max_iter=60, learning_rate=0.2, random_state=seed
    ).fit(Xtr, ytr)
    auc = float(roc_auc_score(yte, m.predict_proba(Xte)[:, 1]))
    return round(max(auc, 1.0 - auc), 3)


def verdict(auc: float) -> str:
    if not np.isfinite(auc):
        return "n/a (too rare)"
    if auc >= LEAK_AUC:
        return "LEAK — must be in ANCHOR_LEAKS"
    if auc >= WATCH_AUC:
        return "partial — not sole evidence"
    return "clean"


def audit(df: pd.DataFrame) -> pd.DataFrame:
    variants = anchor_variants(df)
    rows = []
    for bit in RULE_BITS:
        y = df[bit].to_numpy().astype(int)
        rate = float(y.mean())
        for name, X in variants.items():
            auc = single_feature_auc(X, y)
            rows.append(
                {
                    "anchor": name,
                    "rule_bit": bit,
                    "bit_rate": round(rate, 4),
                    "auc": auc,
                    "verdict": verdict(auc),
                    "declared": name.split("__")[0] in ANCHOR_LEAKS
                    and bit in ANCHOR_LEAKS.get(name.split("__")[0], ()),
                }
            )
        print(
            f"  {bit:18s} rate={rate:6.3f}  "
            + " ".join(f"{r['auc']}" for r in rows[-len(variants) :])
        )
    out = pd.DataFrame(rows)
    # An undeclared leak is the failure this script exists to catch: measured as recoverable, but the
    # contract does not withhold it anywhere.
    out["undeclared_leak"] = (out["auc"] >= LEAK_AUC) & ~out["declared"]
    return out.sort_values("auc", ascending=False)


def write_report(tbl: pd.DataFrame, problems: list[str], cfg: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    leaks = tbl[tbl["auc"] >= LEAK_AUC]
    undeclared = tbl[tbl["undeclared_leak"]]
    watch = tbl[(tbl["auc"] >= WATCH_AUC) & (tbl["auc"] < LEAK_AUC)]

    lines = [
        "# Leak audit — can an 'independent' anchor recover a rule field?\n",
        f"Sample: **{cfg['n']:,}** bookings (non-sea-crew), seed {SEED}, held-out "
        f"{int(TEST_FRAC * 100)}%. One single-feature model per (anchor, rule bit) pair. "
        f"Runtime **{cfg['secs'] / 60:.1f} min**."
        + ("  \n**`--quick` run — directional only.**" if cfg["quick"] else ""),
        "\n## 0. Why this exists\n",
        "Two `validation_anchors.py` declarations were wrong, and **both were found by noticing an "
        "implausible AUC rather than by testing**:\n",
        "- **`age_known` encoded `is_international`** while sitting in Tier A (asserted independent of "
        "every rule field). It inflated the strict `Premium Bleisure vs Budget/Adventure` positive "
        "control from **0.553 to 0.948**.\n",
        "- **`dest_region` encoded `pilgrimage`** — that rule fires on `trip_dest IN ('JED','MED')`, "
        "both Middle East.\n",
        "Noticing is not a method. This table is the test.\n",
        f"**Thresholds:** AUC ≥ **{LEAK_AUC}** = leak, must be withheld wherever that bit is the "
        f"boundary under test. **{WATCH_AUC}–{LEAK_AUC}** = partial; usable, but never as the *only* "
        "evidence behind a boundary that turns on that bit. AUC is reported direction-free "
        "(`max(auc, 1-auc)`), since predicting a bit inversely leaks it just as well.\n",
        "## 1. Contract self-consistency\n",
    ]
    if problems:
        lines += [
            "**FAILED** — the contract contradicts itself. Fix before trusting any validator:\n",
            *[f"- {p}" for p in problems],
            "",
        ]
    else:
        lines.append(
            "**PASSED** — every bit named in `ANCHOR_LEAKS` is loaded by `AUDIT_BITS`, is a real rule "
            "bit, and no anchor is simultaneously in `TIER_A` and `ANCHOR_LEAKS`.\n"
        )
    lines += [
        "## 2. Undeclared leaks — the actionable result\n",
        "Anchors measured as recovering a rule bit that `ANCHOR_LEAKS` does **not** withhold. Every "
        "row here is a validation result that is partly circular.\n",
    ]
    if len(undeclared):
        lines.append(
            undeclared[["anchor", "rule_bit", "bit_rate", "auc", "declared"]].to_markdown(
                index=False
            )
        )
    else:
        lines.append("**None.** Every measured leak is already declared in the contract.\n")
    lines += [
        f"\n## 3. All declared and measured leaks (AUC ≥ {LEAK_AUC})\n",
        leaks[["anchor", "rule_bit", "bit_rate", "auc", "declared"]].to_markdown(index=False)
        if len(leaks)
        else "_none_",
        f"\n## 4. Partial leaks ({WATCH_AUC}–{LEAK_AUC})\n",
        "Not disqualifying. The rule is that a boundary turning on one of these bits must not rest on "
        "the paired anchor alone.\n",
        watch[["anchor", "rule_bit", "bit_rate", "auc"]].to_markdown(index=False)
        if len(watch)
        else "_none_",
        "\n## 5. Full matrix\n",
        tbl.pivot_table(index="anchor", columns="rule_bit", values="auc").round(3).to_markdown(),
        "\n## 6. How to read a `__isnull` row\n",
        "`<anchor>__isnull` tests the **null-indicator alone** — nothing about the recorded value. A "
        "high AUC there means the field leaks a rule bit through *whether it was captured*, which is "
        "how `age` leaked `is_international`: international travel collects passport data and domestic "
        "travel does not, so presence-vs-absence **is** the rule bit. A tree model reads that pattern "
        "directly, so imputing the field does not remove the leak — withholding it does.\n",
        "## 7. Limits\n",
        f"- **Single-feature only.** Two anchors that each score below {LEAK_AUC} can still recover a "
        "bit jointly. This audit bounds the per-anchor leak, not the leak of an arbitrary subset.\n",
        "- **Population-level.** A flagged anchor is still admissible for a comparison whose two sides "
        "do not differ on the bit it encodes — that is `admissible_for_groups`' job, and the reason "
        "the OFW-vs-Balikbayan result keeps the age anchors.\n",
        f"- **Rare bits are skipped**, not fitted: fewer than {MIN_MINORITY:,} minority events returns "
        "`n/a` rather than a number computed on noise.\n",
        "- **Thresholds are conventions**, fixed before the numbers were seen. They are not "
        "distributional tests.\n",
    ]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n")
    tbl.to_csv(OUT / "leak_matrix.csv", index=False)
    print("\nWrote", OUT / "summary.md")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="smaller sample")
    args = ap.parse_args()
    n = 80_000 if args.quick else SAMPLE
    t0 = time.time()

    problems = contract_self_check()
    print("Contract self-check:", "PASSED" if not problems else "FAILED")
    for p in problems:
        print("  ✗", p)

    print(f"\nLoading {n:,} bookings ...")
    df = load(n)
    print(f"  {len(df):,} rows · auditing {len(ANCHORS)} anchors × {len(RULE_BITS)} rule bits")

    print("\nAuditing (one single-feature fit per cell) ...")
    tbl = audit(df)

    write_report(tbl, problems, {"n": len(df), "secs": time.time() - t0, "quick": args.quick})

    undeclared = tbl[tbl["undeclared_leak"]]
    print()
    if len(undeclared):
        print(f"⚠ {len(undeclared)} UNDECLARED LEAK(S):")
        print(undeclared[["anchor", "rule_bit", "auc"]].to_string(index=False))
    else:
        print("No undeclared leaks.")


if __name__ == "__main__":
    main()
