# Capstone Defence — Slide Outline

**PAL Customer Segmentation · MAIDA capstone · owners: Martin / Josh / Jadd**
Working outline for the defence deck. Every number below is sourced from
`docs/defense-brief-2026-08-18.md` (the "what to say / what not to say" list there is binding —
it is reproduced per-slide as ⚠️ guardrails). Update this file first, then build slides from it.

---

## The one-sentence story

> *We went looking for customer clusters and found a continuum — so we flipped the design:
> business rules label every booking, and machine learning's job became proving, refining and
> monitoring those labels. That inversion, honestly validated, is the contribution.*

Every section should push this arc forward. The defence is strongest when the "failure"
(no natural clusters) is presented as the central finding, not an apology.

## Suggested improvements to the proposed structure

Kept: all eight sections, in your order, with your owners. Recommended adjustments:

1. **Merge the telling of §3 (EDA) and §4 (Methodology) into one continuous story** — two slides
   sections, one narrative. The EDA's continuum finding *is the reason* the methodology inverted;
   splitting them across a speaker change would break the best moment in the talk. Josh owns both,
   so keep the handoff inside his block.
2. **Rename §6 from "still trying to improve" to "Limitations & handover readiness."** Panels hear
   "still trying" as unfinished; "known limitations, owned before you ask" is a defensive strength —
   we literally have a brief built for it.
3. **Add a backup-slide appendix** (not presented): validation matrices, the detection-power grid,
   the withdrawn-numbers list. Panels reward having the receipt ready.
4. **Put the "what not to say" list in every presenter's speaker notes**, not on slides.

Timing for a 40-minute defence (adjust pro-rata): opening 3 · problem+TOR 5 · EDA 5 ·
methodology 8 · dashboard 4 · findings 7 · limitations 3 · recommendations 4 · conclusion 1 ·
buffer/Q&A prep 0 — the buffer lives in the Q&A.

---

## 0. Title & agenda *(30 s — whoever opens)*

- Project title, team, PAL + MAIDA logos, date.
- Agenda = the eight sections, one line each. No content.

---

## 1. Problem Statement — **Martin** *(2–3 min, 1–2 slides)*

**Headline:** PAL sells seats to people it cannot see — bookings are anonymous PNRs, and without
knowing *who is flying and why*, pricing, retention and product decisions are one-size-fits-all.

Content:
- The anonymous-lens constraint up front: no loyalty/CRM join, Sabre PNR data only. This is the
  design constraint everything downstream honours — say it here so nobody asks "why not just use
  the loyalty tier?" later.
- The ask: an **anonymous trip-purpose × value segmentation** at the booking level that PAL's
  commercial teams can act on — segments a revenue manager recognises, not statistical artifacts.
- Scale that makes it non-trivial: **38.1M coupon rows → 22.9M bookings → 13.4M customers**,
  2024–2027.
- Why segmentation and not prediction: PAL's need is *communication and targeting* — naming the
  passenger in front of you — which frames why we later accept that segment labels add little
  incremental predictive power (V2). Planting this seed here defuses the toughest validation
  question before it's asked.

---

## 2. TOR — what we promised PAL — **Martin** *(2 min, 1 slide)*

**Headline:** what was promised, what was delivered, and where the risks landed.

Content:
- The deliverables table from the TOR, each row marked **Delivered / Delivered-with-change / Open**.
- **Risk table** (as proposed): risk item → status → mitigation. Candidates from the record:
  - *Data access/quality* → realised, mitigated: initial sample was insufficient; secured the full
    38M-coupon extract (bridges into §3).
  - *No ground-truth labels* → realised, mitigated by design: non-circular validation battery
    (V1–V4) built to work without SME labels; SME labelled sample still requested.
  - *Segments may not exist as natural clusters* → **realised — became the central finding.**
  - *Units/definitions ambiguity* → partially resolved: revenue confirmed USD only on 18 Aug.
  - *Stakeholder availability* → mitigated: 39 SME rules returned, all 24 follow-up questions answered.
- One line on scope discipline: the earlier prototype track is superseded; every quoted result is
  from the real extract.

---

## 3. EDA — the realisation — **Josh** *(4–5 min, 2–3 slides)*

