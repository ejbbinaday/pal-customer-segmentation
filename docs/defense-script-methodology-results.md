# Defence script — Methodology & Results (26 Aug rebuilt deck)

**Deck:** the 28-slide rebuild (`CPT3_DefenseDeck_V3 1.pdf`). **Covers slides 12–18** — the
methodology block (12–14) and the results block (15–18) — plus the entry transition from EDA and
the handoff into the business case. **Block budget: 9:00** (methodology 3:30 · results 5:30).
Companion for everything else: `docs/final-defense-reviewer.md` (§5 slide map, §6 question bank);
the older `defense-script.md` was written for the superseded 26-slide deck — use this file for
these slides.

**How to read this.** `>` blockquotes are words to say. `[Square brackets]` are stage directions.
**Guardrail** lines are what loses marks if said wrong — read them before rehearsing, never while
presenting. Every sentence here is safe against the never-say list; deviate in style, not in
numbers.

---

## Entry — the last EDA beat (end of slide 11) · 0:15

[You have just shown the bookings-vs-revenue region chart. This sentence is the bridge — say it
over slide 11, then click to the divider.]

> "So that's the raw material: customers who buy late, buy cheap, and fly domestic — while the
> money flies to North America. The obvious next question is how you segment a base like that.
> Here's what we did — and the first thing we did was fail in an instructive way."

---

## Slide 12 — Methodology divider · 0:05

[Click through. Don't talk over a divider beyond the sentence you're already finishing.]

---

## Slide 13 — First Clustering Attempt · 1:30

[Click. Let the two point-clouds sit for two seconds before speaking. Point at the LEFT panel
first.]

> "We started the way any of us would: unsupervised clustering. The left panel is what the
> algorithm finds when we ask it for classes — this is Latent Class Analysis, projected down to
> two dimensions.
>
> [Point at the RIGHT panel.] The right panel is the same points, coloured by the business
> segments instead. Same cloud. Everything overlaps everything.
>
> And this is not one algorithm failing. We widened the search to ten methods across six algorithm
> families — centroid methods, mixture models, graph methods, even topological ones that make
> almost no assumptions at all — and every one hit the same ceiling. The best separation any of
> them achieved was 0.38 on a scale where 0.5 is the conventional bar for real structure. The
> criterion that's supposed to find the natural number of groups never found one — not at nine,
> not at four, not even at two.
>
> The conclusion is the most important fact in this project: PAL's customers are not clusters.
> They're a continuum — they blend into each other like colours in a rainbow. And you cannot
> discover boundaries in a rainbow. You have to *choose* them."

**Guardrail — figure caveat, only if asked:** the legend on this figure carries the *v1* segment
names (Budget/Adventure, Family, Last-Minute) — it's the 23 July render. The finding replicates on
the shipped taxonomy with *higher* agreement (ARI 0.389 vs 0.319). Say "the figure predates the
final naming; the re-run is in the repo and is slightly more favourable" — never pretend the names
are current.
**Guardrail:** the k=9 on the left panel is the top of the search range, not a discovered optimum.
**Guardrail:** if someone cites the 0.54 ARI at k=2 — that cut is geography (domestic vs
international, ARI 0.909 against that single bit), not customer structure. Customer-structure
ceiling stays ~0.39.

## Slide 14 — PAL Guides, then Machine Learning · 1:45

[Click. Walk the five stages left to right with your hand, but do NOT read them out one by one.]

> "So we flipped the design. If the data won't draw the lines, the business draws them — and
> machine learning gets three jobs it can actually win.
>
> The pipeline runs left to right: we extract the raw coupons, reassemble flight legs into
> bookings — one purchase, one purpose — and then the model itself is a rule waterfall. A priority
> checklist, built with PAL's own revenue managers: the first rule that matches a booking claims
> it. Fifty-seven of PAL's rules are registered; the six hard ones are asserted in code on every
> single build — if a build violates one, it fails loudly instead of shipping quietly.
>
> Then machine learning takes over — three jobs. It *refines*: inside the five biggest segments,
> latent class analysis finds the sub-types, and every booking now carries its sub-type label. It
> *audits*: four validation stages test every boundary on evidence the rules never touched — I'll
> come back to what they found. And it *watches*: a drift monitor checks every input feeding the
> rules, every month, in about a minute.
>
> One property of this design matters more than it looks: nothing learns at the top level. Scoring
> a new booking means applying the same checklist — the labeller itself cannot drift. If the world
> changes, it shows up in the inputs, and the monitor is pointed exactly there."

