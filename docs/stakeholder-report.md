# PAL Customer Segmentation — Where We Are, In Plain Language

**For:** PAL commercial stakeholders and project sponsors (non-technical)
**From:** Segmentation team (CPT 3)
**Date:** 31 July 2026
**Companion technical docs:** `docs/methodology.md` (the spec) · `docs/business-requirements.md` (the ask)

---

## 1. The one-paragraph version

We were asked to sort PAL's passengers into meaningful commercial groups so that pricing, marketing
and service can be tailored per group instead of averaged across 16 million people. We have done
that: **every booking in the 38-million-row extract now carries one of ten segment labels**, and the
labels flow through to Power BI. The surprise is *how* we got there. We expected the machine to
discover the segments on its own. It didn't — the passenger base turns out to be a smooth spectrum,
not a set of natural clumps. So we flipped the roles: **PAL's business logic draws the boundaries,
and the machine's job is to check and refine them.** That change makes the deliverable more
defensible, not less — but it does mean the boundaries are only as good as the business rules behind
them, which is exactly where we need SME input now.

---

## 2. The analogy to hold onto

Think of a **fruit stand** versus a **paint store**.

At a **fruit stand**, the categories are obvious. Apples are over here, oranges over there. Nobody
argues about which is which — you can spot the gap between the piles from across the room. If
passengers were like this, we would point an algorithm at the data, it would find the piles, and we
would just name them.

PAL's passengers are a **paint store**. The colours run continuously from white through cream to beige
to tan. There is no natural gap where "cream" ends and "beige" begins. But a paint store still needs
named colours on the shelf — customers can't order "wavelength 578 nanometres." So the store *decides*
where the boundaries go, based on what's useful commercially, and then makes sure the names are
applied consistently.

**That is our model.** We tested exhaustively for the fruit stand and it isn't there. So we build the
paint chart deliberately, using PAL's own commercial logic, and we hold ourselves to a high standard
of consistency and usefulness instead of pretending we discovered natural piles.

Two consequences worth stating out loud:

- **A booking near a boundary is genuinely ambiguous, not misfiled.** Cream-vs-beige cases exist. The
  honest thing is to flag them, not to force a confident-looking label.
- **The boundaries are a business decision, so they are yours to set.** We can tell you where the data
  supports a line and where it doesn't. We cannot tell you what PAL wants to treat as "Corporate."

---

## 3. What the model actually does, step by step

The pipeline is five stages. In plain terms:

| Stage | What it does | Everyday equivalent |
|---|---|---|
| **1. Assemble** | Read 38.1M flight legs from PAL's extract into a fast working format | Unpacking the boxes |
| **2. Clean & flag** | Fix bad revenue values, map fare classes to a value ladder, flag staff travel, awards, group fares, refunds | Sorting out what isn't a paying customer |
| **3. Group up** | Combine flight legs → **bookings** (one purchase decision), then bookings → **customers** | A round trip is one decision, not two |
| **4. Label** | Apply PAL's business rules to give each booking one of 10 segments | **This is the part §4 explains** |
| **5. Deliver** | Push the labels back down to every flight leg and hand Power BI a clean table | Putting the price tags on |

Two numbers give a sense of scale: the 38.1 million flight legs become **22.9 million bookings**,
belonging to **13.4 million customers**.

One important detail about **grouping up**: we work at the *booking* level, not the flight-leg level,
because purpose lives in the purchase decision. Someone flying Manila→Los Angeles and back is on one
trip with one purpose; treating the return leg as a separate journey would make a round-trip
Balikbayan look like two one-way OFWs. And a caveat we state everywhere: **only 26% of customers book
more than once** in three years. So "loyalty" and "lifetime value" features are genuinely informative
for a quarter of the base; for the other 74%, a customer *is* their single booking.

---

## 4. The business rules currently in the model

This is the heart of the deliverable, so it's worth reading slowly.

### 4.1 First, who gets excluded

Before any labelling, we remove people who aren't commercial customers:

- **Staff, industry and complimentary travel** (fare classes A, R, P) — not customers.
- **Customers whose every single booking is non-revenue** — 12,306 of them, removed entirely.
- **Refunds and zero/negative-revenue lines** are flagged so revenue measures can exclude them rather
  than silently absorb them.

The result: BI totals still tie to 38,116,259 rows, but commercial measures can filter cleanly.

