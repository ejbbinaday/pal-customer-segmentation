# SME ground-truth labels

Drop a file named **`sme_sample.csv`** here to enable **non-circular** validation. Until it lands, every
accuracy number the project reports is measured against the rule waterfall's own output — i.e. we are
grading our own homework. This file is the answer key.

Business context and the full ask: `docs/stakeholder-report.md` §7.3.

## Format (see `sme_sample_TEMPLATE.csv`)

| column | meaning |
|---|---|
| `customer_id` | the anonymised customer key (`UniqueID` in the extract) |
| `issue_date` | date of issuance — **together with `customer_id` this is the booking key** |
| `true_segment` | the SME-assigned segment: one of the 10 canonical names in `src/pal_colors.py`, or `Unsure` |
| `confidence` | `High` · `Med` · `Low` |
| `notes` | free text — why, especially for the hard calls |

The grain is the **booking** (one purchase decision), matching
`data/interim/pal_features_booking.parquet`. There is no PNR id in the extract, so
`(customer_id, issue_date)` is the join key.

## Four things that matter more than volume

- **`Unsure` is a first-class answer.** Forcing a guess manufactures noise we then cannot detect. A
  genuinely ambiguous booking is a useful signal about where our boundaries are wrong.
- **Spread across segments beats a random draw.** A uniform random 1,000 rows yields ~2 Pilgrimage and
  ~0 Mabuhay Loyalist. Over-sample the rare, high-penalty segments (Corporate ×10, OFW/Migrant ×5)
  deliberately — that is where a labelling error costs the most.
- **Have ~100 rows labelled by every SME.** Where SMEs disagree with each other, that disagreement rate
  is a hard ceiling on any accuracy the model could ever claim. It has to be measured, not assumed.
- **Even 100–200 rows help.** They replace a circular metric with a defensible one.

## What happens when it lands

The scorer reports per-segment recall, the asymmetric cost matrix (Corporate ×10 / OFW ×5 — see
`docs/methodology.md` Stage 7), the proxy-vs-SME confusion matrix, weighted prevalence estimates, and
inter-rater agreement. It is written before the data arrives on purpose, so there is no lag between the
labels landing and the answer.

Complementary ask: `data/constraints/` — hard and soft business constraints. Constraints encode what
SMEs know in general; labels settle the cases where the general rules run out.
