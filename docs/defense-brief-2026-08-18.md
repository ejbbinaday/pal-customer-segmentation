# Results summary — state of the model, 18 August 2026

Everything below is measured on the full **22,911,450-booking** extract with the taxonomy PAL settled on
17–18 August. Revenue is **USD** (confirmed by PAL, 18 Aug — the first time we have had that confirmed).

---

## 1. The taxonomy, as shipped

**11 segments + `Unassigned`.** Four added, three removed against the original ten.

| segment | bookings | share | mean rev/booking | share of revenue |
|---|---|---|---|---|
| Leisure *(was Budget/Adventure)* | 11,595,711 | 50.61% | $80 | 14.95% |
| OFW/Migrant | 3,907,805 | 17.06% | $312 | 19.64% |
| Balikbayan/VFR | 2,871,255 | 12.53% | $615 | **28.41%** |
| **Outbound International Leisure** | 2,182,074 | 9.52% | $398 | 13.98% |
| Corporate | 1,168,451 | 5.10% | $460 | 8.65% |
| `Unassigned` | 566,126 | 2.47% | $177 | 1.61% |
| Premium Bleisure | 343,309 | 1.50% | $1,188 | 6.57% |
| **Ultra Wealthy Leisure** | 157,490 | 0.69% | $1,968 | 4.99% |
| Pilgrimage | 43,616 | 0.19% | $404 | 0.28% |
| **Intl. Student** | 42,153 | 0.18% | $1,159 | 0.79% |
| **MICE** | 27,007 | 0.12% | $269 | 0.12% |
| Mabuhay Loyalist | 6,453 | 0.03% | $113 | 0.01% |

Plus two things that accompany a segment rather than competing with it:

- **`is_last_minute` flag** — 4,411,666 bookings (19.26%)
- **`value_band`** — Budget 63.1% · Mid 30.9% · Premium 6.0%

**Removed:** `Family` (no positive definition — 100% of it was "a group booking nothing else claimed"),
`Digital Nomad` (never implementable in anonymous data), `Last-Minute` (became the flag above).

## 2. What changed, and the number to quote

**23.4% of bookings were genuinely reclassified — 5,358,355.**

⚠️ **Do not quote 62.7%.** That is how many labels differ *textually*, but 39.3% of it is only the
`Budget/Adventure → Leisure` rename. The real change is 23.4%.

**The single biggest improvement: `Unassigned` fell from 9.58% to 2.47% — a 74% reduction.** That closes
taxonomy gap #4, the bucket we had been reporting as the largest actionable gap in the deliverable. 75% of
it was Filipinos buying international economy tickets, now `Outbound International Leisure`.

**The flag beats the segment it replaced.** As a segment, Last-Minute only caught what fell through eight
higher-priority branches: 2,945,686. As a flag it covers every short-lead booking: **4,411,666** —
including 864,292 OFW/Migrant, 315,333 Corporate and 196,364 Balikbayan/VFR that were short-lead all along
and invisible as such. **50% more visible short-lead volume without moving a single threshold.**
(Those three counts are on **v1** labels — correct for "what was invisible before". Under v2 the same
4,411,666 bookings split 858,318 · 415,411 · 193,897, because the retired Last-Minute branch used to
outrank those segments. Say which.)

⚠️ **The flag does not ride along with every segment, and the per-segment *rate* is not all behaviour.**
Three of the eleven rules read `lead_days` too, so three bars of any short-lead-by-segment chart are
partly or wholly rule-induced: **MICE** (`lead_days >= 45`) and **Ultra Wealthy Leisure**
(`lead_days >= 30`) are **0% short-lead by construction**, not by behaviour; and **Corporate's
35.6% is partly circular** — one of its two branches is `any_business AND lead_days <= 7`, which only
admits bookings that are already short-lead. On the `corp_channel` branch, which carries no lead-time
condition, Corporate is **23.3%** — still above the 19.26% book average, so the behavioural claim
survives at a quarter of its apparent size. **Quote 23.3%, not 35.6%.**

## 3. Validation

### V1 — construct validity: do the segments differ on evidence the rules never saw?

**55 segment pairs. On the adaptive measure: 44 clearly distinct, 11 weakly distinguishable, none
indistinguishable. Median AUC 0.861, range 0.611–0.982.**

That is the strongest headline available and it is honestly earned — these are anchors the rules never
consumed, with per-pair withholding where an anchor would have leaked a rule bit.

On the **strict** measure (only the two unconditionally admissible anchors, `dep_month` and `n_bookings`):
median 0.637, and 11 pairs fall below 0.60. **The strict column is thin by construction, not by failure** —
after the July leak audit only two fields are unconditionally clean, so a two-column matrix cannot separate
much. Say which column you are quoting.