### 4.2 The value ladder (from PAL's own dictionary)

Every booking class maps to a fare product, which gives a proper ranking of value. This came from
PAL's V1 data dictionary, so it is authoritative rather than invented:

| Tier | Product | Booking classes |
|---:|---|---|
| 7 | Business Flex | J, C, D |
| 6 | Business Value | I, Z |
| 5 | Premium Economy | W, N |
| 4 | Economy Flex | Y, S, L, M, H |
| 3 | Economy Value | Q, V, B, X |
| 2 | Economy Saver | K, E, T |
| 1 | Economy Supersaver | U, O |

Two classes are **not** fare tiers and are handled specially — **F** means award redemption and **G**
means group fare, but *only from 1 April 2026 onwards*. Before that date the meanings were swapped.
We handle the flip explicitly; missing it would have thrown away ~8,100 award bookings and mislabelled
group travel.

### 4.3 The labelling rules — a waterfall

The rules run **in priority order, and the first match wins**. Think of it as a triage nurse working
down a checklist: the most decisive signal is checked first, and once a booking matches, it stops
there. This matters, because a booking can satisfy several rules at once and the order decides which
one it lands in.

| # | If this is true… | …the booking is labelled | Why this rule |
|---:|---|---|---|
| 1 | Paid with Mabuhay Miles (award redemption) | **Mabuhay Loyalist** | Redeeming miles is definitive proof of loyalty-programme engagement |
| 2 | Booked via corporate channel (TMC / Corporate Web Portal) **or** business cabin with ≤7 days' notice | **Corporate** | Either the channel says "company travel", or the behaviour does — expensive seat, short notice |
| 3 | Flying to Jeddah or Medina | **Pilgrimage** | Destination is unambiguous |
| 4 | Booked through the Sea Crew channel | **OFW/Migrant** | Maritime crew — the channel names it |
| 5 | Ticket issued abroad · international · economy · **one-way** | **OFW/Migrant** | Bought overseas, travelling on a single leg — the migrant-worker pattern |
| 6 | Ticket issued abroad · international · economy · **round trip** | **Balikbayan/VFR** | Same profile but returning — a visit home, not a relocation |
| 7 | Premium cabin on an international route | **Premium Bleisure** | Paying up on a long flight without corporate signals |
| 8 | Group booking | **Family** | Multiple travellers on one purchase |
| 9 | Booked within 3 days of departure | **Last-Minute** | Urgency, whatever the reason |
| 10 | Domestic, non-premium | **Budget/Adventure** | The price-sensitive domestic core |
| — | None of the above | **Unassigned** | Deliberately left blank rather than guessed |

**Notice rules 5 and 6.** OFW/Migrant and Balikbayan/VFR are separated by exactly one thing: whether
the ticket is a round trip. That single bit splits **6.8 million bookings**. It is the weakest
boundary in the whole taxonomy and the first thing we want an SME to rule on.

### 4.4 What this produces

| Segment | Bookings | Share | Avg revenue |
|---|---:|---:|---:|
| Budget/Adventure | 9,037,176 | 39.4% | 74 |
| OFW/Migrant | 3,919,216 | 17.1% | 312 |
| Last-Minute | 2,945,686 | 12.9% | 137 |
| Balikbayan/VFR | 2,911,290 | 12.7% | 618 |
| **Unassigned** | **2,194,061** | **9.6%** | 360 |
| Corporate | 1,001,638 | 4.4% | 493 |
| Premium Bleisure | 481,666 | 2.1% | 1,504 |
| Family | 370,647 | 1.6% | 235 |
| Pilgrimage | 43,617 | 0.2% | 404 |
| Mabuhay Loyalist | 6,453 | 0.03% | 113 |

