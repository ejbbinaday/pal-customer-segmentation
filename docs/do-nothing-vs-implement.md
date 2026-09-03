# Do nothing vs implement the segmentation — a benefits analysis

> **Companion:** `business-case-benchmark.md` is the top-down, benchmark-derived NPV case (imported 23 Aug 2026). This document is the bottom-up measured one; manuscript Chapter 5 §5.2 reconciles the two, including the year-1 cost update ($18,800 placeholder → $77,904 actual budget, breakeven 0.116% → 0.48%).

**Written:** 21 August 2026 · **Audience:** defence panel · **Status:** analysis, not a PAL proposal.

> **Read this first.** Every figure below is one of two kinds, and the document never mixes them.
> **§3–§4 are measured** — computed from the 38.1M-coupon extract, reproducible, no judgement.
> **§5 is assumed** — response and cost parameters no data in this project can supply, collected in one
> table so a reader can replace them and recompute. §7 resolves the decision *without* depending on §5,
> and §8 states what this analysis cannot claim.

---

## 1. The question, and what would make an honest answer

*What does PAL gain by implementing the segmentation, against continuing as it is?*

The dishonest version picks a plausible uplift percentage, multiplies it by a large revenue figure, and
reports the product. It is dishonest because the uplift is invented and the revenue is real, so the output
inherits the authority of the measurement and the arbitrariness of the guess, and nothing in the
presentation tells them apart.

This analysis instead:

1. **Organises by the decision, not by the benefit.** §4 takes the five departments that would consume the
   output and asks, for each: *what decision do they own, what does the absence of a segment label force
   them to do, and what does the data measurably let them do instead?* A benefit no department owns is not
   a benefit.
2. **Measures the mechanism, not the outcome.** The measured quantity is *addressable value*; the recovery
   rate is left as an explicit parameter.
3. **Resolves the decision by breakeven, not forecast** (§7).

## 2. What "do nothing" actually means

Not "no analytics". PAL already has route, cabin, farebrand and channel reporting. The counterfactual is
specific: **every decision in §4 is made using lenses that carry no trip purpose.** A route knows where a
passenger flies, a farebrand knows what they paid, a channel knows where they bought — **none of them knows
why they are travelling, and none of them can be aimed at a person.** So actions default to the
grain the system reports natively: the route, the fare class, the channel — applied uniformly to everyone
inside it.

## 3. The measured base

Complete travel year **2025**, flown coupons only, excluding refunds, non-revenue and revenue-missing rows.
2025 is the only travel year the extract covers completely (`IsCompleteTravelYear`), so it is the only
defensible annual denominator. Revenue is **USD**, per PAL answer B5.

| | |
|---|--:|
| Coupons | 16,155,548 |
| Bookings | 9,832,336 |
| Revenue | **$2,535.0M** |
| Customers (all periods) | 13,435,365 |

**One structural fact underpins all five departments:** **87.8% of customers have `segment_diversity = 1`**
— across their whole history they sit in a single segment. A segment label on a *person* is therefore
stable, not a per-trip accident, which is what makes segment-based treatment coherent at all. 9.4% span
two segments; 2.8% span three or more.

## 4. The five departments

### 4.1 Revenue Management — dropping and raising prices

**Decision owned:** which fares to drop, which to hold or raise, and on what booking horizon.

**What do-nothing forces:** a price move is aimed at a route × cabin × farebrand cell. Everyone in that
cell gets it, because there is no finer thing to aim at.

**Measured — the value spread *inside* a single label:**

