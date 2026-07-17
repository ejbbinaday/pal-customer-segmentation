# Model Monitoring & Metrics Specification

PAL Customer Segmentation — metrics we track, thresholds, cadence, and retrain triggers.

Status: **specification** (production monitoring layer not yet built into the sample pipeline).
Companion script: `monitor_metrics.py` computes the *quality* and *drift* metrics below.

---

## 1. Why three metric regimes

The project uses different metrics for different jobs. Silhouette alone is **not** sufficient — and for a
density-based model (HDBSCAN) it is actively misleading, because Silhouette/Davies-Bouldin/Calinski-Harabasz all
assume convex, roughly spherical clusters and systematically *understate* density-based clusterings.

| Regime | Question it answers | When it runs | Metrics |
|--------|--------------------|--------------|---------|
| **A. Algorithm selection** | Which algorithm produces the best clusters? | Once, at model design | Silhouette, Davies-Bouldin, Calinski-Harabasz, **DBCV**, noise % |
| **B. Label validation** | Are the final business labels good enough? | Every (re)train | Per-segment recall, weighted cost/record (asymmetric penalty matrix) |
| **C. Production monitoring** | Has the world drifted since we trained? | Every monthly refresh | **PSI**, **ARI**, segment-mix / centroid drift, noise % trend |

Regimes A and B already exist in the pipeline (`cluster_compare.py`, `hdbscan_final.py`, Stage 7).
Regime C is the gap this spec closes.

---

## 2. Regime A — Algorithm-selection quality metrics

Computed in `cluster_compare.py` across 7 algorithms; recorded in `methodology.md` and `knowledge-base.md`.

| Metric | Direction | HDBSCAN (current) | Notes |
|--------|:---------:|:-----------------:|-------|
| Silhouette | ↑ | 0.435 | Convex-cluster bias; penalizes density-based models |
| Davies-Bouldin | ↓ | 0.961 | Compactness vs separation; similar convex bias |
| Calinski-Harabasz | ↑ | 1,554 | Between/within dispersion ratio |
| **DBCV** (to add) | ↑ (−1..1) | *compute* | **Density-Based Clustering Validation** — the correct primary metric for HDBSCAN |
| Noise % | ↓ | 7.1% | HDBSCAN/DBSCAN only |
| Cluster-size std | ↓ | — | Balance of cluster sizes |

