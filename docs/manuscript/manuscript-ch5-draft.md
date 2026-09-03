# Chapter 5 — Findings, Recommendations, and Conclusions (FINAL DRAFT)

> **Draft status:** v2.0 (final draft; restructured to the programme outline — §5.1 splits the
> findings into technical/behavioural (§5.1.1) and strategic (§5.1.2), conclusions move to
> §5.6 Final Project Conclusions, and the sections between renumber: economic case §5.3 → §5.2,
> build-vs-buy §5.4 → §5.3, recommendations §5.5 → §5.4, limitations §5.6 → §5.5),
> 23 August 2026. Companion to `manuscript-ch4-draft.md` v1.5 and Appendix A
> (`manuscript-do-nothing-analysis.md` v1.0); §4.x references point into Chapter 4, §A.x into
> the appendix. Sources: the Chapter 4 pipeline outputs, `docs/do-nothing-vs-implement.md` (the
> bottom-up measured business case), `docs/business-case-benchmark.md` (the top-down benchmark
> case and its companion workbook), and `docs/segment-cost-research.md`. Monetary values are
> USD. The same census-vs-sample uncertainty discipline as Chapter 4 applies; in addition,
> §§5.2–5.3 quote *assumed* parameters, and every such number is labelled as measured,
> benchmark-derived, or conditional at the point of use.

---

## 5.1 Summary of Technical and Strategic Findings

Thirteen findings carry the study — eight technical and behavioural (§5.1.1), five strategic
(§5.1.2). Each is stated with its strongest honest form and its measured limit; the section
references give the full evidence.

### 5.1.1 Technical Machine Learning and Behavioural Findings

**F1 — The booking base is a behavioural continuum, and the null is bounded.** No natural,
well-separated clusters exist at the top level: model-selection criteria fall monotonically from
a single component with no elbow anywhere, ten methods across six algorithmic families plateau
at a Gower silhouette of 0.381, the methods disagree with one another about where the boundaries
are (median cross-method ARI 0.41), and every internal validity index computable on the data —
silhouette, Davies–Bouldin, Calinski–Harabasz — agrees that nothing settles (§4.1.1). The claim
is falsifiable, not asserted: a planted-segment power analysis shows the pipeline reliably
recovers a synthetic segment of ≥2% prevalence at distinctness ≈0.494, so no such segment exists
in these features — while anything below ~1% of bookings (~229,000) could hide undetected
(§4.1.2).

**F2 — A rule waterfall co-designed with the airline assigns 22.9M bookings to eleven named
segments plus a 2.47% residual.** The v2 taxonomy (Table 4.2) genuinely reclassified 23.4% of
bookings, cut the unexplained residual by 74%, and encodes 57 SME constraints with the six
enforce-grade rules asserted at build time (§4.1.3). Unsupervised agreement with the taxonomy
peaks only at the trivial geography cut (ARI 0.537 at k = 2, which is the domestic/international
bit rediscovered); past that spine it is moderate at best (0.389), which is the expected shape
on a continuum.

**F3 — The segments are distinguishable on evidence the rules never saw.** On per-pair adaptive
anchors, all 55 pairs are at least weakly distinguishable and 44 are clearly distinct (median
AUC 0.861), against passing negative controls (§4.2.2). The labels are behaviourally validated,
not externally confirmed; adjudication against SME-labelled bookings remains open.

**F4 — The taxonomy's weakest boundary did not improve, and we report that as a result.**
OFW/Migrant vs. Balikbayan/VFR remains split on a single bit; an A/B holding everything but the
labels fixed scored the redesign as neutral (0.730 vs. 0.728). The evidence most likely to move
it — frequent-flyer identity — is data the airline has now agreed to supply (§4.2.2).

**F5 — The segmentation is a lossy but faithful compression, by design.** The label alone
carries real outcome signal (AUC ≈0.60 on two stable outcomes) but adds ≤0.0024 on top of its
input features (§4.2.3). Its value is coordination — five departments reading one customer view
— not prediction, and it is not sold as prediction.

**F6 — The taxonomy is stable across a twelve-month step, with revenue mix the weaker leg.**
Segment shares move 1.71 pp in total variation on full-population counts; revenue mix moves
3.36 pp, led by a 2.7-pp Balikbayan/VFR revenue-share decline on flat volume — yield erosion,
not attrition. Whether a year-old *model* transfers is unresolved: the two-method panel
disagrees (ratios 1.24 and 0.89), and no refit-cadence claim is made (§4.2.4).