| Parent | Parent mean | Spread | What a uniform price move cannot see |
|---|--:|--:|---|
| Corporate | $429/bk | **5.63×** | `round-trip · short-lead · value` at **$965/bk** — 1.1% of bookings, **4.2% of revenue** — beside `one-way · last-minute · flex` at **$171** |
| Leisure | $82/bk | **3.76×** | `one-way · advance · supersaver` at **$30/bk** — **13.8% of all PAL bookings, 1.6% of all revenue** — against `round-trip · advance · saver` at $113 |
| Balikbayan/VFR | $593/bk | **2.68×** | `far-advance · saver · nonstop` **$997** vs `· connecting` **$573** — same fare tier, same trip shape, 1.74× apart |
| OFW/Migrant | $302/bk | 1.60× | narrow — little for level 2 to add |
| Outbound Intl. Leisure | $378/bk | **1.29×** | the most homogeneous parent. **Level 2 buys RM almost nothing here**, and that is reported rather than averaged away |

These parent means reconcile independently with `segment-cost-research.md` §3, computed on a different
base (full extract, all periods) by a different route: $593 vs $615 Balikbayan/VFR, $82 vs $80 Leisure,
$302 vs $312 OFW/Migrant, $429 vs $460 Corporate. Agreement within ~7% across eleven segments.

**Dilution base.** Sub-types priced **at or above 1.25× their parent's mean** — materially above, not
marginally — are **4 of 20 sub-types, 2,132,261 bookings (22.9% of parent bookings), carrying $645.8M
(29.7% of parent revenue)**. A parent-level discount reaches all of them, and every dollar landing there is
margin loss by construction. At a 1.5× threshold it sharpens further: **2 sub-types, 3.9% of parent
bookings, 16.4% of parent revenue ($358.1M)**.

The Balikbayan/VFR row is the cleanest illustration: two cohorts of near-identical size (251,954 and
271,500 bookings), identical fare tier, both round-trip, both far-advance, **1.74× apart in value**,
separated only by whether the itinerary connects. RM prices them identically today because nothing
distinguishes them.

**Confidence: high on the spread, assumed on the recovery.**

### 4.2 Sales — prioritising channels

**Decision owned:** where distribution effort, incentives and commercial terms go.

**What do-nothing forces:** channel priority follows channel-level volume, which is segment-blind:

| Channel | 2025 revenue | Share |
|---|--:|--:|
| Traditional Travel Agency | $810.9M | 32.0% |
| WEB/APP | $717.4M | 28.3% |
| OTA | $380.3M | 15.0% |
| Contact Center | $165.7M | 6.5% |
| Sea Crew | $136.6M | 5.4% |
| Ticket Office | $132.0M | 5.2% |

**Measured — channel mix is not a property of PAL, it is a property of the segment.** Share of each
segment's own revenue, by channel:

| Segment | 2025 rev | Agency | WEB/APP | OTA | Sea Crew | TMC | Corp Portal |
|---|--:|--:|--:|--:|--:|--:|--:|
| Balikbayan/VFR | $712M | **44.2%** | 23.1% | 21.9% | — | — | — |
| OFW/Migrant | $481M | 31.7% | 10.8% | 22.6% | **27.5%** | — | — |
| Leisure | $418M | 26.4% | **48.8%** | 10.8% | — | — | — |
| Outbound Intl. Leisure | $337M | 26.6% | 43.2% | 3.6% | — | — | — |
| Corporate | $230M | 11.8% | 14.0% | 5.7% | — | **42.5%** | **13.0%** |
| Premium Bleisure | $167M | 31.8% | 30.1% | 16.3% | — | — | — |
| Ultra Wealthy Leisure | $118M | 31.8% | 35.6% | 11.0% | — | — | — |
| Intl. Student | $18M | 45.2% | 26.1% | 9.1% | — | — | — |
| Pilgrimage | $7M | **78.2%** | 2.6% | 7.6% | 4.1% | — | — |
| MICE | $3M | 66.2% | **0.0%** | 0.0% | 1.9% | — | — |

Three findings a segment-blind view cannot produce:

- **Agency dependence spans 6.6× — 11.8% (Corporate) to 78.2% (Pilgrimage).** "Reduce agency reliance" is
  a different project in every segment, and in two of them it is not a project at all.