### ⚠️ The weakest boundary did NOT improve

`OFW/Migrant` vs `Balikbayan/VFR` — 6.8M bookings, historically split on a single bit.

| measure | result |
|---|---|
| strict (2 anchors) | **0.548** — not distinguishable |
| adaptive (full admissible set) | 0.713 |
| isolated clean-pair test | 0.72 |
| **A/B, old labels vs new, identical method** | **v1 0.730 · v2 0.728** |

**The taxonomy change is neutral on this boundary.** The A/B held method, anchors and population fixed and
varied only the labels, and found no difference.

⚠️ **And "0.608 → 0.72" is not a real comparison.** The 0.608 in our earlier documents is the *strict
pairwise matrix* cell; 0.72 is the *isolated clean-pair test*. Different tests. Like for like, strict has
gone **0.608 → 0.548**.

**Why:** the only change touching this pair moves 40k bookings, 1.4% of the branch. The Gulf stay-length
discriminator that motivated the work is still a *soft prior* and still changes no label.

### V2 — criterion validity: do the segments predict outcomes they were not built to predict?

| outcome | segment alone | features | features + segment | incremental |
|---|---|---|---|---|
| `flown_any` | 0.598 | 0.906 | 0.906 | +0.0005 |
| `rebook_180d` | 0.604 | 0.694 | 0.696 | +0.0024 |
| `refund_any` | 0.819 | 0.609 | 0.502 | **unstable — do not quote** |

**Honest reading: the segment label adds almost nothing on top of the raw features.** It carries real signal
alone (0.60 on both stable outcomes, against 0.50 for a coin flip) but the features already contain it.
That is expected for a rule-based segmentation — the label *is* a function of the features — and it is why
the deliverable's value is communication and targeting rather than prediction.

### V4 — out-of-time stability: does it hold a year later?

- **Composition holds where the volume is.** The segments showing drift are the smallest ones — Mabuhay
  (0.03%), Pilgrimage (0.2%), MICE (0.13%) — where a few hundred bookings move a mean. Treat as unresolved
  noise, not established behavioural change.
- **A model fitted a year earlier carves the later data about as well as one fitted on it — on the
  best-transferring method.** `GMM(full)` transfer ARI **0.740** against a within-window ceiling of
  **0.595** — ratio **1.24**. So an annual refit buys little.
  ⚠️ **But the panel disagrees, so state the method.** `LCA` transfers *below* its own ceiling —
  0.648 against 0.726, ratio **0.89**. Two methods, opposite sides of 1.0. This is weaker evidence than
  one clean ratio, and "on this evidence a yearly refit buys nothing" overstates it.
  ⚠️ **The earlier figures — LCA 0.729 / 0.645 / ratio 1.13 — do not reproduce and must not be quoted.**
  They came from a run whose per-window sample was silently 43% of intended (`load_sample` applied its
  window filter *below* the reservoir sample, so it returned ~13,000 rows instead of 30,000; found and
  fixed 18 Aug). That a ratio crossed 1.0 when the sample doubled means the earlier estimate was
  noise-dominated — V4 reports point estimates with no interval, and the transfer stage needs a
  multi-seed spread before any ratio is quoted.
- Outcome fields are excluded throughout as right-censored: `flown_any` runs ~100% early and falls to 30.7%
  in the most recent quarter purely because those bookings have not flown yet.

### V3 — detection power: re-run against v2, and it holds

Re-run 18 August at `k=11` (the v2 named-segment count; the 29 July run used 10). **The conclusion is
unchanged.** Reading the *majority* of the 12 method × archetype combinations rather than the luckiest:

| prevalence | majority detection |
|---|---|
| 0.50% · 1.0% | **never**, at any distinctness tested |
| 2.0% | detected at distinctness ≈0.494 |
| 5.0% | detected at ≈0.219 |
| 10.0% | detected at ≈0.13 |

So the bounded null stands: **no segment exists in these features at or above 2% of bookings with
distinctness ≈0.494 or greater** — and the limitation travels with it: **below ~1% of bookings (~229k) a
segment could exist and this pipeline would not find it.**

⚠️ **Do not quote the single-method minimum.** One combination found a group as faint as 0.114 planted
silhouette while groups as distinct as 0.567 were missed elsewhere in the grid — that is the luckiest of
12 draws, not a floor. Quote the majority-rule numbers above.

⚠️ **One instrument failed its own control.** Persistent homology's H0 component count returned median 2,
75th percentile 4, **maximum 131** across 100 draws of unchanged `w=0` data. A statistic ranging 2–131 on
identical input cannot detect anything, so this grid draws no conclusion from it. That qualifies the
28 July report's "1 significant H0 component" — 2 is the modal outcome, so the continuum reading survives,
but as the centre of a noisy distribution rather than a measurement. The H1 loop-noise ratio and the
barcode shape are the robust parts of that analysis; the integer count is not.

