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
**8 distinct values exist across the whole extract**, 99.7% of them `-7`. It therefore carries **zero
booking-timing information** and cannot distinguish "booked 60 days out" from "booked 3 days out".
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
the old `sample-features` baseline and the v3 *synthetic* prototype — misleading to reuse). So
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
"Dictionary reconciliation" and "SME rule" entries below**, which were based on the stale synthetic-set
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
Reconciled the real extract against the data dictionary (`data/raw/PAL_PNR_Synthetic_Data_1000-v2.csv`)
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
richer than the 1,000-row v3 synthetic prototype and should become the real modelling input.
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
*Last updated: 29 July 2026*