- **Corporate is 55.5% corporate-channel** (TMC 42.5% + Corporate Web Portal 13.0%) and only 11.8% agency.
  It is effectively a separate distribution business inside PAL.
- **Sea Crew is 27.5% of OFW/Migrant and ~0% of everything else** — a $136.6M channel serving one segment.
  Its performance is that segment's performance, and vice versa; neither is visible alone.

**Confidence: high, and uniquely, no response assumption is needed to act.** Channel prioritisation is a
reallocation of existing effort, not a new spend. The measured fact *is* the deliverable.

### 4.3 Marketing — designing promos

**Decision owned:** who receives which offer, at what depth, how often.

**What do-nothing forces:** promos are built at route or farebrand level and reach everyone in the cell.

**Measured — the cohort a blanket promo wastes itself on.** Within Leisure, `one-way · advance ·
supersaver` is **13.8% of all PAL bookings but 1.6% of all revenue, at $30 per booking.** A promo aimed at
"Leisure" spends on that cohort at the same rate as on `round-trip · advance · saver` at $113 — 3.8× its
value. The reverse error costs more: the $645.8M in sub-types priced ≥1.25× their parent mean (§4.1) is
where discount depth is pure margin loss.

**Addressable contact volume:** 2,132,261 bookings per campaign cycle sit in those sub-types and could be
excluded from discount targeting while remaining in full-fare communication.

**Confidence: base measured, uplift assumed.** This is also the department where the assumption is most
testable — see §7.

### 4.4 CX — Web/App and lounge

**Decision owned:** where digital experience investment goes; who the lounge and transfer experience is
built for.

**What do-nothing forces:** one web/app experience for everyone, and lounge access set by cabin and tier —
the only two things visible.

**Measured — the three CX-relevant behaviours differ by an order of magnitude across segments:**

| Segment | 2025 rev | Digital rev share | Connecting | Premium cabin |
|---|--:|--:|--:|--:|
| Balikbayan/VFR | $712M | 23.1% | **49.9%** | 0.3% |
| OFW/Migrant | $481M | 10.8% | 45.8% | 1.1% |
| Leisure | $418M | **48.8%** | 10.4% | 0.0% |
| Outbound Intl. Leisure | $337M | 43.2% | 31.9% | 0.0% |
| Corporate | $230M | 14.0% | 15.8% | 26.6% |
| Premium Bleisure | $167M | 30.1% | 38.0% | **81.4%** |
| Ultra Wealthy Leisure | $118M | 35.6% | 41.0% | 79.3% |
| Pilgrimage | $7M | **2.6%** | **97.7%** | 2.8% |

- **Digital share spans 19× — 2.6% to 48.8%.** App investment is worth most to Leisure and Outbound
  Intl. Leisure; it is nearly irrelevant to Pilgrimage and thin for OFW/Migrant at 10.8%, which is
  $481M of revenue arriving almost entirely through humans.
- **Connecting share spans 9× — 10.4% to 97.7%.** Connecting passengers dwell at the hub, so transfer and
  lounge experience is a *Balikbayan/VFR* question first (49.9% connecting on the largest revenue base),
  not a premium-cabin question.
- **Premium concentration is where lounge economics actually sit:** Premium Bleisure 81.4% and Ultra
  Wealthy Leisure 79.3%, together $285M on 2.1% of bookings.

> ⚠️ **An anomaly this analysis surfaced and does not explain.** `Unassigned` is **76.7% premium cabin at
> $179 per booking** — high cabin, low fare, surviving the non-revenue and award filters (252,118
> bookings, $45.2M, against a $258 all-segment average). Either a rule gap catching discounted premium travel, or a fare-data problem. **It must be
> diagnosed before any lounge or premium-cabin policy is set from this output**, and it is precisely the
> kind of thing a segment-blind view cannot surface.

**Confidence: high on the behaviours, assumed on the investment-to-benefit conversion.**

