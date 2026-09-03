# Chapter 4 — Results, Analysis, and Discussion (FINAL DRAFT)

> **Draft status:** v1.5 (final draft; §4.1.1(b) now reports Davies–Bouldin and
> Calinski–Harabasz computed over the LCA sweep — all indices corroborate the continuum; v1.3
> added Table 4.2, the co-designed taxonomy; v1.2 renumbered figures into citation order),
> 23 August 2026. Supersedes v0.1 (8 Aug), which described
> the ten-segment v1 taxonomy; every figure below is measured on the **waterfall-v2 taxonomy PAL
> approved on 17–18 August 2026** (11 named segments + `Unassigned`) unless explicitly labelled
> as a v1-era measurement. All numbers are traceable to pipeline outputs:
> `outputs/model_stress_test/`, `outputs/detection_power/` (18 Aug re-run, k = 11),
> `outputs/validate_construct/`, `outputs/validate_criterion/`, `outputs/validate_temporal/`
> (18 Aug re-runs), `outputs/features_real/`, `outputs/sub_segments/` (incl. the population-level
> level-2 assignment of 21 Aug), `outputs/soft_priors/`, `outputs/monitor_real/`. Numbers derive
> from the real 38.1M-coupon extract only; no prototype-track result is quoted. Monetary values
> are **USD, confirmed by PAL on 18 August 2026**. `[Figure n]` marks are placeholders for
> co-authors; regeneration status of each figure file is tabled at the end.
>
> Two kinds of number appear below, and they carry different uncertainty. Quantities computed
> on the full 22.9M-booking population — segment sizes, revenue shares, the temporal TVDs and
> PSI — are census figures with no sampling error. Quantities from sampled analyses — the
> 60,000-booking LCA sweep, the 20,000/4,000 stress test, V1's 30,000-per-segment models, V2's
> 300,000-booking sample — are single-seed point estimates reported without intervals; §4.3.7
> owns that limit.

---

## 4.1 Presentation of Empirical Clustering Results

### 4.1.1 The central empirical finding: a behavioural continuum, not discrete clusters

The study's most consequential empirical result is a negative one, established affirmatively:
**the PAL booking base does not contain natural, well-separated clusters at the top level.**
Rather than treating this as a failure of method, the analysis converged on it from six
independent algorithmic families and then bounded it with a planted-segment power analysis,
so that the null is falsifiable rather than merely asserted. Latent-class studies of airline
passengers typically report the classes their model selects (e.g., Teichert, Shehu & von
Wartburg, 2008); the contribution here is testing whether any class structure exists to select.

The evidence proceeds in four steps.

**(a) Model selection never settles.** Latent Class Analysis on a uniform reservoir sample of
60,000 bookings shows the Bayesian Information Criterion (Schwarz, 1978; on BIC for class enumeration,
Nylund, Asparouhov & Muthén, 2007) falling monotonically from a single
component upward — 1,148,667 at k = 1, 1,057,599 at k = 2, 1,014,017 at k = 3, through 928,770
at k = 9 — with no elbow anywhere, each added class buying less than the one before (the
k = 1→2 step improves BIC by 91,068, 2→3 by 43,582, 3→4 by 25,269). The base is not even "two
masses": the criterion never identifies a number of groups at which to stop (probe of 23 Aug,
identical sample, seed, and coding as the 19 Aug sweep, which it reproduces exactly at k = 3).
BIC "selects" k = 9 only because the sweep ends there: the reported optimum is the top of the
search range, which is a boundary, not a fitted quantity. Centroid-cost criteria behave identically. A monotone criterion is what a
continuum produces: each added component claims another slice of a smooth density rather than
isolating a real group. `[Figure 1: BIC, taxonomy agreement, and internal validity indices by class count]`

**(b) A ceiling on separation, replicated across ten methods.** The ten-method stress test
(LCA, Gaussian mixtures with full and diagonal covariance, k-prototypes, k-modes, k-means,
SVD+k-means, spectral clustering on Gower distance, Support Vector Clustering, and TDA-Mapper;
20,000 fitted bookings, 4,000 held out, k swept 3–12) found a maximum silhouette (Rousseeuw,
1987) on Gower distance (Gower, 1971) of **0.381** (Spectral(Gower) at k = 3). Against
conventional bands (Kaufman & Rousseeuw, 1990) — above 0.5 strong, 0.25–0.5 weak-but-real,
below 0.25 no structure — the strongest claim any of the ten methods can support on this data
is *weak-but-real* structure. Silhouette is the common separation metric across the ten methods
because it is the one standard internal validity index defined on a precomputed, non-Euclidean
distance matrix; the centroid-based indices (Caliński & Harabasz, 1974; Davies & Bouldin, 1979)
presuppose Euclidean geometry with meaningful centroids, which Gower distance over mixed-type
features does not supply, so they cannot run on this benchmark. Computed instead on the
standardised one-hot (Euclidean) representation over the k = 1–9 LCA sweep, they corroborate
rather than complicate the picture: silhouette never exceeds 0.13 (its maximum is at k = 2 —
the geography cut of §4.1.3), Davies–Bouldin sits between 2.6 and 3.0 at every k, far from the
near-1 values of well-separated clusters, and Calinski–Harabasz declines monotonically from
k = 2 with no interior peak. Every internal validity index that can be computed on this data
points the same way as BIC: nothing settles (Figure 1). The shipped rule taxonomy itself scores a silhouette of **0.091**
in the full standardised feature space — measured with Euclidean distance on the one-hot
matrix, so it is **not on a common scale with the Gower ceiling above** and reads
qualitatively: near zero, neither better nor worse than the unsupervised partitions. We quote
the full-space figure rather than the −0.16 visible in a two-dimensional PCA projection,
because the projection overstates the overlap. `[Figure 2: silhouette by method and k]`

**(c) Independent families disagree about where the boundaries are.** If ten methods were
recovering the same latent partition, their labelings would agree. At k = 10 the median
pairwise Adjusted Rand Index (Hubert & Arabie, 1985) across methods is **0.41**; agreement is high only within
algorithmic families (the two Gaussian mixtures at 0.846; the Euclidean-centroid trio at
0.68–0.79). Six families cutting the same data six different ways is the signature of
partitions imposed on a continuum, not of segments awaiting discovery. `[Figure 3:
cross-method ARI heatmap]`

