# Mentor Presentation Guide — Initial Findings & Next Steps

**Audience:** capstone mentor (technical, will probe method) · **Target:** 15 min talk + 10 min Q&A
**One-line thesis:** *We proved the customer base is a continuum, not clusters — so we made business
rules the labeler and ML the refinement layer. That pivot is the finding.*

**Have open before you start:** `docs/status-report.pdf` (your slide deck — figures are already in it),
plus `outputs/features_real/summary.md` and `outputs/kproto_compare/summary.md` in a second window for
Q&A drill-downs.

---

## TL;DR

- **Data:** real PAL extract, 38.1M coupons (2024–2027) → 22.9M bookings → 13.4M customers, all running
  through a reproducible DuckDB/Parquet pipeline.
- **Central finding:** PAL's customers are a **continuum**, not discrete clusters. No natural *k* — LCA
  BIC is monotone 3→9, silhouette is flat, and three model families disagree with each other.
- **The pivot:** we inverted the design. **Business rules label; ML (LCA) refines and validates.**
  HDBSCAN dropped, with evidence.
- **Result:** 10 segments live at booking grain, plus LCA sub-types inside the oversized ones. Premium
  Bleisure is 2.1% of bookings at **$1,504** avg revenue vs Budget/Adventure's **$74** — that spread is
  the commercial case.
- **Honest limit:** validation is still circular (proxy labels test our own rules). SME ground truth is
  the #1 blocker.

**The 30-second spoken version**, if they say "just summarize it":

> "We got the real 38-million-row extract and built the pipeline end to end. The big finding is negative
> and it reshaped the project: there is no natural number of clusters in this data — customers are a
> smooth continuum, which we confirmed across three model families. So instead of letting the algorithm
> name the segments, we let business rules name them and use LCA to check the axes and split the
> oversized groups. Ten segments are live at booking grain and already exported to Power BI. The one
> thing we can't yet claim is accuracy — our validation is circular until we get hand-labelled bookings
> from a PAL expert, and that's our main ask."

---

## The one analogy to lead with

If your mentor remembers one thing, make it this. Use it at beat 4, then reuse the vocabulary all session.

> **"Our customers are a rainbow, not a box of crayons."**
>
> "We started out assuming the market was a box of crayons — ten distinct colors, and the algorithm's
> job was to find them. What the data actually shows is a rainbow: red really does blend into orange,
> and there's no line in the spectrum where one stops. That's what 'no elbow in the BIC' means.
>
> But a rainbow still has real structure — the spectrum runs in a *direction*. So we stopped asking the
> algorithm to find the crayons, and instead drew the color boundaries ourselves with business rules —
> then used clustering to confirm we'd drawn them **across** the spectrum rather than along it. The
> clusters split on exactly our rule axes, which is the confirmation. Naming 'orange' is a business
> decision. Proving the spectrum runs red-to-violet is the analysis."

Why this lands: it makes the negative result feel like *insight* rather than *failure*, and it gives the
mentor a frame for why rule-based labeling isn't a retreat from ML.

---

## The 6-beat story arc

Each beat = one slide, one message, one number. Don't exceed one number per beat when speaking.

| # | Beat | The one message | Say this number | Show |
|---|---|---|---|---|
| 1 | **Setup** | Anonymous booking data → trip-purpose × value segments for PAL | 38M coupons, 2024–2027 | title + taxonomy |
| 2 | **Pipeline** | Built and running end-to-end on real data | 38.1M → 22.9M bookings → 13.4M customers | pipeline diagram |
| 3 | **What the data says** | Value doesn't discriminate; route + timing do | 71% of bookings are cheap economy | `eda_01`, `eda_02` |
| 4 | **⭐ The pivot** | No natural number of clusters — it's a continuum | BIC monotone 3→9, no elbow; ARI 0.20–0.34 | `clust_01_bic_ari` |
| 5 | **Results** | 10 segments live at booking grain + LCA sub-types | Premium Bleisure $1,504 avg rev vs Budget $74 | segment table, `sub_01` |
| 6 | **Next steps** | One blocker: SME ground truth | 0 hand-labelled bookings today | next-steps slide |