**Headline:** two realisations changed the project: (a) we needed more data, and (b) the customer
base is a **continuum, not distinct clusters**.

Slide 3a — *the data journey*:
- Started on a 30k-row sample; realised trip purpose lives in patterns (lead time, stay length,
  routing, seasonality) that need full volume and a full year to see → secured the 38M-coupon
  extract, rebuilt everything on DuckDB/Parquet.
- One or two EDA figures from `reports/study_guide/` (grain pyramid: coupons → bookings →
  customers; only 26% of customers book more than once — why booking, not customer, is the
  modelling row).

Slide 3b — *the continuum*:
- The money visual: PCA/projection showing one dense cloud, no gaps.
- The receipts, stated calmly: a **ten-method, six-family benchmark** (LCA, GMM, k-prototypes,
  k-modes, KMeans, spectral, SVC, TDA-Mapper…) — separation **ceilings at 0.381 Gower silhouette**
  across all ten. No method finds natural clusters because there are none to find.
- The pre-emptive answer to "or are your methods blind?": **detection power** (V3) — we *planted*
  synthetic segments of known size and distinctness in the real data and measured recovery.
  A majority of methods finds a planted segment at ≥2% prevalence. So the null is about PAL's
  data, not our instruments.
  - ⚠️ Quote the **majority-rule floors** (≈0.494 distinctness at 2% prevalence, ≈0.219 at 5%),
    never the single-method minimum (0.114 — luckiest of 12 draws).
  - ⚠️ Own the bound: **below ~1% of bookings (~229k) a segment could exist and we would not
    find it.**
- Intuition line for the panel: *"Customers don't come in boxes; they come on a dial. So instead of
  asking an algorithm to invent boxes, we let the business draw the lines and made the algorithms
  prove the lines are in sensible places."* — this sentence is the pivot into §4.

---

## 4. Methodology — iteration and workarounds — **Josh** *(7–8 min, 3–4 slides)*

**Headline:** the rules label, and ML checks the labels. Clustering is validator and refiner,
never the labeller.

Slide 4a — *the pipeline in one picture* (the flowchart from `docs/methodology.md`):
- gz → typed Parquet → Stage C clean+flag → Stage F features (coupon → booking → customer) →
  **rule waterfall** (the deliverable: 11 named segments + Unassigned) → Power BI export.
- ML's three jobs hang off the waterfall: **refine** (LCA sub-segments inside oversized parents),
  **test** (V1–V4 validation battery), **monitor** (PSI drift).

Slide 4b — *the iteration story* (storytelling slide — a timeline works well):
1. HDBSCAN prototype on the sample → looked promising → superseded when real data arrived.
2. Real data: clustering benchmark → continuum finding → **inverted the design** to rules-primary.
3. First waterfall → 9.6% Unassigned → SME constraint programme (39 rules from PAL's revenue
   managers, 57 transcribed, all 24 follow-ups answered) → **waterfall v2** → Unassigned down to
   2.47%.
4. PAL approved the revised taxonomy 17–18 Aug: 11 segments + flag + value band.

Slide 4c — *the honest-validation workarounds* (this is where the methodological rigour lives —
give it airtime, panels grade this):
- **Circularity**: a rule-based label is a function of its inputs, so you cannot validate it with
  those inputs. Built a **circularity contract** (`validation_anchors.py`) that raises an error
  rather than warn — validation only ever sees fields the rules never consumed.
- **Right-censoring**: `flown_any` falls to 30.7% in the last quarter *because those flights
  haven't happened yet* — outcome fields excluded from temporal tests, with the censoring curve
  published.
- **Negative controls everywhere**: random half-splits must score ≈0.50 before any real number is
  read; the planted-segment test carries a random-direction control; one instrument (persistent-
  homology H0 count) **failed its own control (range 2–131 on unchanged data) and was retired** —
  say this proudly, it demonstrates the harness works.
- **Hard SME rules asserted at build time** — six "cannot be" rules read from the CSV on every
  build, so code and business rules cannot drift apart.

⚠️ Guardrails for this section: don't claim HDBSCAN "failed" (it was the right tool for the wrong
data shape); don't present LCA/GMM as the model — they are refinement/measurement layers.

