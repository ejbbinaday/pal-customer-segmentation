# Sub-segment scoring — plan to put level 2 in the Power BI model

**Status: ✅ built, 21 August 2026.** Scoped and shipped the same day. §7 records what the plan got
wrong. Levels 1 and 2 both ship in `outputs/powerbi_export/`; the deck and `outputs/sub_segments/summary.md`
were deliberately left untouched.

`outputs/sub_segments/summary.md` characterises 5 parents × 4 LCA sub-types = **20 cells**, fitted on
40,000-booking samples. The Power BI export carries **only** `CustomerSegment`. Nothing in
`outputs/powerbi_export/**` has a row-level sub-type, and `src/export_powerbi.py` never mentions one.
`docs/manuscript/manuscript-ch4-draft.md` (§4.2, the sub-type paragraph) stated the gap plainly at the time: *"row-level
sub-segment assignment is future work (a scoring pass or rule re-expression)."* This is that scoping.

---

## 1. The realisation that makes this cheap: score cells, not rows

`sub_segment.py`'s `code()` reduces every booking to a fully discrete vector — `lead_bucket` (5 buckets),
`value_tier` (integer), `n_coupons_b` (4), `dest_region` (≤8), and four binaries. So the model's input
domain is small and enumerable. Measured over the whole booking table:

| Parent | Bookings | Distinct feature cells | Tier levels |
|:--|--:|--:|--:|
| Leisure | 11,595,711 | 1,281 | 7 |
| OFW/Migrant | 3,907,805 | 5,796 | 7 |
| Balikbayan/VFR | 2,871,255 | 1,175 | 4 |
| Outbound International Leisure | 2,182,074 | 2,857 | 7 |
| Corporate | 1,168,451 | 6,738 | 7 |
| **Total** | **21,725,296** | **17,847** | — |

**17,847 cells cover all 21.7M bookings in the five parents** (94.8% of the 22,911,450-booking table).

So there is no 21.7M-row scoring pass to write. Fit, then `predict` on at most 6,738 rows per parent,
emit one lookup table (cell → sub-type), and join it back in SQL. The entire level-2 model becomes a CSV
a human can read end to end — which is the right property for a layer that will be defended in a room.

## 2. And it lets us drop the 40k sample entirely

StepMix 3.0.0's `fit` accepts sample weights — `(self, X, Y=None, sample_weight=None, y=None)`. Fitting
the cell table weighted by cell counts **is** fitting all 21.7M bookings, exactly, not approximately.
Verified empirically rather than assumed: `score(cells, sample_weight=counts)` returns the identical
average log-likelihood as `score(rows_replicated_by_count)` to machine precision.

That retires the `SAMPLE = 40_000` caveat and, with it, the reservoir-sampling scar the script still
carries a warning about.

> ⚠️ **`m.bic(X)` becomes silently wrong on a weighted cell table.** Its source is
> `-2 * self.score(X, Y) * X.shape[0] + self.n_parameters * np.log(X.shape[0])` — an *unweighted* score
> and *N = number of cells*. On the cell table that is N = 17,847 instead of 21.7M, against the wrong
> likelihood, with no error raised. Compute it by hand:
>
> ```python
> W = w.sum()
> bic = -2 * m.score(cells, sample_weight=w) * W + m.n_parameters * np.log(W)
> ```
>
> `K_RANGE` selection depends on this, so getting it wrong changes which k ships.

## 3. Five blockers to fix before any assignment is trustworthy

**3.1 `dest_region` encoding is sample-dependent — and already broken.**
`code()` does `df["dest_region"].astype("category").cat.codes`, which numbers categories by whatever
appeared *in the sample*. Measured: OFW/Migrant's 40k sample sees **6** regions; its population has
**7**. So the codes shift on any refit, and the missing level cannot be encoded at scoring time at all.
Fix: freeze an explicit region → code map over the population domain (8 values, including the long tail
— Europe n=1, South Asia n=103) and persist it with the model.

