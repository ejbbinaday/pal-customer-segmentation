# Chapter 4 — Results, Analysis, and Discussion (FIRST DRAFT)

> **Draft status:** v0.1, 8 August 2026. All figures below are traceable to pipeline outputs:
> `outputs/model_stress_test/`, `outputs/cluster_diagnostic/`, `outputs/detection_power/`,
> `outputs/validate_construct/`, `outputs/validate_criterion/`, `outputs/validate_temporal/`,
> `outputs/features_real/`, `outputs/sub_segments/`. Numbers derive from the real 38M-coupon
> extract only; no prototype-track result is quoted. Monetary values are in the extract's
> reporting currency (single-currency consistency verified across issue countries, §3 of the
> methodology). `[Figure n]` marks are placeholders for co-authors.

---

## 4.1 Presentation of Empirical Clustering Results

### 4.1.1 The central empirical finding: a behavioural continuum, not discrete clusters

The study's most consequential empirical result is a negative one, established affirmatively:
**the PAL booking base does not contain natural, well-separated clusters at the top level.**
Rather than treating this as a failure of method, the analysis converged on it from six
independent algorithmic families and then bounded it with a planted-segment power analysis,
so that the null is falsifiable rather than merely asserted.

The evidence proceeds in four steps.

**(a) Model selection never settles.** Latent Class Analysis on a stratified sample of 60,000
bookings (four numeric, six binary, one nominal feature) shows the Bayesian Information
Criterion falling monotonically from k = 3 through k = 9 with no elbow (1,016,290 → 932,164);
BIC "selects" k = 9 only because the sweep ends there. Centroid-cost criteria behave
identically. A monotone criterion is what a continuum produces: each added component claims
another slice of a smooth density rather than isolating a real group.

**(b) A ceiling on separation, replicated across ten methods.** The ten-method stress test
(LCA, Gaussian mixtures with full and diagonal covariance, k-prototypes, k-modes, k-means,
SVD+k-means, spectral clustering on Gower distance, Support Vector Clustering, and
TDA-Mapper; 20,000 fitted bookings, 4,000 held out, k swept 3–12) found a maximum Gower
silhouette of **0.381** (Spectral(Gower) at k = 3). Against conventional bands — above 0.5
strong, 0.25–0.5 weak-but-real, below 0.25 no structure — the strongest claim any of the ten
methods can support on this data is *weak-but-real* structure. `[Figure 1: silhouette by
method and k]`

**(c) Independent families disagree about where the boundaries are.** If ten methods were
recovering the same latent partition, their labelings would agree. At k = 10 the median
pairwise Adjusted Rand Index across methods is **0.41**; agreement is high only within
algorithmic families (the two Gaussian mixtures at 0.846; the Euclidean-centroid trio at
0.68–0.79). Six families cutting the same data six different ways is the signature of
partitions imposed on a continuum, not of segments awaiting discovery. `[Figure 2:
cross-method ARI heatmap]`

**(d) A label-free, algorithm-free check agrees.** Persistent homology computed on the Gower
distance matrix — which involves no k, no centroid, and no distributional assumption —
returned one dominant H0 component (gap ratio 1.195): a single connected mass. H1 loop
persistence was indistinguishable from the noise floor of a high-dimensional cloud (longest
bar 1.158× the 95th percentile of all bars), ruling out cyclic structure that partitional
methods would be structurally unable to represent. A subsequent instrument audit (§4.1.3)
showed the *integer count* of significant H0 components is noisy across resamples at this
sample size; we therefore quote it as the modal outcome of a distribution — the mode and
median are 1 — rather than as a point measurement.

Among the ten methods, the full-covariance Gaussian mixture ranked first on the weighted
composite of agreement, separation, stability, robustness, learnability, and cost
(score 0.849), and — critically — **remained first when the taxonomy-agreement axis, the one
circular axis, was weighted to zero** (0.798 vs. 0.785 for GMM-diag and 0.762 for LCA). Its
ranking is therefore not borrowed from the rule taxonomy it was benchmarked against.

Two methodological traps documented during the benchmark are worth reporting because they
generalise. First, high held-out learnability does not imply real structure: SVD+k-means at
k = 3 achieved 0.981 balanced accuracy from an SVM probe trained on its own labels while
scoring only 0.117 on separation — a perfectly *learnable* partition that is nonetheless an
arbitrary geometric slice through a smooth density. Separability figures should never be
quoted without a separation figure beside them. Second, every method proved fragile to
leave-one-feature-out deletion (minimum dropout ARI 0.15–0.49), indicating that no candidate
partition rests on redundant, mutually confirming evidence.

