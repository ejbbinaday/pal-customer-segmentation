# Waterfall v2 — design for review

**Written:** 17 August 2026 · **Status:** design only, **not implemented**
**Authorises:** the five taxonomy decisions in `docs/sme-constraints-intake.md` §7 plus
`Outbound International Leisure`
**Simulated on:** all 22,911,450 bookings in `data/interim/pal_features_booking.parquet`

This is the first change in the SME-constraint programme that **moves PAL's numbers**. 21.8% of bookings
change label. It is written down before being built so the ordering can be argued with rather than
discovered afterwards.

---

## 1. What changes

| | change | source |
|---|---|---|
| **+** | `MICE` | PAL approved · rules S36/S37 |
| **+** | `Ultra Wealthy Leisure` | PAL approved · rule S27 |
| **+** | `Intl. Student` | PAL approved · rule S38 (rewritten) |
| **+** | `Outbound International Leisure` | our analysis — closes taxonomy gap #4 |
| **−** | `Last-Minute` as a segment | PAL: it describes a booking, not a traveller |
| **+** | `is_last_minute` flag (`lead_days <= 3`) | replaces the above |
| **+** | `value_band` attribute (Budget / Mid / Premium) | the "value" half of *purpose × value* |
| **+** | two Corporate branches from `enforce` hard rules | H11, and the H08/H10/H12 composite fence |

Net: **12 emitted segments + `Unassigned`**. `Digital Nomad` remains unimplemented — still no way to
anchor it in anonymous data.

## 2. Three design rules I held to

**① Insert new branches; never reorder existing ones.** Every existing branch keeps its relative
position, so each delta below is attributable to a *new* branch rather than to churn. Reordering would
confound the two and make the before/after unreadable. (Sea-crew and award are arguably more
"definitional" than Corporate and could move up — deliberately not done.)

**② A positive definition beats a residual.** `Family` is defined solely as "a group booking nothing
higher claimed" — 100% of it is `is_group` and nothing else. So `MICE`, which has a real definition, is
checked *before* it. This is the fix for the six-way `is_group` contention.

**③ Specific before general.** `Ultra Wealthy Leisure` is a subset of premium travellers, so it must
precede `Premium Bleisure` or it can never fire. Same for `Intl. Student` before `Balikbayan/VFR`.

## 3. The proposed waterfall

First match wins. New or changed branches marked **▸**.

```
 1     is_award                                                    → Mabuhay Loyalist
 2     corp_channel OR (any_business AND lead_days <= 7)            → Corporate
 3 ▸   round_trip AND stay_nights <= 1 AND max_tier >= 4            → Corporate      [H11 must_be]
 4 ▸   round_trip AND lead_days <= 3 AND stay_nights <= 3
       AND any_premium                                              → Corporate      [fence: H10+H12]
 5 ▸   is_group AND round_trip AND lead_days >= 45
       AND stay_nights BETWEEN 3 AND 7                              → MICE
 6     pilgrimage                                                   → Pilgrimage
 7     sea_crew                                                     → OFW/Migrant
 8 ▸   is_international AND round_trip
       AND stay_nights BETWEEN 90 AND 150                           → Intl. Student
 9     foreign_issue AND is_international AND max_tier <= 4
       AND NOT round_trip                                           → OFW/Migrant
10 ▸   foreign_issue AND is_international AND max_tier <= 4
       AND round_trip
       AND NOT (stay_nights <= 3 AND any_premium)                   → Balikbayan/VFR  [H08 exclusion]
11 ▸   any_premium AND round_trip AND lead_days >= 30
       AND stay_nights >= 7                                         → Ultra Wealthy Leisure
12     any_premium AND is_international                             → Premium Bleisure
13     is_group                                                     → Family
14 ▸   NOT foreign_issue AND is_international AND NOT any_premium    → Outbound International Leisure
15     is_domestic AND NOT any_premium                              → Budget/Adventure
       else                                                         → Unassigned
```