### 4.5 Loyalty — churn prevention

**Decision owned:** who to retain, with what intervention.

**What do-nothing forces:** retention runs on Mabuhay tier — which this project cannot see at all.

**Measured — repeat rate differs 3× by segment:**

| Segment | Customers | Repeat rate | Mean bookings |
|---|--:|--:|--:|
| Corporate | 463,430 | **36.4%** | 2.37 |
| Premium Bleisure | 180,370 | 35.2% | 1.81 |
| Ultra Wealthy Leisure | 97,263 | 31.4% | 1.55 |
| Outbound Intl. Leisure | 1,296,005 | 31.2% | 1.62 |
| Leisure | 6,430,748 | 25.9% | 1.84 |
| OFW/Migrant | 2,539,816 | 25.3% | 1.53 |
| Balikbayan/VFR | 2,160,377 | 21.3% | 1.40 |
| MICE | 19,069 | 13.1% | 1.16 |
| Pilgrimage | 37,583 | **12.2%** | 1.15 |
| Mabuhay Loyalist | 3,725 | 7.8% | 1.10 |

And **87.8% of customers never leave their segment** (§3), so a retention programme aimed at a segment
reaches a stable population rather than a transient one.

> ⚠️ **This is the weakest of the five, and the gap is structural, not fixable by effort.**
> **73.9% of customers have exactly one booking and `tenure_days = 0`.** In a 26-month window a
> brand-new customer and a permanently lost one are *identical* — the data is right-censored. So the
> column above is a **floor on repeat behaviour, not a churn rate**, and no churn model can be built
> on it. The between-segment *ordering* is still informative; the levels are not.
> Separately, **Mabuhay Loyalist is 100% `ever_award` and 7.8% repeat** — it is an award-redemption
> artifact, not a loyalty population, because there is no loyalty-tier field (PAL answer B4).
> **Loyalty is the department that should wait**, and saying so is part of the honest case.

### 4.6 Summary — which departments the output is actually ready for

| Department | Measured evidence | Needs an assumption to act? | Ready? |
|---|---|---|---|
| **Sales** — channels | 6.6× spread in agency dependence; Sea Crew ≈ one segment | **No** — reallocates existing effort | ✅ **First** |
| **CX** — web/app & lounge | 19× digital spread; 9× connecting spread | No, for prioritisation | ✅ **First** |
| **Revenue Management** — pricing | 5.63× within-label spread; $645.8M priced ≥1.25× parent mean | Yes — recovery rate | ✅ with instrumentation |
| **Marketing** — promos | 13.8% of bookings at 1.6% of revenue | Yes — response rate | ✅ **best place to test** |
| **Loyalty** — churn | 3× repeat-rate spread | Yes, and the data is censored | ⛔ **wait for B4** |

**The two departments with the strongest case are not the ones with the biggest number.** Sales and CX can
act on measured facts alone, because prioritisation reallocates effort that is already being spent. RM and
Marketing carry the larger dollars but need a response assumption. That ordering is the practical
recommendation, and it falls out of the evidence rather than out of preference.

## 5. Assumed — every invented number, in one table

**None of these come from the data.** Placeholders, chosen to be conservative and legible. Replace them
and recompute; §7 is built so the conclusion survives wide variation.

| # | Parameter | Placeholder | Basis |
|---|---|--:|---|
| A1 | Blended day rate | $400/day | placeholder |
| A2 | BI developer effort | 20 days | placeholder — the model exists; this is report work |
| A3 | Data/analytics effort | 15 days | placeholder — the pipeline is already written |
| A4 | Annual monitoring & rebuild | 12 days/yr | placeholder — `monitor_real.py` runs in ~1 min |
| A5 | **Year-1 cost** | **$18,800** | = (A2+A3+A4) × A1 |
| A6 | Cost per outbound contact | $0.05 | placeholder |
| A7 | Campaign cycles per year | 12 | placeholder |
| A8 | Promo penetration of a parent-level campaign | 25% of parent bookings | placeholder |
| A9 | Average discount depth when offered | 10% of fare | placeholder |
| A10 | Share of avoidable dilution actually recovered | **left free** — §7 | not assumed |

