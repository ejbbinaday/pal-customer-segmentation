# Continuum Levers — implementation plan

**Written:** 13 August 2026
**Question it answers:** *the continuum finding is established for booking attributes, cross-sectionally,
in the current 11-feature space. Is it a property of PAL's customers, or of our measurement?*

**Companion:** `docs/recommendations-plan.md` (Phases 0–4 — this plan extends Phase 4 rather than
restating it) · `docs/methodology.md` §Techniques · `outputs/model_stress_test/summary.md`

---

## ⛔ PROGRAMME RESULT — 13 August 2026: all six levers null

Run as probe-level screens (3-method panel, k=3–8, 20k samples, same `gower`/`gower_sil` as the harness).
**~14 pre-registered comparisons, none cleared.** Full detail in `docs/knowledge-base.md` §15 and
`outputs/levers/`.

| Lever | Score vs its bar | Verdict |
|---|---|---|
| **A** stay length | 0.319 vs 0.45 · mean delta −0.007 | ❌ Null |
| **B** strip populations | −0.022 vs +0.08 required | ❌ Null — closes the "mixed populations" explanation |
| **C** per-market | 3 of 6 markets cleared; majority required | ⚠️ Fails, but a **systematic pattern** — see below |
| **D** learned representation | 0.304 vs 0.5 · **control leaked at 0.219** | ❌ Null |
| **E** longitudinal | 0.211 vs 0.5 · ARI 0.048 vs 0.6 · **+0.006 over noise** | ❌ Null — closes the biggest open question |
| **G** coarser taxonomy | weakest AUC 0.606 vs 0.75 · signal −44% | ❌ Null — **refutes our own proposal** |

### The instrument this produced: a silhouette **noise floor of 0.205**

Shuffling every feature column (three seeds) and re-running the panel scores **0.201 · 0.214 · 0.201,
mean 0.205**. That is what *no structure at all* looks like on this data. **Never measured before, and it
recalibrates every separation number in the project:**

- The **0.381 ceiling sits +0.176 above the floor — comfortably real.** The continuum finding stands.
- **The textbook bands are wrong for this data.** ">0.5 strong · 0.25–0.5 weak-but-real · <0.25 none"
  assumes a floor of 0. Here "none" is **0.205**.
- ⚠️ **The LCA sub-type silhouettes (0.204 · 0.215 · 0.264) sit at that floor.** Needs a matched
  within-parent shuffled control before acting — but `provisional` now looks generous.

### ~~The one live thread: Lever C's directional pattern~~ — CLOSED 14 Aug 2026

3 of 6 markets cleared, and the split is not random — **all three one-way markets passed** (DVO-MNL 0.511 ·
MNL-DVO 0.496 · CEB-MNL 0.464), **all three round-trip markets failed** (0.363 · 0.435 · 0.432). But the
passing markets have the **lowest agreement with our taxonomy** (ARI 0.16–0.19 vs 0.47–0.53), so whatever
structure is there is not what our rules capture.

**RESOLVED — it was a floor effect.** The three passing markets are all **domestic point-to-point** routes.
Measuring the noise floor *within the domestic population* gives **0.346** (vs 0.205 pooled), because that
population is lower-dimensional and more homogeneous, so random data clusters more easily there. Domestic's
real-data margin over its own floor is **+0.123** against the pooled population's **+0.114** — statistically
identical. **No structure, no live thread, no lever open.**

⚠️ **And it invalidates this plan's own Lever C bar.** "Silhouette > 0.45 in a majority of markets" compares
sub-populations to a *global* threshold, which is meaningless — 0.45 means something different in every
population. **Every future silhouette threshold must be set against a noise floor measured on the same
population with the same feature set.** The same caution applies to the LCA sub-type silhouettes.

### What follows

1. **Close A, B, D, E and G.** Do not spend the 1.5 days on the Stage F change.
2. **Do not take the coarse taxonomy to PAL** — but keep the finding that **Undefined is a real population
   between the others** (0.606 / 0.609), not residue.
3. **Run the matched within-parent shuffled control** before quoting any sub-type silhouette.
4. **Lever F is now the main line of work** — if there are no clusters, soft membership and archetypes are
   the correct answer, not a fallback.
5. **B6 weak supervision** is the only remaining route to an accuracy number.

---

