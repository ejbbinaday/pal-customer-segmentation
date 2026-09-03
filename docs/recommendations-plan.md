# Implementation Plan — acting on the 2026-07-28 stress-test recommendations

**Version:** v1.0 — 28 July 2026
**Source:** `outputs/model_stress_test/summary.md` · `docs/methodology.md` v1.0 · `docs/knowledge-base.md` §15 (2026-07-28)

The ten-method benchmark closed one question (which algorithm) and opened three (ground truth, honest
confidence, production fragility). This plan sequences the work that follows from it.

---

## The sequencing principle

**Sequence by external lead time, not by internal effort.** Everything of consequence downstream depends
on **SME ground-truth labels**, which need someone else's calendar. The labelling instrument therefore ships
in Phase 0 — deliberately before the confidence model that would make the sample smarter — because a
slightly-worse sample sent out this week beats a perfect sample sent out in three.

Everything else is ours to control and can proceed in parallel.

```
Phase 0 ── labelling instrument out the door ──┐
   │                                            │  (SME turnaround: weeks, not ours)
   ├── Phase 1 ── protect + close (parallel)    │
   │                                            ▼
   └── Phase 2 ── confidence layer ──────► Phase 3 ── validate & decide
                                                 │
                       Phase 4 ── the one scoped discovery bet (gated, parallel)
```

---

## Phase 0 — Unblock ground truth (do first, this week)

The single highest-value action available. Every agreement number we have is circular: measured against the
rules' own output. SME labels are what convert validation from *"agrees with us"* to *"agrees with reality"*.

| # | Task | Deliverable |
|---|---|---|
| 0.1 | **Build the sampling instrument** | `src/build_sme_sample.py` → `outputs/sme_sample/sme_sample.xlsx` |
| 0.2 | **Write the labelling guide** | `docs/sme-labelling-guide.md` |
| 0.3 | **Build the scorer before the labels land** | `src/validate_sme.py` |

**0.1 — sampling design (this is where the thought goes).** A uniform random 1,000 draws ≈2 Pilgrimage rows
and ≈0 Mabuhay Loyalist — useless for per-segment recall. The sample must be **stratified with floors**:

- **Block A — per-segment floor:** min 60 rows/segment where available (rare segments taken in full:
  Pilgrimage 43.6k, Mabuhay 6.5k are pools, not constraints). ~600 rows.
- **Block B — natural-prevalence block:** ~300 rows drawn at true prevalence, so unbiased population
  estimates are recoverable via inverse-probability weighting. Block A alone cannot support prevalence claims.
- **Block C — inter-rater overlap:** ~100 rows labelled by **all** SMEs.
- Total ≈ **1,000 rows**, carrying a `stratum` and `sample_weight` column so the scorer can weight correctly.

**Block C is not optional.** If two SMEs disagree with each other, their disagreement rate is a hard ceiling
on any accuracy we can ever claim. Measure Cohen's κ before drawing conclusions about the model. A κ below
~0.6 changes the project's target, not just its score.

Instrument must give the SME what they need to judge and nothing else: route, dates, lead time, cabin,
fare tier, channel, party/group flag, issue country, revenue band — plus `true_segment` (dropdown of the 10 +
`Unsure`), `confidence` (High/Med/Low) and `notes`. **`Unsure` must be a first-class option**; forcing a guess
manufactures noise and we would have no way to detect it.

**0.3 — the scorer ships before the data.** `src/validate_sme.py` reads `data/labels/sme_sample.csv` and emits
per-segment recall, the **asymmetric cost matrix** (methodology Stage 7, Corporate ×10 / OFW ×5), the
proxy-vs-SME confusion matrix, weighted prevalence estimates, and inter-rater κ. Built now, it means the day
labels arrive there is zero lag between data and answer.

**Effort:** 1–2 days ours. SME time ≈ 8–16 hours; recommend splitting across 2–3 SMEs.

---

## Phase 1 — Close the algorithm question; protect production (parallel, cheap)

