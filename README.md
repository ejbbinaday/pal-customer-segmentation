# PAL Customer Segmentation

ML framework to auto-classify Philippine Airlines PNRs into actionable revenue segments.
**The shipped model emits 10 named segments + Unassigned; PAL approved a 13-segment taxonomy on
17 Aug 2026** (adding MICE, Ultra Wealthy Leisure and Intl. Student, and turning Last-Minute into a
flag). The two are deliberately kept apart in `src/pal_colors.py` — `SEG_ORDER` is what the model
emits, `SEG_APPROVED` is what PAL agreed; the waterfall change is pending. See
`docs/methodology.md` v1.8 and `docs/sme-constraints-intake.md` §7.

**The active track is the real 38M-coupon extract.** The customer base is a **continuum**, not a set of
natural clusters — so the **rule-based purpose×value segmentation is primary** and model-based clustering
*refines and validates* it. HDBSCAN is dropped here (categorical-heavy, not density-separable). Confirmed
by a ten-method benchmark across six families (2026-07-28) and bounded by a detection-power test
(2026-07-29); the refinement layer (LCA vs GMM) is under review.

The **`sample-features.csv` baseline** (HDBSCAN on penalty-weighted features → nearest-centroid mapping)
is retained as the reference implementation.

## Repository layout

```
data/raw/      Source datasets (not all tracked — see .gitignore)
                 sample-features.csv   real Jan-2025 PAL snapshot (29,999 rows, 27 cols) — baseline
                 (also holds legacy inputs for the superseded prototype track; not part of any deliverable)
data/PAL-data/ REAL PAL coupon-level extract — 4 gzipped CSVs, ~38M rows, 40 cols, 2024–2027
                 (git-ignored, local only). newQuery2024 / 2025 / 2026Jan_to_May / 2026Jun_to_2027May
data/interim/  Derived Parquet built from the raw gz (git-ignored):
                 pal_parquet/   typed, zstd, partitioned by iss_year — the fast pipeline input
data/constraints/ SME business constraints (tracked): hard_constraints.csv (15 impossibility rules) +
                 soft_constraints.csv (42 tendencies) + README.md (column + status guide). Now holds the
                 RM-Domestic workbook response, not just our guesses; each row tagged with provenance,
                 scope and live firing count. NOT wired into the pipeline — enforcing a rule spends a
                 validation anchor. Validate edits: python src/check_constraints.py
                 See docs/sme-constraints-intake.md and docs/stakeholder-report.md §7
data/labels/   SME ground-truth labels (tracked template): sme_sample_TEMPLATE.csv + README.md.
                 Drop sme_sample.csv here to unlock non-circular validation
data/reference/ Curated lookups (tracked, rebuilt by src/build_airport_ref.py):
                 airport_region.csv — 97 PR sector endpoints → country/region/is_domestic (load-bearing:
                   Stage F's domestic/international split joins it)
                 route_theme.csv    — 32 airports → 8 trip-purpose themes (descriptive only; keyed on
                   TRIP endpoints, so codeshare beyond-points FCO/TLV/CDG/LIS resolve). Kept separate
                   from airport_region.csv on purpose — see that script's docstring
wishlist/      Filled-in SME workbooks returned by PAL (tracked, read-only inputs).
                 PALxMAIDA_Constraints&Wishlist.xlsx — 39 new rules from RM Domestic; analysed in
                 docs/sme-constraints-intake.md, transcribed into data/constraints/ (not yet enforced)
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

**Decks** (1600×900 HTML, self-contained — open in a browser, or export to PNG):

| Deck | Source | PNGs |
|---|---|---|
| Kick-off executive deck | `assets/kick-off-call/pal_executive_deck.html` | `python src/capture_slides.py` |
| **Stakeholder deck** — current methodology · business-rule waterfall · success metrics + worked cost calc · SME constraint asks · persona cards | `assets/tuesday-slides/josh-slides.html` | `python src/capture_slides.py --deck tuesday` → `reports/tuesday_slides/` |

`capture_slides.py` takes `--deck <name\|path>` and `--out <dir>`; it screenshots every `.slide`
element. Needs `playwright` + chromium (it installs both on first run).

**Word version of the briefing pack** (`docs/tuesday-punchlist.docx`, for sending to non-technical
readers) — regenerate with **pandoc** after editing the markdown:

```bash
tail -n +3 docs/tuesday-punchlist.md | pandoc -f markdown -o docs/tuesday-punchlist.docx \
  --toc --toc-depth=2 \
  -M title="Tuesday Briefing Pack — PAL Customer Segmentation" \
  -M subtitle="Source content for the 4 August 2026 presentation"