## What is already ruled out — do not re-run these

Four of the six possible explanations for "no clusters" are closed. Anyone proposing work in this area
should be shown this table first.

| Explanation | Status | Evidence |
|---|---|---|
| Wrong algorithm | ❌ **Closed** | 10 methods, 6 families, 8 axes (`model_stress_test.py`) |
| Methods too weak to detect | ❌ **Closed above 2%** | Planted-segment recovery (`detection_power.py`) |
| Mixed populations masking structure | ❌ **Closed** | Lever B: stripping sea crew + heavy tail made it *worse* (−0.022) |
| Assumption-driven artefact | ❌ **Closed** | H1 barcode, SVC, TDA-Mapper — no k, no centroid, no distributional assumption |
| **Wrong / missing features** | ❌ **Closed** | Levers A and D both null; D's control leaked |
| **Wrong grain, no time dimension** | ❌ **Closed** | Lever E: 1.32M-customer repeat cohort, +0.006 over noise |

**The 11 features currently in the space** (`src/model_zoo.py:70–72`):
`lead_days · value_tier · log_rev · n_coupons` (numeric) ·
`round_trip · foreign_issue · is_group · connecting · peak_month · corp_channel` (binary) ·
`dest_region` (nominal).

Everything below is about changing that list, the population it is computed over, or its representation.

---

## The discipline — read before running anything

This is the part that decides whether the results are worth having.

**1. Pre-register the decision rule.** Metric, threshold, written down before the run. Every lever below
has one. A lever without a threshold is not an experiment, it is a fishing trip.

**2. Anchors are the current numbers.** So results are comparable across levers:

| Metric | Current (booking grain, 11 features) |
|---|---|
| Best Gower silhouette | **0.381** |
| Median cross-method ARI | **0.41** |
| Detection floor (majority of panel) | **2% prevalence** |
| Best within-parent silhouette | **0.264** |

**3. Every positive must replicate out-of-time.** Machinery already exists — `validate_temporal.py`
splits into two adjacent 12-month issuance windows. Fit on the earlier, score the later. **A result that
does not survive the step is noise.** This is non-negotiable and it is cheap.

**4. Correct for the fact that we are running five experiments.** Five levers × three metrics is fifteen
chances for something to look structured. So the bar is *clearing the threshold by a margin*, plus §3
replication — not scraping past it once.

**5. Publish the nulls.** Every lever run gets a `§15 Learning Log` entry whether it worked or not. A null
that is recorded closes a question permanently; a null that is quietly dropped gets re-proposed in six
months.

**6. Add a second success criterion that does not require finding clusters.** For each lever, re-run
`detection_power.py` **in the new feature space**. If the detection floor improves — say 2% → 1% — the
representation is genuinely better at surfacing structure, *even if no natural cluster appears*. That is a
real result and it de-risks the whole programme: a lever can "fail" on clustering and still earn its place.

---

## Lever A — Stay length and upgrade into the feature set

**Why first:** cheapest, and the only candidate feature with **already-demonstrated** discriminative power
on evidence the model has never seen. Median stay by segment runs 3 · 4 · 5 · 10 · 13 · **33** nights, and
nothing in the waterfall put that ordering there (`docs/pipeline-study-guide.md` §5.1).

| # | Task | Deliverable |
|---|---|---|
| A1 | Emit `stay_nights` in `build_booking()` — `date_diff('day', min(departure_date), max(departure_date))`. Verified computable for **98.8%** of the 9.79M round-trip bookings | `src/features_real.py` |
| A2 | Carry `SoldOperatingCabinClass` through Stage C — it is currently used **only** in the `WHERE` filter and never selected — then emit `is_upgrade` (sold cabin ≠ operated cabin, upgrade direction only) | `src/clean_real.py` |
| A3 | Add `stay_nights` to `NUMERIC` and `is_upgrade` to `BINARY`, and to the explicit `SELECT` in `load_sample()` — both are needed, the SELECT is not `*` | `src/model_zoo.py` |
| A4 | Re-run the battery **scoped to round-trip bookings**: `load_sample(where="WHERE round_trip")` | `outputs/model_stress_test_stay/` |
| A5 | Re-run detection power in the new space | `outputs/detection_power_stay/` |
| A6 | Out-of-time replication of any positive | `outputs/.../temporal.md` |