### 1A. Close it in writing, with a stated re-open criterion

Three diagnostics (07-23, 07-27, 07-28), ten methods, six families, and a label-free topological test all
agree. Further clustering search has negative expected value.

| # | Task | Deliverable |
|---|---|---|
| 1.1 | Add an explicit **decision record** to `docs/methodology.md`: algorithm selection **CLOSED**, evidence chain, and the conditions that would re-open it | methodology §Decision Record |
| 1.2 | **Prune the harness** — drop SVC and TDA-Mapper from the default run (SVC burned 590s to finish last); keep them behind `--full-field`. Keep persistence: cheap and the highest-signal test we have | `src/model_stress_test.py` |
| 1.3 | Add **`--report-only`** — rebuild `summary.md` from the saved CSVs without refitting | `src/model_stress_test.py` |

**Re-open criteria (write these down, or "closed" is dogma rather than a decision):** new feature *families*
(ancillary, loyalty tier, length-of-stay); the customer-grain result from Phase 4; or SME labels showing the
rules are systematically wrong rather than merely imprecise.

### 1B. Feature contract + data-quality gate

The one genuinely new red flag: leave-one-feature-out ARI minima of **0.15–0.49**. Losing `dest_region` or
`value_tier` silently reassigns much of the customer base with nothing visibly breaking.

| # | Task | Deliverable |
|---|---|---|
| 1.4 | **Feature contract** — per-feature dtype, null-rate ceiling, cardinality range, value range. **Criticality annotated from measured dropout ARI**, not guesswork — we already have the number per feature | `src/feature_contract.py` |
| 1.5 | **Gate script** — validate `pal_features_booking.parquet` against the contract, non-zero exit on breach; run after Stage F | `src/check_features.py` |
| 1.6 | Wire the gate into the documented run order | `README.md` |

**Effort:** ~1.5 days total for 1A + 1B.

---

## Phase 2 — Confidence layer (the right way to use the GMM result)

GMM won the benchmark, but the benchmark scored *top-level* segmentation while LCA's actual job is
*sub-segmentation*. So this phase does **not** swap the layer on the strength of a mismatched test.

### 2A. Stage-matched head-to-head first

| # | Task | Deliverable |
|---|---|---|
| 2.1 | Add `--scope sub --parents "..."` to run the full battery **inside** each big parent segment. `model_zoo.load_sample(where=...)` and `Spec.drop()` already support this — it is wiring, not new modelling | `src/model_stress_test.py` |

**Pre-registered decision rule** — swap LCA → GMM only if, *inside* the parent segments, GMM wins on
**separation AND stability**, and the Balikbayan/VFR provisional flag (split-half 0.495) improves. Winning on
agreement alone is not sufficient: agreement is the circular axis.

### 2B. Soft membership as a confidence score

Not "better segments" — **honest ambiguity**. A booking that is 60% Balikbayan / 40% OFW is the truthful
output for a continuum, and a hard label is a lie about it.

| # | Task | Deliverable |
|---|---|---|
| 2.2 | Fit GMM on booking features; emit `segment_confidence` (max posterior), `segment_alt` (runner-up), `is_ambiguous` | `src/confidence.py` |
| 2.3 | Join the three columns into the Power BI star schema | `src/export_powerbi.py` |
| 2.4 | Re-draw the SME sample weighted toward ambiguous rows (**active learning** — highest information per label) | `src/build_sme_sample.py` |

Threshold from the posterior distribution (e.g. bottom decile), never a round number pulled from air.

**Pre-registered falsification test:** once SME labels land, ambiguous rows must show **measurably lower
SME-vs-proxy agreement** than confident rows. If they don't, the confidence score is decoration and gets cut.

This buys three things: an honest low-confidence bucket instead of forced assignment; targeted SME labelling;
and a drift-monitoring signal.

**Effort:** 2–3 days.

---

## Phase 3 — Validate, and retire the metrics that prove nothing

Runs when labels arrive.