```

`tail -n +3` drops the markdown H1 so it doesn't duplicate the generated title page. The markdown is the
source of truth — edit it, never the `.docx`. The step-flow diagram in that doc is deliberately
**plain-text inside a code fence** rather than Mermaid: pandoc maps it to Consolas with
`xml:space="preserve"`, so the alignment survives in Word, whereas a Mermaid block would have arrived as
raw code.

> **Streamlit Cloud:** the dashboard entrypoint is now `src/dashboard.py` — update the deployment config.

## Prior prototype track (superseded)

An earlier PNR/coupon-level prototype preceded the real-data pipeline and is **superseded** — kept only
as an audit trail. Its scripts (`src/features_v3.py`, `src/prototype_v3.py`, `src/diagnose_v3.py`) remain
in the tree and still run, but **no result from them is quoted in any deliverable**; every current
conclusion rests on the real 38M-coupon extract below. See `docs/methodology.md`
§Prior Prototype Track.

## Real PAL data (38M coupon rows — active)

The real extract in `data/PAL-data/` is coupon/segment-grained (avg ~2.8 coupons per passenger),
far larger than any earlier sample. Processing goes through DuckDB / Parquet rather than
in-memory pandas:

```bash
python src/build_parquet.py   # gz → data/interim/pal_parquet/ (one pass, ~90s)
python src/profile_raw.py     # profile → outputs/profile_raw/{summary.md, column_profile.csv}
python src/clean_real.py      # Stage C: clean+flag → data/interim/pal_clean/ + outputs/clean_report/
python src/eda_real.py        # Stage E confirmations → outputs/eda_real/confirmations.md
python src/build_airport_ref.py  # airport lookups → data/reference/{airport_region,route_theme}.csv
python src/features_real.py   # Stage F: booking + customer features + proxy labels → data/interim/pal_features_*
python src/cluster_diagnostic.py  # mixed-type clustering diagnostic (LCA + k-prototypes) → outputs/cluster_diagnostic/
python src/kproto_compare.py  # k-prototypes vs k-modes vs LCA head-to-head (~4 min) → outputs/kproto_compare/
python src/model_stress_test.py  # 10-method / 8-axis benchmark + stress battery (~40 min) → outputs/model_stress_test/
python src/model_stress_test.py --quick   # same, ~8 min, directional only
python src/validate_construct.py  # NON-CIRCULAR: are the segments distinguishable? (~15 min) → outputs/validate_construct/
python src/validate_criterion.py  # NON-CIRCULAR: do segments predict held-out outcomes? (~10 min) → outputs/validate_criterion/
python src/detection_power.py  # could we have found a segment if one existed? (~25 min) → outputs/detection_power/
python src/detection_power.py --quick    # same, ~1 min, coarse grid, directional only
python src/validate_temporal.py  # out-of-time stability: do the segments hold a year later? (~5 min) → outputs/validate_temporal/
python src/validate_temporal.py --quick  # same, ~1 min, directional only
python src/build_pbip.py      # Power BI project reproducing the revenue/PAX mock-up → outputs/pbip/
python src/sub_segment.py     # LCA sub-types within large rule segments → outputs/sub_segments/
python src/rule_confidence.py # how *determined* is each rule label? (~1 min) → outputs/rule_confidence/
python src/check_constraints.py       # validate data/constraints/*.csv against the feature table (~1 min)
python src/simulate_waterfall_v2.py   # DESIGN ONLY: proposed taxonomy change, before/after + rule check (~1 min)
python src/probe_stay_length.py       # SME claim: does stay length split OFW from Balikbayan? (~30 s) → outputs/stay_length/
(cd src && python probe_constraint_coverage.py)  # all 39 SME rules: evaluable? fires? (~1 min) → outputs/constraint_coverage/
python src/export_powerbi.py  # Power BI fact table (coupon + agg grain, ~2 min) → outputs/powerbi_export/
python src/report_figures.py  # real-data EDA + preliminary-cluster figures → outputs/report_real/figs/
python src/manuscript_figures.py  # manuscript Ch.4 figures from saved CSVs → outputs/report_real/figs/ms_fig*.png
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
`detection_power.py` answers the one challenge the continuum finding could not: **"or are your methods
blind?"** It **appends planted** segments of known prevalence (0.5–10%) and known distinctness to the real
population — each planted row moved a fraction `w` toward a business-plausible archetype, plus a
**random-direction control** so the result can't be an artefact of a lucky guess — then re-fits the
deployable panel (GMM(full) · LCA · KMeans · SVD+KMeans) at k=10 and measures whether the group comes back
out. Detection is best-F1 of any fitted cluster against the planted membership, against a **pre-registered
threshold** set from `w=0` negative controls rather than a round number.
**Verdict:** a **majority of the panel** recovers a planted segment at **≥2% of bookings** (distinctness
≈0.34), ≥5% (≈0.23) and ≥10% (≈0.13) — so the earlier nulls are evidence about PAL's data, not about our
instruments. **But below ~1% prevalence nothing is detected at any distinctness** (~229k bookings), and that
bound must be quoted alongside the continuum finding. Two rules this run establishes: **floors are
majority-rule** — the luckiest of the 12 method × archetype cells would have claimed 0.5% / 0.059 while
groups at 0.555 distinctness were missed elsewhere — and the **H0 significant-component count is retired as a
detector** (1 → 120 across 100 draws of *unchanged* data; median 1, so the continuum reading holds as the
centre of a noisy distribution). `--report-only` rebuilds the summary from saved CSVs without refitting. See
`outputs/detection_power/summary.md`.
`validate_temporal.py` asks whether the segments are still there a year later — everything before it read a
single pooled snapshot. **Read its §0 before doing any temporal analysis on this extract:** the data is
filtered on **departure** date (2024-05-01 → 2027-05-31), *not* issuance, so issuance is truncated at both
ends and naive calendar-year windows report a **fake collapse in lead time** that is pure selection
(excluded early region: mean lead 105 days vs 38 inside the windows). The windows used are two adjacent
12-month issuance spans, 2024-05→2025-04 vs 2025-05→2026-04. Measures share and revenue-mix TVD on the
**full population**, per-segment profile drift on a **stratified** draw (a uniform sample gives
`Mabuhay Loyalist` ~9 rows), an **adversarial drift AUC** with negative *and* positive control rails, and
**model transfer** against a within-window ceiling. `flown_any`/`refund_any` are excluded as right-censored,
with the censoring curve published so the exclusion is visible.
**Verdict:** shares hold (TVD **1.93 pp**), a model fitted a year earlier transfers for free (GMM(full)
**0.763** vs a 0.746 ceiling), composition is stable across the **98.2%** of bookings that carry the volume
— but **revenue mix is the weaker leg** (TVD 3.21 pp; `Balikbayan/VFR` 29.35%→26.64% of revenue on a flat
headcount share) and the populations are mildly distinguishable (AUC 0.61 vs 0.49/0.99 controls). See
`outputs/validate_temporal/summary.md`.
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
├── model/                        ← what Power BI actually loads
│   ├── dim_date.csv                 1.8k rows — mark as the Date table
│   ├── dim_segment.csv                11 rows — persona dimension (see below)
│   ├── scorecard_segment_month.csv  1,835 rows — per-segment scorecards (see below)
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