### 4.1.2 Bounding the null: detection power

A null result is only as strong as the instrument's sensitivity, so synthetic segments of
known prevalence (0.5–10% of bookings) and known distinctness (a mixing weight *w* from 0.1
to 1.0) were appended to the real population and the deployable four-method panel was refit
at k = 10, with detection thresholds pre-registered from *w* = 0 negative controls. Reading
the majority verdict of the 12 method × archetype combinations (the single most sensitive
cell is a cherry-pick and is not quoted):

| Planted prevalence | Majority-detection floor (distinctness) |
|---|---|
| ~2% of bookings | detected from *w* ≥ 0.75 (planted silhouette ≈ 0.34) |
| ~5% | detected from *w* ≥ 0.50 (≈ 0.23) |
| ~10% | detected from *w* ≥ 0.35 (≈ 0.13) |
| ≤1% | **never detected at any distinctness tested** |

The null can therefore be stated in bounded, falsifiable form: **no segment exists in these
features at or above ~2% of bookings with distinctness at or above ≈0.34** — because a
planted segment of that size and faintness is reliably recovered — while a segment smaller
than ~1% of bookings (~229,000 bookings at population scale) could exist undetected. The
recovery rate was statistically indistinguishable across the two business-motivated
archetypes and a random-direction control (22%, 28%, 29% of cells), so the floors are a
property of the method panel, not of the archetype directions chosen. Because a planted
group is internally coherent in a way a real segment need not be, these floors are
optimistic bounds rather than guarantees.

### 4.1.3 The resulting architecture: rules as taxonomy, clustering as refinement

Given (i) a continuum at the top level and (ii) a business requirement for ten named,
actionable segments, the final architecture is hybrid. A deterministic **rule waterfall**
assigns each of 22.9M bookings (13.4M customers, after excluding 12,306 all-non-revenue
customers) to one of ten segments defined *a priori* with the airline's domain framing;
clustering is retained in two subordinate roles: as the diagnostic battery reported above,
and as a **sub-segmentation layer** — Latent Class Analysis run *within* each of the four
largest segments, where BIC (capped at a business-actionable maximum of four classes, an
explicitly pragmatic cut given the continuum) yields 3–4 behavioural sub-types per parent
(§4.2.4). The clustering benchmark's leader, GMM(full), is under evaluation as a replacement
for LCA in that layer; the comparison is stage-matched and ongoing, and no result in this
chapter depends on its outcome.

The Adjusted Rand Index between the best unsupervised partitions and the rule taxonomy is
modest (0.2–0.41 depending on method and k), which is the expected reading given the
continuum: data-driven partitions neither reproduce nor contradict the business taxonomy;
they cut the same smooth mass along different, roughly equally arbitrary planes. The
justification for the rule taxonomy is therefore not that the data demands it, but that it is
*consistent with* the data (no natural partition is being overridden) and independently
validated on evidence the rules never saw — the subject of §4.2.

## 4.2 Analytical Interpretation of Passenger Segments

### 4.2.1 The ten-segment taxonomy

Applied to the full booking base (22,911,450 bookings; 13,435,365 customers), the taxonomy
resolves as follows. Booking share and mean revenue are computed at booking grain; the
customer column assigns each customer their modal (most frequent, revenue-tiebroken) segment.

| Segment | Bookings % | Mean revenue / booking | Customers % |
|---|---:|---:|---:|
| Budget/Adventure | 39.4 | 74 | 38.4 |
| OFW/Migrant | 17.1 | 312 | 19.0 |
| Last-Minute | 12.9 | 137 | 9.9 |
| Balikbayan/VFR | 12.7 | 618 | 16.4 |
| Unassigned | 9.6 | 360 | 8.8 |
| Corporate | 4.4 | 493 | 3.2 |
| Premium Bleisure | 2.1 | 1,504 | 2.0 |
| Family | 1.6 | 235 | 2.0 |
| Pilgrimage | 0.2 | 404 | 0.3 |
| Mabuhay Loyalist | 0.03 | 113 | 0.03 |

`[Figure 3: booking share vs revenue share by segment]`

