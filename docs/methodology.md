# PAL Customer Segmentation — ML Pipeline Methodology

**Client:** Philippine Airlines (PAL)
**Version:** v0.7 — 23 July 2026

> **Changelog**
> - **v0.7 (23 Jul 2026):** Added the [Tools & Libraries disclosure](#tools--libraries-disclosure); reconciled the header version with the footer (was drifting at v0.5 vs v0.6).
> - **v0.6 (23 Jul 2026):** Real-data track pivot — rule-based purpose×value segmentation is primary, LCA refines/validates; HDBSCAN dropped for the real data. Added the real-data at-a-glance summary.
> - **v0.5 (17 Jul 2026):** Added the [v3 Prototype Pipeline](#v3-prototype-pipeline--pnr-level-anonymous-segmentation) — the adapted pipeline for the new PNR-level `PAL_PNR_Synthetic_Data_1000-v3.csv` schema. Baseline (v0.4) pipeline on `sample-features.csv` retained unchanged below as the reference implementation.
> - **v0.4 (11 May 2026):** Baseline 8-stage pipeline on `sample-features.csv`.

---

## Current Methodology at a Glance

**Active track — the Real-Data Pipeline** (real 38M-coupon extract, 2024–2027; anonymous
trip-purpose × value segmentation at the **booking** grain, rolled up to **customer**):

```
gz → typed Parquet → Stage C clean+flag (coupon grain)
→ Stage F features: coupon → booking (customer_id, issue_date) → customer  (+ airport→region join)
→ RULE-BASED purpose×value proxy segmentation  ← PRIMARY deliverable (the 10 segments)
→ LCA refinement (sub-segment oversized groups; validate axes)  ← ML's role
→ pending SME ground-truth for non-circular validation
```

- **Approach decision (2026-07-23, evidence-based):** a mixed-type clustering diagnostic
  (`src/cluster_diagnostic.py`: LCA + k-prototypes) showed the customer base is a **continuum**
  (BIC has no elbow — no natural *k*) whose structure follows the rule axes (route / direction / value /
  timing), with only moderate cluster–taxonomy agreement (ARI ≈ 0.2–0.34). **So the rule-based
  segmentation is primary; clustering (LCA) refines and validates — it is NOT the labeler.**
  **HDBSCAN is dropped for the real data** (categorical-heavy → not density-separable).
- **Model:** the 10 named segments (Corporate, Mabuhay Loyalist, OFW/Migrant, Balikbayan/VFR, Pilgrimage,
  Family, Premium Bleisure, Budget/Adventure, Last-Minute, Digital Nomad) + an Unassigned bucket.
  Value = authoritative **farebrand tier** (V1 dictionary). Validation stays **proxy-referenced (circular)**
  until SME labels (`data/labels/sme_sample.csv`) land.
- **Code:** `src/build_parquet.py` · `src/clean_real.py` (C) · `src/build_airport_ref.py` ·
  `src/features_real.py` (F) · `src/cluster_diagnostic.py` (method choice). Full plan:
  `docs/real-data-plan.md`; data dictionary: `docs/data-dictionary.md`.
- **Prior tracks (kept for reference, superseded for real data):** the **v3 prototype**
  (synthetic 1k, HDBSCAN — see below) and the **Stages 1–8** `sample-features.csv` baseline. On the v3
  synthetic data HDBSCAN also found no density structure (DBCV ≈ 0), which pre-figured this pivot.

Full detail: [v3 Prototype Pipeline](#v3-prototype-pipeline--pnr-level-anonymous-segmentation) (prior);
real-data methodology → `docs/real-data-plan.md`.

---

## Tools & Libraries (disclosure)

The whole pipeline is plain **Python 3.14** and open-source end to end — there is no proprietary
analytics platform in the loop. The guiding idea: use a heavy-data engine only where the 38M rows
genuinely need one, and keep the modelling itself on familiar, well-audited libraries so the results
are reproducible and easy to hand over. Read this table as *"what each tool is for and why it earns
its place"* rather than a bare dependency list.

| Layer | What we use | Version | What it does / why it's here |
|-------|-------------|---------|------------------------------|
| Language | **Python** | 3.14 | Every script in `src/` (wheels also fine on 3.11–3.13) |
| Heavy data (out-of-core) | **DuckDB** | 1.5.5 | Streams the 38M-coupon gzip and does the coupon → booking → customer aggregation *without* loading it all into memory |
| Columnar storage | **PyArrow** / Parquet | 25.0.0 | Fast typed intermediates in `data/interim/` — sub-second re-reads instead of minutes re-scanning raw gzip |
| Dataframes & math | **pandas** · **NumPy** | 3.0.3 · 2.5.1 | Work on the *aggregated* model-grain table (millions of rows, not tens of millions) |
| Clustering — model-based | **StepMix** (Latent Class Analysis) | 3.0.0 | The refinement layer: finds sub-types inside big segments and tests for natural structure via BIC |
| Clustering — mixed-type | **kmodes** (k-prototypes) | 0.12.2 | Independent cross-check in the diagnostic; handles numeric + categorical features together |
| ML utilities | **scikit-learn** · **SciPy** | 1.9.0 · 1.18.0 | Feature scaling, PCA projection, Adjusted Rand Index, cost metrics |
| Charts | **matplotlib** · **seaborn** | 3.11.0 · 0.13.2 | Every figure; shared segment palette in `src/pal_colors.py` |
| Report build | base64 + headless **Google Chrome** | — | Embeds figures and renders `docs/status-report.pdf` (`src/build_report.py`) |
| Markdown tables | **tabulate** | 0.10.0 | Renders the tables in the `outputs/*/summary.md` files |
| Code quality | **ruff** · **bandit** · **pre-commit** | — | Lint, format, and security-scan every script before it lands |
| Reproducibility pins | joblib · threadpoolctl | 1.5.3 · 3.6.0 | Pinned so clustering output is deterministic run to run |

Full pinned lists live in `requirements-pipeline.txt` (analysis) and `requirements-dev.txt` (tooling).

**Retired for the real-data track (kept for the prior prototypes):** `hdbscan` 0.8.44 and
`imbalanced-learn` 0.14.2 powered the earlier HDBSCAN clustering and resampling experiments. They are no
longer part of the real-data method (see the 2026-07-23 decision) but stay installed so the older tracks
still run for reference.

**Authoritative reference (not a library):** `DataDictionary.v1.xlsx` — the client's V1 data dictionary —
governs every field's meaning and the farebrand value ladder, and is mirrored to `docs/data-dictionary.md`.

---

## Overview

This document describes the end-to-end machine learning pipeline for the PAL Customer Segmentation project. The objective is to produce a baseline segmentation model over PNR booking data, assigning each booking record to one of ten commercially meaningful customer segments. The pipeline combines rule-based proxy labelling, density-based clustering, penalty-weighted feature scaling, and direct nearest-centroid assignment for ambiguous records.

**Two tracks.** The **baseline pipeline** (Stages 1–8, below) is validated on the real Jan-2025 `sample-features.csv` snapshot. The **[v3 prototype pipeline](#v3-prototype-pipeline--pnr-level-anonymous-segmentation)** adapts that same architecture to the richer PNR/coupon-level `PAL_PNR_Synthetic_Data_1000-v3.csv` schema and frames the work explicitly as **anonymous trip-purpose × value segmentation** at the booking level (Sabre's "anonymous" lens — no loyalty/CRM join). It is the current active track.

---

## Target Segments

The model targets ten segments:

| # | Segment | Penalty Weight |
|---|---------|---------------|
| 1 | Corporate | ×10 |
| 2 | Mabuhay Loyalist | ×8 |
| 3 | OFW/Migrant | ×5 |
| 4 | Premium Bleisure | ×4 |
| 5 | Pilgrimage | ×3 |
| 6 | Balikbayan/VFR | ×2 |
| 7 | Family | ×2 |
| 8 | Digital Nomad | ×2 |
| 9 | Last-Minute | ×1 |
| 10 | Budget/Adventure | ×1 |

Penalty weights reflect the business cost of misclassifying a record into the wrong segment. Higher-penalty segments (Corporate, Mabuhay Loyalist, OFW/Migrant) demand greater recall and drive the penalty-weighted feature scaling in Stage 5.

---

## Source Data

| Property | Value |
|----------|-------|
| File | `sample-features.csv` |
| Rows | 29,999 |
| Columns | 27 |
| Target column | `Market Segment` — 100% null (no ground-truth labels exist) |

### Known Data Gaps (Blocking)

The following fields are present in the schema but contain no data in the current extract. Each gap limits one or more proxy segmentation signals:

| Feature | Limits |
|---------|--------|
| `Loyalty status` | Mabuhay Loyalist segment; strengthens Corporate and OFW proxy separation |
| `Length of stay` | Corporate vs. Leisure separation; Digital Nomad identification |
| `Departure Time` | Early-AM Corporate signal |
| `Cargo/baggage add-on` | OFW/Balikbayan confirmation signal |

Until these fields are populated from source systems, the Mabuhay Loyalist segment cannot be assigned via proxy labelling.

---

## Pipeline Stages

### Stage 1 — Data Ingestion & Cleaning

**Script:** `eda_graphs.py`

Load the raw extract and apply the following cleaning steps:

1. Load `sample-features.csv`.
2. Strip the `$` prefix from `Average Fare` and cast to `float`.
3. Parse `PNRCreationDate` and `Flight Date` as `datetime` with `dayfirst=True`.
4. Drop records where `PNRCreationDate` is null — **14 records removed (0.05%)**.

Post-cleaning row count: **29,985**.

---

### Stage 2 — Feature Engineering

**Script:** `eda_graphs.py`, `eda_segments.py`

Derived features are computed from the cleaned raw columns and appended to the feature matrix:

| Derived Feature | Definition |
|-----------------|------------|
| `lead_time` | `Flight Date` − `PNRCreationDate` (days) |
| `fare_per_pax` | `Average Fare` / `PAX Count` |
| `booking_month` | Month extracted from `PNRCreationDate` |
| `cabin_ord` | Ordinal encoding of Cabin: Y=0, W=1, J=2 |
| `is_dom` | Binary flag: 1 if Entity == `DOM`, else 0 |

Categorical encoding:

- **One-hot encoded:** Region, Farebrand, Itinerary Type, Ticketing Channel

Normalisation: all features are scaled with `StandardScaler` before clustering.

**Final feature matrix: 29,985 rows × 40 features.**

---

### Stage 3 — Proxy Label Assignment (Priority Waterfall)

**Script:** `eda_segments.py`

Because no ground-truth labels exist, a rule-based waterfall assigns proxy labels to create training seeds. Rules are applied in priority order; a higher-priority rule overwrites a lower-priority assignment if both match.

| Priority | Segment | Rule |
|----------|---------|------|
| 1 (lowest) | Budget/Adventure | Farebrand in {Economy Supersaver, Economy Saver} |
| 2 | Digital Nomad | PAX == 1 AND Region == ASEAN AND Channel in {WEB, APP} AND Farebrand in {Flex, Value} |
| 3 | Last-Minute | `lead_time` ≤ 3 days |
| 4 | Family | PAX Count between 3 and 5 |
| 5 | Pilgrimage | PAX Count ≥ 4 AND Channel == Traditional Travel Agency |
| 6 | Balikbayan/VFR | Itinerary Type == `Beyonds (INT - DOM)` |
| 7 | OFW/Migrant | Region == Middle East OR Channel == Sea Crew |
| 8 | Premium Bleisure | Cabin == W |
| 9 (highest) | Corporate | Cabin == J |

**Mabuhay Loyalist** has no active proxy rule due to the null `Loyalty status` field.

**Proxy label result:**

| Status | Count | Share |
|--------|-------|-------|
| Labelled | 22,907 | 76.4% |
| Unassigned | 7,084 | 23.6% |
| **Total** | **29,985** | **100%** |

**Note on resampling:** Five resampling strategies (Random Oversample, Undersample, SMOTE, ADASYN, Tomek Links) were evaluated and rejected. Proxy labels are derived from the same features used for classification, so F1 scores of 0.99+ reflect the model re-learning the labelling rules — not a generalisation signal. Class imbalance is handled downstream via the asymmetric penalty matrix in Stage 7.

---

### Stage 4 — Clustering Algorithm Evaluation

**Script:** `cluster_compare.py`

Seven algorithms were evaluated on the full 40-feature scaled matrix. The target was 10 interpretable clusters corresponding to the ten segments.

| Algorithm | Silhouette ↑ | Davies-Bouldin ↓ | Calinski-Harabasz ↑ | Clusters | Noise % |
|-----------|-------------|-----------------|---------------------|----------|---------|
| KMeans | 0.167 | 1.721 | 1,864 | 10 | 0.0% |
| MiniBatchKMeans | 0.136 | 1.976 | 1,668 | 10 | 0.0% |
| GMM | 0.114 | 2.004 | 1,559 | 10 | 0.0% |
| Agglomerative (Ward) | 0.151 | 1.765 | 1,835 | 10 | 0.0% |
| DBSCAN | 0.554 | 0.774 | 1,738 | 221 | 7.9% |
| **HDBSCAN** ★ | **0.435** | **0.961** | 1,554 | **78** | **7.1%** |
| Birch | 0.247 | 1.303 | 1,336 | 10 | 0.0% |

**Decision: HDBSCAN selected.** Rationale:

1. Does not assume spherical clusters — follows actual density contours in feature space.
2. Naturally identifies noise (7.1% ≈ 2,100 records) — genuine boundary cases that are resolved by nearest-centroid assignment rather than forced cluster membership.
3. 78 micro-clusters can be merged to 10 named segments via nearest-centroid mapping (Stage 6).
4. KMeans forces every borderline record into its nearest centroid, silently polluting proxy seeds. HDBSCAN flags them as noise instead, surfacing the ambiguity explicitly.

---

### Stage 5 — Penalty-Weighted Feature Scaling

**Script:** `hdbscan_final.py`

Before fitting HDBSCAN, features are re-scaled according to their discriminative power for high-penalty segments. This ensures that features critical to identifying Corporate or OFW/Migrant bookings carry proportionally greater weight in the HDBSCAN distance metric.

**Procedure:**

```
For each segment s with penalty weight p(s):
    Compute the segment centroid in StandardScaler space
    For each feature f:
        weight[f] += (p(s) / total_penalty) × |mean(f | segment == s)|

Normalise weight vector to mean = 1
Apply weights to scaled feature matrix before HDBSCAN fit
```

**Effect:** Features that strongly identify Corporate bookings (`cabin_ord`, TMC channel, short `lead_time`) and OFW/Migrant bookings (Middle East region, TTA channel, long `lead_time`) receive higher weight in the distance metric. This tightens the corresponding clusters and improves their separation from the high-volume Budget/Adventure mass.

---

### Stage 6 — Cluster → Segment Mapping & Noise Assignment

**Script:** `hdbscan_final.py`

HDBSCAN returns 78 micro-clusters plus a noise set (label = −1). This stage maps all records — micro-clusters and noise alike — to the ten named segments.

**Micro-cluster assignment:**

1. Compute the centroid of each HDBSCAN cluster in penalty-weighted feature space.
2. Compute the centroid of each proxy-labelled segment (from Stage 3) in the same space.
3. Assign each cluster to its nearest segment centroid by Euclidean distance.

**Noise record assignment:**

Records with label = −1 (~7.1% of the dataset) are automatically assigned to their nearest segment centroid using the same penalty-weighted feature space. This is consistent with the micro-cluster assignment logic and requires no human intervention. The penalty-weighted distance metric already biases the space so that high-stakes segments (Corporate, OFW/Migrant) pull nearby ambiguous records correctly.

**Result:** All 29,985 records receive a final segment label. No records remain unassigned.

---

### Stage 7 — Validate (Asymmetric Cost Matrix)

Final label quality is evaluated using the segment penalty matrix rather than standard accuracy or macro-F1.

**Metrics reported:**

| Metric | Definition |
|--------|------------|
| Total weighted cost | Sum of `penalty_weight[true_segment]` for all misclassified records |
| Cost per record | Total weighted cost / total records |
| Per-segment recall | Recall computed separately for each of the ten segments |

**Optimisation target:** maximise recall for Corporate (×10) and OFW/Migrant (×5), the two segments where misclassification carries the highest business cost.

---

### Stage 8 — Dashboard (Power BI)

**Deliverable:** Executive Power BI dashboard at Origin & Destination (O&D) level, segmented by travel month.

| Component | Detail |
|-----------|--------|
| Filters/slicers | Segment, travel month, O&D pair |
| Segment mix | Share of bookings per segment per route |
| Average fare per segment | Fare distribution by segment |
| Lead time distribution | Booking horizon by segment |
| Route × segment heatmap | Cross-tabulation of route and segment volume |

---

## Scripts Reference

| Script | Purpose | Output |
|--------|---------|--------|
| `eda_graphs.py` | Dataset-level EDA | Figs 01–22 |
| `eda_segments.py` | Proxy-segment EDA | Figs 23–35 |
| `cluster_initial.py` | KMeans k=10 baseline, centroid heatmap, radar, PCA | Baseline clustering artefacts |
| `cluster_compare.py` | 7-algorithm comparison, leaderboard | Algorithm comparison table |
| `resample_compare.py` | 5 resampling strategies comparison | Resampling evaluation (rejected) |
| `dbscan_viz.py` | DBSCAN deep-dive | 8 charts |
| `pca_boundaries.py` | Decision boundary visualisation, per-segment zoom grid | Boundary plots |
| `hdbscan_final.py` | HDBSCAN with penalty-weighted features, segment mapping, noise auto-assignment | Final cluster assignments |
| `pal_colors.py` | Canonical 10-segment colour palette | Shared colour constants |

---

## Pipeline Summary

```
sample-features.csv
        |
        v
[Stage 1] Ingest & Clean          29,999 → 29,985 rows
        |
        v
[Stage 2] Feature Engineering     29,985 × 40 features, StandardScaler
        |
        v
[Stage 3] Proxy Label Waterfall   22,907 labelled / 7,084 Unassigned
        |
        v
[Stage 4] Algorithm Comparison    HDBSCAN selected
        |
        v
[Stage 5] Penalty-Weighted Scaling
        |
        v
[Stage 6] Cluster → Segment Map   78 micro-clusters → 10 segments
          + Noise Auto-Assignment  ~2,100 noise → nearest centroid
        |
        v
[Stage 7] Validate                Asymmetric cost matrix, per-segment recall
        |
        v
[Stage 8] Power BI Dashboard      O&D × segment × travel month
```

---

## v3 Prototype Pipeline — PNR-Level Anonymous Segmentation

**Added v0.5 (17 Jul 2026).** This section adapts the baseline architecture (Stages 1–8) to the new
PNR/coupon-level dataset. It reuses the winning method — proxy waterfall → penalty-weighted HDBSCAN →
nearest-centroid mapping + noise auto-assignment → cost-matrix validation — but re-derives every
schema-dependent step for the v3 columns.

### Framing

Because v3 has **no loyalty/CRM join**, this model is Sabre's **"anonymous segmentation" lens**:
each *booking* is segmented by **trip purpose × value** from observable attributes alone. This is a
named, defensible industry approach — not a limitation to apologise for. It is *booking-level*, not
customer-lifetime, segmentation. (See `knowledge-base.md` §15, 2026-07-17 entries, for sources.)

### Source Data (v3)

| Property | Value |
|----------|-------|
| File | `data/raw/PAL_PNR_Synthetic_Data_1000-v3.csv` |
| Dictionary | `data/raw/PAL_PNR_Synthetic_Data_1000-v2.csv` (`Field, Description`) |
| Rows | 1,000 (coupon-level; one coupon per `Unique Identifier`) |
| Columns | 41 — **100% populated (no nulls)** |
| Scope | Validates the *approach*, not production-grade metrics (n is small) |

### Stage P1 — Ingest & Clean (v3 quirks)

The v3 schema differs from `sample-features.csv`; **do not reuse the baseline cleaning code**:

| Quirk | Handling |
|-------|----------|
| Header col 4 malformed: `CouponNumber] ` | strip `]` and whitespace from all headers |
| `NetRevenue` / `NetFare` are strings with a **`$` suffix** (`574$`) | strip trailing `$`, cast to float |
| Dates are US-style **`M/D/YY`** | parse with `dayfirst=False` (**opposite** of baseline) |
| `Group/Individual` is text (`Individual`/`Group`) | map to binary `is_group` |
| `OperatingCabinClass` is combined `Economy/X` | split into cabin + booking class |
| `PaxCount` is always `1` | do **not** use party size; use `is_group` + child age instead |

### Stage P2 — Feature Engineering (v3)

Framed on the industry's highest-signal booking attributes (advance purchase, cabin/fare class,
channel, yield + ancillary). All features below are derivable and fully populated in v3.

| Group | Features | Segment signal |
|-------|----------|----------------|
| **Value / Monetary** | `net_fare`, `net_revenue`, **`ancillary = net_revenue − net_fare`** (100% > 0, median $77), `ancillary_ratio`, `fare_tier` (from 19 RBDs) | value tier; premium/leisure add-on propensity |
| **Timing** | **`lead_time`** = Departure − Issuance (1–180 d), `dep_hour` / `red_eye`, `dep_dow` / `is_weekend`, `booking_month` / `is_peak_season`, `changed_itinerary` (Exchanged status) | business (short lead, red-eye, weekday) vs leisure |
| **Product / route** | `cabin_ord` (Econ 0 / PremEcon 1 / Bus 2), `is_domestic` / `haul_type`, `is_codeshare` (`TripOD≠OnlineOD`), `n_connections` / `is_connecting`, **`pos_mismatch`** (`CountryCodeOfIssue≠PointofOrigin`) | premium vs budget; OFW/VFR diaspora |
| **Party / demo / channel** | `age_band` (child<12 … senior 60+), `is_group`, `gender`, `is_direct` vs **`is_gds`** | family/pilgrimage; corporate (GDS) |

Normalisation: `StandardScaler`, then penalty re-weighting (Stage P4).

**Not derivable from v3 (documented gaps):**

| Gap | Reason |
|-----|--------|
| Length-of-stay / Saturday-night-stay | no return-leg pairing (each row is a single unique coupon) |
| RFM **Recency & Frequency** | no passenger key linking bookings across time (only **Monetary** available) |
| Loyalty tier | absent → **Mabuhay Loyalist** remains un-proxyable (same as baseline) |

### Stage P3 — Proxy Label Waterfall (v3 rules)

The baseline §Stage-3 rules are re-mapped to v3 columns. Rules that depended on PAX count or
Farebrand (absent/constant in v3) are substituted with the `Group/Individual` flag and RBD/fare tiers.
Applied low → high priority; higher overwrites lower.

| Priority | Segment | v3 Rule |
|:--------:|---------|---------|
| 1 (lowest) | Budget/Adventure | deep-discount RBD (O/X/T/Q/V/S/L) + Economy + OTA channel |
| 2 | Digital Nomad | solo `Individual` + regional/ASEAN O&D + digital channel (Website/App) + long lead |
| 3 | Last-Minute | `lead_time` ≤ 3–7 days |
| 4 | Family | `is_group` + leisure timing (weekend) + Economy |
| 5 | Pilgrimage | `is_group` + Gulf/pilgrimage destination + peak season |
| 6 | Balikbayan/VFR | destination PH + foreign origin + long-haul + Economy |
| 7 | OFW/Migrant | `pos_mismatch` (issued abroad) + Gulf/diaspora origin + one-way/long-haul |
| 8 | Premium Bleisure | Premium-Economy/Business cabin + weekend + high ancillary |
| 9 (highest) | Corporate | Business cabin **or** full-fare Y + GDS channel + short lead + weekday early-AM |
| — | Mabuhay Loyalist | *no rule — loyalty field absent* |

### Stage P3b — Negative Learning (impossibility filters)

Applied after the waterfall to send contradictory assignments back to `Unassigned` (baseline KB §9,
re-mapped to v3 fields since loyalty/bags/income are absent). Implemented in `features_v3.apply_negative_learning`:

| Assigned segment | Contradiction → Unassigned |
|---|---|
| Corporate | `lead_time` > 60 **and** Economy cabin (booked far ahead in economy) |
| Corporate | booked via **OTA** (corporate flows through GDS / direct) |
| Digital Nomad | `is_group` (nomad is solo by definition) |
| Premium Bleisure | bottom-quartile ancillary (contradicts the premium-spend signal) |

### Stage P4 — HDBSCAN Discovery + Inductive Labelling (improved)

The first pass penalty-weighted the feature space before clustering; diagnostics showed this *lowered*
DBCV (it bends space toward the proxy rules). The improved design **decouples discovery from priorities**:

1. **Compact features (Tier-3):** cluster the 24-feature subspace (`build_compact_matrix`), dropping the
   19 collinear/duplicate columns. **Mixed-type scaling:** StandardScaler on continuous columns only;
   binary flags stay `{0,1}`.
2. **Hold-out split:** fit everything on train; score a held-out test set inductively.
3. **Unweighted HDBSCAN discovery** (`min_cluster_size` scaled to N — ~30–50 @1k, 150 @30k,
   500–1,000 @6M) — used only to *assess whether density structure exists* (DBCV / silhouette).
4. **Inductive labelling:** compute proxy-seed segment centroids on **train**; assign any row (train,
   noise, or held-out) to its nearest centroid. **Penalties enter only in the P5 cost metric**, not the
   distance.
5. **Unassigned bucket:** rows past the 95th-percentile train distance are left low-confidence rather
   than force-assigned. The deployable scorer = `(scaler + centroids + threshold)`.

### Stage P5 — Validate & Cross-Check

- **Primary:** asymmetric cost matrix + **per-segment recall**, reported on the **held-out** set
  (out-of-sample), optimising Corporate ×10 / OFW ×5.
- **Cluster quality:** DBCV (primary for HDBSCAN), Silhouette, bootstrap ARI (`diagnose_v3.py`).
- **Ground truth:** drop `data/labels/sme_sample.csv` (`Unique Identifier`,`true_segment`) and P5 adds a
  **non-circular** SME hold-out recall automatically. Until then, recall is proxy-referenced (circular).
- **Cross-check:** profile segments against the industry taxonomy (`knowledge-base.md` §15) and flag the
  structural gaps (3 unseeded segments; no latent density structure in the v3 synthetic data).

### Phase → Deliverable mapping

| Phase | Baseline stage | Deliverable |
|-------|----------------|-------------|
| P0 Loader/clean | Stage 1 | `src/features_v3.py` |
| P1 Feature engineering | Stage 2 | `src/features_v3.py` |
| P2 Proxy waterfall | Stage 3 | `src/features_v3.py` (v3 rules) |
| P3 Cluster + map | Stages 5–6 | prototype clustering script (e.g. `src/prototype_v3.py`) |
| P4 Validate | Stage 7 | cost-matrix + per-segment recall report |
| P5 Profile/cross-check | — | segment profiles vs industry taxonomy |

> **Algorithm decision is closed:** HDBSCAN is the plan of record (Stage 4). Re-running the
> 7-algorithm leaderboard on v3 is *confirmatory only*, not a re-opening of the choice.
>
> **⚠️ Superseded for the real-data track (2026-07-23).** On the real 38M-coupon data, the mixed-type
> diagnostic showed a continuum with no natural *k* and only moderate cluster–taxonomy agreement, so
> **HDBSCAN is dropped there**: the rule-based purpose×value segmentation is primary and **LCA** refines/
> validates (see the at-a-glance and `docs/real-data-plan.md`). This note applies to the v3/synthetic and
> `sample-features` tracks only.

---

## Current Limitations (Sample Data)

The current pipeline runs on a **29,999-row January 2025 snapshot**. Key constraints:

| Limitation | Impact |
|-----------|--------|
| All flight dates are January 2025 only | Seasonality signals (Pilgrimage, Balikbayan, OFW deployment) cannot be validated on flight date |
| `Loyalty status`, `Departure Time`, `Length of stay` are 100% null | Mabuhay Loyalist has zero proxy-labelled records; Corporate and OFW proxy rules are weaker |
| No RFM history | Booking frequency and recency cannot be computed per passenger |
| No cargo/ancillary flags | OFW/Balikbayan confirmation signal is absent |

---

## Next Steps — Scaling to Full Historical Data

PAL holds **~6 million PNR records spanning 5 years**. The following actions are recommended in priority order.

### Immediate (Blocking)

| Action | Reason |
|--------|--------|
| Request `Loyalty status` (Mabuhay Miles tier) from PAL | Unlocks Mabuhay Loyalist segment; strengthens Corporate and OFW proxy rules |
| Request flight schedule data | Provides `Departure Time` — early-AM Corporate signal |
| Request return PNR pairing | Derives `Length of stay` — short stay = Corporate, long stay = Leisure |
| Request ancillary / SSR data | Cargo add-on = OFW/Balikbayan signal; seat selection = Corporate |

### Short-Term (Data Preparation)

1. **Filter COVID years.** Exclude or flag 2020–2021 records — anomalous travel patterns will distort cluster positions. Recommended: exclude from training, retain for validation.
2. **Engineer RFM features per passenger** — `flights_last_12m`, `avg_fare_12m`, `routes_flown`, `recency_days`. These serve as the strongest proxy for Mabuhay Loyalist before loyalty data arrives.
3. **Add temporal segment features** — `is_holy_week`, `is_hajj_season`, `is_balikbayan_season`, `is_ofw_deployment_peak`, `travel_quarter`.
4. **Stratified sample for development.** Use 500K records (stratified by year, route region, cabin) for model iteration. Train on sample, predict on full 6M.

### Medium-Term (Pipeline Scaling)

| Component | Current | Recommended at 6M rows |
|-----------|---------|------------------------|
| Data loading | `pandas` | `polars` or chunked `pandas` |
| HDBSCAN | `min_cluster_size=150` | `min_cluster_size=500–1000`, `algorithm='prims_kdtree'` |
| Nearest-neighbour search | `sklearn` brute | FAISS approximate nearest neighbours |

### Full Retrain Sequence

```
[1] Receive 5-year dataset + blocking features from PAL
[2] Clean, engineer RFM + temporal features, filter COVID years
[3] Refit penalty-weighted StandardScaler on full dataset
[4] Refit HDBSCAN (min_cluster_size=500–1000)
[5] Re-run cluster → segment mapping + noise auto-assignment (Stage 6)
[6] Validate with asymmetric cost matrix (Stage 7)
[7] Build Power BI dashboard on final labelled dataset
[8] Define monthly refresh pipeline for production scoring
```

---

## Future Enhancements (When Blocking Data Arrives)

Once `Loyalty status`, `Cargo/baggage add-on`, `Length of stay`, and `Departure Time` are available from PAL systems, the proxy waterfall can be extended with exclusion rules that narrow segment assignments further. For example:

- A record booked 60+ days out in Economy with no loyalty ID is unlikely to be Corporate.
- A record with a cargo add-on on a Manila–Riyadh route is unlikely to be Premium Bleisure.
- A Business-cabin same-day return with loyalty status narrows to Corporate or Premium Bleisure only.

These rules are not implemented in the current pipeline because the required fields are 100% null in the sample dataset and would have no effect. They are documented here as a planned extension, not a current dependency.

---

*Document prepared for Philippine Airlines internal use.*
*v0.7 — 23 July 2026 (added Tools & Libraries disclosure; real-data track: rule-based primary + LCA refinement; HDBSCAN superseded for real data)*