**`model/scorecard_segment_month.csv` — the per-segment scorecard source.** Grain is segment × travel
month plus only the flags a scorecard must filter on (`IsInternational`, the two completeness flags, and
the `IsRefund` / `IsAward` / `IsNonRev` / `RevMissing` exclusions). **1,835 rows / 127 KB**, so a KPI tile
never aggregates 20M rows and the BI developer can check totals in Excel first. Every numeric column is
**additive** (`Coupons`, `Bookings`, `PaxCount`, `NetRevenue`, `NetFare`). **No stored percentages —
deliberately:** a share is valid only in the filter context that computed it, so shares must be DAX
measures (starter DAX in `docs/powerbi-guide.md` §3a). All flags are **coalesced non-NULL**, because a
NULL makes `IsRefund = FALSE` silently drop rows and break reconciliation; the ~542 bookings with genuinely
unknown refund status carry `RevMissing = TRUE`. The build **asserts this table ties to the fact table**
(coupons + bookings) and fails the export otherwise. **No accuracy/recall KPI ships** — that needs SME
ground truth, and any figure computable today is circular.

**`model/dim_segment.csv` — the persona dimension.** One row per segment, related to the fact table on
`Segment` = `CustomerSegment`, so a card visual bound to it **cross-filters with every other visual**
(persona cards that respond to a route or quarter slicer). Columns split three ways on purpose:
**measured** behaviour (lead days, round-trip / international / premium / connecting rates, median+mean
revenue, coupons per booking, top-3 regions, modal channel & issue country) — recomputed from
`pal_features_booking.parquet` on **every build**, at **booking grain** so multi-coupon segments are not
over-weighted; **editorial** persona text (`PersonaName`, `WhyTheyFly`, `WhatTheyWant`, `WhatNotToDo`) —
informed inference, not findings; and **governance** (`Trust`, `DataCaveat`, `IsModelledSegment`,
`PenaltyWeight`, `RevenueAtRiskPerError`, `SegmentColorHex` from `pal_colors.py`). **Put `Trust` and
`DataCaveat` on the card** — persona cards persuade, and a cropped caveat is how "Mabuhay 0.03%" becomes
"the loyalty programme doesn't matter". Filter `IsModelledSegment = FALSE` out of commercial visuals.
Full guide: `docs/powerbi-guide.md` §3b.
`report_figures.py` draws the real-data EDA + preliminary-cluster (LCA/PCA) figures used in the
shareable status report; `build_report.py` embeds them into a self-contained
**`docs/status-report.html`** and renders **`docs/status-report.pdf`** (a colleague-facing summary of
the approach, methodology, EDA and current status) from the `docs/_status-report.template.html` template.