Three segments warrant immediate qualification. **Unassigned** (9.6%) was tested directly for
coherence: if it were a genuine population the rules fail to name, it should be separable
from every named segment. It is clearly distinct from eight of nine (AUC 0.82–0.99) but only
weakly from Corporate (0.68) — the profile of a *residue*, not a missing segment, with its
Corporate-adjacent fringe marking where the Corporate rule's boundary is most improvable.
**Mabuhay Loyalist** (0.03%) is not a measurement of the loyalty base but of our visibility
into it: with no loyalty-tier field in the extract, the only observable signal is award
redemption, and 0.03% of bookings cannot be the true footprint of a national flag carrier's
frequent-flyer programme. **Corporate** is identified without any company or loyalty
identifier, so "business cabin at short notice" necessarily also captures affluent
last-minute leisure; we grade its label confidence as diluted.

### 4.2.2 Construct validity: the segments are distinguishable on evidence the rules never saw

Because every clustering-vs-rules comparison is circular (the proxy labels are the rules' own
output), validation was rebuilt on *anchors* — fields no rule consumes: passenger age (and
whether age was captured), departure month, and customer lifetime booking count, with country,
channel, and destination-region identity admitted only for pairs where the rule bit they
encode is not the boundary under test. The harness includes a negative control (each segment
split randomly in half must yield AUC ≈ 0.50; observed 0.494–0.506, passed) and positive
controls (0.770–0.945) that calibrate the scale.

On strict anchors, **32 of 36 segment pairs are weakly or clearly distinguishable
(AUC ≥ 0.60), and 25 of 36 clearly so (AUC > 0.75)**; passenger age is the dominant
discriminator in most pairs. The two weakest boundaries are instructive:

- **OFW/Migrant vs. Balikbayan/VFR (AUC 0.608 strict; 0.722 on the isolated boundary
  population)** — 6.8M bookings, 30% of the base, separated in the waterfall by a single bit
  (one-way vs. round-trip). The boundary survives two adversarial designs: within single
  issue-countries (so geography cannot carry the result) it remains weakly distinguishable in
  13 of 17 markets (AUC 0.605–0.721), and base-rate-normalised seasonality shows the
  theoretically predicted signature — a December Balikbayan peak (index 1.174 vs. 0.826 for
  OFW) against an OFW peak in August. The split is real but weak; we retain it because the
  two populations demand opposite commercial treatment (§4.3), and we flag it as the
  taxonomy's most improvable boundary rather than as settled.
- **Last-Minute vs. Budget/Adventure (0.645)** — consistent with Last-Minute being defined
  behaviourally (booking lead) rather than demographically, so it cuts across other segments
  by design.

Two limits on interpretation are maintained throughout: distinguishability shows the groups
*differ*; it cannot show that the group labelled Corporate is what the airline's commercial
team means by Corporate (the labels are *behaviourally validated, not externally confirmed*);
and a weak boundary is evidence about that boundary, not authority to merge segments — an
unsupported split is reported to the airline as a proposal with evidence attached.

### 4.2.3 Criterion validity: the labels predict outcomes they were not built from

The segment label alone predicts operational outcomes that no rule consumes: completion of
travel (AUC 0.632), rebooking within 180 days (0.607, right-censoring excluded), and refund
incidence (0.822, though on 347 events this is indicative only). Relative to the full
11-feature model, the single label retains 32% and 56% of achievable discrimination on the
two stable outcomes, while adding essentially nothing *on top of* the features
(incremental AUC ≤ 0.002). The correct reading, which we adopt explicitly, is that the
segmentation is a **lossy but faithful compression** of behavioural signal into ten
communicable labels: valuable for targeting and reporting, not a source of signal beyond its
inputs, and not sold as one. Outcome differences across segments are large and coherent —
rebooking within 180 days ranges from 8.3% (Pilgrimage) and 18.8% (Balikbayan/VFR) to 46.7%
(Last-Minute) and 53.1% (Corporate) — and these gradients, being built from no rule input,
are independent corroboration that the taxonomy tracks real behavioural difference.

### 4.2.4 Temporal stability: the segmentation is not a one-period artefact

Splitting the extract into two adjacent twelve-month issuance windows (9.77M vs. 10.08M
bookings, both chosen to sit strictly inside the region where no lead time up to the 365-day
clip is censored):

- **Sizes hold.** Total-variation distance between the two years' segment mixes is
  **1.93 percentage points** on bookings — on full-population counts, not samples. The
  largest single move is Budget/Adventure at −1.49 pp.
- **Revenue mix moves more than headcount** (TVD 3.21 pp), the operative example being
  Balikbayan/VFR: flat booking share (12.3% → 12.1%) against a revenue-share decline of
  29.35% → 26.64%. We report both figures together as a matter of policy, because revenue
  share is the quantity the commercial organisation acts on and it is the less stable leg.