**(d) A label-free, algorithm-free check agrees — after an audit of its own instrument.**
Persistent homology (Carlsson, 2009) computed on the Gower distance matrix involves no k, no centroid, and no
distributional assumption. Its H1 loop persistence is indistinguishable from the noise floor of
a high-dimensional cloud (longest bar 1.158× the 95th percentile of all bars), ruling out
cyclic structure that partitional methods would be structurally unable to represent. The
*integer count* of significant H0 components, however, failed its own control when audited on
18 August: across 100 draws of unchanged (nothing-planted) data the gap heuristic returned a
median of 2, a 75th percentile of 4, and a maximum of **131**. A statistic that ranges 2–131 on
identical input cannot screen for anything, so we retire the count as an instrument and draw
no conclusion from any single draw of it. The modal outcome — one dominant connected
mass plus a fragment — is consistent with the continuum reading, but it enters the evidence as
the centre of a noisy distribution, not as a measurement. The loop-noise ratio and the barcode
shape are the parts of that analysis that survive the audit.

Among the ten methods, the full-covariance Gaussian mixture ranked first on the weighted
composite of agreement, separation, stability, resistance to feature deletion, learnability,
and cost
(score 0.849), and — critically — **remained first when the taxonomy-agreement axis, the one
circular axis, was weighted to zero** (0.798 vs. 0.785 for GMM-diag and 0.762 for LCA). The
agreement axis was measured against the v1 taxonomy in place at benchmark time; the
zero-weighted ranking is independent of any taxonomy and is the one we rely on.

Two methodological traps documented during the benchmark are worth reporting because they
generalise. First, high held-out learnability does not imply real structure: SVD+k-means at
k = 3 achieved 0.981 balanced accuracy from an SVM probe trained on its own labels while
scoring only 0.117 on separation — a perfectly *learnable* partition that is nonetheless an
arbitrary geometric slice through a smooth density. Separability figures should never be
quoted without a separation figure beside them. Second, every method proved fragile to
leave-one-feature-out deletion (minimum dropout ARI 0.15–0.49), indicating that no candidate
partition rests on redundant, mutually confirming evidence.

All four lines of evidence are claims about the modelled feature space, not about every
possible representation of a traveller; a cluster structure could exist along dimensions the
extract does not carry. §4.1.2 quantifies exactly how large and how distinct a real group
would have to be, in these features, before this battery would see it.

The same shape recurs one level down. When Latent Class Analysis was later run *within* each
large segment (§4.2.5), BIC again preferred the top of its allowed range in every parent. There
is no natural number of customer types inside a segment either; the continuum is the same at
both levels, and every partition we ship is a granularity choice we own rather than a
structure we found.

### 4.1.2 Bounding the null: detection power

A null result is only as strong as the instrument's sensitivity, so synthetic segments of
known prevalence (0.5–10% of bookings) and known distinctness (a mixing weight *w* from 0.1
to 1.0) were appended to the real population and the deployable four-method panel was refit,
with detection thresholds pre-registered from *w* = 0 negative controls. The analysis was
re-run on 18 August at k = 11 to match the shipped segment count (the July run used k = 10);
the conclusion did not move. Reading the majority verdict of the 12 method × archetype
combinations — a single sensitive cell is a selection effect and is never quoted; one
combination recovered a group at planted silhouette 0.114 while groups as distinct as 0.567
were missed elsewhere in the same grid, and both cannot be floors (Table 4.1):

**Table 4.1 — Majority detection floors from the planted-segment power analysis (18 Aug re-run, k = 11).**

| Planted prevalence | Majority-detection floor (planted silhouette) |
|---|---|
| 0.5% and 1% of bookings | **never detected at any distinctness tested** |
| 2% | detected from ≈ 0.494 |
| 5% | detected from ≈ 0.219 |
| 10% | detected from ≈ 0.13 |

The null can therefore be stated in bounded, falsifiable form: **no segment exists in these
features at or above 2% of bookings with distinctness at or above ≈ 0.494** — because a planted
segment of that size and faintness is reliably recovered — while a segment smaller than ~1% of
bookings (~229,000 bookings at population scale) could exist undetected. Recovery rates were
close across the two business-motivated archetypes and a random-direction control (21%, 29%,
and 32% of cells respectively), with the random direction — which has no business story —
sitting inside the range set by the two plausible ones, so the floors are a property of the
method panel, not of the archetype directions chosen. Because a planted group is internally
coherent in a way a real segment need not be, these floors are optimistic bounds rather than
guarantees. `[Figure 4: detection-power consensus grid, majority floor outlined]`

### 4.1.3 The resulting architecture: rules as taxonomy, clustering as diagnostic and refinement

Given (i) a continuum at the top level and (ii) a business requirement for named, actionable
segments, the final architecture is hybrid. A deterministic **rule waterfall** assigns each of
22,911,450 bookings (13.4M customers; 13,127 all-non-revenue bookings are excluded and labelled
as such in the export) to one of **eleven segments plus an `Unassigned` residual — twelve labels
the pipeline can stamp** (Table 4.2). Two descriptors travel *alongside* the segment rather than competing
with it: an `is_last_minute` flag covering every booking made within three days of departure
(4,411,666 bookings, 19.26%), and a three-level `value_band` (Budget 63.1% · Mid 30.9% ·
Premium 6.0%). Clustering is retained in two subordinate roles: as the diagnostic battery
reported above, and as the sub-segmentation layer of §4.2.5.

The taxonomy was co-designed with the airline rather than inferred and presented. PAL's revenue
managers returned 39 rules and answered all 24 follow-up questions; **57 constraints were
transcribed** (15 hard, 42 soft), each with provenance, scope, and a live firing count, validated
by an automated checker. All six enforce-grade hard rules are **asserted at build time, reading
the constraint file directly**, so the rules and the code cannot drift apart — a first draft of
the waterfall satisfied only four of six, which demonstrated that branch ordering alone does not
implement a "cannot be". The 21 live soft tendencies are scored against every booking in a
separate stage that **changes no label**: they are silent on 43.6% of the book (throughout, "the book" and "the base" mean the full
22.9M-booking population), agree with our
labels on 70.5% of the bookings where they fire, and their largest disagreement — routing
1,025,351 Last-Minute bookings to Leisure — independently corroborated the decision, taken with
PAL, to retire Last-Minute as a segment and keep it as the flag.

