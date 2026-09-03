# Defence script — what to actually say

**Deck:** `assets/final-defense/CPT3_DefenseDeck_V3.pptx`, 26 slides.
**Running time:** 37:45 as timed below.

> ⚠️ **Two things to settle before rehearsing from this.**
> 1. **Built against the repo deck.** The team copy (`~/Downloads/CPT3_DefenseDeck_V3 1.pptx`, 8.1 MB
>    against the repo's 1.4 MB) has not been diffed against it — it almost certainly carries Jadd's real
>    dashboard screenshots. **Check that its slide 19 is the sub-segments Sankey.** If it isn't, every
>    number from 19 on shifts and this script needs remapping.
> 2. **Slides 1–4 and 14–15 are skeletons.** Those belong to Martin and Jadd, and their content is not
>    in the repo in a form I could quote. Owners write their own lines; the timings hold.
>
> Timings follow the section budget in `defense-slides-outline.md` — methodology 8 · dashboard 4 ·
> findings 7 · limitations 3 · recommendations 4 · conclusion 1. **Findings is the squeeze: seven slides
> in seven minutes** since the sub-segments slide landed. If you overrun anywhere, overrun there and cut
> slide 17 to a single sentence.

**How to read this.** `>` blockquotes are words to say. `[Square brackets]` are stage directions.
**Guardrail** lines are the things that lose marks if you get them wrong — read those before rehearsing,
not while presenting.

---

## Slide 1 — Title · 0:30 · MARTIN

[Skeleton — Martin's.] Names, programme, client. Keep it under a minute; nobody grades the intro.

## Slide 2 — Agenda · 0:30 · MARTIN

[Skeleton.] One pass down the sections. Say who speaks when so the panel knows when to hold questions.

## Slide 3 — Problem statement · 2:00 · MARTIN

[Skeleton — Martin owns the constraint story.] The spine of it: PAL sees bookings through Sabre's
anonymous lens. No CRM, no loyalty join. So two travellers with opposite purposes can look identical in
the data, and the airline can't tell them apart to talk to them differently.

**Guardrail:** this is **targeting**, not personalisation. Don't promise identity you don't have.

## Slide 4 — Terms of reference · 2:00 · MARTIN

[Skeleton.] The delivery table and the risk register. Every promised item was delivered or openly
redesigned.

**Guardrail:** "delivered differently" is not "not delivered" — own that phrasing rather than apologising
for it.

---

## Slide 5 — The row we model · 1:30 · JOSH

[Click. Point at the funnel, top to bottom.]

> "Thirty-eight million coupons. Twenty-three million bookings. Thirteen million customers. The middle
> row is the one we model, and the reason is about meaning rather than convenience.
>
> A trip purpose belongs to a purchase, not to a person. The same traveller is Corporate in March and
> visiting family in December. If we segmented people, we'd have to pick one and be wrong half the year."

[Beat.]

> "We tested the grain rather than assuming it. A booking averages 1.66 coupons, 42.7% return to their
> origin, and only 1.4% go in more than two directions. It recovers round trips cleanly, which is what
> you'd want from a unit that's supposed to mean one decision."

**Guardrail:** if pressed on the 12,306 excluded customers — every coupon they hold is non-revenue.
Staff and industry travel, excluded before feature engineering.

## Slide 6 — Timing and value · 1:30 · JOSH

[Click. Let both charts sit for a second.]

> "Left is when people buy. Right is what they buy. Both are lopsided the same way.
>
> The left chart is a cliff, not a hill. The busiest moment is the day before departure — **19.3% of
> bookings happen inside three days**, and the median is eighteen days out. That's why there's a rule for
> last-minute travel at all. It isn't an edge case, it's one booking in five."

[Point right.]

> "And the right chart is a supermarket, not a boutique. Two-thirds of the book sits in the two cheapest
> fare brands. All of business class is under one booking in thirty. So asking *what fare did they pay* is
> like trying to tell people apart in a room where everyone's wearing jeans — it sorts almost nobody."

[Pre-empt it before the panel does.]

> "One thing to flag on the left chart: the spike at 120 days is our display cap, not a cluster. Everyone
> who booked four months out or more is stacked into that last column."

**Guardrail:** **booking-grain numbers only on this slide** — median 18 days, 19.26%. The 25-days-and-13.3%
pair is coupon grain and contradicts slide 20's own flag count of 4.41M.

## Slide 7 — Network and grain · 1:30 · JOSH

[Click.]

> "Fifty-eight per cent of bookings never leave the Philippines. Then East Asia, Southeast Asia, North
> America. Every corridor on the right of that chart is somewhere Filipinos have gone to work, and
> **34.6% of bookings are bought abroad**. That's the diaspora footprint, and it's the most useful signal
> we have — because the rules can't see who you are, but they can see where you bought the ticket."

[Beat.]

> "The number that flips the chart: domestic is 58% of bookings and **19% of revenue**. So 'domestic-heavy'
> is true by headcount and false by money. International earns about 5.7 times more per booking."

> "The other half of this slide is the base itself. **Seventy-four per cent of customers appear once** —
> inside our window. About a quarter come back within a year. Which is the second reason we model the
> booking: for most of the base, a customer profile would just be their single booking restated."

**Guardrail:** say **"in-window"**, never "never return". The rate is right-censored — the earliest full
cohort reaches 40.5%. And if asked how long a relationship lasts, it's **285 days** among customers who
returned, not the 82-day average that includes everyone who booked once.

## Slide 8 — First clustering attempt · 1:30 · JOSH

[Click. Say the version caveat immediately — it disarms the one catchable thing here.]

> "Two quick notes before the picture. These are the pre-redesign labels — Family and Last-Minute became a
> dropped segment and a flag on the eighteenth. And it's a uniform sample, not stratified."

[Now the point.]

> "Same sixty thousand bookings, twice, in identical coordinates. Left is what the algorithm found on its
> own. Right is the same dots coloured by our business rules.
>
> Neither picture has gaps. We expected a box of crayons and got a rainbow."

[Beat.]

> "And the fair objection is that the right-hand panel is circular — those axes are built from the same
> fields the rules read. That's true, and it's why it matters: the rules are being plotted on their most
> favourable possible ground, and they *still* don't form islands."

**Guardrail:** the diagonal streaks are the binary encoding's lattice, not structure. `k=9` is the top of
the search range, not a fitted optimum — and it has nothing to do with the nine segments in the legend.
Quote **silhouette 0.091** in the full feature space; the 2-D view scores worse, so the picture overstates
the overlap.

## Slide 9 — The continuum · 2:30 · JOSH

**This is the hinge. Don't rush it.**

[Click.]

> "Ten methods, six different families of mathematics. **None of them reaches the strong-structure band** —
> the ceiling is 0.38 where you'd want above 0.5. When we checked whether the methods agreed with each
> other, the median agreement was 0.41. If real groups existed, different methods would find the same ones."

[Beat. Then the objection, volunteered.]

> "Which leaves the question that could sink all of this: maybe our methods are just blind.
>
> So we tested that. We planted fake segments of known size into the real data and checked whether we'd
> find them. We do, down to about two per cent of bookings. **Below about one per cent we're blind, and
> that's roughly two hundred and twenty-nine thousand bookings** — a group PAL could genuinely be missing.
> We state it as a limitation rather than waiting to be asked."

> "So: customers come on a dial, not in boxes. Instead of asking an algorithm to invent boxes, we let the
> business draw the lines and made the algorithms prove the lines sit in sensible places."

**Guardrail:** majority-rule floors only — ≈0.494 at 2%, ≈0.219 at 5%. **Never 0.114**; that's the luckiest
of twelve cells. And the H₀ component count is retired, so don't cite "one significant component" as clean
evidence.

---

## Slide 10 — Architecture · 2:00 · JOSH

[Click. Walk the five stages left to right, fast.]

> "Extract, ingest, clean, then the waterfall, then the checks. The fourth box is the deliverable — first
> match wins, eleven segments plus an honest Unassigned, at booking grain.
>
> The load-bearing sentence is that **the rules label and the machine learning checks**. ML has three jobs
> here: it refines the oversized segments, it tests whether the boundaries hold, and it watches for drift.
> It never assigns a label."

[If the panel looks sceptical about where the ML went, point at stage five and move on.]

> "And every 'cannot-be' rule PAL's revenue managers gave us is asserted in code on every build. Not
> reviewed — asserted. If a change breaks one, nothing ships."

## Slide 11 — Iteration arc · 1:30 · JOSH

[Click.]

> "The model we're defending is the fourth design. The first won a seven-algorithm bake-off on a thirty
> thousand row sample — HDBSCAN, silhouette 0.435 against KMeans at 0.167. Then the real extract arrived
> and it collapsed, because the real features are categorical and a density method needs terrain to grip.
>
> That's why no number from the prototype reaches a deliverable. It taught us which questions to ask."

[The honest paragraph is the one worth the time.]

> "What the iterations cost: weeks on a prototype we now quote nowhere, and a first waterfall that
> satisfied only four of PAL's six hard rules. **Ordering rules by priority turned out not to be the same
> thing as enforcing them.** Putting Corporate above Bleisure expresses a preference — it does nothing to
> stop a booking that must never be Corporate from landing there. Each of those two failures needed its own
> explicit branch."

## Slide 12 — The ledger · 1:30 · JOSH

[Click. **Do not read the table.** Point at three rows.]

> "Eleven dated iterations, each one a script in the repo with its output report. Three worth pointing at.
>
> Eleventh of May — we backed HDBSCAN when the evidence supported it. Twenty-third of July — we dropped it
> the day the real data said otherwise. And the twenty-eighth: GMM beat our refinement layer on a benchmark
> **and we didn't switch**, because the benchmark scored top-level segmentation and that layer's job is
> sub-segmenting inside a parent. Winning a different race doesn't make you the better runner for this one."

> "Two of the eleven rows changed nothing. We kept them, because a ledger that only records wins is a
> marketing document."

## Slide 13 — The validation harness · 2:30 · JOSH

**If one slide earns the methodology grade, it's this one.**

[Click.]

> "Four mechanisms, and the theme is that none of them relies on us being careful.
>
> A rule label is a function of its inputs, so those inputs can validate nothing — you can't mark your own
> exam with the answer key you wrote. There's a code contract listing every field the rules consumed, and
> it **raises an error**, not a warning, if validation touches one."

[Beat.]

> "It also catches the subtle version. Destination region equals 'Domestic' *is* the domestic flag wearing
> different clothes. A name check can't see that; this one measures it per comparison."

> "Second: flights that haven't happened yet look exactly like churn. Outcome fields near the extract
> boundary are excluded and we publish the censoring curve, so the exclusion is visible instead of quiet.
>
> Third, controls with teeth. Random splits have to score a coin flip before we read any real number, and
> they do — 0.494 to 0.513. One of our own instruments returned **between two and a hundred and thirty-one
> components on identical data**. We retired it, and we went back and qualified the earlier report that had
> used it."

> "Fourth: six hard SME rules checked against every build, read from PAL's own spreadsheet rather than a
> copy of it. That check has already caught a draft that quietly violated two of them."

[Land it and stop.]

> "A retired instrument and a withdrawn number aren't embarrassments. They're evidence the harness bites."

**Guardrail:** the negative control is reported first and loudly, but it doesn't *abort* the run — that's a
reporting convention, not a hard gate. If asked whether it's enforced like the others: *"the circularity
guard raises; hardening the control into an abort is on the list."* Say it plainly.

---

## Slide 14 — Dashboard divider · 0:20 · JADD

[Skeleton.] Hand over. One line.

## Slide 15 — Dashboard · 3:40 · JADD

[Skeleton — Jadd's, and the demo is his.] The spine, from the study guide: it reconciles to the row —
**38,116,259 in equals out, asserted on every build**. Four BI traps designed out. Persona cards carry
Trust and DataCaveat columns so a reader can tell measured from editorial.

**Guardrail:** admit the one manual `.pbix` step rather than glossing it. Have the recording tested on the
venue machine.

---

## Slide 16 — The taxonomy · 1:00 · JOSH & JADD

[Click. **Read the shape, not the rows.**]

> "Eleven segments and an honest Unassigned at 2.47%. Two rows tell you the whole commercial story.
>
> Leisure is **half the bookings and a seventh of the money**. Balikbayan — Filipinos abroad coming home —
> is an eighth of the bookings and **more than a quarter of the revenue**. Volume and value run in opposite
> directions, and everything on the next six slides is a consequence of that."

> "Riding alongside: a short-lead flag on 19.3% of bookings, and value bands. Family and Digital Nomad were
> retired for cause — Family had no positive definition beyond 'a group nothing else claimed'."

## Slide 17 — Share versus revenue · 1:00 · JOSH & JADD

[Click. **Silence for three seconds.** The picture does this one.]

> "Half the bookings earn a seventh of the money.
>
> Which means a route review that can't see segments ranks by volume — and volume is pointing at the
> cheapest half of the book. That's the case for this whole project in one chart."

## Slide 18 — What each segment buys · 1:00 · JOSH & JADD

[Click.]

> "Premium cabins don't make premium segments. Balikbayan is the revenue engine and it flies on **70%
> budget-band fares** — its value is route length and season, not cabin.
>
> And short-lead cuts across segments rather than being a leisure quirk. OFW books later than the book
> average — support tickets, not promo-chasing — while Balikbayan plans furthest ahead at 6.8%. That
> contrast is a pricing lever the old taxonomy couldn't see."

**Guardrail:** say it about your own chart before anyone asks — the two bars reading ~95% premium are
**partly rule echo**, because fare tier is in those segments' definitions.

## Slide 19 — Sub-segments · 1:00 · JOSH

[Click. This is the only slide showing what the ML produced. Let it land.]

> "The rules give PAL eleven segments to talk about. The machine learning gives twenty cells to act on.
>
> This is Balikbayan, divided four ways by latent class analysis. Ribbon width is share, and the position
> and colour are revenue. So the inversion is right there — **the thinnest flow earns the most**, at
> $995, and the fattest earns the least, at $311. Same asymmetry as slide 17, one level down, inside a
> single segment."

> "Every sub-type here is a round trip, so the only thing that varies is how far ahead they book. Three
> times the value on one dial."

**Guardrail:** **never say "BIC chose four"** — the search range stops at four and BIC wanted the maximum in
all five parents. That's the continuum again, one level down. Four is a granularity choice you own.

## Slide 20 — What changed · 1:00 · JOSH

[Click.]

> "Unassigned fell by three quarters — 9.58 to 2.47. Five point four million bookings genuinely
> reclassified. And the flag now sees **4.41 million short-lead bookings against the 2.95 million the old
> segment ever caught** — including 864,000 OFW and 315,000 corporate bookings that were short-lead all
> along and invisible inside their own segments.
>
> Fifty per cent more visible volume without moving a single threshold."

[Point at the box on the right.]

> "And these are the numbers we refuse to quote. Sixty-two point seven per cent 'reclassified' is mostly a
> rename. Corporate at 35.6% short-lead is a rule branch that only admits short-lead bookings — the honest
> figure is 23.3%. If you've seen either of those in an earlier document of ours, we said so here first."

**Guardrail:** if anyone reads the 74% Unassigned drop as a finer taxonomy — **Leisure now holds 50.6% of
the book**, and the missing middle rung is the next taxonomy decision. Volunteer it.

## Slide 21 — Validation results · 1:00 · JOSH

[Click. **Open with the framing, not the number.**]

> "Everything you've seen was labelled by rules we wrote. We don't have an answer key yet — that's the SME
> sample, and it's outstanding. So here are four checks that don't need one.
>
> Are they distinguishable? **Forty-four of fifty-five boundaries clearly distinct, none indistinguishable**,
> on fields no rule ever read. Do they predict? The label alone beats a coin flip at 0.60, and adds almost
> nothing on top of the raw features — which is arithmetic, because it's *made* of them. A compression can't
> beat its source. Could we have missed one? Down to two per cent, no; below one per cent, we're blind and
> we say so. And a year later, the sizes hold."

**Guardrail:** **0.861 is the adaptive median** — the strip on the slide says so, so don't also read it
aloud. The chart's lowest dot is Ultra Wealthy versus Leisure at 0.611, *not* the OFW–Balikbayan boundary at
0.713. And never present "0.608 to 0.72" as an improvement: different tests, and like-for-like it fell.

## Slide 22 — Gulf and cost · 1:00 · JOSH & JADD

[Click.]

> "Our best domain finding. Manila–Gulf round trips pile up at twenty-eight to thirty-two nights —
> **19.1% of them, against 8.5% at a fortnight**. No other corridor comes close.
>
> And we're stopping one step short of the obvious conclusion, because a one-month maximum-stay fare rule
> would paint the identical picture. Fare basis codes settle it. Until then it's a pattern, not a cause."

> "Second half: the first sourced dollar spread this project has had. **$495 to $9,784** of annual value at
> risk per misclassified customer — a twentyfold range. It replaces a penalty ladder whose dollar column was
> penalty times four thousand, and which ranked two segments backwards against measured revenue. PAL asked
> to see a scored run first, so these weights are a proposal."

**Guardrail:** volunteer that two pieces of the SME's own claim failed — no 45-day leave spike exists, and
pooling Hong Kong and Taipei with the Gulf drags discrimination below chance. You test what the client tells
you too.

---

## Slide 23 — Limitations · 2:30 · JOSH

[Click. **Tone is everything here.** These are measurements, not apologies. Never say "unfortunately".]

> "Five limits, and we found all five ourselves.
>
> No loyalty field, so Mabuhay sits at 0.03% and can't be measured — only awaited. We're blind below about
> one per cent prevalence. The build moves by one booking between runs: 1,830 rows have tied sort keys, and
> our own build assertion is what caught it. No ancillary revenue, which understates the bag-heavy segments —
> and those are the two we're telling PAL to protect, so that bias runs against our own recommendation."

[The fifth one is the question you'll get anyway. Own it.]

> "And our labels add almost nothing to a model that already has the raw features. By design, not by
> failure — they're made of those features. What PAL gains isn't prediction, it's a shared vocabulary that
> a revenue manager, a marketer and a dashboard all resolve the same way."

> "In flight: fare basis codes, the penalty weights awaiting PAL's sign-off, an SME-labelled sample, and no
> refit-cadence claim until one stability test runs across more seeds. **The dashboard ships no accuracy
> figure today** — any number we could print would be the model grading its own homework."

## Slide 24 — Recommendations · 3:00 · MARTIN

[Martin's, and the content is on the slide. The stance worth defending out loud:]

> "Data investments before algorithm work. Every model experiment we ran says the ceiling is in the
> features, not the method."

Four in run order: act on the segments — protect Balikbayan, grow the two premium segments, use the
short-lead flag across every segment rather than as a bucket. Then the loyalty join, fare basis codes,
ancillary revenue, an SME sample. Then deploy: deterministic rules mean a SQL job, not a model server, with
the drift monitor as the tripwire. Then dashboard ownership to PAL BI, with the governance columns surviving
every edit.

## Slide 25 — Conclusion · 1:00 · JOSH

[Click. Three beats. **End on the third and stop.**]

> "PAL's customers sit on a continuum, ten algorithms agree, and drawing the lines by business rule and
> validating them independently was the right design. We'd choose it again.
>
> What we're handing over: eleven named, costed segments across 22.9 million bookings, each carrying its own
> trust level, on a dashboard that reconciles to the row.
>
> And what makes those labels safe to use is the machinery around them. Circularity contracts. Controls that
> retired one of our own instruments. Withdrawn numbers named in writing."

[Stop. No recap.]

## Slide 26 — Thanks · 0:15

> "Thank you. We'd like to take your questions."

**Backups open on the machine:** the 55-pair matrix (`pairs.csv` — the per-pair breakdown is the most
likely ask), the detection grid, the withdrawn-numbers list, and the v1→v2 flows.

---

## Before you rehearse

Four sentences carry more weight than anything else in the script. Drill them until they're one breath:

1. **Slide 8:** "These are the pre-redesign labels."
2. **Slide 20:** "Leisure now holds half the book, and the missing middle rung is the next taxonomy decision."
3. **Slide 21:** "We don't have an answer key yet, so here are four checks that don't need one."
4. **Slide 19:** "Four is a granularity choice we made, not a structure we discovered."

The full per-slide guidance for the two hardest slides is in `defense-study-guide.md` §6.1 (limitations)
and §6.2 (validation). The never-say table is §5 — read it the night before.

*Companion to `docs/defense-study-guide.md` and `docs/defense-slides-outline.md`. Last updated 20 August 2026.*
