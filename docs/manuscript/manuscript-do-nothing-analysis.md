# Appendix A — The Do-Nothing Analysis (FINAL DRAFT)

> **Draft status:** v1.0 (final draft), 23 August 2026. The full version of the economic case
> summarised in Chapter 5 §5.2, written to drop in as **Appendix A** (or, inlined, as
> §§5.2.1–5.2.7). Sources: `docs/do-nothing-vs-implement.md` (21 Aug, the bottom-up measured
> case), `docs/business-case-benchmark.md` (the top-down companion), `docs/segment-cost-research.md`,
> and `outputs/powerbi_export/model/fact_flight/`. Monetary values are USD. The chapter-4
> discipline applies throughout, plus one of its own: **every number below is either measured
> (§§A.3–A.4, A.6 — computed from the extract, reproducible) or assumed (§A.5 — collected in one
> ledger so a reader can replace any entry and recompute)**, and the two are never mixed in a
> single claim. §A.7 resolves the decision without depending on §A.5 at all.

---

## A.1 The Question, and What an Honest Answer Requires

*What does the airline gain by implementing the segmentation, against continuing as it is?*

The dishonest version of this analysis is one line long: pick a plausible uplift percentage,
multiply it by a large revenue figure, report the product. It is dishonest because the uplift is
invented and the revenue is measured, so the output inherits the authority of the measurement
and the arbitrariness of the guess — and nothing in the presentation tells a reader which part
is which. This appendix is built against that failure mode, with three disciplines:

1. **Organise by the decision, not by the benefit.** §A.4 takes the five departments that would
   consume the segmentation and asks, for each: what decision do they own, what does the absence
   of a purpose label force them to do, and what does the data measurably let them do instead?
   A benefit no department owns is not a benefit.
2. **Measure the mechanism, not the outcome.** The measured quantity throughout is *addressable
   value* — revenue that uniform treatment demonstrably mis-aims at. The share of it actually
   recovered is a response rate no data in this study can supply, so it is left as an explicit
   free parameter rather than assumed.
3. **Resolve the decision by breakeven, not forecast** (§A.7). The claim defended is not "the
   benefit is $X"; it is that the decision does not depend on knowing the benefit.

## A.2 What "Doing Nothing" Means

Not "no analytics". The airline already reports by route, cabin, fare brand, and channel. The
counterfactual is specific: **every decision in §A.4 is made through lenses that carry no trip
purpose.** A route knows where a passenger flies, a fare brand knows what they paid, a channel
knows where they bought — none of them knows *why* the passenger is travelling, and none of them
can be aimed at a person. Actions therefore default to the grain the systems report natively —
the route, the fare class, the channel — applied uniformly to everyone inside the cell. This
counterfactual is a construct: it is a defensible reading of "no purpose label available", not
an observation of the airline's current allocation, which the study has not been shown (§A.8).

## A.3 The Measured Base

All measured figures use complete travel year 2025 — the only travel year the extract covers in
full, and therefore the only defensible annual denominator — restricted to flown coupons and
excluding refunds, non-revenue, and revenue-missing rows.

| | |
|---|--:|
| Coupons | 16,155,548 |
| Bookings | 9,832,336 |
| Revenue | **$2,535.0M** |
| Customers (all periods) | 13,435,365 |

Two facts about this base carry the whole appendix. First, **87.8% of customers sit in a single
segment across their entire observed history** (9.4% span two; 2.8% span three or more), so a
segment label attached to a person is a stable attribute — the precondition for segment-based
treatment being coherent at all. Second, a measurement caution discovered during this analysis
and now documented for the airline's BI consumers: segment revenue must be aggregated over
*unfiltered* coupon rows. A plausible-looking primary-coupon filter silently discards every
non-primary coupon's revenue — up to −54% on a multi-leg segment — while still returning a
believable number. The means used here were caught and corrected by an independent cross-check:
they agree within ~7% with per-segment values computed on a different base by a different route
(`segment-cost-research.md` §3).

## A.4 Five Decisions, Five Owners

### A.4.1 Revenue Management — dropping and raising prices

Do-nothing aims a price move at a route × cabin × fare-brand cell; everyone in the cell gets it.
What that cannot see is the value spread *inside* a single label (Table A.1) — measured, at
level 2, on the population-exact sub-types of Chapter 4 §4.2.5.

**Table A.1 — Within-segment value spread on the CY2025 flown base (measured).**