**Action:** add DBCV to the leaderboard. Expect it to rank HDBSCAN above KMeans/GMM, reversing the misleading
Silhouette ordering (where DBSCAN's 221 fragmented clusters scored highest at 0.554).

---

## 3. Regime B — Label-validation metrics (business cost)

Computed at Stage 7 (`methodology.md:199`). These are the **optimization target**, not the internal metrics above.

| Metric | Definition | Target |
|--------|------------|--------|
| Per-segment recall | Recall per segment vs proxy labels | NFR-01: **≥ 91%** |
| Total weighted cost | Σ `penalty_weight[true_segment]` over misclassified records | minimize |
| Cost per record | Total weighted cost / N | minimize (peso impact) |

Penalty weights (from `hdbscan_final.py`): Corporate ×10, Mabuhay Loyalist ×8, OFW/Migrant ×5,
Premium Bleisure ×4, Pilgrimage ×3, Balikbayan/VFR ×2, Family ×2, Digital Nomad ×2, Last-Minute ×1, Budget/Adventure ×1.

**Priority:** maximize recall for Corporate (×10) and OFW/Migrant (×5).

---

## 4. Regime C — Production monitoring metrics (the new layer)

These run on each **monthly refresh** and drive the retrain decision.

### 4.1 Population Stability Index (PSI) — *drift*

Detects when the incoming population no longer matches the training population. Track PSI on:

- **Segment mix** — share of bookings per segment (the headline drift signal).
- **Key input features** — `lead_time`, `fare_per_pax`, `cabin_ord`, `Region`, `Ticketing Channel`.

PSI per variable = Σ over bins `(cur% − ref%) · ln(cur% / ref%)`.

| PSI value | Interpretation | Action |
|-----------|----------------|--------|
| < 0.10 | Stable | None |
| 0.10 – 0.25 | Moderate shift | **Investigate** (tracking change, mix change, or real market move) |
| > 0.25 | Significant shift | **Retrain trigger** |

### 4.2 Adjusted Rand Index (ARI) — *stability*

Chance-corrected agreement between two labelings. Two uses:

- **Cross-refresh stability** — ARI between this month's labels and last month's, on records present in both.
- **Bootstrap stability** — re-fit on a 90% resample, compare labels on shared records. Low ARI = unstable model.

| ARI value | Interpretation | Action |
|-----------|----------------|--------|
| ≥ 0.90 | Very stable | None |
| 0.75 – 0.90 | Acceptable | Monitor |
| < 0.75 | Unstable | **Investigate config / retrain** |

(Adjusted Mutual Information, AMI, is an acceptable substitute where cluster sizes are very uneven.)

### 4.3 Segment volume & centroid drift

- **Volume drift** — per-segment count as % of total vs baseline; flag any segment moving > ±30% relative.
- **Centroid drift** — Euclidean shift of each segment centroid in scaled feature space vs baseline; flag > 1.0σ.
- Watch high-penalty segments (Corporate, OFW/Migrant, Mabuhay Loyalist) most closely.

### 4.4 Noise-rate trend

HDBSCAN noise % per refresh. Baseline 7.1%. A rising trend (e.g. > 12%) means the density structure is
changing and the fitted `min_cluster_size` no longer matches the data.

---

## 5. Cadence & retrain triggers

| Cadence | What runs | Owner |
|---------|-----------|-------|
| **Monthly** (refresh) | Regime C: PSI, ARI, volume/centroid drift, noise trend → monitoring report | Pipeline |
| **On trigger** | Full retrain (Regimes A+B re-validated) | Pipeline |
| **Quarterly** | Manual review of segment definitions & penalty matrix | Analyst |

**Retrain is triggered when ANY of:**

1. Segment-mix **PSI > 0.25**, or PSI > 0.10 on ≥ 2 key features.
2. Cross-refresh **ARI < 0.75**.
3. High-penalty segment (Corporate / OFW / Mabuhay) **recall drops below its Stage-7 baseline** (once ground-truth or fresh proxy labels are available).
4. **Noise % > 12%**.
5. Calendar: **6 months** since last retrain regardless of the above.

---

## 6. Data dependencies

Monitoring quality improves sharply once PAL supplies the blocking fields (`knowledge-base.md:225`):

- `Loyalty status` (Mabuhay tier) → unlocks Mabuhay recall in Regime B, sharpens Corporate/OFW separation.
- `Length of stay`, `Departure Time`, `Cargo/baggage add-on` → strengthen proxy labels feeding ARI stability.

Until then, Regime C (PSI/ARI/drift) is fully computable on existing features; Regime B recall for
Mabuhay/OFW/Budget stays capped by the missing loyalty field.

---

## 7. Summary — what we monitor

| # | Metric | Regime | Primary use | Threshold |
|---|--------|:------:|-------------|-----------|
| 1 | Silhouette | A | Algo selection (secondary) | — |
| 2 | Davies-Bouldin | A | Algo selection (secondary) | — |
| 3 | Calinski-Harabasz | A | Algo selection (secondary) | — |
| 4 | **DBCV** | A | **Algo selection (primary for HDBSCAN)** | higher better |
| 5 | Per-segment recall | B | Label quality | ≥ 91% (Corp/OFW priority) |
| 6 | Weighted cost/record | B | Business impact | minimize |
| 7 | **PSI** (segment mix + features) | C | **Drift / retrain trigger** | > 0.25 retrain |
| 8 | **ARI** (cross-refresh) | C | **Stability** | < 0.75 investigate |
| 9 | Volume / centroid drift | C | Segment shift | ±30% / 1.0σ |
| 10 | Noise % trend | C | Density change | > 12% |

Bottom line: **not just Silhouette.** DBCV for quality, PSI + ARI for monitoring are the key additions.