**Guardrail:** ML *checks*, never "approves". The rules label; ML refines, audits, watches.
**Guardrail — "so where's the ML?"** (likely here): the answer is the ten-method benchmark that
*established* the continuum, plus the three jobs just named. Full version: reviewer Q7/Q58.
**Guardrail — "semi-supervised?"** (slide 5 used the term): rules supply the labels — programmatic
weak supervision — unsupervised LCA refines, and the validation trusts neither. No stage treats
the labels as ground truth, which is why no accuracy figure ships.

---

## Slide 15 — Results divider · 0:05

> "Here's what that machinery produced."

## Slide 16 — 11 Segments Identified · 2:00

[Click. Give the table three seconds. Then point at the top row, and the Balikbayan row.]

> "Eleven named segments plus an honest leftover bucket, on all twenty-three million bookings.
> And the story of this table is one inversion, twice.
>
> Look at the top row: Leisure — half of all bookings, fifteen percent of the money, eighty
> dollars a booking. Now look three rows down: Balikbayan — families visiting home — one eighth of
> the bookings and more than a quarter of all revenue, at six hundred fifteen dollars a booking.
> Half the bookings earn a seventh of the money, and the revenue engine is a segment one quarter
> that size. Every commercial recommendation we make flows from that inversion.
>
> Two honesty notes on this table. Unassigned is two and a half percent — down from nearly ten
> when we started, and we kept it visible rather than forcing those bookings somewhere they don't
> belong. And the micro-segments row hides our biggest blind spot: Mabuhay Loyalist reads 0.03
> percent not because loyal customers don't exist, but because this data has no loyalty field —
> we can only see an award redemption. The segment is real; our sight is not. That's the loudest
> data request we're leaving PAL with.
>
> One more thing this table quietly asserts: every dollar in it is US dollars, confirmed by PAL in
> writing — and every figure is computed on the full population, not a sample."

**Guardrail:** if the "10 commercial segments" tile on slide 6 wasn't fixed and a panelist spots
the contradiction: "eleven — the tile carries the original ten-segment requirement count; the
taxonomy PAL approved is eleven plus Unassigned, and the table is correct."
**Guardrail:** never quote an accuracy number here. If asked: "no honest accuracy figure exists
yet, by design — any number today would be the rules grading themselves; the expert-labelled
sample unlocks the real one."
**Guardrail:** Family and Digital Nomad were retired *for cause* (no positive definition;
unimplementable in anonymous data) — not forgotten.

## Slide 17 — Visualizing a Sub Segment: Balikbayan/VFR · 1:45

[Click. Trace the thinnest ribbon, then the fattest, with a finger.]

> "And the inversion doesn't stop between segments — it continues inside them. This is machine
> learning's refinement job, shown for the revenue engine itself.
>
> Balikbayan splits into four sub-types, and they line up on booking horizon. The thinnest flow —
> seventeen percent of the segment, booking around sixty-six days out — is worth nine hundred
> ninety-five dollars a booking. The fattest flow — thirty-nine percent, booking twenty-six days
> out — is worth three hundred eleven. Three times the value, separated by nothing but how far
> ahead they buy and which fare they land on.
>
> Every big segment splits the same way — direction, timing, fare tier — and each model discovered
> that grammar independently, seeing only its own segment. These sub-types are stamped on every
> one of the twenty-one point seven million bookings in the five big segments, so the dashboard
> can slice by them today.
>
> What's it for? Not charging anyone more. It's for *not giving margin away*: a blanket Balikbayan
> discount today reaches the nine-hundred-dollar cohort at the same rate as the three-hundred-
> dollar one. Across all segments, six hundred forty-six million dollars of revenue sits in
> sub-types priced well above their segment average — that's the money a segment-blind discount
> quietly erodes."