| Parent | Parent mean | Spread | What a uniform price move cannot see |
|---|--:|--:|---|
| Corporate | $429/bk | **5.63×** | `round-trip · short-lead · value` at $965/bk — 1.1% of bookings, 4.2% of revenue — beside `one-way · last-minute · flex` at $171 |
| Leisure | $82/bk | 3.76× | `one-way · advance · supersaver` at $30/bk — 13.8% of *all* bookings, 1.6% of *all* revenue — against `round-trip · advance · saver` at $113 |
| Balikbayan/VFR | $593/bk | 2.68× | `far-advance · saver · nonstop` $997 vs `· connecting` $573 — same fare tier, same trip shape, 1.74× apart |
| OFW/Migrant | $302/bk | 1.60× | narrow — little for level 2 to add |
| Outbound Intl. Leisure | $378/bk | **1.29×** | the most homogeneous parent: level 2 buys pricing almost nothing here, reported rather than averaged away |

The dilution base follows directly: sub-types priced **at or above 1.25× their parent's mean**
are 4 of 20 sub-types, 2,132,261 bookings (22.9% of parent bookings), carrying **$645.8M (29.7%
of parent revenue)**. A parent-uniform discount reaches all of them, and every dollar landing
there is margin loss by construction. At a 1.5× threshold the population sharpens to 3.9% of
parent bookings carrying $358.1M. The cleanest illustration is the Balikbayan/VFR pair: two
cohorts of near-identical size, identical fare tier, both round-trip, both far-advance, 1.74×
apart in value, separated only by whether the itinerary connects — priced identically today
because nothing in the do-nothing lenses distinguishes them. Confidence: high on the spread,
assumed on the recovery. `[Exhibit A.1: within-segment value spread and the dilution base]`

### A.4.2 Sales — prioritising channels

Do-nothing sets channel priority from channel-level volume, which is segment-blind. Measured,
channel mix is a property of the segment, not of the airline: agency dependence spans **6.6×**
(11.8% of Corporate's revenue to 78.2% of Pilgrimage's), so "reduce agency reliance" is a
different project in every segment and in two of them no project at all. **Corporate is 55.5%
corporate-channel** (TMC 42.5% + corporate web portal 13.0%) — effectively a separate
distribution business. And **the sea-crew channel is 27.5% of OFW/Migrant and ~0% of everything
else: a $136.6M channel that is one segment**, each invisible without the other. Confidence:
high — and uniquely, no response assumption is needed to act, because channel prioritisation
reallocates effort already being spent. The measured fact *is* the deliverable. `[Exhibit A.2: agency dependence by segment]`

### A.4.3 Marketing — designing promotions

Do-nothing builds promotions at route or fare-brand level, reaching everyone in the cell. The
measured waste cohort: within Leisure, `one-way · advance · supersaver` is **13.8% of all
bookings at 1.6% of all revenue** ($30 per booking); a "Leisure" promotion spends on it at the
same rate as on a cohort worth 3.8× more. The reverse error costs more: the $645.8M of
above-parent-priced bookings (§A.4.1) is where discount depth is pure margin transfer. The
addressable contact volume — bookings excludable from discount targeting while remaining in
full-fare communication — is 2,132,261 per campaign cycle. Confidence: base measured, response
assumed — and this is the one department where the assumption is testable inside a single
campaign cycle, which makes it the natural instrumentation site (§A.7).

### A.4.4 Customer Experience — web/app and lounge

Do-nothing ships one digital experience for everyone and sets lounge policy by cabin and tier —
the only things visible. Measured, the three CX-relevant behaviours differ by an order of
magnitude across segments: digital revenue share spans **19×** (2.6% Pilgrimage to 48.8%
Leisure — with OFW/Migrant at 10.8%, $481M of revenue arriving almost entirely through humans);
connecting share spans **9×** (10.4% to 97.7%), which makes transfer and lounge experience a
*Balikbayan/VFR* question first — 49.9% connecting on the largest revenue base — not a
premium-cabin one; and premium-cabin concentration sits where lounge economics do (Premium
Bleisure 81.4%, Ultra Wealthy Leisure 79.3%; together $285M on 2.1% of bookings). One anomaly
is surfaced and deliberately not explained: on this base, `Unassigned` is 76.7% premium cabin at
$179 per booking — high cabin, low fare, consistent with Chapter 4 §4.2.1's characterisation —
and it must be diagnosed before any lounge or premium policy is set from this output.
Confidence: high on the behaviours, assumed on any investment-to-benefit conversion.
`[Exhibit A.3: digital and connecting share by segment]`

### A.4.5 Loyalty — churn prevention

Do-nothing runs retention on loyalty tier, which this extract cannot see at all. Measured, the
repeat-rate *floor* spans 3× by segment (36.4% Corporate down to 12.2% Pilgrimage), and the
87.8% single-segment fact means a segment-aimed retention programme reaches a stable population.
But the gap here is structural: **73.9% of customers have exactly one booking and zero tenure,
so in a 26-month window a brand-new customer and a permanently lost one are identical.** The
column is a floor on repeat behaviour, not a churn rate; no churn model can be built on it, and
the between-segment ordering is informative while the levels are not. Mabuhay Loyalist is 100%
award-redemption with 7.8% repeat — an artefact of the missing loyalty field, not a loyalty
population. **Loyalty is the department that should wait, and saying so is part of the honest
case.** `[Exhibit A.4: repeat-behaviour floor by segment]`

