# Final Defense Reviewer — 26 August 2026

**Defense: Thursday 27 August 2026 · Panel: seasoned data scientists · Deck: `CPT3_DefenseDeck_V3 1.pdf` (28 slides — the 26 Aug business-first rebuild; the repo pptx is superseded)**

This is the **final consolidated reviewer**: everything current as of 26 Aug, a stress test of the
project's own logic (including fresh findings not in any earlier guide), the methodology, EDA and
results end to end (§1.2–§1.4), the deck slide by slide (§5 — audited page-by-page against the
26 Aug rebuild), and the full question bank a panel of
experienced data scientists would draw from — with model answers. **§1.1 explains every
load-bearing concept in plain English first, technical second — read it before the question
bank.**

How it relates to the other documents: `defense-study-guide.md` (18–20 Aug) remains the drilling
companion (its §6.1/§6.2 deep dives on the limitations and validation slides still stand);
`defense-brief-2026-08-18.md` remains binding on what to say / not say. **This document supersedes
both on anything dated 21–26 Aug** (level-2 shipped, the business cases, the continuum extensions,
and the stress-test findings in §3).

Answer style for everything in §6: **first sentence answers the question. Then one piece of
evidence. Then stop.**

**If you are not the technical presenter, study this way:** read §1 and the *plain* lines and
tables of §1.1–§1.4, know your own rows in §5, and learn the ***Everyone can say*** line under every question in
§6 — each one is a safe, complete answer in ordinary words. The *full versions* are the technical
presenter's depth; you never need them to survive a question. Handing off is always allowed:
answer with the plain line, then “Josh can take that further if useful.”

---

## 1. The story in 60 seconds — current version

> PAL sells seats to passengers it cannot see — anonymous bookings, no loyalty join. We were asked to
> find the customer segments hiding in 38 million coupon rows. We looked properly: ten clustering
> methods across six algorithm families, and they all hit the same ceiling, because PAL's customers
> are not clusters — they're a continuum. We proved that finding could not be our own blindness by
> planting artificial segments in the real data and recovering them. So we flipped the design:
> business rules draw the segment boundaries, and machine learning got three jobs — refine, test,
> monitor. The result is **eleven named, costed segments on 22.9 million bookings, plus twenty
> ML-derived sub-types now assigned to all 21.7 million bookings in the five biggest segments**, a
> dashboard that reconciles to the row, an economic case that resolves on **breakeven (0.48% of one
> measured exposure) rather than forecast**, and — the part we're proudest of — the machinery that
> says exactly how far each label can be trusted.

Emotional register: calm, specific, unembarrassed. We are defending a team that measured its way out
of three wrong designs and wrote every wrong turn down.

### 1.1 The ideas in plain English — what everything hangs on

Thirteen concepts carry the whole defense. Each gets three registers: **plain words**, the
**technical statement**, and **the number to attach**. Panels escalate from plain to technical —
an answer that can move between registers reads as mastery, and one that can only do jargon reads
as memorization.

**1 · The continuum.**
*Plain:* PAL's customers don't come in natural bunches — they blend into each other like the
colors of a rainbow. "Orange" is still a useful word; where orange ends is our decision, not
nature's.
*Technical:* ten clustering methods across six algorithm families ceiling at Gower silhouette
0.381 (0.50 is the conventional "real structure" bar); BIC declines monotonically from k=1; every
computable internal index agrees.
*Number:* 0.381 · no elbow at any k.

**2 · Rules label, ML checks.**
*Plain:* when there are no natural bunches, any algorithm still draws lines — and different
algorithms draw different arbitrary lines. So the business draws them where decisions need them,
and ML's real jobs are to refine below the lines, test whether they sit in defensible places, and
watch for drift.
*Technical:* a deterministic first-match-wins rule waterfall assigns every label; LCA sub-types
the five biggest parents; V1–V4 validate; PSI monitors.
*Number:* 11 segments + Unassigned on 22.9M bookings.

**3 · Circularity and anchors.**
*Plain:* a rulebook can't grade its own homework. If a rule built the label out of field X,
showing that the label "predicts" X proves only that the code ran.
*Technical:* validation may only touch anchors — fields no rule consumed — enforced by a contract
that raises an error, including against disguises (a field that equals a rule input after
coarsening is banned exactly where that bit is the boundary under test).
*Number:* only 2 fields are unconditionally clean — and this is why no accuracy figure exists.

**4 · AUC.**
*Plain:* pick one booking from segment A and one from B at random; AUC is how often a classifier
can tell which is which. 0.50 is coin-flipping, 1.00 is every time.
*Technical:* held-out ROC-AUC on admissible anchors per segment pair, with bands (<0.60 /
0.60–0.75 / >0.75) calibrated by control runs.
*Number:* median 0.861 across 55 pairs · 44 clearly distinct · 0 indistinguishable.

**5 · Silhouette on Gower distance.**
*Plain:* at a wedding, how sure is each guest about which table they belong to? Near zero means
the tables are a seating chart, not friend groups. Gower is the ruler that still works when the
features mix numbers and categories.
*Technical:* mean silhouette computed on Gower dissimilarity — the cross-method separation
yardstick of the ten-method benchmark.
*Number:* ceiling 0.381 against the 0.50 bar.

**6 · BIC and "no elbow".**
*Plain:* BIC scores fit but fines complexity. If real groups exist, the score drops sharply until
you reach the true group count, then levels off — an elbow. Ours never bends: each added group
buys a little less than the last, from one group up.
*Technical:* monotone BIC decline over k=1–9 (StepMix LCA, 60k sample, seed 42); Davies–Bouldin
and Calinski–Harabasz corroborate.
*Number:* 1,148,667 → 988,748 over k=1–4, no interior optimum anywhere.

**7 · ARI.**
*Plain:* how much two ways of labeling the same things agree beyond what luck would give — 0 is
coincidence-level, 1 is identical.
*Technical:* adjusted Rand index; used for method-vs-taxonomy agreement, split-half stability, and
model transfer across years.
*Number:* k=2 scores 0.537 but is geography (0.909 against the domestic bit alone); the
customer-structure ceiling is ~0.39.

**8 · Detection power.**
*Plain:* test the smoke detector with actual smoke before trusting its silence. We hid artificial
segments of known size inside the real data and checked whether our own methods find them. They
do, from 2% of bookings up — so silence on the real data is a finding, not blindness. Below ~1% we
cannot see, and we say so.
*Technical:* planted-segment injection; recovery scored as best-F1 against pre-registered,
control-derived thresholds; floors are majority-rule across the panel.
*Number:* detected at ≥2% prevalence (distinctness ≈0.494) · blind below ~1% (~229k bookings).

**9 · TVD and PSI.**
*Plain:* TVD is the biggest slice-by-slice difference between two pies — how many percentage
points of the mix must move to turn last year's segment shares into this year's. PSI is the
standard early-warning alarm that an input's distribution has shifted.
*Technical:* total variation distance on full-population shares; population stability index per
rule input, decomposed so a brand-new category isn't mistaken for behavioral drift.
*Number:* share TVD 1.71 pp · segment-mix PSI 0.0028 · channel 0.4111, 93% of it the NDC launch.

**10 · Right-censoring.**
*Plain:* our window is ~27 months. A customer seen once might be gone forever — or might have
joined last week; from inside the window the two are identical. So "74% never return" and any
churn rate are illusions of the window, not facts about customers.
*Technical:* repeat behavior must be cohorted by entry date or given an explicit horizon; churn is
not computable on this extract.
*Number:* 73.9% single-booking · 26.5% return within 12 months · segment stability falls
87.8% → 53.4% among repeat customers.

**11 · Weak supervision (the "Semi-Supervised" slide).**
*Plain:* nobody gave us answer keys, so the business rules write the labels, models refine
underneath, and audits test the boundaries — and nothing pretends the labels are the truth, which
is exactly why no accuracy number ships.
*Technical:* programmatic weak supervision via a prioritized rule waterfall; unsupervised LCA
refinement; label-free validation behind the circularity contract.
*Number:* 66.5% of bookings matched exactly one rule (v1 measurement).

**12 · Scoring cells, not rows.**
*Plain:* the sub-segment features are all categorical, so 21.7 million bookings collapse into
17,847 distinct combinations of traits. Score each combination once, weighted by how many bookings
share it — mathematically identical to scoring every booking, and the model becomes a spreadsheet
you can read end to end.
*Technical:* StepMix fitted on the count-weighted cell table; weighted BIC hand-computed because
the library's `bic()` mis-reads weighted data.
*Number:* 17,847 cells = 21,725,296 bookings, exactly.

**13 · Breakeven vs NPV.**
*Plain:* NPV asks "how big might the prize be?" — that needs a forecast. Breakeven asks "how
little must this recover before it pays for itself?" — that needs only the real cost and one
measured exposure. We decide with breakeven and size with NPV, and never average the two.
*Technical:* $77,904 actual cost against the $16.1M dilution pool built on the measured $645.8M
exposure; the +$7.3M NPV is conditional sizing from industry benchmarks.
*Number:* breakeven 0.48% — one dollar in 207.

### 1.2 How it was built — the methodology, start to finish

*Plain version: turn 38 million ticket rows into 23 million purchase decisions, label every one
with a business rulebook, let machine learning split the big groups and audit every boundary, and
ship it as a dashboard that checks its own math.*

The load-bearing idea in one picture — **the rules label, and ML checks the labels**:

```text
raw extract → typed Parquet → clean + flag → features (coupon → booking → customer)
→ RULE WATERFALL — THE MODEL (11 segments + Unassigned)
   ├─ LCA refinement    sub-types inside the 5 biggest segments   (ML job 1)
   ├─ V1–V4 validation  are the boundaries real?                  (ML job 2)
   └─ PSI monitoring    has the world drifted?                    (ML job 3)
→ Power BI star schema (38,116,259 rows in = out, asserted on every build)
```

| Stage | What happens | Plain version | Key number |
|---|---|---|---|
| 1 · Extract | four gzipped CSVs from PAL's warehouse | the raw shoebox of tickets | 38.1M rows · 40 columns · departures May '24–May '27 |
| 2 · Typed Parquet | one conversion pass | file the shoebox into a fast cabinet | ~90 s once; queries drop from minutes to sub-second |
| 3 · Clean + flag | farebrand → value tier 1–7; award / group / non-rev / refund flags; routes parsed | label every ticket's price rung and special cases | ~21 s; exact duplicates ≈ 0, so no dedup |
| 4 · Features | coupon → booking → customer grain changes; airport→region join; four feature families | turn flight legs into purchase decisions | 22.9M bookings · 13.4M customers; every grain change asserted |
| 5 · **Rule waterfall — the model** | a priority checklist; the first rule that matches a booking claims it | a triage nurse working down a checklist | 11 segments + Unassigned 2.47%; six PAL hard rules asserted on every build |
| 6 · LCA refinement | sub-types inside the five biggest segments | ML splits the big groups into actionable cells | 20 sub-types, assigned on 21.7M bookings via 17,847 cells |
| 7 · Validation V1–V4 | four label-free audits (details in §1.4) | checks that never use the rules' own ingredients | 44/55 · floors ≥2% · TVD 1.71 pp |
| 8 · Monitoring | PSI drift alarms on every rule input | tripwires on the data feeding the rules | segment mix 0.0028; the one alarm = the NDC channel launch |
| 9 · Export | Power BI star schema + persona and sub-segment dimensions | a dashboard that checks its own math | 38,116,259 in = out; **no accuracy KPI, by design** |