## 4. The SME constraint programme

PAL's revenue managers returned **39 rules**; all **24 follow-up questions** answered.

- **57 rules transcribed** — 15 hard, 42 soft — each with provenance, scope, live firing count and source
  row. Validated by `src/check_constraints.py`, currently 0 errors.
- **All six `certain` hard rules are now asserted at build time**, reading the CSV rather than a copy, so
  the rules and the code cannot drift apart. A first draft of the waterfall satisfied only 4 of 6 —
  ordering alone does not implement a "cannot be".
- **Stage P** (`src/apply_soft_priors.py`) scores the 21 live tendencies against every booking:
  - no prior fires at all on **43.6%** of the book — PAL's rules are simply silent on two-fifths of it
  - where the tendencies make a call, they **agree with our labels 70.5%** of the time
  - the largest disagreement is *Last-Minute → Leisure* on 1,025,351 bookings, which independently
    corroborates the decision to drop Last-Minute as a segment
  - it changes **no label** — a tendency is not a rule, and disagreement is the finding

### The best domain finding, and its open confound

**Manila–Gulf traffic runs on a one-month clock that no other corridor has.** 19.11% of Gulf round trips
fall in the 28–32 night window against 8.48% at 12–16 — the only corridor where a month outweighs a
fortnight; every other is ≤0.60. RM attributes it to employer-mandated leave.

⚠️ **Unresolved:** if Gulf economy fares carry a one-month maximum-stay condition, the fare rule produces
the identical pattern. `FarebasisCode` would settle it and has been requested. **Until then, present the
pattern, not the explanation.**

Two parts of the SME's claim did **not** survive testing: the "~45 day" leave pattern (no excess at 45),
and grouping Hong Kong/Taipei with the Gulf (pooling them drops discrimination *below chance* — 0.375
against 0.676 Gulf-only).

## 5. Cost of misclassification

Answered in `docs/segment-cost-research.md` with sources. **Annual value at risk per customer spans
$495 to $9,784** — the first real dollar spread this project has had.

Recommended weights replace a ladder whose dollar column was simply `penalty × $4,000` and which was
**inverted against measured revenue in two places**. Notable moves: Premium Bleisure 4 → 9,
Balikbayan/VFR 2 → 4, Corporate 10 → 8. Three overrides where the measurement is documented as blind
(Mabuhay sees only award redemptions; Corporate's rule is the most contested; MICE is valued per booking
when its revenue is per contract). **OFW is left at the measured 3 with the strategic argument flagged for
PAL** — "matters more than its per-booking value" is a commercial judgement, not an empirical one.

PAL's answer was **"see run first"**, so these are a proposal, not agreed values.

---

## What to say, and what not to

**Say:**
- Unassigned fell 74%, closing the largest known gap
- 44 of 55 segment pairs are clearly distinct on independent evidence
- 23.4% of bookings reclassified
- The Gulf one-month pattern is real and corridor-specific
- Every certain SME rule is enforced in code, asserted on every build
- Segment sizes and composition hold across a twelve-month step, on full-population counts

**Do not say:**
- That the weakest boundary improved — it did not
- 0.608 → 0.72 — not the same test
- 62.7% reclassified — that is mostly a rename
- **LCA transfer ARI 0.729 / ceiling 0.645 / ratio 1.13 — withdrawn, computed on a 43% sample.**
  The current numbers are GMM 1.24 and LCA 0.89, and the methods disagree
- **That Corporate is the most short-lead segment at 35.6%** — one of its rule branches only admits
  short-lead bookings. 23.3% is the honest figure
- That MICE or Ultra Wealthy Leisure never book late — they are 0% *by rule construction*
- That the Gulf pattern is *caused* by employer leave — the fare-rule confound is open
- **V3's single-method minimum (0.114 planted silhouette)** — that is the luckiest of 12 draws;
  quote the majority floors (≈0.494 at 2%, ≈0.219 at 5%)
- The H0 component count as a clean measurement — it ranges 2–131 on unchanged data

**Known limitations to own before being asked:** no loyalty field, so Mabuhay is unmeasurable at 0.03%;
no ancillary revenue; segment labels add little incremental prediction over the raw features; detection
blind below ~1% prevalence; the build still moves by ±1 booking between runs (1,830 tied sort keys,
cause and fix recorded).

*Sources: `outputs/validate_construct/`, `outputs/validate_criterion/`, `outputs/validate_temporal/`,
`outputs/soft_priors/`, `outputs/features_real/`, `docs/waterfall-v2-design.md`,
`docs/segment-cost-research.md`, `docs/knowledge-base.md` §15.*
