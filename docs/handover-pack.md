# PAL Customer Segmentation — Handover Pack

**For:** PAL BI / Data & Analytics team · **From:** the MAIDA capstone team (CPT 3)
**Date:** 27 August 2026 · **Status:** v1.0 — the operating manual for the shipped system

> **What this document is.** Everything PAL needs to own this system: what was delivered, how it
> works, how to run a refresh on a new extract, what "retraining" means here (less than you fear),
> how to change the rules safely, a two-week knowledge-transfer plan with pass/fail exercises, and
> the improvement roadmap in the order the evidence supports. Written in two registers throughout —
> plain English first, the technical detail second — so both a commercial owner and an engineer can
> work from the same page.
>
> Deep references live in the repo and are pointed to per section; this document is the map, not a
> replacement for them. **This file also closes an open item: the defence deck's limitations slide
> referenced a "handover pack" — this is that pack.**

---

## 1. What you are receiving

| Deliverable | Where | In one sentence |
|---|---|---|
| **The segmentation model** | `src/features_real.py` (the rule waterfall) | A deterministic rulebook that labels every booking into 11 segments + Unassigned — auditable line by line, no model server needed |
| **Level 2 sub-segments** | `src/sub_segment.py` + `src/subsegment_assign.py` | 20 ML-derived sub-types inside the 5 biggest segments, stamped on all 21.7M of their bookings |
| **The pipeline** | `src/` (one script per stage) | Raw gz extract → cleaned → features → labels → dashboard, every stage writing a checkable report |
| **Power BI star schema** | `outputs/powerbi_export/` (regenerable) | 38,116,259 coupons in = out, asserted; persona and sub-segment dimensions; starter guide inside the folder (`START-HERE.md`) |
| **Validation harness** | `src/validate_*.py`, `src/validation_anchors.py`, `src/detection_power.py` | Four label-free audits + the circularity contract that makes them honest |
| **Drift monitor** | `src/monitor_real.py` | The tripwire: PSI on every rule input + segment-mix stability, ~1 minute per run |
| **SME rule registry** | `data/constraints/*.csv` | PAL's own 57 rules (15 hard / 42 soft), with provenance; the six `enforce` rules are asserted on every build |
| **Documentation** | `docs/` | Methodology spec, data dictionary, business case, stakeholder report, this pack — see the map in §10 |

**The two sentences that explain the whole design.** PAL's customers form a continuum, not natural
clusters — ten methods across six algorithm families confirmed it. So **the rules label, and ML
checks the labels**: business rules draw the segment boundaries where decisions need them, and
machine learning refines below them, audits them on independent evidence, and watches the inputs
for drift.

---

## 2. How it works — the pipeline in one page

```text
raw extract (4 gzipped CSVs, 38.1M coupons)
  → typed Parquet          fast columnar working copy               (~90 s, once per extract)
  → clean + flag           value tiers 1–7, award/group/refund flags (~21 s)
  → features               coupon → BOOKING → customer grain         (22.9M bookings, 13.4M customers)
  → RULE WATERFALL         ← THE MODEL: 11 segments + Unassigned
     ├─ LCA level 2        sub-types inside the 5 biggest segments
     ├─ V1–V4 validation   four label-free audits of the boundaries
     └─ PSI monitoring     drift tripwires on every rule input
  → Power BI export        star schema, 38,116,259 rows in = out (asserted)
```

*Plain version:* a ticket row is one flight leg; the pipeline first reassembles legs into purchase
decisions (bookings), then a priority checklist — like a triage nurse — assigns each booking the
first segment whose rule it matches. Nothing "learns" at the top level, which is a feature: scoring
a new booking is just applying the same checklist, so the labeller itself can never drift. Change
can only enter through the input data — and that is exactly what the monitor watches.

**The grain rule that explains most numbers:** 38.1M coupons → 22.9M bookings (1.66 legs per
booking) → 13.4M customers. If a figure looks wrong by ~40%, someone is mixing coupon-grain and
booking-grain. Full spec: `docs/methodology.md`; field meanings: `docs/data-dictionary.md`.

---

## 3. Setup from zero

**Hardware:** any machine with ~8 GB free RAM (the heavy stages set `memory_limit='8GB'`) and
~15 GB free disk (extract + Parquet intermediates + outputs). A laptop rebuilds everything.

