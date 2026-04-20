# PAL Customer Segmentation — ML Pipeline Methodology

**Client:** Philippine Airlines (PAL)
**Version:** v0.3 — 19 April 2026

---

## Overview

This document describes the end-to-end machine learning pipeline for the PAL Customer Segmentation project. The objective is to produce a baseline segmentation model over PNR booking data, assigning each booking record to one of ten commercially meaningful customer segments. The pipeline combines rule-based proxy labelling, density-based clustering, penalty-weighted feature scaling, and a human-in-the-loop annotation queue, with semi-supervised label diffusion and asymmetric cost validation planned for the final phase.

---

## Target Segments

The model targets ten segments (expanded from an original scope of six):

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

Penalty weights reflect the business cost of misclassifying a record into the wrong segment. Higher-penalty segments (Corporate, Mabuhay Loyalist, OFW/Migrant) demand greater recall and drive several design decisions downstream, including penalty-weighted feature scaling (Stage 6) and the annotation queue priority order (Stage 8).

---

## Source Data

| Property | Value |
|----------|-------|
| File | `sample-features.csv` |
| Rows | 29,999 |
| Columns | 27 |
| Target column | `Market Segment` — 100% null (no ground-truth labels exist) |

### Known Data Gaps (Blocking)

The following fields are present in the schema but contain no data in the current extract. Each gap blocks one or more segmentation signals:

| Feature | Blocks |
|---------|--------|
| `Loyalty status` | Mabuhay Loyalist segment; 4 of 6 negative learning rules |
| `Length of stay` | Corporate vs. Leisure separation |
| `Departure Time` | Early-AM Corporate signal |
| `Cargo/baggage add-on` | OFW/Balikbayan negative rule |

Until these fields are populated from source systems, the affected rules remain inactive and the Mabuhay Loyalist segment cannot be assigned via proxy labelling.

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

---

### Stage 4 — Resampling Analysis (Rejected)

**Script:** `resample_compare.py`

Five resampling strategies were evaluated against a Random Forest classifier to test whether class imbalance could be addressed at this stage:

- Random Oversample
- Random Undersample
- SMOTE
- ADASYN
- Tomek Links

**Decision: all resampling strategies rejected.** Three reasons:

**(a) Circular validation artifact.** Proxy labels are derived from the same features used for classification. F1 scores of 0.99+ reflect the model re-learning the labelling rules, not a generalisation signal.

**(b) SMOTE/ADASYN produce semantically invalid synthetic points.** Proxy label boundaries are sharp rule-based thresholds. Interpolated synthetic records land in regions that violate the rules that defined their class, introducing noise rather than signal.

**(c) Class imbalance is handled downstream.** The asymmetric penalty matrix in Stage 10 is the correct mechanism for managing the cost consequences of imbalanced classes; resampling at this stage would double-count the adjustment.

---

### Stage 5 — Clustering Algorithm Evaluation

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
2. Naturally identifies noise (7.1% ≈ 2,100 records). These are genuine boundary cases better resolved by human annotation than by forced cluster assignment.
3. 78 micro-clusters can be merged to 10 named segments via nearest-centroid mapping (Stage 7).
4. KMeans forces every borderline record into its nearest centroid, silently polluting proxy seeds. HDBSCAN flags them as noise instead, surfacing the ambiguity explicitly.

DBSCAN produced stronger separation metrics but returned 221 clusters with higher noise — not directly mappable to 10 segments without a further reduction step.

---

### Stage 6 — Penalty-Weighted Feature Scaling

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

### Stage 7 — HDBSCAN Cluster to Segment Mapping

**Script:** `hdbscan_final.py`

HDBSCAN returns 78 micro-clusters plus a noise set (label = −1). This stage maps micro-clusters to the ten named segments and prioritises the noise queue for human review.

**Cluster assignment:**

1. Compute the centroid of each HDBSCAN cluster in penalty-weighted feature space.
2. Compute the centroid of each proxy-labelled segment (from Stage 3) in the same space.
3. Assign each cluster to its nearest segment centroid by Euclidean distance.

**Noise queue scoring:**

Records with label = −1 are ranked for annotation by a penalty risk score:

```
penalty_risk_score = penalty_weight[nearest_segment] / distance_to_nearest_centroid
```

Higher scores indicate records that are both high-stakes (high penalty) and geometrically ambiguous (close to a centroid boundary). These are annotated first.

---

