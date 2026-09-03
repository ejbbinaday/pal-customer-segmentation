# Defence Study Guide

**For Martin, Josh and Jadd · defence deck: `assets/final-defense/CPT3_DefenseDeck_V3.pptx` · 18 August 2026**

This is the study companion for the final defence — the principles, the techniques, the numbers,
and the questions, end to end. It is written to be drilled from, not skimmed. The deep technical
walkthrough lives in `docs/pipeline-study-guide.md`; the binding what-to-say list lives in
`docs/defense-brief-2026-08-18.md`. When this guide and an older document disagree on a number,
**this guide and the brief win** — see §9 for the list of stale figures still sitting in older docs.

How to use it: read §1–§4 until you can recite §1 cold. Memorize the two tables in §5. Walk §6
with the deck open. Then drill §7 out loud with someone playing the panel. §8 splits the work
three ways.

---

## 1. The spine — the story in 60 seconds

Every answer you give should hang off this. If a question knocks you sideways, walk back to the
nearest sentence of this and continue from there.

> PAL sells seats to passengers it cannot see — anonymous bookings, no loyalty join. We were asked
> to find the customer segments hiding in 38 million coupon rows. We looked properly: ten
> clustering methods across six algorithm families, and they all hit the same ceiling, because
> PAL's customers are not clusters — they're a continuum. We proved that finding could not be our
> own blindness by planting artificial segments in the real data and recovering them. So we flipped
> the design: business rules draw the segment boundaries, and machine learning got three jobs —
> refine the big segments, test every boundary on evidence the rules never touched, and watch for
> drift. The result is eleven named, costed segments on 22.9 million bookings, a dashboard that
> reconciles to the row, and — the part we're proudest of — the machinery that says exactly how far
> each label can be trusted.

The emotional register to hold all day: calm, specific, unembarrassed. We are not defending a
model that worked on the first try. We are defending a team that measured its way out of three
wrong designs and wrote every wrong turn down.

---

## 2. Principles — the ideas under everything

Seven ideas. Every technique in §3 exists to serve one of these. If you understand these, you can
reconstruct any answer under pressure.

### 2.1 The anonymous lens

Sabre gives PAL the booking, not the person: no name, no loyalty tier, no CRM. This is a hard
constraint, not a choice we made. It decides what a segment can legally be built from (booking
behaviour: lead time, route, fare tier, channel, trip shape) and what it can never see (a
Mabuhay member on a paid ticket, a digital nomad, ancillary spend). Half our stated limitations
are this constraint wearing different clothes.

### 2.2 The booking is the modelling row

One purchase decision has one purpose. A customer, over years, has many. And 74% of customers
appear exactly once **inside our ~27-month issuance window** — so a "customer profile" for most of
the base is just their single booking restated. (That 74% is a window statistic, not a lifetime one:
the earliest full cohort returns 40.5% of the time. The grain argument does not depend on the rate —
even at 40% repeat, most of the base books once and purpose still belongs to the purchase.) We model at booking grain (22.9M rows) and roll up to customers (13.4M) afterwards.
The grain changes twice in the pipeline (coupon → booking → customer) and each change is asserted,
because grain bugs are the silent killers of aggregate numbers.

### 2.3 The continuum, and what it forced

There are no natural clusters in this data. That is a measured result, not an opinion: ten
methods, six families, separation ceiling 0.381 Gower silhouette where 0.50 is the conventional
"real structure" bar; BIC with no elbow anywhere; density methods collapsing outright. When the
data is a smooth cloud, any clustering you force onto it produces boundaries that look
sophisticated and mean nothing — and worse, different methods produce *different* meaningless
boundaries. The honest design on a continuum is to draw the lines where the business needs them
and then test whether the lines sit in defensible places.

The analogy that lands: a rainbow. The spectrum is continuous, yet "orange" is still a useful
word. Naming orange is a business decision; proving the spectrum runs red-to-violet — and that
your instruments could have seen a stripe if one existed — is the analysis.

### 2.4 ML's three jobs (it never labels)

The rule waterfall assigns every label. Machine learning: **(1) refines** — LCA finds sub-types
inside the five biggest segments; **(2) tests** — the four validation stages ask whether the
boundaries are real, and can send a rule back for rework; **(3) monitors** — PSI watches the
input distributions for drift. If a panelist says "so you didn't really use ML", the answer is
that we used ten methods to establish the most important fact in the project, and then gave ML
the jobs a continuum actually supports.

### 2.5 Circularity — a rulebook cannot grade itself

Every label is a function of the fields the rules read. Score the labels against those fields and
you get an A+ for free — the model grading its own homework. So validation runs on **anchors**:
fields the rules never consumed. A code contract (`validation_anchors.py`) enforces this and
raises an error, not a warning. It also catches the sneaky leaks: `dest_region == 'Domestic'` *is*
the domestic rule bit in finer clothing, so it's disqualified from any comparison that turns on
that bit. This is also why **no accuracy number ships anywhere** — every accuracy figure
computable today is circular. That's a design decision, and we say it before anyone asks.

### 2.6 Falsifiability — every claim carries its kill condition