Table 4.2 states the shipped taxonomy in full — the twelve labels as the waterfall defines
them, in evaluation order, with each branch's provenance. Order is semantics: the waterfall is
first-match-wins, so a branch's real population is whatever reaches it, and the most
identity-certain evidence (award redemption, the corporate channel, the sea-crew channel) is
deliberately consumed first. The two descriptors are computed independently of the cascade:
`is_last_minute` is booking lead ≤ 3 days, and `value_band` follows the fare-brand ladder
(tiers 1–2 Budget, 3–4 Mid, above 4 Premium).

**Table 4.2 — The co-designed taxonomy: the v2 waterfall's defining rules, in evaluation order
(first match wins). "Original design" denotes the pre-SME ten-segment proposal; every v2 branch
change traces to a named SME constraint or PAL decision of 17–18 August 2026.**

| # | Segment | Defining rule (branch condition) | Provenance |
|---:|---|---|---|
| 1 | Mabuhay Loyalist | Award redemption (`is_award`) | Original design; visibility caveat in §4.2.1 |
| 2 | Corporate | Corporate channel (TMC / corporate web portal), or a business-cabin leg booked ≤ 7 days out | Original design |
| 3 | Corporate | Round trip with a same-/next-day turnaround (stay ≤ 1 night) on a Flex-or-above fare | SME hard rule H11 — the sheet's one `must_be`; added in v2 |
| 4 | Corporate | Round trip booked ≤ 3 days out, stay ≤ 3 nights, with a premium-cabin leg | SME hard rules H10 + H12, satisfied by one composite fence; added in v2 |
| 5 | MICE | Group booking, round trip, booked ≥ 45 days out, 3–7-night stay, no business-cabin leg | PAL-approved 17 Aug; H13 in the weakened form PAL accepted (party size is unobservable) |
| 6 | Pilgrimage | Destination in the pilgrimage-hub list | Original design; PAL confirmed the list complete, 18 Aug |
| 7 | OFW/Migrant | Sea-crew booking channel | Original design; the channel is identity-definitive, so it fires before any geography test |
| 8 | International Student | International round trip with a 90–150-night stay | PAL-approved 17 Aug; the stay-length core of SME rule S38, its academic-month clause dropped to protect the `dep_month` validation anchor |
| 9 | OFW/Migrant | Foreign-issued international economy (fare tier ≤ 4), one-way | Original design |
| 10 | Balikbayan/VFR | Foreign-issued international economy (fare tier ≤ 4), round trip — excluding premium stays of ≤ 3 nights | Original design; the exclusion is SME hard rule H08, added in v2 (2,934 bookings violated the `cannot_be` without it) |
| 11 | Ultra Wealthy Leisure | Premium-cabin round trip booked ≥ 30 days out with a stay of ≥ 7 nights | PAL-approved 17 Aug; ordered before Premium Bleisure, whose superset condition would otherwise starve it |
| 12 | Premium Bleisure | Any premium-cabin leg on an international itinerary | Original design |
| 13 | Outbound International Leisure | Philippine-issued international travel with no premium-cabin leg | Added in v2; closes taxonomy gap #4 — 75% of the former `Unassigned` |
| 14 | Leisure | Domestic travel with no premium-cabin leg | Original design; renamed from `Budget/Adventure` (PAL, 18 Aug) |
| 15 | `Unassigned` | No branch fires — the residual | Characterised precisely in §4.2.1: domestic premium-cabin travel the waterfall has no branch for |

Three labels from the original design are retired rather than redefined — `Family`,
`Digital Nomad`, and `Last-Minute`, for the reasons given below — and the v1 waterfall is
retained in the build output (`proxy_segment_v1`), so every before/after claim in this chapter
is an A/B on identical data rather than a comparison against memory.

Against the original ten-segment design, the shipped taxonomy adds four segments (Outbound
International Leisure, Ultra Wealthy Leisure, International Student, MICE) and removes three.
`Family` was deleted because it had no positive definition — 100% of it was "a group booking no
other rule claimed" — and `Digital Nomad` because it is unimplementable in anonymous data;
applying "a positive definition beats a residual" honestly produced deleted segments rather than
better rules, which we record as a legitimate outcome. **Genuine reclassification between the two
generations is 23.4% of bookings (5,358,355).** The textual label-difference rate is 62.7%, but
most of that is the `Budget/Adventure → Leisure` rename and must not be quoted as change. The
single largest improvement is the residual: **`Unassigned` fell from 9.58% to 2.47% of bookings,
a 74% reduction**, closing what had been reported to the airline as the largest actionable gap —
75% of the former residual was Filipino-issued international economy travel, now the Outbound
International Leisure segment. Converting Last-Minute from a segment to a flag exposed
4,411,666 short-lead bookings where the segment had ever shown 2,945,686: a priority cascade
hides every overlapping signal below the winning branch, and converting one branch to a flag
recovered 50% more visible short-lead volume without moving a single threshold.

Agreement between unsupervised partitions and the shipped taxonomy has a shape worth reading
precisely (Figure 1, right panel). The maximum ARI over the k = 1–9 LCA sweep is **0.537, at k = 2** — but a
composition probe shows that cut is geography, not customer structure: it matches the single
domestic/international bit at ARI 0.909, assigns every purely international segment to one
class, and splits Corporate — the taxonomy's most geographically mixed segment (§4.2.1) —
almost exactly along its 57/43 domestic/international mix. Past that spine, agreement falls as
k approaches the taxonomy's own cardinality: 0.306 at k = 3, **0.389 at k = 4** (vs. 0.319
against the v1 taxonomy — the redesign agrees *more* with what an unsupervised method finds),
0.210 at k = 9. That is the expected reading given the continuum: data-driven partitions
recover the taxonomy's dominant axis and none of its finer boundaries — they neither reproduce
nor contradict the business taxonomy; they cut the same smooth mass along different, roughly
equally arbitrary planes. The justification for the rule taxonomy is therefore not that the data demands it, but
that it is *consistent with* the data (no natural partition is being overridden) and
independently validated on evidence the rules never saw — the subject of §4.2.

