# Tuesday briefing pack — PAL Customer Segmentation

**Meeting:** 4 August 2026 · **Prepared by:** Josh (not available on the day)
**For:** the team presenting these three agenda items
**Purpose:** source content for your slides — every number here is verified and safe to put on screen

---

## How to use this pack

Three agenda items belong to us: **current methodology**, **ML success metrics**, and **the SME
constraint asks**. The Power BI dashboard review and the sample fields from Hanz sit with other owners.

Each item below is laid out the same way:

| Block | What it's for |
|---|---|
| **The one message** | The single sentence that item has to land. If nothing else survives, keep this. |
| **Slide-ready content** | Numbers and tables already checked — copy straight onto a slide. |
| **Speaker notes** | Context and analogies for explaining it out loud. Not slide material. |
| **Likely questions** | What the room tends to ask, with an answer that holds up. |

**There are already five built slides** covering these items —
`reports/tuesday_slides/PAL_01…05.png` (source: `assets/tuesday-slides/josh-slides.html`, open in a
browser and re-export if you want to edit). Mapping:

| Slide | Covers |
|---|---|
| `PAL_01_Current_Methodology.png` | Agenda item 1 |
| `PAL_02_Business_Rules.png` | Item 1 — the rules in detail |
| `PAL_03_Success_Metrics.png` | Agenda item 2, including the worked calculation |
| `PAL_04_SME_Constraints.png` | Agenda item 3 |
| `PAL_05_Persona_Cards.png` | Optional — the segment personas now in Power BI |

Use them as-is, or rebuild from the content below. **Please read §6 (the do-not-say list) before
presenting** — a few of these numbers are easy to overstate, and Josh won't be in the room to catch it.

---

## 1 · Current methodology

### The one message

> **The passenger base is a smooth spectrum, not a set of natural groups. So PAL's business logic draws
> the segment boundaries, and the machine learning checks them, refines them, and watches them for
> drift. That makes the result more defensible, not less — every boundary is written down and reviewable
> instead of buried inside an algorithm.**

### Slide-ready content — the process in five steps

| # | Step | What happens | Why it matters |
|---|---|---|---|
| 1 | **Assemble** | Read the full 38.1M-coupon extract | Nothing is sampled — the whole book is in scope |
| 2 | **Clean & flag** | Map every booking class to PAL's own **farebrand value ladder (tiers 1–7)**; flag staff travel, awards, group fares, refunds | The value axis is **PAL's own definition**, not one we invented |
| 3 | **Group up** | Combine flight legs into **bookings** (one purchase decision), then roll up to customers | A round trip is *one* trip with one purpose. Counting legs would make a returning Balikbayan look like two one-way OFWs |
| 4 | **Label** | Apply the **priority rule waterfall** → 10 named segments + Unassigned | This is the deliverable. Deterministic and auditable — you can read the exact rule behind any label |
| 5 | **Deliver** | Join the label back onto all 38.1M coupons → Power BI | 38,116,259 rows in = out · **99.95% carry a segment** |

```text
  STEP 1            STEP 2              STEP 3             STEP 4  ★           STEP 5
  ────────────      ────────────        ────────────       ────────────        ────────────
  ASSEMBLE     ──▶  CLEAN & FLAG   ──▶  GROUP UP      ──▶  LABEL          ──▶  DELIVER
  38.1M             booking class       flight legs        rule waterfall      Power BI
  flight legs       → value tier        → 22.9M            first match wins    star schema
  (nothing            1–7               BOOKINGS           10 segments         99.95% carry
   sampled)         drop staff /        → 13.4M            + Unassigned        a segment
                    non-revenue         customers               │
                                                                │
                                        ┌───────────────────────┘
                                        ┆  checks the rules — never assigns labels
                                        ▼
                                        ML AROUND IT
                                        refine (LCA)  ·  test (4 validation stages)
                                        ·  monitor (drift)
```

★ **Step 4 is the deliverable.** Steps 1–3 prepare the data; step 5 ships it. The machine learning
branches off step 4 as a *check*, not as the labeller — that distinction is the whole story of item 1.

**Scale:** 38.1M flight legs → **22.9M bookings** → 13.4M customers.

> A rendered version of this diagram is on slide `PAL_01_Current_Methodology.png` if you'd rather paste
> the graphic than rebuild it.

### Slide-ready content — what the model is

