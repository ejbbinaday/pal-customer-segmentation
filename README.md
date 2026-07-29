# PAL Customer Segmentation

ML framework to auto-classify Philippine Airlines PNRs into actionable revenue segments —
**10 named segments** (see `docs/methodology.md` and `docs/knowledge-base.md`).

Two tracks, two winning approaches:
- **Real 38M-coupon data (active):** the customer base is a **continuum**, not natural clusters — so the
  **rule-based purpose×value segmentation is primary** and model-based clustering *refines and validates* it.
  HDBSCAN is dropped here (categorical-heavy, not density-separable). Confirmed by a ten-method benchmark
  (2026-07-28); the refinement layer (LCA vs GMM) is under review.
- **Prototype tracks (`sample-features.csv`, v3 synthetic):** **HDBSCAN** on penalty-weighted features →
  nearest-centroid mapping to the 10 segments. Retained as the reference implementation.

## Repository layout

```
data/raw/      Source datasets (not all tracked — see .gitignore)
                 sample-features.csv                  real Jan-2025 PAL snapshot (29,999 rows, 27 cols)
                 PAL_PNR_Synthetic_Data_1000-v3.csv   NEW PNR-level prototype data (1,000 rows, 41 cols)
                 PAL_PNR_Synthetic_Data_1000-v2.csv   data dictionary for the v3 schema
                 synthetic_flight_passenger_data.csv  generic synthetic set used by the POC
data/PAL-data/ REAL PAL coupon-level extract — 4 gzipped CSVs, ~38M rows, 40 cols, 2024–2027
                 (git-ignored, local only). newQuery2024 / 2025 / 2026Jan_to_May / 2026Jun_to_2027May
data/interim/  Derived Parquet built from the raw gz (git-ignored):
                 pal_parquet/   typed, zstd, partitioned by iss_year — the fast pipeline input
src/           All Python (analysis pipeline + report/slide generators + shared palette)
docs/          Business + methodology + EDA + monitoring docs, onboarding guide
reports/       Tracked deliverables: HTML EDA report, exported slide PNGs, POC figures
assets/        Presentation sources: kick-off deck (HTML/MD), pitch deck PDF
outputs/       Regenerable analysis artifacts (git-ignored; created by scripts in src/)
```

All scripts resolve paths relative to the repo root via `ROOT = Path(__file__).resolve().parents[1]`,
so they can be run from anywhere (e.g. `python src/hdbscan_final.py`).

## Core pipeline (runs on `data/raw/sample-features.csv`)

| Script | Purpose | Output |
|---|---|---|
| `src/eda_graphs.py`     | Dataset EDA + feature engineering | `outputs/eda_output/` |
| `src/eda_segments.py`   | Proxy-label waterfall + segment EDA | `outputs/eda_output/` |
| `src/cluster_initial.py`| KMeans k=10 baseline | `outputs/cluster_output/` |
| `src/cluster_compare.py`| 7-algorithm leaderboard | `outputs/cluster_compare_output/` |
| `src/dbscan_viz.py`     | DBSCAN deep-dive | `outputs/dbscan_output/` |
| `src/pca_boundaries.py` | Decision-boundary / PCA zoom | `outputs/boundary_output/` |
| `src/hdbscan_final.py`  | **Final model** (HDBSCAN → 10 segments) | `outputs/hdbscan_output/` |
| `src/resample_compare.py`| Resampling study (rejected) | `outputs/resample_output/` |
| `src/monitor_metrics.py`| Production monitoring (DBCV/PSI/ARI/drift) | `outputs/monitor_output/` |
| `src/pal_colors.py`     | Shared segment names + palette (imported everywhere) | — |

## Generators / deliverables

`src/generate_report.py` (HTML EDA report), `src/poc_synthetic.py` + `src/generate_dark_slides.py`
(POC figures), `src/capture_slides.py` (deck → PNGs), `src/dashboard.py` (Streamlit executive dashboard).

> **Streamlit Cloud:** the dashboard entrypoint is now `src/dashboard.py` — update the deployment config.

## v3 prototype (active track)

`src/features_v3.py` implements Stages **P1–P3** of the PNR-level prototype — clean → engineer →
proxy-label waterfall — on `data/raw/PAL_PNR_Synthetic_Data_1000-v3.csv` (see
`docs/methodology.md` §v3 Prototype Pipeline). It exposes `build()` (enriched frame) and
`build_matrix()` (unscaled model matrix), and profiles the features when run:

```bash
python src/features_v3.py     # P1–P3 → outputs/features_v3_output/
python src/prototype_v3.py    # P4–P5 → outputs/prototype_v3_output/
python src/diagnose_v3.py     # structure check (DBCV/ARI/silhouette) → outputs/diagnose_v3_output/
```