**Guardrail — the one sentence that must be exact:** *"Four sub-types per parent is the
granularity we chose — the search offered up to four and the data would happily have taken more.
The continuum again, one level down."* **Never say "BIC chose four."**
**Guardrail:** these are the *sampled* profiles ($311→$995); the manuscript's population-exact fit
reads $322→$962 and states it supersedes these. If a panelist has both: "the manuscript names the
discrepancy and says which is authoritative — the finding, a ~3× spread on booking horizon, is
identical in both."
**Guardrail:** target with sub-types, never score with them — they're actionable partitions of a
continuum, and Balikbayan's are the least stable of the five (provisional, direction over edges).

## Slide 18 — Limitations & Fixes · 1:30

[Click. Tone shift: slower, plainer. This is a list of measurements, not apologies — never say
"unfortunately".]

> "Every result you've just seen comes with limits, and we found all of these ourselves — each one
> has a number and a source, which is only possible because someone went looking.
>
> No loyalty indicator — so the loyalty segment is invisible except through award redemptions.
> A possible undetected segment — and we can bound it: we planted artificial segments in the real
> data to test our own eyesight, and we reliably find anything at two percent of bookings or
> larger. Below one percent — about two hundred thirty thousand bookings — we are blind, and we
> say so rather than claiming the search was exhaustive. No ancillary revenue — so bag-heavy
> segments are undervalued. No demographics — the anonymous lens, working as designed.
>
> One more limit isn't printed here but we own it before you ask: the segment labels add almost
> nothing to *prediction* on top of the raw data — because they're built from that data; a
> compression can't beat its source. Their value is that a revenue manager, a marketer, and a
> dashboard all mean the same thing by 'Balikbayan'. A shared language, not a crystal ball.
>
> In flight: fare and corporate code fields — which settle our best open question about the Gulf
> corridor; penalty weights awaiting PAL's sign-off; and the expert-labelled sample that converts
> every self-referential check into a real accuracy number."

**Guardrail:** the incremental-prediction paragraph pre-empts the single most likely question of
the defence (reviewer Q19) — deliver it as a confirmation, not a concession.
**Guardrail:** "possible undetected segment" must always travel with its bound (≥2% found, <1%
blind). Quote majority floors, never the luckiest cell (0.114).
**Guardrail — if asked "which limitations are NOT on this slide?"** — answer, don't dodge:
revenue mix is the weaker stability leg (3.36 pp vs 1.71 pp on shares), the build varies by ±1
booking in 22.9M (1,830 tied keys, cause named), and the year-over-year model-transfer question is
unresolved (two methods disagree; no refit-cadence claim is made). All three are in the record.

---

## Exit — handoff to the business case · 0:10

> "So: eleven segments, twenty sub-types, four audits, and the limits in writing. What is all of
> that worth in dollars? [Presenter name] takes it from here."

---

## Pocket answers — the five likeliest interruptions in this block

*Fifteen seconds each. First sentence answers; one number; stop.*

- **"How do you know clusters don't exist rather than that you missed them?"** — "We hid
  artificial segments in the real data and our methods find them from two percent of bookings
  upward. Silence on the real data is therefore a finding. Below one percent we're blind, and we
  quote that."
- **"Did you validate any of this?"** — "Four label-free audits behind a firewall that stops us
  grading our own homework: 44 of 55 segment pairs clearly distinct on evidence the rules never
  used, stable across a twelve-month step at under two percentage points of movement. Backup slide
  available."
- **"Why eleven segments?"** — "On a continuum the count must come from the business — the data
  offers none. Ten came from the requirements, eleven from PAL's own decisions, and the audits
  test the chosen lines."
- **"Your model is just IF statements."** — "Deliberately. On a continuum, algorithmic boundaries
  are arbitrary and unexplainable; rules are auditable. The sophistication is in the machinery
  that checks the rules."
- **"What's your accuracy?"** — "No honest figure exists yet, by design — anything computable
  today is self-graded. The expert sample unlocks the real one, contested boundaries first."

**Running order sanity check:** 0:15 + 0:05 + 1:30 + 1:45 + 0:05 + 2:00 + 1:45 + 1:30 + 0:10 =
**9:05.** If you must cut, cut the "what's it for" paragraph on slide 17 to its first sentence
(−0:25) — never cut the limitations slide.

---

*Sources: `docs/final-defense-reviewer.md` (§1.2–§1.4, §5, §6) · `docs/defense-brief-2026-08-18.md`
(binding never-say list) · the 26 Aug deck audit. Last updated: 2026-08-27.*