### A.4.6 Readiness, which falls out of the evidence

**Table A.2 — Department readiness (the ordering is derived, not preferred).**

| Department | Measured evidence | Needs an assumption to act? | Ready? |
|---|---|---|---|
| Sales — channels | 6.6× agency-dependence spread; a $136.6M single-segment channel | **No** — reallocates existing effort | ✅ first |
| CX — web/app & lounge | 19× digital spread; 9× connecting spread | No, for prioritisation | ✅ first |
| Revenue Management — pricing | 5.63× within-label spread; $645.8M priced ≥1.25× parent mean | Yes — recovery rate | ✅ with instrumentation |
| Marketing — promotions | 13.8% of bookings at 1.6% of revenue | Yes — response rate | ✅ the test site |
| Loyalty — churn | 3× repeat-floor spread | Yes — and the data is right-censored | ⛔ wait for the loyalty field |

The two strongest cases are not the ones with the biggest numbers. Sales and CX act on measured
facts alone; Revenue Management and Marketing carry the larger dollars but need a response
assumption first.

## A.5 The Assumption Ledger — Every Invented Number in One Table

None of these come from the data. They are placeholders chosen to be conservative and legible;
a reader replaces any entry and recomputes, and §A.7 is built so the conclusion survives wide
variation.

**Table A.3 — Assumed parameters.**

| # | Parameter | Value | Basis |
|---|---|--:|---|
| A1 | Blended day rate | $400/day | placeholder |
| A2 | BI developer effort | 20 days | placeholder — the model exists; this is report work |
| A3 | Data/analytics effort | 15 days | placeholder — the pipeline is already written |
| A4 | Annual monitoring & rebuild | 12 days/yr | placeholder — the drift monitor runs in ~1 minute |
| A5 | Year-1 cost | ~~$18,800~~ → **$77,904** | **superseded by the actual all-in budget** (people + cloud + compute), 23 Aug — the one ledger entry that has graduated from placeholder to measurement |
| A6 | Cost per outbound contact | $0.05 | placeholder |
| A7 | Campaign cycles per year | 12 | placeholder |
| A8 | Promo penetration of a parent-level campaign | 25% of parent bookings | placeholder |
| A9 | Average discount depth when offered | 10% of fare | placeholder |
| A10 | Share of avoidable dilution actually recovered | **left free** | not assumed — §A.7 |

Two derived quantities: **avoidable dilution** = $645.8M × A8 × A9 = **$16.1M/yr** of discount
landing on bookings priced at least 25% above their parent's average; **redirectable contact
spend** = 2,132,261 × A6 × A7 = **$1.28M/yr**. Sales, CX, and Loyalty are deliberately not
converted to dollars — the first two because prioritisation reallocates existing effort (any
dollar figure would double-count Revenue Management and Marketing), the third because the data
is censored (§A.4.5).

## A.6 What Do-Nothing Costs, Stated Only as Far as the Measurement Supports

- **$645.8M** of parent revenue sits in cohorts priced ≥1.25× their parent mean, which
  parent-uniform pricing and promotion mis-aim at and which cannot be separated without level 2.
- **$136.6M** of revenue flows through a channel serving essentially one segment, invisible
  without the label.
- **$481M** of one segment's revenue arrives through non-digital channels while app investment
  is justified on a blended 28.3% digital share.
- **$16.1M/yr** of discount reaches above-parent-priced bookings — the only figure in this list
  that depends on assumed parameters (A8, A9).
- A **20× spread** in annual value at risk per customer ($495 to $9,784) that do-nothing cannot
  see.

## A.7 The Decision, Resolved Without Forecasting

At the actual all-in budget of **$77,904 per year**, implementation pays for itself if the
airline recovers

**breakeven A10 = 77,904 / 16,145,000 = 0.48%**

of the modelled avoidable dilution — one dollar in 207. Against the marketing contact lever
alone ($1.28M/yr) the breakeven is **6.1%**, and that lever is verifiable inside one campaign
cycle, which is why §A.4.6 nominates Marketing as the instrumentation site even though Sales and
CX are ready first.