**Why this design and not "just cluster it" — the fourth design, not the first.**
*Plain:* we tried the textbook route first. The prototype clustered a small sample beautifully;
on the real data there was nothing to cluster — the customers form a smooth blend (§1.1, idea 1).
When ten different methods from six algorithm families all hit the same ceiling, the honest move
is to stop forcing boundaries and let the business draw them where decisions need them — then
prove those lines sit in defensible places. *Technical:* HDBSCAN dropped (no density separation in
categorical-heavy data); k-prototypes/k-modes lost the head-to-head to LCA; the ten-method
benchmark (GMM, spectral, SVC, TDA-Mapper, persistent homology…) confirmed the continuum on eight
scoring axes; the rule waterfall became primary with LCA as the refinement layer.

**Nothing learns at the top level — and that is a feature.** Scoring a new booking = applying the
same checklist; the labeller itself cannot drift. Change can only enter through the input data,
which is exactly what the monitor watches.

### 1.3 What the data showed — EDA in ten findings

*Plain version: customers buy late, buy cheap, fly domestic — but the money flies international.
Most customers appear only once in our window, the extract has sharp edges you must respect, and
one corridor keeps a clock no other does.*

| # | Finding, in plain words | The numbers | Watch out |
|---|---|---|---|
| 1 | A ticket row is one flight leg; a purchase is usually several | 38.1M coupons → 22.9M bookings (1.66 legs/booking) · 42.7% round trips | this grain change is why our numbers differ from naive row counts |
| 2 | Customers buy late — most show up and buy | median lead 18 days · 19.26% within 3 days | the 120-day pile-up is a data cap, not behaviour; never quote the coupon-grain 25 d / 13.3% |
| 3 | Customers buy cheap | the two cheapest fare brands = 63.1% of bookings (value bands: Budget 63.1 · Mid 30.9 · Premium 6.0) | 70.6% is a different measure (any cheap leg) — don't mix them |
| 4 | Domestic carries the bookings, not the money | domestic 58% of bookings but 19.3% of revenue; North America 8% → 35% at $1,141/booking | multi-region trips are filed alphabetically — a known 1.65% edge |
| 5 | Most customers appear only once — but that's the window, not the customer | 73.9% single-booking · 26.5% return within 12 months · earliest cohort reaches 40.5% | never say "74% never return" |
| 6 | A third of bookings are bought abroad | 34.6% of bookings (38.4% of coupons) | quote the booking figure |
| 7 | The extract is cut by flight date, not purchase date | departures May '24 – May '27; **2025 is the only complete travel year** | naive year-over-year comparisons draw fake cliffs and fake lead-time collapses |
| 8 | Age is mostly missing on purpose | 57% NULL; known for 0.86% of domestic vs 87.6% of international | the gap mirrors a rule — which is why age was banned as validation evidence |
| 9 | The money is in US dollars — confirmed | CY2025 revenue $2,535.0M (PAL confirmed USD 18 Aug) | older docs said "currency unknown" — superseded |
| 10 | Manila–Gulf runs on a one-month clock no other corridor has | 19.11% of Gulf round trips at 28–32 nights vs 8.48% at 12–16; every other corridor ≤0.60 ratio | present the pattern, not the cause — a fare-rule explanation is still open |

### 1.4 What came out — the results

*Plain version: eleven named segments plus an honest leftover bucket; twenty sub-groups inside the
big five; four audits that all passed with stated limits; and money findings that pay for the whole
project many times over.*

**(a) The taxonomy — 11 segments + Unassigned, on all 22.9M bookings:**

| Segment | Bookings | Revenue | $/booking | In one phrase |
|---|---|---|---|---|
| Leisure *(was Budget/Adventure)* | 50.6% | 15.0% | $80 | the domestic economy mass |
| OFW/Migrant | 17.1% | 19.6% | $312 | workers to/from contracts; sea crew included by channel |
| Balikbayan/VFR | 12.5% | **28.4%** | $615 | **the revenue engine** — family visits home, long-haul round trips |
| Outbound Intl. Leisure | 9.5% | 14.0% | $398 | Filipinos buying international economy — the segment that emptied Unassigned |
| Corporate | 5.1% | 8.7% | $460 | business travel; the most contested label, first in line for expert review |
| Unassigned | 2.5% | 1.6% | $177 | honest leftovers — mostly domestic premium-cabin with no rule branch |
| Premium Bleisure | 1.5% | 6.6% | $1,188 | premium international business-leisure mixers |
| Ultra Wealthy Leisure | 0.7% | 5.0% | $1,968 | the top of the ladder — long-stay, far-advance premium |
| Pilgrimage | 0.19% | 0.28% | $404 | Jeddah/Medina traffic |
| Intl. Student | 0.18% | 0.79% | $1,159 | small and high-value |
| MICE | 0.12% | 0.12% | $269 | group events booked far ahead — value understated (per booking, not per contract) |
| Mabuhay Loyalist | 0.03% | 0.01% | $113 | award redemptions only — the loyalty blind spot kept visible on purpose |

Riding alongside: the **short-lead flag** on 19.26% of bookings (4.41M — bigger than the retired
Last-Minute segment ever was), and **value bands** (Budget 63.1 · Mid 30.9 · Premium 6.0).

**(b) The sub-segments.** Twenty cells inside the five biggest segments, now stamped on all 21.7M
of their bookings. *Plain:* every big segment splits along the same three dials — direction,
timing, fare tier — and volume and value invert *inside* segments too: Balikbayan's thinnest
sub-group (16.9%) earns **$995** per booking while its fattest (38.8%) earns **$311**. Two parents
are nearly flat (OFW 1.7×, Outbound 1.2×) — a useful negative: those don't need sub-group pricing.

**(c) The validation scoreboard** — four audits, none using the rules' own ingredients.
*Plain framing: there are four ways a segmentation can be worthless — the groups could be
identical, the labels could mean nothing for behaviour, the method could be blind, or the whole
thing could be a one-year accident. One test per failure mode. Two design rules bind all four:
read the blank test first, and never use the rules' own ingredients.*

| Audit | The question, plainly | The answer | The number |
|---|---|---|---|
| V1 · Construct | are the segments really different? | yes — for 44 of 55 pairs, on evidence the rules never touched; weakest edges sit on Corporate and Leisure, and we say so | median AUC 0.861 · 0 indistinguishable |
| V2 · Criterion | do the labels predict behaviour? | they carry real signal but add nothing over the raw data — expected for labels *built from* that data; owned as a limit | 0.598/0.604 alone · +0.0005–0.0024 incremental |
| V3 · Detection power | could we have missed a hidden group? | not one bigger than ~2% of bookings — the fire drill proves it; below ~1% we're blind and say so | floors ≈0.494 @ 2% · blind <1% (~229k) |
| V4 · Stability | does it hold a year later? | sizes held; revenue mix moved a little more; one narrow sub-question (model transfer) stays open | share TVD 1.71 pp · revenue 3.36 pp · 8/12 labels carry 98.1% |

**V1 · Construct — the instruments behind the number.**
- *Why this test exists:* we drew the boundaries ourselves. If two "segments" cannot be told apart
  on evidence the rules never saw, the boundary is decoration.
- *How it works:* for each of the 55 pairs, train a classifier on anchor fields only and score it
  on held-out data: can it tell segment A from segment B?
- *Why AUC and not accuracy:* segments differ ~1,000× in size (Leisure 50.6% vs Mabuhay 0.03%).
  Accuracy is fooled by imbalance — "call everything Leisure" scores brilliantly while learning
  nothing. AUC asks one question that is fair at any size ratio: pick one random booking from each
  side — how often does the model rank them correctly? It needs no threshold, and its null is a
  fixed 0.50 coin flip, so control runs can calibrate the whole scale.
- *Why gradient boosting as the probe:* it handles missing values and categories natively (age's
  not-at-random gaps get modelled, not imputed away) and it is a strong learner — so a low score
  means "these groups genuinely don't differ", not "our probe was weak". Held-out scoring keeps
  memorization out of the number.
- *Guardrails:* the negative control — each segment split randomly in half, which must score
  ≈0.50 — is read **first**; if it doesn't, the harness leaks and every number below is void (it
  landed 0.494–0.513). A positive control calibrates the top (0.641 on strict anchors). Anchors
  are admitted per pair, so a field never validates the very boundary it encodes.
- *Found / cannot say:* 44 of 55 clearly distinct, median 0.861, zero indistinguishable; the weak
  edges concentrate on Corporate (6) and Leisure (5) and we volunteer that. It cannot certify the
  *names* — "behaviourally validated; names not externally confirmed."

**V2 · Criterion — the instruments behind the number.**
- *Why this test exists:* a label that carries no signal about future behaviour is just paint.
- *How it works:* a four-rung ladder — coin flip → label alone → the 11 raw features → features +
  label — against outcomes no rule reads (did they fly; did they rebook within 180 days).
- *Why a ladder and not one score:* the label is *built from* the features, so it can never beat
  them — "did the segmentation beat the model?" is a rigged question. The two fair questions are:
  how much of the signal does the label alone retain, and does it add anything on top
  (incremental value).
- *Guardrails:* outcomes chosen precisely because no rule consumes them; the refund outcome is
  reported as **infeasible rather than fitted** (347 events is too rare to model honestly);
  bookings near the extract edge are excluded so "hasn't flown yet" is never counted as "didn't
  fly".
- *Found / cannot say:* label alone 0.598/0.604 — real signal; incremental +0.0005–0.0024 —
  effectively nothing, by construction, owned as a limitation. It cannot support selling the
  segmentation as a prediction engine; its value is shared vocabulary and targeting.

**V3 · Detection power — the instruments behind the number.**
- *Why this test exists:* ten methods saying "no clusters" is only evidence if those methods could
  see a cluster when one exists. Otherwise silence just means blindness. This test makes the null
  result falsifiable.
- *How it works:* plant artificial segments of known size (0.5–10% of bookings) and known
  distinctness into the real data, refit the same model panel, and measure whether the planted
  group comes back out.
- *Why F1:* a planted group counts as "found" when some fitted cluster overlaps it well — F1
  balances finding most of it (recall) against not drowning it in a bigger cluster (precision).
  The distinction matters because the observed failure mode is *smearing*: perfect recall with low
  precision means the group was detected but absorbed — useless in practice. F1 punishes exactly
  that.
- *Guardrails:* detection thresholds are **pre-registered** from no-signal control runs — a method
  with a noisy control faces a *higher* bar, not a lower one; published floors are
  **majority-rule** across the 12 method × archetype cells, never the luckiest single cell; and a
  random-direction archetype proves the floor isn't an artifact of a well-chosen guess. One of our
  own instruments failed its control here (a count that returned 2–131 on identical data) and was
  retired — the guardrails work on us too.
- *Found / cannot say:* majority detection from 2% prevalence (distinctness ≈0.494), 5% (≈0.219),
  10% (≈0.13); never below ~1%. It cannot rule out a segment smaller than ~229k bookings, and the
  floors are optimistic — a real hidden group could be messier than a planted one.

**V4 · Out-of-time stability — the instruments behind the number.**
- *Why this test exists:* a segmentation that only describes one period's booking conditions
  passes every other audit and is still worthless to act on.
- *How it works:* split the data into two adjacent 12-month purchase windows — placed carefully
  inside the region the departure-date cut doesn't distort — and re-ask every stability question
  across the step.
- *Why TVD and not a significance test:* the shares are full-population counts, so there is no
  sampling error to test — and TVD reads directly in business terms: how many percentage points of
  the mix moved. *Why an adversarial AUC:* one honest number for "can a model even tell the two
  years apart?" — 0.62, sitting between the nothing-changed rail (0.49) and the everything-changed
  rail (0.99). *Why transfer-with-a-ceiling:* last year's model scores this year, compared not to
  a perfect 1.0 but to the method disagreeing with itself on a single window — the shortfall below
  that ceiling is what a year actually costs.
- *Guardrails:* both windows are exactly 12 months, so seasonality cannot masquerade as drift;
  per-segment profiles use a stratified draw (a uniform sample would give Mabuhay ~9 rows);
  outcome fields are excluded as censored, with the censoring curve published so the exclusion is
  visible.