**RM + Marketing (dilution).** $645.8M × A8 × A9 = **$16.1M/yr** of discount landing on bookings priced
at least 25% above their parent's average.

**Marketing (contact).** 2,132,261 × A6 × A7 = **$1.28M/yr** of contact spend redirectable.

**Sales, CX and Loyalty are not converted to dollars.** Sales and CX because prioritisation reallocates
existing effort and any dollar figure would be double-counting RM and Marketing; Loyalty because the data
is censored (§4.5).

## 6. What do-nothing costs, stated only as far as the measurement supports

- **$645.8M** of parent revenue is in cohorts priced ≥1.25× their parent mean, which a parent-uniform
  price or promo mis-prices and which cannot be separated without level 2 (§4.1).
- **$136.6M** of revenue flows through a channel serving essentially one segment, whose performance is
  invisible without the segment label (§4.2).
- **$481M** of revenue arrives through non-digital channels in one segment while app investment is
  justified on a blended 28.3% digital share (§4.4).
- **$16.1M/yr** of discount reaches bookings priced ≥1.25× their parent average — the only figure here
  that depends on invented parameters (§5).
- **20× spread** in annual value per passenger, $495 to $9,784, that do-nothing cannot see
  (`segment-cost-research.md` §3).

## 7. The decision, resolved without forecasting

Year-1 cost **$18,800** (A5). Against RM + Marketing dilution of $16.1M/yr, implementation pays for itself
if PAL recovers:

$$\text{breakeven A10} = \frac{18{,}800}{16{,}145{,}000} = \mathbf{0.116\%}$$

**One dollar in 859.** Against the Marketing contact lever alone ($1.28M/yr) breakeven is **1.47%** — and
that lever is verifiable inside one campaign cycle, which is why §4.6 nominates Marketing as the test site
even though Sales and CX are ready first.

**Sensitivity is the point.** Make every placeholder ten times worse at once — cost 10× higher ($188,000),
penetration and discount depth each halved (dilution $4.04M) — and breakeven is **4.7%**. Cost 100× higher
with the base halved again: **93%**. The decision only becomes close under assumptions two orders of
magnitude from the placeholders, in both directions simultaneously.

**The defensible conclusion is not that the benefit is $16M. It is that the decision does not depend on
knowing the benefit** — and that two of the five departments (§4.6) need no benefit estimate at all,
because they reallocate effort rather than spend more. The asymmetry exists because the model is already
built: the remaining cost is report-building and monitoring, not research. **Costed before the modelling,
this analysis would have required a real forecast and would look very different.**

## 7a. The five-year picture — a band, not a line

This is the one place the document projects forward, so the extra assumptions are named before the numbers,
not after them: **the pool does not grow** (no traffic or fare growth modelled), **there is no ramp**
(recovery starts at full rate in year 1), and **the recovery rate is constant**. All three are
simplifications; all are conservative on the benefit side except the missing ramp.

**There is no single "implement" line, because the recovery rate is not knowable in advance** (A10).
Drawing one would be the invented number this analysis exists to avoid. So implement is a **band** spanning
1% to 25% recovery, and a reader locates their own belief inside it.

Cumulative value lost to mis-targeted discount, $M — lower is better. Pool = $16.145M/yr (§5):