The sensitivity is the point, and it is restated here honestly for the graduated cost basis. The
earlier form of this analysis stressed a placeholder cost by 10×; **the cost is now a measured
budget, so the stress belongs on what is still assumed.** Halve the promo-penetration and
discount-depth placeholders at once (dilution pool $4.04M/yr): breakeven is **1.9%**. Put
staffing at full market rate on top ($487K/yr, the workbook's shadow cost): **12.1%**. The
decision becomes close only if the recovery rate is believed to be near zero — and two of the
five departments need no recovery assumption at all, because they reallocate rather than spend.
The asymmetry exists because the model is already built: the remaining cost is report-building
and monitoring, not research. Costed before the modelling, this analysis would have required a
real forecast and would look different.

The one forward projection is a band, not a line, because the recovery rate is not knowable in
advance and drawing a single line would be the invented number this appendix exists to avoid.
Its assumptions are named before its numbers: the pool does not grow, there is no ramp, and the
recovery rate is constant — all simplifications, all conservative on the benefit side except
the missing ramp.

**Table A.4 — Cumulative value lost to mis-aimed discount, $M (lower is better; pool $16.145M/yr).**

| Cumulative, $M | yr 1 | yr 2 | yr 3 | yr 4 | yr 5 |
|---|--:|--:|--:|--:|--:|
| Do nothing | 16.15 | 32.29 | 48.44 | 64.58 | **80.73** |
| Implement · 1% recovery | 16.00 | 31.99 | 47.98 | 63.97 | 79.96 |
| Implement · 10% recovery | 14.55 | 29.08 | 43.62 | 58.16 | 72.69 |
| Implement · 25% recovery | 12.13 | 24.24 | 36.35 | 48.47 | **60.58** |
| *Cumulative cost (actual budget, 5%/yr escalation)* | *0.08* | *0.16* | *0.25* | *0.34* | *0.43* |

At 1% recovery the implement path is indistinguishable from do-nothing — the honest low end:
recover almost nothing and ~$430K has been spent to change almost nothing. At 25% the gap
reaches $20.1M by year five. Both ends of the band clear the five-year cost — **0.53% of the
five-year pool** — by orders of magnitude, which is why the decision is resolved on breakeven
rather than on where inside the band the truth sits. `[Exhibit A.5: breakeven and the
five-year band]` The top-down benchmark case (+$7.3M
five-year NPV) sizes the same decision from published industry results and enters only as
conditional planning, under the three conditions of Chapter 5 §5.2.

## A.8 What This Analysis Cannot Claim

1. **No accuracy or recall figure exists, and none is used.** There is no SME ground truth, so
   every available validation scores the rules against the rules. Nothing above depends on the
   labels being *correct*: §§A.3–A.4 measure where value and behaviour sit under the partition,
   which is a property of the cut, not of its truth.
2. **No uplift has been measured.** No experiment, holdout, or campaign has run; A10 is left
   free for exactly this reason.
3. **The segments are not natural kinds** (Chapter 4 §4.1.1). Both levels are actionable
   partitions of a smooth space; a booking near a boundary could sit either side.
4. **Loyalty's numbers are right-censored**; only the between-segment ordering is informative.
5. **Two segments are known to be mismeasured** — MICE is valued per booking where its revenue
   is per contract (a floor), and Mabuhay Loyalist is unmeasurable without a loyalty field.
   Neither carries weight in §A.6 or §A.7.
6. **Corporate's measured value is depressed by its own rule's imprecision** (only 6.4% of it
   matches exactly one rule), which *understates* the case for level 2.
7. **One year of clean data.** 2025 is the only complete travel year; no multi-year trend is
   claimed.
8. **The counterfactual is a construct** (§A.2), not an observation of current allocation.

## A.9 What Would Change These Numbers

| Input | Effect |
|---|---|
| Loyalty tier | The only thing that makes §A.4.5 a real department case rather than a deferral |
| Party size | Lets MICE be valued per contract — the largest single understatement |
| Ancillary revenue | Lets CX be quantified rather than prioritised |
| Diagnosing the `Unassigned` premium anomaly | Blocks lounge/premium policy until resolved |
| Fixing the Corporate rule | Raises measured Corporate value and cleans its 5.63× spread |
| **One instrumented Marketing campaign** | Replaces A10 with a measurement and retires §A.8(2) — the cheapest, highest-value next step |
| SME labels | The only thing that retires §A.8(1) |

---

*Exhibits A.1–A.5 (and the readiness table as Exhibit A.6) are rendered as screenshot-ready
plates in the "PAL Manuscript Plates" artifact, Appendix A section, from the same sources as the
tables above.*

*Measured sources: `outputs/powerbi_export/model/fact_flight/` (complete travel year 2025,
flown, revenue-clean), `data/interim/pal_features_customer.parquet` (repeat behaviour, all
periods), `docs/segment-cost-research.md` §3, `outputs/sub_segments/population_profiles.md`.
Assumed: Table A.3. Revenue is USD, confirmed by PAL, 18 August 2026.*
