# PAL Customer Segmentation

ML framework to auto-classify Philippine Airlines PNRs into actionable revenue segments.
**The shipped model emits 11 named segments + Unassigned = 12 labels** — waterfall v2, shipped
18 Aug 2026. `src/pal_colors.py` is the source of truth and says so itself: `SEG_ORDER` now *equals*
`SEG_APPROVED`, because the waterfall change has landed. v2 added MICE, Ultra Wealthy Leisure,
Intl. Student and Outbound International Leisure; renamed Budget/Adventure → Leisure; dropped Family and
Digital Nomad; and turned Last-Minute into a booking flag (`SEG_FLAGS`, 19.26% of bookings). v1 emitted
9 named + Unassigned — do not quote v1 counts. The Power BI export stamps one further label,
`Excluded (non-revenue)`, on the 15,073 coupons whose customer was dropped at Stage F, so
`dim_segment.csv` has **13 rows**. See `docs/methodology.md` v1.12 and `docs/sme-constraints-intake.md` §7.

> ⚠️ PAL's 17 Aug approval is recorded elsewhere as a "13-segment taxonomy", which reconciles to today's
> 11 only if it counted `Digital Nomad` and `Last-Minute` — both removed on 18 Aug (unimplementable in
> anonymous data; became a flag). `SEG_APPROVED` holds 12 entries, not 13. Worth confirming against the
> approval record before the number is quoted to PAL.

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
                 pal_subsegment.parquet  level-2 assignment: (customer_id, issue_date, sub_segment)
                   for the 21.7M bookings in the five sub-typed parents — src/subsegment_assign.py
                 pal_export_bk.parquet   build cache: booking grain + the level-2 assignment, merged
                   once so the 38.1M-coupon export scan stays inside its 8 GB memory limit. Rebuilt
                   automatically when either input is newer
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
wishlist/      Filled-in SME workbooks returned by PAL (tracked, read-only inputs — never edit these;
                 they are the record of what PAL actually said).
                 PALxMAIDA_Constraints&Wishlist.xlsx — 39 new rules from RM Domestic; analysed in
                 docs/sme-constraints-intake.md, transcribed into data/constraints/ (not yet enforced)
                 pal-questions-answered-2026-08-18.csv — RM's answers to all 24 items in
                 docs/pal-questions.csv. Several are consequential (drop Family, drop Digital Nomad,
                 rename Budget/Adventure to Leisure, read routes directionally) and three conflict
                 with earlier decisions — not yet actioned
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
| `src/monitor_metrics.py`| Monitoring **metric library** + prototype report (DBCV/PSI/ARI/drift). The real-data entrypoint is `src/monitor_real.py` | `outputs/monitor_output/` |
| `src/pal_colors.py`     | Shared segment names + palette (imported everywhere) | — |

## Generators / deliverables

`src/generate_report.py` (HTML EDA report), `src/poc_synthetic.py` + `src/generate_dark_slides.py`
(POC figures), `src/capture_slides.py` (deck → PNGs), `src/dashboard.py` (Streamlit executive dashboard).

**Decks** (1600×900 HTML, self-contained — open in a browser, or export to PNG):

| Deck | Source | PNGs |
|---|---|---|
| **Final defence deck (pptx)** — built from `docs/defense-slides-outline.md`, themed on PAL's CPT3 template; 26 slides + speaker notes, current v2 numbers. Real pipeline figures throughout: the `reports/study_guide/` EDA charts (lead time/fare tiers, region mix), the PCA overlap figure, the ten-method silhouette sweep, the LCA sub-type Sankey (`src/sankey_subsegment.py` — ML's refinement layer), an 11-row dated iteration ledger, plus matplotlib charts generated from the `outputs/` CSVs (detection floors, 55-pair AUC strip, share-vs-revenue, value bands, short-lead rates, Gulf stay-length, flag-vs-segment) | `assets/final-defense/CPT3_DefenseDeck_V3.pptx` | — (native pptx) |
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
python src/sub_segment.py     # LCA sub-types within the 5 largest v2 segments (~2 min) → outputs/sub_segments/
python src/subsegment_assign.py  # LEVEL 2: assign every booking its sub-type (~30 s) → data/interim/pal_subsegment.parquet
python src/monitor_real.py    # drift monitoring on real data: segment-mix + rule-input PSI (~1 min) → outputs/monitor_real/
python src/rule_confidence.py # how *determined* is each rule label? (~1 min) → outputs/rule_confidence/
python src/check_constraints.py       # validate data/constraints/*.csv against the feature table (~1 min)
(cd src && python apply_soft_priors.py)  # Stage P: score the 21 live SME tendencies vs the labels (~1 min)
python src/simulate_waterfall_v2.py   # DESIGN ONLY: proposed taxonomy change, before/after + rule check (~1 min)
python src/probe_stay_length.py       # SME claim: does stay length split OFW from Balikbayan? (~30 s) → outputs/stay_length/
(cd src && python probe_constraint_coverage.py)  # all 39 SME rules: evaluable? fires? (~1 min) → outputs/constraint_coverage/
python src/export_powerbi.py  # Power BI star schema, levels 1+2 (~5 min; needs subsegment_assign.py first) → outputs/powerbi_export/
python src/segment_charts.py  # v2 segment charts: size/revenue, value bands, flag, reclass (~30 s) → outputs/segment_charts/
python src/sankey_subsegment.py  # one parent → its LCA sub-types, as a Sankey (~2 s) → outputs/segment_charts/fig_s07_sankey_*.{png,json}
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
coupons out). It carries **both levels**: `CustomerSegment` (level 1) and `SubSegment` (level 2, the LCA
sub-type inside a parent), so it requires `subsegment_assign.py` to have run first:

