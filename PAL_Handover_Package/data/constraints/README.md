# SME business constraints

Two files, both CSV so they open in Excel with no tooling.

**Updated 17 August 2026.** The first filled-in workbook came back from **RM Domestic**
(`wishlist/PALxMAIDA_Constraints&Wishlist.xlsx` — 39 new rules). Those rules are now transcribed here,
so these files are no longer only our guesses: **15 hard + 42 soft rules**, each tagged with where it
came from and whether it can actually be used. Full intake analysis, including the five decisions still
blocking enforcement: `docs/sme-constraints-intake.md`.

Business context and the plain-language version of the ask: `docs/stakeholder-report.md` §7.

## ⚠️ Nothing here is wired into the pipeline yet

No code reads these files. They are (a) the artifact we hand back to an SME to confirm we understood
them, and (b) the eventual input to the labelling stage. **Enforcing them is a separate, deliberate
step** — because the moment a rule consumes a field, that field can no longer validate the rule
(`src/validation_anchors.py`). Two of the new rules would spend the last of our validation anchors;
that trade-off is the subject of `docs/sme-constraints-intake.md` §6.

## Validate before committing an edit

```bash
python src/check_constraints.py     # 0 errors expected
```

It checks every row against `data/interim/pal_features_booking.parquet`: that the `condition` names
real columns, that DuckDB can evaluate it, that the recorded `fires` count still matches the live
count, and that `status` is consistent with the volume. **A rule that silently stopped matching
anything is worse than a missing rule — it reads as covered.** The check caught exactly that during
transcription (a stale count, a mis-parsed condition, and a rule 2.3× larger than recorded).

⚠️ **If you edit by hand, mind the commas.** Several conditions contain them (`dep_month IN (4,5,12)`,
`turn_dest IN ('DXB','RUH')`) and so do many notes. Excel quotes correctly on save; a plain text editor
will not, and an unquoted comma silently shifts every later column. The checker catches it.

## `hard_constraints.csv` — rules that must never be broken

Statements of impossibility. These shrink the decision space before anyone makes a judgement call:
instead of choosing among 10 segments, an annotator picks among 2 or 3.

| column | meaning |
|---|---|
| `rule_id` | `H01`, `H02`, … — stable id so a rule can be discussed and revised by name |
| `condition` | the situation, in the field names listed below |
| `verdict` | `must_be` (definitively this segment) · `cannot_be` (rule out) · `narrow_to` (restrict to a shortlist) |
| `segments` | one canonical segment name, or several `\|`-separated for `narrow_to` |
| `owner` | which SME group asserted it (RM Domestic / RM International / Network Planning / FF Product Owner) |
| `confidence` | `certain` · `likely` — the only two levels a hard verdict may carry |
| `status` | see the table below |
| `scope` | the sub-population the rule can even be evaluated on |
| `fires` | bookings matching the condition, out of 22,911,450 — **kept live by the checker** |
| `sme_row` | row number in the source workbook, for traceability |
| `notes` | free text — the *why*, which is the part that survives when the rule is revised |

## `soft_constraints.csv` — tendencies, not laws

A lean rather than a rule. "Middle East bookings *tend* to be OFW rather than leisure — but a
Manila–Dubai holiday is perfectly possible." These tilt ambiguous cases, and they tell us **which
boundaries PAL considers soft** — where we should report ambiguity instead of forcing a confident label.

Same columns, except `verdict`/`segments`/`confidence` are replaced by `leans_toward`,
`leans_away_from` and `strength` (`weak` · `moderate` · `strong`).

Where a soft constraint contradicts what the data shows, **that disagreement is the finding** — it gets
reported back, not silently overridden in either direction.

## `status` — can we actually use this rule?

**Updated 17 August 2026** — PAL settled four of the five blocking decisions, so `query` is now empty.

| status | meaning | hard | soft |
|---|---|---|---|
| `enforce` | `certain`, evaluable, fires on real volume — ready to auto-enforce | 6 | — |
| `prior` | soft tilt, usable now | — | 19 |
| `confirmed` | our seeded guess, and the SME agreed | 4 | 2 |
| `unconfirmed` | our seeded guess; the SME did not respond either way | 3 | 4 |
| `withdrawn` | deliberately set aside — kept for the audit trail, never enforced | — | 5 |
| `too_thin` | evaluable, but fires on under ~11k bookings (0.05%) — not worth acting on | 1 | 6 |
| `demoted` / `demoted_from_hard` | a `cannot_be` at only `moderate` confidence, moved to soft | — | 2 |
| `partial` | transcribed with part of the condition dropped as unevaluable | — | 1 |
| `contested` | several segments claim the same predicate | — | 1 |
| `blocked` | not evaluable at all — a field we do not have | 1 | — |
| `unanswered` | placeholder; the SME ask came back empty | — | 2 |
| `test` | `likely` — check against the data, return to the owner if contradicted | 0 | — |