---

## 4.2 Dashboard development — **Jadd** *(3–4 min, 2 slides)*

**Headline:** the segmentation ships as a Power BI star schema PAL's BI team can load, reconcile
and extend — not as a notebook.

Content:
- The export: row-preserving star schema (**38,116,259 coupons in = out**), `fact_flight` 20.6M
  rows, `dim_segment` persona dimension, `dim_date`, and a 1,835-row per-segment monthly
  **scorecard** so a KPI tile never aggregates 20M rows.
- The persona dimension's three-way column split — **measured** behaviour (recomputed every
  build), **editorial** persona text, **governance** (`Trust`, `DataCaveat`, penalty weight) — and
  why `Trust`/`DataCaveat` are on the card: persona cards persuade, and a cropped caveat is how
  "Mabuhay 0.03%" becomes "loyalty doesn't matter."
- The BI traps designed out (pick 2 for the slide, rest to notes): complete-travel-month flag
  (still-filling forward book draws a fake cliff), no stored percentages (shares must be DAX —
  a share is only valid in the filter context that computed it), coalesced non-NULL flags,
  build-time assertion that scorecard ties to fact table.
- Screenshot(s) of the dashboard; live demo only if the defence format allows and a recording
  exists as fallback.
- Deployment reality: `.pbip` project generated programmatically; `.pbix` requires one manual
  save in Power BI Desktop (proprietary binary) — honest about the seam.

---

## 5. Findings — **Josh & Jadd** *(6–7 min, 3 slides)*

**Headline:** 11 validated, named, costed segments covering 97.5% of 22.9M bookings — and the
model tells you exactly how far to trust each one.

Slide 5a — *the taxonomy* (the segment table from the defence brief §1):
- 11 segments + Unassigned; sizes and revenue shares. The shape of the business in one table:
  Leisure is half of bookings but 15% of revenue; **Balikbayan/VFR is 12.5% of bookings and
  28.4% of revenue**; Premium Bleisure averages $1,188/booking.
- Plus the two companions: `is_last_minute` flag (19.26% of bookings) and `value_band`
  (Budget 63 / Mid 31 / Premium 6).
- **The number to quote: Unassigned fell 9.58% → 2.47% — a 74% reduction**, closing the largest
  known gap. And **23.4% of bookings genuinely reclassified** (⚠️ never 62.7% — that is mostly
  the Budget/Adventure → Leisure rename).
- The flag beat the segment it replaced: 4.41M short-lead bookings visible vs 2.95M —
  **50% more short-lead volume without moving a threshold**. ⚠️ Corporate's honest short-lead
  rate is **23.3%**, not 35.6% (one rule branch is circular); MICE and Ultra Wealthy are 0%
  short-lead *by rule construction*.

Slide 5b — *validation scorecard* (one row per stage, traffic-light):
- **V1 construct:** 55 pairs — **44 clearly distinct, 11 weak, 0 indistinguishable**; median
  AUC **0.861** on anchors the rules never saw. ⚠️ Name the measure (adaptive); the strict
  2-anchor column is thin by construction. ⚠️ The weakest boundary (OFW vs Balikbayan) **did not
  improve** — A/B v1 0.730 vs v2 0.728; never say "0.608 → 0.72" (different tests).
- **V2 criterion:** segments alone carry real signal (≈0.60 AUC vs 0.50 coin-flip) but add
  ~nothing over raw features — **expected for a rule-based compression**; the value is
  communication and targeting (callback to §1). ⚠️ `refund_any` unstable, don't quote.
- **V3 detection power:** covered in §3 — one recap line.
- **V4 temporal:** composition holds where the volume is across a 12-month step; drift is
  confined to the three smallest segments. ⚠️ Transfer-ARI: methods disagree (GMM 1.24, LCA
  0.89) — say "an annual refit likely buys little *on the best-transferring method*", and the
  old LCA 1.13 figure is **withdrawn** (computed on a 43% sample).
- Jadd takes the "how this appears in the dashboard" beat: Trust column = this scorecard.