| # | Task | Deliverable |
|---|---|---|
| 3.1 | Run `validate_sme.py`; publish per-segment recall + cost matrix as the **primary** validation | `outputs/validate_sme/summary.md` |
| 3.2 | Add a **"metrics that are not evidence"** note to methodology, promoted from the stress-test report | `docs/methodology.md` |
| 3.3 | Add the do-not-claim line to the talk track | `docs/mentor-presentation-guide.md` |
| 3.4 | Lead the presentation with the continuum finding **as a result** | `docs/mentor-presentation-guide.md` |
| 3.5 | Two figures: persistence diagram + cross-method ARI heatmap; regenerate the status report | `src/report_figures.py`, `docs/status-report.pdf` |

**3.2 is the load-bearing one.** Nearly every method scored **0.85–0.99** held-out accuracy at predicting its
own labels — `SVD+KMeans` reached **0.981 accuracy at 0.117 separation**. Any claim of the form *"we predict
segments with 98% accuracy"* measures nothing, because the labels are a function of the features. Ban it from
the deliverable; replace with per-segment recall against SME labels + the asymmetric cost matrix.

**Effort:** ~1.5 days (0.5 of it blocked on labels).

---

## Phase 4 — The one scoped discovery bet (gated, parallel)

Everything to date is **booking-grain and cross-sectional**. Genuine customer segmentation usually finds its
structure in *behaviour over time*. The continuum finding constrains booking attributes and does **not** rule
out longitudinal structure.

**Viability pre-check — already run (2026-07-28):**

| bookings/customer | customers | % of customers | avg span |
|---|---|---|---|
| 1 | 9.92M | **73.9%** | 0 d |
| 2 | 1.98M | 14.7% | 201 d |
| 3–4 | 0.94M | 7.0% | 382 d |
| 5–9 | 0.42M | 3.1% | 539 d |
| 10+ | 0.17M | 1.3% | 691 d |

Two conclusions. **(1)** `customer_id` genuinely persists across time — a PNR-level key would show a 0-day
span everywhere. **(2)** The experiment is **not** "segment everyone longitudinally", it is **"segment the
repeat cohort"**: ≥3 bookings and >180-day span = **1.32M customers / 8.3M bookings (36% of volume)**. For the
73.9% single-booking majority, customer-grain segmentation collapses to booking-grain — which is what we
already did, and the continuum finding stands there. Framed correctly this is where airline CRM value lives,
not a consolation prize.

| # | Task | Deliverable |
|---|---|---|
| 4.1 | Confirm `customer_id` semantics against `DataDictionary.v1.xlsx` — the span evidence is strong but not proof | KB §15 note |
| 4.2 | Longitudinal features on the repeat cohort: recency, frequency, inter-trip interval + variance, route entropy, cabin-mix drift, seasonality profile, domestic/intl mix, purpose-mix evolution | `src/features_longitudinal.py` |
| 4.3 | Run the **same** harness — `--scope customer`. Reusing the zoo is the payoff for having built it | `outputs/model_stress_test_customer/` |

**Pre-registered kill criteria — written before running, honoured after.** Continue only if **all three** hold:

1. `n_significant_H0` ≥ 3 **and** H0 gap ratio > 1.5 (vs 1 / 1.195 at booking grain)
2. median cross-method ARI > 0.6 (vs 0.41)
3. best Gower silhouette > 0.5 (vs 0.381)

Miss any one → **stop, record the null result in §15, do not revisit.** A null here is a real deliverable: it
would close customer-grain discovery the way Phase 1 closes booking-grain.

**Effort:** 3–4 days.

---

## Pre-registered decisions, in one table

Committing to these *now* is what separates analysis from motivated reasoning.

| Decision | Rule | Set before seeing |
|---|---|---|
| Swap LCA → GMM? | Only if GMM wins separation **and** stability *inside parent segments* | 2.1 results |
| Keep the confidence score? | Only if ambiguous rows show lower SME agreement than confident rows | SME labels |
| Trust the SME labels? | Only if inter-rater κ ≥ ~0.6 on the Block C overlap | SME labels |
| Continue customer-grain discovery? | Only if all three kill criteria clear | 4.3 results |
| Re-open the algorithm question? | New feature families, Phase 4 success, or SME labels showing systematic rule error | — |