> **The one design trap.** `stay_nights` is undefined for one-way bookings — 57.3% of the book — and
> "is it defined" is *exactly* the `round_trip` bit the rules already use. Imputing it would smuggle a rule
> input into the feature space and manufacture agreement. **So the run is scoped to round-trips only.**
> That is a legitimate, self-contained population (9.79M bookings), and it removes the missingness problem
> instead of modelling around it.

**Pre-registered decision rule.** Adopt `stay_nights` into the production feature set only if, on the
round-trip population, **both**: best Gower silhouette **> 0.45** (vs 0.381 pooled), **and** median
cross-method ARI **> 0.55** (vs 0.41). Secondary win condition: **detection floor improves to ≤1%** even if
the clustering criteria miss — that alone justifies keeping the feature for the confidence layer.

**Effort:** 1.5 days. **Owner:** whoever owns Stage F.

### ⛔ Feasibility probe result — 13 Aug 2026: does not clear the bar

Run **before** committing to the pipeline change, on a 20k reservoir sample of round-trip bookings
(4,000 rows for the O(n²) silhouette), GMM(full) and KMeans at k = 3–8, baseline spec vs
`+stay_nights`. Same `gower`/`gower_sil` implementation as the main harness, so the numbers are comparable.

| | baseline | +stay_nights |
|---|---:|---:|
| Best Gower silhouette | 0.323 | **0.319** |
| Best ARI vs proxy | 0.425 | **0.434** |
| Mean silhouette delta | — | **−0.007** |
| Mean ARI delta | — | **−0.022** |
| Silhouette of the **existing rule segments** | **0.009** | **0.009** |

**Adding stay length does not create separation. Both mean deltas are slightly negative, and the best
result (0.319) is nowhere near the pre-registered 0.45 — this is not a near-miss.**

**Why this is not a contradiction of §5.1.** Stay length *does* differ across segments descriptively —
median 3 · 4 · 5 · 10 · 13 · 33 nights. But **a difference in medians is not geometric separation.** The
distributions overlap heavily, and the segments with the most distinctive stay lengths (Pilgrimage at 33
nights) are far too small to move a global silhouette. A feature can carry real descriptive signal and
still fail to make clusters separable.

**Revised recommendation — do not adopt into the clustering feature set.** Keep the derivation, but
re-target it:

1. ✅ **Ship `stay_nights` as a BI / persona field** — it is genuinely informative for commercial readers
2. ✅ **Test it as a V1 validation anchor** — descriptive discrimination is exactly what construct validity
   needs, and it is a field no rule consumes
3. ⬜ **Secondary criterion untested** — the detection-floor test (does the floor improve below 2%?) was not
   run. Cheap to add if anyone wants to close the lever completely
4. ❌ **Do not spend the 1.5 days on the Stage F clustering change** on this evidence

**Bonus finding, and it is worth its own look.** The silhouette of the **rule segments themselves** is
**0.009** — essentially zero. So far as we can tell this had never been computed. It says the rules cut
*across* the density rather than along its seams, which is coherent with everything else: low geometric
separation alongside V1 AUCs of 0.608–0.965 means **the segments differ in ways that matter commercially
without being separable blobs.** Confirm on the full population before quoting it.

**One implementation gotcha found during the probe:** `to_codes()` in `src/model_zoo.py` hardcodes each
numeric by name, so a new feature added to `NUMERIC` is **silently dropped from the LCA input**. Task A3
above is therefore incomplete as written — any future feature needs a branch in `to_codes()` too.

---

## Lever B — Strip the atypical populations *(control, run alongside A)*

**Why:** sea crew (3.7% of coupons) and the 4,896 heavy-tail customers with 100+ coupons are
agency/contract buying, not travellers. They distort geometry far beyond their headcount. Non-revenue is
already excluded; these are not. **This is a control as much as a lever** — it quantifies how much of the
flatness is population heterogeneity rather than genuine continuity.

| # | Task | Deliverable |
|---|---|---|
| B1 | `load_sample(where="WHERE NOT sea_crew AND customer_id NOT IN (heavy_tail)")` — pure wiring, the parameter already exists | `src/model_stress_test.py` |
| B2 | Re-run the battery; report **against the unstripped baseline**, not in isolation | `outputs/model_stress_test_stripped/` |