Alongside, not competing:

```
is_last_minute = lead_days <= 3
value_band     = tier 1-2 'Budget' · tier 3-4 'Mid' · tier 5-7 'Premium'
```

## 4. What the constraint check caught — branches 4 and 10

Running the six `enforce` hard rules against a first draft, **two failed**, and neither was obvious:

- **H10** (`lead <= 3 AND stay <= 3 AND cabin J` cannot be Premium Bleisure) — 349 bookings landed in
  Premium Bleisure anyway. Fixed by branch 4, which is the **composite fence** flagged in
  `sme-constraints-intake.md` §5.3: four independently written SME rules all funnel short-turnaround
  premium travel to Corporate, so expressing it as one branch satisfies H10 and H12 together.
- **H08** (`round_trip AND stay <= 3 AND any_premium` cannot be Balikbayan/VFR) — 2,934 slipped
  through, because **H08 has no lead-time clause** and so is not covered by the fence. Needs the explicit
  exclusion on branch 10. Those bookings now fall to Premium Bleisure, which matches H08's own stated
  rationale ("strictly corporate or premium bleisure").

**Ordering alone does not enforce a `cannot_be`.** With the fixes: **6/6 enforce rules satisfied.**

## 5. Before and after

| segment | v1 | v2 | delta | |
|---|---|---|---|---|
| Budget/Adventure | 9,037,176 | **11,440,686** | +2,403,510 | +27% ⚠️ |
| OFW/Migrant | 3,919,215 | 3,907,804 | −11,411 | −0% |
| Balikbayan/VFR | 2,911,291 | 2,871,253 | −40,038 | −1% |
| **Outbound International Leisure** | 0 | **1,991,297** | +1,991,297 | new |
| Corporate | 1,001,638 | 1,168,451 | +166,813 | +17% |
| **Unassigned** | 2,194,061 | **561,401** | −1,632,660 | **−74%** ✅ |
| Family | 370,647 | 350,527 | −20,120 | −5% |
| Premium Bleisure | 481,666 | 343,100 | −138,566 | −29% ⚠️ |
| **Ultra Wealthy Leisure** | 0 | 157,483 | +157,483 | new |
| Pilgrimage | 43,617 | 43,616 | −1 | −0% |
| **Intl. Student** | 0 | 42,153 | +42,153 | new |
| **MICE** | 0 | 27,226 | +27,226 | new |
| Mabuhay Loyalist | 6,453 | 6,453 | 0 | 0% |
| Last-Minute | 2,945,686 | **0** | — | becomes a flag |

**Labels changed: 5,002,040 (21.8%).** Flag coverage: 4,411,666 (19.26%).
Value bands: Budget 63.1% · Mid 30.9% · Premium 6.0%.

**Where the new segments come from** — each draws from where you would want it to:

- `Outbound International Leisure` ← Unassigned 1,757,710 · Last-Minute 233,587
- `Ultra Wealthy Leisure` ← Premium Bleisure 133,811 · Unassigned 23,653
- `Intl. Student` ← Balikbayan/VFR 29,014 · Unassigned 8,546 · Premium Bleisure 4,005
- `MICE` ← **Family 19,512** · Balikbayan/VFR 7,031

## 6. Three risks to accept or reject before building