```bash
# 1. Python 3.11–3.14
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-pipeline.txt     # pinned — keep it pinned (results depend on it)
pip install -r requirements-dev.txt          # optional: lint + security tooling

# 2. Data in place (not in git)
#    data/PAL-data/*.txt.gz   ← the coupon extract, 4 gzipped CSVs
```

Docker alternative (identical env regardless of host): `docker build -t pal-segmentation .` — see
`README.md` §Docker. Full annotated package list with versions: `docs/installation.md`.

**Two rules that protect reproducibility:** keep `requirements-pipeline.txt` pinned (clustering
output is version-sensitive), and never hand-edit anything under `outputs/` or `data/interim/` —
they are regenerated; the scripts are the source of truth.

---

## 4. The runbook — refreshing on a new extract

*Plain version: drop the new files in, run nine commands in order, and check five numbers. Total
hands-off time ≈ 15 minutes; nothing needs a GPU, a cluster, or a licence.*

**Step 0 — the extract.** Same shape as before: coupon-grain, the ~40 columns in
`docs/data-dictionary.md`. ⚠️ Ask the extract owner to confirm the **filter is on departure date**
(it was 2024-05-01 → 2027-05-31); if the window moves, the monitor's comparison windows must move
with it (§6).

```bash
python src/build_parquet.py        # 1 · gz → typed Parquet (~90 s)
python src/profile_raw.py          # 2 · profile: nulls, ranges, grain (~1 min)
python src/clean_real.py           # 3 · clean + flag (~21 s)
python src/eda_real.py             # 4 · grain confirmations (~1 min)
python src/features_real.py        # 5 · features + THE LABELS (Stage F)
python src/check_constraints.py    # 6 · SME rules still valid vs the feature table (~1 min)
python src/subsegment_assign.py    # 7 · level-2 sub-types onto every booking (~30 s)
python src/monitor_real.py         # 8 · drift report (~1 min) — READ THIS ONE (§6)
python src/export_powerbi.py       # 9 · Power BI star schema (~5 min)
```

Optional after a refresh: `python src/segment_charts.py` (the six segment charts) and
`python src/report_figures.py` (EDA figures) — both draw from the full tables so charts cannot
disagree with the build.

**The five checks after any refresh** (each printed by the stage that owns it):

| # | Check | Where | Healthy looks like |
|---|---|---|---|
| 1 | Coupons in = coupons out | `export_powerbi.py` output — it **asserts** this | equal, or the build fails loudly |
| 2 | Segment distribution vs last run | `outputs/features_real/summary.md` | shares move smoothly; a segment jumping >2–3 pp deserves a look before publishing |
| 3 | Hard-rule assertions | `features_real.py` (build fails if violated) | six PAL `enforce` rules pass |
| 4 | Constraint sheet still evaluable | `check_constraints.py` | 0 errors |
| 5 | Drift verdicts | `outputs/monitor_real/summary.md` | STABLE, or an explainable alarm (§6) |

**If something fails:** every stage writes its report into `outputs/<stage>/summary.md` — read the
failing stage's report first; the assertions name what broke. Nothing downstream should be run past
a failed stage.

---

## 5. "Retraining" — what it actually means here

*Plain version: there is no model to retrain in the usual sense. The labeller is a rulebook — you
re-run it, you don't retrain it. Three different maintenance actions exist, and they are triggered
by evidence, not by a calendar.*

### 5a. Relabelling (every new extract) — automatic

The waterfall is deterministic: rerunning Stage F on new data **is** the "retrain". No fitting, no
seeds, no drift inside the model. Reproducible to within ±1 booking in 22.9M (1,830 tied sort keys
— cause documented; the fix is drafted and is on the hardening list, §9).

### 5b. Refitting level 2 (the LCA sub-types) — occasional

**When:** the taxonomy changes, a segment's profile drifts (§6 flags it), or roughly annually.
**How:** `python src/sub_segment.py` (refit profiles) then `python src/subsegment_assign.py`
(re-stamp bookings). **Three things the next person must know, learned the hard way:**

1. **Determinism is not `random_state`.** The cell table must be `ORDER BY ALL` before StepMix
   sees it — under multithreading, an unordered `GROUP BY` returns rows in a different order every
   run, which changes which local optimum EM lands in. The code does this; do not remove it.
2. **`StepMix.bic()` lies on a weighted cell table** (it uses the unweighted score and N = number
   of cells). Weighted BIC is hand-computed in the script — keep it that way.
3. **Sub-types are provisional by design** — actionable partitions of a continuum, not natural
   kinds. Target with them; never score a customer's worth by them. Balikbayan/VFR's sub-structure
   is the least stable (split-half ARI 0.495) — act on the direction of its value spread, not
   exact cell edges.