| Cumulative, $M | now | yr 1 | yr 2 | yr 3 | yr 4 | yr 5 |
|---|--:|--:|--:|--:|--:|--:|
| **Do nothing** | 0.00 | 16.15 | 32.29 | 48.44 | 64.58 | **80.73** |
| Implement · 1% recovery | 0.00 | 16.00 | 31.99 | 47.98 | 63.97 | 79.96 |
| Implement · 10% recovery | 0.00 | 14.55 | 29.08 | 43.62 | 58.16 | 72.69 |
| **Implement · 25% recovery** | 0.00 | 12.13 | 24.24 | 36.35 | 48.47 | **60.58** |
| *Cumulative cost* | 0.00 | 0.019 | 0.024 | 0.028 | 0.033 | *0.038* |

**What the shape says.** At **1% recovery the implement line sits 2.6 pixels from the do-nothing line**
when plotted — indistinguishable, and left deliberately unlabelled in the chart rather than nudged apart.
That is the honest low end: recover almost nothing and you have spent $38,000 to change almost nothing. At
**25% recovery the gap reaches $20.1M** by year five. Both ends of the band clear the cost by orders of
magnitude — the five-year cost is **0.047% of the pool** — which is why §7 resolves the decision on
breakeven rather than on where inside this band the truth sits.

*The chart version of this table is in the published page; the plotted palette is deliberately two
validated sequential steps, so the 10% row appears in the table and tooltip but is not drawn.*

## 8. What this analysis cannot claim

1. **No accuracy or recall figure exists, and none is used.** There is no SME ground truth, so every
   validation available today scores the rules against the rules — circular. `rule_confidence.py`'s 66.5%
   was computed on **v1** labels and the script still hard-codes the v1 waterfall, so there is no current
   figure at all. **Nothing above depends on the labels being correct** — §3 and §4 measure where value and
   behaviour sit *under* the partition, which is a property of the cut, not of its truth.
2. **No uplift has been measured.** No experiment, holdout or campaign has run. A10 is left free for
   exactly this reason.
3. **The segments are not natural kinds.** The base is a continuum; ten methods across six families found
   no natural clusters. Both levels are actionable partitions of a smooth space, so a booking near a
   boundary could sit either side.
4. **Loyalty's numbers are right-censored** (§4.5). 73.9% single-booking customers means no churn rate can
   be computed, only a floor on repeat behaviour.
5. **Two segments are known to be mismeasured.** MICE is valued per booking where its revenue is per
   contract, so its $1,184/yr is a floor. Mabuhay Loyalist is unmeasurable without a loyalty-tier field.
   Neither carries weight in §6 or §7.
6. **Corporate's measured value is depressed by its own rule** — only 6.4% of it matches exactly one rule,
   25.6% matches three or more. Its **5.63×** internal spread is partly the rule's imprecision. This
   *understates* the case for level 2 rather than overstating it.
7. **One year of clean data.** 2025 is the only complete travel year. No multi-year trend is claimed.
8. **The counterfactual is a construct.** §2 is a defensible reading of "no purpose label available", not
   an observation of PAL's current allocation, which we have not been shown.

## 9. What would change these numbers

| Input | Effect |
|---|---|
| **Loyalty tier** (PAL B4) | The only thing that makes §4.5 a real department case rather than a deferral. |
| **Party size** (B3) | Lets MICE be valued per contract — the largest single understatement. |
| **Ancillary revenue** | Would let CX (§4.4) be quantified rather than prioritised. |
| **Diagnosing the `Unassigned` premium anomaly** | Blocks lounge/premium policy until resolved. |
| **Fixing the Corporate rule** | Raises measured Corporate value and cleans its 5.63× spread. |
| **One instrumented Marketing campaign** | Replaces A10 with a measurement and retires §8.2. Cheapest, highest-value next step. |
| **SME labels** | The only thing that retires §8.1. |

---

*Measured: `outputs/powerbi_export/model/fact_flight/` (complete travel year 2025, flown, revenue-clean),
`data/interim/pal_features_customer.parquet` (repeat behaviour, all periods),
`docs/segment-cost-research.md` §3 (annual value at risk), `outputs/rule_confidence/`. Assumed: §5, all
placeholders. Revenue is USD per PAL answer B5.*