### Stage 8 — Annotation Queue (Human-in-the-Loop)

**Script:** `hdbscan_final.py`

Noise records are presented to human annotators in descending order of penalty risk score:

1. **First annotated:** noise records near the Corporate and OFW/Migrant centroids — high penalty, high ambiguity.
2. **Last annotated:** noise records near the Budget/Adventure centroid — low penalty, low business risk if incorrectly classified.

Ground-truth labels produced by annotation are added as additional seeds and fed into Stage 9.

---

### Stage 9 — Label Diffusion (Planned)

A graph-based semi-supervised learning step will propagate confirmed labels from seeds (Stage 7 cluster assignments + annotated noise from Stage 8) to the remaining unlabelled records.

**Approach:**

1. Construct a k-nearest-neighbour graph over all 29,985 records in penalty-weighted feature space.
2. Use `sklearn.semi_supervised.LabelSpreading` or `LabelPropagation` to propagate labels from labelled seeds to unlabelled neighbours, weighted by feature similarity.

This stage is pending completion of the annotation queue.

---

### Stage 10 — Validate (Asymmetric Cost Matrix)

Final label quality is evaluated using the segment penalty matrix rather than standard accuracy or macro-F1.

**Metrics reported:**

| Metric | Definition |
|--------|------------|
| Total weighted cost | Sum of `penalty_weight[true_segment]` for all misclassified records |
| Cost per record | Total weighted cost / total records |
| Per-segment recall | Recall computed separately for each of the ten segments |

**Optimisation target:** maximise recall for Corporate (×10) and OFW/Migrant (×5), the two segments where misclassification carries the highest business cost.

---

### Stage 11 — Dashboard (Power BI)

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
| `hdbscan_final.py` | HDBSCAN with penalty-weighted features, segment mapping, noise queue | Final cluster assignments, annotation queue |
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
[Stage 4] Resampling (Rejected)
        |
        v
[Stage 5] Algorithm Comparison    HDBSCAN selected
        |
        v
[Stage 6] Penalty-Weighted Scaling
        |
        v
[Stage 7] Cluster → Segment Map   78 micro-clusters → 10 segments
        |                         ~2,100 noise records → annotation queue
        v
[Stage 8] Annotation Queue        Human review, priority by penalty risk score
        |
        v
[Stage 9] Label Diffusion         (Planned) k-NN graph, LabelSpreading
        |
        v
[Stage 10] Validate               Asymmetric cost matrix, per-segment recall
        |
        v
[Stage 11] Power BI Dashboard     O&D × segment × travel month
```

---

## Current Limitations (Sample Data)

The current pipeline runs on a **29,999-row January 2025 snapshot**. Key constraints:

| Limitation | Impact |
|-----------|--------|
| All flight dates are January 2025 only | Seasonality signals (Pilgrimage, Balikbayan, OFW deployment) cannot be validated on flight date |
| `Loyalty status`, `Departure Time`, `Length of stay` are 100% null | Mabuhay Loyalist has zero proxy-labelled records; 4/6 negative learning rules inactive |
| No RFM history | Booking frequency and recency cannot be computed per passenger |
| No cargo/ancillary flags | OFW/Balikbayan negative learning rule is inactive |

---

## Next Steps — Scaling to Full Historical Data

PAL holds **~6 million PNR records spanning 5 years**. The following actions are recommended in priority order.

### Immediate (Blocking)

| Action | Reason |
|--------|--------|
| Request `Loyalty status` (Mabuhay Miles tier) from PAL | Unlocks Mabuhay Loyalist segment and 4/6 negative learning rules |
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
| Annotation queue | CSV export | Dedicated annotation interface (Label Studio or similar) |

### Full Retrain Sequence

```
[1] Receive 5-year dataset + blocking features from PAL
[2] Clean, engineer RFM + temporal features, filter COVID years
[3] Refit penalty-weighted StandardScaler on full dataset
[4] Refit HDBSCAN (min_cluster_size=500–1000)
[5] Re-run cluster → segment mapping (Stage 7)
[6] Annotate noise queue — ~528K records expected at 8.8%
[7] Run label diffusion (Stage 9) on full 6M k-NN graph
[8] Validate with asymmetric cost matrix (Stage 10)
[9] Build Power BI dashboard on final labelled dataset
[10] Define monthly refresh pipeline for production scoring
```

---

*Document prepared for Philippine Airlines internal use.*
*v0.3 — 19 April 2026*