**Pre-registered decision rule.** Silhouette must improve by **≥0.08 absolute** to count as a real effect
rather than sampling noise. If it does, **make the exclusion permanent in Stage F** and re-baseline every
other lever against the stripped population.

**Effort:** 0.5 day.

---

## Lever C — Market-conditioned clustering

**Why:** MNL–LAX and MNL–CEB currently sit in one feature space. Pooling heterogeneous markets can flatten
real within-market structure — long-haul diaspora routes may segment quite differently from domestic, and
averaging destroys both signals.

| # | Task | Deliverable |
|---|---|---|
| C1 | Pick the top 8 O&D markets by booking volume, plus one domestic and one long-haul control | list in the summary |
| C2 | Run the battery per market via `load_sample(where="WHERE trip_od = '...'")`, dropping now-constant columns with `Spec.drop()` | `outputs/model_stress_test_market/` |
| C3 | Report **within-market vs pooled** side by side | `summary.md` |

**Pre-registered decision rule.** Counts only if **a majority of the eight markets** shows silhouette
**> 0.45**. A single market clearing it is a cherry-pick — the same majority-rule discipline used for the
detection-power floors. If it holds, the recommendation is **market-conditioned sub-segmentation**, not a
new top-level taxonomy.

**Effort:** 1 day.

---

## Lever D — Learned representation

**Why:** the benchmark varied the *algorithm* extensively but the *representation* barely — one-hot plus
Gower throughout, with SVD and spectral as the only alternatives. A learned embedding lets the model
discover its own geometry over the categories instead of us imposing one.

| # | Task | Deliverable |
|---|---|---|
| D1 | Multiple Correspondence Analysis on the categorical block — the cheapest option, and standard for this data type | `src/embed.py` |
| D2 | Entity embeddings or a small denoising autoencoder over the mixed feature set | `src/embed.py` |
| D3 | Cluster in embedding space with the existing panel | `outputs/model_stress_test_embed/` |
| D4 | **Shuffled negative control** — same pipeline on column-permuted data | same summary |

> **D4 is mandatory, not optional.** A learned embedding can manufacture apparent clusters out of noise —
> that is its failure mode, and it is invisible without the control. **If the shuffled data also produces
> "clusters", the result is the method, not the data,** and the lever is void. This is the same logic as
> the `w=0` controls that retired H0 as a detector.

**Pre-registered decision rule.** Silhouette **> 0.5** on real data **and** **< 0.2** on shuffled. Both, or
the lever fails.

**Effort:** 2.5 days.

---

## Lever E — Longitudinal, on the repeat cohort

**This is `recommendations-plan.md` Phase 4 — already scoped, already viability-checked.** Do not re-plan
it; run it. Cohort: **1.32M customers with ≥3 bookings over >180 days = 8.3M bookings, 36% of volume.**

**One correction to that plan, and it matters.** Phase 4's kill criterion #1 is
`n_significant_H0 ≥ 3 AND H0 gap ratio > 1.5`. **`detection_power.py` subsequently retired the H0
significant-component count as a detector** — 100 runs on *unchanged* data returned 1 → 120 components. A
statistic with that range cannot gate anything.

**Replace criterion #1 with:**
> **H1 loop-noise ratio** (the part detection power found robust) **and** the new detection-floor criterion
> from §6 above — does the longitudinal space detect a planted cohort at a lower prevalence than 2%?

Criteria #2 (median cross-method ARI > 0.6) and #3 (best silhouette > 0.5) stand unchanged.

**Effort:** 3–4 days.

---

## Lever G — Coarser taxonomy: a 4-segment spine with cross-cutting flags

**Why:** every internal metric peaks well below the current taxonomy size — LCA agreement **0.336–0.337 at
k=4–5** (vs 0.228 at k=9), LCA split-half stability **0.855 at k=5** (vs 0.67 at k=9), and the **0.381
separation ceiling was achieved at k=3**. But that is *not* the argument, and it must not be presented as
one.

> **The trap to state before anyone else does.** Improving separation by asking for fewer groups is
> arithmetic, not discovery — cut a smooth density into three parts and the parts sit further apart than
> ten parts would. This is a third member of the family that already includes *stability without separation
> is not structure* and *a geometric cut through a continuum is perfectly learnable while being wholly
> arbitrary*. **Add: separation that improves only because you asked for fewer groups is not structure
> either.**

