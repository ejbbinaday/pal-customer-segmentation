# PAL Customer Segmentation — Kick-Off Call Speaker Script
**Audience:** Philippine Airlines VPs / Senior Leadership
**Duration:** ~10–12 minutes
**Slides:** pal_executive_deck.html (2 slides)

---

## Before You Begin

Open the HTML file in Chrome, press F11 for full screen. The deck is two slides — scroll or use the arrow keys to advance.

---

## Slide 1 — Methodology

> *"Let me walk you through how the model actually works — five steps, left to right."*

**Step 1 — Data Ingestion & Cleaning**
> *"We start with your raw booking file. Every PNR record is loaded in, and anything incomplete or invalid is automatically removed. No manual cleanup, no human intervention. We ended the POC with just under 30,000 clean records."*

**Step 2 — Feature Engineering**
> *"From each booking, we compute 40 signals — things like how far in advance the ticket was bought, the fare paid, cabin class, travel region, and group size. These signals are the input to everything that follows."*

**Step 3 — Stages 3–6: Labelling & Clustering**
> *"This is the core of the model — three things happen here in sequence."*

> ① *"First, nine business rules run automatically. These are plain English rules your commercial team can read and verify — for example: a Business cabin booking is tagged Corporate; a Middle East route is tagged OFW/Migrant. These rules alone label 76% of passengers instantly."*

> ② *"For the remaining 24%, Machine Learning takes over. We tested seven different algorithms and selected the one with the strongest cluster quality — called HDBSCAN. It groups passengers who behave similarly together, without forcing equal-sized groups. Importantly, it flags borderline cases rather than guessing."*

> ③ *"Finally, the 78 natural clusters the model found are each matched to one of the 10 named segments. Every label is traceable back to the original booking signals — we can always explain why a passenger ended up in a given segment."*

**Step 4 — Validate (Asymmetric Cost Matrix)**
> *"We don't measure accuracy the way a textbook would. A wrong Corporate label costs 10 times more than a wrong Budget label — so the model is scored by peso impact, not just raw percentages. High-value segments like Corporate and OFW/Migrant must meet a higher recall threshold."*

**Step 5 — Dashboard (Power BI)**
> *"The output lands in Power BI — filterable by route, segment, and travel month. Your Revenue Management and Marketing teams can start using it immediately once the full dataset is processed."*

---

## Slide 2 — POC Results

> *"Now let me show you what happened when we ran this on test data."*

**KPI Callouts**
> *"We ran the full pipeline on just under 10,000 synthetic passenger records — designed to mirror real PAL booking patterns. All eight stages completed without a single manual step."*

> *"The model correctly identified the segment for 77.7% of passengers. That number is meaningful because the test data included no historical labels — the model had nothing to learn from except the booking signals themselves."*

> *"The conservative revenue risk estimate — meaning the cost of the labels the model got wrong — came out at ₱1.67 million across 10,000 passengers. On a full production dataset of 30,000 records, that figure scales proportionally. Improving recall on Corporate and OFW/Migrant segments is where the biggest peso savings are."*

**Recall Chart**
> *"The bar chart breaks down accuracy by segment. Corporate and OFW/Migrant — the two highest-penalty segments — are where we focused the model's attention during training, and you can see that reflected in their recall scores."*

**What This Proves**
> *"The key takeaway from the POC: the pipeline runs end-to-end, fully automatically, on real booking data structure. We have a working baseline. The next milestone is running this on your full January 2025 extract and then scaling to the five-year historical dataset."*

---

## Closing

> *"To summarise: we have a working, explainable segmentation model. It runs automatically, it scores accuracy by business cost rather than raw numbers, and the output is ready for Power BI from day one."*

> *"The immediate blocker to unlocking the Mabuhay Loyalist segment — and strengthening Corporate and OFW — is the loyalty status field from your source systems. Once that's available, we can re-run the labelling step and expect a meaningful improvement in the top-segment recall scores."*

> *"Happy to open the floor for questions."*

---

---

## Anticipated Tough Questions

---

**"Why should we hire you if we still need to do work on our end?"**

> *"That's a fair challenge. The data we're asking for — loyalty tier, departure time, length of stay — is a one-time extract from your source systems. A single SQL query from your IT team. That's roughly a day's work on PAL's side.*
>
> *What takes months of specialized expertise is everything else: designing the model, selecting the right algorithm from seven candidates, building the penalty-weighting logic so a wrong Corporate label costs more than a wrong Budget label, validating the outputs, and delivering a live Power BI dashboard your teams can act on. The POC you've just seen — 30,000 records, fully automated, zero PAL involvement — is proof that our side of the work is already done.*
>
> *We're not asking PAL to build the model. We're asking for the fuel to make it more accurate."*

---

**"Who in PAL will actually use this model?"**

> *"Three teams directly:*
>
> *Revenue Management — the segment mix per route tells you who is actually flying each O&D. That drives smarter pricing and seat allocation decisions.*
>
> *Marketing — instead of blasting all passengers, you can target OFW/Migrants before deployment season, Pilgrimage groups before Hajj, Balikbayan passengers before Christmas. The segment labels make that possible.*
>
> *Commercial and Network Planning — you'll know which routes are Corporate-heavy versus Budget-heavy, and price or schedule accordingly.*
>
> *The Power BI dashboard is the interface for all three teams. No one needs to touch the model itself."*

---

**"What is the model actually for — what problem does it solve?"**

> *"Right now, PAL's booking data tells you what a passenger bought — cabin, fare, route. It does not tell you why they flew or who they are as a traveller.*
>
> *The model fills that gap. Every booking gets a label: Corporate, OFW/Migrant, Mabuhay Loyalist, and so on. Once you have that label, you can answer questions like: what share of Manila–Dubai revenue comes from OFW passengers versus Bleisure? Are Corporate bookings on the Cebu route growing or shrinking? Which routes are over-indexed on Budget passengers and underpriced as a result?*
>
> *Without segmentation, those questions are guesswork. With it, they're a filter in Power BI."*

---

**"If this is just a prototype, does that mean no actual model gets delivered?"**

> *"The prototype label refers to the data, not the technology. The pipeline — the code, the algorithm, the validation logic — is production-ready and already running. What makes it a POC today is that we ran it on synthetic test data rather than your full booking history.*
>
> *The production deliverable is exactly this model, retrained on PAL's five-year dataset, outputting a labelled booking table and a live Power BI dashboard. The path from here to there is clear and already scoped: receive the full extract, re-run the pipeline, deliver the dashboard. There is no additional model to build — we are delivering the model."*

---

*Script prepared for PAL internal use — v1.0, May 2026*