**F7 — One level down, the same continuum, and one shared grammar.** Twenty population-exact
sub-types across the five largest segments recover the same three axes independently — trip
direction × booking timing × fare tier — in five separate fits that each saw only one segment's
bookings, while BIC again ran to the top of its allowed range in every parent (§4.2.5).

**F8 — The taxonomy exposes behavioural regularities that survive adversarial checks.** 87.8%
of customers never leave their segment across their observed history, so the label is a stable
personal attribute rather than a per-trip accident; repeat-behaviour floors span 3× (12.2%
Pilgrimage to 36.4% Corporate — floors, because the data is right-censored); OFW/Migrant and
Balikbayan/VFR peak in opposite months (August against December), so the same corridors can be
revenue-managed to two calendars; and Manila–Gulf traffic runs on a one-month stay clock no
other corridor has (month-to-fortnight ratio 2.25 against ≤0.60 everywhere else) — reported as
a pattern, not an explanation, until its fare-rule confound is settled (§4.2.2).

### 5.1.2 Strategic and Business Findings

**F9 — The binding constraint is data identity, not modelling.** The loyalty segment is
unmeasurable at 0.03% (award redemptions are the only visible signal), churn is not computable
(73.9% of customers are observed once, with zero tenure), the extract carries no ancillary
revenue, and age is captured on under 1% of domestic bookings. Each gap has a priced acquisition
case (§4.3.6), and each caps a specific commercial lever in §5.2.

**F10 — The volume story and the value story are near-inverses.** Leisure supplies 50.6% of
bookings and 15.0% of revenue; Balikbayan/VFR supplies 12.5% of bookings and 28.4% of revenue;
on the CY2025 flown base the total-variation distance between the booking mix and the revenue
mix is 36.3 pp ($919M). Any strategy metric denominated in passengers systematically overweights
the low-yield base, and segment-denominated reporting is the correction (§4.3.1).

**F11 — Uniform treatment mis-prices a measured $645.8M.** Sub-types priced at or above 1.25×
their parent's mean hold 22.9% of parent bookings and 29.7% of parent revenue — the population a
parent-uniform price or promotion treats as average — sharpening to $358.1M at a 1.5× threshold;
and two segments (OFW/Migrant, Outbound International Leisure) measurably need no sub-segment
pricing at all, a negative result that spares effort (§4.2.5, Appendix A §A.4.1).

**F12 — Department readiness is derived from the evidence, not asserted.** Sales and CX can act
first because their use needs no response assumption (agency dependence spans 6.6×; the sea-crew
channel is $136.6M serving effectively one segment; digital revenue share spans 19×); Revenue
Management follows with a measured recovery rate; Marketing is the instrumentation site because
its assumption is testable inside one campaign cycle; Loyalty waits for identity data (Appendix
A §A.4.6).

**F13 — The cost of misclassification now has a measured spread.** Annual value at risk per
misclassified customer spans $495 to $9,784 across segments, replacing a placeholder ladder that
was inverted against measured revenue in two places; the resulting asymmetric weights enter the
deliverable as a proposal pending the airline's review (§4.3.5).

## 5.2 The Economic Case: Do Nothing vs. Implement

Two independent estimation routes were built, and they answer different questions. Quoting one
as if it were the other is the main way this business case could be misused, so the manuscript
states the division of labour explicitly. The full bottom-up analysis — the five-department
evidence, the assumption ledger, and the five-year band — is **Appendix A**
(`manuscript-do-nothing-analysis.md`); this section is its summary.

| | Bottom-up (measured) | Top-down (benchmark) |
|---|---|---|
| Question | Does the decision *require* a benefit forecast? | What is the expected value *if benchmarks transfer*? |
| Benefit basis | $16.1M/yr modelled dilution exposure, anchored on the measured $645.8M of parent revenue priced ≥1.25× its parent mean | ~2% of the IATA/McKinsey modern-retailing value pool, cross-checked against published airline case results, risk-adjusted 30% |
| Cost basis | $18,800 placeholder (superseded) | **$77,904/yr actual all-in budget** |
| Result | Breakeven at **0.48%** of the modelled dilution (one dollar in 207, at the actual budget; 0.116% at the old placeholder) | ~$2.7M/yr margin at steady state; **+$7.3M five-year NPV at 10%**; cash-positive in year 1 |
| Load-bearing use | **The decision instrument** | Conditional sizing, for planning only |

The bottom-up route carries the decision. At the actual budget of $77,904 per year, implementing
pays for itself if 0.48% of the measured dilution exposure is averted — and the stress form of
that argument (every assumed parameter degraded at once) still clears by an order of magnitude
(§A.7). The claim is deliberately *not* "the benefit is $2.7M"; it is that the decision does not
depend on knowing the benefit.

