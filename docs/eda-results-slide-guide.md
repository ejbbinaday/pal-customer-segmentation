# Slide Guide — EDA & Initial Results (30 minutes)

**Session:** EDA and initial results walkthrough
**Format:** **19 min talk · 11 min Q&A** · 13 slides + 5 backup
**Assumed audience:** mixed — some technical, some commercial. Where the two need different words, the
script gives the business phrasing first and the technical detail in *If pressed*.

> **The thesis, in one sentence — say this in the first 30 seconds and again at the end:**
> *We got the real 38-million-row extract, and the data told us something we didn't expect: there are no
> natural customer clusters to find. So we changed the design — business rules label, and machine learning
> checks the labels. Nine segments are live and already in Power BI.*

**Companion docs:** `docs/pipeline-study-guide.md` (the full detail behind every slide) ·
`docs/mentor-presentation-guide.md` (a shorter, pivot-focused talk track) ·
figures in `reports/study_guide/`.

---

## Timing budget

| # | Slide | Min | Cum. |
|---|---|---:|---:|
| 1 | Cover + the one-line thesis | 0.5 | 0:30 |
| 2 | What we were given | 1.0 | 1:30 |
| 3 | Three facts that shape everything | 1.5 | 3:00 |
| 4 | Data quality — clean but thin | 1.0 | 4:00 |
| 5 | The row we model — and why | 1.5 | 5:30 |
| 6 | Timing and value | 1.5 | 7:00 |
| 7 | Geography and channel | 1.5 | 8:30 |
| 8 | ⭐ **The pivot — no natural clusters** | 2.5 | 11:00 |
| 9 | Confirmed four more ways | 1.5 | 12:30 |
| 10 | What we built instead | 1.5 | 14:00 |
| 11 | **Initial results — nine segments** | 2.0 | 16:00 |
| 12 | Does it hold up? | 1.5 | 17:30 |
| 13 | Gaps, and what we need | 1.5 | 19:00 |
| — | **Q&A** | **11.0** | **30:00** |

**If you are running late, cut in this order:** slide 7 → slide 4 → slide 9. Never cut 8 or 11.
**If you are cut to 10 minutes:** slides 1, 3, 8, 11, 13 only. That sequence still tells the whole story.

---

## Slide-by-slide

### Slide 1 — Cover · 0:30

**On the slide:** Project title · "EDA & Initial Results" · date · the one-line thesis in large type.

**Say:**
> "Thirty minutes: what the data actually looks like, one finding that changed our approach, and the first
> segmentation results. I'll leave a good ten minutes for questions — and there's one finding I'd
> genuinely like your challenge on."

*Signalling that you want challenge early makes the pivot land as confidence rather than defensiveness.*

---

### Slide 2 — What we were given · 1:00

**On the slide:** a simple table.

| | |
|---|---|
| Coupon rows | **38,116,260** · 42 columns |
| Source files | 4 gzipped CSVs (2024 · 2025 · 2026 Jan–May · 2026 Jun–2027 May) |
| Distinct customers | 13,447,672 — zero nulls on the key |
| Travel dates | 2024-05-01 → 2027-05-31 |
| Ticket issue dates | 2023-03-24 → 2026-07-20 |
| Carrier | PR only |

**Say:**
> "One coupon is one flown leg — Manila to Cebu to Davao is two rows. Everything runs through DuckDB and
> Parquet, so a full rebuild is minutes on a laptop, and there's no licence cost anywhere in the stack."

**If pressed — "is the customer key trustworthy?":** 19.73% of customers appear in more than one source
file with consistent behaviour. That's what tells us the ID persists across extracts and the customer-level
rollup is valid.

---

### Slide 3 — Three facts that shape everything · 1:30

**On the slide:** three boxes, nothing else.

1. **Most customers fly rarely** — median 2 coupons · only **26.1% book twice inside our window**
   (**26.5% within 12 months** of their first booking — quote the horizon, never "never return")
2. **An economy, Philippines-centred airline** — 95.2% economy · **88% in the three cheapest fare brands** · 57.7% domestic
3. **Clean, but demographically thin** — near-zero operational nulls · **age 57% missing** · award tickets **0.02%**

