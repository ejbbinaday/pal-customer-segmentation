# What does a misclassification cost? — research and recommended penalty weights

**Written:** 18 August 2026
**Answers:** PAL question **A1** — *"What does it cost PAL to wrongly label a booking in each of the four
new segments?"* PAL's reply was **"see run first"**, so this proposes a basis rather than waiting.
**Status:** recommendation for PAL to accept, amend or replace. **Not yet wired into any code.**

> **Why this document exists.** The model is scored by an asymmetric cost matrix, and four new segments
> have no weight. The cost-sensitive-learning literature is unambiguous that these numbers are a
> domain-expert input, not a modelling choice: you *"work with domain experts and different stakeholders,
> analyze historical data, and leverage data mining techniques to identify patterns that highlight the
> true costs"* ([Train in Data](https://www.blog.trainindata.com/cost-sensitive-learning-for-imbalanced-data/)).
> So this document does the two halves we *can* do — the historical data and the literature — and marks
> clearly where a business judgement is still required.

---

## 1. The problem with the weights we have

The shipped matrix (`src/hdbscan_final.py`, `src/export_powerbi.py`) is:

| segment | penalty | "revenue at risk per error" |
|---|---|---|
| Corporate | ×10 | $40,000 |
| Mabuhay Loyalist | ×8 | $32,000 |
| OFW/Migrant | ×5 | $20,000 |
| Premium Bleisure | ×4 | $16,000 |
| Pilgrimage | ×3 | $12,000 |
| Balikbayan/VFR · Family | ×2 | $8,000 |
| Last-Minute · Budget/Adventure | ×1 | $4,000 |

**Two problems.**

⚠️ **The dollar column is not an estimate.** It is `penalty × $4,000` in every row. It looks like eleven
independent valuations and it is one number and a ladder. Our own export describes these as *"PAL's own
estimates from the requirements document"*, which is true of the ladder but overstates the dollar figures.

⚠️ **The ladder is inverted against measured revenue in two places.** With revenue now confirmed as USD
(PAL answer B5), we can check it:

| | penalty | mean revenue / booking | total revenue |
|---|---|---|---|
| Mabuhay Loyalist | **×8** | **$113 — the lowest of any segment** | $0.7M (0.01%) |
| Balikbayan/VFR | **×2** | $615 | **$1,765M (28.4% of all revenue)** |

The segment carrying the second-highest penalty is the least valuable per booking we can see, and the
segment carrying the largest share of revenue in the airline sits near the bottom of the ladder. One of
those is a real measurement blindness (see §5); the other is simply wrong.

## 2. What a misclassification actually costs — five components

### C1 · Direct revenue on the booking

The fare at stake if the wrong action is taken. **Measurable from our data.**

### C2 · Dilution — the discount you should not have offered