The top-down route sizes the opportunity, and we quote it with three conditions attached —
conditions that come from this study's own measurements, which is why they belong in the
manuscript rather than a footnote:

1. **The largest lever is currently unmeasurable.** Ancillary uplift ($1.23M/yr, 45% of the
   steady-state benefit) rests on ancillary revenue the extract does not contain (F9). Until
   ancillary data arrives, this lever is an assumption about revenue we have never observed, and
   we classify it as *conditional*, not expected.
2. **The retention lever is not actionable today.** The churn-prevention framing ("flag at-risk
   members before they lapse") presumes an identity the data lacks: with 73.9% of customers
   observed once, no churn score is computable (§A.4.5). The $0.35M/yr retention lever activates
   when loyalty identity arrives, not before.
3. **The revenue base should be the measured one.** The benchmark case assumes a $1.96B annual
   base (16.3M passengers × $120); the extract *measures* ≈$2.9B a year ($6.22B over ~26
   months). The assumption is conservative in direction, but a business case built beside a
   38M-coupon extract should start from the extract's own census figures.

With those conditions, the unconditional near-term benefit concentrates in the marketing-
efficiency and dilution-avoidance levers ($1.10M/yr benchmark-derived, sitting on a measured
$16.1M/yr exposure) — and the breakeven arithmetic above already clears on that lever alone
($77,904 against the $1.28M marketing contact lever is 6.1%). The published airline results the
benchmark case cites (Finnair, airBaltic, KLM, easyJet, Alaska, Delta, United, per the companion
workbook) are quoted there with the correct caveat, which we repeat: they are published because
they succeeded, and the 30% realisation haircut is a coarse correction for that survivorship.

## 5.3 Build vs. Buy: the Vendor Benchmark

The vendor case results quoted in §5.2 double as the benchmark for the *buy* option — a
commercial personalisation or customer-data platform — and the comparison resolves on three
facts rather than on a price quote.

**First, the cost asymmetry is measured.** The in-house model's actual all-in cost is
$77,904/yr; at full market-rate staffing the shadow cost is ~$487K/yr, and even at that cost the
five-year NPV remains positive (+$5.9M, per the workbook sensitivity). Enterprise
personalisation platforms price above the actual budget by roughly an order of magnitude before
integration; a buy decision therefore needs the vendor to deliver something the build cannot,
not merely to match it.

**Second, every vendor result in the evidence base runs on identified customers.** The KLM,
easyJet, and Alaska results rest on loyalty identity, e-mail reach, or logged-in app behaviour.
PAL's environment for this study is anonymous PNR data — the constraint the in-house design was
built *for* (§4.1.3). A bought platform inherits the same identity ceiling (F9): it could not
compute the churn scores or per-member offers its case studies advertise any more than we can,
while its licence would be paid from day one. Buying does not purchase capability; data does.

**Third, governance favours the auditable option.** §5.6's first conclusion is that the taxonomy
is a management instrument whose value depends on boundaries being reviewable, versioned, and
asserted in code — properties the in-house waterfall has and a vendor black box, scored behind
an API, does not. For a deliverable whose weakest boundary is openly flagged and whose SME
constraints are build-time assertions, auditability is a functional requirement, not a
preference.

**Recommendation: build — which is already done — and name the re-evaluation trigger.** The
decision flips only when identity data arrives (loyalty tier, frequent-flyer flags): that event
simultaneously enables the vendors' strongest levers and the in-house model's (F4, F9), so it is
the correct moment to re-run this comparison with live quotes. Until then a vendor engagement
would spend more to hit the same data ceiling. A hybrid remains open at that point: the in-house
taxonomy as the segmentation layer of record, with a vendor activation layer above it — which
keeps the auditable rules and buys only the delivery plumbing.

## 5.4 Recommendations to the Airline

**R1 — Adopt, in the measured readiness order** (F12). Sales and CX first (their use needs no
response assumption — the measured facts are the deliverable: 6.6× spread in agency dependence,
the $136.6M sea-crew channel, 19× spread in digital revenue share); Revenue Management next,
with a measured recovery rate before pricing action on the $645.8M mispricing population;
Marketing behind response measurement; Loyalty deferred until identity data arrives (§4.3.3).

**R2 — Acquire the four data items, in this order: loyalty/frequent-flyer identity, ancillary
revenue, fare-basis codes, age capture at booking.** The first opens the weakest boundary, the
Mabuhay segment, the Corporate dilution problem, the retention lever, and the buy/build
re-evaluation at once — five returns on one field set, which is why it leads. Each of the other
three lifts a named, measured limitation (§4.3.6).

**R3 — Govern the taxonomy as an instrument.** Versioned rules with build-time assertions;
segment revenue shares re-measured, never carried forward (F6); the drift monitor read with its
new-category/drift separation (an NDC-style channel launch is not behavioural drift, §4.2.4);
and re-profiling of the four smallest labels before any campaign use.

**R4 — Run the business case on the two-route discipline.** Use breakeven as the decision
instrument and the benchmark NPV as conditional sizing; re-anchor the benefit levers to measured
artefacts as data arrives (dilution exposure now; ancillary and churn when their data lands);
and rebase the benchmark case's revenue step on the extract's census figures (§5.2, condition 3).

**R5 — Do not buy a platform before the identity data arrives** (§5.3). Re-run the comparison,
with live vendor quotes, when it does.

## 5.5 Limitations and Future Work

The seven limits of §4.3.7 carry into this chapter unchanged; the business case adds its own
three (§5.2), all data-conditional. Future work, in priority order: interval estimation across
seeds for every sampled headline statistic — the single upgrade that addresses the widest class
of residual risk, given that one withdrawn claim in this study traces exactly to its absence;
SME adjudication of ~1,000 labelled bookings (the outstanding strongest test of the segment
names); promotion of the level-2 assignment into the airline's BI model with the same drift
monitoring as level 1; a designed rule for the domestic-premium residual (§4.2.1); one
instrumented marketing campaign, which replaces the free recovery-rate parameter with a
measurement (§A.9); and the buy/build re-evaluation at identity-data arrival (§5.3).

## 5.6 Final Project Conclusions

Four conclusions follow from the findings, and the study closes on what they jointly imply.

**C1 — The taxonomy is a management instrument, not a discovery, and should be governed as
one.** Nothing in the data resists moving a boundary; what protects the deliverable is that its
boundaries are written as reviewable rules, versioned, and asserted in code. The v1 → v2
revision — four segments added, three removed, a residual cut by 74%, executed in days — is the
existence proof that this governance works (§4.3.4).

**C2 — Segmentation can be validated without ground truth.** The four-stage ladder — construct
validity on withheld anchors, criterion validity on unconsumed outcomes, detection power on
planted segments, reliability across time — adapted from classical measurement theory (Cronbach
& Meehl, 1955), produced bounded claims, passing controls, and one public retraction executed
correctly. We consider the ladder itself a methodological contribution alongside the taxonomy.

**C3 — For an airline selling largely to anonymous passengers, the honest unit of segmentation
is the booking, and the honest product is a shared vocabulary.** 87.8% of customers never leave
their segment, so the label survives aggregation to the person; but the model's commercial value
runs through coordination — pricing, promos, channels, service, and retention acting on one view
— not through incremental predictive signal (F5).

**C4 — Anonymous data sets a measurable ceiling, and the ceiling is now priced.** F9's gaps are
not generic complaints: each blocks a named lever (§5.2), each has a specific field that lifts
it, and the airline has already agreed to supply the first of them. The correct sequencing of
the commercial programme follows from the ceiling, not from appetite (§5.4).

The study set out to segment an airline's customers and found, first, that the customers do not
come pre-segmented: the booking base is a continuum, and we can say to within measured bounds
how large and how distinct a hidden segment would have to be for that claim to fail. On that
foundation the deliverable is deliberately an instrument rather than a discovery — eleven named
segments written as auditable rules the airline co-authored, validated on evidence the rules
never saw, stable across a year, refined by machine-learned sub-types where the value spread
justifies it, and honest in print about its weakest boundary, its withdrawn claim, and the data
it cannot see. The economics require no forecast to clear — at the actual budget, half a percent
of one measured exposure pays for the programme — and the analysis of what would make everything
above it better points, from four independent directions, at the same next step: give the model
identity data. Until then, the cheapest and most defensible segmentation platform this airline
can operate is the one it now owns.

---

*References cited in this chapter: Cronbach & Meehl (1955) as in Chapter 4's list; airline case
results (Finnair, airBaltic, KLM, easyJet, Alaska Airlines, Delta, United, Cathay Pacific) and
the IATA/McKinsey modern-retailing estimate are quoted from the business-case companion workbook
(`docs/business-case-benchmark.md`, Aug 2026) as compiled secondary sources — published,
vendor-adjacent, and survivor-biased, which is why they enter only the conditional sizing route,
never the decision instrument.*
