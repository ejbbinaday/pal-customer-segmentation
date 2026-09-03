# PAL Customer Segmentation — Knowledge Base

**Project:** Optimized Market Segmentation for Philippine Airlines
**Team:** Edyll Joshua Binaday, Jeremy Jay Lim, Arien Jadd Versoza, Martin Aloysius Yamzon (PL)
**Version:** v1.1 — 17 July 2026

---

## 📌 How This Knowledge Base Is Maintained

This is a **living document**. Every time we learn something new about the airline
industry, clustering, customer segmentation, our data, or a project decision, it gets
appended to the **[Learning Log](#15-learning-log-living)** (§15) — the newest entries first.

**Rules for maintaining it:**
- Sections 1–14 are the *curated reference* (stable facts, deliverable-grade).
- Section 15 is the *append-only Learning Log* — the working memory of the project.
- Each Learning Log entry uses: `#### YYYY-MM-DD — Title` + a **Domain** tag
  (`Airline Industry` · `Clustering / Methodology` · `Data & Features` · `Project Decision`),
  the learning itself, and a **Source** (paper/URL, script, dataset, or "our analysis").
- When a Learning Log entry supersedes a curated fact, update the curated section too and
  note it in the entry.
- Update the footer `Last updated` date on every change.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [The 10 Segments](#2-the-10-segments)
3. [Revenue Loss Per Misclassification](#3-revenue-loss-per-misclassification)
4. [The 8-Stage Pipeline](#4-the-8-stage-pipeline)
5. [Algorithm Selection — Why HDBSCAN](#5-algorithm-selection--why-hdbscan)
6. [POC Results (withdrawn)](#6-poc-results-withdrawn)
7. [Data Sources](#7-data-sources)
8. [Key Business Rules (Proxy Label Waterfall)](#8-key-business-rules-proxy-label-waterfall)
9. [Negative Learning Rules](#9-negative-learning-rules)
10. [Current Limitations & Next Steps](#10-current-limitations--next-steps)
11. [File Map](#11-file-map)
12. [Presentation Assets](#12-presentation-assets)
13. [Glossary](#13-glossary)
14. [Quick Reference — Numbers to Know](#14-quick-reference--numbers-to-know)
15. [Learning Log (Living)](#15-learning-log-living)

---

## 1. Project Overview

### Problem Statement

> *"There is an opportunity for Philippine Airlines to optimize its customer segmentation models, using machine learning, to further personalize its service and maximize opportunities within each segment."*

PAL flies **16 million passengers annually** across North America, Asia-Pacific, Oceania, and the Middle East. Its booking data tells you *what* a passenger bought — cabin, fare, route. It does not tell you *who they are* or *why they flew*.

The model fills that gap. Every booking record receives a label — Corporate, OFW/Migrant, Mabuhay Loyalist, etc. — derived purely from observable booking signals, with no reliance on historical labels or manual annotation.

### Who Benefits

| Team | How They Use It |
|---|---|
| Revenue Management | Segment mix per route → smarter pricing and seat allocation |
| Marketing | Targeted campaigns by segment (OFW before deployment season, Pilgrimage before Hajj) |
| Sales & Distribution | Identify which channels are profitable per segment |
| Customer Experience | Minimize churn, optimize platform experience by segment |

### Scope

**In scope:** Baseline ML model, domestic + international online commercial passengers, Power BI executive dashboard

**Out of scope:** Production-level integration, real-time passenger scoring on PAL's website/app, production Power BI database

---

## 2. The 10 Segments

| # | Segment | Penalty Weight | Description |
|---|---------|:--------------:|-------------|
| 1 | **Corporate** | ×10 | Business travelers. Short lead times, business/first cabin, loyalty program. Highest revenue value. |
| 2 | **Mabuhay Loyalist** | ×8 | Frequent flyers with active Mabuhay Miles. High CLV, repeat bookings across routes. |
| 3 | **OFW/Migrant** | ×5 | Overseas Filipino Workers. Middle East corridors, economy, 2+ checked bags, TTA channel. |
| 4 | **Premium Bleisure** | ×4 | Business + leisure blend. Premium economy/business cabin, ASEAN routes, high income. |
| 5 | **Pilgrimage** | ×3 | Age 55+, low income, 2+ bags, leisure travel. Group bookings via travel agency. |
| 6 | **Balikbayan/VFR** | ×2 | Visiting Friends & Relatives. Beyond itineraries (INT→DOM), 2+ bags, high income. |
| 7 | **Family** | ×2 | Group of 3–5, 2+ bags, medium income, family travel purpose. |
| 8 | **Digital Nomad** | ×2 | Solo, age <40, mobile/online check-in, ASEAN routes, non-low income. |
| 9 | **Last-Minute** | ×1 | Booked ≤3 days before departure, or emergency travel purpose. |
| 10 | **Budget/Adventure** | ×1 | Economy, low income, leisure. Price-sensitive, promo-driven. |

**Penalty weight** = the relative business cost of misclassifying a passenger *into the wrong segment*. A Corporate passenger labelled as Budget carries a ×10 penalty. A Budget passenger labelled as Corporate carries near-zero penalty (over-served, not harmful).

---

## 3. Revenue Loss Per Misclassification

These are the estimated peso costs anchored to Corporate at ₱40,000 (BR-28):

| Segment | Revenue Loss per Wrong Label |
|---------|---------------------------:|
| Corporate | ₱40,000 |
| Mabuhay Loyalist | ₱32,000 |
| OFW/Migrant | ₱20,000 |
| Premium Bleisure | ₱16,000 |
| Pilgrimage | ₱12,000 |
| Balikbayan/VFR | ₱8,000 |
| Family | ₱8,000 |
| Digital Nomad | ₱8,000 |
| Last-Minute | ₱4,000 |
| Budget/Adventure | ₱4,000 |

---

## 4. The 8-Stage Pipeline

```
Raw PNR File
     │
     ▼
[Stage 1] Ingest & Clean          29,999 → 29,985 rows (14 invalid removed)
     │
     ▼
[Stage 2] Feature Engineering     29,985 × 40 features, StandardScaler
     │
     ▼
[Stage 3] Proxy Label Waterfall   22,907 labelled (76.4%) / 7,084 Unassigned (23.6%)
     │
     ▼
[Stage 4] Algorithm Evaluation    7 algorithms tested → HDBSCAN selected
     │
     ▼
[Stage 5] Penalty-Weighted Scaling  Features re-weighted by segment penalty
     │
     ▼
[Stage 6] Cluster → Segment Map   78 micro-clusters → 10 segments
          + Noise Auto-Assignment  ~2,100 noise records → nearest centroid
     │
     ▼
[Stage 7] Validate                Asymmetric cost matrix, per-segment recall
     │
     ▼
[Stage 8] Power BI Dashboard      O&D × segment × travel month
```

### Stage Details

| Stage | What Happens | Key Output |
|-------|-------------|-----------|
| **1 — Ingest & Clean** | Load raw CSV. Strip `$` from fare. Parse dates. Drop null `PNRCreationDate`. | 29,985 clean records |
| **2 — Feature Engineering** | Compute `lead_time`, `fare_per_pax`, ordinal encode cabin/loyalty/income, one-hot encode categorical cols. | 40-feature matrix |
| **3 — Proxy Labels** | 9 priority-ordered business rules assign a segment label to 76.4% of records. | 22,907 labelled seeds |
| **4 — Algorithm Selection** | Silhouette, Davies-Bouldin, Calinski-Harabász evaluated across 7 algorithms. | HDBSCAN chosen |
| **5 — Penalty Weighting** | Features amplified by their discriminative power for high-penalty segments (Corporate, OFW). | Weighted feature matrix |
| **6 — Cluster Map** | 78 HDBSCAN micro-clusters assigned to nearest segment centroid. Noise records assigned individually. | All 29,985 labelled |
| **7 — Validate** | Per-segment recall + weighted misclassification cost computed. No raw accuracy — scoring by peso impact. | Revenue-weighted metrics |
| **8 — Dashboard** | Power BI output: segment mix by route, avg fare, lead time, O&D heatmap. | Executive dashboard |

---

## 5. Algorithm Selection — Why HDBSCAN

Seven algorithms were evaluated on the real 40-feature dataset (`sample-features.csv`):

| Algorithm | Silhouette ↑ | Davies-Bouldin ↓ | Clusters | Noise % |
|-----------|:-----------:|:----------------:|:--------:|:-------:|
| KMeans | 0.167 | 1.721 | 10 | 0.0% |
| MiniBatch KMeans | 0.136 | 1.976 | 10 | 0.0% |
| GMM | 0.114 | 2.004 | 10 | 0.0% |
| Agglomerative (Ward) | 0.151 | 1.765 | 10 | 0.0% |
| DBSCAN | 0.554 | 0.774 | 221 | 7.9% |
| **HDBSCAN ★** | **0.435** | **0.961** | **78** | **7.1%** |
| Birch | 0.247 | 1.303 | 10 | 0.0% |

**Why HDBSCAN won:**

1. **No spherical cluster assumption** — follows actual density contours, not forced equal-sized buckets
2. **Explicit noise flagging** — 7.1% of records are flagged as borderline instead of silently polluted into the wrong cluster
3. **78 interpretable micro-clusters** — can be merged to 10 named segments via nearest-centroid mapping
4. **Manageable cluster count** — DBSCAN's 221 clusters at ε=0.5 are too fragmented to map cleanly

**Why not KMeans:** Forces every borderline record into its nearest centroid, silently polluting proxy seeds. HDBSCAN surfaces the ambiguity instead.

---

## 6. POC Results (withdrawn)

The original proof-of-concept scorecard in this section was produced on the **superseded prototype
track**, so its figures — overall accuracy, per-segment recall and an estimated revenue-risk total — do
**not** describe performance on real PAL data and have been withdrawn rather than relabelled. Quoting
them alongside real-data results would misattribute the evidence.

**Where the real numbers live:** rule-based segment shares and revenue per segment in
`outputs/features_real/summary.md`; the ten-method benchmark in `outputs/model_stress_test/summary.md`;
non-circular validation in `outputs/validate_construct/`, `validate_criterion/`, `detection_power/` and
`validate_temporal/`. **Per-segment recall against ground truth is not yet available** — it needs the SME
labels (`data/labels/`), and until those land every accuracy figure is circular by construction.

One finding from that era does survive, because the real data reproduced it independently: **OFW,
Budget and Balikbayan overlap heavily in booking behaviour**, and without a loyalty-tier field the model
cannot cleanly separate them. **Loyalty tier remains the single biggest data unlock.**

---

## 7. Data Sources

| Dataset | File | Records | Purpose |
|---------|------|--------:|---------|
| Real PAL bookings (Jan 2025 snapshot) | `data/raw/sample-features.csv` | 29,999 | Main pipeline development and algorithm evaluation |

### Fields in `sample-features.csv`

Key columns used:

| Field | Type | Notes |
|-------|------|-------|
| `PNRCreationDate` | date | Booking creation date |
| `Flight Date` | date | Departure date |
| `Average Fare` | float | Fare in USD (requires `$` strip) |
| `PAX Count` | int | Number of passengers on booking |
| `Cabin` | categorical | Y / W / J |
| `Farebrand` | categorical | Economy Saver, Flex, Business, etc. |
| `Region` | categorical | DOM, ASEAN, Middle East, etc. |
| `Itinerary Type` | categorical | Point-to-point, Beyonds |
| `Ticketing Channel` | categorical | WEB, APP, TTA, Sea Crew, etc. |
| `Market Segment` | target | **100% null** — no ground-truth labels exist |

### Known Data Gaps (Blocking Production Improvement)

| Missing Field | Impact |
|--------------|--------|
| `Loyalty status` (Mabuhay Miles tier) | Mabuhay Loyalist has zero proxy labels; weakens Corporate + OFW separation |
| `Departure Time` | Removes early-AM Corporate signal |
| `Length of stay` | Cannot distinguish Corporate (short stay) from Leisure (long stay) |
| `Cargo/baggage add-on` | Removes OFW/Balikbayan confirmation signal |

---

## 8. Key Business Rules (Proxy Label Waterfall)

Applied in priority order. Higher priority overwrites lower.

| Priority | Segment Assigned | Rule |
|:--------:|-----------------|------|
| 1 (lowest) | Budget/Adventure | Economy class + low income + leisure purpose |
| 2 | Last-Minute | Lead time ≤ 3 days OR emergency travel purpose |
| 3 | Digital Nomad | Leisure + mobile/online check-in + age < 40 + non-low income |
| 4 | Family | Family travel + 2+ bags + medium income |
| 5 | Pilgrimage | Age ≥ 55 + low income + 2+ bags + leisure |
| 6 | Balikbayan/VFR | Family travel + 2+ bags + high income |
| 7 | OFW/Migrant | Economy + 2+ bags + low income + non-business purpose |
| 8 | Premium Bleisure | Premium economy or business cabin + leisure + high income |
| 9 | Mabuhay Loyalist | Loyalty tier = Platinum + leisure/family/emergency |
| 10 (highest) | Corporate | Business or First cabin + business purpose |

**Result:** 76.4% of records labelled. 23.6% remain Unassigned → handled by HDBSCAN + nearest-centroid assignment.

---

## 9. Negative Learning Rules

Applied *after* proxy labelling to invalidate impossible assignments before any annotation:

| Condition | Assignment Invalidated |
|-----------|----------------------|
| Corporate + lead time > 60 days + Economy cabin + no loyalty | Corporate → Unassigned |
| Mabuhay Loyalist + no loyalty card on file | Mabuhay Loyalist → Unassigned |
| OFW/Migrant + zero checked bags | OFW/Migrant → Unassigned |
| Premium Bleisure + low income | Premium Bleisure → Unassigned |

**Effect:** Reduces annotation decision space from 10 possible segments to 2–3 per record, so annotators confirm rather than guess.

---

## 10. Current Limitations & Next Steps

### Immediate (Blocking)

| Action | Why Critical |
|--------|-------------|
| Request Mabuhay Miles loyalty tier from PAL IT | Single biggest unlock — enables Mabuhay Loyalist segment and improves OFW/Corporate separation |
| Request flight schedule data | Provides departure time for early-AM Corporate signal |
| Request return PNR pairing | Derives length of stay (short = Corporate, long = Leisure) |
| Request ancillary/SSR data | Cargo add-on confirms OFW/Balikbayan |

### Short-Term (Data Preparation)

- **Filter COVID years (2020–2021)** — anomalous travel patterns distort cluster positions
- **Engineer RFM features** — `flights_last_12m`, `avg_fare_12m`, `routes_flown`, `recency_days`
- **Add temporal features** — `is_holy_week`, `is_hajj_season`, `is_balikbayan_season`, `travel_quarter`
- **Stratified sample** — use 500K records (stratified by year, route region, cabin) for iteration; train on sample, predict on full 6M

### Pipeline Scaling (at 6M Records)

| Component | Current | Recommended |
|-----------|---------|-------------|
| Data loading | `pandas` | `polars` or chunked `pandas` |
| HDBSCAN `min_cluster_size` | 80–150 | 500–1,000 |
| HDBSCAN algorithm | default | `prims_kdtree` |
| Nearest-neighbour search | sklearn brute | FAISS approximate |

### Full Production Retrain Sequence

```
[1] Receive 5-year dataset + blocking features from PAL
[2] Clean, engineer RFM + temporal features, filter COVID years
[3] Refit penalty-weighted StandardScaler on full dataset
[4] Refit HDBSCAN (min_cluster_size=500–1000)
[5] Re-run cluster → segment mapping + noise auto-assignment
[6] Validate with asymmetric cost matrix
[7] Build Power BI dashboard on final labelled dataset
[8] Define monthly refresh pipeline
```

---

## 11. File Map

### Core Pipeline Scripts

| File | Purpose |
|------|---------|
| `eda_graphs.py` | Stage 1–2: dataset EDA, feature engineering |
| `eda_segments.py` | Stage 3: proxy label assignment + segment EDA |
| `cluster_initial.py` | KMeans k=10 baseline, centroid heatmap, PCA |
| `cluster_compare.py` | Stage 4: 7-algorithm comparison leaderboard |
| `resample_compare.py` | Resampling strategy evaluation (rejected) |
| `dbscan_viz.py` | DBSCAN deep-dive visualisations |
| `pca_boundaries.py` | Decision boundary + per-segment PCA zoom |
| `hdbscan_final.py` | Stages 5–7: penalty-weighted HDBSCAN, mapping, validation |
| `poc_synthetic.py` | Legacy 8-stage POC runner — superseded track, results withdrawn |
| `pal_colors.py` | Canonical 10-segment colour palette (import this everywhere) |
| `generate_dark_slides.py` | Generates 3 dark-themed POC output PNGs |
| `generate_report.py` | Generates `PAL_EDA_Report.html` |
| `capture_slides.py` | Playwright: exports executive HTML deck as PNGs |

### Data Files

| File | Records | Description |
|------|--------:|-------------|
| `sample-features.csv` | 29,999 | Real PAL bookings — Jan 2025 snapshot |

### Output Directories

| Directory | Contents |
|-----------|---------|
| `poc_output/` | 8 POC result figures (white background, for embedding) |
| `poc_output/dark/` | 3 dark-themed POC figures (for dark slide decks) |
| `executive_slides/` | Exported PNG slides from all HTML decks |
| `hdbscan_output/` | Figures from real `sample-features.csv` run (not for POC slides) |
| `eda_output/` | EDA figures |

### Presentation Files

| File | Description |
|------|-------------|
| `kick-off-call/pal_executive_deck.html` | Dark executive deck (3 slides: Methodology, ML Deep Dive, POC Results) |
| `kick-off-call/dark_inserts.html` | Dark theme inserts for pitch deck (Methodology + POC Results) |
| `kick-off-call/pitch_inserts.html` | Blue sky theme inserts (deprecated — replaced by dark_inserts.html) |
| `kick-off-call/script.md` | Speaker script for executive deck |
| `kick-off-call/script_pitch_slides.md` | Speaker script for Methodology + POC Results slides |
| `pal-pitch-deck.pdf` | Original academic pitch deck (blue sky theme, 27 slides) |
| `PAL_EDA_Report.html` | Scrollable EDA report — internal reference only |

---

## 12. Presentation Assets

### Executive Deck (`pal_executive_deck.html`) — 3 Slides

| Slide | File | Content |
|-------|------|---------|
| 01 / Methodology | `PAL_01_Methodology.png` | 5-step pipeline overview |
| 02 / ML Deep Dive | `PAL_02_ML_Deep_Dive.png` | Rule engine → HDBSCAN → segment mapping |
| 03 / POC Results | `PAL_03_POC_Results.png` | KPIs, recall chart, scatter, notes |

### Dark Pitch Deck Inserts (`dark_inserts.html`) — 2 Slides

| Slide | File | Content |
|-------|------|---------|
| Methodology | `PAL_Methodology_Dark.png` | Full pipeline: Req. Scoping → 5 steps → Reporting |
| POC Results | `PAL_POC_Results_Dark.png` | 4 KPIs, recall bars, cluster scatter, findings |

### POC Output Figures (Dark Theme)

| File | Content |
|------|---------|
| `poc_output/dark/poc_kpi_card.png` | 3-KPI summary card |
| `poc_output/dark/poc_recall_dark.png` | Per-segment recall bar chart |
| `poc_output/dark/poc_scatter_dark.png` | PCA cluster separation scatter |

### Recommended Slide Order (for Pitch Deck)

```
Cover → Company & Context → Competitive Landscape → Problem Statement →
Who Would Benefit → Data Landscape → Scope & Limitations →
[PAL_Methodology_Dark.png] →
Negative Learning → Reveal Centroid → Reveal Tracers → Diffusion →
Validate – Cost Sensitive Output →
[PAL_POC_Results_Dark.png] →
Dashboard Wireframe → Requirements Checklist → [Appendix] Literature
```

---

## 13. Glossary

| Term | Plain-English Definition |
|------|--------------------------|
| **PNR** | Passenger Name Record — one booking. Contains cabin, fare, route, dates, PAX count. |
| **HDBSCAN** | The clustering algorithm selected. Groups passengers by booking similarity without forcing equal-sized buckets. Flags borderline cases as "noise" instead of guessing. |
| **Proxy label** | A segment assignment derived from business rules (not ground truth). Used as a training seed because no historical labels exist. |
| **Negative learning** | A pre-filtering step that eliminates impossible segment assignments before annotation. E.g., a passenger booked 60+ days out in Economy cannot be Corporate. |
| **Asymmetric cost matrix** | A scoring system where misclassification costs differ by segment. Getting Corporate wrong costs ×10 more than getting Budget wrong. Accuracy is measured in pesos, not percentages. |
| **Penalty weight** | A number (1–10) assigned to each segment reflecting the business cost of misclassifying a record into that segment. |
| **Recall** | For a given segment: the share of actual segment members correctly identified. 100% recall = no member missed. |
| **NFR-01** | Non-functional requirement: model must achieve ≥ 91% hold-out recall. The red line on recall charts. |
| **Micro-cluster** | One of the 78 natural groupings found by HDBSCAN. Each is mapped to one of the 10 named segments. |
| **Centroid** | The most "typical" passenger in a cluster — the record closest to the average of all records in that cluster. |
| **Noise record** | A record HDBSCAN could not assign to any cluster (7.1% of records). Handled by nearest-centroid assignment in Stage 6. |
| **Label diffusion / spreading** | Propagating confirmed labels outward from annotated seeds to cover unlabelled records via graph-based similarity. |
| **O&D pair** | Origin–Destination pair. E.g., MNL–DXB. The unit of analysis for route-level reporting. |
| **OFW** | Overseas Filipino Worker. A major segment on Middle East and Asia corridors. |
| **VFR** | Visiting Friends & Relatives. Part of the Balikbayan segment. |
| **Bleisure** | Business + leisure travel combined. A traveller extending a work trip for personal travel. |
| **PCA** | Principal Component Analysis. A technique that compresses 40 booking signals into 2 dimensions for visualisation. The scatter chart axes. |
| **Silhouette score** | A cluster quality metric (higher = better separation between clusters). Used to compare algorithms. |
| **RFM** | Recency, Frequency, Monetary — a framework for scoring customer value based on purchase history. Needed for Mabuhay Loyalist identification. |

---

## 14. Quick Reference — Numbers to Know

| Number | What It Is |
|-------:|-----------|
| 16M | PAL annual passengers |
| 29,985 | Clean records in `sample-features.csv` after Stage 1 |
| 40 | Features engineered per booking record |
| 9 | Business rules in the proxy label waterfall |
| 76.4% | Share of real dataset labelled by proxy rules (22,907 records) |
| 7 | Clustering algorithms evaluated |
| 78 | HDBSCAN micro-clusters found on real dataset |
| 7.1% | Noise rate from HDBSCAN (borderline records auto-assigned) |
| 10 | Named customer segments |
| ×10 | Highest penalty weight (Corporate) |
| ₱40,000 | Revenue loss per wrong Corporate label |
| 91% | NFR-01 recall target (the red line) |
| 5 | Years of historical PAL data available for full retrain |
| 6M | Estimated full PAL PNR records for production pipeline |

---

## 15. Learning Log (Living)

> Append-only working memory. Newest first. Entry format:
> `#### YYYY-MM-DD — Title` · **Domain** · learning · **Source**.

---

#### 2026-08-27 — The handover pack exists now, and "retraining" is defined as three different actions
**Domain:** Project Decision
Wrote `docs/handover-pack.md` (+ `.html`, published as a Claude artifact) — the operating manual
for PAL's BI team, closing the open item flagged 19 Aug: the old defence deck's limitations slide
claimed "everything on this slide is also written down in the handover pack" and no artifact by
that name existed. Contents: deliverables inventory · the nine-command refresh runbook with **five
post-refresh checks** (rows-in=out assertion, distribution diff, hard-rule assertions, constraint
sheet, drift verdicts) · **"retraining" disambiguated into three actions** — (a) relabelling is
automatic and deterministic (rerun = retrain, nothing fits), (b) level-2 LCA refit is occasional
with three hard-won invariants (`ORDER BY ALL` is load-bearing; weighted BIC is hand-computed
because `StepMix.bic()` mis-reads weighted cells; sub-types stay provisional), (c) **rule changes
are a governed seven-step release** (propose → simulate → anchor budget → constraints → palette
contract → re-audit V1/V4 → paper trail), with waterfall v2 as the worked example · monitoring
cadence with the NDC alarm as the teaching case · the five Power BI traps (incl. the
revenue-halving filter) · a **two-week KT plan where every exercise has a pass condition** (incl.
deliberately breaking a guardrail on day 7) · the limitations that must travel · and the four-tier
roadmap (data investments → close the validation loop → gated model work → production hardening).
*Generalises: a handover document is a set of runnable procedures with pass conditions, not a
description of the system — the test of KT is whether the receiving team can break something safely
and read the report that catches it. And "retrain" is a dangerous word for a deterministic
labeller: define the maintenance actions by their triggers, or the new owner will schedule
retraining that does nothing and skip the rule governance that matters.*
**Source:** our analysis, 2026-08-27 — `docs/handover-pack.md` v1.0, distilled from `README.md`,
`docs/methodology.md` v1.12, `docs/installation.md`, `outputs/` stage summaries.

---

#### 2026-08-26 — The deck was rebuilt business-first (28 slides), and the validation story moved entirely into Q&A
**Domain:** Project Decision
The defence deck was rebuilt on 26 Aug (`CPT3_DefenseDeck_V3 1.pdf`, 28 pages) — a restructure,
not an edit: Executive Summary with dollar value up front ($2.7M returns · $272K SaaS avoided ·
4,612 man-hours · 3 FTEs · Traveler DNA), business case expanded to five slides (do-nothing chart,
buy-vs-build vendor table, the $360k Traveler DNA system, man-hours), a live Power BI demo, and a
three-horizon timeline. It also adopts the new bookings-vs-revenue region chart (`eda_02b`).
**The strategic consequence: the continuum proof, the ten-method benchmark, circularity, and all
four validation stages are off the slides** — the science is now defended only in Q&A, so backup
slides (old continuum / honest-validation / V1–V4 scorecard) and the question bank carry the
technical defence. Audit findings, all in `final-defense-reviewer.md` §3.1/§5/§7: ① slide 6's stat
tile says **"10 commercial segments"** against slide 16's **"11 Segments Identified"** — an
on-deck contradiction; ② the limitations slide shrank to 4 owned + 3 in-flight and **dropped
"labels add little incremental prediction"** — the previously-rehearsed most-likely question is no
longer owned on-slide; ③ new repo-unsourced numbers lead the deck ($272K reconstructs as cheapest
vendor $350K+ minus the $77,904 build; the man-hours and $360k bases live in the companion
workbook); ④ slide 13's PCA legend still carries v1 segment names — the one stale figure that
survived; ⑤ slide 5 brands the model "Semi-Supervised" — defensible as rules-as-weak-supervision +
unsupervised refinement, but it needs the scripted one-liner. This supersedes the earlier same-day
entry's action items about the 20 Aug pptx ("stratified" caption, "20.6M flight rows",
`clust_01` "≤ 0.34") — those slides no longer exist.
*Generalises: when a deck is rebuilt for a business audience, the first thing cut is the evidence
of rigour — and the Q&A preparation must expand by exactly what the slides dropped. Audit a rebuilt
deck as a new artifact, not a diff: the defects that matter are contradictions between surviving
slides and inherited numbers whose derivations left the room.*
**Source:** our analysis, 2026-08-26 — page-by-page read of `~/Downloads/CPT3_DefenseDeck_V3 1.pdf`
(28 pp) against `docs/defense-brief-2026-08-18.md`, `docs/business-case-benchmark.md`,
`outputs/sub_segments/`, `src/pal_colors.py`.

---

#### 2026-08-26 — Deck context folded into the reviewer, and the pptx audit found two more stale on-slide details
**Domain:** Project Decision
Added a slide-by-slide deck section to `docs/final-defense-reviewer.md` §5 (and the published
artifact), built by **extracting the 26 slide headlines from the built pptx with python-pptx**
rather than from the study guide's table — the repo's own "audit against the artifact, not memory"
rule. Structure confirmed: Problem/TOR Martin (3–4) · EDA+Methodology Josh (5–13) · Dashboard Jadd
(14–15) · Findings Josh & Jadd (16–22) · Before-handover Josh (23) · Recommendations Martin (24) ·
Conclusion Josh (25); timing Martin 8 · Josh 20 · Jadd 7 · conclusion 2.
**Two stale on-slide details the extraction surfaced, both now on the pre-defence checklist:**
① **slide 8's caption still says "60k stratified sample" — the sample is uniform.** The 19 Aug
audit fixed the same wrong word in `report_figures.py`'s suptitle but the deck's own text box kept
it; uniform is also the *correct* choice (stratifying can manufacture structure), so the fix is the
caption, not the method. ② **slide 15 says "the fact table carries 20.6M flight rows" — it is
20.7M since the 21 Aug level-2 rebuild** (the deck was built 20 Aug 00:45). Same class as the
scorecard 1,835 → 3,544 staleness already recorded: the level-2 rebuild moved export-side counts
after the deck froze.
*Generalises: a deck freezes the day it is built; any pipeline rebuild after that date should
trigger a grep of the deck text for the counts that rebuild moves. And a wording fix applied to a
generator does not propagate to artifacts that copied the old wording — search for the sentence,
not just the figure.*
**Source:** our analysis, 2026-08-26 — python-pptx extraction of
`assets/final-defense/CPT3_DefenseDeck_V3.pptx` vs `outputs/powerbi_export/` counts and
`src/report_figures.py`; `docs/final-defense-reviewer.md` §5.

---

#### 2026-08-25 — Region mix inverts on revenue: domestic is 58% of bookings and 19% of revenue; North America is 8% and 35%
**Domain:** Data & Features
Built the revenue companion to the bookings-per-region chart (`fig_route_region_revenue` in
`src/report_figures.py` → `outputs/report_real/figs/eda_02b_region_revenue.png`; grouped bars,
bookings share vs revenue share, same region order, avg $/booking under each label). Measured on all
22.9M bookings (`rev_pos`, the same field eda_01's value panel uses): **Philippines (domestic)
57.69% of bookings but 19.34% of revenue ($91/bk)**; **North America inverts hardest — 8.38% of
bookings, 35.26% of revenue ($1,141/bk, 12.6× domestic)**; East Asia 14.80%/16.90% ($310); Southeast
Asia 11.78%/13.86% ($319); Middle East 4.03%/6.90% ($464); Oceania 3.32%/7.74% ($631). So the
segment-level volume–value inversion (Leisure vs Balikbayan) has a clean geographic expression:
**the domestic network is a volume business, the trans-Pacific network is the revenue business** —
consistent with Balikbayan/VFR (28.4% of revenue) being heavily North America. Caveats that travel
with the chart: `dest_region` is the alphabetical-max label (1.65% of bookings mis-regioned, 19 Aug
entry), and the Europe/South Asia 0% bars mean no own-metal sectors, not no demand.
*Generalises: any share-of-volume chart in this project should offer its share-of-revenue twin —
the two rankings disagree at every grain we have tested (segment, sub-type, and now region), and the
disagreement is usually the commercial finding.*
**Source:** our analysis, 2026-08-25 — DuckDB over `data/interim/pal_features_booking.parquet`;
`src/report_figures.py::fig_route_region_revenue`.

---

#### 2026-08-25 — "87.8% of customers never leave their segment" is mostly censoring: 53.4% among repeaters
**Domain:** Data & Features
Stress-testing `do-nothing-vs-implement.md` §3 for the defence: its enabling fact — **87.8% of
customers have `segment_diversity = 1`** — is carried mostly by the **73.9% of customers who book
exactly once and therefore cannot have diversity > 1** (the same right-censoring §4.5 already owns
for churn). Measured directly on `pal_features_customer.parquet`: among the **3,512,004 repeat
customers** (n_bookings > 1), diversity = 1 holds for **53.41%**; among customers with 3+ bookings,
**38.58%**. Back-of-envelope independence baseline (two bookings drawn independently from the v2
booking mix, Σpᵢ²) is **~31%**, so repeat customers stick to one segment at roughly **1.7× chance** —
real, but far weaker than 87.8%. The person-level treatment argument survives via
`CustomerDominantSegment` (a dominant segment is always defined), but **87.8% must never be quoted
without the censoring caveat** — a data-scientist panel will decompose it in seconds, and the
document was written for that panel. Repaired wording and the drill answer live in
`docs/final-defense-reviewer.md` §3.1 (new doc, 25 Aug — the consolidated defence reviewer:
current-state deltas since the study guide, stress test of the argument chains, 54-question panel
Q&A). Same pass confirmed two open items: the defence deck (built 20 Aug 00:45) still embeds the
23 Jul `clust_01`/`clust_02` PNGs superseded by the 23 Aug renders, and `methodology.md`'s Stage V1
section still says "45 segment pairs" (10-segment era; shipped run tests 55).
*Generalises: any "X% of customers are stable" statistic over a fixed window is bounded below by
the share who only appear once — decompose by opportunity-to-change before quoting stability, or
the number measures the window, not the customer.*
**Source:** our analysis, 2026-08-25 — DuckDB probe over `data/interim/pal_features_customer.parquet`
(13,435,365 customers); `docs/do-nothing-vs-implement.md` §§3, 4.5.

---

#### 2026-08-23 — Chapter 5 restructured to the programme outline: findings split technical/strategic, conclusions move last
**Domain:** Project Decision
Rewrote `manuscript-ch5-draft.md` as **v2.0 — "Findings, Recommendations, and Conclusions"** on the
requested outline: **§5.1 Summary of Technical and Strategic Findings** with **§5.1.1 Technical Machine
Learning and Behavioural Findings (F1–F8)** and §5.1.2 Strategic and Business Findings (F9–F13), and
**§5.6 Final Project Conclusions** (the former C1–C4 plus the concluding statement). Sections between
renumber: economic case §5.3→§5.2 · build-vs-buy §5.4→§5.3 · recommendations §5.5→§5.4 · limitations
§5.6→§5.5. **Two content additions fell out of the split:** a new behavioural finding (F8 — 87.8%
segment stability, the 3× repeat floors, the August/December OFW–Balikbayan complementarity, the Gulf
one-month clock with its confound), which had never been in the findings list despite carrying §4.2.2's
best domain evidence; and four strategic findings (F10–F13: volume–value inversion, the $645.8M
mispricing exposure, derived department readiness, the $495–$9,784 misclassification spread) promoted
from ch. 4/Appendix A prose. Old F8 (identity ceiling) became F9; every F- and §-reference updated in
ch. 5, the two business-case docs, Appendix A, the README, and the plates artifact.
*Generalises: a findings list drifts toward whatever chapter wrote it first — restructuring against an
external outline is a cheap audit that surfaces findings the prose had but the list did not.*
**Source:** our analysis, 2026-08-23 — `docs/manuscript/manuscript-ch5-draft.md` v2.0.

---

#### 2026-08-23 — DB and CH, computed at last, agree with everything: no internal index finds a k
**Domain:** Clustering / Methodology
Ran silhouette, Davies–Bouldin, and Calinski–Harabasz over the k = 1–9 LCA sweep on the standardised
one-hot (Euclidean) representation of the same 60k sample (seed 42; silhouette sampled at 10k). Saved to
`outputs/report_real/lca_validity_indices.csv`. **Silhouette 0.074–0.133** (never leaves the <0.25
no-structure band; max at k = 2, the geography cut). **Davies–Bouldin 2.62–3.03** at every k —
well-separated clusters run near 1 — with its "best" value at k = 9, the top of the range again.
**Calinski–Harabasz declines monotonically from k = 2** (6,610 → 3,210), no interior peak. So every
internal validity index that can be computed on this data agrees with BIC: nothing settles, and the only
preference any index shows is the trivial domestic/international cut. Folded into ch. 4 §4.1.1(b) (v1.5)
and the Figure 1 plate (now five panels); the earlier entry's "not applied" answer is upgraded to
"applied on the representation where they are defined, and they corroborate".
**Also shipped: Appendix A's six exhibits** (spread ratios + dilution stats · agency dependence ·
digital/connecting spans · repeat floors · breakeven stats + the five-year band with the 10% path
deliberately undrawn · readiness table) in the plates artifact, with `[Exhibit A.n]` placeholders in the
appendix.
*Generalises: when a metric cannot run in the primary geometry, compute it in the geometry where it is
defined and report both — "the index does not apply" invites the question; "the index, where computable,
agrees" closes it.*
**Source:** our analysis, 2026-08-23 — `outputs/report_real/lca_validity_indices.csv`;
StepMix k = 1–9, sklearn silhouette/davies_bouldin/calinski_harabasz on the one-hot matrix.

---

#### 2026-08-23 — A stress test designed for a placeholder must be redesigned when the placeholder becomes a measurement
**Domain:** Project Decision
Wrote manuscript **Appendix A** (`docs/manuscript/manuscript-do-nothing-analysis.md` v1.0) — the
do-nothing analysis in manuscript register, expanding Ch. 5 §5.3 from `do-nothing-vs-implement.md`.
**The carry-over that could not survive unchanged: the sensitivity analysis.** The 21 Aug document
stressed year-1 cost by 10× because A5 was a placeholder; A5 is now the actual $77,904 budget, and a 10×
stress on a *measured* number is noise, not diligence. Appendix A restates the stress on what is still
assumed: halve A8·A9 (dilution pool → $4.04M) → breakeven **1.9%**; add market-rate staffing ($487K
shadow) → **12.1%**; base case at the actual budget **0.48%** (one in 207). Five-year cumulative cost at
5%/yr escalation: **$430K = 0.53% of the five-year pool** (supersedes the 0.047% computed on the $18.8K
placeholder).
**Also answered from the code, for the defence: which internal validity indices the model actually uses.**
Silhouette is the cross-method yardstick everywhere (it is the one standard index defined on a precomputed
non-Euclidean distance); **Davies–Bouldin and Calinski–Harabasz appear only in `monitor_metrics.py`, the
prototype-track monitor, subordinate to DBCV** — both presuppose Euclidean centroids, undefined under
Gower on mixed-type features, so they were never applied to the real benchmark. The rationale (with the
1974/1979 citations) is now one sentence in ch. 4 §4.1.1(b) so the question is answered on the page.
*Generalises: every sensitivity analysis encodes which inputs it believes are uncertain. When a
placeholder graduates to a measurement, re-derive the stress on the remaining assumptions — carrying the
old stress forward either overstates the margin (stressing a known) or hides the new binding uncertainty.*
**Source:** our analysis, 2026-08-23 — `docs/manuscript/manuscript-do-nothing-analysis.md` §A.7;
`src/monitor_metrics.py` vs `src/model_zoo.py` grep; `docs/do-nothing-vs-implement.md` §7.

---

#### 2026-08-23 — Two business cases, one decision instrument: the benchmark NPV sizes, the breakeven decides
**Domain:** Project Decision
Imported the top-down benchmark business case (companion workbook, Aug 2026) as
`docs/business-case-benchmark.md` and wrote manuscript **Chapter 5** (`manuscript-ch5-draft.md` v1.0 —
findings, conclusions, the economic case, build-vs-buy, recommendations). The two cases conflict on cost
and philosophy, and Ch. 5 §5.3 resolves it by division of labour: the **bottom-up measured case is the
decision instrument** (breakeven), the **top-down case is conditional sizing** (~$2.7M/yr risk-adjusted,
+$7.3M 5-yr NPV at 10%). **Year-1 cost is now $77,904 actual budget**, superseding the $18,800
placeholder — breakeven moves 0.116% → **0.48%** of the measured $16.1M dilution exposure (one dollar
in 207), and 6.1% against the marketing contact lever alone.
**Three measured conditions attach to the benchmark case, all from our own Ch. 4 results:** ① the
ancillary lever ($1.23M/yr, 45% of the claimed benefit) rests on revenue the extract does not contain;
② the retention/churn lever presumes an identity the data lacks (73.9% single-booking, churn not
computable — the same fact that put Loyalty last in the readiness ordering); ③ the assumed $1.96B
revenue base is ~⅓ below the extract's measured ~$2.9B/yr ($6.22B/26 months) — conservative in
direction, but the case should start from the census figures.
**Build-vs-buy resolves on facts, not price quotes:** actual build cost $77,904/yr ($487K/yr at
market-rate staffing, NPV still +$5.9M); every vendor case study in the evidence base (KLM, easyJet,
Alaska…) runs on identified customers, so a bought platform inherits our anonymity ceiling while
charging licence from day one; and the auditable in-house rules are a functional requirement for a
taxonomy governed as an instrument. **Recommendation: build (done); the re-evaluation trigger is
identity-data arrival**, which enables the vendors' strongest levers and ours simultaneously.
*Generalises: when a top-down and a bottom-up case disagree, do not average them — assign each the
question it can actually answer, and let the measured one carry the decision. And any benefit lever
should be classified measured / benchmark-derived / conditional at the point of use, or the biggest
number in the deck will be the least supported one.*
**Source:** our analysis, 2026-08-23 — `docs/business-case-benchmark.md` (imported),
`docs/do-nothing-vs-implement.md` §§5–7, `docs/manuscript-ch5-draft.md` §§5.3–5.4.

---

#### 2026-08-23 — Extending the ARI panel to k=2 finds a 0.54 peak, and it is geography, not customer structure
**Domain:** Clustering / Methodology
Regenerating `clust_01_bic_ari.png` with the extended `K_RANGE(1, 10)` surfaced a number no document had:
ARI against the v2 taxonomy peaks at **0.537 at k = 2** — above the 0.389 (k = 4) every doc quotes as
"best agreement" — because k = 2 had simply never been fitted. Composition probe of the cut: **ARI 0.909
against the domestic/international bit alone**; every purely international segment lands ≥94.8% in one
class; Corporate — the most geographically mixed segment — splits **50.1/49.9**, i.e. its own 57/43
domestic mix expressed through the other features. So the k = 2 partition is `is_domestic` rediscovered,
and agreement *falls* toward the taxonomy's own cardinality (0.306 k=3 · 0.389 k=4 · 0.210 k=9). That is
a sharper statement of the standing conclusion: **unsupervised methods recover the taxonomy's geographic
spine and none of its finer boundaries.**
**⚠️ Supersedes the 19 Aug guidance "a regenerated figure must annotate ≤ 0.39":** the shipped figure now
annotates **≤ 0.54**, and 0.54 must never be quoted without the geography qualifier — the
customer-structure ceiling is still ~0.39. Reconciled same day: manuscript §4.1.3,
`pipeline-study-guide.md`, `eda-results-slide-guide.md`, and `reports/study_guide/*.png` refreshed to the
23 Aug renders. **Still open: the defence deck embeds the 23 Jul PNGs (clust_01 says ≤ 0.34, clust_02
shows retired segment names) and needs a re-insert.**
*Generalises: extending a sweep can move a "best over the sweep" headline even when every
previously-fitted point reproduces exactly. A max is only as stable as the range it was taken over —
state the range beside the number.*
**Source:** our analysis, 2026-08-23 — composition probe over `pal_features_booking.parquet` (60k,
seed 42, StepMix k = 2); `outputs/report_real/figs/clust_01_bic_ari.png`.

---

#### 2026-08-23 — The BIC sweep never tested k=1 or k=2, and extending it strengthens the continuum claim
**Domain:** Clustering / Methodology
An examiner-style screen of the ch. 4 final draft asked the first question any continuum claim provokes:
"is the base one mass or two?" — and the answer was unmeasured, because every sweep starts at k=3
(`report_figures.py` `K_RANGE = range(3, 10)`; the stress test sweeps 3–12). Ran the probe: identical
60k reservoir sample, seed 42, identical `codes_for_lca` coding, K extended down to 1.
**BIC: k=1 1,148,667 · k=2 1,057,599 · k=3 1,014,017 · k=4 988,748** — the k=3 value reproduces the
19 Aug sweep exactly, verifying the construction. So the monotone decline starts at one component:
there is no elbow at 2 either, and each added class buys less than the one before (91,068 → 43,582 →
25,269). The base is not "two masses"; the criterion never finds a place to stop. Folded into ch. 4
§4.1.1(a); `K_RANGE` is now `range(1, 10)` so the next figure regeneration carries k=1–2 (k=1's
ARI-vs-proxy is degenerately 0, harmless on the plot; `k_star = argmin` is unaffected, still the top of
the range).
**The same screen produced the rest of v1.1's fixes, two worth remembering:** ① the draft had placed the
taxonomy's 0.091 Euclidean silhouette beside the 0.381 Gower ceiling with no comparability warning —
exactly the misreading the 19 Aug entry warned against, reproduced by the same author four days later;
a recorded incomparability needs to travel *with the numbers*, not sit in a log. ② every sampled analysis
reports single-seed point estimates with no interval, and only V4 had owned that; it is now the seventh
limit in §4.3.7 and a census-vs-sample paragraph in the preamble says which numbers carry sampling error
at all.
*Generalises: when a criterion is monotone over a search range, extend the range downward until it isn't —
"no elbow from 3" and "no elbow at all" are different claims, and the second costs four minutes to earn.*
**Source:** our analysis, 2026-08-23 — 60k probe replicating `src/report_figures.py` construction
(StepMix 3.0.0, seed 42, n_init=2); `docs/manuscript-ch4-draft.md` v1.1.

---

#### 2026-08-23 — Manuscript ch. 4 final draft: v2 throughout, and the sub-type figures switch to population-exact
**Domain:** Project Decision
Rewrote `docs/manuscript-ch4-draft.md` as the final draft (v0.1 → v1.0). Everything is now measured on the
shipped v2 taxonomy and the 18 Aug validation re-runs; every withdrawn or superseded figure from the
defence brief's never-say list is either absent or quoted only as an explicit disowning (the 1.13 transfer
ratio, 0.608→0.72, 62.7% reclassified, Corporate 35.6% short-lead, the H0 count, refund AUC).
**The author's call flagged on 21 Aug is resolved: the manuscript quotes the population-exact level-2
profiles** (`outputs/sub_segments/population_profiles.md`) — Balikbayan/VFR $322→$962, Corporate $113→$643 —
**and states that they supersede the sampled ones; the defence deck and `summary.md` keep the sampled
figures** ($311→$995), since the deck is already built and rehearsed against them. Any reader comparing the
two documents will find the discrepancy explained in the manuscript's §4.2.5, not discovered.
**Figure staleness is now tabled in the draft itself:** ms_fig4/5/6 were rendered 8 Aug from pre-re-run
outputs and need one `python src/manuscript_figures.py` pass (renders from saved outputs, no refits);
`eda_01_segments.png` and `sub_01_subtypes.png` are 23 Jul v1-label artwork and need `report_figures.py`
pointed at v2 first. The two OFW↔Balikbayan adversarial checks (13-of-17 markets, seasonality signature)
are kept but labelled as v1-label measurements that stand because the v2 change moves 1.4% of the branch.
*Generalises: a final draft is the right moment to resolve every "author's call" the working documents
carry — and when two shipped artefacts must disagree (population-exact vs sampled), the newer document
should name the discrepancy and say which is authoritative, so the difference reads as a decision.*
**Source:** our analysis, 2026-08-23 — `docs/manuscript-ch4-draft.md` v1.0;
`outputs/sub_segments/population_profiles.md`; `docs/defense-brief-2026-08-18.md` never-say list.

---

#### 2026-08-21 — A benefits case organised by department, and a revenue filter that silently halved a segment
**Domain:** Project Decision
Built `docs/do-nothing-vs-implement.md` for the defence panel, then rebuilt it around **the five departments
that would consume the output** — RM (pricing) · Sales (channels) · Marketing (promos) · CX (web/app &
lounge) · Loyalty (churn) — rather than around abstract benefit levers. The reframing changed the
conclusion, because it forces the question "which department can act on this *today*".
**⚠️ The measurement error worth remembering.** Computing revenue with `Bookings > 0` (equivalently
`IsPrimaryCoupon = TRUE`) **discards every non-primary coupon's revenue**: Balikbayan/VFR **−54%** ($712M →
$331M), Leisure −27%, OFW/Migrant −17%. It bites hardest on multi-leg segments and the result still looks
like a plausible revenue figure. Correct form: `sum(NetRevenue) / sum(Bookings)` over **unfiltered** rows.
**How it was caught: an independent cross-check, not inspection.** The filtered means contradicted
`segment-cost-research.md` §3 by more than 2× (Balikbayan $275 vs $615); the corrected means agree with it
within ~7% across eleven segments ($593/$615 · $82/$80 · $302/$312 · $429/$460). Now documented as the
fourth scorecard warning in `powerbi-guide.md` §3a, because a BI developer will hit it.
**Every figure moved.** Corporate's within-label spread **4.31× → 5.63×**; Leisure 2.86 → 3.76;
Balikbayan 2.58 → 2.68; OFW 1.98 → 1.60; and **Outbound Intl. Leisure 4.26× → 1.29×** — from second-most
heterogeneous to *most homogeneous*, i.e. the parent where level 2 buys RM almost nothing. Volume-vs-value
TVD is **36.26% at level 1 ($919M)** and 36.99% at level 2 — level 2 still adds almost nothing on that
metric (+0.73pp for 2.2× the labels), which is why the doc argues level 2 from within-parent mispricing
instead: sub-types priced **≥1.25× their parent mean** are 22.9% of parent bookings and **29.7% of parent
revenue ($645.8M)**; at 1.5×, **3.9% of bookings and 16.4% of revenue**.
**The department reframing's payoff: the strongest case is not the biggest number.** **Sales and CX need no
response assumption at all** — prioritisation reallocates effort already being spent, so the measured fact
*is* the deliverable. Sales: agency dependence spans **6.6×** (Corporate 11.8% → Pilgrimage 78.2%);
Corporate is **55.5% corporate-channel** (TMC 42.5% + portal 13.0%); **Sea Crew is 27.5% of OFW/Migrant and
~0% of everything else** — a $136.6M channel that *is* one segment. CX: digital revenue share spans **19×**
(2.6% → 48.8%) and connecting share **9×** (10.4% → 97.7%), so transfer/lounge is a *Balikbayan/VFR*
question (49.9% connecting on the largest revenue base), not a premium-cabin one.
**Loyalty is the department that must wait, and saying so strengthens the case.** **73.9% of customers have
exactly one booking and `tenure_days = 0`** — in a 26-month window a new customer and a lost one are
identical, so no churn rate is computable, only a floor on repeat behaviour (12.2% Pilgrimage → 36.4%
Corporate). `Mabuhay Loyalist` is **100% `ever_award`, 7.8% repeat** — an award-redemption artifact, not a
loyalty population, pending PAL answer B4.
**One enabling fact underpins all five:** **87.8% of customers have `segment_diversity = 1`** — they never
leave their segment, so a segment label on a *person* is stable rather than a per-trip accident.
**Breakeven, not forecast:** year-1 cost $18,800 (placeholder) against $16.1M avoidable dilution needs
**0.116%** — one dollar in 859. Ten times worse on every placeholder at once: **4.7%**. The claim is not
"the benefit is $16M" but "the decision does not depend on knowing the benefit".
*Generalises: organise a benefits case by who owns the decision, and the readiness ordering falls out of
the evidence instead of out of preference. And cross-check any aggregate against an independently computed
one — inspection would never have found a filter that returns a plausible number.*
**Source:** our analysis, 2026-08-21 — `docs/do-nothing-vs-implement.md`;
`outputs/powerbi_export/model/fact_flight/` (CY2025, flown, revenue-clean);
`data/interim/pal_features_customer.parquet`; `docs/segment-cost-research.md` §3.

#### 2026-08-21 — "10 named segments" survived in three docs three days after v2 shipped 11
**Domain:** Data & Features
Asked to justify why `dim_segment.csv` has 13 rows against a remembered "10 + 1". The count is right and the
docs were wrong. Authoritative chain: `proxy_segment` in the built booking table has **12 labels = 11 named
+ Unassigned**; `pal_colors.SEG_ORDER` holds the same 12 and carries the comment *"waterfall v2 shipped, so
approved and emitted are the same list"*; the 20 Aug learning-log entry already said 11 + Unassigned and
proved it two ways (12 rows in `profile_drift.csv`, 55 = 11x10/2 pairs in `pairs.csv`). The **13th** row is
export-only: `Excluded (non-revenue)`, stamped on the **15,073 coupons / 13,127 bookings** whose customer was
dropped at Stage F and therefore has no booking row to inherit a label from.
**Still asserting the v1 count on 21 Aug:** `methodology.md`'s at-a-glance table *and* its current-pipeline
mermaid node (both now fixed), and `README.md`'s opening paragraph — which went further and said *"the
waterfall change is pending"*, three days after it landed. Corrected. The `10 segments` references in the
HDBSCAN/Stage-6 sections are **correct** for the superseded prototype track and were left alone; that
ambiguity is exactly why the wrong number reads as plausible.
**Unresolved, and only PAL's record can settle it:** the approval is written up as a *"13-segment
taxonomy"* (17 Aug) while `SEG_APPROVED` holds 12 entries. It reconciles to 11 named only if the 13 counted
`Digital Nomad` and `Last-Minute`, both removed the next day — unimplementable in anonymous data, and
demoted to a booking flag. Flagged in the README rather than silently renumbered.
*Generalises: a stale count is hardest to spot when an older, superseded track makes it a legitimate number
somewhere else in the same document. "10 segments" was never a typo — it was true of the prototype, so
grep-and-fix is wrong and every hit needs reading. The tell that the v2 rename never propagated was not the
count itself but the sentence beside it: "the waterfall change is pending".*
**Source:** our analysis, 2026-08-21 — `data/interim/pal_features_booking.parquet` (`proxy_segment`,
12 labels), `src/pal_colors.py` (`SEG_APPROVED`/`SEG_ORDER`/`SEG_RETIRED`),
`outputs/powerbi_export/model/dim_segment.csv` (13 rows), knowledge base §15 entry 2026-08-20.

#### 2026-08-21 — Level 2 shipped: 21.7M bookings assigned, and three defects only the population could reveal
**Domain:** Clustering / Methodology
Built what the scoping entry above proposed. `src/subsegment_assign.py` assigns a level-2 `SubSegment` to
all **21,725,296** bookings in the five sub-typed parents, and the Power BI export carries it on every fact
table plus a 28-row `dim_subsegment` (20 sub-types + a self-named row per segment without them + Excluded).
Deliberately a *separate* entrypoint from `sub_segment.py`, so `summary.md` — which the deck and
`sankey_subsegment.py` read — is untouched; population profiles go to `population_profiles.md`.
**Reproducibility does not come from `random_state`.** Under `PRAGMA threads=6` a bare `GROUP BY` returns
cells in a different order every run, which changes the order StepMix sees and therefore which EM local
optimum it lands in — two consecutive runs gave **OFW/Migrant different sub-type boundaries**. `ORDER BY
ALL` on the cell table is load-bearing; verified by hashing the lookup CSVs across two full runs.
**`name_sub()` collides within a parent, not just across parents.** On the population fit two OFW/Migrant
classes both round to `one-way · advance · saver`, distinguishable only by connectivity (0% vs 97%) — which
the name never mentions. Collisions now take a `· connecting` / `· nonstop` qualifier.
**Adding one string column to a 38.1M-row `PARTITION_BY` COPY OOMs at 8 GB, three ways** — joined at coupon
grain, joined at booking grain, and with the merge materialised flat. Peak memory scales with
partitions x threads, so `PRAGMA threads=3` for that one statement keeps the 8 GB contract instead of
raising it for everyone; the booking-grain merge is cached to `.build/bk.parquet`. Build 2 min → 5 min.
**A pre-existing level-1 defect fell out of it:** `dim_segment.csv`'s `SegmentSortOrder` had **11 twice**
(Leisure and `Excluded (non-revenue)`) and no 1, so Power BI ordered those two arbitrarily. Excluded moved
to 14; `dim_subsegment` uses a dense 1..28 rank so it cannot inherit the same bug. Also refreshed
`powerbi-guide.md`'s "Segment mix at a glance", which still named **Budget/Adventure, Last-Minute and
Family** — three labels the shipped taxonomy does not contain.
**Row growth landed where predicted:** `fact_dashboard` 2,037,886 → 2,267,904 (**1.11x**), `fact_flight`
20.6M → 20.7M, because the flight grain already groups by most of the LCA's inputs. **Level 1 is
byte-identical** across the rebuild and all three fact tables reconcile (38,116,259 coupons · 22,924,577
bookings · 6,219,305,620 revenue); `SubSegment` has no NULLs, no orphans either way, and sits under exactly
one `CustomerSegment`.
**Open:** the two fits disagree on Balikbayan/VFR — the population fit splits `far-advance · saver` into
connecting (median rev **418**) and nonstop (median rev **962**) where the sample gave
`far-advance · value / supersaver / saver`. The deck, `summary.md` and `manuscript-ch4-draft.md` (still
"future work") keep the sampled version; reconciling is an author's call.
*Generalises: a model fitted on a sample hides three classes of defect that only the population shows —
an encoder that learnt its alphabet from the sample, a naming scheme whose collisions were merely unlikely,
and a memory profile nobody measured. Fitting the whole population is not just more accurate, it is more
revealing.*
**Source:** our analysis, 2026-08-21 — `src/subsegment_assign.py`, `src/export_powerbi.py`,
`docs/subsegment-scoring-plan.md` §7, `outputs/sub_segments/{model_meta.json,population_profiles.md}`,
`outputs/powerbi_export/model/dim_subsegment.csv`.

#### 2026-08-21 — Level 2 is not in the Power BI model, and the scoring pass is far cheaper than assumed
**Domain:** Clustering / Methodology
Asked whether the Power BI export carries sub-segments. It does not: `fact_coupons`, `fact_flight`,
`fact_dashboard` and `scorecard_segment_month` all carry `CustomerSegment` only, `dim_segment.csv` is the
top-level taxonomy (13 rows), and `CustomerDominantSegment` is still a *level-1* label — just resolved per
traveller instead of per coupon. `export_powerbi.py` never references a sub-type.
**The cheap route.** `code()` reduces a booking to a fully discrete vector, so the model's input domain is
enumerable: **17,847 distinct feature cells cover all 21,725,296 bookings in the five parents** (Leisure
1,281 · OFW/Migrant 5,796 · Balikbayan/VFR 1,175 · Outbound 2,857 · Corporate 6,738). So row-level
assignment is not a 21.7M-row scoring pass — it is `predict` on ≤6,738 rows per parent plus a SQL join,
and the resulting level-2 model is a CSV that can be read end to end.
**The sample can go.** StepMix 3.0.0's `fit` takes `sample_weight`, so fitting the count-weighted cell
table *is* fitting all 21.7M bookings exactly — verified, not assumed: `score(cells, sample_weight=counts)`
equals `score(rows replicated by count)` to machine precision. That retires `SAMPLE = 40_000` and the
reservoir-sampling scar.
**But `m.bic(X)` then lies.** Its source is `-2*score(X)*X.shape[0] + n_parameters*log(X.shape[0])` —
unweighted score, N = number of *cells*. On a weighted cell table that is N = 17,847 against the wrong
likelihood, silently, and `K_RANGE` selection depends on it. Weighted BIC must be hand-computed as
`-2*score(cells, sample_weight=w)*W + n_parameters*log(W)`.
**Four defects found in the current sub-segmentation while scoping, all invisible at sample scale:**
① `dest_region` is coded by `astype("category").cat.codes`, which numbers categories by what the *sample*
saw — OFW/Migrant's 40k sample sees **6** regions, its population has **7**, so the codes shift on refit
and the missing level cannot be encoded at all. ② the `value_tier` median-fill is sample-derived (2.0 for
four parents, **4.0 for Corporate**) against population nulls of 12,426 / 11,647 / 1,411 / 1,014 / 0.
③ the dropped-constant-column list is part of the model (Balikbayan drops `round_trip` + `foreign_issue`,
Outbound `foreign_issue`, Leisure `dest_region` — all 11.6M Domestic) and must be persisted, not
re-derived. ④ `name_sub()` collides *across* parents — `one-way · advance · saver` is emitted by Leisure,
OFW/Migrant **and** Outbound — so any Power BI key must be composite `Parent — sub_name`.
*Generalises: a layer fitted on a sample can be silently un-scoreable on the population, and the tell is
always an encoding that learns its own alphabet from the sample. Check the domain, not the fit.*
*Also: when the feature space is discrete, "score every row" is the wrong unit of work — score the
distinct cells and the model becomes auditable as a side effect.*
**Source:** our analysis, 2026-08-21 — `docs/subsegment-scoring-plan.md`;
`data/interim/pal_features_booking.parquet` (22,911,450 bookings); `outputs/powerbi_export/**` parquet
schemas; `src/sub_segment.py`, `src/export_powerbi.py`; `stepmix==3.0.0` source + empirical check.

#### 2026-08-20 — Defence study guide audited against the deck programmatically, not by memory
**Domain:** Project Decision
Rather than re-reading the guide, diffed it against the artefact: pulled all 26 slide titles out of the
pptx with python-pptx and matched them row-by-row to §6's table (**26/26 aligned**), then grepped for every
superseded figure this week produced. The table was already correct after the two renumbers; the gaps were
all in §5 and §9, i.e. the tables meant to stop a stale number reaching the room.
**Added to Memorize:** the 11-segments-vs-12-labels denominators · **Corporate 6 of 10** and Leisure 5 of 10
weak V1 boundaries · Leisure at **50.6%** · the sub-segmentation's 5×4 = **20 cells** and Balikbayan's
**$311 → $995** span · and the **strict median 0.637** beside the adaptive 0.861, since §8 already drilled
that comparison without the guide stating both numbers.
**Added to Never-say — five traps, all found on 19–20 Aug:** "BIC chose four sub-types" (search ceiling) ·
"the drift is in the tiny segments" (v1 wording; Premium Bleisure is 7th-largest of twelve) · "13.3% /
median 25 days" (coupon grain on booking-grain slides) · "74% never return" (right-censored) · "38.4%
issued abroad" as a booking figure (it is the coupon share; bookings are 34.6%).
**Added to §9 Stale numbers:** the V4 TVD generation, "transfers for free", "7 of 10 carrying 98.2%", both
grain traps, and — the one most likely to be quoted at us — **`rule_confidence.py`'s 66.5% / most-contested
Corporate was computed on v1 labels and the script still hard-codes the v1 ten-branch waterfall**, so there
is no current figure. Also noted that any printout whose row 19 is not "sub-segments" is a stale deck.
Closed with a 16-point automated checklist; all pass.
*Generalises: audit a companion document against the artefact it describes, not against your memory of the
artefact. The slide titles are extractable, so the table check is a script — and the parts a script cannot
check (the never-say table) are exactly the parts that rot, because nothing errors when they go stale.*
**Source:** our analysis, 2026-08-20 — `docs/defense-study-guide.md` vs
`assets/final-defense/CPT3_DefenseDeck_V3.pptx` (26 slides), `outputs/validate_construct/pairs.csv`.

#### 2026-08-20 — "11 segments" and "12 labels" are both right, and the deck never said why
**Domain:** Data & Features
Caught in review: slide 21 quotes **8 of 12** labels for V4 while the taxonomy is **11** segments everywhere
else, with nothing on the slide reconciling them. Both are correct and the difference is deliberate.
**11 segments + `Unassigned` = 12 labels the pipeline can stamp.** **V1 tests the 11** — hence
11×10÷2 = **55 pairs** — and excludes `Unassigned` because it has **no positive definition**: it is
"nothing else claimed this", so there is no claim to validate. **V4 tests all 12**, because drift in the
residual bucket *is* informative — if the leftovers change composition, the rules are losing grip on
something. Verified in `profile_drift.csv`: 12 rows, and `Unassigned` sits in the **stable** column
(`small`), alongside Leisure · OFW/Migrant · Balikbayan/VFR · Outbound Intl Leisure · Corporate ·
Ultra Wealthy Leisure · Intl. Student. Slide now reads "8 of 12 labels stable (the 11 segments plus
Unassigned)" so it is self-explaining.
**Second wording trap in the same sentence.** The four drifters are `Premium Bleisure` **1.49%** ·
`Pilgrimage` 0.20% · `MICE` 0.13% · `Mabuhay Loyalist` 0.03% — and **Premium Bleisure is the
seventh-largest of the twelve, bigger than the other three drifters combined.** So "the four that drift are
1.9% of the book" is safe; "the drift is in the tiny segments" is not — that is the *v1* shape of the
sentence surviving into v2 for the second time (the first was "the three smallest segments", corrected
19 Aug).
*Generalises: when two counts of the same thing are both correct, the document has to say which denominator
it is using. A reader who spots the mismatch cannot tell "principled choice" from "arithmetic error" — and
will assume the second.*
**Source:** our analysis, 2026-08-20 — `outputs/validate_temporal/profile_drift.csv`,
`src/validate_construct.py` (`segs = [... if s != "Unassigned"]`), `outputs/validate_construct/pairs.csv`
(55 rows).

#### 2026-08-20 — The validation slide was titled after one of its four rows; it is now titled after what it is
**Domain:** Project Decision
Slide 21 was titled *"44 of 55 boundaries hold on evidence the rules never saw"* — a good sentence about
**V1 only**, while three of the four rows sat outside it. Worse, the slide never said what it *is*.
`methodology.md` defines three routes to validation — **circular** (agreement against `proxy_segment`, which
the rules produced), **Plan A** (~1,000 SME labels, outstanding), **Plan B** (no labels needed) — and
**slide 21 is Plan B**. Its subject is not "our segments are good" but *"we wrote the labels ourselves and
have no answer key yet, so here are four checks that need none."* Retitled **"Four independent checks, and
44 of 55 boundaries hold"** with a kicker: *"V1–V4, our four validation stages — construct · criterion ·
detection power · out-of-time. None may read a field the rules consumed."* Keeps the deck's house style (an
assertive title carrying a number) while making the subject and the framework legible.
**Also written down because it was only ever tacit: "V" is a validation stage, and the ladder is borrowed.**
V1 **construct** validity and V2 **criterion** validity are the standard validity types from classical
measurement theory; V3 is statistical **power**; V4 is **reliability across time**. So "why these four?" has
a real answer — a recognised framework adapted to the problem, not four checks invented ad hoc — and that
answer is worth more to an academic panel than any single number on the slide. It now leads the speaker
notes, and `defense-study-guide.md` §6.2 opens with it.
*Generalises: title a slide after its subject, not after its best row. If three quarters of the content sits
outside the title, the title is a caption that got promoted.*
**Source:** our analysis, 2026-08-20 — `docs/methodology.md` §"The validation ladder" vs
`assets/final-defense/CPT3_DefenseDeck_V3.pptx` slide 21.

#### 2026-08-20 — The validation slide now defines its own units, and a v1 drift count was corrected on the deck
**Domain:** Project Decision
Deck slide 21 carried four numbers in AUC (0.861 · ~0.60 · 0.50 coin flip · the 55-pair chart) and **never
defined AUC**. The chart annotates "coin flip" at 0.50 and "clearly distinct →" at 0.75, which hints at the
scale without stating it, so a non-technical panellist could follow the shape of the argument but not the
units. Added a full-width **explainer strip** between the V1–V4 scorecard and the weak-spot banner: one line
defining AUC operationally ("hand the model one booking from each of two segments and ask which is which;
AUC is how often it gets the order right"), the two thresholds, and — the part that earns its space —
**a statement that these are the per-pair *adaptive* anchors, and why fields are withheld per pair.**
**That discharges a rehearsal guardrail by printing it.** "Say which V1 measure you are quoting" was a note
Josh had to remember; it is now on the slide, and it also makes slide 13's circularity contract visible
doing work rather than merely asserted. Room was found without touching the argument: the four V-rows
tightened from a 0.93 in pitch to 0.82 (their 0.90 in bodies held ~0.34 in of text), and the chart shrank
from 4.35×3.43 to 3.63×2.86 in with the 1089×858 aspect preserved.
**Corrected in the same pass:** V4's line read *"drift sits in the three smallest segments"* — the **v1**
count. Under v2 **four** labels drift (`Mabuhay Loyalist` is_group 0.03% · `Pilgrimage` value_tier 0.2% ·
`MICE` peak_month 0.13% · `Premium Bleisure` log_rev **1.49%**, which is *not* among the smallest). Now
reads "8 of 12 labels stable, carrying 98.1% of bookings; the four that drift are 1.9% of the book between
them" — accurate, and the stronger framing because it leads with what held.
*Generalises: a slide that quotes a metric should define it on the slide. It costs two lines, it serves the
half of the room that will not ask, and it converts a spoken guardrail into a printed one — which is the
only kind that survives a nervous delivery.*
**Source:** our analysis, 2026-08-20 — `assets/final-defense/CPT3_DefenseDeck_V3.pptx` slide 21 against
`outputs/validate_construct/summary.md` §0/§2 and `outputs/validate_temporal/summary.md` §4.

---

#### 2026-08-19 — The sub-segment slide became one Sankey instead of five text columns, and rendering it caught two defects
**Domain:** Project Decision
The first version of deck slide 19 was a five-column text grid — all 20 sub-types, every number visible,
and unreadable from the back of a room. Redesigned as **one worked example drawn as a Sankey**
(`src/sankey_subsegment.py`, new), with the other four parents compressed to a single line of ranges.
**`Balikbayan/VFR` is the right example:** 12.5% of bookings against 28.4% of revenue, recommendation 1 tells
PAL to protect it, and every one of its sub-types is a round trip — so the only axis that varies is booking
horizon, which makes the story one-dimensional and sayable.
**The encoding does the arguing.** Ribbon width is share of the parent; fill and vertical position are median
revenue on a **single-hue sequential ramp** (the sanctioned encoding for an ordinal magnitude). Ordering the
targets by the same value the colour encodes makes the inversion instant: **the thinnest flow (16.9%) earns
the most ($995) and the fattest (38.8%) the least ($311)**. That is slide 17's volume-versus-value asymmetry
repeating *inside* a single segment — the same shape one level down, which is worth saying out loud.
**Two defects that only showed up on looking at the render, not on reading the code.** ① Three-line labels
**collided** on the two thin flows, because the label stack was taller than the ribbon it annotated — fixed by
cutting to two lines and pushing label mids apart with a minimum-separation pass plus leader lines, so
layout is correct at any flow thickness. ② With source and target columns the same height the ribbons ran
**parallel**, reading as a stacked bar rather than a flow — fixed by giving the targets 74% of the source's
span so every ribbon visibly tapers. *Neither was visible in the code; both were obvious in the image.*
**Refined 19 Aug (same day): the PNG is now the diagram only, with every label an editable PowerPoint text
box.** Text baked into a figure cannot be reworded, restyled or reflowed in the deck, which is a real cost
for a slide that will be rehearsed against. The split works because the figure is drawn with
`add_axes((0,0,1,1))` and saved **without** `bbox_inches="tight"`, so axes fractions map linearly onto the
picture's placement — `slide_y = picture_top + (1 - anchor_y) * picture_height`. The script emits a sibling
`.json` with each flow's anchor, colour and numbers, and the slide builder reads it, so realignment is
automatic if the parent or the taxonomy changes. **The geometry constant that matters is `TGT_FRAC`:** taper
and label spacing pull against each other — at 0.88 the ribbons ran parallel again, at 0.62 the label rows
came within 0.12 in of each other. 0.75 with a 0.045 gap gives visible taper *and* 0.458 in of clearance for
a two-line label, which is the balance. A first pass also left the label *frames* overlapping by 0.10 in even
though the text did not, which would have made the wrong box selectable in PowerPoint; heights cut to 0.40 in.
**Also settled: the figure parses `outputs/sub_segments/summary.md` rather than re-fitting the LCA.**
Re-fitting would cost five StepMix sweeps and, worse, create a second set of sub-type numbers that could
disagree with the report the docs already quote. Ramp validated for lightness monotonicity in OKLab
(0.884 · 0.757 · 0.560 · 0.392, even gaps); the categorical checks do not apply to a sequential ramp, and
the sub-3:1 steps are relieved by labelling every flow in ink outside the fill.
*Generalises: always render the chart and look at it. Label collisions and geometry are invisible in source
and unmissable in the image — and a diagram whose two node columns are the same height is not a flow chart,
it is a stacked bar with extra steps. Second lesson: for a figure going into a deck, ship the **marks** as an
image and the **words** as native text. Emitting the geometry alongside the image is what makes that cheap,
and the price is one rule — no tight bounding box, or the coordinate mapping silently breaks.*
**Source:** our analysis, 2026-08-19 — `src/sankey_subsegment.py`,
`outputs/segment_charts/fig_s07_sankey_balikbayan_vfr.png`, deck slide 19.

#### 2026-08-19 — Only one segment is purely domestic, and `Unassigned` is exactly "domestic premium-cabin travel with no branch"
**Domain:** Data & Features
Measured the domestic/international mix of all twelve labels to answer whether `Leisure` is the domestic
segment. **It is — 100.0% domestic by construction** (`is_domestic AND NOT any_premium`, and `is_domestic`
is `bool_and(dom_coupon)`), and it is the **only** purely domestic label. Four are purely international
(`Balikbayan/VFR`, `Outbound International Leisure`, `Premium Bleisure`, `Intl. Student`); the rest are
mixed, because their branches turn on channel, fare or stay length rather than geography — `Corporate` is
the most mixed at **57.2% domestic / 42.8% international**, which fits business travel happening at both
scales.
**Two mechanisms fall out, both previously undocumented.**
① **`OFW/Migrant` is 9.6% domestic, and 100.0% of those 375,888 bookings are sea crew.** The `sea_crew`
branch fires before any geography test, so a seafarer flying Manila–Cebu is OFW/Migrant. Correct by
design — the channel identifies them definitively — but it means "OFW/Migrant" is not a synonym for
"international", and any domestic-only cut of the book still contains a sea-crew population.
② **`Unassigned`'s domestic subset is *identical* to its premium-cabin subset — both exactly 94.5%.** That
is forced: `is_domestic AND NOT any_premium` routes every other domestic booking to `Leisure`, so a domestic
booking can only reach `Unassigned` if it has a J/W cabin leg. And no premium branch can catch it —
`Premium Bleisure` requires `is_international`, `Ultra Wealthy Leisure` requires a long-stay advance round
trip. **So the 2.47% residual is "domestic premium-cabin travel that the waterfall has no branch for",
plus a 5.5% sliver of foreign-issued international economy on premium *fare brands*.**
**This refines the 2026-08-18 entry below**, which read the premium skew as the signature of award
redemptions, upgrades and staff tickets. A simpler explanation fits: **domestic business and premium economy
is premium by brand and cheap by price**, which explains the 81.4% Premium value band and the $177 mean
revenue at once, with no need to posit awards. It also names the missing branch precisely — whatever rule
finally claims `Unassigned` should be a *domestic premium* rule, not a low-value sweep-up.
*Generalises: in a first-match-wins waterfall, the residual bucket is fully determined by what the
catch-all branch excludes. Read the residual as the algebraic complement of the last rule, not as a
mystery — it is usually one missing branch wearing a vague name.*
**Source:** our analysis, 2026-08-19 — DuckDB probes over `data/interim/pal_features_booking.parquet`
against the waterfall CASE block in `src/features_real.py`.

#### 2026-08-19 — The deck had no slide for ML's own output; added one, and the sub-segment k is the same ceiling artefact as the top level
**Domain:** Project Decision
The refinement layer — ML's job 1 in our own architecture diagram — was **mentioned on deck slides 8, 10 and
12 and shown nowhere**. For an ML capstone whose thesis is "rules label, ML checks and refines", the one
thing ML produces had no slide. Added at **position 19** (after the behaviour charts, before "what
changed"), five columns from `outputs/sub_segments/summary.md`: LCA inside the five largest v2 parents,
**four sub-types each = 20 cells**, 40,000 bookings per parent, hash-ordered. Deck is now **26 slides**.
**The finding worth presenting is the grammar, not the twenty names.** Every parent splits on the same three
axes — **direction × timing × fare tier** — recovered per parent, unprompted. That is corroboration rather
than repetition, because each fit saw only one segment.
**And the commercial point is the value spread *inside* a single segment:** Balikbayan/VFR runs **$311** at
26 days out to **$995** at 66 days — **3.2× on booking horizon alone**; Corporate spans **$112 → $656** with
*every* sub-type short-lead, so there the spread is direction and fare rather than timing. OFW (1.7×) and
Outbound International Leisure (1.2×) are nearly flat — **a negative result that is directly useful: those
two segments do not need sub-segment pricing.**
**⚠️ Caught before it reached the slide: `sub_segment.py` has `K_RANGE = range(2, 5)`, so four is the TOP of
the search range and BIC preferred the maximum in all five parents.** The draft footer said "sub-type count
chosen by BIC", which would have presented a search boundary as a discovery — the identical error to reading
`k=9` on the PCA figure as a fitted optimum. Corrected to "four is the most the search offered, and BIC
wanted all four in every parent — the continuum again, one level down". **That is a real finding in its own
right: there is no natural number of types inside a segment either, so the continuum is the same shape at
both levels, and 20 cells is a granularity choice we own rather than a structure we found.**
*Generalises: whenever a model reports the maximum of its own search range, that is a boundary, not a
result — check the range before writing the caption. We have now hit this twice in one deck (k=9 at the top
level, k=4 per parent), which means it is a habit of the tooling, not an accident.*
**Source:** our analysis, 2026-08-19 — `outputs/sub_segments/summary.md` (18 Aug, v2 parents) ·
`src/sub_segment.py` `K_RANGE`/`SAMPLE` · deck slide 19 built via python-pptx from the slide-13 template.

#### 2026-08-19 — Slide 22 now owns five limits, and the limitations inventory is reconciled across four documents
**Domain:** Project Decision
The limitations material was spread over four places with no single owner, and the counts disagreed:
`defense-slides-outline.md` §6 specified **five** own-it bullets, `defense-brief-2026-08-18.md` listed five
in prose, the study guide's slide row said "five limits", and the **built slide showed four** — it had split
"no loyalty field / no ancillary revenue" into two bullets and dropped both "labels add little incremental
prediction" and the V4 multi-seed item. Across the whole paper trail there are **nine** candidate
limitations; the deck now carries five owned plus four in-flight.
**Added to the deck today:** the V4 multi-seed item (in-flight column) and **"Segment labels add little
incremental prediction — by design, not by failure"** (owned column, fifth bullet at T=5.80, one line,
0.15 in clearance above the footer). The second one matters most: `defense-study-guide.md` §7.1 lists
*"Your segments add almost nothing predictive"* as **the single most likely question of the defence**, so it
was rehearsed as a reply while the slide whose thesis is "owned, not hidden" left it out.
**Measured the claim before writing it down** (`outputs/validate_criterion/summary.md`): the label alone
scores **0.598** on `flown_any` and **0.604** on `rebook_180d` against a 0.50 coin flip, but on top of the
11 raw features it buys only **+0.0005 to +0.0024** AUC. Two stable outcomes agreeing at ~0.60 makes the
"real signal, no incremental signal" framing robust rather than cherry-picked. `refund_any` is flagged
`unstable` (347 events, reads −0.107) and must not be quoted — already in the never-say table.
**New doc:** `defense-study-guide.md` **§6.1 "Slide 22 in full"** — the first per-slide section for the
defence deck, in the shape the EDA-results guide uses (on the slide / say / watch for / if pressed), with an
evidence-source table mapping each limit to the output that produced it. Written because the only document
with per-slide guidance, `eda-results-slide-guide.md`, covers a **different 13-slide EDA deck** and stops at
its own slide 13 — so defence slides had one table row each and nothing more.
**Also noted, not fixed:** the slide's closing line claims *"Everything on this slide is also written down in
the handover pack"* and **no artefact by that name exists in the repo**. It may live outside git; §6.1 flags
it as the one sentence on the slide a panellist can ask to see.
*Generalises: when a claim lives in four documents and none of them owns it, the counts will drift — and the
build artefact is the one that silently wins. Give every recurring list one home and derive the rest.*
**Source:** our analysis, 2026-08-19 — `assets/final-defense/CPT3_DefenseDeck_V3.pptx` slide 22 vs
`docs/defense-slides-outline.md` §6, `docs/defense-brief-2026-08-18.md`, `docs/pipeline-study-guide.md` §7.4;
numbers from `outputs/validate_criterion/summary.md`.

#### 2026-08-19 — Pre-defence consistency pass executed: two artefacts regenerated, two slides corrected
**Domain:** Project Decision
Acted on the audit rather than only recording it. **① `validate_temporal.py --report-only`** rebuilt
`summary.md` from the saved (correct) CSVs, so the new majority-of-panel logic took effect without
re-running the analysis — no number could shift. §5 now reads *"The panel disagrees on whether a year-old
model still carves the data… `GMM(full)` 1.24 · `LCA` 0.89 — 1 of 2 at or above 0.95"* and instructs that no
refit-cadence claim be made until the stage runs across several seeds. **The `--report-only` flag is the
reusable lesson**: a script that can regenerate its prose from its own saved outputs lets a reporting fix
ship without re-opening the computation. **② `monitor_real.py` re-run** (full, ~1 min): the withdrawn LCA
1.13 is gone from the shipped drift report, replaced by the method-disagreement statement. Segment-mix PSI
0.0028 STABLE, unchanged. **③ Deck slide 13**: "six 'cannot-be' SME rules" → "six **hard** SME rules"
(H11 is a `must_be`). **④ Deck slide 22**: added a fourth in-flight item, *"No refit-cadence claim yet: V4
transfer needs a multi-seed spread."* — the limit `defense-slides-outline.md` §6 had specified and the built
slide had dropped. Backup at `CPT3_DefenseDeck_V3.backup-before-text-fixes.pptx`; edits made at **run level**
via python-pptx so character formatting survived, new shapes **deep-copied** from their siblings with fresh
unique `cNvPr` ids (duplicate ids are what triggers PowerPoint's repair prompt), positioned on the column's
existing 1.00-inch rhythm at T=5.72 with 0.23 in of clearance above the footer. Verified: 25 slides, zip
intact, speaker notes preserved on both slides.
**One thing left deliberately undone.** The monitor's single `RETRAIN` flag is `channel` at PSI 0.4111 —
but `psi_excl_new` is **0.0285 (STABLE)** and the new category is **NDC**, the channel PAL switched on
mid-window. The report prints both verdicts side by side, so the design is right, but **no prose sentence
explains that the alarm is a new category rather than drift** — a reader of a shipped artefact could act on
"RETRAIN". Adding that sentence is a generator change outside the approved scope; recorded here as the next
small fix.
*Generalises: give every report generator a `--report-only` path. Most "the numbers are stale" incidents are
really "the prose is stale", and the two deserve different costs to fix.*
**Source:** our analysis, 2026-08-19 — `outputs/validate_temporal/summary.md` §5 ·
`outputs/monitor_real/summary.md` · `assets/final-defense/CPT3_DefenseDeck_V3.pptx` slides 13 and 22.

#### 2026-08-19 — V4's findings audited for closure: the two we only wrote down are the two that caused the retraction
**Domain:** Clustering / Methodology
Went back through every V4 finding and asked whether it was *addressed* or merely *recorded*.
**Properly closed (2).** ① The **departure-filter censoring trap** is designed around, not annotated:
`validate_temporal.py` places both windows strictly inside the region where no lead time up to the 365-day
clip is censored, each spanning twelve calendar months, excludes outcome fields near the extract boundary
from every comparison, and publishes `censoring.csv` so the exclusion is visible. ② The **~43% sampling
bug** is fixed at source — `model_zoo.load_sample` wraps the filter in a subquery so the sample sits above
it, and the docstring carries the measurement (2,077 of 40,000 on a `Corporate` filter; ~13,000 of 30,000
on V4's windows) plus "verify with `EXPLAIN` before changing this". A fix the next person cannot undo by
accident.
**Closed as reporting discipline only (1).** ③ "**Revenue mix is the weaker leg**" (3.36 pp vs 1.71 pp;
Balikbayan/VFR 29.35% → 26.64% of revenue on flat headcount) lives in the report's own conclusions and in
the guides, but it is **not on the limitations slide** — arguably the most actionable limit PAL has, since
revenue share is the number the commercial team acts on.
**Not closed (2) — and they are precisely the pair that produced the withdrawn 1.13.** ④ The
**max-over-panel selection effect was still in the code**: `validate_temporal.py` ranked the transfer table
and reported `.iloc[0]` as "Best drift-adjusted transfer is X". That is the mechanism by which July
published 1.13 on LCA and the 18 Aug re-run silently switched the headline to GMM with nobody choosing —
the lesson was written into five documents while the script kept doing the thing. **Fixed today:** the
stage now prints every method's ratio, counts how many clear 0.95, and only claims transfer holds when a
**majority of the panel** agrees — V3's own documented majority-rule convention applied to V4 rather than a
new rule invented. On current numbers it emits *"The panel disagrees… `GMM(full)` 1.24 · `LCA` 0.89 — 1 of
2 at or above 0.95."* ⑤ The **multi-seed spread is still not implemented** — the transfer stage runs one
seed and reports point estimates with no interval, which is exactly what let a 1.13 look like a finding.
Also worth noting the transfer "panel" is only **two** methods, so a 1–1 split is thin by construction;
widening the panel would buy more than another seed.
**Deck gap found in the same pass:** `defense-slides-outline.md` §6 lists **five** own-it limits and
`defense-study-guide.md`'s slide row says "the five limits", but the built slide shows **four** — it split
"no loyalty field / no ancillary revenue" into two bullets and dropped both "labels add little incremental
prediction" and "**V4 transfer needs a multi-seed spread**". The outline told the deck to flag it; the deck
does not.
*Generalises: a lesson is closed when the generator changes, not when the doc does. Audit findings by asking
"what would happen on the next run?" — if the answer is "the same wrong thing, more politely documented",
it is open.*
**Source:** our analysis, 2026-08-19 — `src/validate_temporal.py` (transfer verdict block),
`src/model_zoo.py::load_sample`, `outputs/validate_temporal/`, deck slide 22 via python-pptx vs
`docs/defense-slides-outline.md` §6.

#### 2026-08-19 — A withdrawn number was hard-coded in the drift monitor, so every run republished it
**Domain:** Project Decision
Worst instance of the V4 staleness sweep, and the only one a document fix could not have held:
`src/monitor_real.py` hard-coded "**LCA transfer ARI 0.729 vs a 0.645 within-window ceiling**" in **three
places** — the module docstring, the `cross_window_ari_note` field of `report.json`, and the generated
`summary.md` prose — and it had already emitted it to `outputs/monitor_real/summary.md`. That pair is
**formally withdrawn** (silent ~43% sample; the correct run gives LCA 0.648/0.726 = **0.89**, GMM(full)
0.740/0.595 = **1.24**), and the monitor is a *shipped* stage-5 artefact that goes to PAL, so every
scheduled run was republishing a retracted figure into a deliverable. Replaced all three with the
method-disagreement statement. **`outputs/monitor_real/summary.md` still holds the old line until the
script is re-run** — `outputs/` is git-ignored and generated, so it was left alone rather than hand-patched.
*Generalises: withdrawing a number means grepping `src/`, not just `docs/`. A figure quoted inside a
generator is not a stale sentence — it is a stale sentence with a schedule. And when a retraction lands,
the search should cover every place the number could be **re-emitted**, in priority order: generators
first, then deliverables, then prose.*
**Source:** our analysis, 2026-08-19 — `src/monitor_real.py` lines 18 / 240 / 277 vs
`outputs/validate_temporal/summary.md` §6.

#### 2026-08-19 — The V4 numbers in the study guides were a generation behind, and one of them was a withdrawn claim
**Domain:** Clustering / Methodology
Auditing the deck's eleven-iteration ledger row by row against the scripts and their outputs. **All eleven
rows check out** — every row maps to a script in `src/` with a report in `outputs/`, so the slide's "the
trail is re-runnable, not remembered" is literally true. **The stale material was in the study guides, not
the deck.** `outputs/validate_temporal/summary.md` (18 Aug re-run) reports **share TVD 1.71 pp · revenue TVD
3.36 pp**, and transfer as **GMM(full) 0.74/0.595 = ratio 1.24** against **LCA 0.648/0.726 = 0.89**. The
guides still carried the 29 Jul generation — **1.93 pp / 3.21 pp** — and `pipeline-study-guide.md` still
asserted "**a model fitted a year earlier transfers for free**" with "**0.763 against a 0.746 ceiling — a
year costs us nothing**", which is the *pre-fix* pair; the LCA version of that claim (0.729 / 0.645 /
**ratio 1.13**) is **withdrawn** outright, computed on a silent 43% sample. Also stale: "7 of 10 segments
carrying 98.2%" is the v1-taxonomy profile-drift line; current is **8 of 12 labels carrying 98.1%**.
**The deck is clean** — a full-text scan of all 25 slides and their notes finds none of the withdrawn or
superseded numbers (0.729 · 1.13 · 1.93 · 3.21 · 0.114 · "transfers for free" all absent), and
`defense-brief-2026-08-18.md` and `defense-study-guide.md` both already marked the 1.13 ratio withdrawn.
Refreshed the figures in `pipeline-study-guide.md` (11 sites), `defense-study-guide.md` (4),
`methodology.md`, `eda-results-slide-guide.md` and `recommendations-plan.md`, and replaced every flat
"transfers for free" with the named-method version.
**Two more ledger-integrity notes.** (1) **The deck's eleven and the study guide's eleven are different
elevens:** the deck drops the 31 Jul persona row and adds the 17–18 Aug SME/waterfall-v2 row. Both count to
eleven by coincidence. Added the 17–18 Aug row to the guide's table with a note on the difference — a slide
that says "eleven dated iterations" should not be backed by a table listing a different eleven. (2) **The
12 Aug rule-confidence row (66.5% uncontested, Corporate most contested) was computed on v1 labels and has
not been re-run since waterfall v2**, so the contested share is unknown for the taxonomy actually being
defended. Marked as such in the ledger; the deck's version of the row quotes no number, so it is safe.
*Generalises: a figure has a generation, not just a value. When a script is re-run, grep every doc for the
old value the same day — and when a number is withdrawn, grep for the *sentence* it supported too, because
the prose outlives the digits.*
**Source:** our analysis, 2026-08-19 — `outputs/validate_temporal/summary.md` (18 Aug 21:10) vs the guides;
full-text scan of `assets/final-defense/CPT3_DefenseDeck_V3.pptx` via python-pptx; `src/` ↔ `outputs/`
row-by-row mapping of the eleven ledger entries.

#### 2026-08-19 — The methodology spec still said the v2 waterfall was unbuilt, three weeks after it shipped
**Domain:** Project Decision
Auditing the defence deck's methodology block (slides 10–13) against the repo turned up the spec, not the
deck, as the stale artefact. `docs/methodology.md` was at v1.10 and its changelog asserted "**the waterfall
is unbuilt and proxy labels are unmoved**", while its "Current Methodology at a Glance" pipeline line read
"**PRIMARY DELIVERABLE (the 10 segments)**". Both are false as of 18 Aug: `src/features_real.py` emits the
v2 `proxy_segment`, verified live on the booking parquet — **12 labels = 11 segments + `Unassigned`**,
`Unassigned` **9.58% → 2.47%**, `Leisure` **50.61%**, and **62.69% of bookings carry a different label than
under v1** (mostly the `Budget/Adventure` → `Leisure` rename; genuine reclassification 23.4%). Bumped to
v1.11 with the shipped distribution recorded, the at-a-glance line corrected, and the v1 ten-segment
penalty-weight table explicitly scoped as prototype-track. **The deck was right and the spec was wrong** —
worth noting because the reflex is to trust the doc over the slide.
**Two smaller reconciliations from the same audit.** (1) **"Six 'cannot-be' SME rules" is five plus one:**
`status=enforce` in `hard_constraints.csv` selects H08 · H10 · H11 · H12 · H14 · H15, of which **H11 is a
`must_be` — the only one in the whole sheet**. The count of six is right, the label "cannot-be" is not, and
two of the six (H14, H15) only became enforceable when PAL approved Ultra Wealthy Leisure and Intl. Student
on 17 Aug, so six is itself a v2-era number. (2) **`pipeline-study-guide.md` still listed "H₀ persistent
homology — 1 significant component" as one of six pieces of continuum evidence, with no caveat**, even
though that statistic was retired for returning 2–131 on unchanged control data — and slide 13 of the deck
*boasts about retiring it*. Caveat added. The two H0 runs also differ (29 Jul: median 1, p75 3, max 120;
18 Aug re-run at k=11: median 2, p75 4, max 131); the deck quotes the 18 Aug pair, and `methodology.md` now
cross-references both so the numbers cannot be read as a contradiction.
*Generalises: when a deck and a spec disagree, the deck is often the fresher document — it gets rebuilt for
an audience, the spec gets updated when someone remembers. And a boast about retiring a bad instrument is
only safe if every document has stopped quoting it.*
**Source:** our analysis, 2026-08-19 — `assets/final-defense/CPT3_DefenseDeck_V3.pptx` slides 10–13 read via
python-pptx, against `src/features_real.py`, `src/pal_colors.py`, `data/constraints/hard_constraints.csv`
and DuckDB probes over `data/interim/pal_features_booking.parquet`.

#### 2026-08-19 — The PCA overlap figure is v1-era artwork, but the finding replicates on v2 — and the v2 ARI is *higher*
**Domain:** Clustering / Methodology
`reports/study_guide/clust_02_pca.png` and `clust_01_bic_ari.png` were generated **23 July**, before the
18 August v2 taxonomy. The PCA legend therefore shows **Budget/Adventure** (renamed Leisure), **Family**
(dropped) and **Last-Minute** (now a flag) — three names the defence deck's own taxonomy slide declares
retired. Re-ran the same LCA sweep on the current parquet and v2 labels (60k, seed 42, `n_init=2`):

| k | BIC | ARI vs v1 | ARI vs v2 |
|---|---|---|---|
| 3 | 1,014,017 | 0.243 | 0.306 |
| 4 | 988,748 | **0.319** | **0.389** |
| 6 | 952,209 | 0.280 | 0.269 |
| 9 | 928,770 | 0.226 | 0.210 |

**BIC still falls monotonically — "no natural k" holds.** Best agreement moves **0.319 (v1) → 0.389 (v2)**,
i.e. the redesigned taxonomy agrees *more* with what an unsupervised method finds, while staying inside the
"moderate" band. A regenerated figure must annotate **≤ 0.39**, not ≤ 0.34 — and 0.389 sits right at the
0.4 edge of the shaded band, so the sentence "only moderate agreement" needs care rather than deletion.
Regenerating is therefore **safe and mildly favourable**, but it does not fix the deck by itself: the PNG is
embedded in `CPT3_DefenseDeck_V3.pptx` and must be re-inserted.
**Three reading traps in the same figure, now documented:** (1) **`k* = argmin(BIC)` over `range(3,10)`,
and BIC is monotone — so k\* is always 9, the top of the search range**, not a fitted optimum; it
coincidentally equals the v1 segment count on the right panel and must not be read as a 9-to-9 pairing.
(2) The suptitle said **"stratified sample"** but `USING SAMPLE ... (reservoir)` is **uniform** — fixed in
`src/report_figures.py`; uniform is also the correct choice, since balancing by segment or region equalises
group sizes and can manufacture structure. (3) Two greys collide in the right panel (slate = Last-Minute,
dark grey = Unassigned, unlabelled by design).
**Quantities that make the visual defensible:** PC 1 + PC 2 carry **57.7%** of variance in the 16-column
matrix (4 dims → 81%), so it is a substantial projection, not a thin shadow; rule-segment **silhouette
0.091** in the full feature space versus **−0.16** in the 2-D view — the picture *overstates* the overlap,
so quote 0.091. (Euclidean on the standardised/one-hot matrix; not comparable to the 0.381 Gower ceiling
from the ten-method sweep, which uses a different distance.)
*Generalises: a figure whose labels come from a taxonomy is dated the moment the taxonomy changes. Before a
defence, diff every embedded figure's legend against the current label set — and re-verify the claim on
current data separately, because stale artwork and a stale finding are different problems with different
fixes.*
**Source:** our analysis, 2026-08-19 — re-ran `src/report_figures.py`'s LCA/PCA construction over
`data/interim/pal_features_booking.parquet`; PNG mtimes vs `src/pal_colors.py` retired-segment block.

#### 2026-08-19 — "74% of customers never return" is a right-censoring artifact; the honest figure needs a horizon
**Domain:** Data & Features
The 26.1% repeat rate (73.9% single-booking) pools customers who had **27 months** of observation window
with customers who had **weeks**. Issuance runs 2024-04 → 2026-07-20 at full volume (earlier issuance
appears only for very-long-lead travel into the window, so the extract is **left-truncated too**: a
"first" booking is first-*observed*, not first-ever). Repeat rate by first-booking cohort falls almost
perfectly with remaining runway: **2024 Q2 40.5% · 2025 Q1 27.0% · 2026 Q1 12.6% · 2026 Q3 2.9%.**
On a fixed horizon it is **26.5% within 12 months** of the first booking (8.11M customers with a full
year of runway) and 17.8% within 6 months. So the pooled 26.1% happens to land near a proper 12-month
rate — but by coincidence of cohort mix, not because that is what it measures. **Say "26% within a year",
never "74% never return".** Supersedes the phrasing in the 2026-06 plan-review entry below ("for 74%,
customer ≡ their one booking") — the *conclusion* stands untouched: booking grain was chosen because
purpose belongs to a purchase, and even at 40% repeat most of the base books once. Nothing downstream
reads the repeat rate, so no model changes; the fix is wording, in
`eda-results-slide-guide.md`, `pipeline-study-guide.md`, `defense-study-guide.md`, `eda-report-real-data.md`.
**Same defect, second number: "avg tenure 82 days" (A5) averages over all 13.4M customers, and the 73.9%
with one booking contribute a structural zero.** Among customers who did return, first→last issuance spans
a **median 285 / mean 314 days** — roughly a year, not a quarter. 82 days is arithmetically right and
rhetorically indefensible; it invites "so nobody stays with PAL for three months?"
*Generalises: any "share who never came back" computed on a fixed extract is a statement about the window,
not the customer. Cohort it by entry date before quoting it, or attach an explicit horizon. And never
average a duration over a population where most members cannot have one.*
**Source:** our analysis, 2026-08-19 — DuckDB cohort probes over `data/interim/pal_features_booking.parquet`.

#### 2026-08-19 — The region chart's multi-region trips are labelled alphabetically, and it costs 1.65% of the book
**Domain:** Data & Features
`dest_region = max(intl_region)` in `src/features_real.py` is an **alphabetical** max, not a
furthest-point or primary-destination rule. Region labels sort *East Asia < Europe < Middle East < North
America < Oceania < South Asia < Southeast Asia*, so **Southeast Asia wins every tie**. **785,673 bookings
(3.43%) touch more than one international region**; for **377,331 (1.65% of all bookings)** the assigned
region is not the region of their final destination — mostly trips that really end in East Asia (132,936),
North America (76,802) or Oceania (55,194) being filed under Southeast Asia. Reassigning by final trip
destination: **SE Asia 11.78% → 10.56%**, **East Asia 14.80% → 15.67%**, North America 8.38% → 8.60%,
Oceania 3.32% → 3.41%; **domestic 57.69% is unaffected** (`is_domestic` is `bool_and(dom_coupon)`, exact)
and the bar ordering does not change. Two related facts worth having ready: **7.63% of bookings are
international journeys carrying a domestic feeder leg** (the domestic network partly *feeds* the
international one — they are not separate businesses), and the **Europe/South Asia 0% bars mean no
own-metal sectors**, while **6,334 bookings do have a European trip endpoint** (1,740 South Asian) through
OAL codeshare beyond-points. Not worth re-running the pipeline for 1.65%, but it must be **quoted as a
known edge** rather than discovered by a panellist.
*Generalises: any `max()`/`min()` over a categorical is an alphabetical tiebreak pretending to be a
business rule. Where a booking can hold several category values, the aggregation choice is a modelling
decision and needs stating.*
**Source:** our analysis, 2026-08-19 — DuckDB probes over `data/interim/pal_clean/` joined to
`data/reference/airport_region.csv`; generator `src/report_figures.py::fig_route_region`.

#### 2026-08-19 — The EDA timing slide was quoting coupon-grain numbers against a booking-grain chart
**Domain:** Data & Features
`eda_03_lead_value.png` is drawn from `pal_features_booking.parquet` (22.9M **bookings**), but every
talking-point doc paired it with **median 25 days / 13.3% inside three days** — which are the **coupon**-grain
figures from the 38.1M-row extract. At the booking grain the same distribution is **median 18 days, mean 43.3,
19.26% inside three days**. The direction is structural, not a bug: **coupon-weighting over-counts multi-leg
trips, and multi-leg trips are planned further ahead**, so any coupon-grain lead time reads as more
advance-booked than the purchase decisions we actually model. 19.26% is also the number the rest of the deck
already uses — it is exactly the **4,411,666** bookings `is_last_minute` covers — so the slide was
contradicting slide 18 by 6 points. Corrected in `eda-results-slide-guide.md`, `pipeline-study-guide.md`,
`mentor-presentation-guide.md`, and labelled by grain in `eda-report-real-data.md`.
**Second grain trap on the same chart, right-hand panel:** the bars are `max_tier` — each booking counted at
its **most expensive** leg — giving **63.11%** in the two cheapest brands (identical to `value_band` = Budget,
by construction). The **70.6%** figure circulating from the Stage-E proxy sizing is `min_tier <= 2`, i.e.
bookings with *any* cheap leg (70.68% confirmed). Both are true; they answer different questions. `max_tier`
is the conservative one and is the only one that may be quoted against this figure.
*Generalises: a distribution shown at one grain must be described at that grain. When two grains of the same
extract are both in a deck, every percentage needs its denominator named, or two slides will disagree with
each other in front of a panel.*
**Source:** our analysis, 2026-08-19 — DuckDB probes over `data/interim/pal_features_booking.parquet` and
`data/interim/pal_clean/`; generator `src/report_figures.py::fig_lead_and_value`.

#### 2026-08-18 — V3 re-run against v2: the detection floor holds, and one instrument failed its own control
**Domain:** Clustering / Methodology
Re-ran detection power at `k=11` (v2 named-segment count; the 29 Jul run used 10). **The bounded null is
unchanged**, which is the outcome the brief predicted but had not verified. Majority of the 12
method × archetype combinations: **never detected at 0.5% or 1.0% prevalence** at any distinctness
tested; detected at **2.0% from distinctness ≈0.494**, **5.0% from ≈0.219**, **10.0% from ≈0.13**.
So: *no segment exists in these features at or above 2% of bookings with distinctness ≈0.494 or greater*,
and *below ~1% (~229k bookings) one could exist unseen*. The archetype spread is only 11 points
(late_yield 21% of cells, planned_group 29%, random_dir 32%), and the **random direction — which has no
business story — sits inside the range set by the two plausible ones**, so the floor is a property of the
method panel, not of the directions we guessed.
**⚠️ Quote the majority floor, never the best cell.** One combination recovered a group at **0.114**
planted silhouette while groups as distinct as **0.567** were missed elsewhere in the grid. Both cannot
be floors — the first is the luckiest alignment out of 12 draws, which is what chance produces at that
many. *Generalises: a minimum over a panel is a selection effect, exactly like the max-ratio problem V4
has. Report the consensus and the spread.*
**The new finding is about our own instrument.** On the `w=0` controls — nothing planted, so the answer
must be identical every time — persistent homology's H0 gap heuristic returned **median 2, p75 4,
maximum 131** significant components across 100 draws of 1,200 rows. **A statistic that ranges 2–131 on
unchanged data cannot screen for anything**, so this grid draws no conclusion from it. The instability is
the `argmax`-over-sorted-bar-differences gap heuristic, which jumps whenever two adjacent bars are close
— not the homology. **This qualifies the 28 Jul report**, which cited *one* draw ("1 significant H0
component") as independent confirmation of the continuum: 2 is the modal and median value, so the reading
survives, but as the centre of a noisy distribution rather than a measurement. The H1 loop-noise ratio and
the barcode shape are the robust parts; the integer count is not.
**Source:** our analysis, `outputs/detection_power/`, 18 Aug 2026.

---

#### 2026-08-18 — V4 re-run on the corrected sample: the transfer-ARI number in the defence brief does not reproduce
**Domain:** Clustering / Methodology
Fixing `model_zoo.load_sample`'s filter/sample ordering (entry below) doubled V4's per-window sample from
~13,000 to the intended 30,000 and re-ran it. **The model-transfer table moved enough to change what can
be claimed.**

| | earlier run (~13k/window) | corrected run (30k/window) |
|---|---|---|
| LCA transfer ARI | 0.729 | **0.648** |
| LCA within-window ceiling | 0.645 | **0.726** |
| LCA ratio | **1.13** | **0.89** |
| GMM(full) ratio | not the reported method | **1.24** (0.740 / 0.595) |

**⚠️ The brief's "LCA transfer ARI 0.729 against a within-window ceiling of 0.645 — ratio 1.13" is not
reproducible and must not be quoted.** On the correct sample LCA transfers *below* its own ceiling.
**The qualitative conclusion survives, but only through a different method:** `GMM(full)` reaches ratio
1.24, so "a model fitted a year earlier carves the later data as well as one fitted on it" still holds —
on GMM. The two methods now disagree (1.24 vs 0.89), which is materially weaker evidence than one
method at 1.13, and the honest statement is *"on the best-transferring method"*, not *"on this
evidence"*.
*Two generalisations, both cheap and both missed:*
1. **A ratio that crosses 1.0 when the sample doubles was never a finding.** At 13k the estimate was
   noise-dominated; nothing in the earlier output said so, because the script reports point estimates
   with no interval. **V4's transfer stage needs a spread across seeds before any ratio is quoted.**
2. **`summary.md` reports "best drift-adjusted transfer", i.e. the max ratio over the method panel.**
   That silently cherry-picks, and it is why the reported method changed from LCA to GMM without anyone
   choosing. Reporting the max over a panel is a selection effect; report the panel.
**Unchanged by the fix** (these run on the full population, not the sample): segment-size TVD **1.71 pp**,
revenue-mix TVD **3.36 pp**, adversarial drift AUC **0.621** against a 0.500 negative and 0.995 positive
control, and "composition is stable where the volume is" — 8 of 12 segments carrying 98.1% of bookings
show only negligible-or-small drift, with the drifters all being the smallest segments.
**Source:** our analysis, `outputs/validate_temporal/`, 18 Aug 2026.

---

#### 2026-08-18 — PAL turned on NDC: 366,890 bookings through a channel that did not exist a year ago
**Domain:** Airline Industry
First real-data drift run (`src/monitor_real.py`, Regime C) over two adjacent censoring-safe 12-month
windows. **The segment mix is essentially frozen — PSI 0.0028 — and 22 of 23 rule inputs are STABLE.**
The single flag is `channel`, **PSI 0.4111 → RETRAIN**, and the decomposition names the cause:
**`NDC` has 0 bookings in 2024-05→2025-04 and 366,890 (3.64%) in 2025-05→2026-04.** PAL stood up New
Distribution Capability inside the extract window. Alongside it, **OTA fell 18.08% → 12.93%** and
**WEB/APP rose 32.91% → 37.17%** — a genuine intermediated-to-direct shift, but a small one:
contributions 0.017 and 0.005 against NDC's 0.383.
**⚠️ The RETRAIN verdict is partly an artifact of the metric.** A category absent from the reference
window contributes `share x log(share / eps)`, where `eps = 1e-6` is `psi_categorical`'s clipping floor.
At `eps = 1e-4` the same 3.64% would contribute ~0.21 instead of 0.38. **PSI cannot distinguish "this
category is new" from "this category exploded"** — so `monitor_real.py` now reports `psi_excl_new`
alongside `psi`, and on that measure `channel` is **0.0285 — STABLE**.
*Generalises: any PSI over a categorical with an open value set needs the new-category split, or the
first time a business launches anything the monitor cries retrain.*
**Why it matters commercially:** none of this moved a label — `corp_channel` PSI is 0.0002 — so the
waterfall is unaffected. But a channel carrying 3.6% of bookings and rising is not in any rule, and
`channel` is a rule input for Corporate. Worth asking PAL whether NDC bookings should read as corporate,
direct, or neither before the share grows.
**Source:** our analysis, `outputs/monitor_real/`, 18 Aug 2026.

---

#### 2026-08-18 — Two silent staleness bugs: a per-morsel sample and a palette that still listed dropped segments
**Domain:** Clustering / Methodology
Re-pointing ML's stale stages at v2 turned up two defects that had been producing *plausible* output,
which is the dangerous kind.
**① `WHERE ... USING SAMPLE n ROWS` samples *before* it filters.** Written flat in one SELECT,
DuckDB places `RESERVOIR_SAMPLE` **underneath** `FILTER` in the plan (confirmed by `EXPLAIN`): it draws
n rows from the whole table and only then applies the predicate, so the caller receives
**`n x selectivity`** rows. `sub_segment.py` asked for 40,000 per parent and got **20,191 for Leisure
(50.6% of the book) and 2,077 for Corporate (5.1%)** — the yield tracks the segment's share exactly.
The smallest parent was therefore the thinnest-sampled, precisely where LCA needed the most support.
It is *deterministic*, which is why it never looked broken.
**The same pattern is in `model_zoo.load_sample(n, where=...)`, which most of the study scripts use.**
Blast radius: `validate_temporal` sampled two 12-month windows (~44% of the table each) and so ran on
**~13,000 rows per window, not the 30,000 it asked for** — that is the sample behind the V4 transfer
ARI quoted in the defence brief. `kproto_compare`'s per-segment pass is affected the same way.
`detection_power` and `model_stress_test` pass **no** `where` and are unaffected.
**Two different fixes, because the two call sites want different things:** `sub_segment` now uses
`ORDER BY hash(customer_id, issue_date) LIMIT n` (exact, uniform, reproducible, and it needs a precise
n per parent); `load_sample` wraps the filter in a subquery so the sample sits above it.
*Generalises: when a sample and a filter share a SELECT, read the plan. A deterministic wrong answer
is harder to catch than a crash, and "it returned rows" is not evidence it returned the right ones.*
**② `pal_colors.SEG_ORDER` was still the pre-v2 list** three weeks after v2 shipped — advertising
`Family`, `Digital Nomad` and `Last-Minute`, omitting `MICE`, `Ultra Wealthy Leisure`, `Intl. Student`
and `Outbound International Leisure`. The module's own docstring warns that "a chart legend must never
advertise a segment the model does not assign"; the module was the thing violating it. Now **derived**
(`SEG_ORDER = list(SEG_APPROVED)`) rather than restated, with `SEG_ORDER_V1` for the superseded
prototype scripts and an assert that the emitted list can never intersect `SEG_RETIRED`.
*Generalises: two hand-maintained lists that must agree will eventually not. Derive one from the other,
or assert the relationship — a comment saying "keep these in sync" is not a mechanism.*
**Also settled: Regime A is not applicable, not merely unrun.** DBCV, silhouette and cross-window ARI
score a *fitted clustering*. The deliverable is a deterministic rule waterfall — no clustering, no noise
class, no density to degrade, and re-applying the rules to the same rows scores ARI 1.0 by construction.
`monitor_real.py` states this on the page instead of leaving a blank, and points at V4's LCA transfer
ARI (0.729 vs a 0.645 ceiling) for the stability question that *does* apply.
**Source:** our analysis, `src/sub_segment.py` · `src/pal_colors.py` · `src/monitor_real.py`, 18 Aug 2026.

---

#### 2026-08-18 — The `is_last_minute` flag is not independent of the waterfall: three rules read `lead_days`
**Domain:** Clustering / Methodology
Charting the flag by segment (`src/segment_charts.py`) surfaced an entanglement we had not stated.
**`is_last_minute` is `lead_days <= 3`, and three of the eleven segment rules also read `lead_days`,
so three bars in any "short-lead by segment" chart are partly or wholly rule-induced:**
- **MICE** requires `lead_days >= 45` and **Ultra Wealthy Leisure** requires `lead_days >= 30`. Both are
  therefore **0% short-lead by construction, not by behaviour** — mutually exclusive with the flag by
  definition. A chart that shows them at 0% without saying so invites "these travellers never book late".
- **Corporate is `corp_channel OR (any_business AND lead_days <= 7)`.** The second branch only admits
  bookings that are already short-lead, so **the segment's headline 35.6% is partly circular**. Split by
  branch: `corp_channel` (791,571 bookings, **no lead-time condition**) is **23.3%**; the
  `any_business AND lead_days <= 7` branch (376,880) is **61.4%**. **23.3% is the honest number** — still
  above the 19.26% book average, so the behavioural claim survives, but at a quarter of its apparent size.
**This qualifies a sentence in the 18 Aug defence brief** — "a flag rides along with whatever segment the
booking belongs to" is true of eight segments and false of three. The volume claim is unaffected
(4,411,666 vs 2,945,686 stands); it is the per-segment *rate* reading that needs the caveat.
*Generalises: when a flag and a rule read the same feature, every cross-tab of the two is partly a
tautology. Check the rule text before reading a rate as behaviour.*
**Also note the denominator trap:** the brief's per-segment short-lead counts (864,292 OFW · 315,333
Corporate · 196,364 Balikbayan) are computed on **v1** labels — correct for its "invisible under v1"
framing. Under v2 labels the same 4,411,666 bookings split differently (858,318 · 415,411 · 193,897),
because the retired Last-Minute branch used to outrank those segments. Both are right; say which.
**Source:** our analysis, `src/segment_charts.py` + `src/features_real.py` L272–L305, 18 Aug 2026.

---

#### 2026-08-18 — `Unassigned` survived v2 as a *premium* residual, not a low-value one
**Domain:** Data & Features
Waterfall v2 cut `Unassigned` from 9.58% to 2.47% (566,126 bookings) by routing three-quarters of it to
`Outbound International Leisure`. **What is left is 81.4% Premium value band** — against 6.0% Premium
book-wide, and against 7.4% Budget within `Unassigned` itself. Only the three segments that are premium
*by definition* rank above it — Ultra Wealthy Leisure 96%, Premium Bleisure 95%, Mabuhay Loyalist 94% —
so `Unassigned` is **the most premium-skewed population in the book that was not built to be one**.
Mean revenue is nonetheless only **$177/booking**, the third *lowest* — so the
fare brand is premium while the ticket value is not, which is the signature of award redemptions,
upgrades and staff/industry tickets rather than of high-yield commercial traffic.
**Why it matters:** the standing story about `Unassigned` was "the largest actionable gap" — implicitly
low-value leftovers to be swept up. It is the opposite population, and it is 32.7% short-lead. Whatever
rule finally claims it should be designed for a premium-brand, low-revenue, late-booking traveller.
**Source:** our analysis, `outputs/segment_charts/segment_summary.csv`, 18 Aug 2026.

---

#### 2026-08-18 — Waterfall v2 shipped, and the boundary it was meant to fix did NOT improve
**Domain:** Clustering / Methodology
Built waterfall v2 into `src/features_real.py` (11 segments + Unassigned, `is_last_minute` flag,
`value_band`, six `enforce` rules asserted in code) and re-ran V1. **The headline claim does not survive
the check, and this entry exists so nobody presents it.**
**What the fresh V1 run says about OFW↔Balikbayan:** strict (TIER_A anchors only) **0.548 —
"not distinguishable"**; adaptive (full admissible set) **0.713**; the isolated clean-pair test **0.72**.
**⚠️ The 0.608 in `continuum-levers-plan.md` is the *strict pairwise matrix* cell, not the clean-pair
test.** So "0.608 → 0.72" compares two different measurements and is not a real improvement. Like for
like, strict has gone **0.608 → 0.548**, slightly *worse*.
**The decisive test was an A/B on identical method, anchors and population, varying only the labels**
(`proxy_segment_v1` is retained in the parquet for exactly this): **v1 0.730 · v2 0.728.** The new
taxonomy is **neutral** on this boundary — within noise, marginally negative.
**Why that was predictable in hindsight, and was in fact predicted:** the only v2 change touching this
pair is the H08 exclusion, which moves ~40k premium short-stay bookings out of Balikbayan/VFR — 1.4% of
the branch. **The Gulf stay-length discriminator that justified spending the anchor is still a soft prior
and still changes no label** (see the entry below). We spent the anchor, shipped the taxonomy, and the
boundary is where it was.
*Generalises: keep the previous labels in the output. The A/B took four minutes and it is the difference
between "we improved the weakest boundary" and "we did not". Without `proxy_segment_v1` in the parquet we
would have compared against a remembered number from a different test and been wrong in public.*
**What v2 *did* buy, and it is worth defending on its own terms:** `Unassigned` falls **9.58% → 2.47%**
(−74%), closing taxonomy gap #4; four new segments PAL asked for; `Last-Minute` converted to a flag that
exposes **4,411,666 short-lead bookings against the 2,945,686 the segment ever showed**; and every
`enforce` hard rule now asserted at build time. **Genuine reclassification is 23.4% of bookings
(5,358,355)** — *not* the 62.7% of labels that differ textually, which mostly reflects the
`Budget/Adventure → Leisure` rename. **Quote 23.4%.**
**Source:** our analysis, 2026-08-18 — `outputs/validate_construct/summary.md` line 87 and §3;
A/B run in-session; `docs/waterfall-v2-design.md`.

#### 2026-08-18 — We spent a validation anchor and never wired up the rule it was spent for
**Domain:** Clustering / Methodology
Checking the settled design before recommending next steps: **the OFW↔Balikbayan boundary is still split
on `round_trip` alone.** Branches 9/10 are unchanged from v1. The Gulf stay-length discriminator (S14) is
a **soft prior**, and **nothing in the codebase reads soft priors** — `grep` finds only
`check_constraints.py` opening that file. **19 rules are marked `prior` and not one of them can affect a
label.** So the rule that justified spending `stay_nights` is, today, documentation.
`stay_nights` is not wasted — it does real work in six branches (Corporate ×2, MICE, Intl. Student, Ultra
Wealthy Leisure, the H08 exclusion). But the *headline* reason we spent it is unimplemented, and nobody
noticed across three days of design work because the anchor decision and the labelling mechanism were
discussed in separate sessions.
**And the fix is smaller than the headline number implied.** Promoting S14 to a branch moves **79,993
bookings, 2.6% of the Balikbayan/VFR branch** (median stay 33 vs 12 nights, mean revenue USD 723 vs 619,
0% vs 4% group — the predicted direction, real but narrow). ⚠️ **The 0.676 AUC was measured on a corridor
proxy** — stay length separating Gulf-bound from US/AU-bound *destinations* — **not on the OFW/VFR labels.**
So it will not transform the 0.608 boundary and we must not tell PAL it will.
*Generalises, and it is the sharpest lesson of the week: **a decision to spend a resource is not the same
as the work that spends it.** We priced the trade carefully, took it deliberately, documented it in three
places — and then designed a waterfall that does not contain the rule. Check that the mechanism exists
before pricing what it buys.*
**Corollary worth acting on:** the real discriminator for this boundary is probably a **frequent-flyer
number**, not stay length, and PAL has just agreed to supply `IsFrequentFlyer` / `IsTourCode` /
`Isupgrade`. Those fields are on the critical path for the weakest part of the deliverable — chasing them
beats either implementing S14 or building the soft-prior layer for this particular purpose.
**Source:** our analysis, 2026-08-18 — `docs/waterfall-v2-design.md` §7a.

#### 2026-08-18 — PAL answers all 24 questions: two segments deleted, one renamed, and a correction to our own correction
**Domain:** Project Decision
All 24 open items came back answered in one pass (`wishlist/pal-questions-answered-2026-08-18.csv`, filed
verbatim). Our columns were returned unedited and the ids and schema intact, which is the payoff for
sending a CSV with blank answer columns rather than prose in an email. Methodology v1.9.
**Two segments deleted, which is a first for this project.** ① **`Family` is dropped** — "might be best to
drop family as only other indicator would be group travel during long weekends". We had told them it had
no positive definition (100% of it was *a group booking no other rule claimed*) and they followed the
argument to its end. Its 350,527 bookings redistribute **190,777 → Outbound International Leisure ·
155,025 → Leisure · 4,725 → Unassigned**. ② **`Digital Nomad` is dropped** — the one segment in the
original requirement we never implemented, resolved by deletion rather than definition after months of
being carried as a gap. *Worth noting: applying "a positive definition beats a residual" honestly did not
produce a better rule, it produced a deleted segment. That is a legitimate outcome and we should expect it
again.*
**③ `Budget/Adventure` → `Leisure`, a rename this time.** Reverses our 17 Aug choice to map the name
rather than rename the segment — so palette, Power BI dimension, personas and every deck follow. Cheap
option chosen on Monday, expensive option chosen on Tuesday; the lesson is that "just map it" was our
inference, not their instruction.
**④ They rejected our route-direction fix, and they were right.** We had made the Gulf rule
direction-agnostic; RM said *"do not agree, RUHMNL should be read as is"*. Agnostic matching **conflates
workers leaving for the job with workers coming home** — genuinely different rules that we had merged for
convenience. The directional reading costs almost nothing: **90,540 bookings against 94,247 agnostic, 96%
of the volume with a cleaner definition.** *Generalises: when a rule looks wrong, prefer fixing its
direction to widening it. Widening recovered the volume and lost the concept.*
**⑤ Catholic pilgrimage hubs withdrawn** — "No other airport codes to add". Consistent with our own
measurement that those rules fired on under 700 bookings each. **⑥ H13 unblocked** — the group indicator
may stand in for PNR party size, though the "party > 10" *threshold* stays unevaluable, so the rule ships
weaker (2,832 bookings, 219 of which would otherwise be MICE).
**⑦ Revenue is USD.** First confirmation, after our own guard could only say "plausibly single-currency".
Retroactively validates every revenue figure quoted — and 53 USD for a domestic promo booking is
plausible in a way the unlabelled number never was. *Ask what the units are before quoting the numbers,
not after.*
**⚠️ One answer contradicts a decision made the day before.** D3 supplies a **May/June Mecca window** — a
departure-month rule — immediately after **C8 agreed to withdraw the month-based rules** protecting
`dep_month` as a validation anchor. Recorded in S41 and **deliberately not encoded**, flagged back to
them. *An SME answering one question can undo the answer to another without either party noticing; a
cross-check against already-settled decisions belongs in every intake, not just the first.*
**⚠️ Cost weights deferred** — "see run first" — so any build carries explicit placeholders that must not
reach a published number. **A5 dissolved rather than resolved:** they answered the Family-vs-Outbound
ordering question *and* asked us to drop Family, so the 190,777 bookings land where the rejected
alternative would have put them.
**Net taxonomy: 11 segments + `Unassigned`** — four added, three removed against the original ten.
`SEG_RETIRED` added to `pal_colors.py` so a stale name is a lookup rather than a mystery.
**Source:** `wishlist/pal-questions-answered-2026-08-18.csv`; `docs/waterfall-v2-design.md` §0;
`docs/methodology.md` v1.9.

#### 2026-08-17 — The frequency segment fails its own gate: 1.81× becomes 1.32× under controls, and the anchor is kept
**Domain:** Clustering / Methodology
Ran the pre-registered gate on the proposed frequency-based domestic segment (the "unmanaged business
travel" population). **Both controls pass and the recommendation still dies — because passing is not the
same as mattering.**
**Control 1, within lead-time bands.** Raw gap in bookings per customer was 9.8 vs 5.4 = **1.81×**. Within
bands it is 1.49 · 1.44 · 1.36 · 1.32 · 1.20 · **1.11** as lead time grows — surviving everywhere but
**attenuating monotonically**, so much of the raw gap was composition: mid-tier is concentrated in
short-lead bookings and short-lead bookers fly more.
**Control 2, tenure.** Mid-tier customers sit in the extract longer (343 vs 234 days), which inflates any
lifetime count. On a **rate** basis: **7.5 vs 5.7 bookings/year = 1.32×**, not 1.81×.
**Decision: do not build the segment.** A 1.32× booking-rate difference is not a customer type. And the
axis that *does* separate strongly — **lead time, 5 vs 25 median days, 39.6% vs 12.1% booking inside three
days, ~3.3×** — is **already a rule field** and already drives the Last-Minute flag. So the segment would
spend `n_bookings`, our second-to-last validation anchor, to add a 1.3× signal on top of a flag already
shipping. **`n_bookings` is kept.**
*Generalises, and this is the third time today the same shape has appeared: **a raw ratio is a composition
artifact until you stratify.** 30-night spikes needed a round-number control; "pays more" needed a
booking-timing control; "flies more" needed lead-time and tenure controls. Each time the headline number
was roughly right and roughly meaningless. Set the gate before looking, and state the effect size that
would justify acting — "survives the control" is too low a bar on 22.9M rows, where almost everything
survives.*
**Also worth keeping: cheap axes first.** Before spending an anchor on a new discriminator, check whether
an **already-spent** field separates the same population better. Here `lead_days` (already a rule input,
already flagged) beat `n_bookings` 3.3× to 1.3×, so the expensive option was also the weaker one.
**Source:** our analysis, 2026-08-17 — probes over `pal_features_booking.parquet` +
`pal_features_customer.parquet`; `docs/sme-constraints-intake.md` "Verification result".

#### 2026-08-17 — The "missing value rung" is mostly a yield-management artifact; the real population is frequency, not fare
**Domain:** Data & Features
Same-day revision of the entry below, after testing the two candidate populations on **behaviour** instead
of price. **The correction matters more than the original finding.**
**Fare tier is partly an OUTPUT of booking timing, not a customer property.** Domestic economy, budget
(tier 1–2) vs mid (tier 3–4): **median lead 25 days vs 5 days**, and **39.6% of mid-tier books inside three
days** against 12.1% of budget. Supersaver/Saver inventory sells out early, so a late booker lands in
Value/Flex for the same seat. A large part of "pays 2.6× more" is therefore **"booked late"**. Building a
segment on the fare ladder would **encode a revenue-management mechanism as a customer type** — the exact
error class as reading a spike at 30 nights without a round-number control.
**One difference is genuinely customer-level and timing cannot explain it:** **bookings per customer 9.8
vs 5.4**, and **37.7% vs 20.2%** of bookings from customers with 6+ lifetime bookings. *Inventory does not
make someone fly twice as often.* So a real population exists — it is just not "mid-value leisure". Profile:
flies ~10×, books ~5 days out, 15.7% same-day/overnight turnarounds, Mon–Tue departures 31.0% (between
Budget's 28.9% and Corporate's 33.8%). That reads as **unmanaged business travel** — work trips booked
outside a TMC or corporate portal, at companies that do not pay for business class. It is precisely our own
unconfirmed rule **S04** (`is_domestic AND n_bookings >= 6` leans Corporate), and it is **corporate revenue
we are not recognising as corporate**.
**Outbound international economy IS distinct on behaviour, not just price:** vs domestic mid-tier —
round-trip **64% vs 38%**, median stay **6 vs 3** nights, median lead **19 vs 5** days, connecting
**23.9% vs 5.0%**. Different on every axis. This is taxonomy gap #4 and it earns a segment.
**Recommendation:** no value rung; build `Outbound International Leisure` (~2.0M, closes the gap); build a
**frequency-based** domestic segment on `n_bookings`/`lead_days` rather than fare tier (~3.5M), *after*
testing whether the frequency gap survives controlling for lead time; ship fare tier as a reporting **band**.
**⚠️ And the cost nobody has priced yet: `n_bookings` is one of the two remaining validation anchors.** A
frequency-defined segment spends it, leaving `dep_month` alone. That is a *second* anchor decision of the
same kind as decision 1 and must be taken as deliberately.
*Generalises: before promoting a price difference to a customer difference, ask what else moves with price.
In an airline, fare level is downstream of booking lead time by design, so "pays more" and "books later"
are the same observation until separated. The customer-level metric (frequency) is what survived.*
**Source:** our analysis, 2026-08-17 — probes over `pal_features_booking.parquet` +
`pal_features_customer.parquet`; `docs/sme-constraints-intake.md` "REVISED same day".

#### 2026-08-17 — The missing leisure rung is real, is 17.7% of the book, and is two populations rather than one
**Domain:** Data & Features
Follow-up to the decision-4 sizing: if `Budget/Adventure` is heading to 50.3% of the book, is there
anything between it and the newly-approved *Ultra Wealthy Leisure*? Measured on the post-change segment
using the fare-tier ladder the SME's own rules already use.
**Yes — and it is the commercially important part.** Inside the 11,513,783: tier 1 Supersaver 36.5% ·
tier 2 Saver 30.0% · tier 3 Value 24.4% · tier 4 Flex 9.0%. Split at the SME's own Saver/Value line,
**tier 3–4 is 33.4% of the segment by volume but 56.2% of its revenue, at 2.57× revenue per booking.**
Calling all 11.5M of them "budget" is wrong about a third of them.
**The ladder, filled in** (extract's own revenue units; ratios are the safe reading): Budget (domestic
tier 1–2) 7,657,514 @ 53 → **Middle (tier 3–4 economy) 4,045,178 @ 197 (3.7×)** → Premium Bleisure
481,666 @ 1,504 (7.6×) → Ultra Wealthy 178,069 @ 1,967. Monotone, with the one structural jump where
the cabin product changes rather than the fare.
**⚠️ The find that changes the shape of the question: it is TWO populations.** `Unassigned` is **75%
PH-issued international economy — 1,997,820 bookings at mean revenue 405**, i.e. *higher*-value than the
domestic middle rung, not part of it. So the space between deep-discount domestic and premium cabin holds
(a) **mid-tier domestic economy**, 3,497,751 @ ~197, and (b) **outbound PH-issued international economy**,
~2.0M @ ~405 — and (b) **is taxonomy gap #4**, the bucket we have been reporting to PAL separately as the
largest actionable gap. **Filling the middle rung and closing Unassigned are one conversation, not two** —
worth knowing before anyone schedules them as separate workstreams.
**⚠️ Discipline note: this is a value cut, not a purpose cut, and not a discovered cluster.** Behaviour is
nearly identical across tiers 1–4 (median stay 3–4 nights, round-trip 32–38%); what separates them is what
they *paid*. Legitimate — the deliverable is explicitly *trip-purpose × value* and this is the value axis —
but it must never be presented as structure found in the data. If anyone proposes validating the split
with a silhouette it needs a floor measured on this population with this feature set (2026-08-14 lesson).
*Generalises: when a segment swells past ~40% of the book, check whether the rule that defines it is
coarser than the ladder its own SME rules already use. Here `is_domestic AND NOT any_premium` ignored a
1–7 fare ladder that the constraint sheet leans on in eleven separate rules.*
**Source:** our analysis, 2026-08-17 — probe over `pal_features_booking.parquet`;
`docs/sme-constraints-intake.md` "The missing middle rung".

#### 2026-08-17 — PAL settles the taxonomy: 13 segments, Last-Minute becomes a flag, and the flag exposes 50% more volume than the segment did
**Domain:** Project Decision
All five blocking decisions from `docs/sme-constraints-intake.md` §7 resolved. Methodology v1.8.
**① Anchor: spend `stay_nights`, keep `dep_month`.** The five rules whose *primary* claim was departure
month are `withdrawn` (S02 peak season · S10 Q4–Q1 Balikbayan peak · S12 summer spike to Asian hubs ·
S16 Lent/Easter · S20 off-peak long stays) — kept in the file rather than deleted so the SME can see what
we set aside. S38 was **rewritten** instead: its academic-month clause sat on top of a 90–150 night stay
that stands alone, so the months went and the rule survived (fires 17,354 → 51,223). *The part worth
copying: `src/check_constraints.py` now **fails** if any active rule reads `dep_month`. A decision that
lives only in a doc is a decision that gets undone by the next person; this one is executable.*
**② 10 → 13 segments.** MICE, Ultra Wealthy Leisure and Intl. Student approved. **③** The SME's "Leisure"
is our `Budget/Adventure` — naming only, no rename, so palette / `dim_segment` / personas / PAL's existing
slides are untouched. **⑤** Family's `must_be` on `is_group` demoted.
**The design decision inside ②:** `src/pal_colors.py` now separates **`SEG_ORDER` (11, what the model
emits)** from **`SEG_APPROVED` (13, what PAL agreed)** plus **`SEG_FLAGS`**, with asserts tying each to the
palette. Adding the three new names straight to `SEG_ORDER` would have put segments in every chart legend
that the waterfall never assigns — an empty category reads as "zero customers", not as "not built yet".
*Generalises: the approved taxonomy and the emitted taxonomy are different objects and drift apart the
moment a decision lands ahead of the code. Name them separately or something will quietly plot a lie.*
**④ Last-Minute → flag, and the numbers argue for it more strongly than the reasoning did.** Simulating
the branch removal reproduces `rule_confidence.py` exactly: **84.1% of its 2,945,686 bookings go to
`Budget/Adventure`**, 15.9% to `Unassigned`, nothing else moves. The real find is the asymmetry — as a
*segment* Last-Minute caught only what fell through eight higher-priority rules (2.95M), but as a *flag*
it applies wherever `lead_days <= 3`: **4,411,666 bookings, 19.26%**, including **864,292 OFW/Migrant,
315,333 Corporate and 196,364 Balikbayan/VFR that were short-lead all along and invisible as such.**
**A priority cascade hides every overlapping signal below the winning branch; converting one to a flag
recovered 50% more volume without touching a single rule threshold.** Worth auditing the other branches
for the same effect.
**⚠️ And the cost, which re-opens a question PAL thought it had closed:** `Budget/Adventure` would reach
**11,513,783 — 50.3% of the whole book.** Half the population in one segment is not a targeting unit. PAL
approved *Ultra Wealthy Leisure* at the top of a leisure ladder in the same breath as sending the bottom
rung to 50%, so **the missing middle rung is now the live taxonomy question** — flag it before the
waterfall change ships, not after.
**Source:** our analysis + PAL decisions, 2026-08-17 — `src/pal_colors.py`, `src/check_constraints.py`,
`data/constraints/*.csv`, `docs/sme-constraints-intake.md` §7, `docs/methodology.md` v1.8.

#### 2026-08-17 — 57 constraints transcribed, and the checker that validates them caught three errors in my own transcription
**Domain:** Project Decision
The SME sheet is now typed into `data/constraints/` — **15 hard + 42 soft rules**, each carrying `status`,
`scope`, `fires` and `sme_row` so provenance and usability are legible per row rather than in prose.
**Nothing is wired into the pipeline**, deliberately: these files are the artifact we hand back to the SME
plus the eventual labelling input, and enforcement is the step that spends an anchor.
**The judgement calls applied, all of them visible in the files rather than silent:** row 21 narrowed to
the Gulf and made direction-agnostic (23× the volume); rows 34 and 38 **demoted from `cannot_be` to soft**
because a `moderate`-confidence veto covering 63.1% and 33.5% of the book cannot be a law; row 9 demoted
from `must_be` because six segments claim `is_group`; the nine thin rules kept with `status=too_thin`
rather than deleted, so the SME can see *why* we are querying them.
**The real lesson is `src/check_constraints.py`.** It validates every condition against the live feature
table — columns exist, DuckDB can evaluate it, the recorded `fires` still matches, `status` agrees with
the volume — and **it found three errors in a transcription I had just written by hand**:
① **stale counts.** Every `fires` figure was 2–23 bookings off, because I had rebuilt the parquet with the
determinism fix *after* running the coverage probe. Invisible to inspection, caught instantly by
recomputation. ② **CSV comma corruption.** Conditions like `dep_month IN (4,5,12)` and notes containing
commas were written unquoted, silently shifting every later column on 16 rows. My first repair then made
it *worse*, because I assumed only the condition over-split when unquoted notes did too — the fix was to
stop hand-authoring and regenerate through `csv.writer`. ③ **A rule 2.3× larger than recorded** — S21
fired on 23,254 not 9,979, because `route_theme` matches a themed endpoint in **either** direction while
our probe had matched only the outbound one. **We had just written up the direction trap in the SME's
work and then committed the same class of error in our own.**
*Generalises: for any hand-maintained data file that something downstream will trust, the check script is
not optional scaffolding — it is the only thing standing between "looks right" and "is right". And a rule
that silently stops matching is worse than a missing rule, because it reads as covered.*
**Two schema notes:** `n_bookings` lives on the customer rollup, so one rule (S04) needs a join — the
vocabulary spans two grains, which the checker now handles explicitly. And `any_cabin_j` was added to
Stage F because rows 24/33 turn on cabin `J` specifically, which `any_business` (a business *fare*,
tier ≥ 6) does not capture; writing a condition against a field that did not exist would have been
precisely the sloppiness we flagged in the workbook.
**Source:** our change — `data/constraints/{hard,soft}_constraints.csv` + `README.md`,
`src/check_constraints.py`; `docs/sme-constraints-intake.md` §8.

#### 2026-08-17 — Stage F gains four descriptive fields; the waterfall is untouched, and that is the point
**Domain:** Data & Features
Acting on the SME constraint sheet, `src/features_real.py` now emits **`stay_nights`**, **`dep_dow`**,
**`turn_dest`** and **`route_theme`**, plus a new tracked reference `data/reference/route_theme.csv`
(8 trip-purpose themes over 32 airports, built by `src/build_airport_ref.py`). Methodology v1.7.
**The discipline that made this safe: build the field, do not wire it in.** No waterfall branch reads any
of the four, so proxy labels are bit-identical (Unassigned still 9.58%; every segment count unchanged) —
**and the fields stay admissible as validation anchors.** The moment a rule consumes one it stops being
able to check that rule. Adding the column is reversible; spending it is not. They are registered in a new
`CANDIDATE_ANCHORS` block in `validation_anchors.py` — *not* in `ANCHORS`, and not loaded by
`load_anchors` — with the leaks each would carry written down in advance.
**`stay_nights` coverage: 9,785,597 = 100% of round trips, 42.71% of the book, median 5 nights.** It is
**NULL on one-ways by definition** — there is no stay to measure — and that is not a detail:
*definedness IS `round_trip`*, the sole bit separating OFW/Migrant from Balikbayan/VFR. So a validator
handed this field on that pair sees it wholly present on one side and wholly absent on the other and
scores **AUC 1.0 while proving nothing.** ⚠️ **`stay_nights` therefore cannot validate the very boundary
it was fetched to improve.** Its anchor value is pairs that *agree* on round_trip — Corporate vs Premium
Bleisure, the gap Lever A flagged. New build-time guard `assert_stay_contract()` fails the run if a
one-way ever acquires a value, because the natural bug (reading the raw max gap, which on a one-way is a
connection layover) would leak the rule bit through the missingness pattern silently.
**Two implementation notes worth keeping.** ① **Max-gap, not last-minus-first.** Connections inflate the
naive span — the two disagree on **9.60% of round trips**. ② **Route themes went in a *separate* file
from `airport_region.csv`**, which is byte-identical after the change, because the theme lookup is keyed
on **trip** endpoints (so codeshare beyond-points FCO/TLV/CDG/LIS resolve — none is a PR sector endpoint)
while `is_domestic` is load-bearing in the model. Mixing an experimental SME taxonomy into a load-bearing
join is how a descriptive field quietly becomes a modelling change.
**Doc-vs-code drift found and fixed:** `methodology.md` still listed `age`/`age_known` as **Tier-A**
anchors — the 2026-07-30 leak audit moved both to conditional and the code has read
`TIER_A = ("dep_month", "n_bookings")` ever since. The table was ~3 weeks stale. *Generalises: the leak
audit updated the code and the learning log but not the spec table; a correction is not landed until
every place that states the old fact is changed.*
**Bonus defect found by accident, and worth the habit that found it: the build was not reproducible.**
Running Stage F twice gave `round_trip` = 9,785,597 then 9,785,584. Cause: coupons were ordered by
`departure_dt` alone, but **8,014 bookings have two coupons departing at the same timestamp, and on
3,205 of them the coupons have different `trip_origin`** — so `arg_min`/`arg_max` picked arbitrarily,
flipping `round_trip` on ~20 bookings per run. Pre-existing, not introduced here; `stay_nights` merely
made it visible because its definedness tracks `round_trip`. Fixed by ordering on
`(departure_dt, coupon_number)`; two consecutive runs now agree exactly (`round_trip` = **9,785,666**).
*Generalises: `arg_min`/`arg_max`/`first` over a non-unique ordering key is silently non-deterministic.
The only reason it surfaced is that a number was read twice and compared — do that.*
**Source:** our change — `src/features_real.py`, `src/build_airport_ref.py`, `src/validation_anchors.py`;
`outputs/features_real/summary.md`; `docs/methodology.md` v1.7; `docs/data-dictionary.md` Sheet 3.

#### 2026-08-17 — Gulf travel runs on a one-month clock: the SME's stay-length claim is half true, and the sheet's route notation is backwards
**Domain:** Data & Features
Two probes over the full 22.9M-booking population (`src/probe_stay_length.py`,
`src/probe_constraint_coverage.py`) testing the RM-Domestic constraint sheet. Design point that made the
result trustworthy: **the test had to be differential.** Humans book round numbers, so 7/14/21/28 spike in
every corridor; a raw spike at 30 proves nothing. Each corridor was therefore scored against *its own*
round-number baseline (count at n ÷ median of n±2..±6).
**① The Gulf corridor has a real one-month rhythm that no other corridor has.** Excess at 30 nights is
**2.21 vs a 1.58 round-number control (1.40×)**, spread across 29–30–31 (2.07 · 2.21 · 2.15) — a mandated
month plus travel slop, not a one-day artefact. Decisively: **19.11% of Gulf round trips fall in the 28–32
night window vs 8.48% in the 12–16 window (ratio 2.25)** — the *only* corridor where a month outweighs a
fortnight; every other is ≤0.60 (tourist 0.19 · domestic 0.21 · US/CA/AU 0.60). Supporting gradient inside
the current Balikbayan/VFR bucket: Gulf share **1.96% → 8.72% → 28.09% → 34.49%** across <14/14–27/28–45/46+
bands while group rate falls 6.74% → 0.25%. **Worth AUC 0.676** on a corridor proxy vs the ~coin-flip the
current single-`round_trip`-bit rule gives.
**② "East Asia hubs" is refuted, and pooling it with the Gulf is *worse than useless*.** HKG/TPE show a sharp
ratio at 30 (2.34) on almost no mass — **1.93% of trips in the 28–32 window**, same as tourist hubs. Combined
AUC **0.375 — below chance** (short-haul, short-stay), vs **0.676** Gulf-only. *Generalises: an excess ratio
is not mass. Always report both, or a spike on 2% of a corridor will read like a finding.*
**③ The "~45 day" half of the claim is null** — Gulf excess at 45 is 1.34 against its own 1.58 control, i.e.
*below* baseline.
**④ It is one gradient, not two populations.** Density per night falls monotonically (6.85 → 2.66 → 2.18 →
1.49 → 0.82 %/night); no valley, so **no cut point splits workers from family visitors.** ⚠️ My own first
pass mis-read this: on *raw band shares* 28–45 looks like a second mode purely because that bin is 18 nights
wide against 7. **Unequal-width bins fake bimodality — always divide by band width.**
**⑤ ⚠️ The sheet's route notation is backwards for its own population.** The SME wrote OFW routes as
`TripOD IN ('MNLDXB','MNLRUH',…)`, but **Gulf round trips start in the Gulf 260,216 times vs Manila 26,195 —
9.9× more**: a worker based in Riyadh flying home is `RUHMNL`. Row 21 read literally matches **5,166**
bookings; direction-agnostic it matches **118,841 — 23×**. **Transcribing the workbook verbatim would have
silently gutted its single best rule.** Direction is a per-rule intake decision, not a default: row 18 (a
worker *leaving* for the job, one-way) genuinely is MNL→Gulf and fires on 349,445.
**⑥ Usability triage of all 39: 29 usable · 9 fire on <0.05% of the book · 1 unimplementable.** All four
Pilgrimage rules are in the thin group (fires: **29 · 3 · 349 · 656**) — the segment written most
confidently is the one we can least act on, because conjunctive `AND`s multiply small shares and the routes
are thin (**Catholic hubs FCO+TLV+CDG+LIS = 28,224 trip endpoints total** vs 70,650 for JED/MED). This
**corrects an overstatement I made earlier the same day** — "every Catholic pilgrimage is mislabelled" is
literally true but immaterial. Two rules are unexpectedly huge levers: **row 34 vetoes 63.1% of the book**
and **row 38 removes 33.5% of round trips**, both at confidence *moderate* — so both belong in `soft`.
**⑦ Scope ceilings nobody wrote down:** **26 of 39 rules cite stay length**, defined only for round trips
(**42.7%** of the book) — structurally silent on the other 57%. **Age is populated on just 0.98% of domestic
bookings** (129,023 of 13.2M), so **every age rule is dead for domestic travel**, which is what was asked for.
**⑧ One confound survives.** Fares carry maximum-stay conditions, commonly one month. Excess@30 falls with
value tier (2.01 → 1.19) but so does excess@14 (1.80 → 1.20), so the ratio is flat and tier is not
manufacturing the spike — yet a **Gulf-specific** one-month fare rule would reproduce it exactly. Closing it
needs **`FarebasisCode`**, which is in PAL's own data dictionary and which we do not ingest. **Request it.**
**Decision this settles:** spend `stay_nights` as an anchor (it buys 0.676 on our weakest boundary), keep
`dep_month`, request `Isupgrade`/`IsTourCode`/`IsFrequentFlyer` as replacements. But encode row 21 as a
**soft prior narrowed to the Gulf** — per ④ there is no clean boundary to assert, and per Lever A this will
improve **label quality, not cluster separation.**
**Source:** our analysis — `outputs/stay_length/summary.md`, `outputs/constraint_coverage/summary.md`,
`docs/sme-constraints-intake.md` §3/§4a.

#### 2026-08-17 — First SME constraint sheet returned: 39 new rules, and encoding them would cost us both remaining validation anchors
**Domain:** Project Decision
`wishlist/PALxMAIDA_Constraints&Wishlist.xlsx` came back from **RM — Domestic**: 51 rows, of which 12 are our
own seeded examples returned verbatim and **39 are new** (26 *leans toward* · 9 *cannot be* · 3 *leans away* ·
1 *must be*; 8 `certain` + 1 `likely` are hard, the other 30 soft). Their `Guide` sheet independently arrived at
our exact hard/soft split and enforcement rule, so **no schema negotiation is needed** — the five constraint
types map 1:1 onto `data/constraints/*.csv`. Full intake analysis: `docs/sme-constraints-intake.md`.
**The best contribution:** rows 14/16/17/21 split **OFW vs Balikbayan/VFR on stay length** — the boundary that
currently splits 6.8M bookings on the single `round_trip` bit and scores our lowest construct-validity AUC
(**0.608**). Their mechanism is specific and testable: OFWs hold **employer-mandated ~30- or ~45-day leave**,
balikbayans stay open-ended 14+/21+ over Q4–Q1. That predicts a *distributional spike* at 30 and 45 nights in
the Gulf corridors, checkable on the 9.79M round-trip bookings where stay length is computable.
**⚠️ The cost nobody priced.** Plan B's contract is that a rule input cannot validate its own rule, and after
the leak audit only **two** unconditionally admissible anchors remain (`TIER_A = ("dep_month", "n_bookings")`).
The sheet spends both reserves: **5 rules condition on `Month(DepartureDate)`** (kills `dep_month`) and
**23 of 39 condition on `StayPattern`** (burns `stay_nights`, which Lever A had explicitly re-targeted as a
*candidate Tier-A anchor*). Transcribed as written, construct validity is left with `n_bookings` **alone**.
**This is a trade-off to decide, not a reason to reject the rules** — recommendation is spend `stay_nights`
(it fixes the weakest boundary), keep `dep_month` (the seasonality rules are the file's weakest, `moderate` at
best, and `peak_month` already carries the effect), and request **`Isupgrade` · `IsTourCode` ·
`IsFrequentFlyer`** as replacement anchors — all three are derivable-or-listed and **no rule in the sheet
touches any of them.** *Generalises: every SME rule round silently consumes anchor budget. Price it at intake.*
**Six other things the intake turned up.** ① **`is_group` is over-subscribed six ways** — Family (`must_be`),
Pilgrimage, Premium Bleisure, MICE, Last-Minute and Ultra-Wealthy all claim it; our waterfall's
`WHEN is_group THEN 'Family'` at priority 8 pre-empts all five others, so that `must_be` must be demoted.
② **We only encode Islamic pilgrimage hubs (JED/MED)** — the SME named **FCO/TLV/CDG/LIS**, so *every Catholic
pilgrimage in the book is currently mislabelled*, on a Philippine carrier. ③ **Three new segments** (MICE,
Ultra Wealthy Leisure, Intl. Student) and a 4-way sub-typing of Last-Minute — which supports our own finding
that Last-Minute is an **overlay, not a peer segment** (84.1% would otherwise be Budget/Adventure).
④ **Row 46 is unimplementable** (needs PNR party size; sectoral pax count is always 1). ⑤ **Booking-class `F`
needs its Apr-2026 date guard** — the rationale says "post-April 2026" but the condition omits it; transcribe
as `is_award`, never raw `F`. ⑥ **The ask was for *domestic* constraints; the answer is mostly international** —
1 row names domestic routes, 14 name international corridors, 24 are route-agnostic — and the two fields
domestic rules most need are weakest there (`Age` is **international-only**; `stay_nights` is undefined for
one-ways, i.e. most of the domestic point-to-point book). The **Power BI wishlist sheet came back empty**, and
four segments got zero input: Mabuhay Loyalist, Family, Budget/Adventure and **Digital Nomad** — the one
segment in the requirement we have never implemented.
**Expectation-setting:** Lever A already tested stay length as a *clustering* feature and it was null
(0.323 → 0.319 vs a 0.45 bar). These are *labelling* rules, where descriptive discrimination is exactly what is
wanted — so **`stay_nights` will improve label quality, not cluster separation.** Do not tell PAL the continuum
finding changes because stay length arrived.
**Source:** `wishlist/PALxMAIDA_Constraints&Wishlist.xlsx`; our analysis in `docs/sme-constraints-intake.md`;
cross-referenced against `src/validation_anchors.py`, `src/features_real.py` (proxy waterfall) and
`docs/continuum-levers-plan.md` Lever A.

#### 2026-08-14 — Oversampling tested before and after the rule waterfall: both harmful, and *before* silently rewrites the taxonomy
**Domain:** Clustering / Methodology
Random oversampling with replacement, 100k pool → 20k, same 3-method panel, **each condition scored against
its own matched noise floor** (the discipline established earlier today).

| Condition | sil | own floor | **margin** | ARI | mix |
|---|---:|---:|---:|---:|---|
| **Natural** (control) | 0.294 | 0.201 | **+0.093** | 0.435 | Budget 39.8% · OFW 17.0% · Balikbayan 12.8% |
| **BEFORE** — balance by `dest_region`, then apply rules | 0.142 | 0.223 | **−0.081** | 0.300 | **Budget 11.6% · OFW 30.9% · Balikbayan 26.1%** |
| **AFTER** — apply rules, then balance by segment | 0.208 | 0.149 | **+0.059** | 0.313 | forced 10% each · **33.4% duplicate rows** |

**① Oversampling BEFORE the waterfall rewrites the segmentation — this is the practically important finding.**
Balancing the input by destination region collapses **Budget/Adventure 39.8% → 11.6%** and nearly doubles
**OFW/Migrant 17.0% → 30.9%** and **Balikbayan/VFR 12.8% → 26.1%**. Mechanically obvious in hindsight —
`Budget/Adventure` requires `is_domestic`, and balancing regions cuts domestic from 57.7% to ~1/6 — but the
consequence is that **any upstream resampling changes the headline segment shares without a single customer
behaving differently.** If anyone ever resamples before Stage F, every number in the deliverable moves.

**② BEFORE is worse than noise.** Margin **−0.081**: the real data clusters *less* well than its own shuffled
control. Balancing an input axis leaves a population whose remaining correlations fight the geometry, while
shuffling breaks them and makes spherical clusters easier to find. A negative margin is as clear a rejection
as this framework produces.

**③ AFTER degrades both separation and agreement.** Margin falls **+0.093 → +0.059** and ARI falls
**0.435 → 0.313**, on a sample that is **33.4% duplicated rows**. Note the prediction that balancing would
*inflate* ARI was wrong — it fell, because duplicated minority rows pull cluster centroids toward replicated
points rather than toward real ones. **Caveat on this row's floor:** shuffling columns destroys the very
duplication being tested, so 0.149 is not a perfectly matched control. The direction is unambiguous (both
score and margin fall), but do not over-read the exact margin.

**Conclusion:** neither placement helps. Combined with the earlier rejection of five resampling strategies in
`src/resample_compare.py`, resampling is now closed on this project from both the supervised and unsupervised
side. Imbalance stays handled where it belongs — the **asymmetric cost matrix**, **stratified measurement
sampling**, and **weighted SME sampling**.
**Source:** our analysis — probe over `pal_features_booking.parquet` reusing `src/model_zoo.py`.

#### 2026-08-14 — A silhouette is meaningless without its **matched** noise floor: the domestic "structure" and Lever C's live thread both dissolve
**Domain:** Clustering / Methodology
Follow-up to the question *"would class-imbalance treatment help, since the data is domestic-dominated?"*
Two findings, and the second invalidates one of our own pre-registered bars.
**① Conditioning on domestic/international gives no real gain.** Clustering each separately (20k samples,
same 3-method panel): **domestic sil 0.469** (ARI 0.160) · **international sil 0.234** (ARI 0.383), against a
pooled baseline of 0.319. Domestic looked like a breakthrough — **until we measured its own noise floor.**
Shuffling every column *within the domestic population* scores **0.345 · 0.332 · 0.360, mean 0.346** — versus
**0.205** for the full population. **Domestic's margin over its own floor is +0.123; the pooled population's
is +0.114. Statistically the same.** The domestic population is not more structured; it is
lower-dimensional and more homogeneous, so **random data clusters more easily there**. International is
*worse* than pooled (+0.029 over floor).
**② This closes Lever C's remaining live thread.** The three markets that "passed" (DVO-MNL 0.511 · MNL-DVO
0.496 · CEB-MNL 0.464) are all **domestic point-to-point** routes. Read against a domestic-like floor of
**~0.35** rather than the global 0.205, they sit at the same margin as everything else. The directional
pattern was a floor effect, not structure. **No lever remains open.**
**③ The methodological lesson, and it is the important one.** **Comparing a sub-population's silhouette to a
global threshold is invalid.** Our pre-registered Lever C bar ("silhouette > 0.45 in a majority of markets")
was itself flawed — 0.45 means something different in each population. **Every silhouette must be quoted
against a noise floor measured on the same population with the same feature set.** Corollary already flagged:
the LCA sub-type silhouettes (0.204–0.264) are scored *within parent segments* and so need matched
within-parent floors before anyone reads them as weak-but-real; against a plausibly elevated floor they may
be at or below noise.
**④ Feature-drop confound quantified.** On the full population, dropping `dest_region` alone moves silhouette
**0.319 → 0.364 (+0.045) while agreement falls 0.432 → 0.346** — higher separation, less meaning. Dropping
`round_trip` does nothing (+0.000); dropping `connecting` *hurts* (−0.028). So `Spec.drop()` removing
constant columns in sub-population runs mechanically inflates their scores, which is part — but not all — of
what ② explains.
**On the original question:** class-imbalance treatments (SMOTE/over/under-sampling) are the wrong instrument
regardless. They are supervised techniques; on unsupervised clustering they *manufacture* density rather
than reveal it, which is the same failure mode Lever D's control caught. The project already evaluated and
rejected five of them (`src/resample_compare.py`), and imbalance is correctly handled elsewhere — the
asymmetric cost matrix, stratified measurement sampling, and weighted SME sampling. Also worth stating: at
**57.7% domestic / 42.3% international the data is not imbalanced at all** (1.4:1); the real imbalance is
between *segments* (39.4% vs 0.03%, ~1300:1), which no resampling can fix because it is a detection-floor
problem, not a sampling problem.
**Source:** our analysis — probes over `pal_features_booking.parquet` reusing `src/model_zoo.py`.

#### 2026-08-13 — Six continuum levers, all null: and a silhouette **noise floor of 0.205** that recalibrates every separation number we quote
**Domain:** Clustering / Methodology
Ran the full lever programme from `docs/continuum-levers-plan.md` as probe-level screens (3-method panel —
GMM(full) · KMeans · LCA — k=3–8, 20k samples, same `gower`/`gower_sil` as the harness). **Every lever failed
its pre-registered bar.** Detail below; Lever A has its own entry.

**① The noise floor is the most important result — 0.205.** Shuffling every feature column independently
(three seeds) and re-running the panel gives best silhouettes of **0.201 · 0.214 · 0.201, mean 0.205**. That
is what "no structure at all" scores on this data with these methods. **This had never been measured, and it
changes how every separation number here should be read.** Consequences: the published **0.381 ceiling sits
+0.176 above the floor — comfortably real**, so the continuum finding stands and is now properly calibrated;
but the conventional bands (>0.5 strong · 0.25–0.5 weak-but-real · <0.25 none) are **wrong for this data** —
locally, "none" is 0.205, not 0. **⚠️ Flag for review: the LCA sub-type silhouettes (0.204 · 0.215 · 0.264)
sit at or barely above this floor**, which would make them indistinguishable from noise. Not yet conclusive —
the floor was measured on the full population with the full spec, while sub-types are scored within a parent
on a narrower spec — **a matched within-parent shuffled control is needed before acting on it**, but the
`provisional` flag on those sub-types now looks generous rather than cautious.

**② Lever B — strip atypical populations: NULL, and it closes an explanation.** Removing all sea-crew
bookings and the 4,896 heavy-tail customers (≥100 coupons) moved silhouette **0.294 → 0.272, i.e. −0.022**
against a +0.08 bar. Population heterogeneity is **not** masking structure; the "mixed populations" line in
the ruled-out table moves from *mostly closed* to **closed**.

**③ Lever D — learned representation: NULL, and the control earned its keep.** SVD (MCA-like) 0.304,
autoencoder 0.294, against a 0.5 bar. The mandatory **shuffled control returned 0.219** — within 0.085 of the
real-data score — confirming that dimensionality reduction manufactures most of its own apparent structure.
Had the control been optional we would have reported a spurious improvement.

**④ Lever E — longitudinal, on the repeat cohort: NULL, and this is the big one.** Proper Phase 4 features on
**1,317,609 customers** (≥3 bookings, >180-day span): inter-trip interval and its variance, recency, route
entropy (Shannon over destination regions), seasonality spread, lead-time variance, revenue variance, tier
drift, round-trip/international/premium rates. Result **silhouette 0.211 · ARI 0.048** against bars of 0.5 and
0.6 — and **only +0.006 above the noise floor, i.e. indistinguishable from shuffled data.** Behaviour over
time was the strongest remaining hypothesis and it is now closed at customer grain.

**⑤ Lever G — coarser 4-segment taxonomy: NULL, and it refutes our own proposal.** Merging to a spine
(Domestic leisure 52.5% · Overseas Filipino 26.7% · Undefined 13.9% · Premium & business 6.9%) leaves the
weakest pairwise AUC at **0.606** — statistically the *same* weak boundary as OFW-vs-Balikbayan's 0.608, just
relocated to *Overseas Filipino vs Undefined* — while **signal retained collapses 0.348 → 0.194 (−44%)**
against a 0.02 tolerance. The pre-registered gate (*"a merge that improves geometry while losing predictive
signal is a bad trade"*) caught exactly the trade being proposed. **Do not take the coarse taxonomy to PAL.**
Side-finding worth keeping: the spine's *good* boundaries are strong (Domestic leisure vs Overseas Filipino
**0.947**), so the weakness is specifically **Undefined** — further evidence it is a **real population sitting
between the others rather than residue**, and a stronger reason for PAL to define it.

**⑥ Lever C — per-market: FAILS the majority rule, but the pattern is systematic and warrants a new,
separately pre-registered test.** *(The first run was void — it sampled before filtering, starving 5 of 6
markets. Fixed.)* **3 of 6 markets cleared 0.45**, and the split is not random: the three **one-way** markets
passed (DVO-MNL **0.511** · MNL-DVO **0.496** · CEB-MNL **0.464**) while the three **round-trip** markets
failed (MNL-MNL 0.363 · CEB-CEB 0.435 · DVO-DVO 0.432). **But the passing markets have the *lowest* agreement
with our taxonomy (ARI 0.16–0.19 vs 0.47–0.53 for the round-trip markets)** — so whatever structure exists
inside a directional market is *not* what our rules capture. **Confound that must be resolved first:**
`Spec.drop()` removes constant columns, so one-way markets are clustered in a **lower-dimensional space**,
where higher silhouettes are easier to obtain. **This is a hypothesis for a new pre-registered test, not a
result** — retro-fitting a hypothesis to a failed test is exactly what the plan's discipline section forbids.

**Programme-level note:** roughly **14 pre-registered comparisons across six levers, none cleared.** When
nothing clears there is no multiple-comparison problem to correct for — this is the cleanest possible form of
a null programme.
**Source:** our analysis — `outputs/levers/summary.md`, `outputs/levers/round2.md`, probes over
`pal_features_booking.parquet` reusing `src/model_zoo.py`.

#### 2026-08-13 — Lever A null: stay length adds no separating power, and the rule segments' own silhouette is ~0.009
**Domain:** Clustering / Methodology
Feasibility probe run **before** committing to the Stage F change proposed in
`docs/continuum-levers-plan.md` Lever A. Design: 20k reservoir sample of **round-trip** bookings (stay length
is undefined for one-ways, and *"is it defined"* is the `round_trip` rule bit, so imputing would leak a rule
input), 4,000 rows for the O(n²) silhouette, GMM(full) and KMeans at k = 3–8, baseline 11-feature spec vs
`+stay_nights`. Same `gower`/`gower_sil` code as the main harness, so the numbers are directly comparable.
**Result — the lever fails, and not narrowly.** Best Gower silhouette **0.323 → 0.319**; best ARI vs proxy
0.425 → 0.434; **mean deltas −0.007 (silhouette) and −0.022 (ARI)**. The pre-registered bar was 0.45 / 0.55.
**The reconciliation that matters:** stay length *does* discriminate descriptively — median 3 · 4 · 5 · 10 ·
13 · 33 nights across segments — but **a difference in medians is not geometric separation.** The
distributions overlap heavily, and the most distinctive segment (Pilgrimage, 33 nights) is 0.19% of the book,
far too small to move a global silhouette. **A feature can carry real descriptive signal and still fail to
make clusters separable** — worth remembering before the next feature proposal.
**Re-targeted, not discarded:** ship `stay_nights` as a BI/persona field, and test it as a **V1 construct-
validity anchor**, where descriptive discrimination on a field no rule consumes is exactly what is wanted. Do
**not** spend the 1.5 days on the clustering change.
**Bonus finding — the rule segments' own Gower silhouette is 0.009**, essentially zero, and as far as we can
tell had never been computed (the harness scores *fitted* labels, never the proxy partition). It says the
rules cut **across** the density rather than along its seams. Coherent rather than damaging: near-zero
separation alongside V1 AUCs of 0.608–0.965 means **the segments differ in ways that matter commercially
without being separable blobs.** Confirm on the full population before quoting it externally.
**Implementation gotcha:** `to_codes()` in `src/model_zoo.py` hardcodes each numeric by name, so a feature
added to `NUMERIC` is **silently dropped from the LCA input**. Any future feature needs a branch there too —
the Lever A task list was incomplete as written.
**Source:** our analysis — probe over `pal_clean` + `pal_features_booking.parquet`, reusing `src/model_zoo.py`.

#### 2026-08-13 — External benchmarks: our 0.381 separation ceiling **is** the published aviation figure, and Dolnicar & Leisch give the continuum finding its citation
**Domain:** Clustering / Methodology
Every metric in this project has been quoted against its own null and its own control, which answers *"is
this signal?"* but never *"is this good?"* A literature sweep of aviation and tourism segmentation studies
supplies the second answer, and it substantially changes how the continuum finding should be **presented**
without changing the finding itself.

1. **Our separation ceiling is at the field benchmark, not below it.** Published silhouettes: **0.37**
   (Manhattan) / 0.59 (Euclidean) for a fuzzy-c-means segmentation of European air passengers at k=5;
   **0.145** for K-Means on airline customer data vs 0.68 for DBSCAN on the same. Published aviation range
   **≈0.14–0.68**. Our ten-method Gower-silhouette ceiling of **0.381** sits essentially *on* the
   air-passenger figure and comfortably above the airline K-Means case. **Stop presenting 0.381 as a
   limitation to apologise for.** Sub-segments (0.204–0.264) are below the air-passenger figure but still
   above the K-Means case — so the honest sub-layer read is "weaker than published segments", which is a
   sharper statement than the previous "weak-but-real".
2. **Dolnicar & Leisch (*Marketing Letters* 21(1) 83–101) is the citation the continuum finding has been
   missing.** Their framework classifies data into three regimes — **natural clusters → reproducible
   clusters → constructive segmentation** — and states that naturally occurring clusters are **rare** in
   tourism data. Our result (weak separation, high reproducibility, transfer ARI at its own ceiling) is
   textbook **reproducible/constructive**. This converts "we found no clusters" from a negative result into
   a named, cited, field-normal classification, and it explicitly licenses a business-constructed taxonomy
   as the correct response to a continuum. **This should be the framing in every deliverable.**
3. **V1 construct validity beats the aviation predictive benchmark; V2 criterion validity does not.** Best
   published airline no-show prediction is **AUC 0.78** (KNN, best of six algorithms). Our median pairwise
   construct AUC across the 36 segment pairs is **0.796** — above it, on evidence the rules never saw. But
   V2's segment-only AUC of 0.632 with **+0.002** incremental value is below it. Both are true
   simultaneously and both must be said: **the segments are distinguishable but carry no new signal.**
4. **Sample adequacy is settled, and generously.** Dolnicar, Grün, Leisch & Schmidt give **70× the number
   of segmentation variables** (2014), revised to **100×** (2016). At 11 features that is **1,100 rows
   required**; the pipeline fits on **20,000** — **18× the requirement**, and 3.4× the n=5,800 of the
   canonical airline segmentation study (Teichert, Shehu & von Wartburg, *Transp. Res. A* 42(1) 227–242).
   The 20k sampling cap is no longer a defensible line of attack.
5. **We are over-segmented relative to the literature.** Teichert et al. reach **5 segments** by latent
   class on 5,800 frequent flyers. We deliver **9 named + Unassigned** on weaker separation. Defensible
   *only* via item 2 — the taxonomy is business-constructed, not discovered — so that framing is now
   load-bearing rather than merely honest.
6. **Several of our headline metrics have NO published aviation or tourism benchmark.** Total-variation
   distance, adversarial drift AUC, detection-power floors, rule-competition/boundary-fragility, and
   signal-retained/incremental-value returned nothing. Notably there is **no numeric ARI threshold** in the
   tourism literature — B4's framework is qualitative, so our 0.90/0.75 bands are an MLOps convention, not
   a field standard. There is also **no published minimum viable segment size**, so the ~1% detection floor
   has no comparator. **Every "ideal" figure for these is a logical target and must be labelled as one** —
   implying a standard exists where none does is the failure mode to avoid.
7. **The one benchmark we cannot answer at all is commercial value.** Airline cancellation forecasting and
   overbooking is documented at **1.15–4.16% revenue gain** (a second study: 0.4–3.2%). Nothing in
   `outputs/` estimates what this segmentation is worth. That is the number a client asks for, and it is
   the largest remaining gap in the deliverable — larger than any methodological one.
8. **Comparability caveat that must travel with all of the above.** The published silhouettes are
   **Euclidean, on survey attitude data, n in the thousands**. Ours is **Gower, on mixed-type behavioural
   data, n = 22.9M**. Same word, different measurement — these are order-of-magnitude sanity checks, not a
   like-for-like league table. Two of the sources (the MDPI air-passenger paper and the SAGE sample-size
   paper) returned **HTTP 403** and were read from indexed summaries rather than the publisher PDFs;
   **verify both before either figure enters a client deliverable.**

**Source:** external literature — Dolnicar & Leisch, *Marketing Letters* 21(1) 83–101; Dolnicar, Grün,
Leisch & Schmidt, *Journal of Travel Research* (sample sizes); Teichert, Shehu & von Wartburg,
*Transportation Research Part A* 42(1) 227–242; MDPI *Tourism & Hospitality* 6(1):27; *Black Sea Journal of
Engineering and Science* (K-Means/DBSCAN airline comparison); *No-Show Passenger Prediction for Flights*;
*Airline passenger cancellations: modeling, forecasting and impacts on revenue management*. Written up as
`docs/pipeline-study-guide.md` §6.4 (benchmarks B1–B8) and mirrored in the HTML edition.

#### 2026-08-13 — Stay length and upgrade are both derivable; Digital Nomad is absent and blocked on the wrong field
**Domain:** Data & Features
Checking three features against the code and raw extract ahead of a stakeholder session turned up two
recoverable capabilities and one documentation error.
1. **`round_trip` is in the model and load-bearing** — it is the sole discriminator between waterfall rules
   ⑤ and ⑥ (OFW/Migrant vs Balikbayan/VFR), and therefore owns the weakest boundary in the taxonomy
   (construct-validity AUC 0.608 over 6.8M bookings).
2. **Length of stay is NOT blocked — it is derivable.** `methodology.md` lists it under *Known Data Gaps
   (Blocking)*, which is true of the raw field but false of the quantity: for a round-trip booking it is
   outbound departure → return departure, from coupon dates we already hold. **9,787,386 round-trip
   bookings (42.7% of all), computable on 98.8% of them; median 5 nights (IQR 3–12).** Distribution:
   1–3 nights 31.5% · 4–7 33.7% · 8–14 14.1% · 15–30 13.3% · 31–90 6.7% · 90+ 0.8%. **It already
   discriminates on a field no rule consumes** — median stay by segment: Last-Minute/OFW 3 · Family,
   Budget, Corporate 4 · Mabuhay, Unassigned 5 · **Premium Bleisure 10 · Balikbayan/VFR 13 ·
   Pilgrimage 33** — exactly the persona ordering, with nothing in the waterfall putting it there. Two
   uses: a **candidate Tier-A validation anchor** (strengthens Plan B), and the missing input for
   Corporate-vs-Bleisure separation. Caveat: available only for round trips, itself a rule bit, so it needs
   the same per-pair admissibility treatment as `dest_region`/`issue_country`/`channel`.
3. **Upgrade is derivable and unused.** `SoldOperatingCabinClass` is **0% null** across all 38.1M coupons.
   Sold ≠ operated cabin on **1.022%** of coupons: Y→W 210,968 · Y→J 133,819 · W→J 24,274 (**~369k
   upgrades**) against **~20.4k downgrades** — roughly **18:1**. `SoldBookingClass` ≠ `BookingClass` on
   0.825%. **Caveat that must travel with it: we cannot separate a paid/bid upgrade from an involuntary
   operational one**, so it measures "flew better than they bought", not willingness to pay.
4. **Digital Nomad is absent from the real-data waterfall, and our recorded reason is wrong.** The
   delivered taxonomy is **9 named segments + Unassigned**, not 10 — Digital Nomad exists only in the
   superseded 30k prototype. `src/export_powerbi.py` records it as "blocked on the missing `Loyalty status`
   field"; that is incorrect — the prototype rule never used loyalty, and `methodology.md`'s own gap table
   attributes it to **length of stay**, which item 2 shows is derivable. Sizing the candidate population:
   **725,748 round-trip bookings with 31+ night stays (3.2% of the book)**, of which 66.3% currently sit in
   Balikbayan/VFR, 11.1% Budget/Adventure, 10.7% Unassigned. A narrower definition (long-stay +
   international + economy + non-group + web/OTA) gives **207,512 (0.91%)** — **right at the ~1% detection
   floor from Stage V3**, which explains why clustering was never going to surface it and why a rule or an
   SME definition is the correct instrument. **Recommendation: do not add the rule unilaterally** — take
   the sizing to the SMEs alongside the Unassigned question.
**Source:** our analysis — DuckDB probes over `data/interim/pal_clean/`, `pal_parquet/` and
`pal_features_booking.parquet`; written up in `docs/pipeline-study-guide.md` §5.1.

#### 2026-08-12 — Internal confidence of a deterministic labeller is measurable, and Corporate is the weakest cell
**Domain:** Clustering / Methodology
"How strong are the clusters?" has **two** answers for a rule-based labeller, and conflating them is the
error to avoid. **External validity** (is the label *correct*?) needs evidence outside the rules — that is
Stages V1–V4, and ultimately SME ground truth. **Internal confidence** (how *determined* is the label by
the rule set itself?) is computable today, exactly, on the full 22.9M bookings. Three measures, all run on
`data/interim/pal_features_booking.parquet` with no sampling:
1. **Rule competition** — how many of the 10 branch predicates a booking satisfies. Overall **66.5% match
   exactly one rule · 24.0% match two or more · 9.6% match none** (that last is `Unassigned`, by
   definition). Per segment the spread is large: Budget/Adventure 100% uncontested (but it is the terminal
   catch-all, so this is near-tautological), Premium Bleisure 95.5%, Balikbayan/VFR 89.2% — versus
   **Corporate at 6.4% uncontested with 25.6% matching three or more rules, mean 2.20**. **The segment
   with the highest misclassification penalty (×10) is the one whose label depends most on our chosen
   priority order** — so it is the first boundary to put to the SMEs.
2. **Runner-up label** — what the booking would be called one priority step lower. **84.1% of Last-Minute
   would be Budget/Adventure**, which says Last-Minute is a *behavioural overlay cutting across* the
   taxonomy rather than a peer of the other nine; worth deciding with PAL whether it is a segment or a
   flag. Also: Corporate → Budget/Adventure 28.0%, Corporate → OFW/Migrant 19.7%.
3. **Boundary fragility** — label flips when one threshold moves one notch. **The Corporate `lead_days<=7`
   cut is nearly irrelevant (0.15–0.17% of the book flips)** — the `corp_channel` branch carries that
   segment, which is reassuring since channel is an identity, not an arbitrary number. By contrast the
   **Last-Minute 3-day cut is the most consequential arbitrary number in the model**: widening it to 7 days
   relabels **8.57% (1.96M bookings)**. **Premium Bleisure is the most fragile segment** — moving the value
   cut from tier ≤4 to ≤5 loses 18.6% of it to the OFW/Balikbayan branches, because Premium Economy then
   counts as "economy" there.
**Two implications.** (a) Ship a **`SegmentConfidence`** column (High = 1 rule and not near a threshold ·
Medium = 1 rule near a threshold or 2 rules · Low = 3+ rules · None = Unassigned) through `features_real.py`
into the fact table, so BI can restrict campaign lists to high-confidence members. (b) It is a **sampling
frame for the SME ask** — spend the ~1,000 labels on Low/Medium bookings at contested boundaries
(Corporate ↔ Budget/Adventure, OFW ↔ Balikbayan) rather than uniformly at random.
**Caveat that must travel with these numbers:** they measure how determined a label is, **not whether it is
right**. A booking can be 100% uncontested and still be in the wrong segment if the rule itself is wrong.
**Source:** our analysis — full-population DuckDB probe over `pal_features_booking.parquet`; written up in
`docs/pipeline-study-guide.md` §8.2.

#### 2026-08-12 — Correction: `DaysBeforeMonthEnd` has 12 distinct values at 91.45% `-7`, not 8 at 99.7%
**Domain:** Data & Features
Re-verifying the 2026-07-27 entry ahead of a stakeholder presentation found two wrong figures that had
propagated into four documents (`methodology.md` v0.9 changelog, `knowledge-base.md`,
`stakeholder-report.md`, `tuesday-punchlist.md`). Measured on all **38,116,260** raw Parquet rows: the field
takes **12 distinct values** (`-7, 11, 42, 72, 103, 133, 164, 195, 223, 254, 284, 315`) and **91.45%** of
rows carry `-7` — not "8 distinct values, 99.7%". The original entry's own enumeration listed 12 values, so
the "8" contradicted its own text. **The conclusion is unchanged and the load-bearing check re-confirms
cleanly: every one of the 37 departure months carries exactly one distinct value (max = min = 1), while each
departure month is sold across 12.9 issue months on average.** The field remains departure-month metadata
against a single extract date, carries zero booking-timing information, and cannot anchor LY-vs-CY pickup;
use `LeadTimeDays`, or request repeated dated extracts. **Lesson:** derived summary statistics quoted in prose
drift from the data they describe — re-run the probe before quoting a number in a deliverable.
**Source:** our analysis — DuckDB probe over `data/interim/pal_parquet/` and `data/interim/pal_clean/`.

#### 2026-07-31 — Per-segment scorecard table for BI: the three traps that make a handoff silently wrong
**Domain:** Data & Features
Added `model/scorecard_segment_month.csv` to Stage X (segment × travel month, 1,835 rows, 127 KB) so a
per-segment scorecard never aggregates 20M rows. Three design decisions, each fixing a failure mode that
produces a *plausible but wrong* report rather than a visible error:
1. **No stored percentages, ever.** A `share_of_bookings` column is correct only for the filter context
   that computed it — slice the report to one region and it is silently wrong with nothing broken on
   screen. Shares must be DAX measures over additive columns. Same reason `Bookings` stays
   `sum(IsPrimaryCoupon)` and never a stored `DISTINCTCOUNT`: a pre-aggregated distinct count is not
   re-aggregatable.
2. **NULL booleans are a data-loss trap in BI filter columns.** `IsRefund` and `IsInternational` were
   NULL on a small number of coupons (167 scorecard rows / ~542 bookings, all revenue-missing). In Power
   BI, `IsRefund = FALSE` treats NULL as *not matching*, so those rows vanish from the scorecard and
   totals quietly stop reconciling. All flags are now **coalesced to FALSE on write**, with `RevMissing`
   carried explicitly so the affected rows stay identifiable instead of disguised as clean.
3. **The export now asserts the scorecard reconciles** (coupons + bookings vs the fact table) and fails
   the build otherwise. A scorecard that does not tie is worse than no scorecard, and the BI developer
   should not be the one to discover it.
**Also recorded:** the export ships **no accuracy or recall KPI on purpose**, and the guide says *do not
build an accuracy gauge* — per-segment recall needs SME ground truth, and every figure computable today
is circular. `PenaltyWeight` / `RevenueAtRiskPerError` support a legitimate *cost-weighted risk* tile
instead.
**Source:** our analysis — `src/export_powerbi.py` `build_scorecard()`, `docs/powerbi-guide.md` §3a,
`docs/methodology.md` v1.5.

#### 2026-07-31 — Prototype-track references removed from the docs; results **withdrawn, not relabelled**
**Domain:** Project Decision
All references to prototyping on a synthetic dataset were removed from the documentation surface
(`docs/*.md`, `README.md`, `CLAUDE.md`, `data/labels/README.md`). Two rules governed the sweep, and they
are the reusable part:
1. **A finding is removed together with its provenance, never separated from it.** Stripping the word
   "synthetic" while keeping the number would silently re-attribute the result to real PAL data. This was
   not hypothetical: **§6 POC Results carried a full scorecard — 77.7% overall accuracy, 100% Corporate
   recall, ₱18.09M estimated revenue risk — all produced on prototype data.** Relabelling it would have
   published prototype figures as real-data performance. The section is now marked **withdrawn** with a
   pointer to where real numbers live, and the same treatment was applied to the two learning-log entries
   that were purely prototype-data results. Nothing evidential was lost: the real extract reproduces the
   only conclusion that mattered (no natural clusters) across ten methods with a stated detection bound.
2. **"Synthetic" had two unrelated meanings in these docs, and only one was in scope.** The other is
   Stage V3 detection power, where segments of known prevalence are **planted into the real population**
   to measure our own sensitivity. That is real-data methodology, not prototyping — removing it would
   have destroyed the only thing that makes the null result falsifiable. Those passages now say
   **"planted"** rather than "synthetic" so the two can never be conflated again.
Superseded material is reduced to a stub in `docs/methodology.md` §Prior Prototype Track and `README.md`,
recording that an earlier track existed without characterising its data. `docs/v3-prototype-findings.md`
was removed via `git rm` (recoverable from history). **Code filenames and `data/raw/` inputs were left
untouched** — the prototype scripts still run; they are simply not quoted in any deliverable.
**Source:** project decision, 31 Jul 2026.

#### 2026-07-31 — Persona cards belong in the **model output**, not in a document — and the column split is what makes them safe
**Domain:** Project Decision
Personas written into a report are a snapshot that starts rotting immediately and cannot respond to a
slicer. Shipping them as `model/dim_segment.csv` from Stage X (`src/export_powerbi.py`,
`build_dim_segment()`) fixes both: related to the fact table on `Segment` = `CustomerSegment`, a card
visual bound to it **cross-filters with every other visual**, so the behaviour numbers move when someone
slices to a route or a quarter. Three design decisions worth keeping:
- **Behaviour is recomputed every build, never hardcoded** — a card claiming "books 48 days ahead" cannot
  outlive the number that justified it.
- **Measured at booking grain, not coupon grain.** Coupon grain would weight every booking by its leg
  count and silently flatter multi-coupon segments (Balikbayan/VFR 2.61 coupons vs Last-Minute 1.32).
- **Columns are split into measured / editorial / governance**, because a persona card mixes evidence with
  inference and the reader cannot otherwise tell which is which. Motivation (`WhyTheyFly`) is *not*
  measurable from a booking extract and is labelled as inference in the schema itself.
`Trust` + `DataCaveat` ship **as columns** rather than as report footnotes: persona cards persuade, so the
caveat has to be structurally attached to the thing that misleads. The failure mode being defended
against is concrete — a card reading *"Mabuhay Loyalist · 0.03%"* invites "the loyalty programme is
irrelevant" when the truth is "we cannot see it". `SegmentColorHex` carries `pal_colors.py` into BI so
Power BI, the Python figures and the slide deck colour a segment identically.
**Source:** project decision, 31 Jul 2026 — `src/export_powerbi.py`, `docs/powerbi-guide.md` §3b,
`docs/methodology.md` v1.4.

#### 2026-07-31 — Persona cards, measured: the per-segment behavioural signatures that make the taxonomy legible (and three that indict it)
**Domain:** Data & Features
Built data-backed persona cards for all ten segments from `pal_features_booking.parquet` (median lead
days, round-trip / international / premium / connecting rates, median *and* mean revenue, top-3 dest
regions, modal channel + issue country). Five signatures are strong enough to quote as the segment's
identity, and they were **not** designed in — they fell out of the rules:
- **Balikbayan/VFR books furthest ahead of anyone (median 48 days), has the most complex itinerary
  (2.61 coupons) and is 100% round-trip.** OFW/Migrant, its contested neighbour, is **5.9% round-trip
  at median 14 days lead.** So although the *rule* separates them on one bit, their measured behaviour
  differs on lead time and itinerary complexity too — a genuinely useful argument that the boundary is
  not purely an artefact, and the first thing to put in front of an SME.
- **Pilgrimage connects 95.2% of the time** — highest in the field (no direct MNL–JED), which makes
  connection reliability, not price, its service priority.
- **Corporate is 50.7% domestic** at median 6 days lead — the "corporate = international" assumption is
  wrong on this data.
- **Premium Bleisure earns ₱1,504/booking, 2.4× the next segment, on 2.1% of volume** — headcount share
  is a bad priority proxy.
- **Mabuhay Loyalist's median revenue is ₱22** (taxes on an award). The cleanest demonstration in the
  project that *revenue ≠ value*, and it must be stated whenever that 0.03% share is shown, or the
  reader concludes the loyalty programme is irrelevant rather than **invisible to us**.

Two cards indict the taxonomy rather than describe it, and both are now written as asks:
**`Unassigned` is not junk** — ₱360 mean (above OFW/Migrant), 18.6% premium, 81.4% international, i.e.
2.19M *valuable* bookings falling through the rules, mostly PH-issued outbound economy; and **`Family`
means "ticketed as a group", not "is a family"** (`Pax Count` is always 1 by design), so it is
certainly under-counted. **Presentation caution recorded:** persona cards are persuasive, so every
⚠️/🚨 caveat must travel with its card when reused in a deck.
**Source:** our analysis — DuckDB aggregation over `data/interim/pal_features_booking.parquet`;
written up in `docs/stakeholder-report.md` §8.

#### 2026-07-31 — SME constraint asks are now **two typed files**, and the hard/soft split is the useful distinction
**Domain:** Project Decision
The SME ask was previously one undifferentiated request for "business rules". Splitting it into two
files with different semantics is what made it answerable:
- **`data/constraints/hard_constraints.csv`** — statements of *impossibility*, typed by
  `verdict ∈ {must_be, cannot_be, narrow_to}` + `confidence ∈ {certain, likely}`. These are the rules
  SMEs are most confident about, and they shrink the annotator's decision space from 10 segments to 2–3
  before any judgement call — the mechanism `business-requirements.md` FR-21/FR-24 (Negative Learning)
  always intended.
- **`data/constraints/soft_constraints.csv`** — *tendencies*, typed by `leans_toward` /
  `leans_away_from` / `strength`. Their second job matters as much as their first: they reveal **which
  boundaries PAL itself considers soft**, i.e. where the deliverable should report ambiguity rather
  than force a confident label — which is the honest output for a continuum.
Both ship **pre-filled with our own guesses as worked examples** (7 rows each), because a rule we
invented and an SME confirmed is worth far more than a rule we invented alone, and a blank template
gets a blank response. CSV chosen deliberately (opens in Excel, `condition` accepts near-plain
language); prose in an email is accepted and transcribed by us, so format is never the blocker.
**Where a soft constraint contradicts the data, that disagreement is the finding** — reported back, not
silently overridden in either direction. Complementary to `data/labels/sme_sample.csv`: constraints
encode what SMEs know in general, labels settle the cases where the general rules run out.
**Source:** project decision, 31 Jul 2026 — `data/constraints/README.md`,
`docs/stakeholder-report.md` §7.

#### 2026-07-31 — The asymmetric cost matrix needs a *same-accuracy* worked example to land with non-technical stakeholders
**Domain:** Project Decision
Explaining the penalty matrix by describing it does not work; explaining it by **holding accuracy
constant** does. The canonical example now used in stakeholder material: 1,000 bookings at true
prevalence (44 Corporate, 394 Budget/Adventure), two models **both at exactly 90% accuracy** — Model A
misses 20 Corporate + 80 Budget, Model B misses 2 Corporate + 98 Budget. Weighted by the FR-28 revenue
figures (Corporate ₱40k, Budget ₱4k): **₱1,120,000 vs ₱472,000 revenue at risk — a 2.4× business
difference that plain accuracy cannot see** (Corporate recall 54.5% vs 95.5%, i.e. A fails the NFR-01
≥91% target and B passes). The pedagogic point is that the *placement* of error, not its rate, is the
business quantity. Paired framing that carries it: over-serving a budget passenger costs a courtesy
upgrade; under-serving a Corporate passenger costs ~₱40,000 — the matrix exists because those are not
the same mistake. **Caveat that must travel with the calc:** the metric is built and tested, but
"correct" is still defined as "matches our own rules", so it is machinery awaiting an answer key.
**Source:** our analysis — `docs/stakeholder-report.md` §6; weights from `src/dashboard.py`
(`PENALTY_10`, `REV_LOSS_10`), targets from `business-requirements.md` FR-28 / NFR-01.

#### 2026-07-30 — **`age_known` was leaking a rule field through its *missingness*, and it inflated most of the construct-validity matrix**
**Domain:** Clustering / Methodology
The circularity contract (`src/validation_anchors.py`) declared
`TIER_A = (age, age_known, dep_month, n_bookings)` **"independent of every rule field — always usable, so a
TIER_A-only matrix is directly comparable across all pairs."** That claim was false for `age_known`, and the
error propagated into every number the strict matrix produced.

**The mechanism — a leak no name-based guard can see.** International travel captures passport data;
domestic travel does not. So on the full non-sea-crew population:

| | bookings | `age_known` |
|---|---|---|
| domestic | 12,830,158 | **0.86%** |
| international | 8,969,039 | **87.62%** |

`age_known` is therefore very nearly a *copy* of **`is_international`**, which **is** a rule field — it gates
the `OFW/Migrant`, `Balikbayan/VFR` and `Premium Bleisure` branches of the waterfall. And `age` inherits the
same leak, because a tree model reads *present-vs-NaN* directly and that pattern **is** the rule bit. The
existing guard checked the three anchors that are *coarsenings of values* (`dest_region`→`is_domestic`,
`issue_country`→`foreign_issue`, `channel`→`corp_channel`) and missed the one that leaks through **the
missingness pattern of a field whose values are genuinely innocent**.

**Measured impact — the published positive controls were mostly the leak:**

| pair | published `auc_strict` | age anchors withheld | `age_known` gap |
|---|---|---|---|
| Premium Bleisure vs Budget/Adventure | **0.948** | **0.553** | 0.85 |
| OFW/Migrant vs Budget/Adventure | 0.942 | 0.579 | 0.84 |
| Unassigned vs Budget/Adventure | 0.890 | 0.556 | 0.71 |
| Unassigned vs Last-Minute | 0.833 | 0.577 | 0.63 |
| Corporate vs Budget/Adventure | 0.846 | 0.635 | 0.43 |
| Pilgrimage vs Balikbayan/VFR | 0.768 | 0.642 | 0.21 (marginal) |
| **OFW/Migrant vs Balikbayan/VFR** | **0.617** | 0.550 | **0.04 → keeps age** |

**What this does and does not overturn:**

1. **The headline OFW-vs-Balikbayan result stands.** Both sides are foreign-issue international — `age_known`
   **0.8519 vs 0.8918**, a gap of 4 pp, far inside the 0.20 tolerance — so the age anchors are legitimately
   admissible there and the 0.608/0.617 figure is unaffected. The weakest-boundary *number* survives.
2. **But "the weakest boundary of all 45" does not.** After correction, several domestic-vs-international
   pairs sit *below* 0.617 (0.553, 0.556, 0.579). They are low because **their evidence was withheld**, not
   because those segments are alike — so they are not comparable to 0.617 either. **The ranked pair table is
   no longer a league table** and must not be read as one. Compare only cells sharing an
   `anchors_withheld` set.
3. **The strict matrix has almost no power left.** Only `dep_month` and `n_bookings` are *unconditionally*
   independent of the rules, and on those two a pair we are confident genuinely differs (Premium Bleisure vs
   Budget/Adventure) scores **0.553** against a negative control of 0.50. Per-pair adaptive admissibility is
   therefore **not a nicety, it is the only version with usable power** — the report now says so, and
   positive controls are reported on *both* feature sets because one ceiling cannot calibrate both.
4. **The negative control never would have caught this.** A random half-split *within* one segment has no
   real difference to find, so it correctly returned 0.485–0.515 the whole time. **A passing negative control
   bounds harness noise; it says nothing about whether an admitted feature is independent of the labels.**
   Those are different failure modes and need different tests.

**The transferable lesson: audit missingness, not just values.** A feature can be perfectly innocent in what
it records and still encode a label-defining field in *whether* it was recorded. The guard is now
`ANCHOR_LEAKS[age] = ANCHOR_LEAKS[age_known] = ("is_international",)`, and the general rule for this project
is that **every admissible anchor must be checked for both a value leak and a missingness leak** before it
is trusted.

**Also found, incidentally:** `Pilgrimage` is only **79.5% international**, not 100%. The `pilgrimage` flag
fires on `trip_dest IN ('JED','MED')` while `is_domestic = bool_and(dom_coupon)`, so a pilgrimage booking
whose coupons in this extract are only the *domestic feeder legs* (e.g. CEB→MNL) reads as domestic. That
0.205 gap is what marginally trips the tolerance for `Pilgrimage vs Balikbayan/VFR`.

**Recommended follow-up (not built):** instead of withholding a leaky anchor outright, **restrict the pair to
rows where the rule bit is constant** and use the anchor there — the same matched-comparison logic the
OFW/Balikbayan section already applies within `issue_country`. That recovers power without leaking. Rejected
for `age` on domestic-vs-international pairs specifically, because matching on `age_known = 1` retains only
0.86% of the domestic side.

**Source:** our analysis — direct measurement on `data/interim/pal_features_booking.parquet`;
`src/validation_anchors.py`, `src/validate_construct.py`.

---

#### 2026-07-29 — Out-of-time stability: the segmentation survives a 12-month step, and the extract is **departure-filtered** (which dictates every temporal design)
**Domain:** Clustering / Methodology
`src/validate_temporal.py` (Plan B item B4) splits the extract in time and re-asks every stability
question. Everything validated before this was a **photograph** — one pooled snapshot — so a segment that
existed only because of one period's booking conditions would have passed every earlier test.

**First, a data-structure finding that governs any future temporal work.** The extract is filtered on
**departure date (2024-05-01 → 2027-05-31), not on issuance.** That truncates the issuance axis at *both*
ends, and ignoring it would manufacture findings rather than reveal them:
- **Left:** a booking issued before the travel window opens appears **only if its lead time was long
  enough to reach it**. Issuance before 2024-05 is a long-lead-only sample — mean lead **105 days** in the
  excluded region vs **38** inside it (2023Q3 issuance: 277 days). Included, it would show a spectacular
  "collapse in lead time" that is **pure selection**.
- **Right:** for issue date `d` the longest observable lead is `2027-05-31 − d`. That ceiling drops below
  the modelled 365-day clip after ~2026-06, so the last ~3 months of issuance are missing their long-lead
  tail (min ceiling **315 days**).
- **Therefore the windows are `2024-05-01→2025-04-30` vs `2025-05-01→2026-04-30`** — two adjacent
  12-month windows (9.77M vs 10.08M bookings, 86% of the extract), each covering all twelve calendar
  months so seasonality cannot masquerade as drift. **Not** "2024–25 vs 2026–27": issuance never reaches
  2027 at all.

**Five findings:**

1. **Segment sizes hold.** Share TVD **1.93 pp** across all ten segments on *full-population* counts —
   you would have to move 1.93% of bookings to turn one year's mix into the other's. Largest single move
   `Budget/Adventure` −1.49 pp; `OFW/Migrant` +1.40 pp (+8.7% relative).
2. **Revenue mix is the weaker leg — TVD 3.21 pp, materially worse than share's 1.93.** `Balikbayan/VFR`
   revenue share fell **29.35% → 26.64%** while its *headcount* share barely moved (−0.19 pp). Revenue is
   what the commercial team acts on, so **a segment holding its size is not evidence its value held**.
   Quote both or neither.
3. **The populations are *mildly* distinguishable — adversarial AUC 0.61**, against a negative control at
   **0.492/0.497** (random halves of one window) and a positive control at **0.994** (domestic vs
   international, region withheld). So there is real population shift that the segment sizes absorbed.
   The two control rails are what make 0.61 readable at all.
4. **Composition is stable where the volume is.** 7 of 10 segments show negligible-or-small profile drift
   and carry **98.2% of bookings**. All three moderate-or-larger drifters are the *smallest* segments —
   `Mabuhay Loyalist` (0.03%, SMD 2.448), `Pilgrimage` (0.20%, 0.458), `Family` (1.57%, 0.283) — totalling
   1.8%. **Reported as unresolved, not as behaviour change.** This only became visible because profile
   drift uses a **per-segment stratified draw**: a uniform 30k sample gives Mabuhay ~9 rows, so the
   segments whose stability is least known would have come back `n/a`.
5. **A model fitted a year earlier transfers essentially for free.** GMM(full) transfer ARI **0.763**
   against a **within-window control of 0.746** — ratio **1.02**; LCA 0.729 vs 0.761 (0.96). The control
   is the **ceiling, not a baseline**: the same method fitted on two halves of the *earlier* window, both
   scoring the later one, with no time involved. The shortfall below it — not the raw ARI — is what a year
   costs, and here it is ~zero. Raw ARIs sit well below 1.0 for both, which is the continuum again: these
   methods do not reproduce themselves exactly on *any* split, which is precisely why the ratio is the
   readable number.

**The F/G coding change did not break anything.** `is_award` **is** the Mabuhay rule and its source coding
flipped at 2026-04-01, inside the later window. Monthly award rate runs 0.0036–0.0798% with **no step at
the boundary**, and the highest month in the series is *pre*-change — so `clean_real.py`'s date-aware rule
is preserving semantics. But month-to-month swing exceeds the pre/post difference on ~200 bookings a
month, which is the direct reason Mabuhay's large SMD is reported as noise rather than drift.

**Method note worth reusing:** `flown_any` and `refund_any` are **excluded from every comparison** here.
They run ~100% for early issuance and **30.7%** for 2026Q3 — right-censoring (bookings that have not flown
yet), not a behaviour change. Comparing them across windows would produce a large, wholly artefactual
difference. Same forward-book boundary as the 2026-07-27 fake-cliff finding.
**Source:** our analysis — `outputs/validate_temporal/summary.md`, `src/validate_temporal.py`; plan in
`docs/recommendations-plan.md` §Plan B item B4.

---

#### 2026-07-29 — Detection power: the null is now *bounded*, we are blind below ~1% prevalence, and the H0 component count is not a usable statistic
**Domain:** Clustering / Methodology
`src/detection_power.py` closes the largest hole in the project's story. Every prior diagnostic returned
"no natural clusters", and none of them could answer **"or are your methods blind?"** This plants segments
of known prevalence and known distinctness — **appended** to the real 20k base, never edited in place, so
the counterfactual is *"if PAL's book also contained this group"* — and re-fits the deployable panel
(GMM(full) · LCA · KMeans · SVD+KMeans) at k=10. Distinctness is one knob `w`: each planted row moves a
fraction `w` toward an archetype, so `w=0` is an unmodified random subset and `w=1` a point mass.

**The floors (majority of the 12 method × archetype combinations — see the methodology note below):**

| prevalence | majority detects from | distinctness there | unanimous from |
|---|---|---|---|
| 0.5% | **never** | — | never |
| 1% | **never** | — | never |
| 2% | `w` ≥ 0.75 | ≈0.337 | never |
| 5% | `w` ≥ 0.50 | ≈0.227 | `w` ≥ 0.75 (≈0.40) |
| 10% | `w` ≥ 0.35 | ≈0.128 | `w` ≥ 0.75 (≈0.43) |

**Five things learned:**

1. **The null is now bounded and falsifiable, which is a much stronger deliverable than a bare null.**
   The claim becomes: *no segment exists in these features at or above **2% of bookings** with distinctness
   at or above **≈0.34**, because a planted one at that size and distinctness is recovered by a majority of
   the panel.* The earlier "no clusters" findings are therefore evidence about **PAL's data**, not about our
   instruments.
2. **But we are effectively blind below ~1% prevalence, at *any* distinctness — state this, don't bury it.**
   Not one prevalence at or below 1% reached majority detection even at `w=1` (a literal point mass). 1% of
   22.9M bookings is **~229k bookings** — a commercially meaningful group PAL could still be missing. This
   limitation must travel in the same breath as the continuum finding.
3. **Methodological rule established: never quote the single most sensitive cell.** With 12 combinations per
   cell, one clearing threshold is what the luckiest alignment of an archetype direction and a method's
   inductive bias produces anyway. The naive read of this grid would have claimed detection at **0.502%
   prevalence and 0.059 distinctness** — while groups as distinct as **0.555** were *missed* elsewhere in the
   same grid. Those two numbers cannot both be a floor. All floors are majority-rule.
4. **The floors are direction-independent, and the random control is what proves it.** Detection rate by
   archetype: `late_yield` 22% (27/120) · `planned_group` 28% · **`random_dir` 29%** — spread 7pp. The
   direction with no business story at all sits inside the range set by the two plausible ones, so the
   floors are a property of the method panel, not of directions we guessed well. Per-method: **LCA is the
   most sensitive detector, SVD+KMeans the weakest** (needs 5% prevalence before it finds anything).
5. **Failure mode is *smearing*, not missing.** Averaged at `w=1`, recall hits **1.00** for every method
   while precision lags (LCA 0.77, GMM 0.73, KMeans 0.58, **SVD+KMeans 0.39**). A faint planted group is
   found *and then absorbed into a much larger cluster* — so it would be present in the labels but useless
   for targeting. Recall alone would have badly overstated detection.

**⚠️ A defect in one of our own instruments — this one qualifies an earlier entry.** The `w=0` controls
re-ran H0 persistent homology on unchanged data 100 times, where the answer should be identical every time.
`n_significant_H0` returned **median 1, 75th percentile 3, maximum 120** across 100 draws of 1,200 rows
(60% of draws gave 1). A statistic ranging 1→120 on unchanged data **cannot screen for anything**, so this
grid draws no detection conclusion from it. The instability is the **gap heuristic** (`argmax` over
differences in sorted bar lengths, which jumps whenever two adjacent bars are close), *not* the homology.
Consequence for the 2026-07-28 entry below: its "**1 significant H0 component**" was **one draw** of this
noisy statistic. **1 is the modal and median value, so the continuum reading still holds** — but it should be
reported as the centre of a noisy distribution, never as a clean measurement. The **H1 loop-noise ratio and
the barcode's shape are the robust parts** of that analysis; the integer component count is not.

**Also:** the floors are **optimistic bounds, not guarantees** — a planted group is internally coherent in a
way a real segment may not be, so a messier real segment of the same size and distinctness would be *harder*
to find. And `planted_sil` is **not** comparable to the stress test's 0.381 ceiling: it is measured on a
stratified sample (planted rows over-represented) for one group against the rest, where 0.381 is a
full-partition silhouette on a uniform sample. Do not put them in the same sentence.
**Source:** our analysis — `outputs/detection_power/summary.md`, `src/detection_power.py`; plan in
`docs/recommendations-plan.md` §Plan B item B5.

---

#### 2026-07-28 — Plan B delivered: the segments *are* non-circularly validated, and OFW/Balikbayan is the weakest boundary in the taxonomy (not a spurious one)
**Domain:** Clustering / Methodology
`src/validate_construct.py` + `src/validate_criterion.py` (library: `src/validation_anchors.py`) ran the first
**non-circular** validation this project has: classifiers given *only* fields the proxy waterfall never
consumes. Validation is therefore **no longer blocked on SME labels**.

**The harness validated itself first.** Negative controls — each segment split randomly in half, so there is
nothing to find — landed at **0.494–0.506** across six segments. Positive controls (strict anchors) landed at
**0.770–0.945**. That calibrates the scale: on this data a *real* difference reads 0.77–0.95, and 0.50 is the
floor.

**Segment-distinguishability matrix (45 pairs, held-out AUC, Tier-A anchors):**

| Boundary | strict | adaptive | reading |
|---|---|---|---|
| **Balikbayan/VFR vs OFW/Migrant** | **0.608** | 0.714 | **weakest of all 45** |
| Last-Minute vs Budget/Adventure | 0.645 | 0.685 | 2nd weakest |
| Premium Bleisure vs Balikbayan/VFR | 0.678 | 0.754 | weak |
| … | | | |
| Balikbayan/VFR vs Budget/Adventure | 0.965 | 0.976 | strongest |

**The OFW/Balikbayan verdict is more interesting than the hypothesis it replaced.** The preliminary probe
suggested "one population, split by trip type". The controlled test says **two populations with a genuine but
weak difference** — not spurious, not strong:
- Matched **within** `issue_country` (holding origin market constant, `issue_country` withheld) the split
  survives in *every* country tested: **AUC 0.622–0.721** across CN/US/CA/JP/QA/NZ/AE/HK/KR/SG. So the
  difference is not geographic — the earlier country-mix reading was too coarse.
- **Seasonality carries most of it.** Base-rate-normalised departure-month index (1.0 = base rate):
  December is **1.174 for Balikbayan vs 0.826 for OFW** — a sharp, opposite-direction signal from rules that
  read no month at all. August reverses it (0.923 vs 1.077). Every other month sits at ≈1.0.
- **Recommendation: keep them separate but treat the boundary as soft** — and consider reporting an
  "Overseas Filipino" super-segment with trip type as a sub-dimension. **Do not merge** on this evidence.

**`Unassigned` (2.19M) is a coherent missing population, not a residue.** It is clearly distinct from 8 of 9
named segments (AUC 0.821–0.986) and only weakly separable from Corporate (0.682) — corroborating the
documented taxonomy gap #4 (outbound PH-issued international economy, intentionally left unassigned). Worth a
named segment rather than a bucket.

**Criterion validity — the segmentation is a lossy re-encoding for the outcomes that matter.** Against
outcomes no rule consumes: `flown_any` **signal retained 0.324**, incremental value **+0.002**;
`rebook_180d` **0.555**, **+0.002**. It carries a third to a half of the achievable signal and adds
essentially **nothing** beyond the 11 raw features. Valuable for communication and targeting; **not** a source
of new predictive signal, and must not be sold as one.

**Two methodological findings worth keeping:**
1. **`signal_retained` can exceed 1.0 legitimately** — `refund_any` hit **2.944** (segment-only AUC 0.822 vs
   features-only 0.609). The segment label is *not* a compression of the 11 clustering features: the waterfall
   also reads `sea_crew`, `is_award`, `pilgrimage`, `any_premium`, `any_business`, `is_domestic`,
   `is_international`, **none of which the clustering ever saw**. Those rule inputs carry real outcome signal.
   *But that row is flagged `unstable`* — features+segment (0.541) scored *below* segment alone, which is
   impossible with real signal, so with 347 events in 300k it is rare-event overfitting. Indicative only.
2. **Semantic circularity defeats a name-based guard.** Three anchors that pass any field-name check are
   finer-grained versions of rule fields: `dest_region == 'Domestic'` **is** `is_domestic`,
   `issue_country != 'PH'` **is** `foreign_issue`, `channel IN ('TMC','Corporate Web Portal')` **is**
   `corp_channel`. Admitting them produced **AUC ≈ 1.0 for nearly every pair** on the first run — a result
   that proves only that the rules were applied consistently. Fixed by deciding admissibility **per
   comparison**: an anchor is used only where the rule bit it encodes is not the boundary under test.
   Anyone extending this must keep that discipline.

**Source:** our analysis — `outputs/validate_construct/summary.md`, `outputs/validate_criterion/summary.md`,
`src/validation_anchors.py`; plan in `docs/recommendations-plan.md` §Plan B.

---

#### 2026-07-28 — Non-circular validation *is* possible without SME labels — and the first probe questions the OFW / Balikbayan split
> **Partly superseded the same day** by the controlled test above: the country-mix reading here was too
> coarse. Holding `issue_country` constant, the OFW/Balikbayan split *does* survive (AUC 0.62–0.72 in every
> country) — weakly, but it is not spurious. The audit and MNAR findings below stand.
**Domain:** Data & Features
With internal SME labelling possibly unavailable, we audited which fields the proxy waterfall
(`src/features_real.py`) actually consumes, to find anchors that can validate it non-circularly.

**The circularity audit changed the design.** The rules consume `is_award`, `corp_channel`, `any_business`,
`lead_days`, `pilgrimage`, `sea_crew`, `foreign_issue`, `is_international`, `max_tier`, `round_trip`,
`any_premium`, `is_group`, `is_domestic`. So three fields that *look* like independent markers are
**circular and unusable**: **`sea_crew`** (it *is* the OFW rule), **`is_award`** (the Mabuhay rule),
**`pilgrimage`** (the Pilgrimage rule). Genuinely independent anchors that survive: `refund_any`,
`flown_any`, `age`/`age_known`, `issue_country` *identity*, `channel` *identity*, `min_tier`,
`n_directions`, route identity, and — importantly — **`dep_month`, since the rules use no month at all.**

**Probe results (unconditioned marginals, 22.9M bookings):**
- **Outcomes carry signal:** refund rate spans 0.00% (Family) → **0.45%** (Balikbayan); flown 91.7% →
  99.9% (Last-Minute). Neither field is used by the rules.
- **Seasonality is a working external anchor:** **Balikbayan/VFR peaks in December** — the Philippine
  Christmas homecoming — predicted from domain knowledge and recovered from rules that see no month.
  Pilgrimage is the most seasonal segment (peak/trough **5.39**).
- **⚠️ The OFW vs Balikbayan split is not corroborated by geography.** Those two segments (**6.8M
  bookings, 30% of the base**) are separated by a *single bit* — `round_trip` (one-way → OFW, round-trip →
  Balikbayan). But their `issue_country` mixes are near-identical, both dominated by US/SG/JP/HK, with
  **no Gulf concentration in OFW**. Seasonality partly disagrees (Balikbayan Dec vs OFW May). **Live
  hypothesis: one population — overseas Filipinos — segmented by trip type, not two customer types.**
  Merging them would consolidate two of the four largest segments. Needs a controlled test before acting.

**Two methodological traps found:** (a) **`age` is missing-not-at-random** — `age_known` runs from **0.8%**
(Budget/Adventure) to **89.2%** (Balikbayan), so raw median-age comparisons are across different
subpopulations (Budget/Adventure's "39" rests on 0.8% of 9M rows); model the missingness or don't use it.
(b) **Most segments peak in May**, which is a base rate, so monthly peaks must be base-rate normalised —
Balikbayan's December peak is meaningful *because* it deviates from that base rate.

**Also learned:** the strongest available substitute for row-level labels is **profile-level face validity** —
ten one-page segment profiles reviewed in ~1 hour by one person, roughly two orders of magnitude cheaper than
1,000 row labels. And **detection-power testing by structure injection** converts "we found no clusters" into
"no clusters exist above X% prevalence and Y separation", which needs no external input at all.
**Source:** our analysis — probe queries against `pal_features_booking.parquet`; plan in
`docs/recommendations-plan.md` §Plan B. Results are unconditioned marginals — controlled tests are B1/B2.

---

#### 2026-07-28 — Ten-method stress test: GMM overtakes LCA, but the continuum finding survives four *new* independent tests
> **Qualified 2026-07-29** by the detection-power entry above: the "**1 significant H0 component**" cited in
> learning #2(a) is **one draw of a statistic that ranges 1→120 on unchanged data** (median 1, p75 3, over 100
> draws). The conclusion stands — 1 is the modal value — but quote it as the centre of a noisy distribution,
> not as a measurement. The H1 loop-noise ratio and barcode shape are the robust parts. Learnings #1 and
> #3–#6 are unaffected.
**Domain:** Clustering / Methodology
`src/model_stress_test.py` + `src/model_zoo.py` widened the 2026-07-27 three-way test (k-prototypes /
k-modes / LCA) into **ten methods across six families** — adding **GMM** (full + diag), **SVD+KMeans**,
**Spectral(Gower)**, **Support Vector Clustering**, **TDA-Mapper** and **H0/H1 persistent homology**, plus a
KMeans floor — scored on **eight axes** on the same 20k booking sample and feature set (so it extends, not
replaces, the earlier decisions). Weighted leaderboard:

| method | agreement (ARI) | separation (Gower sil) | stability | robustness | score | score w/o agreement |
|---|---|---|---|---|---|---|
| **GMM(full)** | **0.409** @k=6 | 0.262 | 0.812 | 0.757 | **0.849** | **0.798** |
| GMM(diag) | 0.396 @k=4 | 0.269 | 0.706 | 0.724 | 0.828 | 0.785 |
| Spectral(Gower) | 0.372 @k=3 | **0.381** | 0.582 | 0.431 | 0.785 | 0.754 |
| LCA (incumbent) | 0.337 @k=4 | 0.298 | 0.680 | 0.645 | 0.763 | 0.762 |
| KMeans | 0.226 | 0.136 | **0.970** | **0.802** | 0.673 | 0.762 |
| SVD+KMeans | 0.184 | 0.087 | 0.851 | 0.812 | 0.583 | 0.686 |
| k-prototypes | 0.207 | 0.106 | 0.810 | 0.646 | 0.530 | 0.592 |
| SVC | 0.132 | 0.363* | 0.135 | 0.010 | 0.364 | 0.451 |
| k-modes | 0.228 | 0.144 | 0.471 | 0.247 | 0.363 | 0.346 |
| TDA-Mapper | 0.100 | −0.007 | 0.451 | 0.545 | 0.280 | 0.373 |

**Six things learned:**

1. **GMM(full) beats LCA on the composite, and beats it on the non-circular axes too** (0.798 vs 0.762 with
   taxonomy agreement weighted to zero) — so the win is not borrowed from the rules it is scored against.
   Higher agreement (0.409 vs 0.337), stability (0.812 vs 0.680) and robustness (0.757 vs 0.645); LCA keeps
   the better **separation** (0.298 vs 0.262). **Scope caveat:** this benchmark tests *top-level* segmentation,
   whereas LCA's actual pipeline job is **sub-segmenting inside big parent segments**. Swapping the pipeline
   layer needs a GMM-vs-LCA head-to-head *at that stage* first (as `kproto_compare.py` §5 did).
2. **The continuum finding (2026-07-23) is confirmed by four brand-new, independent lines of evidence** —
   this is the strongest result. (a) **Persistent homology**, which sees no labels, no k, no centroid and
   assumes no distribution: **1 significant H0 component**, gap ratio 1.195 → one connected mass.
   (b) **SVC's emergent k = 1** for every γ ≤ 0.8 — the kernel contour finds *one* blob until γ is large
   enough to shatter it into 27–39 shards while ejecting 43–62% of rows. (c) **TDA-Mapper finds nothing**:
   separation ≈ 0 and *negative* at k ≥ 5. (d) **Median cross-method ARI 0.41** — six families cut the data
   six different ways.
3. **Separation ceilings at 0.381** across all ten methods (weak-but-real band, 0.25–0.5). That is the honest
   upper bound on what *any* clustering can claim here — a number to quote when asked "how good are the
   clusters?"
4. **The SVM separability probe earned its place.** Held-out balanced accuracy on a solution's own labels
   runs **0.85–0.99 for nearly every method**, including ones with silhouette ≈ 0.1. A geometric partition of
   a continuum is perfectly *learnable* while being entirely *arbitrary* — so **a separability/accuracy number
   is not evidence of real segments** and must never be quoted without the silhouette beside it. (Only k-modes
   scored low, 0.69–0.90, and it is the worst method overall.)
5. **KMeans is the most stable and robust method in the field** (0.970 / 0.802) with almost the *least*
   separation — the textbook signature of stably partitioning a smooth density. Same trap
   k-prototypes fell into on 2026-07-27 (split-half 0.97, worst separation), reproduced by a third method.
   **Stability without separation is not evidence of structure.**
6. **New caveat — every method is fragile to losing one feature.** Leave-one-feature-out ARI *minimums* land
   at 0.15–0.49 for all ten (best: SVD+KMeans 0.487, LCA 0.480; GMM(full) 0.409). No method's segmentation is
   robust to a single column going missing, which is a real production risk given the extract's known gaps.

*SVC's 0.363 separation is measured on the 77% of rows still inside a contour at γ=1.6 — a high silhouette
paired with a large outlier share is **selection, not structure**. Its stability is −0.05 (worse than random)
because emergent k jumps discontinuously with γ.

**Also:** `giotto-tda` has no Python 3.14 wheel and fails to build; `kmapper` + `ripser` cover Mapper and
persistent homology and are now pinned in `requirements-pipeline.txt`.
**Source:** our analysis — `outputs/model_stress_test/summary.md`, `src/model_stress_test.py`,
`src/model_zoo.py`; Ben-Hur et al. (2001) "Support Vector Clustering" for the SVC construction.

---

#### 2026-07-27 — The extract has a hard forward-book boundary: any unfiltered trend visual draws a fake cliff
**Domain:** Data & Features
The real extract stops at a **single as-of date** — the last flown departure is **2026-07-21**. Travel months
past that are *forward bookings still filling*, not demand, and the drop-off is severe: Jun-2026 has 1,094,151
coupons (100% flown), Jul-2026 has 1,088,618 (68.9% flown), **Aug-2026 has 627,859 (0% flown)** and Sep-2026
only **316,703 — about 22% of a mature month**. Plotted unfiltered, a 12-month trend or YoY visual shows a
catastrophic decline that is purely an artefact of the extract boundary.
Second, related trap: **travel year 2024 only starts in May** (first departure 2024-05-01), so a full-year
2025-vs-2024 YoY silently compares 12 months against 8.
**Fix shipped:** `src/export_powerbi.py` now derives the boundary from the data (`max(departure_date) where
flown`) and stamps three guards on every row — `DataAsOfDate`, `IsCompleteTravelMonth` (TRUE only through the
last fully-settled month) and `IsCompleteTravelYear` (TRUE for **2025 only** on this extract). Every trend and
YoY visual must default to `IsCompleteTravelMonth = TRUE`. The same flag is repeated on the generated
`dim_date.csv` so the filter works from either side of the model.
**Source:** our analysis — `outputs/powerbi_export/summary.md`; travel-month completeness query.

#### 2026-07-27 — BI fact table hardened: booking key, primary-coupon flag, exclusion flags, dashboard grain
**Domain:** Data & Features
Review of the first export surfaced structural gaps that would have produced wrong Power BI measures. All fixed
in `src/export_powerbi.py` (+ one upstream change to `src/clean_real.py`):
1. **No booking key existed.** Segment is a *booking* attribute on a *coupon* table, and the booking was only
   implicitly the composite (`UniqueID`, `DateOfIssuance`). Added **`BookingID`** (hashed surrogate) and
   **`IsPrimaryCoupon`** — exactly one TRUE per booking, so booking-level measures become a filter instead of a
   DISTINCTCOUNT over a composite. This also fixes the per-leg `Route` repetition that double-counts
   connecting journeys.
2. **`CouponNumber` was dropped in Stage C** — without it legs cannot be ordered or deduped within a booking.
   Now carried through (`pal_clean` 43 → 44 columns).
3. **No Date dimension**, despite YoY and 12-month-trend being explicit requirements. DAX time intelligence
   needs a marked Date table; there are also **two date roles** (`DepartureDate`, `DateOfIssuance`) needing
   `USERELATIONSHIP`. Now generated as `dim_date.csv`.
4. **Exclusion flags were computed upstream but never exported.** `IsAward`, `IsNonRev`, `IsGroupFare`,
   `RevMissing`, `AgeKnown`, `IsReissue` now ship, so a clean revenue measure is a filter rather than a guess.
   Same for the already-computed `DestRegion`, `RoundTrip`, `IsInternational`, `BookingCoupons`, `NLegs`.
5. **The `agg/` rollup barely rolled up** (20.1M rows = 52.8% of coupon rows) because it kept
   `OperatingFlightNumber` (1,213 values) and **day-level** dates (1,126 / 1,173). Added a separate
   **`agg_dashboard/`** at true headline grain (~1.7M rows, ~23× smaller than the coupon table); `agg/` stays
   for flight-level detail pages.
6. **Dropped two dead columns:** `RouteBasis` (100% one value — it was a diagnostic, since served) and
   `CouponStatusLabel` (duplicate of `CurrentCouponStatus`; replaced by the boolean `IsFlown`).
Deliberately **not** renamed despite being misleading: `PaxCount` (sectoral, ≈always 1, not party size),
`DaysBeforeMonthEnd`, `OperatingCarrierCode` (constant `PR`) and the snake_case `is_nonstop` — all four were
requested by name, so they keep their names and carry ⚠️ warnings in the field dictionary instead.
Still open: **currency is undocumented** — Stage F only established revenue is *plausibly* single-currency
(7.3× median spread across 26 issue countries). Confirm with PAL before summing revenue across countries.
**Source:** our analysis — `src/export_powerbi.py`, `outputs/powerbi_export/summary.md`.

#### 2026-07-27 — `DaysBeforeMonthEnd` is departure-month metadata, not a booking snapshot — it cannot anchor LY-vs-CY pickup
**Domain:** Data & Features
The BI field list asked for `DaysBeforeMonthEnd` as the "same-window snapshot anchor for LY vs CY pickup."
It cannot serve that purpose. Verified on all 38.1M raw coupons: **every one of the 37 departure months
carries exactly one distinct value**, even though each month is sold across **13–15 different issue
months**. So the field is a deterministic function of the *departure month* alone, measured against a
single extract date (~2026-07-20): it is a constant **`-7`** for every departure month through Jun-2026,
then steps by month length (11, 42, 72, 103, 133, 164, 195, 223, 254, 284, 315) for future months. Only
**12 distinct values exist across the whole extract**, 91.45% of them `-7` *(figures corrected
2026-08-12 — this entry originally said 8 / 99.7%, which was wrong; see the 2026-08-12 entry)*. It
therefore carries **zero booking-timing information** and cannot distinguish "booked 60 days out" from
"booked 3 days out".
**Implication:** pickup/booking-curve analysis needs either (a) `LeadTimeDays` (departure − issuance,
genuine per-coupon, already exported), or (b) **repeated dated extracts of the same departure months** —
a data request to PAL, since this is a single snapshot. This supersedes the earlier note that the field was
"fine as the LY-vs-CY pickup anchor."
**Source:** our analysis — DuckDB probe over `data/interim/pal_parquet/`; `outputs/powerbi_export/summary.md`.

#### 2026-07-27 — Power BI export built: `OnlineOD` alone resolves Route; `PaxCount` is sectoral, not party size
**Domain:** Data & Features
`src/export_powerbi.py` joins the booking-grain `proxy_segment` onto the 38.1M cleaned coupons (row-preserving:
38,116,259 in = out; 99.95% segment match, the 0.05% gap being the all-non-revenue customers Stage F excludes).
Three findings that change how the report must be built:
1. **Route needs no three-way waterfall.** `OnlineOD` is populated on 99.999% of coupons. On **nonstop**
   coupons (27.6M, 72.4%) `OnlineOD` **is identical to `Sector`** (99.998%), so the "Sector for nonstop"
   rule is satisfied automatically. On **connecting** coupons (10.5M, 27.6%) `Sector` matches only 16.3% —
   correctly so, since a sector is one leg of many. The genuine interline case is the **22.6% of connecting
   coupons where `OnlineOD` ≠ `TripOD`**. Caveat: `Route` repeats per leg, so counting coupons by Route
   double-counts connecting journeys.
2. **`PaxCount` is a *sectoral* count** (1 sector = 1 pax) — it is 1 on 38,114,663 of 38,116,259 coupons and
   is **not party size**. Segment pax = coupon count; party size must come from `BookingType = 'Group'`.
3. **`OperatingCarrierCode` is constant `PR`** across the entire extract, so the "isolate PR-operated" filter
   is a no-op; interline surfaces as `TripOD` ≠ `OnlineOD` instead.
Also confirmed the fare basis: `NetRevenue ≥ NetFare` on **100.0%** of coupons (median gap 7.11 = the YQ
surcharge), so `NetFare` = base fare excl. YQ → use it for **Avg Fare**; `NetRevenue` = fare + YQ → use it
for revenue share / YoY.
**Source:** our analysis — `src/export_powerbi.py`, `outputs/powerbi_export/summary.md`.

#### 2026-07-27 — k-prototypes / k-modes head-to-head: no improvement as labeler; but they *are* more reproducible
**Domain:** Clustering / Methodology
Tested whether swapping in **k-prototypes** or **k-modes** would improve the model. The 2026-07-23
diagnostic had only run k-prototypes **once** at k*, so `src/kproto_compare.py` re-ran all three methods
(k-prototypes · k-modes · LCA) on the **same** 20k booking sample, k = 3–12, on four axes: cost/BIC elbow,
ARI vs the proxy taxonomy, **Gower** silhouette (mixed-type-correct separation) and **split-half stability**
(fit on half A → predict B vs fit on B). **Findings:** (1) **Still no natural k** — k-prototypes/k-modes cost
falls monotonically with per-step gains staying 3–8% (cost *always* falls with k, so there is no elbow to
find); LCA BIC flattens to ≤0.6%/step from k=7 and finally turns up at k=12 (min k=11) — a boundary, not an
elbow. Continuum finding **reconfirmed by a second method family**. (2) **Neither improves labelling** —
best ARI vs proxy: **LCA 0.336** (k=4) vs k-prototypes 0.216 (k=8) vs k-modes 0.212 (k=6); LCA also wins
separation (Gower sil **0.30** vs 0.09 / 0.15). Note k-modes gets *identical* binned input to LCA and still
loses, and k-prototypes gets the *advantage* of raw un-binned numerics and still loses → LCA's win is the
model class, not the encoding. (3) **Methods disagree with each other** (pairwise ARI 0.12–0.43) → no single
reproducible partition exists, exactly as a continuum predicts. (4) **The one real k-prototypes win —
stability:** split-half ARI **0.97–0.98** (k=5/9/10) vs LCA 0.67–0.86 and k-modes 0.37–0.65. **Interpretation
matters:** a hard-centroid method partitions a smooth density very reproducibly *without* the partition being
meaningful (worst silhouette of the three) — high stability here is **not** evidence of clusters. (5)
**Sub-segmentation head-to-head** (inside Budget/Adventure · OFW/Migrant · Balikbayan/VFR at k=4): LCA wins
Gower silhouette in **all three** (0.264/0.215/0.204 vs 0.241/0.151/0.193) and gives more balanced sub-types
(k-prototypes produced a degenerate **2%** sub-segment in OFW); k-prototypes wins stability in all three.
**Decision: keep the pipeline as-is** — rules primary, **LCA** the refinement layer; k-prototypes stays a
diagnostic cross-check only. **Actionable side-finding:** the **Balikbayan/VFR** LCA sub-types are the least
reproducible (split-half ARI **0.495**) — consistent with the earlier colliding auto-names there — so those
sub-types must not be presented as firm; re-derive or reduce the sub-count for that parent.
**Source:** `src/kproto_compare.py` → `outputs/kproto_compare/summary.md`.

#### 2026-07-23 — methodology.md v0.7: Tools & Libraries disclosure + version-drift fix; report humanized
**Domain:** Project Decision
Added a **Tools & Libraries (disclosure)** section to `docs/methodology.md` (bumped v0.6→**v0.7**) —
an intuitive "what each tool is for and why" table covering the real stack: Python 3.14, DuckDB 1.5.5
(out-of-core), PyArrow/Parquet 25.0, pandas 3.0.3 / NumPy 2.5.1, StepMix 3.0 (LCA), kmodes 0.12.2
(k-prototypes), scikit-learn 1.9 / SciPy 1.18, matplotlib 3.11 / seaborn 0.13.2, tabulate, ruff/bandit/
pre-commit, and headless Chrome for PDF; notes `hdbscan`/`imbalanced-learn` as retired-but-installed for
prior tracks, and `DataDictionary.v1.xlsx` as the authoritative reference. Also **reconciled a version
drift** (header said v0.5 while footer said v0.6; changelog was missing v0.6) — added v0.6 + v0.7 entries.
Separately **humanized** `docs/status-report.{html,pdf}` prose (warmer, less robotic; same figures/facts)
and added the same **Tools & Libraries disclosure as a new report section (§05 "What we built it with")** —
so the disclosure lives in both the methodology doc and the shareable report. **Source:**
`requirements-pipeline.txt` + our edits.

#### 2026-07-23 — Colleague-facing status report built (real-data figures generated for the first time)
**Domain:** Project Decision
Produced a shareable status report — **`docs/status-report.pdf`** (7pp, A4) + self-contained
`docs/status-report.html` — covering approach, methodology, EDA and current status for colleagues.
Key point: the real-data track had **only text summaries, no figures** (all PNGs in `outputs/` were from
the old `sample-features` baseline and the superseded prototype — misleading to reuse). So
`src/report_figures.py` now generates genuine real-data figures from `pal_features_booking.parquet`:
3 EDA charts (segment volume×value, route region, lead-time×value-tier) + 2 preliminary-cluster panels
(LCA BIC/ARI curve; PCA projection coloured by LCA class vs. rule segment — visually confirms the
continuum). `src/build_report.py` base64-embeds them into the print template
(`docs/_status-report.template.html`) and renders the PDF via headless Chrome. **Source:** our build.

#### 2026-07-23 — Hybrid adopted; methodology.md pivoted; LCA sub-segmentation of big segments
**Domain:** Project Decision
Decisions signed off: **(1) Hybrid approach** — rule-based purpose×value segmentation is PRIMARY, LCA is the
refinement/validation layer (HDBSCAN dropped for real data). Updated `docs/methodology.md` to **v0.6** (new
at-a-glance real-data track; "HDBSCAN plan of record" flagged ⚠️ superseded for real data) and
`docs/real-data-plan.md` §4. **(2) Sub-segment the big rule segments** (`src/sub_segment.py`, LCA within each
parent) → `outputs/sub_segments/summary.md`. BIC is monotone *within* segments too (continuum all the way
down), so sub-count is **capped at a business-actionable 4** (deliberate cut, not natural k). Interpretable
sub-types emerged, split by direction × timing × value tier × connecting: e.g. **Budget/Adventure** → 4
(one-way advance supersaver $23 / one-way short-lead saver $69 / round-trip advance saver $87 [largest, 38%]
/ one-way connecting $86); **OFW** → 4; **Balikbayan** → 4 ($317–$987 by lead/connecting/value); **Last-Minute**
→ 3. Top-level 10 segments unchanged. Note: auto sub-names can collide (cosmetic; clusters distinct). Taxonomy
stays a data-driven hypothesis to reconcile with PAL (outbound-leisure gap, Digital Nomad). **Source:** our runs.

#### 2026-07-23 — Mixed-type clustering diagnostic: data is a continuum → rules primary, clustering refines
**Domain:** Clustering / Methodology
Per the decision to use a data-driven mixed-type method (HDBSCAN rejected — categorical-heavy data isn't
dense blobs), ran `src/cluster_diagnostic.py` (LCA via `stepmix` + k-prototypes via `kmodes`) on a 60k
stratified booking sample (4 numeric + 6 binary + 1 nominal features). **Findings:** (1) **No natural k** —
LCA BIC decreases monotonically 3→9 (1.016M→932k) with no elbow, picking the range boundary → the customer
base is a **continuum** along the feature axes, not discrete islands. (2) **Only moderate agreement with the
rule-based proxy segments** — ARI 0.20–0.34 (peak at k=5), for both LCA and k-prototypes. (3) But the emergent
clusters split along **exactly the rule axes** (domestic/intl, one-way/round-trip, value, lead) and mainly
sub-divide the big domestic-economy mass (4 of 9 clusters are Budget-dominant sub-types) and cleanly separate
intl-round-trip $724 (Balikbayan) from intl-one-way $260 (OFW). **Conclusion (recommended pivot):** unsupervised
clustering is **not** the right primary labeler here (no natural k; only re-slices our axes); make the
**rule-based purpose×value segmentation primary**, and use LCA/clustering as a **refinement + validation layer**
(sub-segment oversized groups, validate axes, inform taxonomy). Supersedes the v3 "HDBSCAN → 10 segments,
recall-vs-proxy" plan for the real data. Deps added: `kmodes`, `stepmix`. **Source:** `src/cluster_diagnostic.py`.

#### 2026-07-23 — Stage F proxy rules refined + mode()→max() perf fix
**Domain:** Clustering / Methodology
Reviewed the Stage F feature tables + proxy rules and refined (see also `docs/real-data-plan.md` §4):
(1) **`corp_channel`** narrowed to **TMC + Corporate Web Portal** (dropped **NDC** — a distribution tech
standard, not a corporate signal). (2) **Corporate** broadened to `corp_channel OR (business AND lead≤7)`
→ **0.07% → 4.4%** of bookings (captures economy corporate via TMC; avg rev correctly drops $1,245→$493).
(3) **Budget/Adventure** broadened from `tier≤2` to **domestic AND NOT premium** → 29.8% → 39.4%, cutting
**Unassigned 20.9% → 9.6%** (residual is mostly the flagged #4 gap: PH-issued *outbound* international
economy — no home segment in the 10; left Unassigned, to raise with PAL). Value axis still monotonic
($74 Budget → $1,504 Premium Bleisure). **Perf:** the dominant channel/region/country aggregates used
`mode()`, which spilled catastrophically (**34 GB**, killed at 14 min); a booking averages 1.66 coupons so
`max()` is equivalent and cheap → clean 7.5-min run, ~0 spill. Digital Nomad still unseeded (expected).
Refined outputs written to `data/interim/pal_features_{booking,customer}.parquet`. **Source:** review +
`src/features_real.py`.

#### 2026-07-23 — Stage F built & run: booking + customer features + proxy labels
**Domain:** Data & Features
`src/features_real.py` (DuckDB, ~8.5 min) → `data/interim/pal_features_booking.parquet` (**22,911,450**
bookings) + `pal_features_customer.parquet` (**13,435,365** customers) + `outputs/features_real/summary.md`.
Excluded 12,306 all-non-rev customers. **Both data guards passed:** UniqueID appears in >1 source file for
19.73% of customers (cross-file customer key is valid → rollup OK); median-revenue spread across 26 issue
countries = 7.3× (< 20× → plausibly single-currency, likely USD). Coupon→booking aggregation joins the
airport-region ref; booking features cover value (farebrand tier), timing (lead_days, peak_month, round_trip),
route (is_domestic/international, dest_region, pilgrimage), party/channel (group, corp_channel, sea_crew),
loyalty (is_award). **Prioritized proxy-label waterfall** (seeds, not final) → booking mix: Budget/Adventure
29.8%, Unassigned 20.9%, OFW/Migrant 18.0%, Last-Minute 13.7%, Balikbayan/VFR 13.2%, Premium Bleisure 2.6%,
Family 1.6%, Pilgrimage 0.19% (44k to JED/MED), Corporate 0.07%, Mabuhay Loyalist 0.03%; **Digital Nomad
unseeded (0)**. Strong validation: **avg revenue is monotonic across segments** ($53 Budget → $140 Last-Minute
→ $317 OFW → $408 Pilgrimage → $622 Balikbayan → $1,245 Corporate → $1,468 Premium Bleisure), which also
corroborates single-currency. Route mix: 57.7% domestic, 16% East Asia, 10.6% SE Asia, 8.5% North America,
4% Middle East, 3.3% Oceania. Notes: Corporate proxy is thin (restrictive rule); Mabuhay Loyalist seeded by
award only — repeat+premium enrichment deferred to clustering/customer stage. **Source:** `src/features_real.py`.

#### 2026-07-23 — Pre-Stage-F decisions settled + airport→region reference built
**Domain:** Project Decision
After the EDA confirmations, settled three pre-Stage-F decisions (recorded in `docs/real-data-plan.md`
Decisions §): **(1) Population** = exclude only the 12,306 all-non-revenue customers (0.09%); keep the
heterogeneous heavy tail (crew/agency/corporate are signals). **(2) Deliverable unit** = booking-primary
labels + a customer-level dominant-segment rollup. **(3) Route lookup** = we build it. Built
`src/build_airport_ref.py` → `data/reference/airport_region.csv` (tracked): all **97 airport codes** in the
data mapped to country + region (39 PH-domestic, 58 international across North America / Oceania / East Asia
/ Southeast Asia / South Asia / Middle East / Europe), 100% coverage. Low-volume PH strips (BPA/BSI/KTI)
pair only with PH hubs → treated as domestic (provisional). Still open (asks to PAL, non-blocking): SME
label sample; `E`/`Z` coupon-status path codes. **Source:** our EDA + curation.

#### 2026-07-23 — Stage E confirmation pass: value is non-discriminative; route split now essential
**Domain:** Clustering / Methodology
Ran `src/eda_real.py` on `pal_clean` → `outputs/eda_real/confirmations.md`. Findings: **A1** booking grain
`(customer_id, issue_date)` = **22.9M bookings**, avg 1.66 coupons, **42.7% round-trip / 55.3% one-direction**
→ grain is sound (one-way is itself a signal). **A2/A3** heavy tail is **heterogeneous** — 100+-coupon
customers (4,896) are 22% Sea Crew but mostly WEB/APP + agency + corporate portal, and only **12,306
customers (0.09%) are entirely non-revenue** → exclude non-rev cleanly, **do NOT blanket-exclude the tail**
(crew/agency are signals). **A4** lead time median 25 / mean 53 days, negatives just 1,728 (0.005%, reissues)
→ clamp. **A5** loyalty leans on **repeat customers (26.1%, 3.5M)** + premium (6.9%), not the tiny award flag
(6,259 customers, 0.05%). **A6 — key insight:** rough proxy seeds are either tiny (award 0.03%, corporate
~1%) or huge/overlapping (**economy tier≤2 = 70.6%**, foreign-issued econ 33%, last-minute 19%). So **value
is NOT discriminative** (most bookings are cheap economy) — purpose/route/timing must drive segmentation, and
the **airport→region / domestic-vs-international lookup is now essential** (not optional) to split the 70%
economy bulk into domestic-budget vs international-OFW. Confirms §5: expect a few strong segments + heavy
overlap + an Unassigned bucket. **Source:** `src/eda_real.py` run.

#### 2026-07-22 — Stage C built & run: cleaned coupon Parquet (`src/clean_real.py`)
**Domain:** Data & Features
Implemented Stage C (`src/clean_real.py`, DuckDB streaming COPY) → `data/interim/pal_clean/` (1.6 GB,
partitioned by iss_year) + `outputs/clean_report/summary.md`. 38,116,260 → **38,116,259 rows** (dropped 1
junk `SoldOperatingCabinClass='K'`). **No dedup applied** — exact duplicates on the natural coupon key
verified ~0 via a streaming approx-distinct check (the first attempt used a `row_number()` window that
spilled and hit a DuckDB temp-file IO error; removing it made the pass a clean 21s stream). Adds snake_case
columns + flags: `farebrand`/`value_tier` (7 Business Flex…1 Supersaver, date-aware F/G), `is_award`/
`is_group_fare`/`is_nonrev`, `flown`, `lead_time_days`, `is_connecting`/`n_legs`, `trip_origin`/`trip_dest`/
`sector_origin`/`sector_dest`, `revenue`/`net_fare`/`rev_missing`/`is_refund`, `age`/`age_known`,
`is_group_booking`, `foreign_issue`; dropped `OperatingCarrierCode` + `DaysBeforeMonthEnd`; winsorization
deferred to FE. QA results all reconcile with prior verification: flown 93.42%, Mabuhay award 9,152 coupons
(0.024%), Groups 49,821, non-rev 31,249, NULL value_tier 90,222 (=award+groups+nonrev, exact), age-known
43%, foreign-issued 38.4%, connecting 27.6%, avg lead 53.2 days. **Source:** `src/clean_real.py` run.

#### 2026-07-22 — Plan sanity-check: booking grain > directional trip; segment feasibility tempered
**Domain:** Clustering / Methodology
Stress-tested `docs/real-data-plan.md` against the data and made three refinements: (1) **Grain = booking
(`UniqueID`,`DateOfIssuance`), not the directional `TripOD` key.** The `TripOD` key averages only **1.13
coupons** (splits out/return into two journeys), whereas a booking groups round-trips — **43% of bookings
have 2 `TripOD` directions** (out+return), 55% one → ~23M bookings is the purpose unit. (2) **Customer
rollup is a minority signal:** only **26% of customers book >1×** (6.6% have 4+), so tenure/frequency/LTV
inform that minority; for 74%, customer ≡ their one booking — loyalty leans on award flags + that 26%.
(3) **Segment feasibility is uneven:** of the 10 target segments, ~5–6 have decent signal (Last-Minute,
Mabuhay Loyalist, Corporate, Budget/Adventure, OFW; Family moderate) and 3–4 are weak/overlapping
(Balikbayan-vs-OFW, Premium Bleisure, Pilgrimage [needs route lookup], Digital Nomad). Expect an
Unassigned bucket; validation stays proxy-circular until SME labels arrive. Also noted per-km/yield needs
an external airport-coords table (not in data); non-revenue is only 31,249 coupons (clean exclusion).
Verdict: pipeline skeleton (DuckDB→Parquet→clean→EDA→features→sample-cluster→inductive-label) is sound;
these are refinements, not a redesign. **Source:** our DuckDB verification + plan audit.

#### 2026-07-22 — V1 dictionary (authoritative) overturns two v2-based corrections + adds farebrand ladder
**Domain:** Data & Features
Client supplied the authoritative **`data/PAL-data/DataDictionary.v1.xlsx`** (sheets `Dictionary` +
`Farebrand_relationship`) for the real data. It **supersedes the two corrections in the earlier
"Dictionary reconciliation" and "SME rule" entries below**, which were based on the stale legacy
`...v2.csv`. Corrections, all **verified against the Parquet**:
- **`UniqueID` = "Unique customer identifier"**, NOT a PNR. Verified: single IDs span up to **1,162 days
  (~3.2 yr)** and 26% make >1 booking → it tracks a person across bookings. **Customer-level features
  (repeat frequency, tenure, lifetime value, loyalty) are back on** — reinstates the "trip + customer
  rollup" grain. (There is no explicit PNR id; a trip = `UniqueID`×`TripOD_DepartureDate`×`TripOD_Path`.)
- **`CurrentCouponStatus` F = flown, O = open** (not "ticketed/unticketed"). Verified: every future
  departure is `O`, every past is `F`, 0 future-flown. Realised travel = flown coupons.
- **Farebrand ladder** (`Farebrand_relationship`) maps all 26 RBD letters to 8 farebrands →
  authoritative ordinal value tier, **replaces the ad-hoc `FARE_TIER`**: Business Flex (J,C,D) >
  Business Value (I,Z) > Premium Economy (W,N) > Economy Flex (Y,S,L,M,H) > Economy Value (Q,V,B,X) >
  Economy Saver (K,E,T) > Economy Supersaver (U,O); plus **Non-revenue** A,R (biz), P (econ) = staff/comp
  (clean exclusion lever for non-customers); **Groups** G; **Award** F.
- **Mabuhay award coding flips at 2026-04-01**: award = (≥Apr-2026 & `F`) OR (<Apr-2026 & `G`) ≈ **9,152
  coupons** (1,031 + 8,121) — far more than the F-only ~1,038; post-Apr `G` = Groups (49,821). So the
  earlier "F post-Apr only" award rule was correct but incomplete.
- **`Age` structurally missing** (V1: DOB vs issuance, **international ops only**) → not missing-at-random;
  `age_known` is itself a signal. **`Pax Count`** is sectoral by design (1 sector = 1 pax), so ~always 1 —
  group signal comes from `BookingType`/Groups. **`DaysBeforeMonthEnd`** is a revenue-accounting snapshot
  (days before end of travel month, for YoY same-point comparison; >month-length = accounting overrides)
  → **drop from segmentation**. **`TripOD`** includes codeshare (OAL) sectors; **`OnlineOD`** is PR-only.
**Source:** `DataDictionary.v1.xlsx` + our DuckDB verification. Plan fully rewritten in
`docs/real-data-plan.md` (§0/§0a farebrand table/§1 grain/§4/decisions).

#### 2026-07-22 — SME rule: BookingClass 'F' = Mabuhay Miles award ticket (issued ≥ Apr 2026)
**Domain:** Airline Industry
SME (client) rule: an `F` in **`BookingClass` or `SoldBookingClass`** means the ticket was bought with
**Mabuhay Miles (loyalty points)** — an award redemption — **only for tickets issued 2026-04-01 onwards**;
earlier `F` entries mean something else and must not be treated as award. `F` is not a normal fare RBD
(absent from the dictionary's economy/premium/business lists). *Verified on the Parquet:* only 1,132 `F`
booking-class coupons exist in all 38.1M, clustered in 2026 and ramping after April; applying the cutoff
gives **1,038 award coupons (all economy cabin)**, with `BookingClass`/`SoldBookingClass` agreeing ~1,064×.
Impact: this is a **direct, high-precision but very low-coverage Mabuhay Loyalist signal** — it partly
offsets the "no repeat-loyalty possible" limitation from the PNR-grain finding, but only seeds the segment
(absence of `F` ≠ non-member; signal exists only from Apr-2026 on, so don't read the 2026 rise as loyalty
growth — it's when the coding began). Feature: `award_ticket` = (`BookingClass='F'` OR `SoldBookingClass=
'F'`) AND `DateOfIssuance >= '2026-04-01'`; exclude `F` from `FARE_TIER` value mapping. Captured in
`docs/real-data-plan.md` §0a/§1/§4. **Source:** client SME rule + our verification (`src/` DuckDB query).

#### 2026-07-22 — Dictionary reconciliation corrects key assumptions (UniqueID = PNR, not passenger)
**Domain:** Data & Features
Reconciled the real extract against the legacy data dictionary
and found the profiling made wrong inferences — **corrected in `docs/real-data-plan.md`**:
(1) **`UniqueID` = the PNR (booking), NOT a passenger** (dictionary: "Unique identifier for the PNR").
The 13.45M distinct IDs are **bookings, not people**; the anonymous data has **no persistent passenger
key**, so there is **no passenger-level rollup / lifetime value / repeat-loyalty** possible — the model
grain is **PNR** (matches the project's stated PNR-level anonymous framing). This limits **Mabuhay
Loyalist** detection to within-booking signals. Verified in-data (avg 2.5 directional legs/PNR = round
trips; 99% single BookingType). (2) **`CurrentCouponStatus` F/O = ticketed / open(unticketed), NOT
flown / future** — departures run to 2027, so `F` can't mean flown; realised travel must be derived
from `DepartureDate`. (3) **`Pax Count` is ~always 1** (dict: "always 1"; only 1,596/38.1M are 2–5) →
party size unusable; group signal comes only from `BookingType`. (4) **`POO` = origin airport**, not the
country the dict's "PointofOrigin" implies (separate `CountryCodeOfIssue` exists). (5) **`Gender` is in
the dictionary but absent from the real data**; `Revenues w YQ`=dict `NetRevenue` (incl. ancillaries),
`Net Fare`=`NetFare`, `BookingType`=`Group/Individual`, `Channel Category`=`Channel`. (6) The heavy
100+-coupon tail is ~all Pax Count=1 and non-Group → likely agency/technical PNRs. (7) `DaysBeforeMonthEnd`
range (−7…315) conflicts with the dict definition — meaning unclear, confirm with PAL. **Source:** our
reconciliation (dictionary + DuckDB checks on the Parquet).

#### 2026-07-22 — Real data profiled (DuckDB/Parquet) + cleaning/EDA/feature plan
**Domain:** Data & Features
Profiled all 38.1M coupon rows via `src/build_parquet.py` (gz → `data/interim/pal_parquet/`, typed +
zstd + partitioned by iss_year, ~90s one pass) and `src/profile_raw.py` (→ `outputs/profile_raw/`).
Key findings: **13.45M distinct `UniqueID`** (0 null) at **mean 2.83 coupons / 2.51 trips per passenger**
(median 2, p95 8, max 771 — a long agency/crew tail); `OperatingCarrierCode` is **constant (PR)** →
drop; `CurrentCouponStatus` F(lown) 93.4% / O(pen) 6.6%; **`Age` is 57% null** (can't be a primary
feature); `Revenues w YQ` heavy right-skew (median 82.6, p99 1,150, max 290k) with 7,385 negative /
92,867 zero / 1,771 null, and `Net Fare` 38,442 negative (refunds/ADMs); cabin economy-dominated
(Y 94% / J 3% / W 3%); Non-Group 97.4%; nonstop 72%; **channels include "Sea Crew"** (maritime-crew
signal), NDC, TMC, OTA; geography MNL 38% / PH-issued 62% / US 10%; compound route cols
(`TripOD_Path`, `TripOD_Coupons`, `*_CouponStatus`) are space/hyphen-delimited and need parsing;
booking **lead time = departure − issuance** is available. Wrote the full plan to
**`docs/real-data-plan.md`** (grain decision → cleaning → EDA → feature engineering). **Decisions
signed off 2026-07-22:** model grain = **trip + passenger rollup**; **flown** coupons drive behaviour
with **open kept flagged**; **investigate the 100+-coupon crew/agency tail in EDA before** any
exclusion; use the **full 2024–2027 span** (account for uneven coverage vs truncating).
Toolchain decision: DuckDB out-of-core + Parquet for the 38M rows; pandas/sklearn only on the
aggregated model-grain table; clustering fits on a stratified sample + inductive labelling.
Added `duckdb`/`pyarrow`/`tabulate` to `requirements-pipeline.txt` and bandit skip `B608`
(DuckDB SQL built from internal constants only). **Source:** our analysis (`src/profile_raw.py`).

#### 2026-07-22 — Real PAL coupon-level data received (~38M rows, 2024–2027)
**Domain:** Data & Features
Received the first tranche of **real PAL data** in `data/PAL-data/` — four gzipped CSVs
(`newQuery2024`, `newQuery2025`, `newQuery2026Jan_to_May`, `newQuery2026Jun_to_2027May`),
~3.6 GB compressed, **38,116,260 data rows** total (10.4M / 16.2M / 7.07M / 4.35M respectively).
All four share an **identical 40-column header** (md5 `53318f34…`) and pass `gzip -t`. Grain is
**coupon/segment level** (one row per flown/booked coupon), not PNR level — must aggregate to
`UniqueID` (hashed pax) / PNR for segmentation. Columns include `DateOfIssuance`, `POO`,
`CountryCodeOfIssue`, coupon status, sold+operating booking/cabin classes, OD paths
(`TripOD`/`OnlineOD`/`Sector`), flight/carrier details, `is_nonstop`, `Channel Category`,
`BookingType`, hashed `UniqueID`, `Age`, `Revenues w YQ`, `Net Fare`, `Pax Count`. Format quirks:
UTF-8 BOM on header, double-quoted text fields, SQL-style `.0000000` timestamps. This is far
richer than any earlier sample and should become the real modelling input.
The original `data/OneDrive_1_7-22-2026.zip` was a **truncated/incomplete download** (single stored
entry, no central directory — `unzip`/`bsdtar`/`ditto` all rejected it); the user re-extracted the
`.gz` files directly into `PAL-data/`. **Source:** our analysis of `data/PAL-data/`.

#### 2026-07-17 — Docs reconciled: at-a-glance summary + BR drift fixed + methodology-upkeep rule
**Domain:** Project Decision
Added a **"Current Methodology at a Glance"** summary at the top of `methodology.md` (one-line P1→P5 flow,
current vs baseline track). **Reconciled the BR↔code drift:** `business-requirements.md` §5.4/§5.5 now carry
a "⚠️ Superseded" note — the human annotation + label-diffusion pipeline (FR-22–26) was replaced by
automated noise auto-assignment; Negative Learning (FR-21) retained as §P3b. New standing rule (CLAUDE.md +
memory [[keep-methodology-current]]): keep `methodology.md` — incl. the at-a-glance + footer date — in sync
on every methodology change, and keep BR/KB consistent. Joins the README and KB living-doc rules.
**Source:** our doc pass.

#### 2026-07-17 — Improved v3 model: hold-out + Tier-3 + negative learning + Unassigned bucket
**Domain:** Clustering / Methodology
While awaiting real data, applied the agreed improvements to the v3 pipeline:
(1) **hold-out split** (train 800 / test 200, stratified) with an **inductive** scorer
(scaler + train proxy-seed centroids + distance threshold) → out-of-sample recall;
(2) **Tier-3 feature pruning** → compact 24-feature matrix (from 58; drops the |corr|>0.9 dups) with
**mixed-type scaling** (scale continuous, keep binaries {0,1});
(3) **decoupled penalties** — HDBSCAN discovery is now UNWEIGHTED; penalties enter only in the cost
metric (was lowering DBCV before);
(4) **negative learning P3b** in `features_v3.apply_negative_learning`;
(5) **Unassigned bucket** — rows past the 95th-pctl train distance are left low-confidence (test 8%),
no more forcing 42% noise into Family.
**Results: withdrawn** — these were prototype-track measurements; see the 2026-07-31 entry on why such figures are withdrawn rather than relabelled. The one *structural* observation that survived, because it is about the method rather than the data: out-of-sample ≈ in-sample, i.e. the labeller generalises and the ceiling is set by the rules and the data, not by memorisation. **Recall stays
proxy-referenced (circular) until SME labels arrive** — added an auto-detected hook at
`data/labels/sme_sample.csv` (+ template/README) for non-circular validation.
**Source:** `src/features_v3.py`, `src/prototype_v3.py`; outputs/prototype_v3_output/.

#### 2026-07-17 — GAP: negative learning is NOT in the v3 pipeline
**Domain:** Clustering / Methodology
The documented framework (business-requirements, KB §9) includes **negative learning** — impossibility
filters applied after proxy labelling to send contradictory assignments back to Unassigned. It exists in
`poc_synthetic.py` Stage 4 but was **not carried into `features_v3.py`/`prototype_v3.py`**, and
`methodology.md` §P3 omitted it. Reason it lapsed: the baseline NL rules key on `Loyalty status`,
`checked bags`, `income` — none present in v3 — so they don't port 1:1. Portable v3-appropriate rules
exist (e.g. Corporate + lead>60 + Economy → invalidate; Corporate via OTA → invalidate; Digital Nomad +
group → invalidate; Premium Bleisure + low ancillary → invalidate). **Caveat:** NL refines proxy-seed
purity but does not fix the no-structure finding, and under circular validation "cleaner" seeds can make
recall look better without meaning more. Status: open — add as Stage P3b if we continue the rule track.
**Source:** code audit (grep); [[v3-prototype-data]].

#### 2026-07-17 — Built src/prototype_v3.py (Stages P4–P5); end-to-end prototype runs
**Domain:** Clustering / Methodology
`src/prototype_v3.py` runs P4–P5: StandardScaler → penalty-weighted HDBSCAN (min_cluster_size=30,
min_samples=5) → nearest-centroid cluster→segment mapping + noise auto-assignment → cost-matrix +
DBCV validation. Reuses `monitor_metrics.dbcv` and `pal_colors`. **Results: withdrawn** — prototype-track measurements (cluster counts, noise rate, DBCV, silhouette and per-segment recall against proxy seeds). They do not describe real-data performance; see the 2026-07-31 entry. Do not quote them. 3 segments unassignable (no seed): Mabuhay Loyalist, OFW/Migrant,
Pilgrimage. Next iterations: tune min_cluster_size/min_samples, richer or larger data, revisit the OFW
seed (v3 `pos_mismatch`≈0). Recall here measures agreement with proxy seeds (partly circular, per the
methodology's own note).
**Source:** `src/prototype_v3.py` run; outputs/prototype_v3_output/prototype_v3_report.json.

#### 2026-07-17 — Built src/features_v3.py (Stages P1–P3); proxy seeds thin for 3 segments
**Domain:** Data & Features
Implemented the v3 loader/clean/engineer/proxy-waterfall in `src/features_v3.py` → **58-feature
matrix**, 0 NaNs, all sanity checks pass (lead_time≥0, ancillary≥0). Proxy waterfall labels **45.7%**
of rows (vs 76.4% baseline; rest handled later by HDBSCAN + nearest-centroid). Distribution:
Balikbayan/VFR 11.9%, Corporate 11.1%, Family 7.5%, Digital Nomad 7.2%, Budget 5.5%, Premium
Bleisure 1.7%, Last-Minute 0.8%; Unassigned 54.3%.
**Key finding — 3 segments got ~0 proxy seeds on the prototype data (superseded track):** OFW/Migrant (its
`pos_mismatch` signal is ~0 — `CountryCodeOfIssue` almost always equals `PointofOrigin` in v3),
Pilgrimage (few Middle-East routes), Mabuhay Loyalist (no loyalty field, by design). A segment with
no proxy seed has **no centroid to map clusters to**, so it can't be assigned in the prototype. This
is a data-distribution limitation, not a bug — v3 is mostly PH-origin outbound to US/Asia, so the
inbound-diaspora/OFW pattern is underrepresented. Options next: relax OFW/Pilgrimage rules, or accept
the gap and document it. haul mix: LongHaul 474 / Regional 268 / Other 183 / Domestic 75.
**Source:** `src/features_v3.py` run; outputs/features_v3_output/.

#### 2026-07-17 — Dependency capture (3 requirements files) + optional Docker
**Domain:** Project Decision
`requirements.txt` was dashboard-only and **missing the entire pipeline stack**. Fixed by splitting deps:
`requirements.txt` (lean, Streamlit Cloud) · **`requirements-pipeline.txt`** (pinned ML/EDA:
scikit-learn 1.9.0, hdbscan 0.8.44, scipy 1.18.0, numpy 2.5.1, pandas 3.0.3, imbalanced-learn 0.14.2,
matplotlib 3.11.0, seaborn 0.13.2) · `requirements-dev.txt` (tooling). All pinned versions install and
import on **Python 3.14** (standalone `hdbscan` builds fine — the feared 3.14 wheel gap did not
materialise). Added an optional **`Dockerfile`** (python:3.11-slim, dashboard as default CMD) +
`.dockerignore`. **Recommendation stands: Docker is optional at prototyping stage** — the real
reproducibility win was capturing/pinning deps; containerize for the eventual PAL production handoff.
**Caveat:** Dockerfile not yet built/verified (no running Docker daemon in the dev session) — run
`docker build -t pal-segmentation .` to confirm.
**Source:** our setup; `README.md` §Docker / §Setup.

#### 2026-07-17 — Added ruff + bandit + pre-commit tooling (first pass done, repo green)
**Domain:** Project Decision
Code-quality tooling added: **ruff** (lint + format) and **bandit** (security) run via **pre-commit**.
Config in `pyproject.toml` (`[tool.ruff]`, `[tool.bandit]`) + `.pre-commit-config.yaml`; dev deps in
`requirements-dev.txt` (kept separate from runtime `requirements.txt` used by Streamlit Cloud). Lint
excludes `outputs/reports/assets/scratchpad/docs`. Enable with `pip install -r requirements-dev.txt &&
pre-commit install`. First pass applied across `src/` (all 15 files reformatted; ~60 lint issues fixed:
unused imports/vars, import sorting, empty f-strings, loop vars renamed to `_`). All hooks now pass.
**Gotchas learned:** (1) bandit `# nosec` needs **space-separated** IDs, not comma — use `# nosec B605`
(comma silently breaks suppression); (2) deterministic MD5 for non-security data hashing → use
`hashlib.md5(..., usedforsecurity=False)` to clear the B324 HIGH finding legitimately; (3) `zip()`
strict-check (B905) is ignored — 41 hits in plotting code where lengths are known equal.
Tools pinned in pre-commit: pre-commit-hooks v6.0.0, ruff v0.15.22, bandit 1.9.4.
**Source:** our setup + first-pass run; `README.md` §Code quality.

#### 2026-07-17 — methodology.md v0.5 adds an adapted PNR-level prototype pipeline
**Domain:** Project Decision
`docs/methodology.md` bumped to **v0.5**: the validated v0.4 pipeline on `sample-features.csv` is kept
as the baseline/reference; a new section documented the adapted stages (clean → features → proxy
waterfall → penalty-weighted HDBSCAN + mapping → validate), plus the phase→deliverable map. HDBSCAN was
recorded as the closed algorithm decision at that point.
> **Superseded 2026-07-23 / reduced to a stub 2026-07-31.** HDBSCAN was subsequently dropped for the real
> data, and this section is now `docs/methodology.md` §Prior Prototype Track — see the 2026-07-31 entry
> on why prototype results were withdrawn rather than relabelled.
**Source:** our update; `docs/methodology.md` §Prior Prototype Track.

#### 2026-07-17 — Our PNR-only model is Sabre's "anonymous segmentation" lens
**Domain:** Airline Industry
Airlines apply three segmentation lenses simultaneously (Sabre): **(1) anonymous** — segment a
booking from trip attributes alone, no PII/loyalty needed; **(2) customer-specific** — RFM +
loyalty + declared preferences (needs CRM history); **(3) use-case** — ad-hoc campaign cohorts.
Because we cluster PNR/coupon data with no loyalty join, our model **is** the anonymous lens:
**trip-purpose × value at the booking level**, *not* customer-lifetime segmentation. This is a
legitimate, named industry approach — frame the project this way. If a loyalty/passenger key is
added later, we can graduate to customer-level RFM/CLV.
**Source:** Sabre — Customer segmentation for airline marketing (sabre.com/insights).

#### 2026-07-17 — Canonical airline segment taxonomy & how PAL's 10 map to it
**Domain:** Airline Industry
The foundational taxonomy splits by **trip purpose**: **Business/Corporate** (time-sensitive,
price-insensitive, short lead, short stay, mid-week, premium cabin, highest yield), **Leisure**
(price-sensitive, long lead, long stay incl. a Saturday night, round-trip, restricted fares),
**VFR** (diaspora/ethnic O&D, price-driven — very relevant to PAL), and **Bleisure** (business
pattern + extended/weekend stay). Modern critique: business-vs-leisure alone is too coarse for
willingness-to-pay and ancillary propensity → **unsupervised clustering is favored over hard rules**
(exactly our approach). PAL's 10 segments = this trip-purpose×value scheme enriched with PH-diaspora
specifics; the only segment **not** PNR-derivable is **Mabuhay Loyalist** (needs loyalty tier).

| Industry segment | PAL segment(s) | PNR-derivable? |
|---|---|---|
| Corporate/business | Corporate | ✅ cabin+fare class+GDS+short lead |
| Bleisure/premium leisure | Premium Bleisure | ✅ premium cabin+weekend+ancillary |
| Price-sensitive/occasional | Budget/Adventure, Last-Minute | ✅ deep-discount RBD, lead time |
| VFR/diaspora | Balikbayan/VFR, OFW/Migrant | ✅ origin region + POS mismatch |
| Group/family | Family, Pilgrimage | ⚠️ via Group flag (not party size) |
| Modern niche | Digital Nomad | ⚠️ partial |
| Loyalty-value | Mabuhay Loyalist | ❌ needs loyalty tier |

**Source:** Teichert et al. (customer segmentation, airline industry); Expert Journal of Marketing
(airlines segmentation in hyper-competition); Sabre; Navan/Switchfly (bleisure 2025–26).

#### 2026-07-17 — Highest-signal booking features (industry-validated)
**Domain:** Airline Industry
Per revenue-management / price-discrimination literature, the strongest trip-purpose discriminators
from booking data are: **advance purchase (lead time)** ⭐ *(single strongest business-vs-leisure
signal)*, **Saturday-night / length-of-stay**, **cabin & fare (RBD) class**, **booking channel**
(corporate-TMC/GDS → business; OTA → leisure; direct → engaged), and **yield/monetary incl. ancillary
spend**. Day-of-week & time-of-day, one-way vs round-trip, nonstop vs connecting, party size/children,
and diaspora-route flags are secondary but useful.
**Source:** ScienceDirect (advance-purchase behavior; day-of-week price discrimination); IATA
(dynamic pricing of airline offers); Sabre trip-purpose attributes.

#### 2026-07-17 — RFM in airlines: we have "M", not "R/F"
**Domain:** Clustering / Methodology
RFM is the backbone of airline customer-value/CLV work, extended in recent research to **ancillary
spend** (not just fare). **Recency & Frequency require a passenger key that links bookings across
time**, which the prototype data lacked. *(Superseded 2026-07-22: the real extract's `UniqueID` **is** a
customer key — it spans up to 1,162 days and 26% of customers book more than once, so R and F **are**
computable there. See the 2026-07-22 profiling entries.)* On the prototype data we had a
strong **Monetary** axis (NetRevenue, NetFare, ancillary) but **cannot compute R or F** without
stitching bookings via name+DOB or a frequent-flyer number. This is the same "No RFM history" gap the
methodology already flagged. Consequence: model at the PNR level, not customer-lifetime.
**Source:** RFM airline value studies (ResearchGate); "Estimating travellers' value… auxiliary
services (RFM)", J. Retailing & Consumer Services 2023; our analysis of v3.

#### 2026-07-17 — Stage-3 proxy waterfall must be re-derived per schema (v3 variant)
**Domain:** Clustering / Methodology
The proxy-label rules in §8 are written for `sample-features.csv` columns and **do not translate 1:1
to v3**: the Family/Pilgrimage rules used PAX 3–5 / ≥4 but v3 `PaxCount` is always 1 → substitute the
**Group/Individual flag** (+ child age); Budget used Farebrand tiers (absent) → substitute deep-discount
RBD / low NetFare; Region/Channel taxonomies differ. A v3-specific proxy waterfall was drafted
(Corporate = Business cabin/full-fare Y + GDS + short lead; Premium Bleisure = premium cabin + weekend +
ancillary; OFW = POS-mismatch + Gulf origin; VFR = foreign-origin→PH long-haul; Last-Minute = lead ≤3–7d;
etc.). Mabuhay Loyalist still has no rule (no loyalty field). **General principle: proxy rules are
schema-specific and must be re-mapped whenever the input schema changes.**
**Source:** our analysis; `docs/methodology.md` §Stage 3.

#### 2026-07-17 — HDBSCAN min_cluster_size scales with dataset size
**Domain:** Clustering / Methodology
`min_cluster_size` is not a fixed constant — it scales with N: **~150 at 30k rows** (sample-features),
**~30–50 for the 1k-row v3 prototype**, **500–1,000 at the 6M-row production scale**. At 6M also switch
to `algorithm='prims_kdtree'` and FAISS ANN. 1k rows validates the *approach*, not production metrics.
**Source:** `docs/methodology.md` scaling table; our analysis.

#### 2026-07-17 — Validation: cost matrix is primary, DBCV/silhouette secondary
**Domain:** Clustering / Methodology
Two distinct metric regimes must not be conflated. **Model validation (Stage 7)** = asymmetric cost
matrix + **per-segment recall** (optimize Corporate ×10 and OFW ×5) — this is the authoritative
success metric (NFR-01 ≥ 91% recall). **Cluster-quality / algorithm-selection** = DBCV (correct
primary for HDBSCAN), Silhouette, Davies-Bouldin, Calinski-Harabász (from `monitoring-metrics.md`
Regime A). Report both, but Stage-7 cost governs.
**Source:** `docs/methodology.md` §Stage 7; `docs/monitoring-metrics.md`.

#### 2026-07-17 — Repo reorganized into data/src/docs/reports/assets/outputs
**Domain:** Project Decision
Flat root replaced by: `data/raw/` (CSVs), `src/` (all .py, kept flat so `from pal_colors import`
still resolves), `docs/`, `reports/` (tracked deliverables), `assets/` (deck sources), `outputs/`
(git-ignored regenerable artifacts). Every script resolves paths via
`ROOT = Path(__file__).resolve().parents[1]`, so they run from anywhere. ⚠️ Streamlit Cloud entrypoint
is now `src/dashboard.py`. See `README.md`.
**Source:** our reorg on 2026-07-17.

---

*Knowledge base maintained by CPT 3 — PAL Customer Segmentation*
*Last updated: 27 August 2026*

#### 2026-09-03 — New Data Extract (Jun 2026–May 2027) Integration & Validation Lift
**Domain:** Data Source / Methodology
A new iteration of the data extract introduced 5 critical new fields: `FareBasisCode`, `TourCode`, `RevPaxInd`, `ItinType`, and `FF_Ind`. These were cleanly integrated into the `clean_real.py` and `features_real.py` pipeline across 46.3M rows.
**Crucial Validation Lift**: Using these fields as validation anchors drastically improved the proxy label's construct validity scores across all tested segment boundaries. For example, the Leisure vs Corporate AUC lifted from 0.636 → 0.878, and Balikbayan vs Pilgrimage lifted from 0.727 → 0.955.

#### 2026-09-03 — Mabuhay Loyalist Expansion
**Domain:** Segment Definition
Previously, Mabuhay Loyalist was defined purely by award redemptions (booking class F/G), severely undercounting the segment (0.03% of data). Using the new `FF_Ind` field, the segment definition was expanded to `ff_ind = 1 OR is_award`. This successfully shifted ~17% of total bookings (drawn mostly from Leisure and Outbound Intl Leisure) into the segment while maintaining structural coherence (revenue CV improved from 2.20 to 1.70).

#### 2026-09-03 — Gulf Corridor Fare Artifact vs Behavioral Confound
**Domain:** Segment Analysis (OFW vs Balikbayan)
Analysis of the new `FareBasisCode` field resolved the long-standing "30-day stay spike" debate on Gulf routes. Statistical testing (Chi-squared p=0.0) confirmed the 30-day stay spike is heavily concentrated in specific fare families (e.g., TARI, TLFS, TSVF). Because the spike is tied to specific fares rather than distributed evenly across the economy cabin, it is primarily a **fare-rule artifact** (max stay limit) rather than a purely behavioral pattern (employer-mandated leave).