**Spend your time like this:** beats 1–3 in 5 min, **beat 4 in 4 min** (this is the intellectual core —
slow down here), beat 5 in 4 min, beat 6 in 2 min.

---

## Beat-by-beat talk track

### 1. Setup (45 sec)
> "PAL gave us anonymous booking data — no names, no stated trip purpose. The goal is to infer *why*
> someone is flying and *what they're worth*, then hand PAL an actionable segmentation. Ten named
> segments: Corporate, OFW/Migrant, Balikbayan/VFR, Budget/Adventure, Last-Minute, Family, Premium
> Bleisure, Pilgrimage, Mabuhay Loyalist, Digital Nomad."

### 2. Pipeline (1.5 min)
> "38 million coupon rows is too big for pandas, so the pipeline runs on DuckDB + Parquet. We roll up
> **coupon → booking → customer**, where a booking is (customer, issue date) — that's the unit that
> captures a purpose, because 43% of bookings are round-trips that would otherwise get split. Cleaning,
> EDA, feature engineering, and BI export are all reproducible scripts."

### 3. What the data says (2.5 min)
Three EDA facts that *forced* design decisions — present them as consequences, not trivia:

- **57.7% domestic** → the domestic/international split, not fare, is the primary purpose axis.
- **71% of bookings are Economy Saver/Supersaver** → value is nearly non-discriminative, so we had to
  build an airport→region lookup to separate domestic-budget from international-OFW/diaspora.
- **Median lead time 25 days; 13.3% booked within 3 days** → timing is a strong, direct signal
  (Last-Minute is the one segment the data hands us for free).

> **Analogy for "value is non-discriminative":** "Asking *what fare did they pay* is like trying to tell
> people apart in a room where everyone's wearing jeans. 71% bought the cheapest economy fare, so that
> question sorts almost nobody. We had to ask a different one — *where are they going, and how far
> ahead did they book* — which is why building the airport→region lookup became essential rather than
> optional."

### 4. ⭐ The pivot — the part your mentor actually cares about (4 min)

Present it as a hypothesis that was tested and rejected, then acted on. Three lines of evidence:

1. **The original plan was HDBSCAN → 10 segments**, and the real data killed it: on 38M coupons the
   categorical-heavy feature space is not density-separable, so there is no density structure to find.
2. **Mixed-type methods, same answer.** LCA on a 60k stratified booking sample: BIC falls
   monotonically 3→9 (1.016M → 932k) and picks the boundary — **no elbow means no natural k**.
   Agreement with the business taxonomy is only moderate: **ARI 0.20–0.34**.
3. **Confirmed by a second model family.** k-prototypes vs k-modes vs LCA, k = 3–12: LCA wins as the
   refinement layer (ARI **0.336**, Gower silhouette **0.30** vs 0.09/0.15), and none of them find an
   elbow. Pairwise agreement between methods is only 0.12–0.43.

**If they stop you on a metric, define it in one breath** (full glossary below):

- **DBCV** — "does this data actually have dense clumps?" Negative = no. Ours was negative everywhere.
- **Silhouette** — "how cleanly separated are the groups?" ~1 tight, ~0 no separation. Ours: 0.10.
- **BIC** — model-fit score where lower is better; we use it to *choose k*. It never bottomed out.
- **Elbow** — the point where adding another cluster stops helping. **No elbow = no natural k.**
- **ARI** — how much two labelings agree, 1 = identical, 0 = random. Ours vs the rules: 0.20–0.34.

Then the punchline — say this almost verbatim:

> "So the honest reading is that PAL's customers are a **smooth continuum** along route, direction,
> timing and value — not discrete islands. Unsupervised clustering can't be the labeler, because it
> just re-slices the axes we already know. But the emergent clusters *do* fall along exactly those
> axes, which **validates the rules**. So we inverted the design: **rule-based purpose × value
> segmentation is primary, and LCA becomes the refinement and validation layer.**"

**The trap to sidestep, unprompted:** one sentence, delivered before they ask —
> "One caveat we enforce on ourselves: our validation is still *circular*. Recall against proxy labels
> only measures the model re-learning our own if/else rules, so we don't report it as accuracy.
> It's grading your own exam with your own answer key — you'll always score well, and it proves nothing."

That single sentence buys you more credibility than any metric on the slide.

### 5. Results (4 min)