**Say:**
> "These three facts explain every decision that follows. There's no rich purchase history to cluster on.
> The value axis is squeezed into a narrow band. And we can't see who the customer *is* — only what they
> *did*. So the segmentation has to run on behaviour: timing, route, direction, fare, channel."

**This is the slide that makes the pivot feel inevitable.** Land it properly and slide 8 becomes an
obvious consequence rather than bad news.

---

### Slide 4 — Data quality · 1:00

**On the slide:** a short pass/flag table.

| Check | Result |
|---|---|
| Rows removed in cleaning | **1** (a junk cabin code) |
| Exact duplicates | ~0 on the natural coupon key |
| Flown vs open | 93.4% / 6.6% |
| Refunds · non-revenue · award | 0.10% · 0.08% · 0.02% |
| Age known | 43% |
| Reissues (negative lead time) | 1,728 rows — clamped and flagged |

**Say:**
> "The operational data is genuinely clean — we removed exactly one row out of thirty-eight million. What's
> missing is demographic, not operational. Every exception ships as a flag rather than being quietly
> filtered, so totals always reconcile to the full extract."

---

### Slide 5 — The row we model, and why · 1:30

**On the slide:** the funnel.

```
38,116,259 coupons     one flown leg
        ↓  group by customer + issue date
22,911,450 bookings    ONE PURCHASE DECISION  ← the modelling row
        ↓  group by customer
13,435,365 customers   only 26% book more than once *in our window*
```

**Say:**
> "A trip *purpose* belongs to a purchase, not to a person. The same traveller can be Corporate in March
> and visiting family in December — if we segmented people we'd have to pick one and be wrong half the
> year. So the booking is the unit."

**If pressed — "is that grain justified?":** we tested it, we didn't assume it. It recovers round-trips
cleanly at 1.66 coupons per booking, 42.7% of bookings return to origin, and only 1.4% have more than two
directions. We also excluded 12,306 customers whose every coupon was non-revenue — staff and industry
travel.

---

### Slide 6 — Timing and value · 1:30

**On the slide:** `reports/study_guide/eda_03_lead_value.png`

**Say:**
> "Left is when people book. Median 18 days out, but look at the spike at zero — **19.3% book inside three
> days.** That's a real last-minute population, and it's why we have a rule for it. Right is what they buy:
> two-thirds of the book sits in the two cheapest fare brands."

**Grain warning — quote booking-grain numbers on this slide.** The figure is drawn from the 22.9M
**bookings**, so it is median **18** days and **19.26%** inside three days (= the 4,411,666 the flag
covers, quoted everywhere else in the deck). Median 25 / 13.3% are the **coupon**-grain figures
(38.1M coupons); multi-leg trips are planned further ahead, so coupon-weighting looks more advance-booked.

**Watch for:** someone reading the spike at 120 days as a cluster. **It's the display cap, not a finding**
— say so before they ask.

---

### Slide 7 — Geography and channel · 1:30

**On the slide:** `reports/study_guide/eda_02_region.png`, plus a channel line as text.

> Channels: WEB/APP 35.4% · Travel Agency 27.8% · OTA 14.9% · Ticket Office 6.1% · Contact Centre 4.7% ·
> **Sea Crew 3.7%** · NDC 2.4% · TMC 1.8%

**Say:**
> "58% domestic, then East Asia, Southeast Asia and North America. **34.6% of bookings are issued
> abroad** — that's the diaspora footprint, and it's the single most useful signal we have. Note Sea Crew
> as its own channel: a contract-driven population that behaves nothing like a leisure traveller."

**Grain note:** 34.6% is the **booking**-grain foreign-issue share, which is what belongs next to this
booking-grain chart. **38.4%** is the **coupon**-grain figure — foreign-issued trips carry more legs, so
coupon-weighting inflates them. The region bars themselves need no such caveat: domestic is 57.69% of
bookings and 58.52% of legs, so "58% domestic" is safe at either grain.

**If pressed — "why is Europe zero?":** no own-metal European *sectors* in this extract, so it's an
absence of operation, not an absence of demand. Precisely: **6,334 bookings do have a European trip
endpoint** (and 1,740 a South Asian one) via OAL codeshare beyond-points — the bar is built from flown
own-metal sector endpoints, which is why it reads 0%.