**The real argument is the boundary evidence, and it is strong:**

| Finding | Implication |
|---|---|
| OFW vs Balikbayan: **AUC 0.608**, split on a single bit, 6.8M bookings | `recommendations-plan.md` already states the live hypothesis: *one population — overseas Filipinos — segmented by trip type rather than two customer types* |
| **84.1% of Last-Minute** would otherwise be Budget/Adventure | A behaviour cutting *across* the taxonomy, not a peer of it |
| `Family` means *"ticketed as a group"*, not *"is a family"* | An attribute of the booking, not a customer type |
| Corporate is only **6.4% uncontested**, 25.6% matching 3+ rules | The most priority-order-dependent label we have |

**The proposed shape:**

| Core segment | Share | Built from |
|---|---:|---|
| **Domestic leisure** | ~39% | Budget/Adventure |
| **Overseas Filipino** | ~30% | OFW/Migrant + Balikbayan/VFR merged |
| **Premium & business** | ~6.5% | Corporate + Premium Bleisure |
| **Undefined** | ~9.6% | Unassigned |

…with **Last-Minute · Group travel · Pilgrimage · Award** demoted to **cross-cutting flags**.

> **Flags lose nothing — they free information.** Today a last-minute Corporate booking is labelled
> *Last-Minute* and the Corporate signal is discarded. As a flag you see both, so *last-minute Corporate*
> and *last-minute leisure* become separately targetable. Strictly more actionable, not less.

| # | Task | Deliverable |
|---|---|---|
| G1 | Emit `proxy_segment_coarse` **as a parallel column, never a replacement** — so BI can show both and the change is reversible | `src/features_real.py` |
| G2 | Emit the demoted bits as flags: `IsLastMinute`, `IsGroupTravel`, `IsPilgrimage` (`IsAward` already ships) | `src/features_real.py` · `src/export_powerbi.py` |
| G3 | Re-run **V1 construct validity** on the spine — do 4 segments separate better on independent anchors than 9 did? | `outputs/validate_construct_coarse/` |
| G4 | Re-run **V2 criterion validity** — does *signal retained* degrade when you merge? | `outputs/validate_criterion_coarse/` |
| G5 | Re-run **V4 out-of-time** on the coarse taxonomy | `outputs/validate_temporal_coarse/` |
| G6 | Cross-tab spine × flags to prove nothing is lost in the demotion | `summary.md` |

**Pre-registered decision rule.** Propose the coarse taxonomy to PAL only if **both**: the **weakest
pairwise AUC across the spine exceeds 0.75** (today's weakest pair is 0.608 — the merge should eliminate it,
not relocate it), **and** V2 **signal retained does not fall by more than 0.02 absolute** (0.324 → ≥0.304).
*A merge that improves geometry while losing predictive signal is a bad trade and must fail this gate.*

**This is a proposal, never a unilateral merge.** Consistent with the standing project policy: an
unsupported boundary becomes *a proposal to PAL with the evidence attached*. The framing to use:

> *"Four of your nine segments are either indistinguishable from each other on independent evidence, or are
> behaviours that cut across the others. A four-segment spine with cross-cutting flags fits the data better
> and loses no information. Is that a more useful shape for your commercial teams?"*

**Sequencing dependency — run after Lever A.** If stay length separates Corporate from Premium Bleisure
properly (median stay 4 vs 10 nights), that particular merge weakens and the spine may want to be five
segments rather than four. **Do not run G before A.**

**Effort:** 0.5 day — every bit is already computed by the waterfall; this is aggregation and re-validation,
not new modelling.

---

## Lever F — Continuum-native output *(run regardless)*

**Why unconditional:** these are useful whether or not any lever finds structure, and if all levers null
they become the answer rather than the consolation prize.

| # | Task | Deliverable |
|---|---|---|
| F1 | **Soft membership** — `recommendations-plan.md` Phase 2B: GMM posteriors → `segment_confidence`, `segment_alt`, `is_ambiguous` | `src/confidence.py` |
| F2 | **Archetypal Analysis** — find the extreme corners of the population and express each booking as a mixture. Purpose-built for data without cluster structure, and **absent from the ten-method field** | `src/archetypes.py` |
| F3 | Join both into the star schema and the SME sampling frame | `src/export_powerbi.py` |

