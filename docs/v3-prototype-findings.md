# v3 Prototype — Honest Findings & Recommendations

**Date:** 17 July 2026 · **Scope:** clustering prototype on `PAL_PNR_Synthetic_Data_1000-v3.csv` (1,000 PNRs)
**Verdict:** the pipeline works; **the data has no latent cluster structure to find.** Treat this as
validation of the *approach and plumbing*, not of a *result*. Do not present the recall numbers as model accuracy.

---

## 1. What we built and ran

End-to-end PNR-level pipeline (`src/features_v3.py` → `src/prototype_v3.py`): clean → 58 engineered
features → v3 proxy waterfall → StandardScaler → penalty-weighted HDBSCAN → nearest-centroid mapping +
noise auto-assignment → validation. A separate diagnostic (`src/diagnose_v3.py`) stress-tests whether
real structure exists, using **non-circular** metrics only.

## 2. The metrics, read honestly

### Shipped prototype (penalty-weighted, 58 features)
| Metric | Value | Read |
|---|---|---|
| DBCV (primary for HDBSCAN) | **0.023** | ≈ 0 → no density structure |
| Silhouette | 0.235 | weak |
| Noise | 42.1% | very high (baseline on real 30k data: 7.1%) |
| Per-segment recall vs proxy | 53–100% | **circular — not accuracy** (see §3) |

### Diagnostic (cleaned 24-feature space, **unweighted**, defensible metrics)
| Config | Clusters | Noise | **DBCV** | Bootstrap ARI |
|---|---|---|---|---|
| HDBSCAN mcs=15 | 4 | 1.9% | **−0.171** | 0.994 |
| HDBSCAN mcs=30 | 4 | 37.9% | **−0.103** | 0.860 |
| HDBSCAN mcs=50 | 2 | 75.5% | **−0.043** | 0.834 |
| HDBSCAN on PCA-90 (17 comps) | 2 | 29.7% | **−0.192** | — |

KMeans silhouette sweep: k4=0.103, k5=0.101, k6=0.097, k8=0.096, k10=0.117, k12=0.121
→ **flat ~0.10, no peak, drifts up with k** = there is no natural number of clusters.

## 3. Why the recall numbers are misleading (circularity)

The proxy labels are produced by deterministic rules on the **same features** the model then clusters.
"Recall vs proxy" therefore measures how well nearest-centroid **re-discovers our own if/else rules**,
not how well the model captures reality. `methodology.md` already flags this (resampling section:
F1 ≈ 0.99 "reflects the model re-learning the labelling rules"). Balikbayan/VFR and Digital Nomad hit
100% precisely because their rules carve out trivially separable regions.

## 4. Root cause

1. **The synthetic data has no embedded structure.** Negative DBCV across *every* configuration, a flat
   KMeans silhouette with no peak, and PC1 explaining only ~11% of variance all point to a single diffuse
   cloud, not clusters. Clustering cannot recover structure that was never generated.
2. **High ARI is a false comfort.** Bootstrap ARI is 0.83–0.99, but that only says HDBSCAN is *consistent*
   across resamples — a stable partition of a structureless cloud is still meaningless. Stability ≠ validity.
3. **Feature redundancy.** 19 feature pairs had |corr| > 0.9 (e.g. `net_fare ≡ net_revenue`,
   `is_nonstop ≡ 1−is_connecting`, `is_domestic ≡ is_regional_carrier`), inflating a 58-dim space over
   only 1,000 points and further degrading density estimation.
4. **Penalty-weighting bends space toward the rules.** It *lowered* DBCV (0.030 → 0.023 at mcs=30),
   i.e. it manufactures rule-shaped separation rather than revealing data-driven structure.

## 5. What this means (the useful reframing)

On this data, **segments are definitional (rule-driven), not emergent.** That is not a failure — it means
ML's role here is **label propagation, refinement, and drift monitoring on top of business rules**, which
is exactly what the proxy-label + cost-matrix design already supports. This is a legitimate, defensible
story for PAL — but the 53–100% recall must **not** be presented as "model accuracy."

## 6. Recommendations (priority order)

1. **Get real (or structure-embedding) data — the #1 blocker.** Real PAL PNRs, or a synthetic generator
   that plants segment archetypes with correlated features. Also fixes `pos_mismatch ≈ 0` (the OFW signal)
   and the 3 unseeded segments (OFW/Migrant, Pilgrimage, Mabuhay Loyalist).
2. **Retire circular validation.** Report DBCV + bootstrap-ARI + a small **hand-labelled** ground-truth
   sample. Drop recall-vs-proxy as a quality claim.
3. **Feature hygiene before re-clustering.** Remove complements/duplicates, collapse redundant one-hots,
   cluster a compact mostly-continuous behavioral subspace; consider Gower distance for mixed types.
4. **Separate discovery from priorities.** Cluster unweighted to see genuine structure; apply penalty
   weights only in the cost/mapping stage.
5. **Don't force-assign noise.** Keep an "Unassigned/low-confidence" bucket (distance threshold) rather
   than pushing 42% of points to a nearest centroid (which inflated Family from 75 → 325).

## 7. What is solid

Reproducible, tooled pipeline (ruff/bandit/pre-commit, pinned deps, Docker); sound, documented feature
engineering; cost-sensitive framing; and honest, non-circular diagnostics. The scaffold is ready — it is
waiting on data with real structure.

*See `knowledge-base.md` §15 (2026-07-17) and `methodology.md` §v3 Prototype Pipeline.*