**If pressed — "how do you label a two-stop trip?":** `dest_region = max(intl_region)`, which for a
multi-region itinerary picks the **alphabetically last** region, not the primary destination. **785,673
bookings (3.4%) touch more than one international region**, and for **377,331 (1.65% of the book)** the
bar they sit in is not their final destination's region — systematically pushing trips into *Southeast
Asia* (it sorts last). Reassigning by final destination moves **SE Asia 11.78% → 10.56%** and **East Asia
14.80% → 15.67%**; nothing else shifts more than 0.2pp and the ordering is unchanged. Own it as a known,
measured 1.65% labelling edge, not a defect that changes the story.

---

### Slide 8 — ⭐ The pivot · 2:30

**The most important slide. Do not rush it.**

**On the slide:** `reports/study_guide/clust_01_bic_ari.png`

**Say:**
> "We set out to let an algorithm discover the segments. This is what happened.
>
> The left chart is a score for 'how many groups are in this data' — lower is better, and normally it falls,
> bottoms out, then rises. That bottom is your natural number of groups. **Ours never bottoms out. It just
> keeps falling.** There is no natural number of segments here.
>
> The right chart says that when we *do* force groups out, they only agree with the business taxonomy
> about a third of the way.
>
> **Our customers are a rainbow, not a box of crayons.** Red really does blend into orange, and there's no
> line in the spectrum where one stops."

**Then the reframe — this is the sentence that decides how the room takes it:**
> "That sounds like a negative result, and it is — but it's the most useful thing we found. It means the
> boundaries are a **commercial decision, not a mathematical discovery**. Which is arguably how it should
> be: your commercial team should decide what 'Corporate' means, not an algorithm."

---

### Slide 9 — Confirmed four more ways · 1:30

**On the slide:** `reports/study_guide/ms_fig1_separation_ceiling.png` (or `clust_02_pca.png` for a
less technical room — the PCA scatter shows the same thing with no maths).

**If you show `clust_02_pca.png`, know these five things about it:**

| Question you will get | Answer |
|---|---|
| "It's only 2 of 16 dimensions" | PC 1 + PC 2 hold **57.7%** of the variance; 4 dims reach 81%. A real view, not a thin shadow — and the 42% off-screen is exactly why ten formal methods follow |
| "Overlap by eye isn't a measurement" | Rule-segment silhouette **0.091** in the full feature space (0 = groups sit on top of each other). The 2-D view scores −0.16, so the picture is *harsher* than the data — quote **0.091** |
| "Why nine classes?" | `k* = argmin(BIC)` over k = 3–9, and BIC falls monotonically, so k\* is the **top of the range**. The model wanted more classes than we offered — that *is* the continuum finding. It is **not** paired with the 9 segments on the right |
| "Stratified by what?" | Nothing — it's a **uniform** reservoir sample (seed 42). Deliberate: balancing by segment or region equalises group sizes and can manufacture structure. The old "stratified" wording was wrong and is fixed |
| "Isn't the right panel circular?" | Yes, and say so first: the axes are built from the same 11 fields the rules read, so the rules get **home advantage** in this projection — and still form no islands. That makes the overlap harder to dismiss, not easier |

**Regenerated 23 August on v2 labels** — the retired names are gone from the legend, so the v1-era
warning is discharged for the *files*; **the deck still embeds the 23 Jul versions and needs a
re-insert** (until then, say "v1 labels, before the redesign" when it goes up). The sweep now starts
at k = 1: BIC falls 1,148,667 → 928,770 with no elbow anywhere, not even at 2. One new number to
handle with care: the ARI panel peaks at **0.537 at k = 2**, and that cut is geography (0.909 against
the domestic/international bit alone; Corporate splits 50/50, its actual domestic mix) — quote it only
with that qualifier; the customer-structure ceiling is still **0.389 at k = 4**. Silhouette 0.091
unchanged.

**Say:**
> "We didn't take one method's word for it. Ten methods, six different families of mathematics. **None of
> them reaches the 'strong structure' band** — the ceiling is 0.38 where you'd want above 0.5. And when we
> checked whether the methods agreed with *each other*, the median agreement was 0.41. If real groups
> existed, different methods would find the same ones."