---

## Plan B — validation without SME labels

**Added 28 Jul 2026** because internal SME labelling may not be available. This is not a downgraded Plan A;
it answers a different and largely more answerable question.

> **Plan A asks:** *are our labels correct?* — needs labels, needs someone else's calendar.
> **Plan B asks:** *is the segmentation behaviourally real, temporally stable, and would we know if it
> weren't?* — answerable **entirely from data already on disk.**

### First, the circularity audit (done — it changes the design)

The proxy waterfall (`src/features_real.py`) consumes: `is_award`, `corp_channel`, `any_business`,
`lead_days`, `pilgrimage`, `sea_crew`, `foreign_issue`, `is_international`, `max_tier`, `round_trip`,
`any_premium`, `is_group`, `is_domestic`.

**Anything on that list is circular and cannot validate anything.** That rules out three fields that look
like obvious independent markers and are not: **`sea_crew`** (it *is* the OFW rule), **`is_award`** (it *is*
the Mabuhay rule), **`pilgrimage`** (it *is* the Pilgrimage rule). Checking this first prevented three
invalid tests.

**Genuinely independent anchors that survive:** `refund_any` · `flown_any` · `age`/`age_known` ·
`issue_country` *identity* (only the foreign/domestic bit is used) · `channel` *identity* (only
`corp_channel`/`sea_crew` are used) · `min_tier` · `n_directions` · route identity · **`dep_month` — the
rules use no month at all.**

### Feasibility probe (run 2026-07-28, unconditioned marginals)

| Test | Result | Verdict |
|---|---|---|
| **Outcomes** the rules never saw | refund rate spans **0.00% (Family) → 0.45% (Balikbayan)**; flown spans 91.7% → 99.9% (Last-Minute) | ✅ signal exists |
| **Demographics** | median age Premium Bleisure **50**, Balikbayan 42, Corporate 41, OFW 37, Family 36 | ⚠️ signal, but see MNAR below |
| **Seasonality** | **Balikbayan/VFR peaks in December** — the Philippine Christmas homecoming — from rules that use no month | ✅ genuine external validation |
| | Pilgrimage is the most seasonal segment (peak/trough ratio **5.39**) | ✅ |
| **Country mix, OFW vs Balikbayan** | both dominated by US/SG/JP/HK; **no Gulf concentration in OFW** | ❌ **does not corroborate the split** |

Two cautions on reading that table. **(a) Age is missing-not-at-random:** `age_known` runs from **0.8%**
(Budget/Adventure) to **89.2%** (Balikbayan), so those medians describe wildly different subpopulations —
Budget/Adventure's "39" rests on 0.8% of 9M rows. Age is usable only with missingness modelled explicitly.
**(b) Most segments peak in May**, which is a base-rate effect; Balikbayan's December peak is notable
*precisely because it deviates* from that base rate. Normalise against the overall monthly distribution.

### The finding this already surfaced

**`OFW/Migrant` vs `Balikbayan/VFR` — 6.8M bookings, 30% of the base — is split on a single bit:
`round_trip`** (one-way → OFW, round-trip → Balikbayan). Independent evidence is **split** on whether that
bit separates two populations: *country mix says no* (both are the same US/SG/JP/HK diaspora), while
*seasonality says partly yes* (Balikbayan peaks December, OFW peaks May). The live hypothesis is that these
are **one population — overseas Filipinos — segmented by trip type rather than two customer types.**
Commercially that matters: it would merge two of your four largest segments. Resolving it is Plan B's
highest-value single question, and it needs no SME.

### Tier 1 — zero external input (start now)