`src/prototype_v3.py` runs Stages **P4–P5** (improved): **hold-out split** → compact 24-feature matrix
(mixed-type scaling) → **unweighted** HDBSCAN discovery → inductive nearest-centroid labelling with an
**Unassigned bucket** → cost-matrix + DBCV validation on the **held-out** set. Penalties are used only in
the cost metric (not the feature space); negative learning (P3b) runs in `features_v3.build()`.

> **SME ground truth:** drop `data/labels/sme_sample.csv` (`Unique Identifier`,`true_segment`) and the
> script reports a **non-circular** hold-out recall automatically — see `data/labels/README.md`.

> **Known gap (v3 data):** OFW/Migrant, Pilgrimage, and Mabuhay Loyalist have no proxy seed in the
> v3 synthetic set, so they are not assignable in this prototype (see `docs/knowledge-base.md` §15).
>
> **Honest verdict:** diagnostics (negative DBCV, flat KMeans silhouette) show the v3 synthetic data has
> **no latent cluster structure** — this validates the *approach*, not a result, and the recall numbers
> are circular. Full analysis + recommendations: **`docs/v3-prototype-findings.md`**.

## Real PAL data (38M coupon rows — active)

The real extract in `data/PAL-data/` is coupon/segment-grained (avg ~2.8 coupons per passenger),
far larger than the synthetic prototype. Processing goes through DuckDB / Parquet rather than
in-memory pandas:

```bash
python src/build_parquet.py   # gz → data/interim/pal_parquet/ (one pass, ~90s)
python src/profile_raw.py     # profile → outputs/profile_raw/{summary.md, column_profile.csv}
python src/clean_real.py      # Stage C: clean+flag → data/interim/pal_clean/ + outputs/clean_report/
python src/eda_real.py        # Stage E confirmations → outputs/eda_real/confirmations.md
python src/build_airport_ref.py  # airport→country/region lookup → data/reference/airport_region.csv
python src/features_real.py   # Stage F: booking + customer features + proxy labels → data/interim/pal_features_*
python src/cluster_diagnostic.py  # mixed-type clustering diagnostic (LCA + k-prototypes) → outputs/cluster_diagnostic/
python src/kproto_compare.py  # k-prototypes vs k-modes vs LCA head-to-head (~4 min) → outputs/kproto_compare/
python src/model_stress_test.py  # 10-method / 8-axis benchmark + stress battery (~40 min) → outputs/model_stress_test/
python src/model_stress_test.py --quick   # same, ~8 min, directional only
python src/validate_construct.py  # NON-CIRCULAR: are the segments distinguishable? (~15 min) → outputs/validate_construct/
python src/validate_criterion.py  # NON-CIRCULAR: do segments predict held-out outcomes? (~10 min) → outputs/validate_criterion/
python src/build_pbip.py      # Power BI project reproducing the revenue/PAX mock-up → outputs/pbip/
python src/sub_segment.py     # LCA sub-types within large rule segments → outputs/sub_segments/
python src/export_powerbi.py  # Power BI fact table (coupon + agg grain, ~2 min) → outputs/powerbi_export/
python src/report_figures.py  # real-data EDA + preliminary-cluster figures → outputs/report_real/figs/
python src/build_report.py    # embed figures + render → docs/status-report.{html,pdf}
```