## 4.2 Analytical Interpretation of Passenger Segments

### 4.2.1 The eleven-segment taxonomy

Applied to the full booking base, the taxonomy resolves as follows (Table 4.3; booking grain;
revenue in USD).

**Table 4.3 — The taxonomy applied to the 22.9M-booking population: sizes, revenue, and revenue
share (census figures, USD).**

| Segment | Bookings | Share | Mean revenue / booking | Share of revenue |
|---|---:|---:|---:|---:|
| Leisure | 11,595,711 | 50.61% | $80 | 14.95% |
| OFW/Migrant | 3,907,805 | 17.06% | $312 | 19.64% |
| Balikbayan/VFR | 2,871,255 | 12.53% | $615 | **28.41%** |
| Outbound International Leisure | 2,182,074 | 9.52% | $398 | 13.98% |
| Corporate | 1,168,451 | 5.10% | $460 | 8.65% |
| `Unassigned` | 566,126 | 2.47% | $177 | 1.61% |
| Premium Bleisure | 343,309 | 1.50% | $1,188 | 6.57% |
| Ultra Wealthy Leisure | 157,490 | 0.69% | $1,968 | 4.99% |
| Pilgrimage | 43,616 | 0.19% | $404 | 0.28% |
| International Student | 42,153 | 0.18% | $1,159 | 0.79% |
| MICE | 27,007 | 0.12% | $269 | 0.12% |
| Mabuhay Loyalist | 6,453 | 0.03% | $113 | 0.01% |

`[Figure 5: booking share vs revenue share by segment]`

At the customer level the labels are stable rather than per-trip accidents: **87.8% of customers
never leave their segment** across every booking in the extract, so a segment stamped on a
person means something.

Four qualifications accompany the table.

**`Unassigned` is a residue with a precise algebraic identity, not a missing segment.** In a
first-match-wins waterfall the residual is fully determined by what the catch-all branch
excludes, and reading it that way names the population exactly: because the final branch routes
every domestic booking without a premium cabin to Leisure, a domestic booking can only reach
`Unassigned` by carrying a business- or premium-economy leg — and indeed the residual's domestic
subset and its premium-cabin subset are the same 94.5%. What remains after v2 is therefore
**domestic premium-cabin travel the waterfall has no branch for**, plus a 5.5% sliver of
foreign-issued international economy on premium fare brands. It is 81.4% Premium by fare brand
(against 6.0% book-wide) yet averages only $177 per booking — premium by brand and cheap by
price. Whatever rule eventually claims it should be designed for that traveller, not as a
low-value sweep-up.

**Mabuhay Loyalist measures our visibility, not the loyalty base.** With no loyalty-tier field
in the extract, the only observable signal is award redemption: the segment is 100% award
bookings with a 7.8% repeat rate — an award-redemption artefact. 0.03% of bookings cannot be the
true footprint of a national flag carrier's frequent-flyer programme.

**Corporate is identified without any company or loyalty identifier**, so its rules necessarily
also capture affluent short-notice leisure; we grade its label confidence as diluted. It is also
the most geographically mixed segment (57.2% domestic / 42.8% international) — consistent with
business travel at both scales. Only Leisure is purely domestic (by construction), and four
segments are purely international; OFW/Migrant is 9.6% domestic, every one of those 375,888
bookings being sea crew, whose channel identifies them before any geography test.

**The `is_last_minute` flag is not independent of the waterfall, and per-segment short-lead
rates must be read against the rules.** Three of the eleven rules read booking lead directly:
MICE (`lead_days ≥ 45`) and Ultra Wealthy Leisure (`lead_days ≥ 30`) are 0% short-lead **by
construction**, and one of Corporate's two branches admits only short-lead bookings. On
Corporate's other branch — the corporate-channel branch, which carries no lead-time condition —
the segment is **23.3% short-lead**, still above the 19.26% book average, so the behavioural
claim survives at a quarter of its apparent size. 23.3% is the quotable figure; the raw 35.6%
is partly circular.

### 4.2.2 Construct validity: the segments are distinguishable on evidence the rules never saw

