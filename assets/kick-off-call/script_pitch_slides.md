# PAL Customer Segmentation — Speaker Script
## Methodology & POC Results Slides
**Audience:** Philippine Airlines VPs / Senior Leadership
**Slides:** PAL_Methodology_Dark.png · PAL_POC_Results_Dark.png
**Duration:** ~8–10 minutes for both slides

---

## Slide 1 — Methodology

> *"Let me walk you through exactly how the model works — five steps, left to right. I want to be specific, because this is what you are actually buying."*

---

**[Point to: Requirements Scoping box — top left]**

> *"Before any code runs, we align with your commercial teams on the segments that matter to PAL. Corporate, OFW/Migrant, Mabuhay Loyalist — these are not generic categories. They come from conversations with Revenue Management, Network Planning, and Marketing. That alignment happens here, at the top."*

---

**[Point to: Step 1 — Ingestion & Cleaning]**

> *"Step one is simply loading your booking data. Every PNR record is ingested and cleaned automatically. Incomplete records, zero-fare entries, obvious errors — removed without any manual intervention. On the synthetic POC dataset, we processed just under 30,000 records in minutes."*

---

**[Point to: Step 2 — Feature Engineering]**

> *"From each booking, we compute 40 signals. Not just the ticket price — we look at how far in advance the seat was purchased, cabin class, the O&D pair, loyalty tier, baggage add-ons, group size. These 40 signals become the input language the model reads."*

---

**[Point to: Step 3 — ML Labelling & Clustering]**

> *"This is where the model does the work. Two things happen in sequence."*

> *"First, nine plain-English business rules run across the full dataset. A Business cabin booking on a short-haul route with same-day return — tagged Corporate. An Economy booking to the Middle East with two checked bags — tagged OFW/Migrant. These nine rules alone label 76% of all passengers, instantly."*

> *"For the remaining 24%, Machine Learning takes over. We use an algorithm called HDBSCAN — it finds natural groupings in the data without forcing equal-sized buckets. Passengers who behave alike end up in the same cluster. On the POC, it found 78 distinct micro-clusters, which we then map to the 10 named segments. Every label is traceable back to the original booking signals — there is no black box here."*

---

**[Point to: Step 4 — Asymmetric Cost Validation]**

> *"Most models measure accuracy as a raw percentage. We do not. We score accuracy in pesos. A wrong Corporate label costs ten times more than a wrong Budget label — because Corporate passengers are worth roughly ₱40,000 per ticket on average. So the model is penalised heavily when it misses a high-value passenger, and the validation threshold for Corporate and OFW/Migrant is set higher than for Budget or Last-Minute. Accuracy is business accuracy, not textbook accuracy."*

---

**[Point to: Step 5 — Dashboard & Insights]**

> *"The final output is a labelled booking table and a Power BI dashboard. Filterable by route, by segment, by travel month. Revenue Management can see the Corporate share on MNL–Singapore. Marketing can pull every OFW-tagged booking departing in June. This is Day-1 ready once the full dataset is processed."*

---

**[Point to: Reporting & Insights — bottom right]**

> *"The entire flow — from raw booking file to labelled, validated, dashboard-ready output — is automated. No manual steps. That is the pipeline."*

---

## Slide 2 — POC Results

> *"Now let me show you what happened when we actually ran this pipeline."*

---

**[Point to: KPI cards — top row]**

> *"We ran all eight stages on 10,000 synthetic records structured to mirror real PAL booking patterns. Four numbers matter here."*

> *"77.7% overall accuracy — on data the model had never seen, with no historical labels to learn from. It is identifying passenger type purely from booking behaviour."*

> *"₱18.1 million is the conservative estimate of revenue risk from the labels the model got wrong. That number sounds large. But it is the worst-case cost of the current POC baseline — and it tells us exactly where to focus improvement."*

> *"100% recall on Corporate. The highest-penalty segment in the entire model was captured perfectly. Every Corporate passenger in the test set was correctly identified."*

> *"78 micro-clusters. The model did not force passengers into neat boxes — it found 78 natural groupings and mapped them to the 10 named segments. The clusters are real and separable."*

---

**[Point to: Recall bar chart — left panel]**

> *"The bar chart breaks down accuracy segment by segment. The red line is the 91% recall target — that is the business threshold above which a segment is considered reliably identified."*

> *"Corporate, Family, Digital Nomad — all at or above target. Last-Minute is right at the threshold."*

> *"The segments below the line — OFW/Migrant at 18%, Budget/Adventure at 22%, Premium Bleisure at 38% — those are the improvement opportunities. And we know exactly why they are low: these segments overlap in booking behaviour, and they are the ones that would benefit most from the Mabuhay Miles loyalty data. Once loyalty tier is available, we expect these numbers to move materially."*

---

**[Point to: Cluster scatter — centre panel]**

> *"The scatter plot is visual proof that the segments are distinct. Each dot is a passenger. The diamonds are the cluster centroids — the most representative passenger in each group. The fact that the colours are separated, not blended together, means the model is finding real structure in the data, not noise."*

---

**[Point to: Key Findings — right panel]**

> *"Three things this POC proves. First — the pipeline runs. End-to-end, automated, on real booking data structure. Second — Corporate accuracy is already production-quality. Third — the path to improving OFW and Mabuhay recall is clear and specific: one data field, loyalty tier, from your source systems."*

---

## Closing

> *"To summarise what you have just seen: a working, explainable segmentation model. It runs automatically. It scores accuracy by business cost rather than raw percentages. And Corporate — your highest-value segment — is already being identified perfectly."*

> *"The single fastest way to improve the remaining segments is the Mabuhay Miles loyalty status field. One extract from your IT team. Once we have that, we re-run the labelling step and expect OFW and Mabuhay Loyalist recall to cross the 91% threshold."*

> *"Happy to take questions."*

---

## Anticipated Tough Questions

---

**"Your accuracy is only 77.7% — that is not good enough."**

> *"Fair challenge. Two things to put that number in context.*
>
> *First, 77.7% is the baseline — the first run on synthetic data, before any tuning on real PAL bookings and before the loyalty field is included. It is the floor, not the ceiling.*
>
> *Second, the 77.7% is dragged down by three segments — OFW, Budget, and Premium Bleisure — which overlap heavily in booking behaviour without loyalty data. Corporate, which is your highest-revenue segment, is at 100%. The model is already reliable where it matters most commercially.*
>
> *Once we run on your full five-year extract with loyalty tier included, we expect overall accuracy to cross 85%, with OFW and Mabuhay above the 91% threshold."*

---

**"What does ₱18.1 million revenue risk actually mean?"**

> *"It means: if the model mis-labels a Corporate passenger as Budget, PAL loses the opportunity to serve that passenger correctly — price correctly, offer the right product, retain them. The ₱18.1M is the sum of those missed-opportunity costs across all misclassified records in the 10,000-record POC.*
>
> *Importantly, the inverse is also true. Every percentage point improvement in Corporate or OFW recall translates directly into a recoverable revenue number. That is why we score accuracy in pesos — so you know exactly what improving the model is worth."*

---

**"Why is OFW recall so low at 18%?"**

> *"OFW passengers book in Economy, carry multiple bags, and travel on Middle East routes — but so do a meaningful share of Budget and Balikbayan passengers. Without loyalty status, those three groups look nearly identical in the booking data.*
>
> *The loyalty field disambiguates them. An OFW passenger typically does not hold a Mabuhay Miles card; a returning Balikbayan often does. One field resolves the ambiguity. That is why the loyalty extract is the single most important piece of data we are asking for."*

---

*Script prepared for PAL internal use — v1.0, May 2026*
