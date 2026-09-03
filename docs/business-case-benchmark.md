> **Provenance & scope (added on import, 23 Aug 2026).** This is the **top-down, benchmark-derived**
> business case (companion workbook, Aug 2026), imported verbatim below the rule. It answers a
> different question from `do-nothing-vs-implement.md`, the **bottom-up measured** case built from the
> extract: this document sizes the expected value *if published industry benchmarks transfer*; the
> bottom-up case shows the decision *does not depend* on any benefit forecast (breakeven 0.116% at its
> $18.8K placeholder cost — **0.48% at this document's $77,904 actual budget**). Known reconciliation
> items, argued in manuscript Chapter 5 §§5.2–5.3: the revenue base here ($1.96B) is ~⅓ below the
> extract's measured ~$2.9B/yr; the ancillary lever (45% of the claimed benefit) rests on revenue the
> extract does not contain; the retention/churn lever is not computable on current data (73.9% of
> customers are single-booking); and the vendor case studies are identified-customer results applied
> to an anonymous-PNR model. Quote this document's numbers with those conditions attached.

---

# Do Nothing vs Implement: The Passenger Segmentation Model

> **For $78K a year — our actual all-in budget — the segmentation model returns about $2.7M a year in margin once ramped. Over five years that is +$7.3M in net present value; doing nothing quietly forfeits $7.6M.**

Airline of ~16.3M passengers/yr · benefits deliberately modeled at ~2% of the IATA–McKinsey industry benchmark, risk-adjusted · all figures USD · Aug 2026

---

## Headline numbers

| | |
|---|---|
| **What it costs us per year** | **$78K** — actual budget: people + cloud + compute, all-in (Year 1) |
| **What it returns per year, once ramped** | **$2.7M** — ~28× the annual cost, after a 30% risk haircut |
| **Five-year value of implementing** | **+$7.3M** — NPV at 10%; cash-positive within Year 1 |
| **Cost of doing nothing** | **$7.6M** — margin never earned over 5 years (NPV) |

---

## 5-Year Do Nothing vs Implement Benefit

Cumulative position, USD millions:

| | Year 1 | Year 2 | Year 3 | Year 4 | Year 5 |
|---|---:|---:|---:|---:|---:|
| **Implement** (cumulative net of all costs) | +$0.5M | +$2.0M | +$4.5M | +$7.3M | **+$10.3M** |
| **Do nothing** (benefit foregone) | −$0.5M | −$2.2M | −$4.7M | −$7.7M | **−$10.7M** |

The two paths diverge from year one: implementing is cash-positive within the first year; every year of inaction adds roughly $3M of foregone margin at steady state.

---

## How these numbers were built — six steps to sense-check

Every step is an editable cell in the companion workbook; challenge the step, not the arithmetic.

**1. Start from our revenue base.** 16.3M passengers × $120 average revenue per passenger = **$1.96B** a year, of which 15% (~$293M) is ancillary.
*Sense-check: swap in our actual revenue per pax and ancillary share.*

**2. Claim three small benefit levers.** Targeted offers lift ancillary revenue **+2%** ($5.9M); retention improves passenger revenue **+0.10%** ($1.7M); marketing gets **10%** more efficient ($1.6M saved).
*Sense-check: peers report far more — airBaltic +6% seat revenue, Finnair +3% total revenue, McKinsey 10–20% marketing efficiency.*

**3. Count margin, not revenue.** Incremental revenue is taken at **30% contribution margin**; only the marketing saving counts at full value. Gross benefit: ~$3.8M/yr.
*Sense-check: is 30% fair for ancillary-weighted incremental revenue?*

**4. Apply a failure haircut and a ramp.** Multiply by a **70% realization factor** (execution risk) → **~$2.7M/yr** steady state; benefits ramp 20% → 60% → 90% → 100% as segments go live from month 6–9.
*Sense-check: is a 30% failure discount harsh enough for our delivery record?*

**5. Subtract what it actually costs us.** **$77,904** all-in in Year 1 (manpower, cloud, compute — our budget), escalated 5%/yr → **$0.43M** total over five years.
*Sense-check: does this budget hold in Years 2–5? At full market-rate staffing (~$487K/yr) the NPV is still +$5.9M.*

**6. Discount and compare.** Benefits minus costs, discounted at **10%** → **+$7.3M NPV** for implementing. Doing nothing spends $0 and earns $0 — forfeiting **$7.6M NPV** of the same benefits.
*Sense-check: substitute our WACC for the 10% rate.*

---

## What the model changes for each department

Same teams, same budgets — different decisions. Evidence figures are published results from the named airlines.

| Department | Doing nothing (today) | With the segmentation model |
|---|---|---|
| **Revenue Management** — drop / increase prices | Prices move on booking-class averages — drops give margin away to passengers who would have paid; increases push out the price-sensitive. | Segment willingness-to-pay tells RM **when a drop wins volume and when to hold price**. Evidence: Finnair +3% revenue from segment-aware pricing; MIT studies 3–6%. |
| **Sales** — prioritize channels | Equal effort across direct, OTA and trade regardless of who actually buys where; commissions paid on bookings that would have come direct. | Segments show **which customers buy through which channel** — steer high-value segments to direct, spend trade incentives only where they add bookings. Evidence: KLM −40% cost per booking from predictive channel bidding. |
| **Marketing** — design promos | Blanket seat sales discount everyone — including passengers who would have paid full fare; half the clicks, more unsubscribes. | Promos designed **per segment**: the fare sale goes to price-hunters, bundles and upgrades to the premium-willing — margin protected. Evidence: easyJet 2× revenue per email from 57% fewer, segmented sends. |
| **CX** — web/app & lounge | One web/app experience for all; lounge and service investment spread thin with no view of who values it. | Web/app content and journeys **personalized by segment**; lounge and service perks aimed at segments that value them. Evidence: airBaltic +5.8% site conversion; Delta +25 NPS points in disruptions. |
| **Loyalty** — churn prevention | Churn discovered after members lapse; win-back is late, untargeted, expensive. Cathay's unsegmented program change: 10.7% elite churn, ~HK$62M/yr. | Churn scores flag at-risk members **~85 days before they lapse**; retention offers go only to the winnable. Evidence: Alaska +198% loyalty conversion; United 10× campaign return. |

---

## Where the $2.7M a year comes from

Risk-adjusted annual margin at steady state, by lever:

| Lever | Margin / yr | Driven by |
|---|---:|---|
| Ancillary uplift (targeted offers) | $1.23M | Marketing (targeted promos) + RM (offer pricing) + CX (web/app merchandising) |
| Marketing efficiency | $1.10M | Marketing (fewer, sharper campaigns) + Sales (channel spend prioritization) |
| Retention / repeat flying | $0.35M | Loyalty (pre-lapse intervention) + CX (segment-aware service moments) |

One model, five consumers: every department reads the same segments, so pricing, promos, channels, service and retention finally act on the same view of the customer.

---

## Notes and sources

Source: companion workbook (Benefit Assumptions · Cost Model · Do Nothing vs Implement sheets), August 2026. Build cost is the airline's own budget figure ($77,904 all-in for Year 1, user-provided), escalated 5%/yr. Benefit levers are small fractions of published benchmarks — the IATA/McKinsey modern-retailing value pool of $45B by 2030 (~$7 per passenger) implies a ceiling of ~$114M/yr at our traffic; the model claims ~2% of it. Case-study figures are published results by the named airlines and vendors, published because they succeeded — hence the 70% realization haircut. Planning estimates, not audited outcomes.