> **⚠️ Revenue figures are shown without a currency symbol on purpose.** The extract's revenue field
> has **no documented unit**. We verified it is *plausibly* a single currency (median revenue varies
> only 7.3× across 26 major issue countries), and the magnitudes look like **USD** rather than pesos —
> a 74 median on a domestic ticket is implausible in pesos. **Please confirm the unit**; every revenue
> comparison in this report is valid as a *ratio* regardless, but no absolute figure should be quoted
> to a third party until the currency is settled. (The peso amounts in §6 are a separate thing — they
> are PAL's own estimates of revenue-at-risk from the requirements document, not extract values.)

### 4.5 Where the rules are visibly incomplete — read this before using the numbers

Four honest gaps, each with a specific cause:

1. **9.6% of bookings are Unassigned.** The largest cause is a known taxonomy hole: an
   *outbound, Philippine-issued, international, economy* booking — an ordinary Filipino flying abroad
   on a cheap ticket — matches none of the ten rules. We left it blank on purpose rather than sweeping
   it into the nearest segment. **This needs a segment definition from PAL, not a technical fix.**
2. **Mabuhay Loyalist is 0.03%, which cannot be true.** We have no loyalty-tier field, so the only
   loyalty signal available is award redemption — and almost nobody in this extract paid with miles.
   The segment is real; our ability to see it is not. **Mabuhay tier is our single highest-value
   missing field.**
3. **"Family" only means "group booking."** The extract's passenger-count field is always 1 by design
   (it counts flight sectors, not party size), so a genuine family of four booking together is
   invisible unless it was ticketed as a group.
4. **Corporate is diluted by design.** Without loyalty data or a company identifier, "business cabin +
   short notice" also catches the wealthy last-minute leisure traveller. This is the rule most likely
   to change once SMEs weigh in.

---

## 5. What the machine learning actually contributed

We ran this properly before flipping the approach, and it's worth stating what was tested, because
"we tried and it didn't work" is a much weaker claim than what we can actually support.

**Ten different clustering methods across six families** were run on the same data — including three
that need no assumptions about cluster shape at all. Every one of them says the same thing: **no
natural groupings**. The best separation any method achieved was 0.381 on a 0-to-1 scale, where ~0.5
is usually the minimum to claim real structure exists.

Then we asked the harder question — **"or are our methods simply blind?"** We manufactured artificial
segments of known size and distinctness, hid them inside the real data, and checked whether the
methods found them. They did: a planted group is reliably recovered at **2% of bookings and above**.
So the methods work; the clumps genuinely aren't there.

That test also gives us an honest limit to publish alongside the finding: **below about 1% of bookings
— roughly 229,000 — a real segment could exist and we would not have detected it.** We would rather
state that bound than let "no clusters found" imply more certainty than we have.

We also checked the segmentation isn't a one-off snapshot. Splitting the data into two consecutive
12-month periods and re-running everything: **segment sizes hold steady** (largest single shift 1.5
percentage points), and **a model fitted a year earlier still works on the later year.** One caution —
*revenue mix moved more than headcount did.* Balikbayan/VFR held its share of passengers while falling
from 29.4% to 26.6% of revenue. **A segment holding its size is not evidence its value held.**

**So what is the ML doing in the final pipeline?** Three real jobs: splitting oversized segments into
useful sub-groups, independently testing whether the rule boundaries hold up, and providing the drift
monitoring that tells you when the rules have gone stale.

---

## 6. How we'll know if it's working — and a worked example

### 6.1 Why plain accuracy is the wrong target

Ask a warehouse to sort parcels. It gets 90% right. Is that good? It depends entirely on **which** 10%
it got wrong. Mixing up two boxes of identical envelopes costs nothing. Putting the one crate of
medical supplies on the wrong truck is a serious problem — same error rate, wildly different
consequence.

Segmentation is the same. **Mistaking a Corporate traveller for Budget Leisure means under-serving
your most valuable passenger and quoting them a promo fare** — a real revenue loss, estimated at
around ₱40,000 per record. The reverse mistake — treating a budget leisure passenger as Corporate —
costs a courtesy upgrade. **Over-serving is cheap. Under-serving is expensive.** So the errors get
weighted by what they actually cost:

| Segment | Penalty weight | Est. revenue at risk per error |
|---|---:|---:|
| Corporate | ×10 | ₱40,000 |
| Mabuhay Loyalist | ×8 | ₱32,000 |
| OFW/Migrant | ×5 | ₱20,000 |
| Premium Bleisure | ×4 | ₱16,000 |
| Pilgrimage | ×3 | ₱12,000 |
| Balikbayan/VFR · Family · Digital Nomad | ×2 | ₱8,000 |
| Last-Minute · Budget/Adventure | ×1 | ₱4,000 |

### 6.2 The sample calculation

Take a test batch of **1,000 bookings**, at the true segment mix — so 44 are genuinely Corporate and
394 are genuinely Budget/Adventure. Compare two models that score **identically on plain accuracy**:

**Model A — 900 correct, 90% accurate.** Its 100 errors: 20 Corporate mislabelled as Budget, and 80
Budget mislabelled as Last-Minute.

**Model B — 900 correct, 90% accurate.** Its 100 errors: 2 Corporate mislabelled, and 98 Budget
mislabelled.

Now weight the errors by cost:

| | Model A | Model B |
|---|---|---|
| Plain accuracy | 90% | 90% |
| Corporate errors | 20 × ₱40,000 = ₱800,000 | 2 × ₱40,000 = ₱80,000 |
| Budget errors | 80 × ₱4,000 = ₱320,000 | 98 × ₱4,000 = ₱392,000 |
| **Total revenue at risk** | **₱1,120,000** | **₱472,000** |
| **Cost per booking scored** | **₱1,120** | **₱472** |
| Corporate recall (24/44 vs 42/44) | **54.5%** ❌ | **95.5%** ✅ |

**Two models, same accuracy, 2.4× difference in business impact.** Model B is the one you want, and
plain accuracy cannot tell them apart. This is what the asymmetric cost matrix is *for*: it makes the
model care about the passengers PAL cares about.

The two headline numbers we will report per release:

- **Per-segment recall** — of all the genuine Corporate travellers, what share did we catch?
  Target from the requirements: **≥91%**, with Corporate and OFW/Migrant as the priority.
- **Weighted cost per booking** — the peso-weighted error rate. Minimise.

### 6.3 The honest caveat, and why §7 follows from it

**We can compute these numbers today, but they don't yet mean what they appear to mean.** Right now
"correct" is defined as "matches what our own rules said" — so we are grading our own homework. The
scoring machinery is built and tested; **what's missing is an answer key.**

We *have* independently confirmed the segments carry real signal — they predict things the rules never
looked at, like whether a booking gets refunded or rebooked within 180 days. That tells us the labels
aren't noise. It does **not** tell us they're the right labels for PAL's commercial purposes. Only an
SME can settle that.

---

## 7. What we need from the SMEs

Three asks, in priority order. The first is the critical path — it depends on someone else's calendar,
so it's the one we'd like to trigger at this meeting.

### 7.1 Ask 1 — Hard constraints (rules that must never be broken)

A **hard constraint** is a statement of impossibility. "A booking made 60 days in advance, in economy,
with no loyalty ID, **cannot** be Corporate." These are valuable because they're the rules SMEs are
most confident about, and they shrink the problem before anyone has to make a judgement call — instead
of choosing among 10 segments, an annotator picks among 2 or 3.

**File:** `data/constraints/hard_constraints.csv` — **already created and pre-filled with 7 example
rules.** Column guide: `data/constraints/README.md`.
**Format:** one rule per row. First five rows shown:

```csv
rule_id,condition,verdict,segments,owner,confidence,notes
H01,lead_days >= 60 AND max_tier <= 4 AND NOT corp_channel,cannot_be,Corporate,RM Domestic,certain,Corporate travel is booked late and in premium cabins
H02,channel = 'Sea Crew',must_be,OFW/Migrant,RM International,certain,Maritime crew channel is definitive
H03,is_award,must_be,Mabuhay Loyalist,FF Product Owner,certain,Award redemption proves programme engagement
H04,any_business AND lead_days <= 1 AND round_trip,narrow_to,Corporate|Premium Bleisure,RM International,likely,Same-day business return is one of these two only
H05,pilgrimage_dest AND max_tier <= 2,cannot_be,Premium Bleisure,RM International,certain,Pilgrimage traffic is not a bleisure product
```

- `verdict` is one of **`must_be`** (definitively this segment), **`cannot_be`** (rule out), or
  **`narrow_to`** (restrict to a shortlist, `|`-separated).
- `confidence` is `certain` or `likely`. Only `certain` rules are enforced automatically; `likely`
  rules are tested against the data first and brought back to you if they contradict it.
- Rows H01–H05 above are **our current guesses, pre-filled as examples.** We need SMEs to correct,
  delete and extend them — a rule we invented and an SME confirmed is worth far more than a rule we
  invented alone.

### 7.2 Ask 2 — Soft constraints (tendencies, not laws)

A **soft constraint** is a lean, not a law. "Middle East corridor bookings *tend* to be OFW rather than
leisure — but a Manila–Dubai holiday is perfectly possible." These don't forbid anything; they tilt
ambiguous cases and, importantly, they tell us **which boundaries you consider soft** — where we should
report ambiguity rather than force a confident label.

**File:** `data/constraints/soft_constraints.csv` — **already created and pre-filled with 7 example
tendencies.**
**Format:** one tendency per row, with a strength. First five rows shown:

```csv
rule_id,condition,leans_toward,leans_away_from,strength,owner,notes
S01,dest_region = 'Middle East' AND max_tier <= 3,OFW/Migrant,Premium Bleisure,strong,RM International,Corridor is labour-driven but not exclusively
S02,dep_month IN (4,5,12),Balikbayan/VFR,Corporate,moderate,RM Domestic,Peak season skews to visiting family
S03,lead_days <= 3 AND max_tier >= 6,Corporate,Last-Minute,strong,RM International,Premium urgency reads as business not emergency
S04,is_domestic AND n_bookings >= 6,Corporate,Budget/Adventure,weak,RM Domestic,Frequent domestic repeat booking hints at business travel
S05,connecting AND NOT round_trip AND foreign_issue,OFW/Migrant,Family,moderate,RM International,Connecting one-ways from abroad fit relocation
```

- `strength` is `weak` / `moderate` / `strong`.
- Where an SME's soft constraint contradicts what the data shows, **that disagreement is the finding** —
  we will bring it back rather than quietly override either side.

**On format:** CSV is deliberate — it opens in Excel, needs no tooling, and the `condition` column can
be written in near-plain language. If it's easier for SMEs to work in Excel or simply write prose in an
email, **send it in whatever form is easiest and we will transcribe it.** Do not let the format be the
blocker; the content is what's scarce.

### 7.3 Ask 3 — A labelled sample (the answer key)

This is the one that unlocks §6. **We need roughly 1,000 bookings labelled by hand** with the segment
the SME believes each one really is.

**File:** `data/labels/sme_sample.csv` — template already in place at
`data/labels/sme_sample_TEMPLATE.csv`.

We supply a spreadsheet with everything an SME needs to judge and nothing more — route, dates, lead
time, cabin, fare tier, channel, group flag, issue country, revenue band. The SME fills in three
columns: `true_segment` (dropdown of the 10), `confidence` (High/Med/Low) and free-text `notes`.

Four design points worth flagging:

- **"Unsure" is a first-class answer.** Forcing a guess manufactures noise we then cannot detect. If a
  booking is genuinely ambiguous, that is a real and useful data point about our boundaries.
- **The sample is stratified, not random.** A random 1,000 would contain about two Pilgrimage rows and
  zero Mabuhay Loyalists. We over-sample the rare, high-value segments deliberately.
- **~100 rows go to every SME.** Where SMEs disagree with *each other*, that disagreement rate is a
  hard ceiling on any accuracy we could ever claim. We need to measure it before quoting a score.
- **Effort: 8–16 hours total, ideally split across 2–3 SMEs.** The scoring code is already written and
  waiting, so results come back the same day the labels land.

### 7.4 The decisions only PAL can make

| Question | Why we can't answer it |
|---|---|
| Is 6 segments or 10 the deliverable? | The requirements specify 6; the model produces 10. Both are defensible — it's a commercial choice about how finely to act. |
| How should outbound PH-issued international economy be segmented? | This is the 9.6% Unassigned bucket. It needs a definition, not an algorithm. |
| Is OFW/Migrant vs Balikbayan/VFR one segment or two? | 6.8M bookings split on a single bit. If PAL treats them the same commercially, merging is more honest. |
| Are the penalty weights right? | ×10 for Corporate and ₱40,000 per error are our estimates. They drive the whole optimisation and should be PAL's numbers. |
| Can we get Mabuhay tier? | Without it, the Mabuhay Loyalist segment stays effectively invisible. |

---

## 8. Persona cards — who each segment actually is

Segment names and percentages don't make anyone act. A **persona card** does: one card per segment,
showing who this person is, how they behave, what they're worth, and what to do about them.

Everything below is **measured from the 22.9M bookings, not imagined.** Where a card says "books 48
days ahead," that is the median lead time for that segment. The one thing we cannot measure is the
*motivation* — the "why they fly" line — so those are inferences, marked as such.

**How to read the numbers:** *Lead* = median days booked in advance · *RT* = share that are round
trips · *Intl* = share flying international · *Conn* = share with a connection · revenue is given as
**median / average** per booking (the gap between them shows how skewed the segment is), and — as
flagged in §4.4 — **deliberately without a currency symbol until PAL confirms the unit.**

---

### 💼 Corporate — ×10 penalty
**1.00M bookings · 4.4% · 231 median / 493 avg**

| | |
|---|---|
| **Behaviour** | Lead **6 days** · RT 47.6% · Intl 49.3% · **Premium cabin 29.1%** · Conn 16.2% |
| **Where** | Domestic 50.7% · Southeast Asia 19.1% · East Asia 14.9% |
| **How they book** | **TMC / corporate portal** — someone else's system, not a consumer channel |
| **The tell** | Short notice + expensive seat. Half their flying is domestic, which surprises people. **Highest repeat rate in the base — 53.1% book again within 180 days.** |
| **Why they fly** *(inferred)* | Meetings with fixed dates. Schedule beats price; they cannot move the trip. |
| **What they want** | Reliability, lounge, change flexibility, fast rebooking when disrupted |
| **Do not** | Send them promo fares or treat a cancelled meeting as churn |
| **⚠️ Caveat** | Without loyalty or company data, this also catches the wealthy last-minute leisure traveller. Most likely rule to change after SME review. |

### ✈️ Mabuhay Loyalist — ×8 penalty
**6,453 bookings · 0.03% · 22 median / 113 avg**

| | |
|---|---|
| **Behaviour** | Lead **14 days** · RT 38.7% · Intl 85.1% · Conn 32.1% · Group 12.6% |
| **Where** | East Asia 40.5% · Middle East 24.0% · Domestic 14.9% |
| **The tell** | **22 median revenue** — they paid in miles, so the cash line is just taxes. This is the clearest example in the whole set of why *revenue* is not *value*. |
| **Why they fly** *(inferred)* | Accumulated flying, now spending it. Often the family trip they've saved for. |
| **What they want** | Award availability on the routes they actually want, tier recognition, upgrade paths |
| **🚨 This card is not trustworthy** | 0.03% cannot be true. We have no loyalty-tier field, so the only signal is award redemption. **The segment is real; our ability to see it is not.** Fixing this needs Mabuhay tier data, not modelling. |

### 🌏 OFW/Migrant — ×5 penalty
**3.92M bookings · 17.1% · 233 median / 312 avg**

| | |
|---|---|
| **Behaviour** | Lead **14 days** · **RT only 5.9%** · Intl 90.1% · **Conn 38.2%** · Premium 2.5% |
| **Where** | East Asia 30.5% · Southeast Asia 28.3% · North America 14.7% |
| **How they book** | **Traditional travel agency**, ticket issued abroad (top country: US) |
| **The tell** | One-way, bought overseas, economy, often with a connection. **The 5.9% round-trip rate is the signature** — this is relocation, not a holiday. |
| **Why they fly** *(inferred)* | Work abroad. The trip is a life event, planned around a contract, not a calendar. |
| **What they want** | Generous baggage, agency support in-language, payment options, predictable connections |
| **Do not** | Optimise them purely on fare — baggage and connection reliability likely matter more than a small fare saving |
| **Note** | 1.1M of these are Sea Crew, identified by channel with certainty. The open question is the other 72%. |

### 🥂 Premium Bleisure — ×4 penalty
**482k bookings · 2.1% · 1,038 median / 1,504 avg**

| | |
|---|---|
| **Behaviour** | Lead **40 days** · RT 63.0% · **Intl 100% · Premium 100%** · Conn 34.4% · 2.16 coupons |
| **Where** | North America 32.3% · East Asia 29.2% · Southeast Asia 20.3% |
| **The tell** | **Highest revenue per booking of any segment by 2.4×**, and they plan ahead. Premium without corporate signals. |
| **Why they fly** *(inferred)* | Blending work and leisure, or simply affluent leisure — they chose to pay up. |
| **What they want** | Seat comfort, lounge, an experience worth the premium they voluntarily paid |
| **Commercial note** | 2.1% of bookings, but at 1,504 average they punch far above their headcount. Small segments are not low-priority segments. |

### 🕌 Pilgrimage — ×3 penalty
**43.6k bookings · 0.2% · 257 median / 404 avg**

| | |
|---|---|
| **Behaviour** | Lead **10 days** · RT 38.2% · Intl 80.3% · **Conn 95.2%** · Group 5.5% |
| **Where** | **Middle East 77.1%** (Jeddah / Medina) |
| **The tell** | **95.2% connect** — the highest of any segment. Nobody flies MNL–JED directly, so the whole journey is stitched. |
| **Why they fly** *(inferred)* | Religious obligation. Timing is fixed by the calendar, not by price or convenience. |
| **What they want** | Group handling, baggage for gifts, connection reliability above all — a missed connection here is not a rescheduled trip |
| **Note** | Smallest identifiable segment, but the most cleanly defined — destination alone settles it. |

### 🏠 Balikbayan/VFR — ×2 penalty
**2.91M bookings · 12.7% · 471 median / 618 avg**

| | |
|---|---|
| **Behaviour** | Lead **48 days** *(the longest)* · **RT 100%** · Intl 100% · **Conn 39.6%** · **2.61 coupons** *(the most)* |
| **Where** | East Asia 32.4% · North America 27.5% · Southeast Asia 21.1% |
| **How they book** | Traditional travel agency, ticket issued abroad (top country: US) |
| **The tell** | Books furthest ahead, most complex itinerary, always returns. **Planned months out and rarely moved** — the family is expecting them. |
| **Why they fly** *(inferred)* | Coming home to family. Emotional, seasonal, and price-aware but not price-driven. |
| **What they want** | Baggage allowance for pasalubong, group/family seating, peak-season availability |
| **⚠️ Watch this one** | Held its passenger share while **falling from 29.4% to 26.6% of revenue** year on year. A segment holding its size is not evidence its value held. |
| **⚠️ Boundary risk** | Separated from OFW/Migrant by **one bit** — round trip or not. 6.8M bookings hinge on it. Top SME question. |

### 👨‍👩‍👧 Family — ×2 penalty
**371k bookings · 1.6% · 205 median / 235 avg**

| | |
|---|---|
| **Behaviour** | Lead **9 days** · RT 59.8% · Intl 55.0% · **Group 100%** · Premium 0.4% |
| **Where** | Domestic 45.0% · East Asia 22.7% · Middle East 18.8% |
| **The tell** | Ticketed as a group. Books late for a leisure trip — 9 days is closer to Corporate than to Balikbayan. |
| **Why they fly** *(inferred)* | Travelling as a party — reunions, holidays, group events. |
| **What they want** | Seating together, simple group changes, baggage, kid-friendly handling |
| **⚠️ Caveat** | This segment means **"ticketed as a group,"** not "is a family." The passenger-count field is always 1 by design, so a genuine family of four booking individually is invisible here. Under-counted, certainly. |

### ⚡ Last-Minute — ×1 penalty
**2.95M bookings · 12.9% · 99 median / 137 avg**

| | |
|---|---|
| **Behaviour** | Lead **1 day** · RT 20.7% · Intl 8.2% · Premium 7.7% |
| **Where** | Domestic 91.8% |
| **How they book** | Web / app — self-serve, fast |
| **The tell** | Almost entirely domestic, booked the day before, one-way. **46.7% book again within 180 days** — second only to Corporate (53.1%), and well above Balikbayan/VFR (18.8%). They come back. |
| **Why they fly** *(inferred)* | Something happened. Family emergency, sudden work need, a plan that changed. |
| **What they want** | Availability, a booking flow that works on a phone under stress, easy changes |
| **Commercial note** | Low value per booking but high repeat rate — this is a **volume and goodwill** segment, not a yield segment. Cross-cuts the others behaviourally. |

### 🎒 Budget/Adventure — ×1 penalty
**9.04M bookings · 39.4% · 56 median / 74 avg**

| | |
|---|---|
| **Behaviour** | Lead **23 days** · RT 39.5% · **Domestic 100% · Premium 0%** · 1.50 coupons |
| **Where** | Domestic only |
| **How they book** | Web / app |
| **The tell** | **The largest segment by far — 4 in 10 bookings — and the cheapest at 56 median.** This is where the LCC fight happens. |
| **Why they fly** *(inferred)* | Leisure within the Philippines, price-led, flexible on timing. |
| **What they want** | Price transparency, promos, no surprises at check-in |
| **Commercial note** | Individually low-value, collectively enormous. This segment is the one most exposed to Cebu Pacific and AirAsia promo pricing. |

### ❓ Unassigned — no penalty assigned
**2.19M bookings · 9.6% · 260 median / 360 avg**

| | |
|---|---|
| **Behaviour** | Lead **35 days** · RT 65.5% · Intl 81.4% · **Premium 18.6%** · Conn 21.0% |
| **Where** | East Asia 36.2% · Southeast Asia 25.8% · Domestic 18.6% |
| **The tell** | **This is not junk.** At 360 average it out-earns OFW/Migrant, and 18.6% fly premium. It is mostly one identifiable group: **an ordinary Filipino, ticket issued in PH, flying abroad in economy** — who matches none of our ten rules. |
| **Why it exists** | A hole in the taxonomy, not a modelling failure. We left it blank rather than sweeping 2.19M bookings into the nearest segment. |
| **🚨 The ask** | **PAL needs to define this segment.** It is the single largest actionable gap in the deliverable, and it needs a commercial definition, not an algorithm. |

---

### How to actually present these

Four options, in the order we'd recommend:

1. **One slide per segment in the deck** — the four high-penalty segments only (Corporate, Mabuhay,
   OFW/Migrant, Premium Bleisure) plus Unassigned as the ask. Five slides. Trying to present ten is
   how a deck loses a room.
2. **A printable one-page card sheet** — all ten on two sides of A4, for people who want the reference
   after the meeting. We can generate this from the same numbers.
3. **A Power BI page** — one card visual per segment, filtered live so the numbers move when someone
   slices by route or quarter. Highest effort, highest credibility, and it makes the cards
   self-updating rather than a snapshot.
4. **This document** — the full version with caveats attached, for anyone who wants to check a claim.

Our suggestion: **option 1 for Tuesday, option 2 as the handout.** Say the word and we'll generate
the card sheet — either as a shareable web page or as a PDF/PowerPoint-ready layout.

> **A note on honesty in persona cards.** Persona cards are persuasive, which makes them dangerous.
> A card that says "Mabuhay Loyalist: 0.03% of bookings" invites someone to conclude the loyalty
> programme is irrelevant, when the truth is that we cannot see it. **Every caveat above travels with
> its card.** If these get reused in a deck, please keep the ⚠️ and 🚨 lines attached.

---

## 9. Dashboard *(not this report's item — owned separately)*

Power BI review sits with the dashboard owner; walkthrough and screenshots are in
`docs/powerbi-guide.md` and `outputs/pbip/README.md`. Two data facts from our side that any dashboard
reader needs, because they will otherwise misread a chart:

1. **The forward-booking cliff.** The extract stops at one date, so future travel months are still
   filling — September 2026 holds only ~22% of a mature month. An unfiltered trend chart draws a
   **dramatic fake collapse**. Guard flags ship with the data (`IsCompleteTravelMonth`,
   `IsCompleteTravelYear`) and every trend visual must filter on them. 2024 also starts in May, so an
   unguarded full-year comparison puts 12 months against 8.
2. **The requested "pickup vs last year" measure cannot be built from this extract.** The field we
   expected to support it is departure-month accounting metadata, not a booking snapshot — 8 distinct
   values across all 37 months. Genuine pickup needs lead-time-based measures (shipped) or **repeated
   dated extracts of the same departure months**, which is a new data request to PAL.

---

## 10. Bottom line

**What's done:** a complete, running pipeline that labels 22.9M bookings with 10 commercially
meaningful segments, delivered into Power BI, with the labelling logic written down and reviewable.

**What we learned that changed the plan:** the passenger base is a spectrum, not a set of natural
clumps — tested ten ways, then stress-tested to prove our methods weren't simply blind. So business
logic draws the lines and ML checks them, rather than the reverse.

**What we can defend:** the segments are stable over time, a model fitted a year earlier still works,
and the segments predict outcomes the rules never looked at.

**What we cannot defend yet:** that these are the *right* boundaries for PAL's commercial purposes.
Every accuracy number we have is currently graded against our own rules.

**The single most valuable thing anyone can do for this project this week:** get the hard/soft
constraints and ~1,000 labelled bookings into SME hands. Everything downstream is waiting on it, the
scoring machinery is already built, and it costs SMEs less than two days of collective effort.

---

*Prepared for the 4 August 2026 stakeholder meeting. Technical detail behind every claim here lives in
`docs/methodology.md`; the evidence trail is in `docs/knowledge-base.md` §15.*