- *Found / cannot say:* share TVD 1.71 pp; 8 of 12 labels stable carrying 98.1% of bookings;
  revenue mix is the weaker leg (3.36 pp — a segment holding its size is not proof its value
  held); the transfer sub-question is unresolved (two methods, opposite verdicts — no claim made).
  It cannot promise behaviour under a structural shock — that is the monitor's job, not a claim.


**(d) The money findings:**
- Half the bookings earn a seventh of the money (Leisure 50.6% → 15.0%); Balikbayan/VFR inverts it
  (12.5% → 28.4%).
- **$645.8M** of revenue sits in sub-groups priced ≥1.25× their segment average — the measured
  exposure behind the **0.48% breakeven** (one dollar in 207 pays for the whole build).
- Channel mix belongs to the segment, not the airline: agency dependence spans **6.6×**; Sea Crew
  is a **$136.6M channel serving one segment**; Corporate is 55.5% corporate-channel.
- CX priorities invert by segment: digital revenue share spans **19×**; lounge/transfer is a
  *Balikbayan* question (49.9% connecting), not a premium-cabin one.
- Department readiness falls out of the evidence: **Sales and CX can act now** (no assumptions
  needed), RM with instrumentation, Marketing is the test site, **Loyalty waits** (censored data).

**(e) What the results cannot claim** — say these before the panel does: no accuracy figure (no
ground truth yet); no measured uplift (no campaign has run); the segments are useful partitions of
a smooth blend, not natural kinds; no churn rate exists (censoring); and the segment *names* are
behaviourally validated but not externally confirmed — "the group we call Corporate behaves like
business travel; PAL's experts haven't yet certified the name."

---

## 2. What changed since the study guide (21–25 Aug) — learn these first

The study guide is current to 20 Aug. Five things have moved since; a panelist who read the newest
material will probe exactly here.

### 2.1 Level 2 shipped (21 Aug) — the sub-types are now assignments, not descriptions

*In one sentence: the sub-groups inside the five biggest segments are no longer just described —
every booking now carries its sub-group label in the dashboard.*

- `subsegment_assign.py` assigns a `SubSegment` to **all 21,725,296 bookings** in the five sub-typed
  parents. Power BI carries it on every fact table plus a **28-row `dim_subsegment`**.
- The trick worth being able to explain: the LCA feature space is discrete, so **17,847 distinct
  cells cover all 21.7M bookings** (Leisure 1,281 · OFW 5,796 · Balikbayan 1,175 · Outbound 2,857 ·
  Corporate 6,738). Score cells, join in SQL — the whole level-2 model is a readable CSV.
- The 40k sample is retired for the assignment path: StepMix fits the **count-weighted cell table =
  the whole population exactly** (verified to machine precision). ⚠️ `StepMix.bic()` is wrong on a
  weighted cell table (unweighted score, N = cells), so **weighted BIC is hand-computed** — a good
  "do you actually understand your libraries" answer.
- **Two fits, two profiles.** The deck and `sub_segments/summary.md` keep the **sampled** profiles
  (Balikbayan **$311 → $995**); the manuscript quotes the **population-exact** ones
  (**$322 → $962**) and states in §4.2.5 that they supersede the sampled ones. If a panelist has
  both documents: *"the manuscript names the discrepancy and says which is authoritative — the deck
  was already rehearsed against the sampled figures, and the finding (a ~3× value spread on booking
  horizon inside one segment) is identical in both."*
- Side-effect numbers that moved: **scorecard is now 3,544 rows** (was 1,835 — it carries
  `SubSegment`), `fact_flight` 20.7M (was 20.6M). The study guide's memorize table still shows the
  old pair.

### 2.2 The economic case (21–23 Aug) — two documents, one division of labour

*In one sentence: we now have two money stories — a measured one saying this pays for itself if
we recover half a percent of one exposure, and an industry-benchmark one saying the prize could be
~$2.7M a year.*

- **Bottom-up, measured** (`do-nothing-vs-implement.md`): organised by the five departments that
  would consume the output. Measured facts (CY2025, the only complete travel year: **$2,535.0M**
  revenue, 9.83M bookings): within-segment value spreads up to **5.63×** (Corporate); **$645.8M**
  of parent revenue sits in sub-types priced ≥1.25× their parent mean; agency dependence spans
  **6.6×**; digital revenue share spans **19×**; Sea Crew is a **$136.6M channel serving one
  segment**. Decision resolved by **breakeven**: year-1 cost is the **actual $77,904 budget**, so
  recovering **0.48%** (one dollar in 207) of the $16.1M/yr dilution pool pays for it. Stress:
  halve the two promo placeholders → **1.9%**; add market-rate staffing ($487K shadow) → **12.1%**.
- **Top-down, benchmark** (`business-case-benchmark.md`): ~**$2.7M/yr** risk-adjusted margin,
  **+$7.3M** five-year NPV at 10%. **Quote only with its three conditions attached**: ① the
  ancillary lever (45% of the benefit) rests on revenue the extract does not contain; ② the
  retention lever presumes identity the data lacks (73.9% single-booking — churn not computable);
  ③ its $1.96B revenue base is ~⅓ below the extract's measured ~$2.9B/yr.
- The line that resolves any "your two cases disagree" attack: **"the breakeven decides, the NPV
  sizes — we never average them."**
- Readiness ordering (falls out of the evidence, not preference): **Sales and CX first** (no
  response assumption needed — they reallocate existing effort), RM with instrumentation, Marketing
  is the best test site (one instrumented campaign replaces the free parameter), **Loyalty waits**
  (right-censored data).

### 2.3 The continuum claim got strictly stronger (23 Aug)

*Plain version: we asked the data “how many groups are you?” five different ways, and every way
answered “none you don't already know” — the only cut any method finds is domestic vs
international.*

- **BIC extended down to k=1**: 1,148,667 (k=1) → 1,057,599 → 1,014,017 → 988,748 (k=4), monotone
  from one component. "No elbow from 3" is now "**no elbow at all** — the base is not even two
  masses."
- **Davies–Bouldin and Calinski–Harabasz finally computed** (on the one-hot/Euclidean representation,
  where they are defined): DB 2.62–3.03 at every k (well-separated ≈ 1; its "best" is k=9, the top
  of the range again); CH declines monotonically from k=2; Euclidean silhouette 0.074–0.133. **Every
  internal validity index that can be computed agrees with BIC: nothing settles.**
- **The k=2 finding — know this cold, it is the newest number in the project.** Extending the ARI
  sweep to k=2 finds ARI **0.537** vs the v2 taxonomy — *above* the 0.389 (k=4) every document
  quotes. But a composition probe shows the k=2 partition is **`is_domestic` rediscovered**
  (ARI **0.909** against the domestic/international bit alone; Corporate — 57/43 domestic — splits
  50.1/49.9). Agreement *falls* toward the taxonomy's own cardinality (0.306 k=3 · 0.389 k=4 ·
  0.210 k=9). The sharp sentence: **"unsupervised methods recover the taxonomy's geographic spine
  and none of its finer boundaries."** ⚠️ Never quote 0.54 without the geography qualifier; the
  customer-structure ceiling is still ~0.39.

### 2.4 Manuscript finalised (23 Aug)

*In one sentence: the thesis chapters are final, and build-vs-buy lands firmly on build.*

Ch. 4 v1.1 (results/validation, v2 throughout, every withdrawn number absent or explicitly
disowned), Ch. 5 v2.0 (findings F1–F13, economic case, build-vs-buy, recommendations), Appendix A
(do-nothing in manuscript register). Build-vs-buy resolves on facts: $77,904/yr actual build cost;
every vendor case study (KLM, easyJet, Alaska…) runs on **identified** customers, so a bought
platform inherits our anonymity ceiling while charging licence from day one. **Recommendation:
build (done); re-evaluation trigger is identity-data arrival.**

### 2.5 The sensitivity analysis was redesigned — a good methodological story

*In one sentence: when a guessed cost became a real budget, we redid the what-if analysis on the
things that are still guesses.*

The 21 Aug version stressed year-1 cost by 10× because it was a placeholder. When the $77,904
actual budget landed, stressing a *measured* number became noise — so Appendix A restates the
stress on what is still assumed (the promo placeholders, the staffing shadow). One-line lesson if
asked about the analysis process: *"every sensitivity analysis encodes which inputs it believes are
uncertain; when a placeholder graduates to a measurement, you re-derive the stress."*

---

## 3. Stress test — where the logic can break

This section is the adversarial pass this document exists for. §3.1 is new material found on
25 Aug — not in any earlier guide. §3.2 is the open-items list a well-read panelist could spring.
§3.3 maps the project's three load-bearing argument chains and where each can be attacked.

### 3.1 New findings from this pass (25 Aug)

#### ⚠️ Finding 1 — "87.8% of customers never leave their segment" is mostly censoring. Fix the line before Thursday.

`do-nothing-vs-implement.md` §3 presents **87.8% `segment_diversity = 1`** as the structural fact
that makes person-level segment treatment coherent. But **73.9% of customers book exactly once and
therefore cannot have diversity > 1** — the same censoring the document itself flags in §4.5.
Measured directly on `pal_features_customer.parquet` (25 Aug):

| Population | Share with `segment_diversity = 1` |
|---|--:|
| All 13,435,365 customers | **87.8%** |
| The 3,512,004 repeat customers (n_bookings > 1) | **53.4%** |
| Customers with 3+ bookings | **38.6%** |

A back-of-envelope independence baseline (two bookings drawn independently from the v2 mix,
Σpᵢ²) is **~31%** — so repeat customers stay in one segment at roughly **1.7× chance**, which is a
real but much weaker claim than 87.8%.

**The honest line to use:** *"Among customers we observe more than once, about half stay in a
single segment — roughly 1.7 times what independent draws would give — and the segment label is a
booking-level fact first. For the 74% we see once, the label simply is their booking."* The
segment-treatment argument survives (a person's *dominant* segment is still well-defined, and
`CustomerDominantSegment` ships), but **87.8% must never be said without the censoring caveat** —
a data scientist will decompose it in their head in about ten seconds, and the do-nothing document
was written *for this panel*.

#### ⚠️ Finding 2 — the 26 Aug rebuild took the validation story off the slides, and carries four new exposure points

The deck was rebuilt on 26 Aug (28 pages, business-first — full map in §5). Audit findings:

- **The technical spine is gone from the slides.** No continuum slide, no ten-method benchmark, no
  circularity slide, no V1–V4 scorecard, no 23.4%/Unassigned-74% story, no Gulf finding. The deck
  argues value; **the science is now defended entirely in Q&A** — the question bank is the main
  event, not the safety net. Keep the old deck's continuum / honest-validation / Plan-B scorecard
  slides as **backup slides**.
- **On-deck contradiction:** slide 6's stat tile says **"10 commercial segments"**; slide 16 is
  titled **"11 Segments Identified"**. Fix the tile (11 named + Unassigned) or a panelist will do
  it for you.