**⚠️ `Budget/Adventure` reaches 49.93% of the book.** Half the population in one segment is not a
targeting unit. We decided against splitting it (the value rung failed its verification — §"Verification
result" in the intake doc), so the mitigation is the **`value_band` attribute**: it reports as Budget
7.3M / Mid 3.5M without inventing a customer type. **If PAL wants a real split, that is a new decision
and it should be taken now, not after the numbers ship.**

**⚠️ `Premium Bleisure` loses 29%.** 133,811 bookings move to `Ultra Wealthy Leisure`. This is correct —
ultra-wealthy leisure *is* a premium subset and PAL asked for it — but Premium Bleisure is a segment PAL
already has persona slides for, and it shrinks by nearly a third. Needs saying out loud, not discovering.

**⚠️ 21.8% of labels change.** Every published figure, persona card, scorecard and monitoring baseline
derived from `proxy_segment` becomes stale on the same day. Sequencing matters more than the change.

## 7. One open ordering choice

Branches 13/14: does a **PH-issued international economy group booking** — a family of four to Japan —
belong to `Family` or `Outbound International Leisure`?

| ordering | Family | Outbound Intl Leisure |
|---|---|---|
| **Family first** (as drafted) | 350,527 (−5%) | 1,991,297 |
| Outbound first | 159,821 (**−57%**) | 2,182,074 |

**Recommendation: Family first**, i.e. as drafted. Not because it is more correct — arguably "Outbound
first" is, since Family is a residual and Outbound has a positive definition — but because **nobody has
asked PAL**, it moves a further 190,777 bookings, and the `is_group` question is still open with RM
Domestic (§5.1). Do not pre-empt a decision that is one email away.

## 8. The anchor position is unchanged from what was agreed

The design consumes: `is_award` · `corp_channel` · `any_business` · `lead_days` · `round_trip` ·
**`stay_nights`** · `max_tier` · `is_group` · `pilgrimage` · `sea_crew` · `is_international` ·
`foreign_issue` · `any_premium` · `is_domestic`.

It does **not** touch `dep_month`, `n_bookings`, `dep_dow`, `route_theme` or `turn_dest`. So it spends
**exactly the one anchor we agreed to spend** (`stay_nights`) and no more — and it leaves `dep_dow`,
`route_theme` and `turn_dest` still unused, so they remain candidate replacement anchors alongside the
two Tier-A fields. **`src/check_constraints.py` already fails if any active rule reads `dep_month`**; the
same guard should be extended to the waterfall when this is built.

## 9. Downstream work this triggers

Not optional, and larger than the waterfall edit itself:

1. **Penalty weights / asymmetric cost matrix** — four new segments have no weight. This is a *business*
   input (cost of misclassifying each), not ours to invent.
2. **`dim_segment.csv` personas** — four new rows: measured columns recompute automatically, but
   `PersonaName` / `WhyTheyFly` / `WhatTheyWant` / `WhatNotToDo` / `Trust` / `DataCaveat` are editorial.
3. **Re-run validation V1–V4.** Every construct-validity AUC, detection-power floor and temporal-stability
   figure is computed against `proxy_segment` and becomes stale. The headline OFW↔Balikbayan AUC of 0.608
   must be re-measured — improving it is the whole point of spending `stay_nights`.
4. **`src/validation_anchors.py`** — move `stay_nights` into `RULE_FIELDS`; add `round_trip` to
   `AUDIT_BITS`; re-run `src/audit_leaks.py`.
5. **Monitoring baselines** (PSI/ARI) re-baseline, or drift alerts fire on our own change.
6. **`pal_colors.py`** — `SEG_ORDER` finally converges with `SEG_APPROVED`.
7. **Docs** — methodology v1.9, knowledge base, stakeholder report, persona cards, slide decks.

## 10. Recommended sequence

1. Get PAL to accept or reject the three risks in §6 — especially `Budget/Adventure` at 50%.
2. Get **penalty weights** for the four new segments. Without them Stage 7 cannot score.
3. Build the waterfall + flag + band; assert all six `enforce` rules in code, not in review.
4. Re-run V1–V4 **before** publishing any new segment size, so the numbers ship with their validation.
5. Then personas, Power BI, monitoring re-baseline, docs.

**Nothing here is built. Section 6 is the decision gate.**

---

*Simulation: `python src/simulate_waterfall_v2.py` (add `outbound-first` for the §7 alternative). It re-checks the six `enforce` rules on every run and exits non-zero if any is violated. Companions: `docs/sme-constraints-intake.md` (why each rule
exists) · `data/constraints/*.csv` (the rules) · `docs/methodology.md` (spec of record).*
