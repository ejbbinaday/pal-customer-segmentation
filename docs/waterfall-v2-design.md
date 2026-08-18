# Waterfall v2 — design for review

**Written:** 17 August 2026 · **Revised:** 18 August 2026 after PAL's answers · **Status:** design
only, **not implemented**
**Authorises:** the five taxonomy decisions in `docs/sme-constraints-intake.md` §7, PAL's answers in
`wishlist/pal-questions-answered-2026-08-18.csv`, and `Outbound International Leisure`
**Simulated on:** all 22,911,450 bookings in `data/interim/pal_features_booking.parquet`

This is the first change in the SME-constraint programme that **moves PAL's numbers**. 21.8% of bookings
change label. It is written down before being built so the ordering can be argued with rather than
discovered afterwards.

---

## 0. Revision 18 August — what PAL's answers changed

All 24 questions came back answered. Five changed the design:

| Item | PAL's answer | Effect on this design |
|---|---|---|
| **A6 / C6** | *"might be best to drop family"* | **`Family` is removed entirely.** It had no positive definition — 100% of it was "a group booking no other rule claimed". Its 350,527 bookings redistribute: **190,777** to Outbound International Leisure, **155,025** to Leisure, 4,725 to Unassigned |
| **D4** | *"consider budget/adventure as leisure"* | **`Budget/Adventure` is renamed `Leisure`.** A rename, not a mapping — reversing the 17 Aug position, so palette, Power BI dimension, personas and decks all follow |
| **D2** | *"drop this segment"* | **`Digital Nomad` is removed.** Never implemented, so no bookings move — but the original 10-segment requirement is formally reduced |
| **C2** | *"do not agree, RUHMNL should be read as is"* | The Gulf rule is now **explicitly directional on the inbound leg** rather than direction-agnostic. **RM is right** — agnostic matching conflates workers *leaving* for the job with workers *coming home*, which are different rules. It costs almost nothing: **90,540 bookings vs 94,247** agnostic, so 96% of the volume with a cleaner definition |
| **D3** | *"No other airport codes to add"* | The **Catholic pilgrimage hubs are withdrawn** — Jeddah/Medina only. Consistent with the measurement: those rules fired on under 700 bookings each |
| **B3** | *"yes these can stand in"* | **H13 is unblocked.** The group indicator substitutes for party size, so branch 5 gains `AND NOT any_cabin_j`. ⚠️ The "party > 10" *threshold* is still unevaluable, so this is the weaker form RM accepted |
| **A1** | *"see run first"* | Cost weights deferred. **The build proceeds on explicit placeholders**, to be replaced before anything is scored for real |
| **A2 / A3 / A4** | accept · accept · ok | The three risks in §6 are **cleared** |
| **B5** | *"US Dollar $"* | Revenue is **USD** — first confirmation. Retroactively validates every revenue figure we have quoted |

**Dropping `Family` also settles the A5 ordering question by dissolving it.** A5 asked whether an
international group booking is `Family` or `Outbound International Leisure`; PAL answered "Family" *and*
separately asked us to drop Family. With the segment gone, those 190,777 bookings land in Outbound
International Leisure — which is where the alternative ordering would have put them anyway. **§7 is
therefore closed.**

⚠️ **One answer conflicts with a decision already taken.** D3 supplies a **May/June Mecca window** — a
departure-month rule — immediately after **C8 agreed to withdraw the month-based rules** to keep
`dep_month` as a validation anchor. Their seasonal knowledge is recorded in `soft_constraints.csv` S41 but
**deliberately not encoded**. This needs raising with them: either the pilgrimage seasonality stays out,
or the anchor decision is revisited. It should not be resolved silently in either direction.

---

## 1. What changes

| | change | source |
|---|---|---|
| **+** | `MICE` | PAL approved · rules S36/S37 |
| **+** | `Ultra Wealthy Leisure` | PAL approved · rule S27 |
| **+** | `Intl. Student` | PAL approved · rule S38 (rewritten) |
| **+** | `Outbound International Leisure` | our analysis — closes taxonomy gap #4 |
| **−** | `Last-Minute` as a segment | PAL: it describes a booking, not a traveller |
| **−** | `Family` | PAL 18 Aug: no positive definition beyond `is_group` |
| **−** | `Digital Nomad` | PAL 18 Aug: drop it — never implementable in anonymous data |
| **~** | `Budget/Adventure` → **`Leisure`** | PAL 18 Aug: a rename, not a mapping |
| **+** | `is_last_minute` flag (`lead_days <= 3`) | replaces the above |
| **+** | `value_band` attribute (Budget / Mid / Premium) | the "value" half of *purpose × value* |
| **+** | two Corporate branches from `enforce` hard rules | H11, and the H08/H10/H12 composite fence |

Net: **11 segments + `Unassigned`** — four additions and three removals against the original ten.

## 2. Three design rules I held to

**① Insert new branches; never reorder existing ones.** Every existing branch keeps its relative
position, so each delta below is attributable to a *new* branch rather than to churn. Reordering would
confound the two and make the before/after unreadable. (Sea-crew and award are arguably more
"definitional" than Corporate and could move up — deliberately not done.)