Only `enforce` rules would be applied automatically. `test` rules are checked against the data first
and brought back to the owner if the data contradicts them.

### The five rules marked `withdrawn`, and why

**`dep_month` is retained as a validation anchor** (decision 1), which means **no active rule may read
it** — the checker enforces this, not just the convention. S02, S10, S12, S16 and S20 all turned on
departure month as their *primary* claim (peak season, the Q4–Q1 Balikbayan peak, the summer spike to
Asian hubs, Lent/Easter, off-peak long stays), so nothing survives removing the clause. They are kept
rather than deleted so RM Domestic can see exactly what we set aside and why.

**S38 was rewritten rather than withdrawn.** Its academic-month clause was a refinement on top of a
90–150 night stay, which stands alone — so the months were dropped and the rule survives. It fires
wider as a result (17,354 → 51,223) and is flagged to the SME as a modified transcription.

## Three things to know before reading the conditions

1. **Route direction is not obvious, and the workbook got it backwards.** The SME wrote OFW routes as
   `TripOD IN ('MNLDXB', …)`, but **Gulf round trips start in the Gulf 260,216 times against Manila's
   26,195** — a worker based in Riyadh flying home is `RUHMNL`. Read literally, their best rule matched
   5,166 bookings instead of 118,841. Rules here therefore use `turn_dest` (outbound airport) where the
   direction is deliberate, and `route_theme` where it is not.
2. **`stay_nights` is NULL on one-ways by definition** — there is no stay to measure. 26 of the 39 new
   rules cite it, so they are structurally silent on the 57% of the book that is not a round trip.
3. **`age` is populated on only 0.98% of domestic bookings.** It is an international-only field, so
   every age rule is dead for domestic travel — which is what the ask was for.

## Field names available in `condition`

From `data/interim/pal_features_booking.parquet` (see `docs/data-dictionary.md`). Conditions may also be
written in prose — transcription is our job, not the SME's.

`lead_days` · `round_trip` · `is_domestic` · `is_international` · `dest_region` · `issue_country` ·
`foreign_issue` · `channel` · `corp_channel` · `sea_crew` · `max_tier` / `min_tier` (1–7 farebrand
ladder: 1 Supersaver · 2 Saver · 3 Value · 4 Economy Flex · 5 Premium Economy · 6 Business Value ·
7 Business Flex) · `any_premium` (cabin J or W) · `any_cabin_j` (cabin J only) · `any_business`
(business *fare*, tier ≥ 6) · `is_award` · `is_group` · `pilgrimage` · `connecting` · `n_coupons` ·
`dep_month` · `rev_pos` · `age` / `age_known`

**Added 17 Aug 2026** (`docs/methodology.md` v1.7): `stay_nights` · `dep_dow` (0 = Sunday … 6 = Saturday) ·
`turn_dest` (outbound destination airport) · `route_theme` (one of `gulf_labour`, `east_asia_hub`,
`asian_tourist_hub`, `islamic_pilgrimage`, `catholic_pilgrimage`, `domestic_leisure`, `premium_holiday`,
`diaspora_north_america` — see `data/reference/route_theme.csv`).

`n_bookings` is on the **customer** rollup, not the booking table; the checker joins for it.

Canonical segment names are in `src/pal_colors.py`. **Resolved 17 August 2026:**

- the SME's **"Leisure"** is our existing **`Budget/Adventure`** — a naming difference, not a new segment
- **`MICE`**, **`Ultra Wealthy Leisure`** and **`Intl. Student`** are **approved as real segments**,
  taking the taxonomy from 10 to 13. They are in `SEG_APPROVED`, *not* in `SEG_ORDER` — the waterfall
  does not emit them yet, so no chart should list them.
- **`Last-Minute (flag)`** is written that way because Last-Minute is no longer a peer segment. It
  describes a booking, not a kind of traveller: 84.1% of it would otherwise be `Budget/Adventure`.

## Related ask

`data/labels/` — the hand-labelled sample (`sme_sample.csv`) that turns our accuracy numbers from
"agrees with our own rules" into "agrees with reality". Constraints and labels are complementary:
constraints encode what SMEs know in general, labels settle the cases where the general rules run out.