Booking-grain segment mix (from `outputs/features_real/summary.md`) — read only the bolded rows aloud:

| Segment | % bookings | Avg rev |
|---|---|---|
| **Budget/Adventure** | **39.4%** | **$74** |
| OFW/Migrant | 17.1% | $312 |
| Last-Minute | 12.9% | $137 |
| **Balikbayan/VFR** | **12.7%** | **$618** |
| Unassigned | 9.6% | $360 |
| Corporate | 4.4% | $493 |
| **Premium Bleisure** | **2.1%** | **$1,504** |
| Family / Pilgrimage / Mabuhay | 1.8% combined | — |

> "The commercial story is the spread: Premium Bleisure is 2% of bookings at 20× the revenue per
> booking of Budget/Adventure. That asymmetry is what makes segmentation worth doing — it's the
> restaurant where one tasting-menu table brings in what twenty walk-ins do. You'd want to know which
> table is which *before* you decide who gets the attention."

Then ML's actual contribution:
> "LCA earns its place by sub-segmenting the oversized rule segments. Budget/Adventure splits into 4
> interpretable sub-types along direction × lead × value — one-way advance supersaver at $23, versus
> round-trip advance saver at $87, which is the largest at 38%. OFW and Balikbayan split 4 ways,
> Last-Minute 3. We deliberately capped sub-types at 4 because BIC is monotone here too — the continuum
> goes all the way down, so the cut is a business-actionability choice, not a natural k. It's like
> zooming a map: you *can* keep zooming forever, so you stop at the level you can actually act on —
> streets, not floorboards. Four sub-types is a campaign you can run; forty isn't."

Close the beat on delivery:
> "It's already shipped as a Power BI star schema — 38.1 million rows in, 38.1 million out, 99.95%
> segment match, with the remainder labelled `Excluded (non-revenue)` so BI totals still tie."

### 6. Next steps + your asks (2 min)

Lead with the blocker, and be explicit that you're asking for something.

1. **SME ground truth — the #1 blocker.** A few hundred hand-labelled bookings converts every metric
   we have from circular to real. *Ask the mentor: how do we get PAL SME time for this?*
2. **Reconcile the taxonomy with PAL.** Digital Nomad has no anonymous signal, Pilgrimage is 0.19%,
   Mabuhay Loyalist is 0.03% (award tickets only started coding in Apr 2026), and there's no
   outbound-leisure segment. Some of these ten may need to be merged or dropped.
3. **Harden the provisional bits.** Balikbayan/VFR sub-types are the least reproducible (split-half
   ARI 0.495) — treat as provisional and re-fit.
4. **Build the dashboard on the exported star schema** and add drift monitoring (PSI/ARI) for handoff.
5. *Ask: what does this mentor want to see at the final defense — model rigor, or business impact?*
   Their answer changes where you spend the remaining weeks. Get it on the record now.

---

## Anticipated questions — short answers ready

| They ask | You answer |
|---|---|
| "Why not just use k-means with k=10?" | "We can force k=10, but there's no evidence for it: silhouette is flat ~0.10 with no peak, BIC is monotone, and three model families disagree with each other (pairwise ARI 0.12–0.43). Forcing k would be reporting an artifact of the algorithm as a finding about customers." |
| "If it's rule-based, where's the machine learning?" | "ML is the editor here, not the author. Three concrete jobs: LCA validated that the rule axes are the real axes of variation, LCA found the sub-types inside the oversized segments, and clustering gives us drift monitoring in production. Plus the negative result itself — ruling out density clustering with evidence — is the methodological contribution." |
| "ARI is only 0.2–0.34. Doesn't that mean your rules are wrong?" | "It means the partitions differ, not that the axes differ. The emergent clusters split on exactly route/direction/timing/value — they mostly sub-divide our biggest segment and cleanly separate international round-trip at $724 from international one-way at $260, which is the Balikbayan/OFW distinction. Low ARI here is what a continuum looks like, not a contradiction." |
| "You sampled 20k–60k out of 38M. Is that valid?" | "LCA and k-prototypes are compute-bound, so we use stratified samples and check reproducibility with split-half ARI — 0.86–0.99 for the configs we rely on. The rule-based labeling itself runs on all 22.9M bookings, no sampling." |
| "How accurate is the segmentation?" | "We can't claim accuracy yet, and won't. Validation is proxy-referenced and therefore circular. That's exactly why SME labels are the top ask." |
| "Why booking grain and not customer or PNR?" | "Trip purpose is a property of a trip, not a person — people wear different hats. The same customer flies OFW one month and Balikbayan the next, the way the same person drives to work on Monday and to the beach on Saturday. You label the journey, not the driver. So we label bookings, then roll up a dominant-segment view per customer for CRM." |
| "Can you segment 38M rows in production?" | "Already do — the whole pipeline is DuckDB/Parquet, cleaning streams in ~21 seconds, and the BI export takes ~2 minutes." |