**Why Archetypal Analysis specifically.** Every method we have tried asks *"where are the gaps?"* — the
wrong question for a continuum. AA asks **"who are the extremes, and how does everyone blend between
them?"** It yields output a commercial team can act on — *"this customer is 70% Balikbayan, 30% Premium
Bleisure"* — without asserting a boundary that does not exist.

**Pre-registered falsification (inherited from Phase 2B).** Once SME labels land, ambiguous rows must show
**measurably lower** SME-vs-proxy agreement than confident rows. If they do not, the confidence score is
decoration and gets cut.

**Effort:** 2–3 days.

---

## Pre-registered decisions, in one table

*Written before running. Honoured after.*

| Lever | Primary criterion | Secondary (counts on its own) | Anchor |
|---|---|---|---|
| **A** Stay length | silhouette > 0.45 **and** cross-method ARI > 0.55 | detection floor ≤ 1% | 0.381 / 0.41 / 2% |
| **B** Strip populations | silhouette improves ≥ 0.08 absolute | — | 0.381 |
| **C** Per-market | silhouette > 0.45 in **a majority of 8** markets | — | 0.381 |
| **D** Embedding | silhouette > 0.5 real **and** < 0.2 shuffled | — | 0.381 |
| **E** Longitudinal | H1 loop ratio **+** ARI > 0.6 **+** silhouette > 0.5 | detection floor ≤ 1% | 0.41 / 0.381 |
| **G** Coarser taxonomy | weakest spine AUC > 0.75 **and** signal retained ≥ 0.304 | — | 0.608 / 0.324 |
| **F** Continuum-native | ambiguous rows show lower SME agreement | — | — |

**Universal gate:** any positive must **replicate across the two 12-month issuance windows** before it
changes the pipeline.

**Stop rule:** if A, B, C and D all return null, **booking-grain discovery is closed.** Record it, stop
proposing feature variants, and let Levers E, F and G carry the remaining upside. **Note G is not a
discovery lever** — it does not look for new structure, it proposes a better-fitting shape for the
structure we already have, so it stays live regardless of how A–D land.

---

## Sequencing

```
Week 1   A  stay length + upgrade      ████████        ← start here
         B  strip populations          ███              (control, parallel)
         G  coarser taxonomy           ██               (after A — cheapest, 0.5d)
Week 2   C  per-market                 ██████
         E  longitudinal (Phase 4)     ████████████     (independent, parallel)
Week 3   D  learned representation     ██████████
         F  soft membership + AA       ██████████       (unconditional)
```

**Total ≈ 11–14 days**, of which **A + B + G is 2.5 days** and covers the highest-expected-value ground —
including the one lever that could change the shipped taxonomy.

Run A and B before committing to anything else. If stay length moves the needle, C and D get more
interesting; if it does not, the continuum claim hardens considerably and D becomes hard to justify.

---

## What we are explicitly not doing

- ❌ **Trying feature sets until something clusters.** Every lever has a threshold written first.
- ❌ **Reopening the algorithm question.** Ten methods across six families is enough; the open questions
  are features, population and grain.
- ❌ **Replacing the rule waterfall with a fitted model**, whatever any lever returns. Rare segments
  (Mabuhay 0.03%, Pilgrimage 0.19%) sit below every detection floor we have and only rules can deliver them.
- ❌ **Acting on a positive that has not replicated out-of-time.**
- ❌ **Shrinking the taxonomy because the metrics improve.** Lever G rests on boundary evidence — the
  0.608 pair and the 84% overlay — not on silhouette rising at low *k*, which is arithmetic.

---

## Risks

| Risk | Mitigation |
|---|---|
| **We find a cluster that is noise** | Pre-registered thresholds · out-of-time replication · shuffled control on Lever D |
| **Scope creep into a research project** | Hard stop rule after A–D · fixed effort per lever |
| **A positive result destabilises the deliverable before Friday's asks land** | None of this changes the shipped taxonomy without SME input. Levers inform the *next* version |
| **Effort competes with the SME critical path** | Phase 0 (unblock ground truth) outranks every lever here. If they compete, ground truth wins |

---

*Extends `docs/recommendations-plan.md`. Any lever run — positive or null — gets a `docs/knowledge-base.md`
§15 entry the same day.*