- **The limitations slide (18) shrank to 4 owned + 3 in-flight** and dropped "labels add little
  incremental prediction" — previously called the single most likely question and deliberately
  owned on-slide. Q19 must now be answered from the manuscript record, not the slide. Also gone:
  ±1-booking reproducibility, revenue-mix-weaker-leg, V4 multi-seed. ("Possible Undetected
  Segment" survives and is the V3 blind-spot hook.)
- **New, repo-unsourced numbers now lead the deck:** $2.7M annual returns (benchmark case —
  carries three conditions), **$272K SaaS costs avoided** (reconstructable: cheapest vendor
  $350K+ minus the $77,904 build), **4,612 man-hours / $35,143 / 3 FTEs**, and the **$360k**
  Traveler DNA system cost. Each needs a one-line source card (§6.11, Q57).
- **Slide 13's PCA legend still shows v1 names** (Budget/Adventure, Family, Last-Minute) — the one
  stale figure that survived the rebuild. Re-render or own it verbally (finding replicates on v2,
  ARI *higher*: 0.389 vs 0.319).

*(Supersedes the 25 Aug finding about `clust_01` "≤ 0.34", the "stratified" caption and the
"20.6M flight rows" text — all three slides no longer exist in the rebuild.)*

#### Finding 3 — the methodology spec still says "45 segment pairs" in the Stage V1 section.

`methodology.md`'s non-circular-validation section describes V1 as "all 45 segment pairs" — the
10-segment-era count. The deck, brief and study guide all say **55** (11 named → 11×10/2). If a
panelist reads the spec: *"the stage description predates the v2 taxonomy; the shipped run tests
55 pairs and the changelog records the taxonomy change."* (Same class of ambush as §9 of the study
guide; this one wasn't on that list.)

### 3.2 Open items a well-read panelist can spring (know the disposition of each)

| Open item | Disposition to state |
|---|---|
| **"13-segment taxonomy" in PAL's 17 Aug approval record vs `SEG_APPROVED` = 12** | Reconciles only if the 13 counted Digital Nomad + Last-Minute, both removed 18 Aug. Flagged in the README; **confirm against the approval record before quoting any count to PAL** |
| **The "handover pack" sentence** (old deck's slide 23) | ✅ **Resolved 27 Aug** — `docs/handover-pack.md` now exists: runbook, retraining semantics, rule-change governance, two-week KT plan, roadmap. If asked, it can be shown |
| **`rule_confidence.py` figures (66.5% uncontested, Corporate most contested)** | Computed on **v1 labels**; the script still hard-codes the v1 waterfall. Honest answer: "not re-measured since the redesign; directionally it is why Corporate leads the SME sampling frame" |
| **Deck $311→$995 vs manuscript $322→$962** | Sampled vs population-exact fits; manuscript §4.2.5 names the discrepancy and declares the population fit authoritative |
| **Balikbayan/VFR sub-types are the least stable** | Split-half ARI 0.495 (sampled) and the two fits disagree on its sub-structure. Answer: sub-types are provisional, actionable partitions of a continuum — target with them, never score with them |
| **`Unassigned` is 76.7% premium-cabin at $179/booking in CY2025** | Not an error: the residual is algebraically "domestic premium-cabin travel with no branch" (domestic subset = premium subset = 94.5%). It **blocks lounge/premium policy until diagnosed**, and we say so |
| **`dest_region` is an alphabetical max** | 1.65% of bookings (377,331) carry a region that is not their final destination (SE Asia wins ties). Known edge, quoted not discovered; domestic 57.69% is exact and unaffected |
| **Multi-seed transfer spread still not implemented** | V4's transfer stage runs one seed, two methods. Recorded as in-flight work (off-slide since the 26 Aug rebuild); no refit-cadence claim is made anywhere |
| **The monitor's one RETRAIN flag** | `channel` PSI 0.4111, but **93% of it is NDC arriving from zero** (366,890 bookings in a channel that didn't exist); excluding new categories it is 0.0285 STABLE. Both verdicts print side by side |

### 3.3 The three load-bearing argument chains, and the attack on each link

**Chain A — the continuum.** *In one plain sentence: the customer base is a smooth blend, not
natural bunches — and we would have noticed bunches if they existed.*
*Claim:* no natural clusters exist in these features.
*Evidence stack:* Gower silhouette ceiling **0.381** across ten methods / six families (bar: 0.50)
→ BIC monotone **from k=1** → DB/CH/Euclidean-silhouette all agree, no interior optimum → SVC
emergent k=1; TDA-Mapper finds nothing; median cross-method ARI 0.41 → H0 homology consistent
(count retired as an instrument, the robust parts stand) → **detection power bounds it**: planted
segments recovered at ≥2% prevalence, so the nulls are about the data, not the instruments.
*Attacks:* "silhouette is depressed on mixed/one-hot data" → that is why there are six independent
method families and a detection-power test, not one index. "Your planted segments are convex
perturbations — a real segment could differ in a direction your features don't span" → correct, and
that is the stated form of the claim: **no segment *in these features*** at ≥2% prevalence; the
feature-dropout fragility (min ARI 0.15–0.49) is owned as a production risk. "Blind spots?" →
volunteered: below ~1% (~229k bookings) nothing is detected at any distinctness tested.

**Chain B — the validation.** *In one plain sentence: we drew the lines ourselves, so the burden
is proving the lines mean something on evidence we didn't control.*
*Claim:* the chosen boundaries are real and trustworthy to a stated degree. *Evidence stack:* circularity contract (raises, doesn't warn; catches semantic leaks) →
V1: 44/55 clearly distinct, median AUC 0.861 adaptive, **0 indistinguishable**, negative control
0.494–0.513 → V2: real signal (~0.60), ~zero incremental — by construction, owned in the
manuscript's limitations (the rebuilt deck dropped the bullet) →
V3: floors majority-rule, pre-registered thresholds → V4: shares hold (TVD 1.71 pp) on full
population. *Attacks:* "0.861 is cherry-picked" → it is the **median**, the bands are calibrated by
controls, and the strict column (0.637) is reported beside it with the reason it is thin. "55 tests
— multiplicity? intervals?" → single-seed point estimates with no intervals is **owned as the
seventh limitation** in the manuscript (census-vs-sample statement); the verdict never hangs on one
pair clearing a threshold by a hair, and the weakest boundary is disclosed, not hidden. "Your
weakest boundary didn't improve" → correct, on the slide: A/B 0.730 → 0.728, neutral, because the
change touched 1.4% of that branch.

**Chain C — the economics.** *In one plain sentence: the case is built so the go/no-go decision
doesn't require believing any forecast.*
*Claim:* implementing dominates doing nothing, without forecasting.
*Evidence stack:* measured exposure ($645.8M ≥1.25× parent mean; the department spreads) → actual
cost ($77,904) → breakeven 0.48% → sensitivity on what is still assumed (1.9% / 12.1%) → benchmark
NPV as conditional sizing only. *Attacks:* "the $16.1M pool is itself built on placeholders" →
yes, A8×A9 are placeholders on the **measured** $645.8M; that is why the conclusion is "the
decision does not depend on knowing the benefit", and why Marketing is nominated as the test site —
one instrumented campaign replaces the free parameter. "87.8% stability" → §3.1 Finding 1; use the
repaired line. "Your two cases disagree" → division of labour, never averaged.

---

## 4. Master numbers — one table, current to 25 Aug

**Bold** = changed or new since the study guide's memorize table.

| Number | What it is |
|---|---|
| 38,116,259 / 22,911,450 / 13,435,365 | coupons → bookings → customers (1.66 coupons/booking) |
| 11 + Unassigned (12 labels; 13 rows in `dim_segment` with export-only `Excluded`) | shipped taxonomy |
| 2.47% (was 9.58%) | Unassigned — a 74% cut |
| 23.4% (5,358,355) | genuinely reclassified — never 62.7% |
| 50.61% · $80 · 14.95% | Leisure share · mean rev/bk · revenue share |
| 12.53% · $615 · 28.41% | Balikbayan/VFR — the revenue engine |
| 1.50% · $1,188 / 0.69% · $1,968 | Premium Bleisure / Ultra Wealthy Leisure |
| 19.26% (4,411,666) | short-lead flag (segment only ever caught 2,945,686) |
| 0.381 | Gower silhouette ceiling, ten methods (bar 0.50) |
| **BIC monotone from k=1** (1,148,667 → 988,748 over k=1–4) | no elbow **at all** |
| **0.537 @ k=2 = geography** (ARI 0.909 vs `is_domestic`); ~0.39 customer-structure ceiling | the newest continuum number — never quote 0.54 unqualified |
| 44 / 55 clearly distinct · median AUC 0.861 adaptive (strict 0.637) · 0 indistinguishable | V1; negative control 0.494–0.513 |
| Corporate 6/10 · Leisure 5/10 | where the 11 weak V1 pairs concentrate |
| 0.548 / 0.713 / 0.72 / 0.730→0.728 | OFW–Balikbayan: strict / adaptive / isolated / A/B (neutral) |
| 0.598 / 0.604 · +0.0005 / +0.0024 | V2 label-alone AUCs · incremental over features (refund_any: never) |
| ≈0.494 @ 2% · ≈0.219 @ 5% · ≈0.13 @ 10% · never at 0.5–1% (~229k blind) | V3 majority floors |
| 1.71 pp / 3.36 pp · 8 of 12 labels stable carrying 98.1% | V4 share TVD / revenue TVD / composition |
| GMM 1.24 · LCA 0.89 (1.13 withdrawn) | V4 transfer ratios — the methods disagree; no refit-cadence claim |
| 5 parents × 4 = 20 sub-types; **21,725,296 bookings assigned via 17,847 cells** | level 2 — k=4 is the top of the search, never "BIC chose 4" |
| $311→$995 (deck, sampled) / **$322→$962 (manuscript, population)** | Balikbayan value span on booking horizon |
| 39 / 57 / 24 / 6 | SME rules returned / transcribed / questions answered / hard rules asserted |
| 43.6% / 70.5% | book where SME priors are silent / agreement where they speak |
| 19.11% vs 8.48% | Gulf 28–32-night share vs 12–16 (cause open — fare-rule confound) |
| $495–$9,784 | annual value at risk per customer (weights are a proposal) |
| **$2,535.0M** | CY2025 measured revenue (the only complete travel year) — USD confirmed 18 Aug |
| **$645.8M / $16.1M/yr / $77,904 / 0.48%** | dilution exposure / pool / actual year-1 cost / breakeven (1 in 207; stress 1.9% / 12.1%) |
| **~$2.7M/yr · +$7.3M NPV** | benchmark case — quote only with its three conditions |
| **$272K · 4,612 h / $35,143 / 3 FTEs · $360k** | the 26 Aug rebuild's new business numbers — derivations and source-card duty in §6.11 (Q57) |
| **87.8% → 53.4% → 38.6%** | segment_diversity=1: all / repeaters / 3+ bookings (§3.1 — use the repaired line) |
| 26.5% within 12 months (2024 Q2 cohort: 40.5%) | repeat rate — never "74% never return" |
| PSI 0.0028 · channel 0.4111 (93% = NDC) → 0.0285 excl-new | drift monitor |
| ±1 booking (1,830 tied keys) | reproducibility — cause named, fix drafted |
| **3,544 / 20.7M** | scorecard rows / fact_flight rows (study guide's 1,835 / 20.6M are stale) |
| 38,116,259 in = out | dashboard reconciliation, asserted every build |

**Never-say list:** unchanged from the brief and study guide §5 — 62.7% · 0.608→0.72 · 35.6%
Corporate short-lead (say 23.3%) · "MICE/UWL never book late" · Gulf *caused* by leave · 1.13
transfer · 0.114 detection · H0 count as a measurement · any accuracy % · refund_any · "BIC chose
four" · "the tiny segments drift" · coupon-grain lead figures (25 days / 13.3%) · "74% never
return" · "38.4% issued abroad" (bookings: 34.6%). **Add three: 0.54 without the geography
qualifier · 87.8% without the censoring caveat · $7.3M NPV without its three conditions.**

---

## 5. The deck — slide-by-slide context (26 Aug rebuild)

**Audited page-by-page against `CPT3_DefenseDeck_V3 1.pdf` (28 pages) on 26 Aug.** This is a
business-first restructure, not an edit: Executive Summary with the dollar value up front, EDA
compressed to four content slides, methodology to two, results to three, the **business case
expanded to five slides**, a **live Power BI demo**, and a timeline. The technical spine — the
continuum proof, the ten-method benchmark, circularity, V1–V4 — is **off the slides entirely**:
the deck argues value, and **the science is defended in Q&A only** (§6 is the main event). Owners
are no longer printed on the slides — re-split and re-time (§7).

Structure: Business framing (2–6) · EDA (7–11) · Methodology (12–14) · Results (15–18) ·
Business case (19–23) · Live demo (24) · Recommendations & conclusion (25–27) · Q&A (28).

| # | Slide (as built) | The claim → the proof | The trap |
|---|---|---|---|
| 1 | Capstone Final Defense | — team (Martin PL · Jeremy · Jadd · Josh), mentors, AIM Aug 2026 | intros under a minute |
| 2 | Business Context — About · Vision · Challenge | PAL ~16M pax/yr; industry pain is real → news: PAL $25M loss on fuel, Cebu Pacific ₱5.9B H1 loss, AirAsia PH ₱271.94M obligations | clippings are context, not our analysis — know each headline's date/source; don't over-claim PAL's financials |
| 3 | Executive Summary — Problem · Solution · Value | $2.7M annual returns · $272K SaaS costs avoided · 4.6k man-hours · 3 FTEs · Traveler DNA unlocked | **every number here needs its qualifier**: $2.7M is the *benchmark* case (three conditions); $272K = cheapest vendor ($350K+) − $77,904 build; man-hours basis is not in the repo — carry a source card (§6.11 Q57) |
| 4 | Day in a Life of an Airline Analyst | five departments decide segment-blind today → RM prices · Sales channels · Marketing promos · CX web/app & lounge · Loyalty churn | this is the do-nothing framing — if asked "which first": Sales/CX (no response assumption), Marketing test site, **Loyalty waits** (censored) |
| 5 | Proposed Solution — four deliverables | Semi-Supervised Model · Executive Dashboard · Technical Guide · Business Insight | **"Semi-Supervised" needs a one-liner** (§6.11 Q55): rules supply labels (weak supervision), unsupervised LCA refines, validation trusts neither |
| 6 | Converting 38.1M coupons into commercial segments | stat tiles: 38.1M · 22.9M · 13.4M · **10 commercial segments** · 40+5 features · 3 years · 1 EDW | ⚠️ **"10 commercial segments" contradicts slide 16's "11 Segments Identified" — fix the tile**; "3 years May '24–May '27" is *departure* coverage — issuance is truncated at both ends |
| 7 | EDA divider | — | — |
| 8 | Finding Booking Intent | coupon = flight segment; unique ID rolls 4 coupon rows into 1 purchase decision | the grain was tested, not assumed — 1.66 coupons/bk, 42.7% round-trip; one purchase = one purpose |
| 9 | Booking Lead Time — "The Average Customer Buys Late" | lead-time distribution, Last-Minute ≤3d marker | the 120-day pile-up is a **data cap**, not behaviour; booking grain: median 18 d, 19.26% ≤3 d — never the coupon-grain 25 d / 13.3% |
| 10 | Bookings Per Fare Brand — "Buys Cheap" | two cheapest brands = 63.1% of the network | 63.1% is `max_tier` (≡ value_band Budget); the 70.6% floating around is *any-cheap-leg* — different question |
| 11 | Bookings Per Region — "Domestic Leads by Volume, North America in Revenue" | the bookings-vs-revenue twin chart: domestic 58% of bookings, 19.3% of revenue; NA 8% → 35% at $1,141/bk | `dest_region` is an alphabetical max (1.65% known edge); Europe/South Asia 0% = no own-metal sectors, not no demand |
| 12 | Methodology divider | — | — |
| 13 | First Clustering Attempt | PCA overlap: LCA classes (k=9) vs rule segments, same cloud | ⚠️ **legend still shows v1 names** (Budget/Adventure, Family, Last-Minute) — re-render or own it (finding replicates on v2, ARI *higher*: 0.389); k=9 is the top of the search range; silhouette 0.091 Euclidean ≠ 0.381 Gower |
| 14 | PAL Guides, then Machine Learning | 5 stages: Source Extraction → Ingestion → Rule waterfall → LCA Refinement → BI | "so where's the ML?" — the benchmark, V1–V4 and monitoring are now **Q&A-only**: have Q7/Q58 cold |
| 15 | Results divider | — | — |
| 16 | 11 Segments Identified | the v2 table: Leisure 50.6/15.0/$80 · OFW 17.1/19.6/$312 · Balikbayan 12.5/28.4/$615 · OIL 9.5/14.0/$398 · Corporate 5.1/8.7/$460 · PB 1.5/6.6/$1,188 · UWL 0.7/5.0/$1,968 · micro 0.5/1.2 · Unassigned 2.5/1.6/$177 | the micro-segments row hides Mabuhay at 0.03% — the loyalty-gap caveat must be said; revenue is USD, confirmed 18 Aug; header contradicts slide 6's tile |
| 17 | Visualizing a Sub Segment: Balikbayan/VFR | Sankey: $995 (16.9%, 66 d) · $814 (13.8%, 131 d) · $482 (30.4%, 55 d) · $311 (38.8%, 26 d) — volume–value inversion inside one segment | never "BIC chose four" (k=4 is the search top); these are the *sampled* profiles — the manuscript's population fit ($322→$962) is authoritative; sub-types are **assigned on all 21.7M bookings** since 21 Aug |
| 18 | Limitations & Fixes | owned: no Mabuhay indicator · possible undetected segment · no ancillary · no demographics; in flight: fare/corporate codes · penalty weights · SME samples | "possible undetected segment" = the V3 blind spot — volunteer the floors (≥2% majority, blind <1%, ~229k); ⚠️ the **incremental-prediction limit is off the slide** — Q19 is answered from the manuscript now; ±1 booking and revenue-mix-weaker-leg also live off-slide |
| 19 | Business Case divider | — | — |
| 20 | Do Nothing vs Do Something | five-year benchmark: +$10.3M implement vs −$10.7M do nothing; RM +3% · Sales −40%/booking · Marketing 57% fewer discounts · CX +5.8% conversion; assumptions box: ~2% of IATA–McKinsey, $78k/yr cost | this is the **top-down** case — the three conditions travel with it; under pressure, pivot to the bottom-up **breakeven 0.48%** (the decision instrument); the per-department evidence is vendor case studies on *identified* customers |
| 21 | Buy vs Build Analysis | ~$77,904 build vs Salesforce $750K+ · Adobe $800K+ · Boxever $600K+ · Nevio blackbox · Hightouch $350K+ · Segment $400K+ | $272K on slide 3 = Hightouch $350K − our $77.9K; vendors' case studies run on identified customers — a bought platform inherits our anonymity ceiling; re-evaluation trigger = identity data |
| 22 | Traveler DNA | PAL's underutilized **$360k** profiling system (Altéa → CKC → Segmentation Studio → auto-assignment); the Studio filter is used by **one** SME | know the **source of $360k** before quoting it; the pitch is "our segments feed the existing system", never "replace it" |
| 23 | Man Hours Savings | 4,612 h/yr by department (RM 3,159 the bulk) · $35,143 · ≈3 FTEs | smallest lever — frame as "frees the analysts", not the business case; carry the derivation basis (not in the repo) |
| 24 | Power BI Dashboards — live demonstration | the star schema, live | fallback = recording tested on the venue machine; depth if probed: 38,116,259 in = out asserted, the four BI traps, no accuracy KPI by design |
| 25 | Recommendations & Conclusion divider | — | — |
| 26 | Recommended Timeline | H1 0–6 mo Quick Wins (refinement, governance, UAT) · H2 6–18 mo Scale (DS+DevOps, Azure ML, personalized offers) · H3 18–36 mo Augment (RM systems, Salesforce, hyper-personalization) | H2/H3 personalization is **conditional on identity data** — hold the data-before-algorithms stance; H1's real gates are SME labels + fare basis codes |
| 27 | Conclusion | 1 act on the segments · 2 enhance the model · 3 deploy it · 4 manage the dashboard | end there, no recap |
| 28 | Thank you — panel questions and discussion | — | backup slides ready (see below) |

**Backup slides to carry:** the old deck's continuum slide (ten-method sweep), the honest-validation
slide (circularity contract), and the V1–V4 scorecard (44/55) — the rebuild dropped them, and Q58
("did you validate?") is best answered with one on screen. The study guide's §6.1/§6.2 deep dives
were written for those dropped slides — still gold, but as Q&A material now, not per-slide scripts.

---

## 6. The panel question bank — by attack surface

Seasoned data scientists attack in a predictable order: rigor → design → circularity → the null
result → time → money → data → ethics → process. Drill each block out loud.

### 6.1 Statistical rigor

*What they're really testing: do you know the difference between a number and a measurement?
The through-line of every answer: we report point estimates, we said so in writing first, and no
conclusion hangs on any single number.*

**Q1. "You report 55 pairwise AUCs. Did you correct for multiple comparisons? Where are the
confidence intervals?"**
*Everyone can say:* We know these are estimates from single runs, and we said so in our own write-up before anyone asked. The safety net is a built-in blank test: we also scored pairs that should show nothing, and they showed nothing — so the results are not an artifact of the method.

*Full version:* No formal correction, and we own that: every sampled analysis reports single-seed point estimates,
which is the seventh limitation in the manuscript. (The worry is real: run 55 comparisons and a
few look good by luck alone.) Two things keep the conclusion safe — the negative control (each
segment split randomly in half, which *should* be indistinguishable) lands at 0.494–0.513, so the harness
manufactures nothing; and the verdict never rests on one pair clearing a band by a hair — the
median is 0.861 and zero pairs fall in the not-distinguishable band. A multi-seed spread is listed
as pre-handover work.

**Q2. "Where do your AUC bands — 0.60, 0.75 — come from?"**
*Everyone can say:* We didn't pick the cutoffs out of the air. We measured what “nothing there” scores and what “definitely there” scores on our own data, and set the bands between those two ends.

*Full version:* Calibrated, not asserted: a positive control — a pair we already know differs — sets the top of
the scale (0.641 on strict anchors after the `age_known` leak was fixed), and a negative control —
a random split that shouldn't differ at all — sets the floor at ~0.50. The bands sit between
those measured ends and belong to the adaptive column; quoting a strict number against them
understates our own result.

**Q3. "Your silhouette bar of 0.50 — says who?"**
*Everyone can say:* It's the standard textbook threshold — but we never relied on one measure. Five different measures all say the same thing: there is no natural grouping in this data.

*Full version:* The conventional Kaufman–Rousseeuw reading — above 0.5, each point is clearly closer to its own
group than to the next one; below it, the “groups” are a seating chart, not friend groups. But
the claim never hangs on one index: BIC is monotone from k=1, Davies–Bouldin sits at 2.6–3.0 everywhere, Calinski–Harabasz
declines monotonically, and four assumption-free tests (SVC, Mapper, homology, cross-method ARI)
agree. Every internal index that can be computed on this data fails to find a k.

**Q4. "TVD of 1.71 pp between windows — is that statistically significant?"**
*Everyone can say:* That number is computed on every booking, not a sample — so it isn't an estimate, it's a count. The segment mix moved by less than two percentage points in a year.

*Full version:* It is computed on the full population, not a sample, so there is no sampling error to test
against. (TVD 1.71 pp means: moving 1.71% of all bookings between slices would turn last year's
mix into this year's.) And we do not claim zero drift: the adversarial AUC — a classifier trying
to guess which year a booking came from — reads 0.62 against controls at 0.49/0.99, i.e.
real, mild shift that the segment shares absorbed. The claim is bounded, not absolute.

**Q5. "Your benchmark ran on 20–60k samples of 22.9M rows. Why should I trust sample-level
conclusions?"**
*Everyone can say:* The headline numbers are computed on all 22.9 million bookings. Samples were only used for the heavy experiments, and we say exactly which numbers came from samples.

*Full version:* Because the conclusions that matter are re-checked at the population where possible: shares, TVD
and the waterfall itself are full-population; level 2 is now fitted on the whole population via
the weighted cell table; and the manuscript carries a census-vs-sample statement naming exactly
which numbers carry sampling error. The 40k reservoir-sampling defect we found and fixed (2,077 of
40,000 rows returned under threading) is disclosed — we treat sampling as a risk, not a convenience.

**Q6. "Single seed, point estimates, and you withdrew a headline number this month. Why should we
trust the rest?"**
*Everyone can say:* We found the bug ourselves, retracted the number publicly, and changed the code so it cannot happen again. That is the strongest reason to trust the rest.

*Full version:* The withdrawal is the argument for trust: we found the 43% sampling bug ourselves, withdrew the
1.13 transfer ratio, grepped every generator so it cannot be re-emitted, and changed the script so
it now requires a majority of the panel rather than reporting the best method. A team that has
never retracted anything has usually never checked.

### 6.2 Design and methodology

*What they're really testing: did the design follow the data or a habit? Every answer traces to
one fact — the data has no natural clusters — so the structure had to come from the business and
be tested afterwards.*

**Q7. "So you didn't really use machine learning."**
*Everyone can say:* We used ten machine-learning methods to discover the most important fact in the project: this customer base has no natural clusters. Then ML got the jobs that finding supports — splitting big segments into sub-types, testing every boundary, and watching for change.

*Full version:* Ten methods across six families, scored on eight axes, established the most important fact in the
project — there are no natural clusters. Acting on that *is* the data science. ML then got the
three jobs a continuum supports: it sub-types the five biggest segments (now assigned on 21.7M
bookings), it tests every boundary on evidence the rules never saw, and it watches for drift.

**Q8. "Your model is a CASE statement."**
*Everyone can say:* On purpose. When there are no natural groups, an algorithm's boundaries are arbitrary and unexplainable. Business rules are auditable — and all the sophistication went into proving the rules draw defensible lines.

*Full version:* Deliberately — on a continuum, the labeller must be auditable and deterministic, because any
clustering forced onto a smooth cloud produces boundaries that look sophisticated and mean nothing.
The sophistication is in the machinery around the rules: the circularity contract, four validation
stages, detection-power bounds, and build-time assertions of PAL's own hard constraints.

**Q9. "Why is the waterfall not just weak supervision? A Snorkel-style label model would weight
your rules instead of hard-prioritising them."**
*Everyone can say:* That technique needs an answer key to learn from, and there is no answer key yet. We did the careful manual version: business priorities set the rule order, and PAL's own experts' rules agree with our labels about 70% of the time where they overlap.

*Full version:* The ingredients are the same — labelling functions, priors, agreement statistics — but a label
model needs either ground truth or rule-agreement structure to estimate weights, and we have no
ground truth yet. What we did instead: priority order settled by business precedence with PAL,
rule competition measured (66.5% of bookings matched exactly one rule on v1), and the 21 SME soft
tendencies scored against the labels (70.5% agreement where they speak) without changing any. When
SME labels land, re-weighting the rules becomes estimable — that is Plan A's second dividend.

**Q10. "Why eleven segments? Why not seven, or twenty?"**
*Everyone can say:* The data doesn't pick a number — the business does. It started at ten from the requirements and became eleven through PAL's own decisions. Then we tested every boundary: 44 of 55 clearly hold up.

*Full version:* On a continuum the count must come from the business — the data offers no k (BIC monotone from
k=1). It started at ten from the requirements and moved to eleven through PAL's own rules and
answers: four added, three retired for cause. The validation then tests the *chosen* lines: 44 of
55 clearly distinct.

**Q11. "Why booking grain and not customer grain?"**
*Everyone can say:* One purchase is one trip purpose. Most customers appear only once in our data anyway, so the booking is the honest unit — we roll up to customers afterwards.

*Full version:* One purchase decision has one purpose; a customer over years has many. 74% of customers appear
once in our window, so a customer profile for most of the base is their single booking restated —
and even at the 40% repeat rate of the earliest full cohort, purpose still belongs to the purchase.
We model 22.9M bookings and roll up to 13.4M customers afterwards, with each grain change asserted.

**Q12. "GMM won your benchmark. Why is LCA still in the pipeline?"**
*Everyone can say:* The two tools won different contests. GMM won at top-level grouping, but that isn't its job here — LCA's job is splitting inside a segment, and we won't swap tools until they compete on the actual job.

*Full version:* Because the benchmark scored *top-level* segmentation and LCA's job is *sub-segmentation inside a
parent* — a different stage. Swapping on an unmatched test would be the same mistake as quoting the
luckiest detection cell. The stage-matched re-test — the same head-to-head, but on the job LCA
actually does — is specified; until it runs, GMM is our best
measuring instrument and LCA is the refinement layer.

**Q13. "Why not a learned embedding — UMAP + HDBSCAN, or a deep model?"**
*Everyone can say:* It's on the roadmap with strict go/no-go rules. But ten very different methods all hit the same ceiling, which tells us the limit is in the data we have, not in the algorithm. New data beats new math here.

*Full version:* It is on the roadmap as a gated experiment with a pre-registered decision rule and a stop
condition (`continuum-levers-plan.md`). But ten methods spanning radically different inductive
biases all hit the same ceiling, which says the ceiling is in the features, not the method — so
data investments (loyalty tier, fare basis, ancillary) rank above algorithm work.

**Q14. "Why did you drop HDBSCAN after building your prototype on it?"**
*Everyone can say:* That algorithm looks for crowds separated by empty space. In the real data there is no empty space, so it had nothing to find. We kept the prototype for the record and quote nothing from it.

*Full version:* The real extract is categorical-heavy and not density-separable — there is no empty space between
crowds for a density method to find. Not the algorithm's fault; there is nothing for it to find.
The prototype survives as the reference implementation and no number from it reaches a deliverable.

**Q15. "Four sub-types per parent — how was that chosen?"**
*Everyone can say:* Four wasn't discovered — it's the most our search allowed, and the data would happily have taken more. So twenty sub-segments is a choice we own, exactly like the eleven segments.

*Full version:* It wasn't discovered, and we say so: the search ran k=2–4 and BIC wanted the maximum in all five
parents — the continuum again, one level down. Twenty cells is a granularity we own, the same way
the eleven segments are. What *is* a finding: every parent independently splits on the same three
axes — direction × timing × fare tier.

### 6.3 Circularity and validation

*The deepest trap in the project: the rules made the labels, so any score computed from the
rules' own inputs is the model grading its own homework. Every answer shows where the independent
evidence came from.*

**Q16. "Isn't validating rules with the data that built them circular?"**
*Everyone can say:* Completely — which is why we never grade the rules with their own ingredients. The code physically blocks it: validation can only use fields the rules never touched.

*Full version:* Completely — which is why we never do it. A code contract lists every field the rules consumed and
raises an error, not a warning, if validation touches one. It also catches disguised leaks:
`dest_region == 'Domestic'` *is* the domestic rule bit in finer clothing, so it is disqualified
exactly where that bit is the boundary under test. And it is why no accuracy number ships anywhere.

**Q17. "But your 'admissible' anchors still correlate with rule inputs. Departure month correlates
with pilgrimage season. Isn't that indirect leakage?"**
*Everyone can say:* There's a difference between a field that IS the rule in disguise — banned — and a field that is merely related to real behaviour — which is exactly the independent evidence we want. And the blank test proves the setup cannot invent differences that aren't there.

*Full version:* Correlation through *behaviour* is the whole point of construct validity — if segments are real,
independent evidence should differ across them. Leakage is *mechanical identity*, and that is what
the contract removes (a field that equals a rule input under coarsening). Two guards for the
seasonality case specifically: a base-rate-normalised `dep_month` robustness check (most segments
peak in May regardless), and the negative control proving the harness cannot manufacture
separation from these anchors.

**Q18. "Median 0.861 — your best number?"**
*Everyone can say:* It's the middle value of all 55 comparisons, not the best one — and we volunteer where the weak spots are: Corporate and Leisure.

*Full version:* The median of 55, not the maximum; zero pairs are indistinguishable; the negative control sits at
~0.50. And we volunteer the weak tail: eleven weak pairs, concentrated on Corporate (6) and
Leisure (5) — which independently agrees with the rule-competition diagnostic that Corporate is the
most contested label. Two methods agreeing on where the softness is, is the strongest kind of
result.

**Q19. "Your labels add nothing predictive."** *(the single most likely question)*
Confirmed, measured, and owned — in the manuscript's limitations (the rebuilt deck no longer
carries the bullet, so the answer stands on the record, not the slide). The label alone carries
real signal — 0.598 and 0.604 against a 0.50 coin flip — but adds +0.0005 to +0.0024 on top of the
raw features, because the label is *made* of those features: a compression cannot beat its source.
The deliverable's value is a shared vocabulary and targeting, not prediction, and we priced it
accordingly.

**Q20. "What's your accuracy?"**
*Everyone can say:* There is no honest accuracy number yet, on purpose — any number today would be the rules grading themselves. PAL's experts hand-labelling about a thousand bookings unlocks the real one.

*Full version:* *Everyone can say:* Correct, and we measured it ourselves. The labels are built from the data, so they can't beat the data at prediction. Their value is that a pricing analyst, a marketer and a dashboard all mean the same thing by “Balikbayan” — a shared language, not a crystal ball.

*Full version:* No honest accuracy figure exists yet, by design — every one computable today would grade the rules
against themselves. The SME gold sample (~1,000 bookings, inter-rater kappa) unlocks a real figure;
contested boundaries — Corporate first — are the sampling frame.

**Q21. "Who validates the rule thresholds — lead ≤ 3 days, tiers 1–2?"**
*Everyone can say:* We wiggled every cutoff to see how many labels flip. Most barely move anything; the one that did — the 3-day last-minute cutoff — is a big part of why Last-Minute became a flag instead of a segment.

*Full version:* Boundary-fragility diagnostics: move each threshold a notch and count label flips. The Corporate
7-day cut is nearly inert (0.15–0.17%); the Last-Minute 3-day cut was the most consequential
arbitrary number in the model (widening to 7 days relabels 8.57% of the book) — which is part of
why Last-Minute is now a flag, not a segment. Thresholds with owners, not folklore.

**Q22. "What happens if one of your controls fails?"**
*Everyone can say:* The system stops loudly instead of continuing quietly. And one of our own instruments did fail its test — we retired it and corrected the earlier report that had used it.

*Full version:* The circularity guard raises a `CircularityError`; the construct harness reports its negative
control first with the sentence "if this is not ≈0.50, every number below is void." One instrument
did fail its control — the H0 component count, 2–131 on unchanged data — and we retired it and
re-qualified the earlier report that used it.

### 6.4 The continuum and the null result

*“You claim nothing is there. Prove you could have seen something.” The stack: many unrelated
instruments agreeing, plus a fire drill — planted segments — proving the instruments work.*

**Q23. "How do you know clusters don't exist rather than that you missed them?"**
*Everyone can say:* We ran a fire drill: we hid fake segments inside the real data to see whether our methods would find them. They do, down to 2% of bookings. So finding nothing in the real data means something. Below 1% we're blind — and we say so.

*Full version:* We planted artificial segments in the real data and measured whether our own panel recovers them.
At ≥2% of bookings, a majority of methods finds them (distinctness ≈0.494), at 5% (≈0.219), at 10%
(≈0.13). So when the same panel finds nothing in the unplanted data, that is evidence about the
data. Below ~1% we are blind — ~229k bookings — and that bound travels with the claim.

**Q24. "Your planted segments are neat geometric perturbations. A real segment could be messier —
or live in features you don't have."**
*Everyone can say:* True, and we state it: a real hidden group could be messier, or could live in data we don't have — which is why our top recommendation is new data, not more algorithms.

*Full version:* Both true, both stated: the floors are optimistic because a planted group is internally coherent,
and the claim is explicitly "no segment *in these features*". A loyalty tier or ancillary spend
could reveal structure these forty columns cannot — that is why the top-ranked recommendation is
data investment, not more clustering.

**Q25. "You found ARI 0.54 at k=2 — doesn't that contradict 'no structure'?"**
*Everyone can say:* When forced to make just two groups, the algorithm rediscovers domestic versus international — something everyone already knows. Beyond that, the machines find none of our finer boundaries.

*Full version:* No — we probed the cut's composition: it is the domestic/international split rediscovered
(ARI 0.909 against that single bit), and agreement *falls* toward the taxonomy's own cardinality.
Unsupervised methods recover the taxonomy's geographic spine and none of its finer boundaries —
which is the continuum finding stated more sharply, not a contradiction of it.

**Q26. "Is one mass or two? Did you ever test k=1?"**
*Everyone can say:* Yes — the test now starts from “is this even one group or two?” The answer: not even two. There is no natural number of groups at all.

*Full version:* Yes — as of 23 Aug the sweep extends to k=1, and BIC — a fit score with a built-in fine for
complexity, which should drop sharply at the true group count and then level off — declines
smoothly from one component:
there is no elbow at 2 either, and each added class buys less than the one before. "No natural k"
is now measured from the ground up.

**Q27. "Ten methods agreeing could mean ten methods sharing a blind spot."**
*Everyone can say:* The ten methods were picked precisely because they make different assumptions — and the fire drill proves the toolkit can see a group when one actually exists.

*Full version:* The families were chosen to *not* share assumptions: centroid, mixture-model, graph-spectral,
boundary-based (SVC), topological (Mapper, homology) — plus the detection-power test, which is
method-independent evidence that the panel can see a group when one exists. And the SVM probe cuts
the other way: it scores 0.85–0.99 even for methods with silhouette ≈0.1, which taught us that
separability without separation is exactly the illusion to guard against.

### 6.5 Temporal stability and drift

*Everything above could be true of one lucky snapshot. These ask whether it survives time.
Honest scoreboard: composition yes, revenue mix mostly, model transfer unresolved.*

**Q28. "Will this hold next year?"**
*Everyone can say:* Sizes held over a year — less than two percent of the mix moved. The money side moved a little more, so we watch value, not just headcount.

*Full version:* One twelve-month step says yes on composition: shares hold at TVD 1.71 pp — only 1.71% of the mix
moved — on the full population,
8 of 12 labels stable carrying 98.1% of bookings. Revenue mix is the weaker leg — 3.36 pp, with
Balikbayan/VFR falling 29.35% → 26.64% of revenue on flat headcount — so a segment holding its size
is not evidence its value held, and we watch that.

**Q29. "Your two transfer methods disagree — 1.24 vs 0.89. Doesn't that undermine V4?"**
*Everyone can say:* Two tools gave two different readings on one narrow question, so we simply make no claim on that question until it's re-run properly. The main result doesn't depend on it.

*Full version:* It bounds it. The composition result is full-population and does not depend on transfer at all.
The transfer stage runs one seed on a two-method panel — thin by construction — so no refit-cadence
claim is made anywhere, and the multi-seed spread is listed as in-flight pre-handover work
(off-slide since the 26 Aug rebuild).

**Q30. "Your drift monitor fired RETRAIN. What did you do?"**
*Everyone can say:* The alarm went off because PAL launched a whole new sales channel (NDC) mid-year. The alarm correctly noticed a real change — just not misbehaviour. Excluding the new channel, everything is stable.

*Full version:* Decomposed it before acting. (PSI is a drift alarm: it scores how much an input's distribution
moved between two windows.) 93% of the channel alarm is NDC arriving from zero — a channel PAL
switched on mid-window, not behavioural drift. Excluding new categories the same feature reads
0.0285, stable. The report prints both verdicts; a new-category alarm and a drift alarm need
different responses, and retraining on a distribution change we *caused* would have been the wrong
move.

**Q31. "What breaks your segmentation — a competitor, a fare-structure change?"**
*Everyone can say:* Then the input data shifts and the monitoring alarm fires — that is exactly what it's for. We claim stability for the year we tested, nothing beyond it.

*Full version:* Anything that moves the input distributions — and that is what the PSI monitor is for. We tested
one 12-month step inside one extract; we claim nothing about structural shocks, and the drift alarm
is the honest substitute for a claim.

### 6.6 Economics and the business case

*Money questions fail two ways: invented uplifts and hidden assumptions. The defense: a breakeven
so small it needs no forecast, and every assumption in a table where a skeptic can replace it.*

**Q32. "Your breakeven denominator — the $16.1M pool — is built on invented parameters."**
*Everyone can say:* The exposed money — $646M priced well above its segment average — is measured. Only how much of it a campaign can claw back is assumed, and the cost is so small that recovering half a percent already pays for everything. The first real campaign replaces the guess with a measurement.

*Full version:* Correct, and the document says so in its own §5: penetration and depth are placeholders applied to
the **measured** $645.8M exposure. That is why the conclusion is "the decision does not depend on
knowing the benefit": halve both placeholders and breakeven is 1.9%; add market-rate staffing and
it is 12.1%. And why Marketing is the nominated test site — one instrumented campaign replaces the
free parameter with a measurement.

**Q33. "Your two business cases disagree on cost and revenue base."**
*Everyone can say:* One is a measurement, one is an industry benchmark. We make the decision with the measured one — it needs almost nothing to be true — and use the benchmark only to show how big the prize could be.

*Full version:* By design, and we never average them: the bottom-up measured case is the decision instrument
(breakeven), the top-down benchmark case is conditional sizing (~$2.7M/yr, +$7.3M NPV). The
benchmark case carries three conditions from our own results — its ancillary lever rests on revenue
the extract doesn't contain, its churn lever needs identity the data lacks, and its $1.96B base is
a third below the measured figure.

**Q34. "87.8% of customers stay in one segment — impressive. How many of those book once?"**
*Everyone can say:* Fair catch — most customers only book once, so of course they stay in one segment. Among people we see repeatedly, about half stay in one segment, still well above chance. And the label describes the trip first, the person second.

*Full version:* *(the trap — answer before they finish)* 73.9%, so the honest figure is the repeat-customer one:
53.4% of customers we observe more than once stay in a single segment, against a ~31% independence
baseline — about 1.7× chance. The person-level claim rests on the *dominant* segment, which ships
as its own field, and the segment label is a booking-level fact first.

**Q35. "Why is Loyalty told to wait when churn is the classic segmentation use case?"**
*Everyone can say:* You can't measure customer loss when 74% of customers appear only once — a brand-new customer and a lost one look identical in our window. We'd rather say “wait for the loyalty data” than sell an illusion.

*Full version:* Because no churn rate exists in this data: 73.9% of customers have one booking and tenure zero, so
a new customer and a lost one are identical — right-censored. The between-segment *ordering* of
repeat floors (12.2% to 36.4%) is informative; the levels are not. Saying "wait for the loyalty
join" is part of the honest case.

**Q36. "What does a misclassification cost?"**
*Everyone can say:* Between roughly $500 and $10,000 per customer per year depending on the segment, built from published airline research plus our own measured numbers. PAL still has to sign off on the weights.

*Full version:* $495 to $9,784 per customer per year depending on segment, from five sourced cost components plus
our measured economics in confirmed USD. The previous ladder was penalty × $4,000 and inverted
against measured revenue in two places. PAL asked to see a scored run before agreeing weights — so
they ship as a proposal.

**Q37. "Can RM set fares with this tomorrow?"**
*Everyone can say:* Not pricing yet — the labels haven't been checked against expert judgement. Today it is reliable for reporting, prioritising and targeting.

*Full version:* Not pricing, not yet — labels are unverified against ground truth. Today it is solid for reporting,
targeting and prioritisation; Sales and CX can act on measured facts alone. The pricing path needs
the SME sample plus one instrumented campaign.

### 6.7 Data quality and engineering

*At 38 million rows, every aggregate is a claim. These answers show assertions and cross-checks
doing the work that eyeballing can't.*

**Q38. "Is the pipeline reproducible?"**
*Everyone can say:* Yes — to within one booking in 22.9 million, and we can even name why those few flip. Everything is scripts; there are no manual steps in the labelling.

*Full version:* To within one booking in 22.9 million, and we can name the booking — 1,830 rows carry tied sort
keys; cause identified, fix drafted. Every stage is one script writing a checkable report; the
labeller is deterministic, so drift can only enter through the input data, which the monitor
watches.

**Q39. "How do you know your aggregates are right at 38M rows?"**
*Everyone can say:* The build checks itself: rows in must equal rows out, or it refuses to finish. And our worst bug was caught exactly by that kind of cross-check — not by eyeballing.

*Full version:* Assertions and cross-checks, not inspection: the export asserts coupons in = coupons out
(38,116,259), the scorecard must tie to the fact table or the build fails, and independent
recomputation caught our worst bug — a revenue filter that silently halved Balikbayan/VFR (−54%)
was found because the means contradicted a separately-computed table by 2×; corrected, they agree
within ~7% across eleven segments.

**Q40. "Your trends fall off a cliff at the end."**
*Everyone can say:* Recent months look low only because those trips haven't flown yet — bookings are still arriving. The dashboard hides incomplete months by default.

*Full version:* They don't — recent travel months are forward book still filling (Sep-2026 holds ~22% of a mature
month). The extract is departure-filtered, so the dashboard defaults every trend visual to
complete travel months, and V4's windows were designed inside the censoring-safe region for the
same reason. Naive calendar windows would have faked a lead-time collapse.

**Q41. "Age is 57% missing. How do you model with that?"**
*Everyone can say:* Mostly by design — children and infants. The pattern of what's missing actually carries information, so we treat it carefully; we even banned one field from validation because its gaps mirrored one of the rules.

*Full version:* The missingness is by design (infants/children mostly) and it is MNAR — missing *not* at random,
meaning the gap itself carries information: age is known on 0.86% of domestic bookings against
87.62% of international — and that is exactly why `age_known` was demoted from the anchor set: it
was a near-copy of a rule field. Where age is used, the gradient-boosting handles NaN natively, so
the pattern is modelled rather than imputed away.

**Q42. "What's the ugliest data decision you made?"**
*Everyone can say:* Trips that touch several countries get filed under one region alphabetically — it affects under two percent of bookings, and we quote it before anyone finds it.

*Full version:* `dest_region` on multi-region trips is an alphabetical max — 1.65% of bookings carry a region that
isn't their final destination. Measured, quoted as a known edge, not worth a pipeline re-run, and
the domestic split — which is load-bearing — is exact. Second candidate: stay_nights is NULL on
one-ways *by definition*, and the build asserts that, because its missingness pattern *is* the
round-trip rule bit.

**Q43. "One data fact that changed your analysis?"**
*Everyone can say:* The extract is cut by flight date, not purchase date. It sounds subtle, but it invalidates naive year-over-year comparisons and shaped our whole time analysis.

*Full version:* The extract is filtered on departure date, not issuance. That single fact invalidates naive
calendar-year comparisons (a fake lead-time collapse), forces the V4 window design, and censors
every outcome field near the boundary. It is recorded in the methodology so no future analysis
trips on it.

### 6.8 Delivery, maintenance, governance

*“What happens when you leave?” Deterministic rules, builds that fail loudly, and caveats that
travel with the data instead of living on a slide.*

**Q44. "Who maintains this after you leave?"**
*Everyone can say:* PAL's BI team. It's rules in a scheduled database job — no model server, no retraining, a build that fails loudly, and a drift alarm.

*Full version:* PAL BI, and it is built for that: deterministic rules (a SQL job, no model server), a build that
fails loudly if reconciliation breaks, hard SME rules asserted from PAL's own CSV so code and rules
cannot drift apart, a drift monitor as the tripwire, and Trust/DataCaveat governance columns that
travel with every persona card.

**Q45. "Why does the dashboard ship no accuracy KPI?"**
*Everyone can say:* Because any accuracy number today would be self-graded, and a number on a dashboard tile outlives its caveat.

*Full version:* Because any figure computable today is circular, and a printed accuracy number would outlive its
caveat. The scorecard ships additive counts only; shares are DAX measures because a share is only
valid in the filter context that computed it.

**Q46. "Why keep Mabuhay Loyalist at 0.03% if it's unmeasurable?"**
*Everyone can say:* We kept it visible on purpose — deleting it would hide the fact that we can't see loyalty at all. It's the loudest data request we have.

*Full version:* To keep the gap visible. Deleting it would hide the fact that the extract has no loyalty field;
keeping it with `Trust = low` and its DataCaveat on the card makes the missing join the loudest
data request on the table. The segment is real — our ability to see it is not.

**Q47. "What was delivered vs promised?"**
*Everyone can say:* Everything promised was delivered or openly redesigned — and each redesign happened because the data demanded it, recorded at the time it happened.

*Full version:* Every promised item delivered or redesigned openly — the redesigns are the finding. The TOR's
clustering model became rules-plus-validation because the data demanded it; the risk register
recorded each pivot when it happened, with evidence attached.

### 6.9 Ethics and responsible use

*The line to hold: we classify trips, not people. Say plainly what the anonymous lens cannot see,
and where PAL's own governance takes over.*

**Q48. "Your Pilgrimage segment infers religion from routes. Your OFW segment tracks migrant
workers. Is this appropriate?"**
*Everyone can say:* The labels classify trips on anonymous data — routes and seasons PAL already plans around — never identities. Any pricing use goes through PAL's own review, and every persona card carries a “what not to do” warning.

*Full version:* The segments classify *trips*, not persons, on anonymous data — no names, no identity join, and
the pilgrimage rule is a route/seasonality fact (Jeddah/Medina), the same one PAL's network
planning already uses. The governance line: these labels prioritise service and capacity, and any
use in *pricing against* a segment is a PAL policy decision that should go through their fairness
review — the persona cards carry WhatNotToDo fields for exactly this reason.

**Q49. "Could segment-based pricing be discriminatory?"**
*Everyone can say:* The value axis is PAL's existing fare ladder — the segmentation doesn't create price discrimination, it shows where treating everyone identically mis-serves them. Our recommendations lead with service and channels, not pricing.

*Full version:* The value axis is the fare ladder PAL already sells — the segmentation doesn't create price
discrimination, it reveals where uniform treatment mis-serves. The recommendation set deliberately
leads with non-pricing uses (channels, CX, targeting), and misclassification costs are published so
the harm of a wrong label is explicit rather than hidden.

**Q50. "Privacy?"**
*Everyone can say:* No names, no contact details, no payment data anywhere — the design assumes anonymity rather than working around it.

*Full version:* No names, contacts or payment data anywhere; the customer key arrives anonymised; age is 57% NULL
and gated behind an explicit flag. The whole design is Sabre's anonymous lens — the constraint we
built inside, not around.

### 6.10 Process and meta

*Character questions. The audit trail is the answer: dated retractions, documents allowed to
disagree on purpose, and pre-registered kill conditions.*

**Q51. "Your own documents contradict each other."**
*Everyone can say:* They are a dated diary, kept on purpose. When documents disagree, the newest binding one wins — and we hunt the differences with scripts, not memory.

*Full version:* They are a dated audit trail, deliberately kept: a living learning log, versioned changelogs, and a
stale-figures register that we maintain because we *expect* older documents to age. When a document
and the deck disagree, the defence brief is binding — and finding those disagreements is a chore we
do programmatically, by diffing guides against the artifacts they describe.

**Q52. "What would change your mind about the whole design?"**
*Everyone can say:* Expert labels disagreeing with a rule, a boundary failing on independent evidence, or instability over time — each one has a test watching for it.

*Full version:* Expert labels disagreeing systematically with a rule; two segments proving indistinguishable on
independent evidence; a boundary unstable across time; or a planted-segment test failing its
controls. Each has a stage watching for it, and the policy is fixed: an unsupported split becomes a
proposal to PAL with evidence attached, never a unilateral change.

**Q53. "What did you get wrong?"**
*Everyone can say:* Three bugs — all found by us, all disclosed, all fixed at the source. The fact that our system makes mistakes findable is the real deliverable.

*Full version:* Three things we found ourselves: a sampling bug that silently ran an analysis on 43% of its
intended rows — headline withdrawn, script now majority-rule; an instrument that failed its own
control — retired; and a revenue filter that halved a segment — caught by cross-check, documented
as a warning for PAL's BI team. The project's real deliverable is that these are *findable* in our
system.

**Q54. "If you had three more months?"**
*Everyone can say:* The expert-labelled sample first, one measured marketing campaign second, the loyalty data third. Data before algorithms.

*Full version:* The SME gold sample first — it converts every circular metric into a real one and re-weights the
rules. Then one instrumented marketing campaign to replace the recovery-rate assumption with a
measurement. Then the loyalty join, which unlocks Mabuhay, churn, and the vendors' strongest
levers simultaneously. Data before algorithms, in that order.

### 6.11 Asked off the 26 Aug rebuild

*Numbers that walked onto the slides after the documents froze. Each needs its derivation in one
breath — or it becomes the panel's favorite loose thread.*

**Q55. "Your solution slide says 'Semi-Supervised Model'. What exactly is semi-supervised here?"**
*Everyone can say:* The rules act as the teacher, the algorithms study under them, and the audits check the teacher. If pressed for a textbook phrase: rule-based labels with machine-checked boundaries.

*Full version:* The labels come from business rules — programmatic weak supervision — and the model layers around
them are unsupervised: LCA refines below the rules, and a four-stage validation harness tests the
boundaries on evidence the rules never consumed. "Semi-supervised" is the closest standard term
for that hybrid; stated precisely, it is rule-based labelling with model-based refinement and
validation, and no stage treats the labels as ground truth — which is why no accuracy figure ships
anywhere.

**Q56. "One slide says 10 commercial segments, another says 11. Which is it?"**
*Everyone can say:* Eleven segments plus an “Unassigned” leftover bucket. The tile is a stale count — our mistake, and the table is the correct one.

*Full version:* Eleven named segments plus an honest Unassigned — the shipped taxonomy, verified in the built
table and the palette code. The tile is a stale count from the original ten-segment requirement
and we own that. *(Fix it before Thursday and this question never happens — checklist item 1.)*

**Q57. "Where do $2.7M, $272K, and 4,612 hours actually come from?"**
*Everyone can say:* Three separate things. The $2.7M is an industry-benchmark scenario with our stated caveats. The $272K is simply the cheapest vendor's price minus our actual cost. The man-hours are the team's estimate of analyst time freed, from the companion workbook. None of them decides the case — the payback math does.

*Full version:* Three different instruments, kept deliberately apart. **$2.7M/yr** is the top-down benchmark case —
levers modelled at ~2% of the IATA–McKinsey industry pool, taken at 30% contribution margin with a
70% realization haircut — and it carries three conditions from our own data: the ancillary lever
rests on revenue the extract does not contain, the churn lever needs identity the data lacks, and
its revenue base is a third below the measured figure. **$272K** is the buy-vs-build delta: the
cheapest comparable vendor at $350K+/yr against our $77,904 actual build. **4,612 hours / $35,143 /
3 FTEs** is the analyst-time estimate by department (RM carries 3,159 of it) — its basis lives in
the companion workbook, not the repo, so whoever presents it must carry the one-line derivation.
And the decision rests on none of these: the bottom-up breakeven is 0.48% of one measured exposure.

**Q58. "There is no model validation anywhere in this deck. Did you validate?"**
*Everyone can say:* Yes — four different ways, kept off the slides on purpose. The segments differ on evidence the rules never used; they hold up a year later; hidden test-segments prove our methods can find groups when they exist; and a strict firewall stops us from grading our own homework. We carry a backup slide, and we can go as deep as the panel wants.

*Full version:* Extensively — it is off the slides by design, not omission, and here is the one-minute version:
four label-free stages behind a circularity contract that raises rather than warns. Construct: 44
of 55 segment pairs clearly distinct on fields no rule consumed, median AUC 0.861, zero
indistinguishable. Criterion: the label carries real signal alone (~0.60) and adds almost nothing
over the raw features — expected for a compression, owned as a limitation. Detection power:
planted segments recovered from 2% prevalence, so the "no clusters" result is about the data, not
our instruments — blind below ~1%, and we say so. Stability: shares hold within 1.71 pp across a
twelve-month step. Backup slide available. *(Have it ready — this is the likeliest technical
opener given the rebuilt deck.)*

---

## 7. Action checklist before Thursday

1. **Fix slide 6's "10 commercial segments" tile → 11** (or drop the tile). It contradicts
   slide 16's own title, and a panelist will spot it in seconds (§3.1 Finding 2).
2. **Rehearse the "Semi-Supervised Model" one-liner** (slide 5, Q55) — a methods purist will probe
   the term.
3. **Build source cards for the rebuild's new numbers**: $2.7M (benchmark + its three conditions),
   $272K (= cheapest vendor $350K − $77,904 build), 4,612 h / $35,143 / 3 FTEs (basis is in the
   companion workbook, not the repo), and the **$360k** Traveler DNA system cost — one line each:
   who computed it, from what (Q57).
4. **Slide 13 PCA legend still shows v1 names** — re-render from the 23 Aug v2 figure or own the
   caveat verbally (finding replicates on v2, ARI higher: 0.389).
5. **Prepare backup slides**: the old deck's continuum sweep, honest-validation, and V1–V4
   scorecard slides — Q58 is best answered with one on screen.
6. **Re-split owners and timing across the 28 slides** — the rebuild no longer prints presenter
   names, and the old budget (Martin 8 · Josh 20 · Jadd 7) doesn't map onto a deck whose center of
   gravity moved to the business case.
7. **Fix or rehearse the 87.8% line** (§3.1 Finding 1) — anyone presenting the department/do-nothing
   material must know 53.4% / 38.6% cold.
8. **Confirm the 17 Aug approval record's "13-segment" wording** before quoting any taxonomy count
   back to PAL.
9. **Copy the final deck into `assets/final-defense/`** — the repo still holds the superseded
   20 Aug pptx, and the audit trail should end on what was actually presented.
10. Mock session: 30 minutes hostile Q&A from §6 in random order — **Q1, Q19, Q23, Q25, Q32, Q34,
    plus the new Q55–Q58 at minimum**. Q58 first: it is the likeliest opener for this deck.
11. Night before: the brief's what-to-say / never-say lists, plus the three qualifier rules (0.54 ·
    87.8% · $7.3M) and the Q19 change — the incremental-prediction limit is answered from the
    manuscript now, not the slide.

---

*Sources: `docs/defense-brief-2026-08-18.md` (binding) · `docs/defense-study-guide.md` ·
`docs/methodology.md` v1.12 · `docs/do-nothing-vs-implement.md` · `docs/business-case-benchmark.md`
· `docs/knowledge-base.md` §15 (entries through 23 Aug) · `outputs/` stage summaries · 25 Aug
DuckDB probe of `data/interim/pal_features_customer.parquet` (§3.1) · 26 Aug page-by-page audit of
`CPT3_DefenseDeck_V3 1.pdf`, the 28-slide rebuild (§5). Last updated: 2026-08-26.*