| # | Task | Deliverable | Status |
|---|---|---|---|
| B1 | **Criterion validity** — do segments predict `refund_any`, `flown_any`, reissue, and next-trip behaviour? Report **segment-only vs full-feature vs null** model, i.e. *what fraction of achievable signal survives the compression* | `src/validate_criterion.py` | ✅ **done 2026-07-28** |
| B2 | **Construct validity** on the surviving anchors, with an explicit missingness model for age | `src/validate_construct.py` | ✅ **done 2026-07-28** |
| B3 | **Seasonality vs the known calendar** — pre-register predictions (Balikbayan→Dec, Pilgrimage→Hajj/Umrah window, OFW→deployment rhythm), then test, base-rate normalised | part of B2 | ✅ **done 2026-07-28** |
| B4 | **Out-of-time stability** — two adjacent 12-month *issuance* windows (the extract is departure-filtered, so calendar-year splits are invalid); do sizes, profiles and revenue mix hold? | `src/validate_temporal.py` | ✅ **done 2026-07-29** |
| B5 | **Detection power by injection** — plant segments of known prevalence and separation into the real population, find the detection floor | `src/detection_power.py` | ✅ **done 2026-07-29** |
| B6 | **Weak supervision** — 3+ *independent* labelling functions per segment from disjoint feature families, combined with a Dawid–Skene label model → accuracy estimate with no gold labels. Also: characterise the **2.19M Unassigned** — one coherent missing segment, or a grab bag? | `src/weak_labels.py` |

**B1's framing matters.** A segmentation is a *compression*, so it will never beat the raw features. The
honest question is how much actionable signal it retains while staying interpretable — report the ratio, not
a win/loss.

**B5 was the highest-value remaining Tier-1 item and is now done (2026-07-29).** It converted *"we found no
clusters"* into *"no clusters exist above 2% prevalence with distinctness ≈0.34, and here is the proof we
could have found them"* — and, just as usefully, established that **below ~1% prevalence the pipeline detects
nothing at any distinctness**, which is a bound the deliverable must state rather than a gap it can leave
implicit. It also retired the H0 significant-component count as a detector (1 → 120 across draws of unchanged
data). Full results: `outputs/detection_power/summary.md`; KB §15 (2026-07-29).

**B4 is done (2026-07-29; figures refreshed from the 18 Aug re-run).** Shares hold across a 12-month step
(TVD **1.71 pp**, full population). On model transfer the methods **disagree** — GMM(full) ratio **1.24**,
LCA **0.89** — so the claim holds only on the best-transferring method; the 29 Jul ratio of 1.02 and the
LCA 1.13 are superseded, and 1.13 is **withdrawn** (43% sample). Two caveats it
surfaced: **revenue mix is less stable than headcount** (TVD **3.36 pp**; Balikbayan/VFR 29.35%→26.64% of
revenue on a flat share), and the extract is **departure-filtered**, which invalidates calendar-year windows
for any future temporal work. **B6 is now the highest-value remaining Tier-1 item** — weak supervision would
put an accuracy estimate on the labels with no gold data, and it is the last Tier-1 axis untouched.

### B1–B3 results (run 2026-07-28)

**The harness validated itself before anything was interpreted.** Negative controls (random half-splits)
landed at **0.494–0.506**; positive controls at **0.770–0.945**. A real difference on this data reads
0.77–0.95.

| Finding | Evidence |
|---|---|
| **OFW/Balikbayan is the weakest boundary of all 45** | AUC **0.608** strict / 0.714 adaptive |
| …but it is **real, not spurious** | Survives matched within-country in *every* market tested: **0.622–0.721** (CN/US/CA/JP/QA/NZ/AE/HK/KR/SG) |
| …and seasonality carries most of it | December index **1.174 Balikbayan vs 0.826 OFW**; August reverses (0.923 vs 1.077); other months ≈1.0 |
| **`Unassigned` is a coherent missing population, not a residue** | Distinct from 8 of 9 segments (**0.821–0.986**); only weak vs Corporate (0.682) — corroborates taxonomy gap #4 |
| **The segmentation is a lossy re-encoding for key outcomes** | `flown_any` signal retained **0.324**, incremental **+0.002**; `rebook_180d` **0.555**, **+0.002** |
| 2nd weakest boundary | Last-Minute vs Budget/Adventure **0.645** |