Key references:
- **`docs/stakeholder-report.md`** — the **non-technical stakeholder report**: plain-language
  methodology, the full rule waterfall as implemented, ten data-backed **persona cards**, the success
  metrics with a worked peso cost calculation, and the SME asks (hard/soft constraints + labelled
  sample) with exact file formats. Written for PAL commercial stakeholders, not for engineers.
- **`docs/pal-questions.md`** — **the consolidated ask list for PAL: 24 open items in four groups**
  (7 blocking decisions · 5 data requests · 8 changes-to-their-rules needing confirmation · 4 still
  unanswered from the original workbook). Each row carries our recommendation, so most can be answered
  "agreed". Group A gates the waterfall change; A1 (misclassification cost weights) gates scoring entirely.
- **`docs/waterfall-v2-design.md`** — **the taxonomy change, designed and simulated but NOT built.**
  Adds MICE / Ultra Wealthy Leisure / Intl. Student / Outbound International Leisure, turns Last-Minute
  into a flag, and ships fare tier as a value band. Full before/after on all 22.9M bookings (21.8% of
  labels move; Unassigned falls 74%), the ordering rationale, the two branches the hard-constraint check
  forced, three risks needing a PAL decision, and the downstream work it triggers.
  Simulate: `python src/simulate_waterfall_v2.py`
- **`docs/sme-constraints-intake.md`** — **intake analysis of the first filled-in SME constraint
  workbook** (`wishlist/PALxMAIDA_Constraints&Wishlist.xlsx`, RM Domestic, 39 new rules). Maps every rule
  onto our hard/soft schema and feature table, flags the three fields we must build (`stay_nights`,
  `dep_dow`, a route-theme lookup), the rule conflicts needing an SME decision, and — the item most
  likely to be missed — **the validation-anchor budget these rules spend**. Five blocking decisions,
  a suggested order, and what to send back. §3 and §4a carry the probe results below.
  Probes: `python src/probe_stay_length.py` (does stay length actually separate OFW from Balikbayan?
  → `outputs/stay_length/`) and `python src/probe_constraint_coverage.py` (all 39 rules: evaluable?
  on how much of the book? fires on enough volume? → `outputs/constraint_coverage/`). The second
  imports `build`/`connect` from the first, so run it from `src/` or with `src/` on `PYTHONPATH`.
- **`docs/continuum-levers-plan.md`** — **can we find structure the current setup missed?** Seven levers
  (stay length · strip atypical populations · per-market · learned embedding · longitudinal · **coarser
  taxonomy** · continuum-native output), each with a **pre-registered decision rule**, an out-of-time
  replication gate, and a hard stop rule.
  Records which four of the six explanations for "no clusters" are already closed, so they are not re-run.
  Also corrects one kill criterion in `recommendations-plan.md` Phase 4 that relied on the retired H0 detector.
- **`docs/recommendations-plan.md`** — the sequenced plan acting on the 2026-07-28 stress-test findings
  (SME ground truth first, feature-contract gate, GMM confidence layer, pre-registered decision rules,
  and the one gated customer-grain experiment).
- **`docs/mentor-presentation-guide.md`** — talk track for presenting initial findings + next steps
  (TL;DR, 6-beat arc, per-beat script, term explainers, analogy cheat sheet, anticipated Q&A,
  what not to claim).
- **`docs/eda-results-slide-guide.html`** — the same talk track as a **self-contained presenter guide**:
  each slide a card with its chart embedded, the spoken script styled as a script block, and a **live
  timing rail** (start/pause clock that tells you which slide you should be on). Prints to PDF. Rebuild
  with the generator noted in the file footer after editing the markdown.