### 5c. Changing the rules (the taxonomy itself) — governed, not casual

*Plain version: the rules are the model, so a rule change is a model release — simulate first,
check the guardrails, re-audit, then ship. The repo contains a worked example of doing this right:
the v1 → v2 change (waterfall v2, 18 Aug).*

The seven-step release procedure:

1. **Write the proposal** — what changes, why, expected movement
   (`docs/waterfall-v2-design.md` is the template).
2. **Simulate before building** — a before/after on the full 22.9M bookings, the
   `simulate_waterfall_v2.py` pattern: how many labels move, where they go, does any hard rule
   break.
3. **Check the anchor budget** — the scarce resource nobody expects: a field can be a rule input
   **or** validation evidence, never both. Spending a clean field on a rule permanently weakens
   the audit. Only two fields are unconditionally clean today (`dep_month`, `n_bookings`);
   `src/validation_anchors.py` is the registry and it **raises** on violations.
4. **Check the SME constraints** — `python src/check_constraints.py`; the six `enforce` rules in
   `data/constraints/hard_constraints.csv` are asserted on every build (the build fails, not
   warns). Note: ordering alone does not implement a "cannot be" — the v2 build initially
   satisfied only 4 of 6.
5. **Update the palette contract** — `src/pal_colors.py` (`SEG_ORDER`/`SEG_APPROVED`/
   `SEG_RETIRED`): charts assert they can never advertise a segment the waterfall doesn't emit.
6. **Re-run the audits** — V1 construct + V4 stability at minimum
   (`validate_construct.py` ~15 min · `validate_temporal.py --quick` ~1 min directional); after a
   large change, V3 (`detection_power.py --quick`) too.
7. **Update the paper trail** — `docs/methodology.md` changelog + `README.md`; regenerate
   `dim_segment.csv` via the export. A rule change that skips the docs will resurface as a "stale
   number" incident — the project's history proves it.

### 5d. When the calendar does matter

Re-run `validate_temporal.py` when a new 12-month issuance window completes clean of the
departure-date censoring (§0 of that script explains the window math — read it before any temporal
analysis; naive calendar windows fake a lead-time collapse).

---

## 6. Monitoring — the tripwires and how to read them

**Cadence: monthly** `python src/monitor_real.py` (~1 min), or after any extract refresh.
Output: `outputs/monitor_real/summary.md`.

| Signal | What it measures, plainly | Bands | Current |
|---|---|---|---|
| Segment-mix PSI | has the share-of-segments pie shifted? | <0.10 stable · 0.10–0.25 watch · ≥0.25 act | **0.0028** — very stable |
| Per-rule-input PSI | has any field feeding a rule shifted? | same bands | 22 of 23 stable |
| Per-segment volume/revenue drift | is any single segment moving? | judgement + trend | small drifters are the small segments |

**The worked example that teaches the tool** — the one alarm in the current report: `channel`
reads PSI **0.4111 → RETRAIN**. Decomposed, **93% of it is NDC** — a sales channel PAL switched on
mid-window, going from 0 to 366,890 bookings. Excluding brand-new categories the same feature reads
**0.0285 → STABLE**. The report prints both verdicts side by side. *The lesson: a new-category
alarm and a behaviour-drift alarm need different responses — the first means "does the waterfall
need a branch for this new thing?", the second means "has the world changed under an existing
rule?". Retraining on a distribution change PAL itself caused would have been the wrong move.*

**What the monitor deliberately does not compute:** clustering-quality scores (DBCV/silhouette) and
cross-window ARI — those grade a *fitted* clustering, and the shipped labeller is deterministic
(re-applied to the same bookings it scores 1.0 by construction). The report says so on the page
rather than leaving a blank.

**Escalation:** PSI ≥ 0.25 on a rule input after excluding new categories → investigate the field
before the next publish; sustained segment-share move > ~2 pp → re-run V1 on the affected
boundaries; new channel/farebrand appears → taxonomy question for the commercial owner, §5c.

---

## 7. The Power BI model — rebuild and the traps

Rebuild: `python src/export_powerbi.py` (requires `subsegment_assign.py` first). The folder
`outputs/powerbi_export/` is a self-contained handoff — `START-HERE.md` inside is the 5-minute
guide (canonical copy: `docs/powerbi-guide.md`, with starter DAX).