The pattern across the whole project: before reading a result, establish what noise looks like.
Negative controls (random splits must score 0.50), positive controls (calibrate the scale),
pre-registered thresholds (set from control runs, not round numbers), planted-segment tests (prove
the instrument can see before believing what it doesn't see). One instrument failed its own
control — the persistent-homology component count returned anywhere from 2 to 131 on identical
data — so we retired it and went back to qualify the earlier report that had used it.

### 2.7 Cost asymmetry — errors are not equal

Mislabeling an Ultra Wealthy Leisure passenger as Budget costs more than the reverse. The cost
research (`docs/segment-cost-research.md`) puts annual value at risk per customer at **$495 to
$9,784** depending on segment, from published airline revenue-management sources plus our own
measured economics. The recommended penalty weights replace a ladder that was flatly inverted
against measured revenue in two places. PAL hasn't signed off — they asked to see a scored run
first — so present the weights as a proposal.

---

## 3. Techniques — plain words, one analogy, what it showed

Format per entry: what it is → why we used it → what it found → the follow-up question it invites.

### 3.1 The labelling layer

**Rule waterfall (the model).** An ordered list of if-then rules; the first rule that matches a
booking claims it, like a triage nurse working down a checklist. Priority order matters enormously
— a booking that is both corporate-channel and short-lead goes to whichever rule stands higher.
*Found:* 11 segments + 2.47% Unassigned on 22.9M bookings. *Invites:* "who wrote the rules?" —
seeded by us, then rebuilt around 39 rules from PAL's own revenue managers, with every 'cannot-be'
rule asserted in code on every build.

**Penalty weights.** A multiplier per segment expressing how expensive a wrong label is there.
Used in the baseline pipeline's feature scaling and proposed (v2, dollar-grounded) for scoring.
*Invites:* "who set them?" — measured from revenue where possible, three documented overrides
where the measurement is blind, and awaiting PAL's decision.

### 3.2 The clustering zoo (what we tested and why it lost)

You don't need to derive any of these. You need one sentence of mechanism and one of verdict.

- **HDBSCAN** — finds crowds separated by empty space, and refuses to label stragglers. Our
  prototype's engine. On the real data there is no empty space, so it collapses. Not the
  algorithm's fault; there's nothing for it to find.
- **KMeans** — carves the space into k cells around k centres; every point must join one.
  Produces boundaries even where none exist — which is exactly the danger on a continuum.
- **k-prototypes / k-modes** — KMeans's cousins for mixed numeric + categorical data. Tested
  head-to-head; no improvement. Verdict: no.
- **GMM (Gaussian mixture)** — soft overlapping ovals with membership probabilities instead of
  hard walls. Won the ten-method benchmark (composite 0.849 vs LCA's 0.763) and transfers best
  across time. It is our best *measuring instrument*, not the labeller.
- **LCA (latent class analysis)** — a mixture model for categorical data: assumes hidden types,
  asks which mix best explains the answers, like inferring diners' tastes from order patterns.
  Its job is sub-segmentation inside the five biggest segments.
- **Spectral, SVC, TDA-Mapper** — three more families (graph-based, boundary-based,
  topology-based) included so nobody could say we only tried centroid methods. Same ceiling.

### 3.3 The measuring instruments

- **Gower distance** — a distance that works when features are mixed (numbers + categories);
  each feature contributes a 0–1 dissimilarity. The common ruler for everything above.
- **Silhouette (on Gower)** — how much closer a point is to its own cluster than the next one,
  −1 to +1. Our ceiling: **0.381**, below the 0.50 bar for real structure. Analogy: how sure each
  guest is about which table they belong to at a wedding.
- **BIC** — model fit with a fine for complexity. If real clusters exist, BIC drops sharply at
  the true k (an "elbow"). Across k=3–9: no elbow anywhere.
- **ARI (adjusted Rand index)** — agreement between two labelings, corrected for luck; 0 is
  chance, 1 identical. Used for stability (split-half, bootstrap) and model transfer across years.
- **AUC** — the probability a classifier ranks a random positive above a random negative.
  0.50 is a coin flip, 1.0 is perfect. The workhorse of V1: "can a classifier tell segment A from
  segment B using only fields the rules never saw?"
- **F1** — the harmonic balance of precision and recall; used in detection power to score whether
  a planted segment was recovered.
- **PSI (population stability index)** — how much a distribution moved between two windows;
  the standard credit-scoring drift alarm. The monitor's tripwire.
- **TVD (total variation distance)** — the largest share-of-population disagreement between two
  mixes; how we report segment-mix drift (1.71 pp on shares, year over year).
- **Persistent homology (H0/H1)** — topology: how many blobs and loops survive as you zoom out.
  The H0 blob-count **failed its control (2–131 on identical data) and is retired**. The loop-noise
  ratio and barcode shape remain; the integer count does not. Know this because it's in an
  earlier report.

### 3.4 The four validation stages (the heart of the defence)

- **V1 · Construct — "are the segments really different?"** For all 55 segment pairs, train a
  classifier on *anchor* fields only, held out, with negative controls read first. Result:
  **44 clearly distinct, 11 weak, 0 indistinguishable; median AUC 0.861** on the adaptive
  measure. The strict measure (only the two unconditionally clean anchors) gives 0.637 — thin
  **by construction**, because after the leak audit only two fields are unconditionally admissible.
  Always say which column you're quoting.
- **V2 · Criterion — "do they predict anything they weren't built from?"** Ladder: null →
  segment-only → features → features+segment, on outcomes no rule consumes. The label alone
  scores ~0.60 vs a 0.50 coin flip — real signal — but adds ~nothing on top of the raw features
  (+0.0005 on flown, +0.0024 on rebook). Expected: a rule label *is* a compression of the
  features, and a compression can't beat its source. Its value is communication and targeting.
  `refund_any` came back unstable — never quote it.
- **V3 · Detection power — "could we have missed one?"** Plant synthetic segments of known size
  and distinctness in the real data, refit the panel, measure recovery against thresholds set from
  control runs. Majority-rule floors: found at 2% prevalence (distinctness ≈0.494), 5% (≈0.219),
  10% (≈0.13); **never found at 0.5–1%, at any distinctness**. So the continuum claim carries its
  own bound: blind below ~1% (~229k bookings).
- **V4 · Temporal — "does it hold a year later?"** Two adjacent 12-month issuance windows
  (calendar years are a trap here — the extract filters on *departure* date, so naive windows
  fake a lead-time collapse). Shares hold (TVD 1.71 pp); revenue mix is the weaker leg (3.36 pp,
  Balikbayan 29.35% → 26.64% of revenue on flat headcount). Model transfer: **the two methods
  disagree** — GMM transfers above its own ceiling (ratio 1.24), LCA below (0.89) — so say "on
  the best-transferring method a yearly refit buys little", nothing stronger.

### 3.5 The SME programme

39 rules returned by PAL's revenue managers; 57 transcribed (15 hard, 42 soft) with provenance
and live firing counts; all 24 follow-up questions answered. The six *certain* hard rules are
asserted at build time, reading PAL's CSV directly. Stage P scores the 21 live soft tendencies
against our labels without changing any: silent on 43.6% of the book, agreeing 70.5% where they
speak — and their largest disagreement (Last-Minute → Leisure, on 1,025,351 bookings)
independently corroborated our decision to retire Last-Minute as a segment. A tendency is not a
rule; disagreement is the finding.

### 3.6 The engineering

- **DuckDB + Parquet** — four gzipped CSVs become a typed, partitioned columnar store in ~90s;
  queries drop from minutes to sub-second. No cluster, no licence; a laptop rebuilds everything.
- **Star schema** — one fact table ringed by dimensions (date, segment). 38,116,259 coupons in,
  38,116,259 out, asserted. The scorecard table (1,835 rows) means a KPI tile never scans 20M rows.
- **No stored percentages** — a share is only valid in the filter context that computed it, so
  shares are DAX measures, never columns.
- **Determinism honesty** — the build moves by ±1 booking between runs: 1,830 bookings have tied
  sort keys. Cause found, fix drafted, disclosed. If asked "is it reproducible?", this is the
  strongest possible answer: yes, to within one booking, and we can name the booking.

---

## 4. Findings you must be able to defend without slides

1. **Unassigned fell 74%** (9.58% → 2.47%). 75% of the old bucket was Filipinos buying
   international economy tickets — now Outbound International Leisure.
2. **23.4% of bookings genuinely reclassified** (5,358,355). The 62.7% figure is textual label
   difference, dominated by the Budget/Adventure → Leisure rename.
3. **The flag beats the segment it replaced.** As a segment, Last-Minute caught 2,945,686
   bookings (only what fell through eight higher branches). As a flag: 4,411,666 — 50% more
   short-lead volume visible without moving a threshold.
4. **Revenue concentrates where headcount doesn't.** Balikbayan/VFR: 12.5% of bookings, 28.4% of
   revenue, $615/booking. Leisure: 50.6% of bookings, 15.0% of revenue, $80. Ultra Wealthy:
   0.7% of bookings at $1,968/booking.
5. **The Gulf one-month clock.** 19.11% of Gulf round trips at 28–32 nights vs 8.48% at 12–16;
   every other corridor's ratio ≤0.60. RM reads it as employer-mandated leave — but a one-month
   maximum-stay fare rule would draw the identical picture, so until fare basis codes arrive we
   present the pattern, not the cause. Two parts of the SME's claim failed testing: no 45-day
   spike, and pooling HK/Taipei with the Gulf drops discrimination below chance (0.375 vs 0.676).
6. **The weakest boundary did not improve.** OFW vs Balikbayan, 6.8M bookings, historically split
   on one bit. A/B with method and anchors held fixed: v1 0.730, v2 0.728 — neutral. The only
   change touching the pair moves 1.4% of the branch.

---

## 5. Numbers — memorize and never-say

### Memorize (quiz each other until automatic)

| Number | What it is |
|---|---|
| 38.1M / 22.9M / 13.4M | coupons → bookings → customers |
| 26% | customers who ever book twice |
| 0.381 | Gower silhouette ceiling, all ten methods (bar: 0.50) |
| 11 + Unassigned | segments shipped; Unassigned at **2.47%** (was 9.58%) |
| 23.4% | bookings genuinely reclassified |
| 44 / 55, median AUC **0.861** | V1 clearly-distinct pairs (**adaptive**; strict median is 0.637) |
| 11 segments + `Unassigned` = **12 labels** | V1 tests the 11 → 55 pairs; V4 tests all 12 |
| Corporate **6 of 10** · Leisure **5 of 10** | weak V1 boundaries — the 11 weak pairs concentrate on two segments |
| 50.6% | Leisure's share of the book — the missing-middle-rung question |
| 5 parents × 4 sub-types = **20 cells** | LCA refinement; Balikbayan spans **$311 → $995** on booking horizon |
| ≈0.494 @ 2% · ≈0.219 @ 5% · ≈0.13 @ 10% | V3 majority detection floors; blind below ~1% (~229k) |
| 1.71 pp / 3.36 pp | V4 share TVD / revenue-mix TVD (18 Aug re-run; 1.93/3.21 are the 29 Jul figures) |
| 0.730 → 0.728 | weakest boundary A/B — neutral |
| 19.11% vs 8.48% | Gulf 28–32-night share vs 12–16 |
| 39 / 57 / 24 / 6 | SME rules returned / transcribed / questions answered / hard rules asserted |
| 43.6% / 70.5% | book where SME priors are silent / agreement where they speak |
| $495–$9,784 | annual value at risk per customer |
| 19.26% | bookings carrying the short-lead flag |
| 38,116,259 | dashboard rows in = out |
| 1,835 / 20.6M | scorecard rows / fact_flight rows |

### Never say (each has ended up in a document at some point — that's why this table exists)

| Don't say | Because | Say instead |
|---|---|---|
| "62.7% reclassified" | mostly the Leisure rename | 23.4% |
| "0.608 → 0.72, the boundary improved" | different tests; like-for-like it *fell* | A/B 0.730 → 0.728, neutral |
| "Corporate is the most short-lead at 35.6%" | one rule branch only admits short-lead | 23.3%, on the branch with no lead-time condition |
| "MICE / Ultra Wealthy never book late" | 0% short-lead **by rule construction** | their rules require ≥45 / ≥30 days' lead |
| "Gulf pattern is caused by employer leave" | fare-rule confound open | the pattern is real and corridor-specific; cause pending fare basis codes |
| "Transfer ratio 1.13, refits unnecessary" | **withdrawn** — computed on a silent 43% sample | GMM 1.24, LCA 0.89 — the methods disagree |
| "Detectable down to 0.114 distinctness" | luckiest of 12 method×archetype cells | majority floors: ≈0.494 @ 2% |
| "One significant H0 component" | instrument retired (2–131 on unchanged data) | continuum holds as the centre of a noisy distribution |
| any accuracy % | circular until SME labels exist | "no honest accuracy number exists yet, by design" |
| `refund_any` results | unstable | the two stable outcomes only |
| "BIC chose four sub-types" | `K_RANGE = range(2,5)` — four is the **top of the search**, and BIC wanted the max in all five parents | "four is the granularity we chose; BIC preferred the maximum every time — the continuum, one level down" |
| "the drift is in the tiny segments" / "the three smallest" | v1 wording; `Premium Bleisure` is 1.49%, the **7th-largest of twelve** | "8 of 12 labels stable carrying 98.1%; the four that drift are 1.9% of the book" |
| "13.3% book short-lead, median 25 days" | **coupon**-grain figures on booking-grain slides | median **18 days**, **19.26%** — the 4,411,666 the flag covers |
| "74% of customers never return" | right-censored: it measures our ~27-month window | "74% book once **in-window**; 26.5% return within 12 months; the 2024 Q2 cohort reaches 40.5%" |
| "38.4% of bookings are issued abroad" | that is the **coupon** share | **34.6%** of bookings (38.4% of coupons) |

---

## 6. The deck, slide by slide — claim · proof · trap

> **Numbers below match `CPT3_DefenseDeck_V3.pptx` (26 slides).** Renumbered twice on 19 August: once
> after `add_eda_intro.py` inserted the grain slide at position 5, and again when the **sub-segments
> slide was added at position 19**. If anyone is working from a printout, check that their row 7 reads
> "network & grain" and their row 19 reads "sub-segments" — otherwise they have a stale deck.

| # | Slide | The claim | The proof behind it | The trap to not fall into |
|---|---|---|---|---|
| 1 | Title | — | — | keep intros under a minute |
| 2 | Agenda | — | — | — |
| 3 | Problem (Martin) | anonymous data hides opposite travellers | Sabre lens, no CRM/loyalty | don't promise personalization — it's targeting, not identity |
| 4 | TOR (Martin) | every promised item delivered or redesigned openly | delivery table + risk register | "delivered differently" ≠ "not delivered" — own the phrasing |
| 5 | Grain: coupon → booking → customer (Josh) | a booking is one purchase decision | the funnel: 38,116,259 → 22,911,450 → 13,435,365 | the grain was tested, not assumed — 1.66 coupons/booking, 42.7% round-trip |
| 6 | EDA: timing & value (Josh) | short-lead, economy-heavy, and the data has edges | real lead-time + farebrand-tier distributions (22.9M bookings) | the 120-day pile-up is a data cap, not behaviour |
| 7 | EDA: network & grain (Josh) | domestic-heavy network; most of the base books once *in-window* | real region-mix chart; 26% repeat *within our window*, 26.5% within 12 months | say "in-window", never "never return" — repeat rate is right-censored (2024 Q2 cohort: 40.5%) |
| 8 | First clustering attempt (Josh) | everything overlaps — visually | the PCA figure: LCA's own classes vs rule segments, same cloud (PC 1+2 = 57.7% of variance; rule silhouette **0.091**) | **the figure carries v1 labels** (Budget/Adventure, Family, Last-Minute — retired 18 Aug); the sample is *uniform*, not stratified; `k=9` is the top of the search range, not a fitted optimum |
| 9 | Continuum (Josh) | no natural clusters, and we'd know if there were | ten-method silhouette sweep (k=3–12) + detection-floor chart | quote majority floors, never 0.114 |
| 10 | Architecture (Josh) | rules label, ML checks | pipeline stages; build-time assertions | ML "checks", never "approves" |
| 11 | Iteration arc (Josh) | fourth design, not first | v0→v3, and what each wrong turn cost | the slide *does* quote the prototype's 0.435/0.167 — say "on the 30k sample, which is why no number from it reaches a deliverable", don't claim we quote it nowhere. "Three retired" = Family, Digital Nomad, Last-Minute (Last-Minute became the flag; Budget/Adventure was **renamed**, not retired): 10 + 4 − 3 = 11 |
| 12 | Iteration ledger (Josh) | eleven dated iterations, verdicts recorded | the 11 May → 18 Aug trail, one script per row | point at 3 rows (11 May, 23 Jul, 28 Jul); never read the table |
| 13 | Honest validation (Josh) | the harness can't fool us | circularity contract, controls, retired instrument | retired ≠ broken analysis — the robust parts stand |
| 14 | Divider (Jadd) | — | — | demo fallback = recording |
| 15 | Dashboard (Jadd) | reconciles to the row | 38,116,259 in=out; traps designed out | admit the one manual .pbix step |
| 16 | Taxonomy (both) | 11 segments + honest Unassigned | the table, v2 numbers, USD confirmed | Family/Digital Nomad were *retired for cause*, not forgotten |
| 17 | Share vs revenue chart (both) | half the bookings earn a seventh of the money | paired-bar chart, rebuilt from all 22.9M bookings each run | let the picture sit before talking |
| 18 | Behaviour charts (both) | premium cabins ≠ premium segments; short-lead cuts across segments | value-band mix + short-lead-rate charts | the ~95%-Premium bars are partly rule echo — say so; Corporate's hatch is rule-induced |
| 19 | Sub-segments — ML's job 1 (Josh) | volume and value invert *inside* a segment too | one worked example as a Sankey: Balikbayan/VFR → 4 sub-types, thinnest flow (16.9%) earns the most ($995), fattest (38.8%) the least ($311); other four parents on one line | **never say "BIC chose four"** — `K_RANGE = range(2,5)`, so four is the top of the search and BIC wanted the maximum in all five parents: the continuum, one level down |
| 20 | What changed (Josh) | real change is 23.4% | 74% Unassigned drop; flag-vs-segment chart 4.41M vs 2.95M | the never-say numbers live here — pre-empt them |
| 21 | Validation — **Plan B** (Josh) | four label-free checks; 44/55 boundaries hold | V1–V4 scorecard + the 55-pair AUC strip chart + an AUC explainer strip | V = validation stage, and Plan B needs no answer key — say that first; the strip names the measure in print, so don't read it aloud · **see §6.2** |
| 22 | Gulf + cost (both) | best domain finding + first dollar spread | real stay-length distribution chart; $495–$9,784 | pattern, not cause; weights are a proposal |
| 23 | Limitations (Josh) | owned before asked | five owned limits + four in-flight fixes (V4 multi-seed and incremental-prediction added 19 Aug) | these are *our* findings about ourselves — keep that tone · **see §6.1** |
| 24 | Recommendations (Martin) | four strategies, ordered | manuscript ch. 5 | data investments before algorithm work — take the stance |
| 25 | Conclusion (Josh) | the honesty machinery is the product | three beats | end on beat 3, no recap |
| 26 | Thanks | — | — | backups ready |

---

## 6.1 Slide 23 in full — limitations

*Every other slide states a finding; this one states what the findings cannot do. It is the slide most
likely to be mis-delivered, because the temptation is to apologise. Don't. The material is strong.*

**On the slide.** Two columns.

*Owned, not hidden (5):*

| Limit | The number behind it |
|---|---|
| No loyalty field in the extract | Mabuhay sits at **0.03%** (6,453 bookings) and cannot be measured, only awaited |
| Blind below ~1% prevalence | a real segment of **~229k** bookings could exist and V3 would not find it |
| Build moves by ±1 booking between runs | **1,830** tied sort keys — cause found, fix drafted, disclosed |
| No ancillary revenue in the data | per-booking value understates bag-heavy segments (OFW especially) |
| Labels add little incremental prediction | the label alone scores **0.598** (`flown_any`) and **0.604** (`rebook_180d`) against a 0.50 coin flip — but added *on top of* the 11 raw features it buys **+0.0005 to +0.0024** AUC. *A compression cannot beat its source.* Quote the two **stable** outcomes only; `refund_any` is flagged unstable (347 events) and reads −0.107 |

*In flight (4):* fare basis codes (requested — they settle the Gulf confound) · penalty weights awaiting
PAL sign-off ("show us a scored run first") · an SME-labelled sample for a real accuracy number ·
no refit-cadence claim until V4 transfer runs across several seeds.

**Say:**
> "Five limits, and we found all five ourselves. The one worth dwelling on is the last: our labels add
> almost nothing to a model that already has the raw features — because the labels are *made* of those
> features. A compression can't beat its source. What PAL gains isn't prediction, it's a shared vocabulary
> that a revenue manager, a marketer and a dashboard all resolve the same way. And the dashboard ships no
> accuracy figure today, deliberately — any number we could print would be the model grading its own
> homework."

**Watch for — the tone trap.** Delivered flatly this is a list of failures; delivered correctly it is a
list of measurements. The distinction is that **each limit has a number and a source**, which is only
possible because someone went looking. Say "we measured" rather than "unfortunately".

**Watch for — the handover-pack claim.** The slide closes with *"Everything on this slide is also written
down in the handover pack."* No artefact by that name exists in the repo (searched 19 Aug 2026) — it may
live outside git. **Confirm where it is before the defence**, because this is the one sentence on the slide
a panelist can ask to see.

### If pressed

**"Your segments add almost nothing predictive. Why do they matter?"** *(the single most likely question in
the whole defence — it is now owned on the slide, so answer it as a confirmation, not a concession)*
> Prediction was never the job; targeting and communication were. The label alone carries real signal
> (0.60 vs a coin flip), and the reason it adds little *on top of* the features is that it is made of them.
> V2 measured exactly that and we put it on the limitations slide ourselves.

**"Which limitations are *not* on this slide?"** *(a fair question — answer it, don't dodge)*
> Two, both in the maintainer docs rather than the deck: **revenue mix is the weaker leg** (3.36 pp vs
> 1.71 pp on share year over year — Balikbayan/VFR held its headcount while falling 29.35% → 26.64% of
> revenue, so a segment holding its size is not evidence its value held), and **every clustering method is
> fragile to feature dropout** (leave-one-out ARI minima 0.15–0.49), which is a production risk given the
> extract's known field gaps. Both are in `pipeline-study-guide.md` §7.4.

**"±1 booking — so the pipeline isn't reproducible?"**
> It is reproducible to within one booking in 22.9 million, and we can name the booking: 1,830 rows have
> tied sort keys. Cause identified, fix drafted. That is a stronger answer than "yes" would be.

**"What happens if one of your controls fails?"** *(follows naturally from slide 13)*
> The circularity guard **raises** — a `CircularityError`, not a warning. The negative control is reported
> first, at §0, with the line "if it is not, the harness leaks and every other number below is void."
> Hardening that from a reporting convention into an abort is on the list.

**"Why no accuracy number on the dashboard?"**
> Because every label came from our own rules, so any accuracy we computed would be measured against the
> thing being tested. The SME gold sample is what unlocks a real figure, and contested boundaries —
> Corporate first — are the sampling frame.

### Where each limit's evidence lives

| Limit | Source |
|---|---|
| Loyalty / Mabuhay 0.03% | `outputs/eda_real/confirmations.md` A5 · `outputs/segment_charts/segment_summary.csv` |
| Blind below ~1% | `outputs/detection_power/summary.md` §5 · `floor.csv` |
| ±1 booking, 1,830 tied keys | `outputs/features_real/` · brief §"Known limitations" |
| No ancillary revenue | `docs/real-data-plan.md` schema notes |
| Incremental prediction ≈0.002 | `outputs/validate_criterion/summary.md` |
| Revenue mix weaker leg | `outputs/validate_temporal/summary.md` §2 |
| Feature-dropout fragility | `outputs/model_stress_test/` |
| V4 transfer disputed | `outputs/validate_temporal/summary.md` §5 (GMM 1.24 · LCA 0.89) |

---

## 6.2 Slide 21 in full — validation (Plan B)

*Slide 13 explains why the harness can be trusted. **This slide is what it produced.** It is the only slide
carrying four independent results at once, which makes it the easiest one to quote loosely — and the
numbers here are the ones our own older documents got wrong most often.*

**What the slide *is*, in one sentence.** `methodology.md` defines three routes to validation: **circular**
(agreement against `proxy_segment`, which the rules produced — unavoidable today and worthless as proof),
**Plan A** (~1,000 SME-labelled bookings, an actual answer key, still outstanding), and **Plan B** (needs no
labels at all). **This slide is Plan B.** Its subject is not "our segments are good" — it is *"we wrote the
labels ourselves and have no answer key yet, so here are four checks that do not need one."*

**And "V" is a validation stage.** V1 and V2 are lifted from classical measurement theory — **construct** and
**criterion** validity are the standard validity types in psychometrics; V3 is statistical **power**; V4 is
**reliability across time**. If asked why these four: the ladder is a recognised framework adapted to our
problem, not four checks we invented. Title and kicker say so on the slide as of 20 Aug — *"Four independent
checks, and 44 of 55 boundaries hold"* over *"V1-V4, our four validation stages - construct, criterion,
detection power, out-of-time. None may read a field the rules consumed."*

**On the slide.** A four-stage scorecard, the 55-pair chart, a full-width **explainer strip** (added
20 Aug), and one caption owning the weak boundary.

| Stage | The question | The answer | What it actually means |
|---|---|---|---|
| **V1 · Construct** | Are they distinguishable? | **44 of 55** pairs clearly distinct · **0** indistinguishable · median AUC **0.861** | The segments differ on evidence the rules never consumed. This is the headline result of the project |
| **V2 · Criterion** | Do they predict anything? | label alone **0.598 / 0.604** vs a 0.50 coin flip; **+0.0005 to +0.0024** on top of the raw features | Real signal, no *incremental* signal — a compression cannot beat its source. The value is targeting, not prediction |
| **V3 · Detection power** | Could we have missed one? | planted segments found from **≥2%** prevalence; **never** below ~1% | The null is falsifiable, with a stated blind spot of ~229k bookings |
| **V4 · Stability** | Does it hold a year later? | share TVD **1.71 pp**; **8 of 12** labels stable, carrying **98.1%** of bookings | Not a one-period artefact. Revenue mix is the weaker leg (3.36 pp) |

**Why V1 counts 11 and V4 counts 12** — asked on 20 Aug, and a panellist can ask it too. **11 segments + `Unassigned` = 12 labels.** V1 tests the **11**, so 11×10÷2 = **55 pairs**; `Unassigned` is excluded because it has **no positive definition** — it is "nothing else claimed this", so there is no claim to validate. V4 tests all **12**, because drift in the residual bucket *is* meaningful: if the leftovers change composition, the rules are losing grip on something. (It came back *small*, i.e. stable.) Same taxonomy, different denominators, both deliberate.

**Say:**
> "We can't grade the rulebook against itself, so we went looking for corroboration it never had access to.
> Do the groups differ on independent evidence? Do they predict outcomes they never saw? Would we have
> spotted a group we missed? Do they survive a year? **Four different ways of being wrong, one test each** —
> and 44 of the 55 boundaries hold on fields no rule ever read."

### Watch for — four traps, all of them ours

**1 · Name the V1 measure — the strip now says it for you.** The explainer states on the slide that these
are the per-pair adaptive anchors, so this trap is discharged in print; you still need it for questions.
**0.861 is the *adaptive* median**, not the strict one. Strict uses only the two
unconditionally-admissible anchors (`dep_month`, `n_bookings`); adaptive adds the rest per pair, wherever the
rule bit they encode is not what separates those two groups. The bands (**<0.60 not distinguishable · 0.60–0.75
weakly · >0.75 clearly distinct**) are calibrated for the **adaptive** column. Quoting a strict number against
an adaptive band understates your own result.

**2 · Strict is thin on purpose, and that is a finding.** Before the 30 July `age_known` correction the strict
positive control read 0.770–0.945; almost all of that was `age_known` standing in for `is_international`, a
rule field. With the age anchors correctly withheld, the strict positive control is **0.641**. So **a low
strict AUC now means "we withheld the evidence that would have separated them", not "these segments are the
same."** If someone reads the strict column as the honest one and the adaptive as the flattering one, that is
backwards — strict is the one with almost no power left.

**3 · The lowest bar is not the boundary you rehearsed.** The chart's weakest pair is **Ultra Wealthy Leisure
vs Leisure at 0.611**. OFW–Balikbayan sits at **0.713** in this matrix — seventh weakest. If a panellist
points at the lowest bar: *a brand-new segment carved off the top of a segment holding half the book is
exactly where the softest edge belongs, and it is on our list.*

**4 · "The three smallest segments" was a v1 leftover — corrected on the slide 20 Aug.** It now reads
"8 of 12 labels stable, carrying 98.1% of bookings; the four that drift are 1.9% of the book between them."
Know why: under v2 **four** labels drift, not three — `Mabuhay Loyalist` (is_group, 0.03% of bookings), `Pilgrimage` (value_tier, 0.2%), `MICE` (peak_month,
0.13%) and `Premium Bleisure` (log_rev, **1.49%** — the **seventh-largest of twelve**, bigger than the other
three drifters combined, so do not call the drifters "the tiny ones" either). The safe form is **"8 of 12
labels carrying 98.1% of bookings are stable; everything moderate-or-larger is 1.9% of the book"**, and the
drifters are *unresolved*, not established behaviour — a few hundred bookings move a mean at that size.

### One boundary, four numbers — this is why the trap exists

`OFW/Migrant` vs `Balikbayan/VFR`, 6.8M bookings, historically split on a **single bit** (`round_trip`):

| measure | result | when to quote it |
|---|---|---|
| strict (2 anchors) | **0.548** — not distinguishable | only alongside its own control |
| adaptive (full admissible set) | **0.713** | the 55-pair matrix reading |
| isolated clean-pair test | **0.72** | the round-trip-only population |
| **A/B, v1 labels vs v2, method and population fixed** | **0.730 → 0.728** | *the* answer on whether the redesign helped |

⚠️ **Never say "0.608 → 0.72".** The 0.608 in our older documents is the **strict matrix cell**; 0.72 is the
**isolated clean-pair test**. Different tests. Like for like, strict went **0.608 → 0.548** — it got *worse*.
The honest line is the A/B: **neutral**, because the only change touching this pair moves **40k bookings,
1.4% of the branch**, and the Gulf stay-length discriminator that motivated the work is still a **soft prior**
that changes no label.

### The finding that is not on the slide but should be in your head

The 11 weak pairs are not scattered — they concentrate on two segments:

| Segment | Weak boundaries (of its 10) |
|---|---|
| **Corporate** | **6** |
| **Leisure** | **5** |
| every other segment | at most 1–2 |

Two readings, both of which strengthen the defence:

- **Leisure's softness *is* the missing middle rung, measured.** A segment holding 50.6% of the book contains
  a bit of everything, so it is hard to separate from anything. That turns "half the book in one segment is
  not a targeting unit" from an assertion about targeting into five of your eleven soft boundaries.
- **Corporate is the least well-defined segment on two independent diagnostics** — most contested by the rules
  internally (only **6.4%** of its bookings uncontested, 12 Aug) and most weak boundaries on evidence the
  rules never saw. Internal ambiguity and external indistinguishability agreeing, on the one segment carrying
  the **×10** penalty. **That is why Corporate is first in line for the SME gold sample.**

Two methods agreeing is the strongest kind of result. Say it.

### If pressed

**"Isn't 0.861 just your best number?"**
> It is the **median** of 55 pairs, not the maximum, and none of the 55 falls in the not-distinguishable band.
> The negative control — each segment split randomly in half — lands at 0.494–0.513, so the scale is honest.

**"Why is your strict column so much weaker than your adaptive one?"**
> Because we caught ourselves. `age_known` was in the unconditional tier until we measured it: 0.86% of
> domestic bookings have a known age against 87.62% of international, so it was a near-copy of a rule field.
> Demoting it cost most of the strict column's power. Trap 2 above is the consequence.

**"Your weakest boundary didn't improve."**
> Correct, and we put it on the slide. A/B with method, anchors and population held fixed: 0.730 to 0.728 —
> neutral. The only change touching that pair moves 1.4% of the branch, so neutral is the expected result,
> not a disappointment. What would move it is the Gulf discriminator, and that is still a soft prior.

**"Your segments add almost nothing predictive."** → see §6.1, limit 5. Answer it as a confirmation.

**"How do you know you didn't just miss a segment?"** → V3. Quote the **majority-of-panel** floors (≈0.494 at
2%, ≈0.219 at 5%, ≈0.13 at 10%), never the single-method minimum of 0.114, and volunteer the ~229k blind spot.

**"Will this hold next year?"**
> One twelve-month step: sizes hold at 1.71 pp, revenue mix moves more at 3.36 pp. On model transfer **the two
> methods disagree** — GMM 1.24, LCA 0.89 — so we make no refit-cadence claim until that stage runs across
> several seeds. The composition result does not depend on it.

**"Isn't validating rules with the data that built them circular?"** → slide 13. The contract **raises**, and
this slide is what survived it.

### Where each number lives

| Number | Source |
|---|---|
| 44 of 55 · median 0.861 · 11 weak · 0 indistinguishable | `outputs/validate_construct/pairs.csv` |
| bands, negative control 0.494–0.513, strict-vs-adaptive | `outputs/validate_construct/summary.md` §0, §2 |
| Corporate 6/10 · Leisure 5/10 weak boundaries | `pairs.csv`, grouped by segment |
| Corporate 6.4% uncontested | `outputs/rule_confidence/summary.md` §1 *(v1 labels — not re-run since v2)* |
| V2 0.598 / 0.604 · +0.0005 / +0.0024 | `outputs/validate_criterion/summary.md` §1 |
| V3 floors and the ~229k blind spot | `outputs/detection_power/summary.md` §5, `floor.csv` |
| V4 1.71 pp · 3.36 pp · 8 of 12 · four drifters | `outputs/validate_temporal/summary.md` §2, §4 |
| V4 transfer GMM 1.24 · LCA 0.89 | `outputs/validate_temporal/summary.md` §5 |
| the boundary's four numbers and the A/B | `docs/defense-brief-2026-08-18.md` §V1 |

---

## 7. The question bank — drill these out loud

Answer style: first sentence answers the question. Then one piece of evidence. Then stop.
The worst defence answer is a good answer that keeps going.

### 7.1 The five most likely (one owner each — rehearse as a team)

**"Your segments add almost nothing predictive. Why do they matter?"** *(Josh)*
Because prediction was never the job — targeting and communication were. The label alone carries
real signal (0.60 vs a coin flip), and the reason it adds little on top of the features is that
it's *made* of the features: a compression can't beat its source. What PAL gains is a shared
vocabulary that a revenue manager, a marketer, and a dashboard all resolve the same way.

**"How do you know clusters don't exist, rather than that you missed them?"** *(Josh)*
We planted artificial segments in the real data and measured whether our own panel recovers them.
At 2% of bookings or larger — a majority of methods finds them. So when the same panel finds
nothing in the unplanted data, that's evidence about the data. Below ~1% we're blind, and we quote
that bound alongside the finding.

**"Isn't validating rules with the data that built them circular?"** *(Josh)*
Completely — which is why we never do it. A code contract lists every field the rules consumed and
raises an error if validation touches one. It also catches disguised leaks: a field that equals a
rule input in finer clothing is disqualified for exactly the comparisons where it leaks. And it's
why no accuracy number ships: every one computable today would be circular.

**"What does a misclassification actually cost?"** *(Martin)*
Between $495 and $9,784 per customer per year depending on the segment, built from five cost
components each sourced from published airline revenue-management research plus our own measured
economics in confirmed USD. The previous ladder was penalty × $4,000 and inverted against measured
revenue in two places. PAL asked to see a scored run before agreeing weights — so it's a proposal.

**"Who maintains this after you leave?"** *(Jadd)*
PAL BI, and the system is built for that: deterministic rules (a SQL job, no model server),
a build that fails loudly if the scorecard stops tying to the fact table, hard SME rules asserted
from PAL's own CSV, a drift monitor as the tripwire, and governance columns — Trust and DataCaveat
— that travel with every persona card.

### 7.2 Methodology pressure

- **"So you didn't really use machine learning."** Ten methods, six families, eight scoring axes
  — and the finding was that no natural clusters exist. Acting on that *is* the result. ML now
  does the three jobs a continuum supports: refine, test, monitor.
- **"Why eleven segments? Why not seven, or twenty?"** The count comes from the business, not the
  data — on a continuum it must. It started at ten from the requirements, and moved to eleven
  through PAL's own rules and answers (four added, three retired for cause). The validation then
  checks the *chosen* lines: 44 of 55 pairs clearly distinct.
- **"Median AUC 0.861 — cherry-picked?"** It's the adaptive measure: all admissible anchors, with
  per-pair withholding wherever an anchor would leak a rule bit. The strict measure — only the two
  unconditionally clean anchors — gives 0.637, thin by construction since a two-column matrix
  can't separate much. We report both and always name which one we're quoting.
- **"Why not embeddings / deep learning?"** It's on the roadmap as a gated experiment
  (`docs/continuum-levers-plan.md`), with a pre-registered decision rule and a stop condition.
  But every test we've run says the ceiling is in the features, not the method — the ten-method
  benchmark spans radically different inductive biases and they all land in the same place. Data
  investments come first.
- **"What would change your mind?"** Expert labels disagreeing with a rule; two segments proving
  indistinguishable on independent evidence; a boundary unstable across time. And the policy is
  fixed: an unsupported split becomes a proposal to PAL with the evidence attached, never a
  unilateral merge.
- **"Your own earlier report said the transfer ratio was 1.13."** Withdrawn, and we found the bug
  ourselves: the sampler applied its window filter below the reservoir sample, so per-window
  samples were silently 43% of intended. On the corrected run the two methods disagree — GMM 1.24,
  LCA 0.89 — so the refit-cadence claim is weaker than it was, and we say so.
- **"Why did the weakest boundary not improve?"** Because almost nothing touched it: the only
  change moves 1.4% of that branch, and the Gulf stay-length discriminator is still a soft prior
  that changes no label. The A/B held everything fixed except the labels and found no difference.
  Fixing this boundary needs new data (fare basis, loyalty), not new rules.

### 7.3 Commercial and revenue management

- **"Can I set fares with this tomorrow?"** Not pricing, not yet — labels are unverified against
  ground truth until the SME sample lands. Today it's solid for reporting, targeting, and
  prioritisation.
- **"Premium Bleisure is 1.5% of bookings — why care?"** $1,188 per booking against Leisure's
  $80 — 15× the unit value, 6.6% of revenue from 1.5% of volume. Headcount is the wrong lens,
  and the persona card carries that warning as a column so it can't be cropped off a slide.
- **"Which segment worries you most?"** Corporate: high value, most contested label, and one of
  its two rule branches is partly circular on lead time (hence 23.3%, not 35.6%). It's first in
  line for the SME labelled sample.
- **"Is Balikbayan stable?"** In size, yes; in value, watch it — 29.35% → 26.64% of revenue on a
  flat headcount share across the 12-month step. A segment holding its size is not evidence its
  value held.

### 7.4 Marketing and loyalty

- **"Mabuhay at 0.03% is obviously wrong."** It is, and we agree. No loyalty-tier field exists in
  the extract; the only visible signal is an actual award redemption. The segment is real — our
  ability to see it is not. That's the single highest-value data request on the table.
- **"Why did you delete Family?"** It had no positive definition — 100% of it was "a group booking
  nothing else claimed". A rule that means "leftovers" isn't a segment. Party size isn't
  observable either: the pax field counts sectors, not people.
- **"Where did Last-Minute go?"** It became a flag, and got bigger: 4.41M bookings vs the 2.95M
  the segment caught, including 864k OFW and 315k corporate short-lead bookings that were
  invisible before. PAL's own soft rules corroborated the retirement — their largest disagreement
  with our old labels was exactly Last-Minute → Leisure, on over a million bookings.

### 7.5 Finance, IT, data

- **"Can I trust the revenue numbers?"** USD, confirmed by PAL on 18 August — the first time we've
  had that in writing. Refunds, awards and non-rev travel ship as flags so totals reconcile;
  commercial tiles must filter them.
- **"Why does every trend fall off a cliff at the end?"** It doesn't — recent travel months are
  forward book still filling. The dashboard defaults trend visuals to complete travel months;
  that default must survive future edits.
- **"Is the pipeline reproducible?"** To within ±1 booking of 22.9 million — 1,830 tied sort keys,
  cause identified, fix drafted. Every stage is one script writing a checkable report; scoring
  needs no inference, so the labeller cannot drift. Drift enters only through the input data,
  which is what the monitor watches.
- **"Production risk?"** A silently missing input column degrades the labels without failing
  loudly. The mitigation is a feature contract validated at ingestion — specified, and it should
  gate any production deployment.
- **"Privacy?"** No names, contacts, or payment data anywhere; the customer key arrives
  anonymised. Age is 57% NULL by design and gated behind an explicit flag.

### 7.6 Curveballs

- **"What if a new low-cost carrier reshapes the market next year?"** Then the input distributions
  move and the PSI monitor fires — that's what it's for. We tested one 12-month step inside one
  extract; we make no claim about behaviour under a structural shock, and the drift alarm is the
  honest substitute for a claim.
- **"You keep saying 'honest'. Is that covering for weak results?"** The results stand on their
  own: 44 of 55 boundaries clearly distinct, a 74% cut in Unassigned, a corridor finding nobody
  had quantified. The honesty machinery is what makes those numbers *usable* — a decision-maker
  who can't see the error bars can't safely act on the point estimate.
- **"Two methods disagree on temporal transfer. Doesn't that undermine V4?"** It bounds it. The
  full-population composition result — shares holding within 1.71 pp — doesn't depend on transfer
  at all. The transfer question needs a multi-seed spread before anyone should quote a ratio, and
  that's listed as pre-handover work.
- **"If PAL had given you loyalty data, would the whole design change?"** The waterfall gains a
  branch and Mabuhay becomes measurable, but the architecture stands — a loyalty tier is one more
  field, not a new paradigm. The continuum finding wouldn't reverse: adding a column doesn't
  create density gaps in the other forty.

---

## 8. Per-presenter drill

**Martin (problem, TOR, recommendations).** Own the constraint story (anonymous lens) and the
risk register — every TOR risk fired and each has a disposition. For recommendations, the stance
to hold: data investments before algorithm work, and the weights are a costed proposal awaiting
PAL. Must-know numbers: $495–$9,784, the four risk dispositions, Balikbayan 12.5%/28.4%.

**Josh (EDA, methodology, findings, limitations, conclusion).** The heaviest load: the continuum
proof chain (ceiling 0.381 → planted segments → majority floors → blind spot), the circularity
contract, all four validation stages with the honest reading of each, and every entry in the
never-say table. Rehearse the 0.861-vs-0.637 explanation until it's one breath.
Two slides changed shape on 19–20 Aug and need their own passes: **19 (sub-segments)** — new, and the
only slide showing what the ML produced; lead with "the rules give eleven segments to talk about, the LCA
gives twenty cells to act on", and never say BIC chose four. **21 (validation)** — open with the Plan B
framing, not the number: *we wrote these labels ourselves and have no answer key yet, so here are four
checks that need none.* Both have full speaker notes in the deck; §6.2 is the long form for 21.

**Jadd (dashboard).** The reconciliation argument (38,116,259 in = out, asserted), the four traps,
the persona card governance columns, and the maintenance answer (§7.1 last question). Have the
demo recording tested on the actual venue machine.

**Everyone:** recite §1 cold; know the memorize-table; read the defence brief's what-to-say list
the night before.

---

## 9. Stale numbers in older documents — don't get ambushed by our own paper trail

Several repo documents predate the 17–18 August taxonomy approval and carry superseded figures.
If a panelist quotes one at you, the answer is "that document predates the approved v2 taxonomy —
the current figure is X, and the changelog is in the defence brief." Known stale figures:

- **"10 segments" / "9 named + Unassigned"** → now 11 named + Unassigned.
- **Unassigned 9.6%** as a current number → that was v1; now 2.47%.
- **Budget/Adventure 39.4% of bookings, $74** → renamed Leisure; 50.6%, $80 under v2 counting.
- **Premium Bleisure 2.1%, $1,504** → v2: 1.5%, $1,188.
- **Family and Digital Nomad as live segments** → both retired for cause.
- **"Last-Minute: genuinely open question"** → answered; it's a flag now.
- **"Currency undocumented"** → USD, confirmed by PAL 18 August.
- **LCA transfer ratio 1.13** → withdrawn (43%-sample bug); current: GMM 1.24, LCA 0.89.
- **"1 significant H0 component"** → instrument retired; continuum holds via the robust parts.
- **Penalty ladder ×1–10 with Corporate ×10, Mabuhay ×8** → superseded by the dollar-grounded
  proposal (Corporate 8, Premium Bleisure 9, Balikbayan 4), pending PAL.
- **V4 share/revenue TVD 1.93 pp / 3.21 pp** → the 29 Jul run; the 18 Aug re-run gives **1.71 / 3.36**.
- **"a model fitted a year earlier transfers for free"** → only on the best-transferring method; the
  panel now disagrees (GMM 1.24 · LCA 0.89), so no refit-cadence claim is made at all.
- **"7 of 10 segments show negligible drift, 98.2%"** → the v1 count; v2 is **8 of 12 carrying 98.1%**.
- **Lead time "median 25 days / 13.3% inside three days"** → **coupon** grain. At booking grain, the
  grain we model, it is **median 18 / 19.26%** — and 19.26% is the flag's own 4,411,666.
- **"38.4% issued abroad"** as a booking figure → 38.4% of *coupons*; **34.6%** of bookings.
- **66.5% of labels uncontested / Corporate most contested** → computed on **v1** labels, 12 Aug, and not
  re-run since waterfall v2. Still directionally the reason Corporate leads the SME sample, but if asked
  for a current figure the honest answer is "not measured since the redesign."
- **`rule_confidence.py` output generally** → same caveat: it hard-codes the v1 ten-branch waterfall.
- **The deck itself was 24, then 25, then 26 slides** → any printout whose row 19 is not "sub-segments"
  is stale.

---

## 10. Study plan

**Session 1 — the story (90 min, together).** Read §1–§2 aloud, argue about any sentence anyone
can't defend, then each person recites §1 from memory. Close by walking the deck once, silently,
against the §6 table.

**Session 2 — the machinery (2 h, Josh leads).** §3 end to end. For each technique, one person
explains it in plain words + analogy, another plays the panelist and pushes one level deeper.
Stop at the level of §3 — deriving math on a whiteboard is not required and not useful.

**Session 3 — the gauntlet (2 h, full mock).** Present the deck to time (targets: Martin 8,
Josh 20, Jadd 7, conclusion 2). Then 30 minutes of hostile Q&A from §7 in random order, including
at least three stale-number ambushes from §9. Score each answer: did the first sentence answer
the question? Did it stop?

**Night before:** the defence brief's "What to say, and what not to" — all three of you,
individually. Then stop studying. You know this project better than anyone in the room; the
preparation's job is to make that visible.

---

*Sources: `docs/defense-brief-2026-08-18.md` (binding) · `docs/pipeline-study-guide.md` (deep
dives, §6.2 metrics and §12 glossary) · `docs/methodology.md` · `docs/segment-cost-research.md` ·
`docs/waterfall-v2-design.md` · `outputs/` stage summaries. Last updated: 2026-08-18.*