The classic revenue-management loss. *"Demand is diluted when those passengers who would be willing to
pay the regular price purchase a product at the markdown price… better paying customers are turned away
for discount customers"*
([USC Illumin](https://illumin.usc.edu/the-algorithm-behind-plane-ticket-prices-and-how-to-get-the-best-deal/);
formal treatment in [Optimal timing of airline promotions under dilution, *EJOR*](https://www.sciencedirect.com/science/article/abs/pii/S0377221719302504)).

**This is the asymmetry that matters most for us.** Labelling a high-yield traveller as price-sensitive
and sending them a promo fare *destroys margin on a sale you already had*. The reverse error — withholding
a promo from a genuinely price-led traveller — costs you a sale you never had. **The first error is more
expensive than the second**, which is precisely why the cost matrix is asymmetric rather than symmetric.

Airlines build *"increasingly complex fences… to distinguish these fares from full fares to help reduce
dilution effects"* — the fare ladder in our own `max_tier` field is that fencing, which is why yield
sensitivity below is keyed to cabin and fare.

### C3 · Spill and spoilage — the seat you protected for the wrong person

*"Spoilage refers to empty seats, while spill refers to lost demand due to closed availability"*
([Maxamation](https://maxamation.com/performance-monitoring-of-airline-revenue-management-departments/)).
Segment errors feed the forecast that drives seat protection, so a systematically mislabelled segment
mis-protects inventory. Second-order for us today — the segmentation does not yet drive inventory — so it
is noted and **excluded from the arithmetic**.

### C4 · Contact waste — the cheapest component by three orders of magnitude

A wrongly targeted email costs cents. Travel email marketing returns **$36–42 per $1 spent** and
segmented campaigns convert at **3–8% against a 1.8% baseline**, with segmented programmes reported at
**3–4× the conversion** of unsegmented blasts
([Foundry CRO 2026 benchmarks](https://foundrycro.com/blog/travel-hospitality-marketing-benchmarks-2026/),
[Scale Growth](https://scalegrowth.digital/resources/email/email-marketing-for-travel/),
[HubSpot](https://blog.hubspot.com/marketing/email-marketing-stats)).

**The implication runs the other way from intuition:** the *send* is nearly free, so the cost of a
misclassification is almost entirely the **foregone uplift** and the **dilution**, not the wasted contact.
A 3–4× conversion difference on a segment worth $2,000 a year dwarfs the $0.02 email.

### C5 · Relationship and lifetime value — the multiplier

The largest component for frequent segments, and the best-documented in the literature.

*"Business travelers tend to book ten times a year on average, but leisure travelers book once every
three years"* — a **30× frequency spread** — and airlines *"love corporate travelers because their
frequency is high and predictable, thus leading to a massive CLV"*
([OpenJaw Data Science](https://medium.com/the-openjaw-data-science-blog/in-travel-retailing-some-customers-are-more-equal-than-others-part-1-202eb78d869f)).
Independently, *"business visitors spend approximately three times more than leisure tourists"*
([Polaris MICE market analysis](https://www.polarismarketresearch.com/industry-analysis/meetings-incentives-conferences-and-exhibitions-market)).

⚠️ **We do not adopt the 30× figure.** Our own data measures a far narrower spread (§3), because a PNR-level
extract over ~3 years sees a fraction of a real lifetime and because our booking counts needed
tenure-normalising. **Using the industry 30× would inflate the corporate weight by an order of magnitude
on someone else's population.** It is cited as directional support for *frequency being the dominant CLV
driver*, not as a coefficient.

## 3. What our own data says

Booking grain, all 22,911,450 bookings, proposed taxonomy, **USD** (PAL B5).
`bookings/yr` is **tenure-normalised** — `n_bookings ÷ (tenure_days/365)` — because raw lifetime counts are
inflated by how long a customer has been in the extract, a confound that cost us a wrong conclusion on
17 August.

| segment | mean $/booking | bookings/yr | **annual value $** | % premium cabin |
|---|---|---|---|---|
| Ultra Wealthy Leisure | 1,968 | 5.0 | **9,784** | 100% |
| Premium Bleisure | 1,188 | 6.1 | **7,256** | 100% |
| Intl. Student | 1,159 | 4.2 | 4,830 | 10% |
| Corporate | 460 | 8.5 | 3,916 | 32% |
| Balikbayan/VFR | 615 | 4.4 | 2,718 | 1% |
| Outbound International Leisure | 398 | 5.1 | 2,037 | 0% |
| Pilgrimage | 404 | 4.3 | 1,746 | 4% |
| OFW/Migrant | 312 | 5.0 | 1,565 | 2% |
| MICE | 269 | 4.4 | 1,184 | 1% |
| Mabuhay Loyalist | 113 | 5.1 | 570 | 2% |
| Leisure | 80 | 6.2 | 495 | 0% |

**Annual value at risk spans 20× — $495 to $9,784.** That is the honest dollar spread, and it is the first
time this project has had one.

### Two results worth pausing on

**MICE measures low ($1,184/yr) and the literature says it should be high.** *"A single corporate
conference can generate more revenue than 100 individual holiday bookings"*
([GroupRM](https://grouprm.net/MICE-Automation-a-growing-opportunity-for-Airline)), against a global MICE
market of **$862bn in 2024** ([Polaris](https://www.polarismarketresearch.com/industry-analysis/meetings-incentives-conferences-and-exhibitions-market)).
The reconciliation is that **we measure per *booking*, and MICE's value is per *event*** — 27,007 individual
bookings that in reality belong to a much smaller number of large contracts. Our grain cannot see the
contract. **This is a known understatement, not a finding that MICE is low-value.**

**Corporate measures at $460/booking, below Balikbayan/VFR.** That is a real fact about our *rule*, not
about corporate travel: `rule_confidence.py` already records Corporate as **the most contested segment —
only 6.4% of it matches exactly one rule and 25.6% matches three or more**. The branch sweeps in
short-notice domestic economy alongside genuine business travel, which drags the mean down. **The rule
dilutes the segment.**

## 4. The formula

```
annual value at risk   =  mean revenue per booking  ×  bookings per year   (both measured)
raw cost per error     =  annual value at risk      ×  yield sensitivity
weight                 =  sqrt(raw ÷ floor), rescaled so the top segment = 10
```

**Yield sensitivity** encodes C2, the dilution asymmetry — how much damage a wrongly-offered discount does:

| | factor | rationale |
|---|---|---|
| 100% premium cabin | **2.0** | the seat could have been sold dearer; a promo here is pure margin loss |
| Corporate · MICE · Intl. Student | **1.5** | fare-insensitive but not always premium — schedule and flexibility drive the purchase |
| everything else | **1.0** | price-led; a discount is the correct offer, so a wrong one costs little |

**Why compress with a square root.** Raw ratios span **40×**. Feeding that into
`hdbscan_final.py`'s penalty-weighted feature scaling would let one 0.69%-of-bookings segment dominate the
distance metric — the weights there are normalised as `pw / TOTAL_PENALTY` and multiplied into feature
magnitudes. Square-root compression preserves the ordering, keeps the spread at **5×** (comparable to the
existing 1–10 ladder, so the scale stays interpretable), and stops the tail wagging the model. **The raw
dollar figures are reported alongside, so nothing is hidden by the compression.**

## 5. Recommended weights

| segment | annual $ at risk | measured | **recommended** | existing | note |
|---|---|---|---|---|---|
| Ultra Wealthy Leisure | 9,784 | 10 | **10** | — | new |
| Premium Bleisure | 7,256 | 9 | **9** | 4 | existing weight badly understated it |
| Mabuhay Loyalist | 570 | 2 | **8** ⚠️ | 8 | **override — see below** |
| Corporate | 3,916 | 5 | **8** ⚠️ | 10 | **override — see below** |
| Intl. Student | 4,830 | 6 | **6** | — | new |
| Balikbayan/VFR | 2,718 | 4 | **4** | 2 | 28% of all revenue; was under-weighted |
| MICE | 1,184 | 3 | **4** ⚠️ | — | **override — see below** |
| Outbound International Leisure | 2,037 | 3 | **3** | — | new |
| Pilgrimage | 1,746 | 3 | **3** | 3 | unchanged |
| OFW/Migrant | 1,565 | 3 | **3** ← *PAL's call* | 5 | see §6 |
| Leisure | 495 | 2 | **2** | 1 | |
| Unassigned | — | 0 | **0** | 0 | not a segment |

### The three overrides, and why each is legitimate

An override is only defensible where we have **documented evidence that the measurement is blind** — not
where we simply dislike the answer.

**Mabuhay Loyalist: measured 2 → recommended 8 (keep PAL's original).** We can only see **award
redemptions**, because there is no loyalty-tier field — the segment is 0.03% of bookings and $113 mean
revenue for that reason alone. This is the single best-documented blindness in the project and the reason
the persona card carries a `DataCaveat` column. **Revisit once PAL supplies loyalty tier (answer B4).**

**Corporate: measured 5 → recommended 8.** The rule is documented as the most contested in the model
(6.4% uncontested), so its measured mean is depressed by cheap short-notice domestic bookings that are not
really corporate. Also the segment with the highest measured booking frequency (8.5/yr), which is the CLV
driver the literature identifies. **Not restored to 10** — that figure was never measured, and 8 reflects
both the dilution of the rule and the genuine value of the traveller.

**MICE: measured 3 → recommended 4.** Per §3, our booking grain cannot see the event contract. A modest
bump acknowledges a known understatement without inventing a number we cannot support.

## 6. One item that is PAL's call, not ours

**OFW/Migrant — measured 3, existing 5.** The formula ranks it on the value of a single booking.
The strategic argument points the other way: **2.19 million OFWs as of 2024**
([PSA / Statista](https://statista.com/statistics/1287067/philippines-number-of-overseas-filipino-workers)),
and PAL's transpacific and Gulf franchise is built on this traffic and the balikbayan flows around it
([Flying411 on the 2026 A350-1000 deliveries](https://flying411.com/blog/philippine-airlines-fleet-expansion-2025/549)).
OFW/Migrant is also **19.6% of measured revenue — $1.22bn** — on a low per-booking figure.

**We are not overriding this one.** "This segment matters more than its per-booking value" is a commercial
judgement about franchise defence, and inventing a weight for it would be exactly the invention A1 was
asked to avoid. **Recommend PAL sets this number.** If they want it held at 5, that is a decision we can
implement in one line and record with their name on it.

## 7. What would change these numbers

1. **Loyalty tier (B4)** — would move Mabuhay Loyalist from an override to a measurement.
2. **Party size (B3)** — would let MICE be valued per contract rather than per booking, which is the
   biggest single understatement in the table.
3. **Fixing the Corporate rule** — the 6.4%-uncontested problem. A cleaner Corporate branch would raise
   its measured value and remove the need for that override.
4. **A real CLV horizon.** Our tenure is short (234–343 days mean) against a 3-year extract, so
   `bookings/yr` is a *rate*, not a lifetime. A longer history would widen the spread and probably move
   it toward the industry frequency gap rather than away from it.
5. **Ancillary revenue.** Entirely absent from our data. It skews toward premium and leisure segments, so
   its absence understates exactly the top of this table.

⚠️ **These are proposed weights on a measured basis, not measured costs.** The dollar figures in §3 are
real. The weights in §5 are those figures shaped by two judgements — yield sensitivity and square-root
compression — plus three documented overrides. **Any of the three can be argued with, which is the point
of writing them down separately.**

---

## Sources

**Airline revenue management — dilution, spill, spoilage**
- [Optimal timing of airline promotions under dilution — *European Journal of Operational Research*](https://www.sciencedirect.com/science/article/abs/pii/S0377221719302504)
- [The Algorithm behind Plane Ticket Prices — USC Viterbi, Illumin](https://illumin.usc.edu/the-algorithm-behind-plane-ticket-prices-and-how-to-get-the-best-deal/)
- [Performance Monitoring of Airline Revenue Management Departments — Maxamation](https://maxamation.com/performance-monitoring-of-airline-revenue-management-departments/)
- [Fundamentals of Pricing and Revenue Management — George Mason University (PDF)](https://catsr.vse.gmu.edu/SYST660/Chap4_Fundamentals_of_Pricing_and_Revenue_Management.pdf)
- [Taking Flight: The Science of Revenue Management — IDeaS](https://ideas.com/taking_flight_the_science_of_revenue_management/)

**Customer lifetime value in travel**
- [In travel retailing, some customers are more equal than others — OpenJaw Data Science](https://medium.com/the-openjaw-data-science-blog/in-travel-retailing-some-customers-are-more-equal-than-others-part-1-202eb78d869f)
- [Airline customer lifetime value estimation using data analytics — *Journal of Air Transport Management*](https://www.sciencedirect.com/science/article/abs/pii/S0969699716303921)
- [How Your Customer Lifetime Value Affects How the Airline Treats You — FlyerTalk](https://www.flyertalk.com/articles/how-your-customer-lifetime-value-affects-how-the-airline-treats-you.html)

**Segmentation economics and campaign benchmarks**
- [Travel & Hospitality Marketing Benchmarks 2026: CPC to ROAS — Foundry CRO](https://foundrycro.com/blog/travel-hospitality-marketing-benchmarks-2026/)
- [Email Marketing for Travel: Sequences That Fill Trips — Scale Growth Digital](https://scalegrowth.digital/resources/email/email-marketing-for-travel/)
- [Email marketing ROI: key stats — HubSpot](https://blog.hubspot.com/marketing/email-marketing-stats)

**MICE / group travel valuation**
- [MICE Market Size & Trends — Polaris Market Research](https://www.polarismarketresearch.com/industry-analysis/meetings-incentives-conferences-and-exhibitions-market)
- [Is MICE Automation a Growing Opportunity For Airlines? — GroupRM](https://grouprm.net/MICE-Automation-a-growing-opportunity-for-Airline)
- [How airlines can bolster group booking revenue — GroupRM](https://www.grouprm.net/how-airlines-can-bolster-group-booking-revenue-by-providing-a-compelling-shopping-experience/)

**Cost-sensitive learning methodology**
- [Cost-Sensitive Learning for Imbalanced Classification — Machine Learning Mastery](https://machinelearningmastery.com/cost-sensitive-learning-for-imbalanced-classification/)
- [Cost-Sensitive Learning: Beyond Accuracy in Imbalanced Classification — Train in Data](https://www.blog.trainindata.com/cost-sensitive-learning-for-imbalanced-data/)
- [Cost-Sensitive Learning and the Class Imbalance Problem — Ling & Sheng (ResearchGate)](https://www.researchgate.net/publication/268201268_Cost-Sensitive_Learning_and_the_Class_Imbalance_Problem)
- [Post-tuning the decision threshold for cost-sensitive learning — scikit-learn](https://scikit-learn.org/1.5/auto_examples/model_selection/plot_cost_sensitive_learning.html)

**Philippine market context**
- [Number of Overseas Filipino Workers — PSA / Statista](https://statista.com/statistics/1287067/philippines-number-of-overseas-filipino-workers)
- [Survey on Overseas Filipinos — Philippine Statistics Authority](https://psa.gov.ph/statistics/survey/labor-and-employment/survey-overseas-filipinos)
- [Philippine Airlines Fleet Expansion 2025–26 — Flying411](https://flying411.com/blog/philippine-airlines-fleet-expansion-2025/549)

**Internal, this repository**
- `outputs/features_real/summary.md` — segment sizes and revenue
- `outputs/rule_confidence/summary.md` — the Corporate contestedness figures
- `docs/methodology.md` §Stage 7 — how the cost matrix is applied
- `src/hdbscan_final.py` `PENALTY`, `src/export_powerbi.py` `PERSONA` — the weights in force today
