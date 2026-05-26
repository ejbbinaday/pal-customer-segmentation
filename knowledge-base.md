# PAL Customer Segmentation — Knowledge Base

**Project:** Optimized Market Segmentation for Philippine Airlines
**Team:** Edyll Joshua Binaday, Jeremy Jay Lim, Arien Jadd Versoza, Martin Aloysius Yamzon (PL)
**Version:** v1.0 — May 2026

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
| Real PAL bookings (Jan 2025 snapshot) | `sample-features.csv` | 29,999 | Main pipeline development and algorithm evaluation |
| Synthetic POC dataset | `synthetic_flight_passenger_data.csv` | 10,000 | POC validation on PAL-structure data |

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

*Knowledge base maintained by CPT 3 — PAL Customer Segmentation*
*Last updated: May 2026*