---

## Term explainers

Know these cold — not to recite, but so you're never caught defining your own metric. The third column
is what matters live: the number is only useful if you can say what it *means for PAL*.

### Validation metrics (the ones on your slides)

| Term | In one line | What our number says |
|---|---|---|
| **DBCV** *(Density-Based Clustering Validation)* | Scores whether density-based clusters are real. Range −1 to 1; **negative = worse than no clustering**. | **−0.04 to −0.19** on v3 → no density clumps exist. This is what killed HDBSCAN. |
| **Silhouette** | Per-point: how much closer am I to my own group than the next one? ~1 = tight and separated, ~0 = no separation. | **Flat ~0.10** across k=4–12 with no peak → groups barely separated, and no k is better than another. |
| **BIC** *(Bayesian Information Criterion)* | Model fit penalized for complexity — lower is better. Standard way to **pick the number of classes**. | Falls **monotonically 3→9** and picks the boundary → the data always wants "one more cluster," i.e. a continuum. |
| **Elbow** | The k where the fit curve bends and extra clusters stop paying off. The classic "how many clusters?" test. | **No elbow, in any method.** The single most important negative result in the project. |
| **ARI** *(Adjusted Rand Index)* | Agreement between two labelings, corrected for chance. 1 = identical, 0 = random. | **0.20–0.34** vs the rule segments → same axes, different cut lines. Not "the rules are wrong." |
| **Gower distance / Gower silhouette** | A distance that handles **mixed data** (numbers + categories) in one metric, which Euclidean can't. Silhouette computed under it. | **0.30 for LCA** vs 0.09–0.15 → LCA separates mixed-type bookings best. Why LCA is the refinement layer. |
| **Split-half ARI** | Fit on half the data, predict the other half, compare to fitting on that half. Measures **reproducibility**. | LCA 0.67–0.86; k-prototypes 0.97 but with the *worst* separation — stable ≠ meaningful. Balikbayan sub-types 0.495 → provisional. |
| **Precision / recall** | Of what I labelled X, how much was right (precision); of all true X, how much did I catch (recall). | Ours is **circular** — measured against our own rules. Do not present as accuracy. |
| **PSI** *(Population Stability Index)* | Measures whether a distribution has shifted vs a baseline — the standard **drift** alarm. | Not a finding yet; it's the production monitoring we'd add at handoff. |

### Methods

| Term | In one line | Why it's in our story |
|---|---|---|
| **Unsupervised learning** | Finding structure with **no labels to learn from** — nobody told us who's an OFW. | The whole problem. It's also why validation is so hard: there's no answer key. |
| **HDBSCAN** | Density clustering — finds dense regions, calls the sparse gaps "noise." No k needed. | The **original plan of record**, dropped with evidence. Needs dense blobs; our data is categorical-heavy and diffuse. |
| **LCA** *(Latent Class Analysis)* | A **probabilistic** model: assumes hidden classes generate the observed pattern, gives each booking a probability of membership. Handles categorical data natively. | The winner as the **refinement layer** — best mixed-type separation, and it's what finds the sub-types. |
| **k-means / k-modes / k-prototypes** | Hard-assignment clustering: means for numbers, modes for categories, **prototypes for both**. You must pick k upfront. | Run as an independent cross-check. Same verdict, second model family — that's what makes the continuum finding credible. |
| **PCA** *(Principal Component Analysis)* | Compresses many correlated features into a few axes carrying the most variance. Used to visualize high-dimensional data in 2D. | The scatter on `clust_02_pca.png`. On v3, PC1 held only ~11% of variance = diffuse cloud, no dominant axis. |
| **Stratified sample** | A sample that preserves the proportions of each group, so small segments don't vanish. | How we run 20k–60k samples for the compute-heavy models. The rule labeling itself uses all 22.9M. |
| **Bootstrap** | Resample the data repeatedly to see how stable a result is. | KMeans and k-prototypes scored highest on stability with nearly the *least* separation — so **stability ≠ validity**. A stable partition of a structureless cloud is still meaningless. |