`build_parquet.py` converts the four gz files to a typed, partitioned Parquet dataset (all downstream
steps read this — sub-second queries vs multi-minute gz scans). `profile_raw.py` characterises the raw
data (null rates, cardinality, ranges, coupon→customer grain, money/age sanity, top categories).
`clean_real.py` (Stage C) writes a cleaned, flagged coupon Parquet (`data/interim/pal_clean/`) — farebrand
value tier, date-aware Mabuhay award/group/non-rev flags, flown/open, money flags, parsed routes — plus a
QA report; ~21s streaming, no dedup needed (exact duplicates verified ~0).
`features_real.py` (Stage F) aggregates coupon→booking→customer, joins the airport-region lookup, excludes
all-non-rev customers, engineers the four feature families + loyalty, and applies a prioritized proxy-label
waterfall → `data/interim/pal_features_booking.parquet` (22.9M) + `pal_features_customer.parquet` (13.4M)
+ `outputs/features_real/summary.md`. Includes data guards (UniqueID persistence, currency sanity).
`kproto_compare.py` answers "would k-prototypes/k-modes improve the model?" — a head-to-head against LCA on
the same sample (elbow, ARI vs the rule segments, Gower silhouette, split-half stability, and
sub-segmentation inside the big parents). **Verdict: no** — LCA stays the refinement layer; see
`outputs/kproto_compare/summary.md` and `docs/methodology.md` v0.8.
`model_stress_test.py` + `model_zoo.py` widen that three-way test into a **ten-method, six-family,
eight-axis benchmark**: LCA · GMM (full + diag) · k-prototypes · k-modes · KMeans · SVD+KMeans ·
Spectral(Gower) · Support Vector Clustering · TDA-Mapper, scored on taxonomy agreement, Gower-silhouette
separation, natural-*k* (own criterion + **H0/H1 persistent homology**), split-half and bootstrap
stability, perturbation and leave-one-feature-out robustness, an **SVM separability probe**, and cost.
`model_zoo.py` is the library — one `fit(train, k, test, spec) -> Fit` contract per family, plus the
shared Gower/probe/persistence instruments — and is the file to edit to add a method.
**Verdict:** `GMM(full)` leads the composite (**0.849** vs LCA's 0.763) and still leads with the circular
agreement axis zeroed, so the **refinement layer is under review — but the pipeline is unchanged**, because
this benchmark scores *top-level* segmentation while LCA's job is *sub-segmentation* (needs a stage-matched
re-test first). The **continuum finding is reconfirmed by four independent new tests** and separation
**ceilings at 0.381** across all ten methods. See `outputs/model_stress_test/summary.md` and
`docs/methodology.md` v1.0.
**Plan B — non-circular validation** (`docs/recommendations-plan.md` §Plan B). Every earlier validation number
is measured against `proxy_segment`, which the rules themselves produced. These two scripts need **no ground
truth**, so they work whether or not SME labelling happens.
`validation_anchors.py` is the **circularity contract** and the single source of truth: which fields the rule
waterfall consumes (so they validate nothing), which are *mechanically* tied to trip type (they leak
`round_trip`), and which remain admissible. It raises `CircularityError` rather than warning. Note the subtle
class of leak it handles: `dest_region == 'Domestic'` **is** `is_domestic`, `issue_country != 'PH'` **is**
`foreign_issue`, `channel IN ('TMC','Corporate Web Portal')` **is** `corp_channel` — so those anchors are
admitted **per comparison**, only where the rule bit they encode isn't the boundary under test.
`validate_construct.py` builds a **segment-distinguishability matrix**: for all 45 segment pairs, held-out AUC
from a classifier given only admissible anchors, with a **negative control** (random half-splits, must be
≈0.50 — read it first, it's the harness self-test) and **positive controls** to calibrate the scale. Includes a
dedicated section on **OFW/Migrant vs Balikbayan/VFR** (6.8M bookings, split on the single bit `round_trip`)
and a profile of the 2.19M `Unassigned`.
`validate_criterion.py` runs a **null → segment-only → 11-features → features+segment** ladder against
outcomes no rule consumes (`flown_any`, `refund_any`, `rebook_180d`), reporting *signal retained* and
*incremental value* — because a segmentation is a compression and can never beat the features it came from.
Rare-event outcomes are **reported as infeasible rather than fitted**, and `rebook_180d` excludes
right-censored bookings near the extract boundary.
`build_pbip.py` generates a **Power BI project** (`outputs/pbip/`) reproducing the "Passenger Revenue & PAX
Performance" mock-up: `model.bim` (TMSL — 6 tables, 15 measures, data embedded as inline-CSV Power Query so
the file is self-contained) + `report.json` (60 visual containers) + a PAL theme + CSV fallbacks.
**A `.pbix` cannot be generated programmatically** — its `DataModel` part is a proprietary binary
Analysis Services database, and Power BI Desktop (the only writer) is Windows-only. So the flow is
**File → Open → the `.pbip`**, then **File → Save As → `.pbix`**. Figures are the mock-up's *illustrative*
ones; `outputs/pbip/README.md` records where they diverge from the real extract (real data shows flat revenue
and −1.1% PAX, not +6.2%/+6.5%) and flags that real `NetRevenue` implies **₱163 per passenger**, which is not
a credible fare — units need confirming with PAL before any revenue figure ships.
`export_powerbi.py` joins the booking-grain `proxy_segment` back down onto the cleaned coupons and writes
the **preliminary Power BI star schema** into `outputs/powerbi_export/` — row-preserving (coupons in =
coupons out):

The folder is laid out as a **self-contained handoff** — zip it and send it:

```
outputs/powerbi_export/
├── START-HERE.md                 5-min starter guide (copy of docs/powerbi-guide.md)
├── summary.md                    field dictionary, reconciliation, caveats
├── model/                        ← the three things Power BI actually loads
│   ├── dim_date.csv                 1.8k rows — mark as the Date table
│   ├── fact_flight/                20.6M rows — full dashboard (flight no., O&D, lead time)
│   └── fact_dashboard.parquet       2.1M rows — fast summary-only alternative
├── qa/sample_100k.csv             100k rows — build + validate DAX before moving GBs
└── detail/fact_coupons/           38.1M rows — only for Age / UniqueID
```

