# SME business constraints

Two files, both CSV so they open in Excel with no tooling. **The rows currently in them are *our*
guesses, pre-filled as worked examples** — the point of the ask is for SMEs to correct, delete and
extend them. A rule we invented and an SME confirmed is worth far more than a rule we invented alone.

Business context and the plain-language version of this ask: `docs/stakeholder-report.md` §7.

## `hard_constraints.csv` — rules that must never be broken

Statements of impossibility. These shrink the decision space before anyone makes a judgement call:
instead of choosing among 10 segments, an annotator picks among 2 or 3.

| column | meaning |
|---|---|
| `rule_id` | `H01`, `H02`, … — stable id so a rule can be discussed and revised by name |
| `condition` | the situation, in field terms or near-plain language |
| `verdict` | `must_be` (definitively this segment) · `cannot_be` (rule out) · `narrow_to` (restrict to a shortlist) |
| `segments` | one canonical segment name, or several `\|`-separated for `narrow_to` |
| `owner` | which SME group asserted it (RM Domestic / RM International / Network Planning / FF Product Owner) |
| `confidence` | `certain` or `likely` |
| `notes` | free text — the *why*, which is the part that survives when the rule is revised |

Only `certain` rules are enforced automatically. `likely` rules are tested against the data first and
brought back to the owner if they contradict it.

## `soft_constraints.csv` — tendencies, not laws

A lean rather than a rule. "Middle East bookings *tend* to be OFW rather than leisure — but a
Manila–Dubai holiday is perfectly possible." These tilt ambiguous cases, and they tell us **which
boundaries PAL considers soft** — where we should report ambiguity instead of forcing a confident label.

| column | meaning |
|---|---|
| `rule_id` | `S01`, `S02`, … |
| `condition` | the situation |
| `leans_toward` | the more likely segment |
| `leans_away_from` | the segment it argues against |
| `strength` | `weak` · `moderate` · `strong` |
| `owner` | asserting SME group |
| `notes` | the reasoning |

Where a soft constraint contradicts what the data shows, **that disagreement is the finding** — it gets
reported back, not silently overridden in either direction.

## Field names available in `condition`

From `data/interim/pal_features_booking.parquet` (see `docs/data-dictionary.md`). Conditions may also be
written in prose — transcription is our job, not the SME's.

`lead_days` · `round_trip` · `is_domestic` · `is_international` · `dest_region` · `issue_country` ·
`foreign_issue` · `channel` · `corp_channel` · `sea_crew` · `max_tier` / `min_tier` (1–7 farebrand
ladder) · `any_premium` · `any_business` · `is_award` · `is_group` · `pilgrimage` · `connecting` ·
`n_coupons` · `dep_month` · `rev_pos` · `age` / `age_known` · `n_bookings` (customer grain)

Canonical segment names are in `src/pal_colors.py`.

## Related ask

`data/labels/` — the hand-labelled sample (`sme_sample.csv`) that turns our accuracy numbers from
"agrees with our own rules" into "agrees with reality". Constraints and labels are complementary:
constraints encode what SMEs know in general, labels settle the cases where the general rules run out.