- **Composition holds where the volume is.** Seven of ten segments show negligible-to-small
  profile drift, jointly carrying 98.2% of bookings. The three drifting segments (Family,
  Pilgrimage, Mabuhay Loyalist) are the taxonomy's smallest, where a few hundred bookings
  move a mean; their drift is classified as unresolved rather than as behavioural change.
- **A year-old model transfers at its own ceiling.** A GMM fitted on the earlier window
  labels the later window at ARI 0.763 against a within-window self-agreement ceiling of
  0.746 (ratio 1.02): on this evidence an annual refit buys nothing, and drift monitoring
  (adversarial window-classification AUC 0.61, against controls at 0.497 and 0.994 — mild
  but real population shift) is the appropriate cadence instead.

### 4.2.5 Sub-types within the large segments

Within each of the four largest segments, LCA on 40,000-booking samples resolves 3–4
sub-types along lead time, trip topology (one-way/round-trip, nonstop/connecting), and fare
tier. Illustratively: Budget/Adventure divides into advance-purchase supersaver one-ways
(27%, median revenue 23), short-lead saver one-ways (28%), advance round-trips (38%), and a
small connecting cohort; OFW/Migrant's largest sub-type is short-lead saver one-ways (47%)
with an advance-purchase *connecting* one-way cohort (37%) at markedly higher revenue (297
vs. 210 median); Balikbayan/VFR is uniformly round-trip but splits sharply on planning
horizon, including a far-advance connecting sub-type with median revenue 987. These
sub-types are profile characterisations fitted on samples; row-level sub-segment assignment
is future work (a scoring pass or rule re-expression), and the sub-types inherit the
continuum caveat — they are actionable partitions of a smooth space, not natural kinds.

## 4.3 Strategic Marketing and Revenue Implications for Philippine Airlines

### 4.3.1 The volume–value inversion

The taxonomy's first strategic lesson is that PAL's volume story and value story are close to
inverses. Budget/Adventure supplies 39.4% of bookings at 74 per booking and roughly 11% of
revenue; Balikbayan/VFR supplies 12.7% of bookings but ~27–29% of revenue; Premium Bleisure
supplies 2.1% of bookings at 1,504 per booking — approximately 11% of revenue from a
fiftieth of the volume. Any strategy metric denominated in passengers will therefore
systematically overweight the low-yield base, and any uniform marketing treatment (a
network-wide promo fare, for instance) transfers margin to segments that would have flown
anyway while failing the segments that carry the revenue. Segment-denominated reporting is
not a refinement here; it is a correction.

### 4.3.2 Segment-level implications

**Balikbayan/VFR — the revenue engine, and the active risk.** Highest total revenue
contribution, longest planning horizons, a verified December peak, and the one materially
adverse trend in the data: a 2.7-pp revenue-share decline year-on-year on flat volume —
yield erosion, not attrition. Implications: protect yield on diaspora corridors (North
America, where the US is the second issue country at 3.6M coupons) rather than stimulate
volume; time campaigns to the far-advance booking window the sub-types reveal (median leads
of 62–105 days, with a connecting far-advance sub-type at nearly 1,000 median revenue that
justifies premium-economy upsell); and diagnose the yield decline before discounting into it.

**OFW/Migrant — high-value, structurally distinct, operationally underserved.** One-way,
short-to-medium lead, foreign-issued, with a distinct high-revenue connecting sub-type
(Middle East and long-haul corridors). Because the Balikbayan boundary is the taxonomy's
weakest (§4.2.2), campaign logic should not lean hard on that single bit: where treatment
differs sharply between the two (e.g., one-way flexible products vs. round-trip seasonal
bundles), eligibility should be checked against the sub-type profile, not the label alone.
The seasonal complementarity (OFW August peak vs. Balikbayan December) allows the same
corridors to be revenue-managed to two calendars.

**Corporate and Premium Bleisure — the yield frontier, under a labelled caveat.** Together
6.5% of bookings and ~19% of revenue, with the highest rebooking rates in the base (53.1%
and 39.7%): these are the retention segments, where a single defection costs the most future
revenue — the rationale for the asymmetric misclassification-cost weighting in the
methodology. The dominant marketing error to avoid is documented in the deliverable itself:
do not send promotional fares to Corporate-labelled customers (it dilutes yield in the one
segment defined by schedule-over-price), and do not read a cancelled meeting as churn. Both
recommendations are conditioned on the diluted-trust caveat: without a company or loyalty
identifier, Corporate targeting should be treated as propensity, not identity.