The folder is laid out as a **self-contained handoff** — zip it and send it:

```
outputs/powerbi_export/
├── START-HERE.md                 5-min starter guide (copy of docs/powerbi-guide.md)
├── summary.md                    field dictionary, reconciliation, caveats
├── model/                        ← what Power BI actually loads
│   ├── dim_date.csv                 1.8k rows — mark as the Date table
│   ├── dim_segment.csv                13 rows — persona dimension (see below)
│   ├── dim_subsegment.csv             28 rows — level-2 dimension (see below)
│   ├── scorecard_segment_month.csv  3,544 rows — per-segment scorecards (see below)
│   ├── fact_flight/                20.7M rows — full dashboard (flight no., O&D, lead time)
│   └── fact_dashboard.parquet       2.3M rows — fast summary-only alternative
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
the `IsRefund` / `IsAward` / `IsNonRev` / `RevMissing` exclusions). **3,544 rows / 471 KB** (it carries `SubSegment` too), so a KPI tile
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

**`model/dim_subsegment.csv` — the level-2 dimension.** `SubSegment` is the LCA sub-type *inside* a
parent segment, assigned per booking by `subsegment_assign.py` and related on `SubSegment`. 28 rows: 20
sub-types across the five biggest parents, plus a self-named row for each segment that has none (MICE's
`SubSegment` is `MICE`) — a NULL would silently drop those eight segments out of every level-2 visual and
break reconciliation against `dim_segment`. The key is composite (`Parent — sub-name`) because the names
are **not** unique alone: `one-way · advance · saver` is emitted by Leisure, OFW/Migrant and Outbound
International Leisure alike. `IsSubTyped` separates real sub-types from the self-named rows.
`SubSegmentSortOrder` is a dense 1..28 rank; colour is inherited from the parent. The sub-types are
**actionable partitions of a continuum, not natural kinds** — target with them, never score with them.
Full guide: `docs/powerbi-guide.md` §3c.
`monitor_real.py` is the **real-data drift monitor** (Regime C): it imports the dataset-agnostic metric
functions from `monitor_metrics.py` and runs segment-mix PSI, per-rule-input PSI and per-segment
volume/revenue drift across the two censoring-safe 12-month windows defined in `validate_temporal.py`.
It deliberately does **not** compute DBCV/silhouette or cross-window ARI — those score a fitted
clustering, and the shipped labeller is deterministic; `outputs/monitor_real/summary.md` says so on the
page rather than leaving a blank. `sub_segment.py` runs LCA **inside** the five largest v2 segments.
`segment_charts.py` draws the six **shipped-taxonomy segment charts** — share of bookings vs share
of revenue, mean revenue per booking, `value_band` mix, short-lead rate, the top v1→v2 reclassification
flows, and Last-Minute segment-vs-flag — plus a `segment_summary.csv` table view, all aggregated in
DuckDB over the full 22.9M-booking table so a chart cannot drift from the build.
`sankey_subsegment.py` draws **one** parent segment fanning into its LCA sub-types (default
`Balikbayan/VFR`; `--parent` selects another) for the deck's refinement slide — ribbon width is share of
the parent, fill is median revenue on a single-hue sequential ramp. It **parses
`outputs/sub_segments/summary.md`** rather than re-fitting the LCA, so the figure cannot disagree with the
report the docs quote; run `sub_segment.py` first if the taxonomy changes. **The PNG is the diagram only —
no text** — and a sibling `.json` carries each flow's label anchor in axes fractions, so every label lives
in PowerPoint as an editable text box: `slide_y = picture_top + (1 - anchor_y) * picture_height`. The
figure is saved without a tight bounding box precisely so that mapping holds.
`report_figures.py` draws the real-data EDA + preliminary-cluster (LCA/PCA) figures used in the
shareable status report; `build_report.py` embeds them into a self-contained
**`docs/status-report.html`** and renders **`docs/status-report.pdf`** (a colleague-facing summary of
the approach, methodology, EDA and current status) from the `docs/_status-report.template.html` template.

Key references:
- **`docs/handover-pack.md`** — **the operating manual handed to PAL (27 Aug)**: deliverables
  inventory, the nine-command refresh runbook with five post-refresh checks, what "retraining"
  means here (relabel / refit level 2 / the seven-step rule-change release procedure), how to read
  the drift monitor (with the NDC alarm as the worked example), the Power BI traps, a two-week KT
  plan with pass conditions, limitations that must travel, and the four-tier improvement roadmap
  (data before algorithms). **This is the "handover pack" the old defence deck's limitations slide
  referenced** — that open item is closed. `handover-pack.html` is the shareable artifact version.
- **`docs/stakeholder-report.md`** — the **non-technical stakeholder report**: plain-language
  methodology, the full rule waterfall as implemented, ten data-backed **persona cards**, the success
  metrics with a worked peso cost calculation, and the SME asks (hard/soft constraints + labelled
  sample) with exact file formats. Written for PAL commercial stakeholders, not for engineers.
- **`docs/defense-brief-2026-08-18.{md,html}`** — **one-page state of the model**: taxonomy as shipped,
  what changed and the number to quote (23.4%, not 62.7%), all four validation stages with the honest
  reading of each, the SME programme, and an explicit *what to say / what not to say* list. Written for
  presenting, so every claim carries its caveat. The `.html` is the shareable version, published
  as a Claude artifact: every claim carries a coloured confidence rail marking it safe to state,
  caveated, or not to be said.
- **`docs/final-defense-reviewer.md`** — **the final consolidated defence reviewer (25–26 Aug)**:
  opens with §1.1–§1.4 — every load-bearing concept in three registers (plain English → technical →
  the number), then the methodology, EDA and results end to end in the same dual register — then:
  everything that changed after the study guide (level-2 assignment, the two business cases, the
  k=1/k=2 continuum extensions), a stress test of the three load-bearing argument chains with three
  fresh findings (the 87.8% segment-stability figure decomposes to 53.4% among repeat customers;
  the deck still embeds the stale 23 Jul clustering PNGs; methodology.md's V1 section still says
  45 pairs), a slide-by-slide walkthrough of the **26 Aug rebuilt deck** (28 slides, business-first —
  the audit found the "10 vs 11 segments" on-deck contradiction and that the validation story moved
  entirely into Q&A), a 58-question panel Q&A with model answers, and the pre-defence action
  checklist.
  Supersedes the study guide and brief on anything dated 21–25 Aug. The companion
  **`final-defense-reviewer.html`** is the shareable version, published as a Claude artifact —
  same content with the Q&A as click-to-reveal self-quiz cards.
- **`docs/defense-script-methodology-results.md`** — **word-for-word talk track for slides 12–18
  of the 26 Aug rebuilt deck** (methodology + results blocks, 9:05 timed): spoken lines, stage
  directions, per-slide guardrails aligned to the never-say list, the entry/exit transitions, and
  five pocket answers for likely interruptions. The older `defense-script.md` covers the
  superseded 26-slide deck.
- **`docs/defense-study-guide.md`** — **the defence study companion**: the one-story spine, the
  seven principles, every technique in plain words with an analogy, the memorize/never-say number
  tables, a claim·proof·trap map of the 24-slide deck, a drilled question bank with owners, the
  stale-figures ambush list (older docs still carry v1 numbers), and a three-session study plan.
- **`docs/defense-slides-outline.md`** — **slide-by-slide outline for the capstone defence deck**:
  the eight agreed sections with owners (Martin/Josh/Jadd), per-slide headlines and content grounded
  in the defence brief's numbers, the ⚠️ what-not-to-say guardrails inlined per slide, timing budget,
  backup-slide list and team Q&A prep. Build the deck from this file; the brief stays authoritative
  on the numbers.
- **`docs/metrics-explained.html`** — the **executive companion to the brief**: every validation metric
  with what it actually measures in plain terms, an analogy, the scale it sits on with the ideal value
  marked, and where we landed. Written for a reader who should not have to know what an AUC is. Also
  carries the withdrawal notice for the superseded transfer-ARI figure. Published as a Claude artifact;
  reuses the brief's design tokens so the two read as one set.
- **`docs/segment-cost-research.md`** — **answers PAL question A1: what a misclassification costs.**
  Five cost components each sourced from published airline revenue-management and customer-value
  research, our own per-segment economics in confirmed USD (annual value at risk spans **$495–$9,784**),
  a transparent weight formula, and **recommended penalty weights** with three documented overrides.
  Flags that the shipped ×1–10 ladder is inverted against measured revenue in two places.
- **`docs/pal-email-draft.md`** — draft of the two open questions to PAL (the Mecca-seasonality
  contradiction and the promised-fields timing), plus notes on what was deliberately left out.
- **`docs/pal-questions.md`** + **`docs/pal-questions.csv`** — **the consolidated ask list for PAL:
  24 open items in four groups** (7 blocking decisions · 5 data requests · 8 changes-to-their-rules
  needing confirmation · 4 still unanswered from the original workbook). Each row carries our
  recommendation, so most can be answered "agreed". Group A gates the waterfall change; A1
  (misclassification cost weights) gates scoring entirely. The CSV is the sendable version — blank
  `answer`/`answered_by`/`answered_date` columns so it comes back filled in, like the constraint
  workbook did. Both are hand-maintained: update them together.
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
- **`docs/do-nothing-vs-implement.md`** — **the benefits analysis: what PAL gains by implementing the
  segmentation vs continuing as it is.** Written for the defence panel and organised by **the five
  departments that would consume the output** — RM (pricing) · Sales (channels) · Marketing (promos) ·
  CX (web/app & lounge) · Loyalty (churn) — so every claim maps to a decision someone owns. Measured
  figures (§4) and assumed parameters (§5) are kept strictly apart, and the decision is resolved by
  **breakeven rather than forecast** (§7 — 0.116% of avoidable dilution covers year-1 cost, still 4.7%
  with every placeholder 10x worse at once). Key finding: **Sales and CX need no response assumption at
  all**, so they are ready first even though RM carries the larger dollars; **Loyalty should wait** — 73.9%
  of customers are right-censored, so no churn rate exists. §8 lists the eight things it cannot claim.
- **`docs/business-case-benchmark.md`** — the **top-down, benchmark-derived** business case
  (imported 23 Aug 2026 from the companion workbook): $77,904/yr actual all-in cost against
  ~$2.7M/yr risk-adjusted margin, +$7.3M five-year NPV. Carries an import preface naming its
  reconciliation items against the bottom-up case; manuscript Ch. 5 §§5.2–5.3 argue how the two
  divide the work (breakeven decides, NPV sizes) and the build-vs-buy comparison.
- **`docs/subsegment-scoring-plan.md`** — **how level 2 (LCA sub-types) got into the Power BI model** — ✅ built 21 Aug 2026.
  Today the export carries only `CustomerSegment`; sub-types exist as profiles, not assignments. Scopes the
  missing scoring pass: the feature space is discrete, so **17,847 cells cover all 21.7M parent bookings** —
  score cells, join in SQL, and the whole model is a readable CSV. Also lets the 40k sample be dropped
  (StepMix takes `sample_weight`), lists five encoding blockers, and puts the cost at ~2 days.
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
- **`docs/manuscript/manuscript-ch4-draft.md`** — **final draft (v1.1)** of manuscript Chapter 4 (Results,
  Analysis, Discussion): §4.1 empirical clustering results, §4.2 segment interpretation +
  validation, §4.3 strategic implications for PAL. Measured on the v2 taxonomy and the 18 Aug
  validation re-runs, with citations and a census-vs-sample uncertainty statement. All numbers
  traceable to `outputs/` stage summaries.
- **`docs/manuscript/manuscript-ch5-draft.md`** — **final draft (v2.0)** of manuscript Chapter 5
  (Findings, Recommendations, and Conclusions), restructured to the programme outline: §5.1
  Summary of Technical and Strategic Findings (§5.1.1 technical/ML/behavioural F1–F8, §5.1.2
  strategic F9–F13), §5.2 the two-route economic case, §5.3 build-vs-buy, §5.4 recommendations,
  §5.5 limitations and future work, §5.6 Final Project Conclusions.
- **`docs/manuscript/manuscript-do-nothing-analysis.md`** — **final draft (v1.0)** of manuscript
  Appendix A: the full do-nothing analysis in manuscript register — five decision owners, the
  assumption ledger, breakeven at the actual $77,904 budget (0.48%), and the five-year band.
  Expands Ch. 5 §5.2; the working-document source is `docs/do-nothing-vs-implement.md`.
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