**The five traps every new BI developer hits — designed out, but the defaults must survive edits:**

1. **The fake cliff.** Travel months after the extract boundary are still-filling forward book.
   Default every trend visual to `IsCompleteTravelMonth = TRUE` (full-year comparisons: 2025 is
   the only complete travel year).
2. **Grain double-count.** Use `IsPrimaryCoupon = TRUE` for booking-level measures; `Bookings` is
   `SUM(IsPrimaryCoupon)`, never a DISTINCTCOUNT.
3. **Revenue-halving filter.** Never compute revenue with `Bookings > 0` as a row filter — it
   silently drops non-primary coupons' revenue (it cost Balikbayan −54% before an independent
   cross-check caught it). Correct form: `SUM(NetRevenue) / SUM(Bookings)` over unfiltered rows.
4. **No stored percentages.** Shares are DAX measures, never columns — a share is only valid in
   the filter context that computed it.
5. **Caveats on the cards.** `Trust` and `DataCaveat` ship as columns on `dim_segment` — keep them
   on persona cards. A cropped caveat is how "Mabuhay 0.03%" becomes "loyalty doesn't matter".
   And **no accuracy KPI exists by design** — any number computable today would be self-graded.

---

## 8. Knowledge transfer — the two-week plan

*Each exercise has a pass condition. The goal is not to watch us run it — it is that by day 10,
PAL has run everything, broken something safely, and read every report the system writes.*

**Week 1 — operate it.**

| Day | Exercise | Pass condition |
|---|---|---|
| 1 | Environment + `build_parquet.py` + `profile_raw.py` | profile row count = **38,116,259**; column profile matches the data dictionary |
| 2 | Run steps 3–6 of the runbook | segment table in `outputs/features_real/summary.md` matches the published distribution (Leisure ≈50.6%, Unassigned ≈2.47%) |
| 3 | `subsegment_assign.py` + `monitor_real.py`; write a 5-line reading of the drift report | the write-up correctly explains the NDC alarm as a new category, not behaviour drift |
| 4 | `export_powerbi.py`; open the model; tie totals | fact totals reconcile to `scorecard_segment_month.csv` in Excel; trend visual filtered to complete months |
| 5 | Read `docs/methodology.md` §Current Methodology + the validation ladder; teach it back in 10 minutes | can answer: why rules and not clustering? why no accuracy number? |

**Week 2 — change it safely (sandbox on a branch).**

| Day | Exercise | Pass condition |
|---|---|---|
| 6 | Wiggle a threshold: change the short-lead flag from 3 → 5 days in a copy of Stage F; measure the movement | reports how many bookings' flag flips, and why the *segment* labels don't move |
| 7 | Break a guardrail on purpose: write a toy rule that reads `dep_month`; run `check_constraints.py` | watches it **fail**, and can explain the anchor budget (§5c step 3) in plain words |
| 8 | Refit level 2 twice; hash-compare the lookup CSVs | identical hashes; can explain why `ORDER BY ALL` is load-bearing |
| 9 | Mock rule change end to end: simulate → constraints → V4 `--quick` → docs note | the seven steps of §5c executed in order, on a throwaway rule |
| 10 | Mock monthly review: run the monitor on a modified sample, present verdicts to the commercial owner | correct STABLE/WATCH/ACT calls; escalation path named |

**Exit criteria:** PAL has produced one full refresh unassisted; one drift report read correctly;
one simulated rule change through all seven steps; and knows which document answers which question
(§10).

---

## 9. Limitations that must travel with the system

*Say these before anyone asks; each has a number and a source — they are measurements, not
apologies.*

- **No accuracy figure exists — by design.** Every label came from our rules, so any accuracy
  computable today is circular. The SME-labelled sample (~1,000 bookings) unlocks a real one.
- **The loyalty blind spot.** No loyalty-tier field → Mabuhay Loyalist is visible only via award
  redemptions (0.03%). The segment is real; our sight is not.
- **Blind below ~1% prevalence.** A real segment smaller than ~229k bookings could exist and the
  detection tests would not have found it.
- **Labels add no incremental prediction** over the raw features (+0.0005–0.0024 AUC) — a
  compression cannot beat its source. The value is shared vocabulary and targeting, not prediction.
- **No churn rate is computable** — 73.9% of customers have one booking in a ~27-month window; a
  new customer and a lost one are identical (right-censoring). Loyalty use-cases wait for the
  identity join.