### Our pipeline vocabulary

| Term | In one line |
|---|---|
| **Coupon → booking → customer (grain)** | "Grain" = what one row means. One coupon = one flight leg; a **booking** = (customer, issue date), which is the unit that carries a trip purpose; **customer** = lifetime rollup. 38.1M → 22.9M → 13.4M. |
| **Proxy label** | A best-guess label generated by business rules because no true label exists. Our 10 segments are proxies today — real, usable, but unverified. |
| **Circular validation** | Testing a model against labels derived from the same rules and features it learned from. Guarantees a good score, proves nothing. |
| **Ground truth** | Labels a human expert assigns. We have **none** — the #1 ask. |
| **Feature engineering** | Turning raw fields into signals a model can use — lead time, round-trip flag, region, value tier. |
| **Waterfall (labeling)** | Prioritized if/else rules applied in order; first match wins. How a booking gets exactly one segment. |
| **Unassigned bucket** | Bookings no rule confidently claims (9.6%). Deliberate — better an honest "don't know" than a forced label. |
| **Star schema / fact table** | BI layout: one big table of events (`fact_flight`) + small lookup tables (`dim_date`). What Power BI expects. |
| **Continuum** | Values blend smoothly with no natural break points — as opposed to discrete, separable groups. **Our central finding.** |

> **The one sentence tying it together, if a mentor asks you to justify the whole design:**
> "We have no labels and no natural clusters, so the only honest options were to invent labels with
> rules or to force a k the data doesn't support. We chose rules — and used the clustering to prove the
> rules point in the right direction."

---

## Analogy cheat sheet

One line each — enough to recall the full version mid-sentence. Don't use more than three in the talk;
save the rest for Q&A. Stacked analogies start to sound like you're avoiding the numbers.

| Concept | Analogy |
|---|---|
| **Continuum, not clusters** ⭐ | Rainbow, not a box of crayons — no line where red stops |
| Circular validation | Grading your own exam with your own answer key |
| Rules label, ML refines | ML is the **editor**, not the author |
| Value doesn't discriminate | Telling people apart in a room where everyone's wearing jeans |
| Revenue asymmetry | One tasting-menu table = twenty walk-ins |
| Sub-type cap of 4 | Zooming a map: stop at streets, not floorboards |
| Booking grain, not customer | People wear hats — label the journey, not the driver |

---

## Delivery notes

**Do:**
- Lead the pivot with the *evidence*, then the *decision*. Mentors reward a rejected hypothesis with
  receipts far more than a clean-looking result.
- Flag the circularity yourself before they find it.
- Use one number per point. You have far more numbers than the room can absorb.
- End on the two asks (SME access, defense priorities) so they have something concrete to respond to.

**Don't:**
- Don't call the 53–100% proxy recall "model accuracy." It isn't, and it's the one claim that can
  unravel the whole session.
- Don't stack analogies. Three in the talk, max — the rainbow at beat 4, jeans at beat 3, restaurant at
  beat 5. Past that, they read as a substitute for evidence instead of a way into it.
- Don't defend HDBSCAN. You dropped it with evidence; that's a strength, so say so plainly and move on.
- Don't read tables aloud. Point at the shape, speak the contrast.

**If you only get 5 minutes:** beats 4, 5, 6 — the continuum finding, the segment mix with the
$1,504-vs-$74 spread, and the SME ask. Skip pipeline and EDA entirely.

---

*Sources: `docs/status-report.pdf`, `docs/methodology.md` (§at-a-glance),
`docs/knowledge-base.md` §15 (2026-07-23, 2026-07-27), `outputs/{features_real,cluster_diagnostic,kproto_compare,sub_segments}/summary.md`.*

*Last updated: 31 July 2026*