Slide 5c — *the domain finding* (Josh):
- **Manila–Gulf traffic runs on a one-month clock no other corridor has** — 19.11% of Gulf round
  trips at 28–32 nights vs 8.48% at 12–16; every other corridor ≤0.60. RM attributes it to
  employer-mandated leave. ⚠️ **Present the pattern, not the explanation** — a one-month
  maximum-stay fare rule would produce the identical signature; `FarebasisCode` requested.
- Bonus rigour beat: two parts of the SME's own claim did *not* survive testing (no 45-day
  excess; pooling HK/Taipei with the Gulf drops discrimination below chance) — we test what
  we're told, including by the client.
- Cost of misclassification: annual value at risk **$495–$9,784 per customer** — the first real
  dollar spread; recommended penalty weights replace an inverted ad-hoc ladder. ⚠️ PAL's answer
  was "see run first" — these are a proposal, not agreed values.

---

### Sub-segments — ML's job 1, added 19 Aug 2026 (deck slide 19)

The deck promised the refinement layer on slides 8, 10 and 12 and never showed it — a gap worth closing in
an ML capstone. First draft was a five-column text grid; **redesigned 19 Aug as one worked example drawn as
a Sankey** (`src/sankey_subsegment.py` → `outputs/segment_charts/fig_s07_sankey_balikbayan_vfr.png`), with
the other four parents compressed to a single line of ranges. Underlying data is unchanged: **LCA inside the
five largest v2 segments, four sub-types each (20 cells)**, from `outputs/sub_segments/summary.md` (40,000
bookings per parent, hash-ordered).

- **Why Balikbayan/VFR is the example:** 12.5% of bookings against 28.4% of revenue, and recommendation 1
  tells PAL to protect it. Every sub-type is a round trip, so the axis that varies is booking horizon.
- **The visual carries the argument:** ribbon width is share, colour and position are median revenue, so
  the **inversion is immediate** — the thinnest flow (16.9%) earns the most ($995), the fattest (38.8%) the
  least ($311). That is slide 17's volume-versus-value asymmetry repeating one level down.

- **The message is the grammar, not the twenty names.** Every parent splits on the same three axes —
  direction × timing × fare tier — recovered per parent without being told.
- **The commercial point is the spread inside one segment.** Balikbayan/VFR $311 (26 days out) → $995
  (66 days), 3.2× on booking horizon alone. Corporate $112 → $656 with every sub-type short-lead, so there
  the spread is direction and fare. OFW 1.7× and Outbound International 1.2× are flat — those two do not
  need sub-segment pricing, which is a finding in itself.
- ⚠️ **Never say "BIC chose four".** `sub_segment.py` has `K_RANGE = range(2, 5)`, so four is the **top of
  the search range** and BIC preferred the maximum in all five parents. That is the continuum one level
  down — no natural number of types inside a segment either. Four is our granularity choice, not a
  discovery. Same trap as `k=9` on the PCA slide; handle it identically.
- Sub-types are **descriptive only** — they change no top-level label and nothing downstream reads them.

---

## 6. Limitations & handover readiness — **Josh** *(3 min, 1 slide)*

**Headline:** known limitations, owned before you ask — and what's in flight to close them.

The own-it list (from the brief):
- No loyalty field → Mabuhay unmeasurable at 0.03%; no ancillary revenue.
- Segment labels add little incremental *prediction* over raw features (by design — see V2). *(On the
  slide since 19 Aug: "Segment labels add little incremental prediction — by design, not by failure.")*
- Detection blind below ~1% prevalence (~229k bookings).
- Build moves by ±1 booking between runs (1,830 tied sort keys — cause and fix documented).
- V4 transfer needs a multi-seed spread before any refit-cadence claim is made. *(On the slide since
  19 Aug, in the in-flight column: "No refit-cadence claim yet: V4 transfer needs a multi-seed spread.")*

In flight before handover:
- `FarebasisCode` to resolve the Gulf fare-rule confound.
- Penalty weights awaiting PAL sign-off ("see run first").
- SME labelled sample (`data/labels/`) to unlock non-circular *accuracy* — today any accuracy
  figure would be circular, which is why the dashboard deliberately ships none.

---

## 7. Recommendations — **Martin** *(4 min, 2 slides — from the manuscript)*