**3.2 The `value_tier` median-fill is sample-derived.** `fillna(median)` — sample medians are 2.0 for
four parents and **4.0 for Corporate**. Population nulls: Outbound 12,426 · Leisure 11,647 · OFW 1,411 ·
Corporate 1,014 · Balikbayan 0. Persist the fill value; never recompute it per run.

**3.3 The dropped-constant-column list is part of the model.** `code()` drops within-parent constant
columns. Sample and population agree today — Balikbayan drops `round_trip` + `foreign_issue`, Outbound
drops `foreign_issue`, and Leisure drops `dest_region` (all 11.6M bookings are Domestic) — but the
kept-column list must be written out alongside the model, not re-derived at scoring time.

**3.4 Sub-type names collide across parents.** `name_sub()` returns `direction · timing · tier`.
`one-way · advance · saver` is emitted by **Leisure, OFW/Migrant *and* Outbound Intl. Leisure**;
`round-trip · advance · saver` by **Leisure, Balikbayan/VFR *and* Outbound**. The Power BI key must
therefore be composite (`Parent — sub_name`). Add an assert for within-parent uniqueness too: it holds
today but is not guaranteed by construction, since two classes can round to the same name triple.

**3.5 The non-parent segments need a sentinel.** The other seven labels — Unassigned 566,126 · Premium
Bleisure 343,309 · Ultra Wealthy Leisure 157,490 · Pilgrimage 43,616 · Intl. Student 42,153 · MICE
27,007 · Mabuhay Loyalist 6,453 = **1,186,154 bookings (5.2%)** — plus the export's
`Excluded (non-revenue)` coalesce, get no sub-type. A NULL in a Power BI drill column drops rows
silently. Pick one value and document it: `SubSegment` = the parent name, or `(no sub-type)`.

---

## 4. Work items

### A. `src/sub_segment.py` — emit a model, not just a report

- Build the weighted cell table per parent in DuckDB (one `GROUP BY` over `pal_features_booking.parquet`).
- Fit `K_RANGE` with `sample_weight`; select k on the **hand-computed weighted BIC** (§2).
- Write `outputs/sub_segments/lookup/<parent>.csv` — cell columns + `sub_index` + `sub_name` (≤6,738 rows).
- Write `outputs/sub_segments/model_meta.json` — region map, tier fill, kept columns, chosen k, weighted
  BIC per k, seed, StepMix version. Everything §3 says must be frozen.
- Keep `summary.md`, but regenerate its profiles from the population-weighted cells.
  **Every percentage and median in the current summary.md is a 40k-sample figure and will move.**
- ~150 LOC net, mostly replacing `load_parent`/`code`. Runtime is the `GROUP BY`; fitting 17,847
  weighted rows is seconds.

### B. `data/interim/pal_subsegment.parquet` — the assignment table

`(customer_id, issue_date, sub_segment)` for 21.7M bookings: booking ⋈ lookup on the cell columns, ~1 min
in DuckDB. Needed because the export joins at booking grain — `bk` is keyed on `(customer_id, issue_date)`,
verified unique at 22,911,450 rows / 22,911,450 distinct keys.

*Alternative:* join the lookup inline in the export and skip the file. Cheaper, but the assignment stops
being inspectable outside the export, and `monitor_real.py` or any drift work can't reuse it.
**Recommend the file.**

### C. `src/export_powerbi.py` — carry the column

- `bk` view (~line 428): add the join to the assignment table.
- `FIELDS`: one entry — `("SubSegment", "...", "model output (booking grain, level 2)")`. It then flows
  into `fact_coupons` and `fact_flight` automatically, since the agg keys are `FIELDS − AGG_DROP`.
- `DASH_KEYS`: add explicitly, or `fact_dashboard` silently stays level-1-only.
- `SCORECARD_KEYS`: add — the scorecard grows ~4x (184 KB → ~700 KB, still opens in Excel).
- New `build_dim_subsegment()` → `model/dim_subsegment.csv`, 20 rows: composite key, parent, sub-name,
  sort order, the profile stats, colour derived from the parent's `SegmentColorHex`.