**Revised recommendation on the motivating question:** the earlier "one population" hypothesis is **not**
supported — *keep the two segments separate*, but treat the boundary as **soft**, and consider reporting an
**"Overseas Filipino" super-segment with trip type as a sub-dimension**. Do not merge on this evidence.

**Next actions this created:** promote `Unassigned` to a named segment proposal (it behaves like one); and
stop presenting the segmentation as predictive — it adds ~nothing over the raw features, so its value is
communication and targeting, which is a different and defensible claim.

### Tier 2 — public data (no PAL, no SME)

| # | Task |
|---|---|
| B7 | Benchmark segment shares and country mix against **PSA OFW deployment statistics**, **DOT visitor arrivals**, **BSP remittance-corridor data**. A source wholly independent of PAL — and a direct test of the OFW/Balikbayan question above |

### Tier 3 — the cheapest human asks, ascending

| # | Task | Ask size |
|---|---|---|
| B8 | **Profile-level face validity** — one reviewer, ten one-page segment profiles, *"which of these don't look right?"* | **~1 hour, one person** |
| B9 | **Analyst labelling** against a written rubric, inter-rater κ measured; reported honestly as *analyst-validated, not SME-validated* | ~1 day, internal |
| B10 | **LLM-as-annotator** from **business-language** segment definitions — never the rule thresholds, or it merely re-derives the rules and is circular — validated against B9's subset and reported as weak supervision with measured agreement | ~hours |

**B8 should be attempted even if Plan A is dead.** It is roughly two orders of magnitude cheaper than 1,000
row labels and captures a large share of the value: an SME who cannot commit a day can usually spare an hour
to say *"that isn't what Corporate looks like."* Escalating the full labelling ask to a one-hour profile
review is the single most likely way to get **some** expert signal into this project.

### What Plan B cannot do

It **cannot confirm the segment names.** It can establish that segments differ behaviourally, hold up over
time, survive resampling, and that our detection was sensitive enough to trust the null. It cannot tell you
that the group labelled *Corporate* is what PAL's commercial team means by Corporate. That stays a business
judgement, and **every deliverable must say so** — "behaviourally validated; segment names not externally
confirmed" — rather than let Plan B's strength imply an endorsement it cannot give.

### Revised sequencing

Plan B's Tier 1 becomes the **new Phase 0**, since it has no external dependency. Phase 0's original
labelling instrument (`build_sme_sample.py`, `validate_sme.py`) is **built but parked**: it costs 1–2 days,
and if any labelling window ever opens — a new SME, a client workshop, a PAL analyst with spare capacity —
being ready to use it immediately is worth far more than the build cost. Do not delete it.

---

## Explicitly not doing

Named so they don't creep back in:

- **More clustering algorithms.** Ten across six families, plus a label-free topological test. The shape isn't there; adding methods to look for it is a category error.
- **Deep clustering / autoencoders / SOMs.** Same reason, higher cost, worse interpretability.
- **More features hoping structure appears.** Distinct from Phase 4, which changes the *grain and the question*, not the search intensity.
- **Chasing the separation ceiling.** 0.381 is the honest bound. Quote it; don't try to beat it with metric shopping.

---

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| SME time never materialises | Validation stays circular indefinitely | Phase 0 first; small ask (1k rows); scorer pre-built so turnaround is instant |
| SMEs disagree with each other | Caps achievable accuracy | Block C overlap + κ, measured before any model claim |
| SME labels contradict the rules | Re-opens the closed decision | That is the re-open criterion working as designed, not a failure |
| Phase 4 returns null | ~4 days spent | Kill criteria pre-registered; the null is itself publishable |
| Feature gate too strict | Pipeline blocked on benign drift | Severity from *measured* dropout ARI; warn vs fail tiers |

---

*Effort figures are engineering estimates and exclude SME calendar time, which dominates the critical path.*