**② A positive definition beats a residual.** `Family` was defined solely as "a group booking nothing
higher claimed" — 100% of it was `is_group` and nothing else. That is why `MICE` is checked early, and
ultimately why **PAL dropped `Family` altogether**: applying the principle honestly left nothing behind
it. The six-way `is_group` contention is resolved by the segment ceasing to exist rather than by an
ordering tweak.

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
       AND stay_nights BETWEEN 3 AND 7 AND NOT any_cabin_j          → MICE            [H13 via B3]
 6     pilgrimage                        (Jeddah/Medina only)       → Pilgrimage
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
13 ▸   NOT foreign_issue AND is_international AND NOT any_premium    → Outbound International Leisure
14 ~   is_domestic AND NOT any_premium                              → Leisure        [renamed]
       else                                                         → Unassigned
```

`Family` and `Digital Nomad` have no branch — both were dropped by PAL on 18 August.

Alongside, not competing:

```
is_last_minute = lead_days <= 3
value_band     = tier 1-2 'Budget' · tier 3-4 'Mid' · tier 5-7 'Premium'
```

## 4. What the constraint check caught — branches 4 and 10

Running the six `enforce` hard rules against a first draft, **two failed**, and neither was obvious:

- **H10** (`lead <= 3 AND stay <= 3 AND cabin J` cannot be Premium Bleisure) — 349 bookings landed in
  Premium Bleisure anyway. Fixed by branch 4, the **composite fence** flagged in
  `sme-constraints-intake.md` §5.3: four independently written SME rules all funnel short-turnaround
  premium travel to Corporate, so expressing it once satisfies H10 and H12 together.
- **H08** (`round_trip AND stay <= 3 AND any_premium` cannot be Balikbayan/VFR) — 2,934 slipped
  through, because **H08 carries no lead-time clause** and so is not covered by the fence. Needs the
  explicit exclusion on branch 10. Those bookings now fall to Premium Bleisure, matching H08's own
  stated rationale ("strictly corporate or premium bleisure").

**Ordering alone does not enforce a `cannot_be`.** With the fixes: **6/6 satisfied**, re-asserted on
every run of `src/simulate_waterfall_v2.py`, which exits non-zero if that stops being true.

## 5. Before and after

| segment | v1 | v2 | delta | |
|---|---|---|---|---|
| **Leisure** *(was Budget/Adventure)* | 9,037,176 | **11,595,711** | +2,558,535 | +28% ⚠️ |
| OFW/Migrant | 3,919,215 | 3,907,804 | −11,411 | −0% |
| Balikbayan/VFR | 2,911,291 | 2,871,256 | −40,035 | −1% |
| **Outbound International Leisure** | 0 | **2,182,074** | +2,182,074 | new |
| Corporate | 1,001,638 | 1,168,451 | +166,813 | +17% |
| **Unassigned** | 2,194,061 | **566,127** | −1,627,934 | **−74%** ✅ |
| Premium Bleisure | 481,666 | 343,309 | −138,357 | −29% ⚠️ |
| **Ultra Wealthy Leisure** | 0 | 157,489 | +157,489 | new |
| Pilgrimage | 43,617 | 43,616 | −1 | −0% |
| **Intl. Student** | 0 | 42,153 | +42,153 | new |
| **MICE** | 0 | 27,007 | +27,007 | new |
| Mabuhay Loyalist | 6,453 | 6,453 | 0 | 0% |
| Family | 370,647 | **0** | — | dropped |
| Last-Minute | 2,945,686 | **0** | — | becomes a flag |
| Digital Nomad | 0 | 0 | — | dropped |

Flag coverage: 4,411,666 (19.26%). Value bands: Budget 63.1% · Mid 30.9% · Premium 6.0%.

**Where the new segments come from** — each draws from where you would want it to:

- `Outbound International Leisure` ← Unassigned 1,757,710 · Last-Minute 233,587 · **Family 190,777**
- `Ultra Wealthy Leisure` ← Premium Bleisure 133,811 · Unassigned 23,653
- `Intl. Student` ← Balikbayan/VFR 29,014 · Unassigned 8,546 · Premium Bleisure 4,005
- `MICE` ← **Family 19,511** · Balikbayan/VFR 7,031
- `Leisure` ← Budget/Adventure 9,037,176 (rename) · Last-Minute 2,476,607 · **Family 155,025**

## 6. Risks — status after PAL's answers

**✅ CLEARED (A2).** `Leisure` reaching ~50% of the book: **accepted**. It is now 50.61%, marginally
higher than the 49.93% put to them because it also absorbs 155,025 ex-`Family` bookings. The mitigation
is unchanged — `value_band` reports it as Budget 7.3M / Mid 3.5M without inventing a customer type.

**✅ CLEARED (A3).** `Premium Bleisure` losing 29% to `Ultra Wealthy Leisure`: **accepted**.

**✅ CLEARED (A4).** The relabelling volume: **"ok with decision"**. Note it is now larger than the 21.8%
put to them, because `Family` and the rename move on top. Sequencing still matters — re-run validation
before publishing any new segment size.

**⚠️ STILL OPEN — the D3/C8 conflict.** PAL supplied a May/June Mecca window after agreeing to withdraw
the month-based rules. Recorded, not encoded. **Raise before building.**

**⚠️ STILL OPEN — A1, and it gates scoring.** Cost weights are deferred until PAL sees the model run, so
the build must carry **explicit placeholders** that cannot be mistaken for agreed values.

## 7. ~~Ordering choice~~ — closed

Dissolved by dropping `Family`; see §0.

## 7a. ⚠️ Known gap — the anchor bought less than the headline implied

**The boundary `stay_nights` was spent to fix is still split on `round_trip` alone.**

Branches 9 and 10 are unchanged from v1. The Gulf stay-length discriminator (**S14**) is a *soft prior*,
and **nothing in the codebase reads soft priors** — only `check_constraints.py` opens that file. So the
rule that justified the anchor trade is currently documentation.

`stay_nights` is not wasted: it does real work in six branches (Corporate ×2, MICE, Intl. Student,
Ultra Wealthy Leisure, and the H08 exclusion). But the *headline* justification is unimplemented.

**And implementing it would be smaller than the 0.676 figure suggests.** Promoting S14 to a branch ahead
of Balikbayan/VFR moves **79,993 bookings — 2.6% of that branch**:

| | S14 → OFW | stays VFR |
|---|---|---|
| bookings | 79,993 | 2,965,951 |
| mean revenue (USD) | 723 | 619 |
| median stay | **33 nights** | 12 nights |
| % group | 0% | 4% |
| median lead | 39 days | 47 days |

The profile difference is real and in the predicted direction. But **the 0.676 AUC was measured on a
*corridor proxy*** — stay length separating Gulf-bound from US/Canada/Australia-bound destinations — **not
on the OFW/VFR labels themselves.** Applied as a rule it touches 2.6% of the branch, so **it will not
transform the 0.608 boundary AUC and we should not tell PAL it will.**

**Two ways forward, and they are not exclusive:**

1. **Promote S14 to a branch** (cheap, honest, modest). Every branch in this waterfall is already
   inferential — "cabin J → Corporate" is a heuristic — so a moderate-strength rule is not out of place
   in a *proxy* labeller. Do it, and state the size plainly.
2. **Build the soft-prior consumption layer.** 19 rules are marked `prior` and none of them can affect
   a label. Until that layer exists, three-quarters of the SME's contribution is inert. This is the
   larger prize and it is the architecture the constraint files were designed for.

**The real fix for this boundary is probably neither.** A frequent-flyer number is a far stronger
OFW-vs-Balikbayan signal than stay length, and PAL has just agreed to supply `IsFrequentFlyer`,
`IsTourCode` and `Isupgrade` (B2). **Those fields are on the critical path for the weakest part of the
deliverable** — chasing them matters more than either option above.

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
6. **`pal_colors.py`** — `SEG_ORDER` converges with `SEG_APPROVED`. `SEG_RETIRED` already records the
   four departures (`Budget/Adventure` renamed, `Family` and `Digital Nomad` dropped, `Last-Minute`
   flagged) so a stale reference is a lookup rather than a mystery.
8. **Anything naming `Budget/Adventure`, `Family` or `Digital Nomad`** — the rename and the two drops
   touch the stakeholder report, persona cards, both slide guides and the manuscript draft. This is the
   largest documentation change in the programme.
7. **Docs** — methodology v1.9, knowledge base, stakeholder report, persona cards, slide decks.

## 10. Recommended sequence

1. ~~Get PAL to accept or reject the three risks in §6~~ — ✅ **done 18 Aug, all three accepted.**
2. **Resolve the D3/C8 seasonality conflict** — one email, and it should not be decided silently.
3. **Cost weights are deferred by PAL** (*"see run first"*), so build with **explicit placeholders**
   that cannot be mistaken for agreed values. Stage 7 cannot score for real until they arrive.
4. Build the waterfall + flag + band; **assert all six `enforce` rules in code, not in review.**
5. Re-run V1–V4 **before** publishing any new segment size, so the numbers ship with their validation.
   The OFW↔Balikbayan AUC of 0.608 is the one to watch — improving it is why `stay_nights` was spent.
6. Then personas, Power BI, monitoring re-baseline, and the documentation sweep (§9.8 — the rename plus
   two drops touch every deliverable that names a segment).

**Nothing here is built.** The §6 gate is now cleared apart from two items: the **D3/C8 seasonality
conflict** and **A1's deferred cost weights**. Neither blocks building the waterfall; both block
*publishing* from it.

---

*Simulation: `python src/simulate_waterfall_v2.py` — re-checks the six `enforce` rules on every run and exits non-zero if any is violated. Companions: `docs/sme-constraints-intake.md` (why each rule
exists) · `data/constraints/*.csv` (the rules) · `docs/methodology.md` (spec of record).*