**If pressed — "maybe your methods are just blind?":** *(the best question you'll get — welcome it)*
> "We tested exactly that. We planted fake segments of known size into the real data and checked whether
> we'd find them. We do, down to about 2% of bookings. **Below about 1% we're blind, and we state that as a
> limitation.** So the null result is bounded, not just asserted."

---

### Slide 10 — What we built instead · 1:30

**On the slide:** the waterfall ladder, ten rungs, first-match-wins.

**Say:**
> "So we inverted the design. **Business rules draw the boundaries; machine learning checks that we drew
> them sensibly, splits the segments that are too broad, and watches for drift.**
>
> Read it top to bottom — first line that matches wins, nothing below is consulted. Every label is
> auditable: you can trace any booking to the exact rule that produced it. There is no black box at the
> top level."

**Flag the weak spot yourself, before anyone finds it:**
> "Rules five and six are separated by a single bit — did they buy a return ticket. That one bit decides
> 6.8 million bookings between overseas workers and returning Filipinos. **It's the least defensible line
> we have, and it's the first thing I want your view on.**"

---

### Slide 11 — Initial results · 2:00

**On the slide:** `reports/study_guide/eda_01_segments.png`

**Say:**
> "Nine named segments plus a deliberate gap, on all 22.9 million bookings, already joined back down to
> every coupon and shipped to Power BI — 38.1 million rows in, 38.1 million out.
>
> **The two bars are inverted, and that's the commercial story.** Budget/Adventure is 39% of bookings at
> the lowest value per booking. Premium Bleisure is 2.1% at roughly **twenty times** that. A
> headcount-ranked report buries the most valuable segment on the airline."

**Three things to say out loud before they're asked:**
1. **9.6% Unassigned is deliberate.** Mostly Philippines-issued economy passengers flying abroad, matching none of the rules. *We left it blank rather than folding it into the nearest segment to tidy the chart.* It needs a definition from your side.
2. **Mabuhay at 0.03% cannot be true.** There's no loyalty-tier field, so award redemption is the only thing we can see. *The segment is real; our ability to see it is not.*
3. ⚠️ **The axis says USD, but the currency is undocumented.** Treat the ratio as the finding, not the absolute values.

---

### Slide 12 — Does it hold up? · 1:30

**On the slide:** two findings, side by side. Optionally `ms_fig4_construct_auc.png`.

**Say:**
> "Two independent checks. First: can you tell the segments apart using only evidence the **rules never
> saw** — age, departure month, how often someone books? Mostly yes. The one weak pair is overseas workers
> versus returning Filipinos, which is the single-bit boundary I flagged.
>
> Second, and we only found this last week: **length of stay is derivable** from the coupon dates, for 42%
> of bookings. We never used it in any rule — and median stay lines up exactly with the personas.
> Last-minute travellers 3 nights, Corporate 4, Premium Bleisure 10, returning Filipinos 13, pilgrimage 33.
> **Nothing in the rules put that ordering there.**"

**The honest limit — say it before the Q&A, not during:**
> "What we cannot yet give you is an accuracy figure. Every number we can compute today is measured against
> the same rules that created the labels — that's marking our own homework, and we won't present it as
> accuracy. The machinery is built and tested; it needs about a thousand bookings hand-labelled by someone
> on your commercial team."

---

### Slide 13 — Gaps and asks · 1:30

**On the slide:** three gaps, four asks.

**Known gaps, stated not hidden**
- **9.6% Unassigned** — needs a commercial definition
- **Mabuhay invisible** — no loyalty-tier field
- **Digital Nomad not implemented** — the tenth target segment; we've sized the candidate population at ~726k long-stay round trips and would rather you define it than us guess

**What we need**
1. **~1,000 hand-labelled bookings** — unblocks a real accuracy number *(the critical path)*
2. **A definition for Unassigned** — 2.19M bookings
3. **Mabuhay tier on the booking record**
4. **Repeated dated extracts** — for genuine booking-curve analysis

**Close on:**
> "The segmentation isn't a forecasting engine and we won't sell it as one. What it gives you is a shared,
> auditable language for 22.9 million bookings — and the first honest map of where value concentrates,
> where it's quietly eroding, and where we're still blind."

---

## Backup slides — have these ready, don't present them

| # | Slide | Pull it up when someone asks |
|---|---|---|
| B1 | `clust_02_pca.png` | "Show me what a continuum actually looks like" |
| B2 | `ms_fig5_detection_floor.png` | "How do you know you didn't just miss a segment?" |
| B3 | `ms_fig6_temporal_stability.png` | "Will this still be true next year?" |
| B4 | `sub_01_subtypes.png` | "So what did the machine learning actually contribute?" |
| B5 | Value-tier ladder (1–7 farebrand table) | "Where does your value score come from?" |

---

## Q&A preparation

**The ten most likely questions, with short answers.** Say the first sentence; expand only if they push.

| They ask | You say |
|---|---|
| *"So you didn't really use machine learning?"* | We benchmarked ten methods across six families — the finding was that no natural clusters exist. **Acting on that is the result.** ML now does three jobs: sub-segmentation, validation, drift monitoring. |
| *"How accurate is it?"* | **No honest number yet, by design rather than omission.** Everything computable today is circular. It needs ~1,000 expert-labelled bookings — that's our main ask. |
| *"Why nine segments and not ten?"* | The requirement asks for ten; **Digital Nomad isn't implemented.** We've sized the candidate population and would rather you define it than we guess. |
| *"Can I use this for pricing tomorrow?"* | **Not for pricing yet** — labels are preliminary. Today it's solid for reporting, targeting and prioritisation. |
| *"What's Unassigned — is it junk?"* | **The opposite.** It out-earns overseas workers per booking and 18.6% fly premium. It's the largest actionable gap we have. |
| *"Why is Mabuhay so small?"* | Because there's no loyalty field. The segment is real; our ability to see it is not. **A data request, not a model change.** |
| *"Which boundary is weakest?"* | Overseas workers vs returning Filipinos — 6.8M bookings split on one bit, and the lowest score in our independent check. |
| *"Will it survive next year?"* | We tested one 12-month step: sizes hold (1.71 pp), and on the best-transferring method a model fitted a year earlier transfers as well as a fresh one (GMM ratio 1.24 — though LCA is 0.89, so the methods disagree). **But that's one step inside one extract** — not evidence against a demand shock. |
| *"Why does the trend fall off a cliff?"* | It doesn't — the data stops 21 July 2026 and later months are still filling. Always filter to complete travel months. |
| *"What are you blind to?"* | Three things: any segment under ~1% of bookings; anything needing loyalty tier, stay length or ancillary spend; and behaviour under a shock. |

### Questions you should hope for

- *"Are your methods just blind?"* → the planted-segment test. **Your best answer of the day.**
- *"Isn't your validation circular?"* → yes, and we say so first — that's why the four label-free studies exist.
- *"Why didn't you switch to the method that scored higher?"* → because the benchmark tested a different task than the pipeline stage. The re-test is specified.

### If you genuinely don't know

> *"I don't have that in front of me — let me check and come back today."*

**Do not improvise a number.** Every figure in this deck is traceable to a script, and that traceability is
worth more than an answer.

---

## What not to claim

- ❌ Any **accuracy or recall figure** — there is no honest one yet
- ❌ That the **segment names are validated** — say *"behaviourally validated; names not externally confirmed"*
- ❌ That the **sub-types are actionable** — they're provisional, split-half 0.495
- ❌ Absolute **revenue values in a stated currency** — the unit is undocumented; quote ratios
- ❌ **"Ten segments"** — it's nine named plus Unassigned

---

## Pre-flight checklist

- [ ] Figures exported from `reports/study_guide/` and legible at the back of the room
- [ ] `docs/pipeline-study-guide.html` open in a second window for drill-downs
- [ ] `outputs/features_real/summary.md` open for exact segment counts
- [ ] Backup slides B1–B5 loaded but hidden
- [ ] Know your three numbers cold: **38.1M coupons · 22.9M bookings · 9 segments + 9.6% Unassigned**
- [ ] Decide who fields commercial questions vs method questions before you walk in

---

*Companion to `docs/pipeline-study-guide.md`. Figures: `reports/study_guide/`. Last updated 13 August 2026.*