- **Revenue mix is the weaker stability leg** (TVD 3.36 pp vs 1.71 pp on shares) — a segment
  holding its size is not evidence its value held.
- **Known edges:** ±1 booking build variance (1,830 tied keys); `dest_region` is an alphabetical
  max on multi-region trips (1.65% of bookings); the `Unassigned` premium-cabin anomaly must be
  diagnosed before any lounge/premium policy is set from this output.

---

## 10. Future improvements — in the order the evidence supports

*Plain version: data before algorithms. Every test says the ceiling is in the data we have, not in
the methods — so the roadmap starts with fields, not fancier models.*

**Tier 1 — data investments (each unlocks something specific):**

| Ask | Unlocks |
|---|---|
| **Loyalty tier join** (PAL answer B4) | Mabuhay becomes measurable; churn/retention becomes a real department case; the vendors' strongest levers and ours simultaneously |
| **Fare basis codes** (requested) | Settles the Manila–Gulf one-month-clock confound (behaviour vs fare rule) |
| **Ancillary revenue** | Corrects per-booking value for bag-heavy segments (OFW especially); quantifies the CX case |
| **Party size** (B3) | Lets MICE be valued per contract — the largest single understatement |
| **Repeated dated extracts** | Enables the LY-vs-CY pickup measure the current extract cannot support |

**Tier 2 — close the validation loop:**
1. **SME gold sample** — ~1,000 hand-labelled bookings, contested boundaries first (Corporate),
   with inter-rater agreement. Retires the circularity caveat; also makes rule *re-weighting*
   estimable (a proper label model over the rules).
2. **One instrumented marketing campaign** — replaces the invented recovery-rate assumption in the
   business case with a measurement; verifiable inside a single campaign cycle.
3. **Penalty-weight sign-off** — the dollar-grounded proposal ($495–$9,784 spread) awaits PAL's
   "see a run first".

**Tier 3 — model work (each gated by a pre-registered decision rule; see
`docs/continuum-levers-plan.md`):**
- Stage-matched GMM vs LCA re-test on the sub-segmentation job (GMM won the *top-level* benchmark;
  swap only if it wins the actual job).
- V4 transfer with a multi-seed spread and a wider method panel (the current two-method,
  single-seed reading is unresolved on purpose).
- Re-run `rule_confidence.py` against the v2 waterfall (its published figures are v1-era).
- The seven "continuum levers" (per-market fits, learned embeddings, longitudinal features …) —
  each with a stop rule, embeddings last.

**Tier 4 — production hardening:**
- **Feature contract at ingestion** — a silently missing input column degrades labels without
  failing loudly; the contract should gate any production deployment.
- Fix the 1,830 tied sort keys (drafted) → byte-identical builds.
- Add the one-sentence NDC explanation to the monitor's prose (the verdicts are printed; the
  explanation should be too).
- Keep every report generator's `--report-only` path — most "stale numbers" incidents are stale
  prose, and the two deserve different fix costs.

---

## 11. Document map — which file answers which question

| Question | Read |
|---|---|
| How does the whole method work, formally? | `docs/methodology.md` (spec + changelog) |
| What does each field mean? | `docs/data-dictionary.md` |
| How do I set up the environment? | `docs/installation.md` |
| How do I build the dashboard / write DAX? | `docs/powerbi-guide.md` (copied into the export as `START-HERE.md`) |
| What do the segments mean commercially? | `docs/stakeholder-report.md` (personas, plain language) |
| Why should PAL invest — the money case? | `docs/do-nothing-vs-implement.md` (measured) + `docs/business-case-benchmark.md` (benchmark) |
| What did PAL's own experts contribute? | `docs/sme-constraints-intake.md` + `data/constraints/README.md` |
| What changed when, and why? | `docs/knowledge-base.md` §15 (the dated learning log) |
| The full study version of everything above? | `docs/final-defense-reviewer.md` |
| What's still open with PAL? | `docs/pal-questions.md` / `.csv` |

**Handover contacts:** the capstone team remains reachable through AIM for a transition period;
the learning log (`docs/knowledge-base.md` §15) is the append-only project memory — keep writing
to it. The single most important habit to inherit: **when a number changes, grep the generators
first, then the docs** — a figure quoted inside a script is a stale sentence with a schedule.

---

*Prepared by CPT 3 — PAL Customer Segmentation · Sources: `README.md`, `docs/methodology.md`
v1.12, `docs/installation.md`, `outputs/` stage summaries, `docs/knowledge-base.md` §15.
Last updated: 2026-08-27.*
