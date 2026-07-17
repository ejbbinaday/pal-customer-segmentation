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
6. [POC Results](#6-poc-results)
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

## 6. POC Results

The synthetic POC ran the full 8-stage pipeline on **10,000 synthetic records** structured to mirror real PAL booking patterns (from `synthetic_flight_passenger_data.csv`).

### Top-Line KPIs

| Metric | Value | What It Means |
|--------|------:|---------------|
| Overall Accuracy | **77.7%** | Share of labelled records correctly identified |
| Estimated Revenue Risk | **₱18.09M** | Conservative misclassification cost across 5,055 evaluated records |
| Corporate Recall | **100%** | Highest-penalty segment captured perfectly |
| Micro-Clusters Found | **78** | Mapped to 10 named segments |
| Records Processed | **10,000** | Full pipeline, zero manual steps |

### Per-Segment Recall (POC)

NFR-01 target: **≥ 91%**

| Segment | Recall | vs. Target | Penalty |
|---------|:------:|:----------:|:-------:|
| Corporate | 100% | ✓ Above | ×10 |
| Family | 99% | ✓ Above | ×2 |
| Digital Nomad | 95% | ✓ Above | ×2 |
| Last-Minute | 91% | ✓ At target | ×1 |
| Balikbayan/VFR | 73% | ✗ Below | ×2 |
| Mabuhay Loyalist | 63% | ✗ Below | ×8 |
| Pilgrimage | 54% | ✗ Below | ×3 |
| Premium Bleisure | 38% | ✗ Below | ×4 |
| Budget/Adventure | 22% | ✗ Below | ×1 |
| OFW/Migrant | 18% | ✗ Below | ×5 |

### Why OFW and Budget Recall Is Low

OFW, Budget, and Balikbayan passengers overlap heavily in booking behaviour (economy, bags, price). Without the Mabuhay Miles loyalty field, the model cannot disambiguate them. **One data field — loyalty tier — is the single biggest unlock for improving these scores.**

---

## 7. Data Sources

| Dataset | File | Records | Purpose |
|---------|------|--------:|---------|
| Real PAL bookings (Jan 2025 snapshot) | `data/raw/sample-features.csv` | 29,999 | Main pipeline development and algorithm evaluation |
| Synthetic POC dataset | `data/raw/synthetic_flight_passenger_data.csv` | 10,000 | POC validation on PAL-structure data |
| **PNR-level prototype (v3)** | `data/raw/PAL_PNR_Synthetic_Data_1000-v3.csv` | 1,000 | New 41-field PNR/coupon schema for clustering prototype — see §15 (2026-07-17) for profile, quirks, buildable features. Dictionary: `...-v2.csv` |

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
| `poc_synthetic.py` | Full 8-stage pipeline on synthetic POC data |
| `pal_colors.py` | Canonical 10-segment colour palette (import this everywhere) |
| `generate_dark_slides.py` | Generates 3 dark-themed POC output PNGs |
| `generate_report.py` | Generates `PAL_EDA_Report.html` |
| `capture_slides.py` | Playwright: exports executive HTML deck as PNGs |

### Data Files

| File | Records | Description |
|------|--------:|-------------|
| `sample-features.csv` | 29,999 | Real PAL bookings — Jan 2025 snapshot |
| `synthetic_flight_passenger_data.csv` | 10,000 | Synthetic PAL-structure data for POC |

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
| 10,000 | Synthetic POC records |
| 77.7% | POC overall accuracy |
| 100% | POC Corporate recall |
| 18% | POC OFW/Migrant recall (lowest — loyalty data gap) |
| ₱18.09M | POC estimated revenue risk |
| 91% | NFR-01 recall target (the red line) |
| 5 | Years of historical PAL data available for full retrain |
| 6M | Estimated full PAL PNR records for production pipeline |

---

## 15. Learning Log (Living)

> Append-only working memory. Newest first. Entry format:
> `#### YYYY-MM-DD — Title` · **Domain** · learning · **Source**.

---

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
**Results:** train discovery 2 clusters, 53.4% noise, DBCV −0.072 (structure still absent — data
unchanged, as expected). HOLD-OUT recall vs proxy: Last-Minute/Premium Bleisure 100%, Family 67%,
Digital Nomad/Budget 64%, Corporate 61%, Balikbayan 58% (cost 114, 1.31/record, n=87). Out-of-sample ≈
in-sample → the labeller generalises; the ceiling is set by rules/data, not memorisation. **Recall stays
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

#### 2026-07-17 — DIAGNOSIS: v3 synthetic data has no latent cluster structure
**Domain:** Clustering / Methodology
`src/diagnose_v3.py` stress-tested the data with **non-circular** metrics on a cleaned 24-feature space
(dropped 19 |corr|>0.9 redundancies). Result is conclusive: **DBCV is NEGATIVE** across every config
(−0.043 to −0.192, incl. PCA-90) — worse-than-random density validity, i.e. no real clusters. KMeans
silhouette is flat ~0.10 with **no peak** (k4=0.103…k12=0.121, monotonic) → no natural k. **Bootstrap
ARI is high (0.83–0.99) but that is a TRAP** — it means HDBSCAN is *consistent*, not that clusters are
*real*; a stable partition of a structureless cloud is still meaningless (stability ≠ validity).
**Implications:** (1) the shipped recall (53–100%) is circular — it measures rediscovery of the proxy
rules on the same features, not accuracy; do NOT present it as model quality to PAL. (2) On this data,
segments are **definitional (rule-driven), not emergent** — ML's role is label propagation/refinement/
drift-monitoring on top of rules, not unsupervised discovery. (3) Penalty-weighting *lowered* DBCV
(0.030→0.023) — it bends space toward the rules. **#1 recommendation: real / structure-embedding data.**
Full write-up: `docs/v3-prototype-findings.md`.
**Source:** `src/diagnose_v3.py`; outputs/diagnose_v3_output/diagnosis.json.

#### 2026-07-17 — Built src/prototype_v3.py (Stages P4–P5); end-to-end prototype runs
**Domain:** Clustering / Methodology
`src/prototype_v3.py` runs P4–P5: StandardScaler → penalty-weighted HDBSCAN (min_cluster_size=30,
min_samples=5) → nearest-centroid cluster→segment mapping + noise auto-assignment → cost-matrix +
DBCV validation. Reuses `monitor_metrics.dbcv` and `pal_colors`. **Results on v3 (1k rows):**
8 micro-clusters, 42.1% noise; DBCV 0.023, silhouette 0.235, Davies-Bouldin 1.465; per-segment recall
vs proxy seeds — Balikbayan/VFR 100%, Digital Nomad 100%, Budget 87%, Last-Minute 75%, Family 63%,
Corporate 61%, Premium Bleisure 53% (weighted cost 527, 1.15/labelled record). **Read as prototype
validation of the *approach*, not production metrics** — 1k rows is small, noise is high, and Corporate
(×10) at 61% is below the 91% target. 3 segments unassignable (no seed): Mabuhay Loyalist, OFW/Migrant,
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
**Key finding — 3 segments get ~0 proxy seeds on the v3 synthetic data:** OFW/Migrant (its
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
(comma silently breaks suppression); (2) deterministic MD5 for synthetic-data hashing → use
`hashlib.md5(..., usedforsecurity=False)` to clear the B324 HIGH finding legitimately; (3) `zip()`
strict-check (B905) is ignored — 41 hits in plotting code where lengths are known equal.
Tools pinned in pre-commit: pre-commit-hooks v6.0.0, ruff v0.15.22, bandit 1.9.4.
**Source:** our setup + first-pass run; `README.md` §Code quality.

#### 2026-07-17 — methodology.md v0.5 adds the v3 prototype pipeline
**Domain:** Project Decision
`docs/methodology.md` bumped to **v0.5**: the validated v0.4 pipeline on `sample-features.csv` is kept
as the baseline/reference; a new **"v3 Prototype Pipeline — PNR-Level Anonymous Segmentation"** section
documents the adapted stages (P1 clean → P2 features → P3 v3 proxy waterfall → P4 penalty-weighted
HDBSCAN + mapping → P5 validate), plus the phase→deliverable map. HDBSCAN is recorded as the closed
algorithm decision (leaderboard re-run is confirmatory only).
**Source:** our update; `docs/methodology.md` §v3 Prototype Pipeline.

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
time** — which our v3 data lacks (every `Unique Identifier` is a unique single coupon). So we have a
strong **Monetary** axis (NetRevenue, NetFare, ancillary) but **cannot compute R or F** without
stitching bookings via name+DOB or a frequent-flyer number. This is the same "No RFM history" gap the
methodology already flagged. Consequence: model at the PNR level, not customer-lifetime.
**Source:** RFM airline value studies (ResearchGate); "Estimating travellers' value… auxiliary
services (RFM)", J. Retailing & Consumer Services 2023; our analysis of v3.

#### 2026-07-17 — v3 dataset profile, quirks, and buildable features
**Domain:** Data & Features
`data/raw/PAL_PNR_Synthetic_Data_1000-v3.csv` — PNR/coupon-level, **1,000 rows × 41 fields, 100%
populated (no nulls)**. `...-v2.csv` is its data dictionary.
**Cleaning quirks (do NOT reuse sample-features code as-is):** header col 4 malformed `CouponNumber] `;
`NetRevenue`/`NetFare` are strings with a **`$` suffix** (`574$`); dates are US-style **`M/D/YY`**
(`dayfirst=False` — opposite of the sample-features pipeline); `Group/Individual` is text
(`Individual`/`Group`, 62/38); `PaxCount` is **always 1**; `OperatingCabinClass` is combined
`Economy/X`; `Unique Identifier` is unique per row (no multi-coupon grouping).
**Buildable features:** value — net_fare, net_revenue, **ancillary = Rev−Fare** (100% positive,
median $77, max $1,012), fare_tier (19 RBDs); timing — **lead_time** (1–180 d, med 93), dep_hour /
red-eye, dep_dow / is_weekend, booking_month / peak-season, changed_itinerary (Exchanged status);
route — cabin_ord (Econ 790/PremEcon 104/Bus 106), is_domestic/haul_type, is_codeshare (45%),
n_connections/is_connecting (83% nonstop), **pos_mismatch** (CountryCodeOfIssue≠PointofOrigin → OFW/VFR);
party/channel — age_band (2–85; child age 2 present), is_group, gender, is_direct vs is_gds (GDS 10%).
**Not derivable from v3:** ❌ length-of-stay / Saturday-night-stay (no return-leg pairing);
❌ RFM Recency/Frequency (no passenger key); ❌ loyalty tier.
**Source:** our profiling script (`scratchpad/profile_v3.py`) on the v3 file.

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
*Last updated: 17 July 2026*