Read `outputs/powerbi_export/summary.md` before building measures. The load-bearing caveats:
**default trend visuals to `IsCompleteTravelMonth = TRUE`** — travel months after the extract boundary are
still-filling forward book and will draw a fake cliff; use `IsPrimaryCoupon = TRUE` (one row per booking)
for booking-level measures and `BookingID` to dedupe the per-leg `Route` repetition; `CustomerSegment` is
the **rule-based proxy** label; `PaxCount` is sectoral (≈always 1, *not* party size); `Age` is 57% NULL by
design (filter `AgeKnown`); and **`DaysBeforeMonthEnd` cannot drive LY-vs-CY pickup** (one value per
departure month — use `LeadTimeDays`).
`report_figures.py` draws the real-data EDA + preliminary-cluster (LCA/PCA) figures used in the
shareable status report; `build_report.py` embeds them into a self-contained
**`docs/status-report.html`** and renders **`docs/status-report.pdf`** (a colleague-facing summary of
the approach, methodology, EDA and current status) from the `docs/_status-report.template.html` template.

Key references:
- **`docs/recommendations-plan.md`** — the sequenced plan acting on the 2026-07-28 stress-test findings
  (SME ground truth first, feature-contract gate, GMM confidence layer, pre-registered decision rules,
  and the one gated customer-grain experiment).
- **`docs/mentor-presentation-guide.md`** — talk track for presenting initial findings + next steps
  (TL;DR, 6-beat arc, per-beat script, term explainers, analogy cheat sheet, anticipated Q&A,
  what not to claim).
- **`docs/powerbi-guide.md`** — the colleague-facing Power BI starter guide (star schema, load steps,
  starter DAX, the four gotchas). **Canonical copy** — `export_powerbi.py` copies it into the export
  folder as `START-HERE.md` on every build, since `outputs/` is git-ignored. Edit it here, not there.
- **`docs/data-dictionary.md`** — authoritative field reference (mirror of the client's
  `DataDictionary.v1.xlsx`), incl. the farebrand → value-tier ladder.
- **`docs/real-data-plan.md`** — the cleaning → EDA → feature-engineering plan (grain, decisions).
- **`docs/knowledge-base.md`** §15 — profile findings + dictionary-reconciliation notes.

## Setup

Three dependency files, by purpose:

| File | Use |
|------|-----|
| `requirements.txt` | Lean, dashboard-only — what **Streamlit Cloud** installs |
| `requirements-pipeline.txt` | Full ML/EDA stack to run the `src/` scripts (pinned) |
| `requirements-dev.txt` | ruff · bandit · pre-commit |

```bash
pip install -r requirements-pipeline.txt   # run the pipeline
pip install -r requirements-dev.txt        # + tooling (optional)
```

Tested on Python 3.11–3.14. Clustering output is sensitive to `scikit-learn`/`hdbscan`
versions — keep `requirements-pipeline.txt` pinned.

## Docker (optional — reproducible environment)

Python is pinned to 3.11 in the image, so it builds identically regardless of the host.

```bash
docker build -t pal-segmentation .

# Dashboard (default CMD) → http://localhost:8501
docker run --rm -p 8501:8501 pal-segmentation

# Run a pipeline script, writing figures back to the host
docker run --rm -v "$PWD/outputs:/app/outputs" pal-segmentation python src/hdbscan_final.py
```

Not required for day-to-day prototyping (use the venv above); most useful for guaranteed
reproducibility or an eventual production/PAL handoff.

## Code quality (ruff · bandit · pre-commit)

Dev tooling is configured in `pyproject.toml` (`[tool.ruff]`, `[tool.bandit]`) and
`.pre-commit-config.yaml`. Enable it once:

```bash
pip install -r requirements-dev.txt
pre-commit install                 # run hooks automatically on every git commit
```

Useful commands:

```bash
pre-commit run --all-files         # run every hook across the whole repo
ruff check src/                    # lint
ruff check --fix src/              # lint + auto-fix
ruff format src/                   # format
bandit -c pyproject.toml -r src/   # security scan
pre-commit autoupdate              # bump pinned hook versions
```

Hooks: `ruff` (lint, `--fix`) + `ruff-format`, `bandit` (security), plus whitespace/EOF/YAML/TOML/
large-file checks. `outputs/`, `reports/`, `assets/`, and `scratchpad/` are excluded from linting.