- **`docs/eda-results-slide-guide.md`** — **slide-by-slide talk track for a 30-minute EDA + initial-results
  session** (19 min talk / 11 min Q&A, 13 slides + 5 backup). Per-slide: what goes on it, which figure from
  `reports/study_guide/`, a spoken script, and the objection it pre-empts. Includes a timing budget with a
  cut-list, Q&A prep, a "what not to claim" list, and a pre-flight checklist.
- **`docs/pipeline-study-guide.md`** — **end-to-end walkthrough for presenters**: raw gzip → cleaned
  coupons → bookings → the rule waterfall → Power BI, with the grain changes, the four BI traps, a
  numbers cheat sheet, and likely-questions/answers. Also carries the **rule-confidence diagnostics**
  (rule competition · runner-up label · boundary fragility) that quantify how *determined* each
  deterministic label is — see §10.2. Also carries the **EDA findings and the decision trail** (§1, §3),
  the **metrics map** (§6.1 — which metric scores which layer, and why the rule layer needs external
  validity rather than BIC/silhouette), **every metric explained in plain words** (§6.2 — the four
  questions any segmentation must answer, an analogy and a null value per metric, and one number read
  end to end), **where GMM fits** (§6.3 — benchmark winner, measurement instrument, candidate; not in
  the pipeline), the **Layer-2 validation logic** (§7 — why a rulebook cannot grade itself, and the four
  ways a segmentation can be worthless with one test each), department-grouped Q&A (Commercial/RM,
  Marketing & Loyalty, Finance, IT/Data, mentors), a plain-language glossary, **strategic recommendations
  for PAL** (§13 — commercial plays, early-warning signals, repeat-purchase behaviour, taxonomy decisions,
  ranked data investments, and how *not* to use the segmentation), and the prioritised asks.
- **`docs/pipeline-study-guide.html`** — the same guide as a **self-contained presentation-grade report**
  for a mixed-seniority, cross-functional room. Open in any browser; no build step, no dependencies.
  Carries an **audience switcher** (Everyone / Business / Technical) that filters detail depth, and
  prints to PDF with every section expanded. **11 figures are embedded as base64**, so the file stays
  self-contained (~2.4 MB). Keep in sync with the markdown, which is the source.
- **`reports/study_guide/`** — the 11 figures used by both guides (copied from
  `outputs/report_real/figs/`, regenerate with `python src/report_figures.py` +
  `python src/manuscript_figures.py`). Tracked, because `outputs/` is git-ignored and the markdown
  references them.
- **`docs/powerbi-guide.md`** — the colleague-facing Power BI starter guide (star schema, load steps,
  starter DAX, the four gotchas). **Canonical copy** — `export_powerbi.py` copies it into the export
  folder as `START-HERE.md` on every build, since `outputs/` is git-ignored. Edit it here, not there.
- **`docs/data-dictionary.md`** — authoritative field reference (mirror of the client's
  `DataDictionary.v1.xlsx`), incl. the farebrand → value-tier ladder.
- **`docs/real-data-plan.md`** — the cleaning → EDA → feature-engineering plan (grain, decisions).
- **`docs/manuscript-ch4-draft.md`** — first draft of manuscript Chapter 4 (Results, Analysis,
  Discussion): §4.1 empirical clustering results, §4.2 segment interpretation + validation,
  §4.3 strategic implications for PAL. All numbers traceable to `outputs/` stage summaries.
- **`docs/eda-report-real-data.md`** — consolidated EDA report on the real 38M-coupon extract
  (raw profile, cleaning, grain confirmations, proxy-segment magnitudes, modelling implications).
  Supersedes `docs/eda-report.md` (prototype sample).
- **`docs/knowledge-base.md`** §15 — profile findings + dictionary-reconciliation notes.
- **`docs/exec-methodology-flowchart.drawio`** / **`.mmd`** — the stakeholder methodology flowchart in
  two Lucidchart-importable formats (File → Import Diagram → draw.io, or Insert → Diagram as code →
  Mermaid). Six cards; each carries a plain-language caption naming its colour's meaning (prepare /
  deliverable / prove / in your hands / what we need from you), a business headline, and a muted italic
  method line. Legend included. Same content in both; for exec buy-in decks.

## Setup

Full annotated list of every package/tool + version (incl. beyond-pip tools like pandoc and
the Playwright Chromium browser): **`docs/installation.md`**.

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