Construct and criterion validity are used in §§4.2.2–4.2.3 in their classical
measurement-theory sense (Cronbach & Meehl, 1955), adapted to a setting with no ground-truth
labels. Because every clustering-vs-rules comparison is circular (the proxy labels are the
rules' own output), validation was rebuilt on *anchors* — fields no rule consumes — with a leak audit
(July 2026) that had teeth: it found that age *capture* is a near-perfect proxy for
international travel (age is recorded on under 1% of domestic bookings against 88% of
international ones), which is a rule bit. The harness therefore withholds anchors **per pair**:
passenger age and its capture flag are admitted only for pairs where international-vs-domestic
is not the boundary under test, and country, channel, and destination-region identity likewise.
Only two anchors — departure month and customer lifetime booking count — are unconditionally
clean. Sea-crew bookings are excluded throughout, because the channel anchor would otherwise
carry the OFW rule inside it. The harness includes a negative control (each segment split
randomly in half must yield AUC ≈ 0.50; observed 0.494–0.513, passed) and positive controls
that calibrate the two ceilings: a known-different pair reaches 0.641 on the strict two-anchor
set and 0.816 on the per-pair adaptive set.

The two measures answer different questions and every quotation below names which it uses. On
the **adaptive** measure — the interpretable one — **all 55 segment pairs are at least weakly
distinguishable (AUC ≥ 0.60): 44 clearly so (AUC > 0.75), 11 weakly, none indistinguishable;
median AUC 0.861, range 0.611–0.982.** On the **strict** two-anchor measure the median is 0.637
and 11 pairs fall below 0.60 — a matrix that is thin **by construction, not by failure**: after
the leak audit only two fields are unconditionally clean, and a two-column model cannot separate
much. A low strict AUC now means "we withheld the evidence that would have separated them", not
"these segments are the same". Two reading disciplines attach to the headline. Because
anchors are withheld per pair, adaptive cells rest on different feature sets: the 55-pair
distribution summarises the evidence for each boundary and is not a league table of boundary
quality — cells are directly comparable only within groups of equal withheld anchors. And the
55 pairs are tested simultaneously with no multiplicity correction; per-cell sampling error is
small relative to the band widths at these sample sizes, but a verdict sitting within a few
hundredths of a band edge should be read as provisional. `[Figure 6: construct-validity AUC
matrix]`

The weakest boundary is instructive, and we report it at length because the honest version
is a negative result. **OFW/Migrant vs. Balikbayan/VFR** — 6.8M bookings, 30% of the
base, separated in the waterfall by a single bit (one-way vs. round-trip) — scores **0.548
strict** (not distinguishable), **0.713 adaptive**, and 0.72 on an isolated clean-pair design.
The v2 redesign was in part motivated by this boundary, and **it did not improve it**: an A/B
holding method, anchors, and population fixed and varying only the labels scored v1 at 0.730
and v2 at 0.728 — neutral, within noise. Like for like, the strict cell moved 0.608 → 0.548
across the two generations; the apparent improvement "0.608 → 0.72" that circulated in working
documents compares two different tests and is disowned here. The mechanism is plain: the only
v2 change touching this pair moves ~40,000 bookings, 1.4% of the branch, and the stay-length
discriminator that motivated the work was encoded as a soft prior, which by design changes no
label. The boundary survives two adversarial checks — within single issue-countries it remains
weakly distinguishable in 13 of 17 markets (AUC 0.605–0.721), and base-rate-normalised
seasonality shows the theoretically predicted signature — a December Balikbayan peak against
an OFW peak in August. Both checks were measured on v1 labels; the v2 change moves 1.4% of
this branch, so they stand. We
retain the split because the two populations demand opposite commercial treatment (§4.3), and
we flag it as the taxonomy's most improvable boundary rather than as settled.

One domain finding bears directly on this boundary and we report it with its confound attached.
**Manila–Gulf traffic runs on a one-month clock that no other corridor has**: 19.11% of Gulf
round trips fall in the 28–32-night window against 8.48% at 12–16 nights — the only corridor
where the month window outweighs the fortnight (every other corridor's ratio is ≤ 0.60, the
Gulf's is 2.25). The airline's revenue managers attribute the pattern to employer-mandated
leave, and two parts of their original claim did not survive testing: there is no excess at the
claimed ~45 days, and pooling Hong Kong/Taipei with the Gulf destroys the discrimination
rather than strengthening it. The confound is open: a one-month maximum-stay condition on Gulf
economy fares would produce the identical pattern, and the fare-basis field that would settle it
has been requested. Until it arrives, we present the pattern, not the explanation —
and, consistent with that, the stay-length rule is encoded as a soft prior that changes no
label.

Two limits on interpretation are maintained throughout. Distinguishability shows the groups
*differ*; it cannot show that the group labelled Corporate is what the airline's commercial
team means by Corporate — the labels are *behaviourally validated, not externally confirmed*,
and adjudication against ~1,000 SME-labelled bookings remains the outstanding strongest test.
And a weak boundary is evidence about that boundary, not authority to merge segments: an
unsupported split is reported to the airline as a proposal with evidence attached.

### 4.2.3 Criterion validity: the labels predict outcomes they were not built from

The segment label alone predicts operational outcomes that no rule consumes: completion of
travel (AUC 0.598 against the 11-feature model's 0.906) and rebooking within 180 days (0.604
against 0.694; right-censored bookings excluded). A third outcome, refund incidence, is
excluded from all claims: at 347 events the model is flagged unstable by its own harness and
its AUC is not quotable. Relative to the full feature model, the single label retains 24% and
54% of achievable discrimination on the two stable outcomes, while adding essentially nothing
*on top of* the features (incremental AUC +0.0005 and +0.0024). The correct reading, which we
adopt explicitly and carry onto the limitations of the deliverable, is that the segmentation is
a **lossy but faithful compression** of behavioural signal into eleven communicable labels:
real signal alone (0.60 against a 0.50 coin flip, twice), valuable for targeting and reporting,
not a source of signal beyond its inputs, and not sold as one. This is the expected result for
a rule-based segmentation — the label *is* a function of the features — and it is a design
property, not a failure.

Customer-level behaviour corroborates the gradient the labels claim: the floor on repeat
behaviour runs from 12.2% (Pilgrimage) to 36.4% (Corporate). We state it as a floor
deliberately. 73.9% of customers appear exactly once in the extract, and in a 26-month window a
new customer and a lost one are indistinguishable, so no churn rate is computable from this
data. For the same reason we never quote a "share who never return": on a fixed
horizon, **26.5% of customers rebook within 12 months of their first booking** (measured on the
8.11M customers with a full year of runway), and that is the honest form of the number.

### 4.2.4 Temporal stability: the segmentation is not a one-period artefact

Splitting the extract into two adjacent twelve-month issuance windows (9,770,643 vs. 10,076,646
bookings, both placed strictly inside the region where no lead time up to the 365-day clip is
censored, with outcome fields near the extract boundary excluded from every comparison):

- **Sizes hold.** Total-variation distance between the two years' segment mixes is **1.71
  percentage points** on bookings — on full-population counts, not samples. The largest single
  move is OFW/Migrant at 1.39 pp.
- **Revenue mix moves more than headcount** (TVD 3.36 pp), the operative example being
  Balikbayan/VFR: flat booking share against a revenue-share decline of 29.35% → 26.64%. We
  report both figures together as a matter of policy, because revenue share is the quantity the
  commercial organisation acts on and it is the less stable leg.
- **Composition holds where the volume is.** Eight of the twelve labels show
  negligible-to-small profile drift, jointly carrying **98.1% of bookings**. The four drifting
  labels (Premium Bleisure, Pilgrimage, MICE, Mabuhay Loyalist) jointly hold 1.9% of the book;
  in the three smallest of them a few hundred bookings move a mean, and Premium Bleisure's
  drift is on a single revenue feature. All four are classified as unresolved rather than as
  established behavioural change, and should be re-profiled before campaign use.
- **The population has measurably shifted, mildly.** An adversarial window classifier reaches
  AUC 0.621 on the modelled features, read against a negative control at 0.500 and a positive
  control at 0.995 — clear of the negative rail, so the drift is real even though the segment
  mix absorbed it (segment-mix PSI 0.0028). The one input flagged for retraining illustrates
  why monitoring must separate *new categories* from *drift*: the channel field's PSI of 0.4111
  is produced almost entirely by **NDC, a distribution channel PAL switched on mid-window**
  (0 bookings in the earlier year, 366,890 — 3.64% — in the later); excluding the new category
  the channel is stable (PSI 0.0285).
- **Whether a year-old model still carves the data is unresolved, and we say so.** The transfer
  panel disagrees: GMM(full) labels the later window at 1.24× its own within-window
  self-agreement ceiling, while LCA reaches only 0.89× — one method on each side of 1.0. No
  refit-cadence claim is made on this evidence, and none should be until the stage reports a
  spread across seeds. This paragraph replaces an earlier, stronger claim: a prior run reported
  LCA at ratio 1.13, a figure that is **formally withdrawn** — it was computed on a silently
  43%-sized sample, and a ratio that crosses 1.0 when the sample doubles was never a finding.
  The reporting defect that let it ship (quoting the best method of a panel) has been removed
  from the generator, which now prints every method and applies a majority rule.

`[Figure 7: booking vs revenue share across the two windows]`

### 4.2.5 Sub-types within the large segments: fitted, audited, and assigned at population scale

Within each of the five largest segments — Leisure, OFW/Migrant, Balikbayan/VFR, Outbound
International Leisure, and Corporate, jointly 94.8% of bookings — Latent Class Analysis
resolves four sub-types per parent: twenty cells in all. Two properties of this layer matter
more than the twenty names.

First, its honesty condition. The class-count search ran over k = 2–4 and **BIC preferred the
maximum in every parent** — the identical ceiling behaviour as the top level (§4.1.1). "Four
sub-types" is therefore the most the search offered, not a discovery, and the layer inherits
the continuum caveat in full: these are actionable partitions of a smooth space, capped at a
business-actionable granularity we own. What *is* a finding is the shared grammar: every parent
splits along the same three axes — trip direction, booking timing, and fare tier — recovered
independently in five separate fits that each saw only one segment's bookings.

Second, unlike the interim version of this work, the layer is **assigned at the row level, on
the full population**. Because the model's inputs are fully discrete, its input domain is
enumerable: 17,847 distinct feature cells cover all 21,725,296 bookings in the five parents,
so the model is fitted on the count-weighted cell table — verified equivalent, to machine
precision, to fitting every booking — with the information criterion recomputed against the
true population count. Fitting the population rather than a sample surfaced and fixed a class
of defects invisible at sample scale (an encoder that had learnt its alphabet from the sample,
a sample-derived imputation constant, and naming collisions now resolved with qualifiers and
composite keys). The profiles below are population-exact and supersede the sampled profiles
quoted in earlier working documents and the defence deck; the largest revision is in
Balikbayan/VFR, where the far-advance saver mass resolves into a connecting sub-type (median
$418) and a nonstop one (median $962).

Commercially, the layer's value is the revenue spread *inside* single segments.
**Balikbayan/VFR spans $322 to $962 median revenue on booking horizon alone** (~3× — every
sub-type is a round trip, so horizon is the only axis that varies), and **Corporate spans $113
to $643** with every sub-type short-lead, so its spread is direction and fare rather than
timing. Leisure spans $27 (advance-purchase supersaver one-ways, 28.4% of the segment) to $96.
The complement is just as useful: OFW/Migrant (~1.8×) and Outbound International Leisure
(1.2×) are nearly flat — **two segments that demonstrably do not need sub-segment pricing**, a
negative result that spares effort. `[Figure 8: sub-type profiles within the five parents]`

## 4.3 Strategic Marketing and Revenue Implications for Philippine Airlines

### 4.3.1 The volume–value inversion

The taxonomy's first strategic lesson is that PAL's volume story and value story are close to
inverses. Leisure supplies 50.6% of bookings at $80 per booking and 15.0% of revenue;
Balikbayan/VFR supplies 12.5% of bookings and 28.4% of revenue; Ultra Wealthy Leisure supplies
5.0% of revenue from 0.69% of bookings. On the CY2025 flown base, the total-variation distance
between the booking mix and the revenue mix is 36.3 percentage points — $919M of revenue sits
in different segments than a volume-proportional view would place it. Any strategy metric
denominated in passengers therefore systematically overweights the low-yield base, and any
uniform treatment (a network-wide promo fare, for instance) transfers margin to segments that
would have flown anyway while failing the segments that carry the revenue. Segment-denominated
reporting is the correction.

### 4.3.2 Segment-level implications

**Balikbayan/VFR — the revenue engine, and the active risk.** Highest revenue contribution,
the longest planning horizons in the base, a verified December peak, and the one materially
adverse trend in the data: a 2.7-pp revenue-share decline year-on-year on flat volume — yield
erosion, not attrition. It is also 49.9% connecting traffic on the largest revenue base in the
book, which makes transfer experience and lounge access a Balikbayan question before it is a
premium-cabin one. Implications: protect yield on diaspora corridors rather than stimulate
volume; time campaigns to the far-advance windows the sub-types reveal (the nonstop far-advance
sub-type books a median 114 days out at $962 median revenue); and diagnose the yield decline
before discounting into it.

**OFW/Migrant — high-value, structurally distinct, operationally underserved.** One-way,
short-to-medium lead, foreign-issued, with a distinct high-revenue connecting sub-type on the
Middle East and long-haul corridors — and a channel fact with no parallel elsewhere: **sea-crew
bookings are 27.5% of the segment and ~0% of everything else, a $136.6M channel that is
effectively one segment.** Because the Balikbayan boundary is the taxonomy's weakest (§4.2.2),
campaign logic should not lean on that single bit: where treatment differs sharply between the
two, eligibility should be checked against the sub-type profile, not the label alone. The
seasonal complementarity — OFW August peak against the Balikbayan December peak — allows the
same corridors to be revenue-managed to two calendars, and the Gulf one-month clock (§4.2.2),
once its fare-rule confound is settled, is a scheduling and inventory fact of direct use.

**Corporate and Premium Bleisure — the retention economics, under a labelled caveat.** Together
6.6% of bookings and ~15% of revenue, with the highest repeat floors in the base: these are the
segments where a single defection costs the most future revenue — the rationale for the
asymmetric misclassification-cost weighting of §4.3.5. The dominant marketing error to avoid is
documented in the deliverable itself: do not send promotional fares to Corporate-labelled
customers (it dilutes yield in the one segment defined by schedule-over-price), and do not read
a quiet quarter as churn — with 73.9% of customers observed only once, churn is not measurable
here. Both recommendations carry the diluted-trust caveat: without a company or loyalty
identifier, Corporate targeting is propensity, not identity, and its honest short-lead rate is
23.3%, not the partly rule-induced 35.6%.

**Leisure — defend with cost discipline, refine with sub-types.** The LCC battleground, now
half the book. Its sub-types differ enough to matter operationally: the advance-purchase
supersaver cohort (median $27, 28.4% of the segment) is price-elastic filler that should never
receive acquisition spend, while the round-trip advance cohort (median $96, 33.8%) is the
natural target for ancillary attach. Treating the segment as one 50.6%-of-bookings block would
be the single largest source of wasted marketing spend available in this taxonomy.

**Outbound International Leisure — the segment the residual was hiding.** New in v2, 9.5% of
bookings at 14.0% of revenue, created by giving a positive definition to three-quarters of the
former `Unassigned`. After a revenue-measurement correction (§4.3.7) it is the *most
homogeneous* large segment (1.29× within-label spread), so sub-segment pricing buys little
here; its value is that 2.2M bookings previously reported as a gap now carry an actionable
name.

**The niches.** Pilgrimage is the cleanest-defined segment (destination settles it) and cheap
to activate around known event calendars. International Student is small but high-value
($1,159 mean) with a long-stay definition that makes it visible to schedule planning. MICE is
valued per booking in this table and per contract in reality — its 0.12% understates it by
construction. All four drifting labels of §4.2.4 should be re-profiled before campaign use.

### 4.3.3 Which departments can act on this, and in what order

Organising the implications by the department that owns each decision, rather than by segment,
changes the readiness ordering — because it forces the question "who can act on this today".

**Sales and Customer Experience can act first, because their use requires no response
assumption.** Prioritisation reallocates effort already being spent, so the measured fact is
the deliverable: agency dependence spans 6.6× across segments (11.8% for Corporate to 78.2% for
Pilgrimage); Corporate is 55.5% corporate-channel; digital revenue share spans 19× (2.6% to
48.8%) and connecting share 9× — so app investment, agency strategy, and transfer experience
each have a named segment owner from day one. **Revenue Management follows, with
instrumentation**: sub-types priced at ≥1.25× their parent mean hold 22.9% of parent bookings
and 29.7% of parent revenue ($645.8M on the CY2025 flown base) — the population a
parent-uniform price treats as average — but acting on it needs a measured recovery rate, not
an assumed one. **Marketing's case depends on response assumptions** and is stated as a
breakeven rather than a forecast: against a placeholder year-1 cost of $18,800 and a modelled
$16.1M/yr of avoidable discount dilution, implementation pays for itself if 0.116% of the
dilution is averted — one dollar in 859 — and still clears at 4.7% with every placeholder made
ten times worse at once. The claim is not "the benefit is $16M"; it is that the decision does
not depend on knowing the benefit. **Loyalty must wait**, and saying so strengthens the case:
with 73.9% of customers observed once and zero tenure, churn is not computable from this
extract, and the Mabuhay segment is an award-redemption artefact until a loyalty field arrives
(§4.3.6). One enabling fact underpins all of it: 87.8% of customers never leave their segment,
so a segment label attached to a person is a stable attribute, not a per-trip accident.

### 4.3.4 What the continuum finding implies for strategy

The absence of natural clusters is itself a strategic result, in three ways. First, it means
**the taxonomy is a management instrument, not a discovery**: its boundaries are choices, so
they can and should be moved when commercial policy changes — nothing in the data will resist,
and governance (documented rules, versioned changes, build-time assertions) matters more than
it would for "found" segments. The v1 → v2 revision is the existence proof: four segments
added, three removed, a residual cut by 74%, at a measured cost of 23.4% of labels — executed
in days because the boundaries live in reviewable rules. Second, it cautions against
**personalisation theatre**: customers occupy a smooth behavioural space, adjacent-segment
misassignment is expected, and 12.2% of customers cross segment boundaries within the extract,
so treatments should degrade gracefully across boundaries rather than switch discretely.
Third, the detection-power bound marks a **known blind spot with commercial meaning**: a
coherent group smaller than ~1% of bookings (~229,000 bookings) — a single corporate account
programme, a nascent route community — would be invisible to this pipeline, so segment
discovery below that scale must come from business knowledge or external data, not from this
model.

### 4.3.5 Pricing the boundaries: the cost of misclassification

The asymmetric cost matrix that weights the pipeline's error reporting was rebuilt from
sourced, segment-level economics: annual value at risk per misclassified customer spans **$495
to $9,784** across segments — the project's first dollar-denominated spread, replacing a
placeholder ladder whose dollar column was a flat multiple of an arbitrary penalty and which
was inverted against measured revenue in two places. The notable moves follow the measurement:
Premium Bleisure 4 → 9, Balikbayan/VFR 2 → 4, Corporate 10 → 8, with three documented overrides
where the measurement is known to be blind (Mabuhay sees only award redemptions; Corporate's
rule is the most contested; MICE is valued per booking when its revenue is per contract).
OFW/Migrant is deliberately left at its measured weight of 3, with the argument that it
"matters more than its per-booking value" flagged to the airline as a commercial judgement
rather than an empirical one. PAL's response — "see run first" — means these weights enter the
deliverable as a proposal, not as agreed values.

### 4.3.6 The data investment case

The analysis makes specific, evidence-backed cases for four data acquisitions, each following
from a measured limitation rather than a general appetite for data. **Loyalty and
frequent-flyer fields** (PAL agreed on 18 August to supply frequent-flyer, tour-code, and
upgrade indicators) are the largest: they sit on the critical path of the weakest boundary
(§4.2.2), would make the Mabuhay segment measurable (its 0.03% is a visibility artefact), and
would resolve the Corporate dilution problem. **Fare-basis codes** settle the one open confound
in the study's best domain finding — whether the Gulf one-month clock is worker behaviour or a
fare rule. **Age capture at booking**: age is the strongest admissible discriminator wherever
it is admissible, yet it is recorded on under 1% of domestic bookings; raising capture would
improve both validation power and targeting precision. **Trip context** (length of stay on
foreign-originating itineraries, ancillary spend) would let the weakest boundaries be tested on
the evidence most likely to separate them.

### 4.3.7 Boundary conditions on the strategic claims

Seven limits circumscribe everything above, and we prefer to own them in print. The
segment *names* are behaviourally validated but not externally confirmed; adjudication against
~1,000 SME-labelled bookings remains the outstanding strongest test. Prediction is not
causation: a segment that predicts rebooking is not a licence to treat its members differently
without a policy decision. Temporal stability is demonstrated across one twelve-month step
inside one extract — not through a demand shock, network change, or fare restructure — and the
revenue mix is the less stable leg, so segment revenue shares should be re-measured, not
carried forward, at each planning cycle; whether models transfer across years is explicitly
unresolved (§4.2.4). The segmentation adds almost no predictive signal on top of its input
features — by design, and stated rather than discovered. The build carries known measurement
edges, each documented where a consumer will hit it: the pipeline output moves by ±1 booking
between runs (1,830 tied sort keys, cause recorded); 1.65% of bookings carry a destination
region assigned by an alphabetical tiebreak on multi-region trips; refund incidence is
unusable as an outcome at 347 events; and revenue aggregations must be computed over
unfiltered coupon rows — a plausible-looking primary-coupon filter silently discards up to
half of a multi-leg segment's revenue, an error caught here only by cross-checking two
independently computed aggregates. The extract has no ancillary revenue at all, so every
revenue figure understates the commercial difference between segments that differ in ancillary
attach. And every number from a sampled analysis in this chapter is a single-seed point
estimate reported without an interval — the withdrawn transfer ratio of §4.2.4 is the measured
cost of that practice, and seed-spread interval estimation is the pipeline's outstanding
methodological upgrade.

---

*Draft ends. Figure files (all in `outputs/report_real/figs/` unless noted; 1–2 and 4–6
generated by `src/manuscript_figures.py`, 3 and 7 by `src/report_figures.py`):*

| Placeholder | File | Content | Status (23 Aug) |
|---|---|---|---|
| Figure 1 | `clust_01_bic_ari.png` (+ `lca_bic_ari.csv`, `lca_validity_indices.csv`) | BIC k = 1–9, ARI vs the taxonomy, and silhouette/DB/CH — no index settles; geography-only agreement peak | current — 23 Aug (indices computed 23 Aug; the plates artifact carries all five panels) |
| Figure 2 | `ms_fig1_separation_ceiling.png` | Gower silhouette by method × k — the 0.381 ceiling | current — rendered 23 Aug (stress-test inputs unchanged since 28 Jul) |
| Figure 3 | `ms_fig2_cross_method_ari.png` | cross-method ARI heatmap at k = 10 | current — rendered 23 Aug |
| Figure 4 | `ms_fig5_detection_floor.png` | detection-power consensus grid, majority floor outlined | current — rendered 23 Aug (18 Aug k = 11 grid) |
| Figure 5 | `eda_01_segments.png` | segment volume vs revenue share | current — rendered 23 Aug (v2 labels, USD) |
| Figure 6 | `ms_fig4_construct_auc.png` | construct-validity AUC matrix | current — rendered 23 Aug (adaptive matrix; weakest cell 0.611 outlined) |
| Figure 7 | `ms_fig6_temporal_stability.png` | booking vs revenue share across the two windows | current — rendered 23 Aug (TVDs computed from data) |
| Figure 8 | `sub_01_subtypes.png` | sub-type profiles within the five parents | current — rendered 23 Aug (population-exact profiles, five parents; `fig_s07_sankey_balikbayan_vfr.png` remains the deck's worked example) |

*Figure numbers follow citation order (renumbered v1.2); the `ms_figN` file basenames keep their
original numbering — the table above is the mapping. All eight were regenerated on 23 Aug:
`python src/manuscript_figures.py` renders the `ms_fig*` files from saved stage outputs (no
refits); `python src/report_figures.py` renders Figures 1, 5, and 8 from the current parquet and
the population profiles. Screenshot-ready plates for every figure, in this order:
the "PAL Manuscript Plates" artifact.*

*References cited in this chapter (for merge into the manuscript bibliography):*

- Caliński, T., & Harabasz, J. (1974). A dendrite method for cluster analysis. *Communications in Statistics*, 3(1), 1–27.
- Carlsson, G. (2009). Topology and data. *Bulletin of the American Mathematical Society*, 46(2), 255–308.
- Davies, D. L., & Bouldin, D. W. (1979). A cluster separation measure. *IEEE Transactions on Pattern Analysis and Machine Intelligence*, PAMI-1(2), 224–227.
- Cronbach, L. J., & Meehl, P. E. (1955). Construct validity in psychological tests. *Psychological Bulletin*, 52(4), 281–302.
- Gower, J. C. (1971). A general coefficient of similarity and some of its properties. *Biometrics*, 27(4), 857–871.
- Hubert, L., & Arabie, P. (1985). Comparing partitions. *Journal of Classification*, 2(1), 193–218.
- Kaufman, L., & Rousseeuw, P. J. (1990). *Finding Groups in Data: An Introduction to Cluster Analysis*. Wiley.
- Nylund, K. L., Asparouhov, T., & Muthén, B. O. (2007). Deciding on the number of classes in latent class analysis and growth mixture modeling: A Monte Carlo simulation study. *Structural Equation Modeling*, 14(4), 535–569.
- Rousseeuw, P. J. (1987). Silhouettes: A graphical aid to the interpretation and validation of cluster analysis. *Journal of Computational and Applied Mathematics*, 20, 53–65.
- Schwarz, G. (1978). Estimating the dimension of a model. *Annals of Statistics*, 6(2), 461–464.
- Teichert, T., Shehu, E., & von Wartburg, I. (2008). Customer segmentation revisited: The case of the airline industry. *Transportation Research Part A: Policy and Practice*, 42(1), 227–242.