Four blocks, as proposed:

**a. Actions on the deterministic segments** — per-segment commercial plays keyed to the
economics: protect Balikbayan/VFR (28% of revenue on 12.5% of bookings), grow Premium Bleisure
and Ultra Wealthy (highest per-booking value), use the `is_last_minute` flag for willingness-to-pay
plays across *all* segments rather than a bucket. Include one "how *not* to use it": not a
prediction engine, not below-1%-prevalence microsegments.

**b. Model enhancement strategy** — ranked data investments: loyalty-tier join (unlocks Mabuhay +
non-circular anchors), `FarebasisCode`, ancillary revenue, SME labelled sample; then the gated
experiments from `docs/continuum-levers-plan.md` (each with a pre-registered decision rule and a
hard stop — recommend *the discipline*, not just the experiments).

**c. Model deployment strategy** — deterministic waterfall = trivially deployable (no model
server; SQL/rules engine); hard-constraint assertions run on every build; refit cadence: evidence
so far says yearly refit buys little, confirm with multi-seed V4 before committing; drift monitor
(`monitor_real.py`, segment-mix + rule-input PSI) as the tripwire that triggers a rules review.

**d. Dashboard management strategy** — ownership handover to PAL BI; the governance columns
(`Trust`, `DataCaveat`) as living metadata that must survive edits; scorecard-ties-to-fact
assertion as the regression test; complete-travel-month discipline for any new visual; refresh
process (rebuild export → reload `.pbip`).

---

## 8. Conclusion — **Josh** *(1 min, 1 slide)*

Three beats and stop:
1. **The finding:** PAL's customers are a continuum — so we built a segmentation that draws the
   lines where the business needs them, then *proved* where the lines hold (44/55 boundaries
   clearly distinct) and said plainly where they don't.
2. **The deliverable:** 11 named, costed, validated segments + flag + value band on 22.9M
   bookings, shipped as a reconciling Power BI model with its trust levels printed on it.
3. **The lesson** (capstone register): the most valuable thing we produced isn't the labels —
   it's the *honesty machinery* around them: circularity contracts, negative controls, retired
   instruments, withdrawn numbers. That's what makes the labels usable.

Thank-you slide → Q&A.

---

## Appendix / backup slides (build, don't present)

- V1 full 55-pair distinguishability matrix · V3 detection grid · V4 censoring curve.
- The withdrawn-numbers slide (LCA 1.13 transfer, 0.608→0.72, 62.7%, H0 count) — deploy only if
  a panelist quotes an old document at you.
- Waterfall v2 before/after flows (`outputs/segment_charts/` reclassification chart).
- SME constraint programme detail: 57 rules, Stage P results (silent on 43.6% of the book;
  70.5% agreement where it speaks; the Last-Minute disagreement that corroborated dropping it).
- Pipeline runtimes/scale slide (DuckDB/Parquet, ~90s ingest) for IT-flavoured questions.

## Q&A prep (all presenters — 10 minutes as a team, before the defence)

Rehearse the five hardest, one owner each:
1. *"Your segments add nothing predictive — why do they matter?"* → Josh (V2 framing: compression
   by design; value is communication/targeting; the label carries 0.60 alone).
2. *"How do you know clusters don't exist rather than you missed them?"* → Josh (V3 planted
   segments + the honest ~1% blind spot).
3. *"Isn't validating rules with the data that built them circular?"* → Josh (anchors contract,
   negative controls).
4. *"What does a misclassification actually cost?"* → Martin ($495–$9,784 spread, sourced;
   weights proposed, not agreed).
5. *"Who maintains this after you leave?"* → Jadd (deterministic rules + assertions + drift
   monitor + governance columns).

**Every presenter reads `docs/defense-brief-2026-08-18.md` "What to say, and what not to"
the night before.** The ⚠️ items above are lifted from it; the brief is authoritative.

---

*Sources: `docs/defense-brief-2026-08-18.md` · `docs/methodology.md` (Current Methodology at a
Glance) · `docs/pipeline-study-guide.md` · `docs/segment-cost-research.md` · `README.md`.*
*Last updated: 2026-08-18.*