| | |
|---|---|
| **Unit of analysis** | The **booking** = one customer + one issue date = one purchase decision |
| **The model** | A prioritised **rule waterfall**, first match wins → 10 segments + Unassigned |
| **What learns/fits** | **Nothing at the top level.** Models work *below* it (sub-segmenting large groups) and *around* it (validation, drift monitoring) |
| **Scoring a new booking** | Apply the same rules. The labeller itself cannot drift — drift only enters through the input mix, which is what monitoring watches |
| **The lens** | **Anonymous trip-purpose × value** — needs no loyalty/CRM join. A named industry approach (Sabre's anonymous segmentation) |

A useful line if someone asks what kind of model this is:

> *"The segmentation itself uses no machine learning — it's a deterministic set of business rules over
> observable booking attributes, which is exactly why it can be audited. The machine learning sits
> around it: refining, testing and monitoring."*

### Slide-ready content — techniques and their status

If asked *"what techniques did you use?"*, this is the answer. **The status column is the important
part** — it separates what is in the pipeline from what was run once to answer a question from what was
tested and rejected. Those three get conflated easily.

| Technique | What it's for | Status |
|---|---|---|
| **Rule waterfall** | Assigns the segment | ✅ **In pipeline — primary** |
| **Farebrand value ladder** | The value axis, tiers 1–7 | ✅ In pipeline |
| **Negative learning** (impossibility rules) | Rules out invalid segments before labelling | ✅ Design principle — and the basis of the hard-constraint ask in item 3 |
| **LCA** (Latent Class Analysis) | Splits oversized segments into sub-types | ✅ In pipeline — **under review** |
| **GMM** (Gaussian mixture) | Beat LCA on the benchmark | ⏸️ **Candidate, not adopted** — needs a like-for-like re-test first |
| **Asymmetric cost matrix + per-segment recall** | The success metric — item 2 | ✅ Built, **awaiting ground truth** |
| **Four validation stages** | Do the segments hold up? (construct · criterion · detection power · out-of-time) | ✅ All run |
| **PSI / ARI drift monitoring** | Flags when the rules go stale | 📋 Specified, not yet wired |
| **k-prototypes · k-modes** | Mixed-type cross-check | 🔬 Diagnostic only |
| **KMeans · SVD+KMeans · Spectral · SVC · TDA-Mapper · persistent homology** | Assumption-free structure tests | 🔬 Benchmark only — **all found no structure** |
| **HDBSCAN** | Was the original plan of record | ❌ **Dropped** — categorical-heavy data isn't density-separable |

### Slide-ready content — the evidence for the pivot

1. **Ten methods across six families.** Best separation any of them reached: **0.381**, where ~0.5 is
   the usual minimum for claiming real structure exists.
2. **"Or were the methods just blind?"** Groups of known size were planted into the real data. A planted
   segment is reliably recovered at **≥2% of bookings** — so the methods work; the groups aren't there.
3. **The stated blind spot:** below **~1% of bookings (~229k)** a real segment could exist and would not
   have been detected. This bound is published alongside the finding.
4. **Not a one-off snapshot.** Across two consecutive 12-month windows segment shares hold (largest
   single move 1.5pp) and **a model fitted a year earlier still transfers.**

### Speaker notes

The analogy that works, if the room needs one: a **fruit stand** has obvious piles — you can see the gap
between apples and oranges from across the room. A **paint store** runs continuously from white through
cream to beige with no natural gap, yet it still needs named colours on the shelf, because nobody orders
"wavelength 578 nanometres." **PAL's passengers are a paint store.** The boundaries are chosen
deliberately, for commercial usefulness.

Two consequences worth saying out loud: a booking near a boundary is **genuinely ambiguous, not
misfiled**; and because the boundaries are a business decision, **they are PAL's to set.**

### Likely questions

- **"So the ML did nothing?"** → It does three things, none of them labelling: **LCA** sub-segments the
  oversized groups, **four validation stages** independently test the boundaries, and **PSI/ARI
  monitoring** watches for drift. Plus the ten-method benchmark that produced the pivot in the first place.
- **"Which algorithm did you settle on?"** → For the segmentation, none — it's rules. For the refinement
  layer, **LCA today, with GMM a candidate that has deliberately not been swapped in**, because the
  benchmark tested top-level segmentation while LCA's actual job is sub-segmentation. Swapping on a
  mismatched test would be the wrong call.
- **"Why drop HDBSCAN?"** → It's a density-based method and this data is categorical-heavy, so there is
  no density to find. Wrong tool for the data type, not a tuning failure.
- **"What's your DBCV / silhouette?"** → DBCV was never computed on the real extract and doesn't apply
  here, for the reason above. **Quote 0.381, the separation ceiling.** Do not quote a DBCV figure.
- **"Isn't a rule-based system a step backwards?"** → The rules encode PAL's commercial intent, which an
  algorithm cannot infer. And whether they're right is measurable — that's items 2 and 3.

---

## 2 · ML success metrics — what they're for, plus the worked calculation

### The one message

> **Plain accuracy is the wrong target, because it treats every mistake as equal and these aren't.
> Mistaking a Corporate traveller for Budget Leisure means under-serving PAL's most valuable passenger
> and quoting them a promo fare — roughly ₱40,000 of revenue at risk. The reverse mistake costs a
> courtesy upgrade. So every error is weighted by what it actually costs.**

### Slide-ready content — the worked calculation

This is the one to spend time on. A test batch of **1,000 bookings** at the true segment mix: **44
genuinely Corporate**, 394 genuinely Budget/Adventure. Two models, **both exactly 90% accurate**, both
making 100 errors:

| | Model A | Model B |
|---|---|---|
| Plain accuracy | 90% | 90% |
| Corporate errors | 20 × ₱40,000 = **₱800,000** | 2 × ₱40,000 = **₱80,000** |
| Budget errors | 80 × ₱4,000 = **₱320,000** | 98 × ₱4,000 = **₱392,000** |
| **Revenue at risk** | **₱1,120,000** | **₱472,000** |
| Cost per booking scored | ₱1,120 | ₱472 |
| **Corporate recall** | **54.5%** (24 of 44) ✗ | **95.5%** (42 of 44) ✓ |

**Same accuracy. 2.4× the business impact.** Plain accuracy cannot tell these two models apart — which
is the entire reason the cost matrix exists.

### Slide-ready content — the two numbers reported per release

1. **Per-segment recall** — of all the genuine Corporate travellers, what share were caught?
   **Target ≥91%**, with Corporate (×10) and OFW/Migrant (×5) as the priorities.
2. **Weighted cost per booking** — the peso-weighted error rate. Minimise.

Penalty weights: Corporate ×10 · Mabuhay ×8 · OFW ×5 · Premium Bleisure ×4 · Pilgrimage ×3 ·
Balikbayan and Family ×2 · Last-Minute and Budget ×1.

### 🔴 The caveat that must be said out loud — it sets up item 3

> *"The scoring machinery is built and tested. But today 'correct' means matches what our own rules said
> — we are grading our own homework. What's missing is an answer key. That's the third item."*

The segments **have** been shown to carry real signal: they predict refunds and 180-day rebooking, which
no rule looks at. So the labels aren't noise. That does **not** prove they are the *right* labels for PAL.

**Do not skip this.** If the room leaves believing there is a validated accuracy figure, the third ask
loses its reason to exist.

### Speaker notes

The analogy: a warehouse sorts 1,000 parcels and gets 90% right. Good? It depends entirely on *which*
10%. Swapping two boxes of identical envelopes costs nothing. Putting the medical-supplies crate on the
wrong truck is serious. Same error rate, completely different consequence.

### Likely questions

- **"Where did ₱40,000 come from?"** → It is **PAL's own estimate**, from the requirements document —
  not ours. It drives the whole optimisation, so PAL should confirm it or replace it with their number.
- **"So what's your accuracy today?"** → **There is no ground-truth accuracy figure yet, by design.**
  Anything quotable now is circular. With ~1,000 labelled bookings, a real figure comes back the same day.
- **"Why not just maximise revenue?"** → Because segment revenue and segment *value* diverge. Mabuhay
  Loyalist's median revenue is about 22 — they paid in miles, so that's just taxes. Optimising on revenue
  alone would deprioritise the most loyal flyers.

---

## 3 · Asks from the SMEs — the constraints

### The one message

> **Three asks. Two are constraint files that already exist and are pre-filled with our own best
> guesses — because a blank template gets a blank response. We need SMEs to correct, delete and extend
> them; a rule we drafted and an SME confirmed is worth far more than a rule we drafted alone. The third
> is the answer key: roughly 1,000 bookings labelled by hand.**

### Ask 1 — HARD constraints · `data/constraints/hard_constraints.csv`

**What it is:** statements of *impossibility*. "Booked 60+ days out, economy, no loyalty ID — **cannot**
be Corporate." These shrink the decision space before anyone makes a judgement call: instead of choosing
among 10 segments, an annotator picks between 2 or 3.

**Format — one rule per row. Seven examples are already in the file:**

```csv
rule_id,condition,verdict,segments,owner,confidence,notes
H01,lead_days >= 60 AND max_tier <= 4,cannot_be,Corporate,RM Domestic,certain,Corporate books late and premium
H02,channel = 'Sea Crew',must_be,OFW/Migrant,RM International,certain,Maritime crew channel is definitive
H03,is_award,must_be,Mabuhay Loyalist,FF Product Owner,certain,Award redemption proves engagement
H04,any_business AND lead_days <= 1,narrow_to,Corporate|Premium Bleisure,RM International,likely,Same-day business return
```

- `verdict` = **`must_be`** · **`cannot_be`** · **`narrow_to`** (a shortlist, `|`-separated)
- `confidence` = `certain` or `likely` — only `certain` is auto-enforced; `likely` gets tested against
  the data and taken back to the owner if it conflicts

### Ask 2 — SOFT constraints · `data/constraints/soft_constraints.csv`

**What it is:** a *lean*, not a law. "Middle East bookings *tend* to be OFW rather than leisure — but a
Manila–Dubai holiday is perfectly possible." These tilt the ambiguous cases. Their second job matters as
much as the first: they reveal **which boundaries PAL itself considers soft** — i.e. where the model
should report ambiguity instead of forcing a confident label.

**Format — one tendency per row. Seven examples are already in the file:**

```csv
rule_id,condition,leans_toward,leans_away_from,strength,owner,notes
S01,dest_region = 'Middle East' AND max_tier <= 3,OFW/Migrant,Premium Bleisure,strong,RM International,...
S02,dep_month IN (4,5,12),Balikbayan/VFR,Corporate,moderate,RM Domestic,Peak season skews to family
S03,lead_days <= 3 AND max_tier >= 6,Corporate,Last-Minute,strong,RM International,Premium urgency = business
```

- `strength` = `weak` · `moderate` · `strong`
- Where a soft constraint **contradicts the data, that disagreement is the finding** — it gets reported
  back rather than quietly overriding either side

**On format, say this:** CSV is deliberate — it opens in Excel and the `condition` column accepts
near-plain language. **If prose in an email is easier, send that and we'll transcribe it. Format must
never be the blocker; the content is what's scarce.** Column guide: `data/constraints/README.md`.

### Ask 3 — the answer key · `data/labels/sme_sample.csv`

**Roughly 1,000 bookings labelled by hand.** We supply route, dates, lead time, cabin, fare tier,
channel, group flag, issue country and revenue band — nothing more. The SME fills in `true_segment`,
`confidence` (High/Med/Low) and free-text `notes`. Template: `data/labels/sme_sample_TEMPLATE.csv`.

Four design points worth stating:

- **"Unsure" is a first-class answer.** Forcing a guess manufactures noise that cannot then be detected.
- **Stratified, not random.** A uniform random 1,000 yields about 2 Pilgrimage rows and 0 Mabuhay Loyalist.
- **About 100 rows go to *every* SME.** Where SMEs disagree with each other, that rate is a **hard
  ceiling on any accuracy the model could ever claim.** It has to be measured before a score is quoted.
- **8–16 hours of SME time total, ideally split across 2–3 people. The scorer is already written**, so
  results come back the same day the labels land.

### Likely questions

- **"Can't you infer the rules from the data?"** → That was the original approach — see item 1. The data
  shows *where* a line can go, not *where PAL wants it*.
- **"Which single thing helps most?"** → Mabuhay tier data. Without it that segment is effectively
  invisible: 0.03% of bookings, which cannot be true.
- **"How long until we see improvement?"** → The metric improves the same day labels arrive; rule changes
  follow within about a week.

---

## 4 · The decisions only PAL can make — bring these to the table

| Question | Why we can't answer it |
|---|---|
| **6 segments or 10?** | The requirements specify 6; the model produces 10. Both are defensible — it's a commercial choice about how finely PAL wants to act. |
| **How should PH-issued outbound international economy be segmented?** | This is the **9.6% Unassigned** bucket — 2.19M bookings. It needs a definition, not an algorithm. |
| **OFW/Migrant vs Balikbayan/VFR — one segment or two?** | **6.8M bookings** split on a single bit: round trip or not. If PAL treats them the same commercially, merging is the more honest option. |
| **Are the penalty weights right?** | ×10 and ₱40,000 are estimates, and they drive the whole optimisation. |
| **Can we get Mabuhay tier data?** | Without it, Mabuhay Loyalist stays invisible. |

---

## 5 · Two data facts to state before anyone reads a chart

Not our agenda items, but they will come up, and both produce visible nonsense if missed:

1. **The forward-booking cliff.** The extract stops at a single date, so future travel months are still
   filling — September 2026 holds only about 22% of a mature month. **An unfiltered trend chart draws a
   dramatic fake collapse.** Every trend visual must filter on `IsCompleteTravelMonth = TRUE`. 2024 also
   starts in May, so an unguarded full-year comparison puts 12 months against 8.
2. **The requested last-year-vs-current-year pickup measure cannot be built from this extract.** The
   field expected to support it turns out to be departure-month accounting metadata rather than a booking
   snapshot — one single value per departure month, all 37 of them. Pickup needs **repeated dated extracts of the
   same departure months**, which is a new data request to PAL.

---

## 6 · 🔴 Do not say — please read before presenting

Josh won't be in the room, so these guardrails matter more than usual. Each one is a claim that would
not survive scrutiny.

| Don't | Why, and what to say instead |
|---|---|
| **Don't quote a model accuracy or recall figure** | There is no ground-truth number yet. Everything computable today is measured against the rules that produced the labels — circular. Say: *"no validated accuracy figure until the SME labels land."* |
| **Don't call proxy-referenced recall "model accuracy"** | It is agreement with our own rules. This is the single claim most likely to unravel the session. |
| **Don't quote a DBCV figure** | It was never computed on the real extract and doesn't apply to categorical-heavy data. Quote the **0.381** separation ceiling instead. |
| **Don't quote a separability or accuracy figure without the silhouette beside it** | The separability probe scores 0.85–0.99 for almost every method, including ones with essentially no separation — a geometric cut through a continuum is perfectly learnable while being arbitrary. |
| **Don't say a stable result means a real one** | KMeans and k-prototypes were the **most stable** methods in the field with nearly the **least** separation. **Stability is not structure.** |
| **Don't present absolute revenue figures externally** | The extract's revenue field has **no documented unit**. It's plausibly a single currency and the magnitudes look like **USD, not pesos** (a 74 median on a domestic ticket is implausible in pesos). **Ratios and shares are safe; absolutes are not, until PAL confirms the unit.** The ₱ amounts in item 2 are separate — those are PAL's own revenue-at-risk estimates from the requirements document. |
| **Don't describe "Family" as a count of families** | The rule means *ticketed as a group*. The passenger-count field is always 1 by design, so families booking individually are invisible. It is under-counted. |
| **Don't present Unassigned as junk or an error** | 2.19M bookings that out-earn OFW/Migrant per booking, 18.6% flying premium. It is a real gap in the taxonomy, deliberately left blank rather than guessed — and it's an ask, not a defect. |
| **Don't imply Mabuhay Loyalist is a small segment** | 0.03% cannot be true. We have no loyalty-tier field, so award redemption is the only visible signal. **The segment is real; our ability to see it is not.** |

---

## 7 · If you're asked something not covered here

Say it's a fair question, note it, and commit to a written answer rather than improvising — the backing
detail is deep and specific, and a wrong answer costs more than a deferred one.

- **Full narrative with every figure's source:** `docs/stakeholder-report.md`
- **Authoritative methodology spec:** `docs/methodology.md` (start with *Current Methodology at a
  Glance*, which has the pipeline and validation diagrams)
- **Power BI handoff, including per-segment scorecards and persona cards:**
  `docs/powerbi-guide.md`, and `outputs/powerbi_export/START-HERE.md` for the developer
- **Evidence trail, dated:** `docs/knowledge-base.md` §15

---

## The three sentences to close on

1. **What's done:** 22.9M bookings labelled with 10 commercially meaningful segments, delivered into
   Power BI, with the logic written down and reviewable.
2. **What can be defended:** the segments are stable over time, a model fitted a year earlier still
   works, and they predict outcomes the rules never looked at.
3. **What cannot be defended yet — and the ask:** that these are the *right* boundaries for PAL. Every
   accuracy number today is graded against our own rules. **The constraints and roughly 1,000 labelled
   bookings are the unlock, and they cost less than two days of collective SME time.**

---

*Prepared 31 July 2026 by Josh. Questions after the meeting → Josh. Every figure in this pack traces to
`docs/stakeholder-report.md`.*