**Budget/Adventure — defend with cost discipline, refine with sub-types.** The LCC
battleground. Its four sub-types differ enough to matter operationally: the advance-purchase
supersaver cohort (median revenue 23) is price-elastic filler that should never receive
acquisition spend, while the round-trip advance cohort (median 87) is the natural target for
ancillary attach. Treating the segment as one 39%-of-bookings block would be the single
largest source of wasted marketing spend available in this taxonomy.

**Last-Minute — a behavioural overlay to price, not to court.** Defined by lead time, cutting
across demographics, with the second-highest rebooking rate (46.7%) and 99.8% completion:
this is dependable, urgency-driven demand suited to inventory-management levers (protecting
late inventory, dynamic pricing) rather than persuasion marketing.

**Family and Pilgrimage — niche, seasonal, and small enough to drift.** Pilgrimage is the
cleanest-defined segment (destination settles it) and cheap to activate around known event
calendars; both segments' year-on-year profile drift is noise-dominated (§4.2.4) and last
year's description of them should be re-profiled before campaign use.

### 4.3.3 What the continuum finding implies for strategy

The absence of natural clusters is itself a strategic result, in three ways. First, it means
**the taxonomy is a management instrument, not a discovery**: its boundaries are choices, so
they can and should be moved when commercial policy changes — nothing in the data will
resist, and governance (documented rules, versioned changes) matters more than it would for
"found" segments. Second, it cautions against **personalisation theatre**: since customers
occupy a smooth behavioural space, adjacent-segment misassignment is common and expected
(16.4% of coupons belong to customers whose trip-level and dominant labels disagree), so
treatments should degrade gracefully across boundaries rather than switch discretely. Third,
the detection-power bound marks a **known blind spot with commercial meaning**: a coherent
group smaller than ~1% of bookings (~229,000 bookings) — a single corporate account
programme, a nascent route community — would be invisible to this pipeline, so bottom-up
segment discovery below that scale must come from business knowledge or external data, not
from this model.

### 4.3.4 The data investment case

The analysis makes specific, evidence-backed cases for three data acquisitions. **Loyalty
tier** is the largest: the Mabuhay segment's observed 0.03% is a visibility artefact, and
with tier data both the loyalty segment and the Corporate dilution problem (§4.2.1) become
resolvable. **Demographics coverage**: age is the single strongest non-circular
discriminator between segments (§4.2.2) yet is missing on 57% of coupons; raising capture at
booking would improve both validation power and targeting precision. **Trip context**
(length of stay, ancillary spend): the known gaps that would let indistinguishable-on-anchors
boundaries (OFW vs. Balikbayan foremost) be tested on the evidence most likely to separate
them. Each recommendation follows from a measured limitation rather than a general appetite
for data.

### 4.3.5 Boundary conditions on the strategic claims

Four limits circumscribe everything above. The segment *names* are behaviourally validated
but not externally confirmed; SME adjudication remains the outstanding strongest test.
Prediction is not causation: a segment that predicts rebooking is not a licence to treat its
members differently without a policy decision. Temporal stability is demonstrated across one
twelve-month step inside one extract, not through a demand shock, network change, or fare
restructure. And revenue implications inherit the revenue-mix instability (§4.2.4): the
commercial numbers move faster than the behavioural ones, so segment revenue shares should be
re-measured, not carried forward, at each planning cycle.

---

*Draft ends. Figure files (all in `outputs/report_real/figs/`; 1–2 and 4–6 generated by
`src/manuscript_figures.py`, the rest by `src/report_figures.py`):*

| Placeholder | File | Content |
|---|---|---|
| Figure 1 | `ms_fig1_separation_ceiling.png` | Gower silhouette by method × k — the 0.381 ceiling |
| Figure 2 | `ms_fig2_cross_method_ari.png` | cross-method ARI heatmap at k = 10 |
| Figure 3 | `eda_01_segments.png` | segment volume vs value (verify it carries revenue *share*; regenerate if needed) |
| Figure 4 | `ms_fig4_construct_auc.png` | construct-validity AUC matrix, weakest boundary outlined |
| Figure 5 | `ms_fig5_detection_floor.png` | detection-power consensus grid, majority floor outlined |
| Figure 6 | `ms_fig6_temporal_stability.png` | booking vs revenue share across the two windows |
| Figure 7 | `sub_01_subtypes.png` | LCA sub-type profiles within the four large segments |