- `docs/powerbi-guide.md` (canonical, copied to `START-HERE.md`): the `Segment → SubSegment` drill
  hierarchy, the sentinel, and the relationship `dim_subsegment[SubSegment] → FACT[SubSegment]`.
- ~120 LOC, on top of the existing ~2 min build.

### Row growth — measure it, expect it to be small

`fact_flight` already groups by coupon-grain analogues of most of the LCA's inputs — `LeadTimeDays`,
`DestRegion`, `RoundTrip`, `IsConnecting`, `FarebrandValueTier`, `TravelMonth`, `CountryCodeOfIssue`.
`SubSegment` is a deterministic function of the cell, so within a `fact_flight` group it is near-constant
and rows barely multiply. (Not exactly constant: `max_tier` is the booking-level max over coupons, so it
isn't identical to per-coupon `FarebrandValueTier`, and `BookingCoupons` is in `AGG_DROP`.)

`fact_dashboard` is the exposed one — `DASH_KEYS` has no `LeadTimeDays` and no `IsConnecting`, so a group
genuinely spans sub-types. Hard upper bound 4x (2.0M → ~8.2M rows, 29 MB → ~120 MB); expect far less.
Measure after B, before touching the export:

```sql
SELECT count(*) FROM (SELECT DISTINCT <DASH_KEYS>, sub_segment FROM fact JOIN sub USING (...));
```

**Decision gate:** if dashboard rows more than triple, keep `fact_dashboard` at level 1 and drill through
to `fact_flight` instead.

### D. Docs — same turn, per CLAUDE.md

`methodology.md` (the refinement layer stops being profile-only) · `pipeline-study-guide.md` §Layer 1 ·
`manuscript-ch4-draft.md` (the "future work" sentence retires) · `README.md` (export contents, docs index)
· `knowledge-base.md` §15.

**Scheduling conflict, not a technical one:** defence deck slide 19 and `src/sankey_subsegment.py` both
read the current 40k-sample figures — the Sankey reads `summary.md` *by design*, so it cannot disagree
with the docs. Re-fitting on the population (§2) moves every one of those numbers. If the defence is
imminent, either do A's re-fit after it, or ship only the assignment and keep the 40k profiles as the
quoted figures.

---

## 5. Sequence and cost

| # | Step | Effort | Deliverable |
|--:|:--|:--|:--|
| 1 | A — fit, lookup, frozen meta | ~half a day | an auditable 17,847-row model |
| 2 | B — assignment table + QA | ~1 hour | every parent booking gets exactly one sub-type; counts reconcile to §1 |
| 3 | Measure dashboard row growth | 15 min | **decision gate** |
| 4 | C — export, dim, guide | ~half a day | `SubSegment` in four tables + `dim_subsegment` |
| 5 | D — docs + deck call | ~2 hours | consistency restored |

**~2 days. No new dependencies** (duckdb, stepmix, pandas, numpy all pinned already).

**Regression test:** the top-level taxonomy does not change, so every level-1 figure in the export must
come out identical. Diff `scorecard_segment_month.csv` before/after — any drift in a level-1 number means
the join fanned out and the level-2 column corrupted the level-1 measures.

## 6. What this does not do

Doesn't make sub-types natural kinds — the continuum caveat carries straight down, and these stay
actionable partitions of a smooth space. Doesn't validate them beyond BIC and split-half stability.
Doesn't touch customer grain: `CustomerDominantSegment` stays level 1. Doesn't change a single level-1
label.

---

*Scoped 21 August 2026. Measurements in §1 and §3 are from `data/interim/pal_features_booking.parquet`
(22,911,450 bookings, built 18 Aug 2026); the StepMix behaviour in §2 was verified against the installed
`stepmix==3.0.0`.*

---

## 7. What actually happened — where the plan was wrong

Shipped as scoped except for five things, all found by building it.

**The assignment lives in a new script, not in `sub_segment.py`.** `summary.md` feeds the defence deck and
`sankey_subsegment.py`, and the plan had step A regenerating it. `src/subsegment_assign.py` is a separate
entrypoint instead: `sub_segment.py` is untouched, and the population-fitted profiles go to
`outputs/sub_segments/population_profiles.md`. Nothing the deck reads changed.

**The fit was not reproducible, and `random_state` was not the reason.** Under `PRAGMA threads=6` a bare
`GROUP BY` returns the cells in a different order every run, which changes the order StepMix sees and so
which EM local optimum it lands in — two consecutive runs gave OFW/Migrant different sub-type boundaries.
`ORDER BY ALL` on the cell table is load-bearing. Verified by hashing the lookups across two full runs.

**The name collision the plan called "not guaranteed by construction" fires immediately.** On the
population fit, two OFW/Migrant classes both round to `one-way · advance · saver`, separated only by
connectivity (0% vs 97% connecting) — which the name never mentions. Colliding names now take a
`· connecting` / `· nonstop` qualifier, ordinal as last resort. §3.4 predicted the cross-parent collision
and under-rated the within-parent one.

**Row growth was over-estimated, and the memory cost was missed entirely.** `fact_dashboard` grew
**1.11x** (2,037,886 → 2,267,904), far inside the 3x gate, and `fact_flight` only 20.6M → 20.7M — as
predicted. What the plan missed: a 49th column that is a ~45-byte string blows the 8 GB DuckDB limit on
the 38.1M-row `PARTITION_BY` COPY. It OOMs three ways — joined at coupon grain, joined at booking grain,
and even with the merge materialised flat. The fix that keeps the memory contract is `PRAGMA threads=3`
for that one statement (peak memory scales with partitions x threads), plus caching the booking-grain
merge to `outputs/powerbi_export/.build/bk.parquet`. Build time went ~2 min → ~5 min.

**A pre-existing level-1 defect surfaced on the way.** `dim_segment.csv`'s `SegmentSortOrder` had **11
twice** — Leisure and `Excluded (non-revenue)` — and no 1, so Power BI ordered those two arbitrarily.
`EXCLUDED` moved to 14 (a non-revenue residual sorts last), and `dim_subsegment` uses a dense 1..28 rank
rather than `parent_sort * 100 + k` so it cannot inherit the same class of bug.

### Verified on the shipped build

- Level 1 unchanged: `dim_segment` profile values byte-identical across the rebuild (MICE 27,007 / 0.12% /
  64 days; Mabuhay Loyalist 6,453 / 0.03% / 14 days).
- All three fact tables reconcile: **38,116,259 coupons · 22,924,577 bookings · 6,219,305,620 revenue**.
- `SubSegment`: zero NULLs, 28 distinct values, zero orphans in either direction against `dim_subsegment`,
  and every sub-segment sits under exactly **one** `CustomerSegment` — so the drill hierarchy is valid.
- 21,725,296 assigned bookings = the parent total exactly, so the join did not fan out.

### Still open

- ~~`docs/manuscript-ch4-draft.md` still says row-level assignment "is future work"~~ **Closed
  23 Aug:** the manuscript (now `docs/manuscript/manuscript-ch4-draft.md` v1.1, §4.2.5) reports the
  shipped row-level assignment and quotes the population-exact profiles. The deck plus `summary.md`
  still quote the 40k-sample profiles — the manuscript names that discrepancy and which is
  authoritative. Balikbayan/VFR is where the two fits genuinely
  disagree: the population fit splits `far-advance · saver` into connecting (median rev 418) and nonstop
  (median rev 962) instead of the sampled `far-advance · value / supersaver / saver`. Reconciling those is
  an author's call, not a build step.
- No validation beyond weighted BIC. Split-half stability on the population fit is not run.
- Future re-scoring on *new* data can still meet a feature level absent from `model_meta.json`'s frozen
  maps. Today's maps cover the population they were fitted on, so it cannot happen in this build; a
  documented fallback is needed before this runs on a fresh extract.
