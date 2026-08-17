# SME constraints intake — `PALxMAIDA_Constraints&Wishlist.xlsx`

**Received:** 17 August 2026 · **File:** `wishlist/PALxMAIDA_Constraints&Wishlist.xlsx`
**Responding SME:** RM — Domestic · **Ask it answers:** `data/constraints/README.md`
**Status:** analysed, probed, **transcribed** into `data/constraints/*.csv` (15 hard + 42 soft rules), and
**all five blocking decisions resolved by PAL on 17 Aug** (§7). 6 hard rules are marked `enforce` and 19
soft rules `prior`; 5 are `withdrawn` to protect a validation anchor. **The waterfall is still untouched** —
the remaining work is the taxonomy change itself (10 → 13 segments, Last-Minute → flag), which §7 sizes.
Validate any edit with `python src/check_constraints.py`.

---

## 1. What actually came back

The workbook has four sheets. Only one carries new content.

| Sheet | Content | Verdict |
|---|---|---|
| `Guide` | Definitions of the 5 constraint types and 5 confidence levels | Matches our `hard`/`soft` split — see §2 |
| `Constraints` | **51 rows** — 12 are our own seeded examples returned verbatim (owner `MAIDA`), **39 are new** (owner `RM- Domestic`) | The deliverable |
| `DataDictionary (Fields)` | 33 fields the SME was told they could reference | **6 of them do not exist in our feature table** — §4 |
| `PowerBI DB Wishlist` | Header row only — `Department / Requested Field/View / Remarks` | **Empty. Unanswered ask.** |

The 39 new rows break down as:

| Verdict | n | | Confidence | n |
|---|---|---|---|---|
| Leans Toward | 26 | | moderate | 18 |
| Cannot Be | 9 | | strong | 9 |
| Leans Away From | 3 | | **certain** | **8** |
| Must Be | 1 | | weak | 3 |
| | | | likely | 1 |

**8 `certain` + 1 `likely` = 9 rows are hard constraints** under our own rule ("only `certain` is auto-enforced");
the other 30 are soft priors. That roughly triples `hard_constraints.csv` (7 → ~16) and quadruples
`soft_constraints.csv` (7 → ~37).

### Segments they wrote for

| Segment as written | n | Maps to our canonical name |
|---|---|---|
| Premium Bleisure | 6 | ✅ Premium Bleisure |
| Corporate | 5 | ✅ Corporate |
| VFR | 4 | ✅ Balikbayan/VFR |
| OFW | 4 | ✅ OFW/Migrant |
| Pilgrimage | 4 | ✅ Pilgrimage |
| Leisure | 3 | ✅ **`Budget/Adventure`** — confirmed by PAL 17 Aug as a naming difference, not a new segment |
| **Ultra wealthy leisure** | 3 | ✅ **approved as a new segment** by PAL, 17 Aug |
| **Intl. Student** | 3 | ✅ **approved as a new segment** by PAL, 17 Aug |
| **MICE** | 3 | ✅ **approved as a new segment** by PAL, 17 Aug |
| Last-Minute *(as 4 named flavours)* | 4 | ⚠️ **becomes a flag, not a segment** (PAL, 17 Aug) — their sub-typing is what argued for it |

**Never mentioned:** `Mabuhay Loyalist`, `Family`, `Budget/Adventure`, `Digital Nomad`, `Unassigned`.
Four of our ten segments got zero SME input, and three segments we didn't model got twelve rules between
them — all three of which PAL has now approved, taking the taxonomy to 13.

---

## 2. It fits our schema almost exactly

This is the good news and it is not trivial. Their `Guide` sheet independently arrived at the same
hard/soft distinction we designed:

| Their constraint type | Our column | Notes |
|---|---|---|
| `must be` | `hard.verdict = must_be` | 1:1 |
| `cannot be` | `hard.verdict = cannot_be` | 1:1 |
| `narrow to` | `hard.verdict = narrow_to` | 1:1, `\|`-separated segments |
| `leans toward` | `soft.leans_toward` | 1:1 |
| `leans away from` | `soft.leans_away_from` | 1:1 |

Confidence maps too — `certain`/`likely` are our hard-constraint levels, `strong`/`moderate`/`weak` are our
soft strengths. Their `Guide` even restates our enforcement rule ("`certain` is auto-enforced; `likely` is
tested against the data and returned to the SME if contradicted"). **No schema negotiation needed.**

One inconsistency to fix on intake: **row 9** is `Must Be` at confidence `Likely`, and **row 34** is
`Cannot Be` at `moderate`. Hard verdicts only take `certain`/`likely`; `moderate` is a soft strength.
Row 34 goes to `soft_constraints.csv` as a strong lean-away, not a hard veto.

---

## 3. The single most valuable thing in the file

**Rows 14, 16, 17 and 21 hand us a discriminator for the weakest boundary in the taxonomy.**

`OFW/Migrant` vs `Balikbayan/VFR` is the boundary that splits 6.8M bookings on a single bit
(`round_trip`, waterfall rules ⑤ vs ⑥) and scores the lowest construct-validity AUC in the project —
**0.608**, barely above chance. We have flagged it as the weakest leg of the deliverable in every doc.

The SME split them on **stay length**, a field the waterfall does not consume:

| Row | Segment | Condition | Strength |
|---|---|---|---|
| 21 | OFW | `StayPattern BETWEEN 28 AND 45 AND CountryCodeOfIssue != 'PH'` | moderate |
| 14 | VFR | `CountryCodeOfIssue != 'PH' AND round_trip AND StayPattern >= 14 AND tier <= Economy Flex` | strong |
| 16 | VFR | `Month(dep) IN (11,12,1) AND StayPattern >= 21 AND round_trip` | strong |
| 17 | VFR | **cannot_be** `StayPattern <= 3 AND cabin IN ('J','W')` | certain |

The mechanism they give is specific and testable: OFWs get **employer-mandated annual leave of precisely
~30 or ~45 days**; balikbayans stay open-ended, 14+ and typically 21+ over the Q4/Q1 holidays. That is a
*distributional* claim — a spike at 30 and 45 nights in the OFW corridors — which we can check directly
against the 9.79M round-trip bookings where stay length is computable.

### ✅ TESTED 17 Aug 2026 — `src/probe_stay_length.py`, `outputs/stay_length/summary.md`

**Verdict: the Gulf half is confirmed, the rest of the claim is not.**

The test had to be *differential*, because humans book round numbers — 7, 14, 21 and 28 spike in every
corridor, for nobody's employer's sake. So the question is whether 30 is conspicuous in the labour
corridors **relative to each corridor's own round-number baseline**.

| corridor | excess @30 | excess @14 (control) | ratio | share of trips at 28–32 nights |
|---|---|---|---|---|
| **Gulf** (DXB/RUH/DMM/DOH) | **2.21** | 1.58 | **1.40** | **19.11%** |
| East Asia (HKG/TPE) | 2.34 | 1.79 | 1.31 | **1.93%** |
| Asian tourist hubs | 1.83 | 1.73 | 1.06 | 1.50% |
| US/Canada/Australia | 1.59 | 1.78 | 0.89 | 11.28% |
| Domestic | 1.19 | 1.22 | 0.98 | 0.79% |

1. **Gulf: confirmed, and strongly.** It is the only corridor where the one-month window holds *more*
   traffic than the two-week window (19.1% at 28–32 vs 8.5% at 12–16 — ratio 2.25; every other corridor
   is ≤0.60). The excess is spread over 29–30–31 (2.07 · 2.21 · 2.15), which is what a mandated month
   plus travel-day slop looks like, not a single-day artefact.
2. **"East Asia hubs": refuted — and actively harmful.** HKG/TPE show a sharp *ratio* at 30 but on
   almost no mass (1.93% of trips, indistinguishable from tourist hubs). Grouping them with the Gulf
   drags the discrimination **below chance**: AUC **0.375** combined vs **0.676** Gulf-only.
   **Row 21's `[Middle East / East Asia Hubs]` bracket must be narrowed to the Gulf.**
3. **45 nights: null.** Gulf excess @45 is 1.34 against its own 1.58 control — *below* baseline. The
   SME's "~30 **or ~45**" is half right.
4. **Not two populations — one gradient.** Density per night falls monotonically (6.85 → 2.66 → 2.18 →
   1.49 → 0.82 %/night). There is no valley between a "family visit" mode and a "worker" mode, so
   **no cut point produces a clean split.** The rule is a tilt, which is exactly how the SME graded it
   (*moderate / leans toward*) — so encode it as a soft prior, never a hard boundary.
5. **Supporting evidence is monotone and clean.** Within the current Balikbayan/VFR bucket, Gulf share
   rises 1.96% → 8.72% → **28.09%** → 34.49% across the <14 / 14–27 / 28–45 / 46+ bands, while group
   rate falls 6.74% → 0.69% → 0.45% → 0.25%. Longer stays really are more Gulf and more solo.
6. **One confound survives.** Published fares carry maximum-stay conditions, commonly one month. Excess
   @30 falls monotonically with value tier (2.01 at tier 1 → 1.19 at tier 7) — but so does excess @14
   (1.80 → 1.20), so the *ratio* is flat and tier is not specifically manufacturing the 30-spike. A
   **Gulf-specific** one-month fare rule would still reproduce this exactly. Resolving it needs
   `FarebasisCode`, which is in their data dictionary and which **we do not currently ingest**.

**What it's worth:** AUC **0.676** on a corridor proxy, against the ~coin-flip the current single-bit
rule gives. Not a solved boundary — a materially better one, on a genuinely independent axis.

---

## 4. Field coverage — what we can evaluate today

Across the 39 new rows:

| Field they used | Rows | Have it? | Our column |
|---|---|---|---|
| **StayPattern** | **23** | ⚠️ **derivable, not built** | — (see below) |
| PurchaseLeadTime | 14 | ✅ | `lead_days` |
| OperatingCabinClass | 12 | ✅ | `any_premium` / `any_business` |
| Farebrand | 11 | ✅ | `max_tier` / `min_tier` (1–7 ladder) |
| Isroundtrip | 11 | ✅ | `round_trip` |
| TripOD (named airports) | 10 | ⚠️ needs a **route-theme lookup** |`trip_origin`/`trip_dest`, `dest_region` |
| DepartureDate → `Month()` | 5 | ✅ | `dep_month` — **but see §6** |
| Booking Type = Group | 7 | ✅ | `is_group` — **but see §5** |
| Age | 3 | ⚠️ international bookings only | `age` / `age_known` |
| Channel | 2 | ✅ | `channel`, `sea_crew` |
| CountryCodeOfIssue | 2 | ✅ | `issue_country`, `foreign_issue` |
| DepartureDate → `DayOfWeek()` | 2 | ⚠️ **derivable, not built** | — |
| is_nonstop / OperatingCarrierCode | 1 | ✅ | `connecting` |
| **PaxCount > 10** (row 46) | 1 | ❌ **not obtainable** | sectoral pax count is always 1 |

### The three build items

1. **`stay_nights`** — 59% of the new rules need it and it is **not in `pal_features_booking.parquet`**.
   It is derivable (outbound departure → return departure, from coupon dates we already hold):
   **9,787,386 round-trip bookings, 42.7% of the book, computable on 98.8% of them.** Median 5 nights.
   ⚠️ Defined only for round trips — and *"is it defined"* is the `round_trip` rule bit, so it needs the
   same per-comparison admissibility handling as `dest_region`/`issue_country`.

2. **`dep_dow`** — trivial from `departure_date`. Two rules (39, 42) need it, and both encode the same
   real pattern: corporate departs Mon/Tue, leisure departs Fri/Sat.

3. **Route-theme lookup** — the SME named 26 specific `TripOD` codes across five themes. We currently
   hardcode only `JED`/`MED` as `pilgrimage_dest`. Extend `src/build_airport_ref.py`:

   | Theme | Codes given | Currently |
   |---|---|---|
   | Catholic pilgrimage | FCO, TLV, CDG *(Lourdes)*, LIS *(Fatima)* | ❌ missing |
   | Hajj/Umrah | JED, MED | ✅ have |
   | Gulf/East-Asia labour | DXB, RUH, DMM, DOH, HKG, TPE | partial — via `dest_region` |
   | Asian tourist hub | BKK, SIN, ICN, NRT | ❌ missing |
   | Domestic leisure endpoint | MPH *(Boracay)*, PPS *(Palawan)*, USU *(Coron)*, IAO *(Siargao)* | ❌ missing |
   | Premium holiday | HNL, SYD, CTS, MEL | ❌ missing |

   ⚠️ **Correction after measuring (17 Aug).** I first wrote that the missing Catholic hubs mean *"every
   Catholic pilgrimage in the book is currently mislabelled"* — true, but the volume makes it nearly
   irrelevant: **FCO 4,379 · TLV 16,990 · CDG 5,408 · LIS 1,447 = 28,224 trip endpoints total**, against
   70,650 for JED/MED. PAL barely serves these as trip endpoints. Worth adding for correctness; **not**
   worth describing as a significant miss. See the rule-level consequence in §4a below.

---

## 4a. Usability, measured — `src/probe_constraint_coverage.py`

All 39 rules were transcribed to SQL and counted against the full 22.9M-booking population
(`outputs/constraint_coverage/summary.md`, per-rule CSV in `rules.csv`). "Usable" is three questions:
can we evaluate it · on how much of the book · does it fire on enough volume to matter.

**Result: 29 usable · 9 fire too thin to act on · 1 unimplementable.**

### The nine that fire too thin (<0.05% of the book, ~11k bookings)

| row | segment | fires | why |
|---|---|---|---|
| 22 | Pilgrimage | **29** | Catholic hubs × group × age ≥ 50 — three thin filters multiplied |
| 24 | Pilgrimage | **3** | business cabin × ≤4 nights × JED/MED/TLV |
| 25 | Pilgrimage | 349 | lead ≥ 90 × religious hub × round trip |
| 23 | Pilgrimage | 656 | Mar/Apr × FCO/TLV |
| 51 | Intl. Student | 3,907 | age 18–26 × stay ≥ 90 — age is international-only |
| 48 | Ultra Wealthy | 5,325 | premium × group × round trip |
| 31 | Prem Bleisure | 6,307 | premium × group |
| 45 | MICE | 6,792 | group × mid-tier × SIN/NRT/BKK |
| 29 | Prem Bleisure | 9,979 | premium × 5–14 nights × HNL/SYD/CTS/MEL |

**All four Pilgrimage rules are in this list.** The segment the SME wrote most confidently about is the
one we can least act on — not because the reasoning is wrong, but because the routes are thin and the
conditions are conjunctive. Each extra `AND` multiplies a small share by another small share.

### ⚠️ The transcription trap — the sheet's route notation is backwards

The SME wrote OFW routes as `TripOD IN ('MNLDXB', 'MNLRUH', …)`. But **Gulf round trips overwhelmingly
start in the Gulf, not Manila: 260,216 vs 26,195 — 9.9× more.** A worker based in Riyadh flying home has
`TripOD = RUHMNL`. Their own flagship rule (row 21) names the wrong direction:

- read literally: **5,166** bookings
- direction-agnostic: **118,841** bookings — **23× more**

Transcribing the workbook verbatim would have silently gutted its single best rule. Every route-named
rule needs a direction decision at intake, and the answer is not always "as written" — row 18 (a worker
*leaving* for the job, one-way) genuinely is MNL→Gulf and fires healthily on 349,445.

### The scope ceiling nobody wrote down

- **26 of 39 rules cite stay length**, which exists only for round trips — **42.7% of the book**. Those
  rules are structurally silent on the other 57%.
- **3 rules cite age.** `age_known` covers 37.6% overall but only **0.98% of domestic bookings**
  (129,023 of 13.2M). **Every age rule is dead for domestic travel** — which is what was asked for.

### Two rules are very large levers

- **Row 34** (Prem Bleisure `cannot_be` tier ≤ 2) vetoes **63.1% of the entire book** in one line, at
  confidence *moderate*. Sound, but it is not a minor tilt — it must land in `soft` (§2), not `hard`.
- **Row 38** (Corporate `cannot_be` stay ≥ 8) removes **33.5% of round trips**. Also *moderate*.

### One rule cannot be implemented

**Row 46** — *MICE cannot be `OperatingCabinClass == 'J'` if Pax Count > 10*. Sectoral passenger count is
always 1 in the extract; the SME acknowledged this themselves in row 9. Without a PNR-level party size we
cannot evaluate it. **Return to sender**, or ask whether the PNR group indicator plus a group-fare booking
class can stand in.

---

## 5. Where the rules conflict with each other

These are not transcription problems. They need an SME decision.

### 5.1 Six segments are all claiming `is_group` — and one of them claims it absolutely

| Row | Segment | Group condition | Verdict |
|---|---|---|---|
| 9 *(our seed)* | Family | `Booking Type == 'Group'` | **Must Be** |
| 22 | Pilgrimage | Group + Europe/Holy-Land OD + Age ≥ 50 | leans |
| 31 | Premium Bleisure | Group + cabin J/W | leans (weak) |
| 41 | Last-Minute (Spontaneous Group) | Group + lead ≤ 5 + round trip | leans |
| 44, 45 | MICE | Group + lead ≥ 45 / Flex-Value fares | leans |
| 48 | Ultra wealthy leisure | Group + J/W + round trip | leans |

**A `must_be` on Family pre-empts all five others.** Our current waterfall already does exactly this —
`WHEN is_group THEN 'Family'` sits at priority 8 and swallows every group booking that survives to it.
Row 9 was our own seeded guess and the SME let it stand at `Likely`, but their own subsequent rows
contradict it six ways.

**Recommendation:** demote row 9 from `must_be` to a soft lean. `is_group` is the most over-subscribed
predicate in the entire constraint set and cannot be a deterministic assignment for anyone.

### 5.2 Ultra Wealthy Leisure and Premium Bleisure overlap with no tie-break

A booking with cabin `J`, lead 30+, stay 7–10 nights, round trip satisfies **both** row 47 (Ultra Wealthy,
*strong*) and row 30 (Premium Bleisure, *moderate*). Strength alone resolves it, but that is an accident,
not a designed boundary. The natural discriminator is spend — which the SME never referenced despite
`NetRevenue` being available. **Ask: what fare or revenue level separates "ultra wealthy" from "bleisure"?**

### 5.3 A clean composite they may not have noticed

Rows 17, 33 and 43 are three independent `certain` `cannot_be` rules — VFR, Premium Bleisure and
Last-Minute all excluded from *short-turnaround premium travel* — and row 35 makes Corporate a `must_be`
on the same territory. **Four SMEs' rules converge on one fence:** premium cabin + stay ≤ 3 + short lead
⇒ Corporate, definitively. That composite is more defensible than any of the four alone and should be
written up as a single named rule.

### 5.4 Booking-class `F` needs a date guard

Row 4 (our seed, confirmed `certain`): `BookingClass == 'F'` ⇒ Mabuhay Loyalist. The rationale even says
*"post-April 2026"* — but **the condition does not encode it**. In our extract, `F` means Mabuhay Award
only for tickets issued from Apr 2026; before that it meant *Economy, Non-revenue*. Implemented literally
this mislabels every pre-April-2026 non-revenue ticket as a loyalty redemption. Transcribe as
`is_award` (which already carries the guard), never as raw `BookingClass = 'F'`.

---

## 6. ⚠️ The cost nobody has priced: these rules eat our validation anchors

This is the item most likely to be missed, and it is the one that can quietly break the deliverable.

Our non-circular validation (Plan B, `src/validation_anchors.py`) rests on a hard contract: **a field
consumed by a rule cannot validate that rule.** After the leak audit, exactly **two** fields remain
unconditionally admissible:

```
TIER_A = ("dep_month", "n_bookings")
```

The new constraints spend both of our reserves:

| Anchor | Status before | What the sheet does | After |
|---|---|---|---|
| `dep_month` | **TIER_A** — one of two | Rows 16, 19, 23, 28, 50 all condition on `Month(DepartureDate)` | ❌ becomes a rule input → leaves TIER_A |
| `stay_nights` | earmarked **candidate Tier-A anchor** (Lever A: *"re-targeted, not discarded — test as a V1 construct-validity anchor"*) | 23 of 39 rules consume it | ❌ burned before it was ever used |
| `n_bookings` | TIER_A | untouched | ✅ survives — **alone** |

**If we transcribe the sheet as written, construct validity is left with one admissible anchor.** A
one-column validation matrix is not a validation matrix.

This is a genuine trade-off, not an argument against adopting the rules — better rules that are harder to
validate may still be the right call. But it must be a decision, not a side effect. Three ways out:

1. **Spend `dep_month`, protect `stay_nights`.** Adopt the seasonality rules; hold the stay-length rules
   as *reported diagnostics* rather than label inputs, keeping stay length as the Tier-A anchor Lever A
   recommended. Cheapest, and it preserves the validation story.
2. **Spend `stay_nights`, protect `dep_month`.** The inverse — take the OFW/VFR discriminator (§3, the
   highest-value item here) and drop the five seasonality rules, which are the weakest in the file
   (`moderate` at best, and Philippine peak-season effects are already visible in `peak_month`).
3. **Find new anchors.** `Isupgrade` is derivable and unused (`SoldOperatingCabinClass` is 0% null; sold ≠
   flown on 1.02% of coupons, ~369k) and **no rule in the sheet touches it**. `IsTourCode` and
   `IsFrequentFlyer` are in their data dictionary, also untouched by every rule. These are candidate
   replacement anchors and should be requested explicitly before we spend the ones we have.

**Option 2 + 3 is the recommendation, and the probe now prices it.** Spending `stay_nights` buys
**AUC 0.676 on the OFW↔Balikbayan boundary** (§3), against the coin flip the current single-bit rule
delivers — on an axis independent of everything the waterfall already uses. That is worth one anchor.
Keeping `dep_month` costs us the five seasonality rules, which the coverage probe shows are the file's
weakest anyway. Request `Isupgrade` / `IsTourCode` / `IsFrequentFlyer` as replacements in the same round.

⚠️ **Note what spending it does *not* buy.** The distribution is a gradient, not two populations (§3.4),
so stay length **improves the tilt; it does not create a clean boundary.** Do not let this be reported
internally as "the OFW/VFR problem is solved."

### And a prior result that constrains expectations

**Lever A already tested stay length as a clustering feature and it was null** — best Gower silhouette
0.323 → 0.319, mean delta −0.007, against a pre-registered bar of 0.45. Stay length discriminates
*descriptively* (median 3 · 4 · 5 · 10 · 13 · 33 nights across segments) but does not make clusters
geometrically separable.

**This does not invalidate the SME rules** — they are labelling rules, not clustering features, and
descriptive discrimination is exactly what a rule needs. But it does set the expectation: **adding
`stay_nights` will improve label quality, not cluster separation.** Nobody should promise PAL that the
continuum finding changes because stay length arrived.

---

## 7. What fits where — and what blocks it

### Fits now, no decisions needed

| Item | Where |
|---|---|
| Catholic pilgrimage hubs (FCO/TLV/CDG/LIS) | `src/build_airport_ref.py` — extend `pilgrimage_dest` beyond JED/MED |
| Domestic leisure endpoints (MPH/PPS/USU/IAO) | same file, new theme column |
| `dep_dow` feature | `src/features_real.py` |
| Row 34 re-filed as soft, row 9 conflict logged | `data/constraints/*.csv` |
| §5.3 composite fence (premium + short stay + short lead ⇒ Corporate) | new hard rule, `certain`, four-way SME agreement |
| §3 distributional test — is there a 30/45-night spike in the Gulf corridors? | one probe over `pal_features_booking.parquet` |

### Blocked on a decision — ✅ RESOLVED 17 August 2026

| # | Decision | Outcome | Rules unblocked |
|---|---|---|---|
| 1 | Anchor trade-off — spend `dep_month` or `stay_nights`? | **Spend `stay_nights`, keep `dep_month`.** The 5 rules whose primary claim is departure month are **withdrawn** (S02, S10, S12, S16, S20); S38 rewritten without its month clause. `src/check_constraints.py` now *fails* if any active rule reads `dep_month`, so the decision is enforced rather than remembered. Request `Isupgrade` / `IsTourCode` / `IsFrequentFlyer` as replacement anchors. | ~23 |
| 2 | Are MICE / Ultra Wealthy Leisure / Intl. Student real segments? | **Yes — approved, taxonomy goes 10 → 13.** Added to `SEG_APPROVED` in `src/pal_colors.py` with colours; deliberately **not** in `SEG_ORDER`, because the waterfall does not emit them yet. | 9 |
| 3 | Is their "Leisure" our `Budget/Adventure`? | **Yes — a naming difference.** Mapped in place; **no rename**, so the palette, Power BI dimension, personas and existing PAL slides are untouched. | 4 |
| 4 | Does Last-Minute stay a segment? | **No — it becomes a flag.** It describes a booking, not a traveller. Sized below; the waterfall change is pending. | 4 |
| 5 | Demote Family's `must_be` on `is_group`? | **Demoted** (S31, now `contested` at `weak`). Two narrower questions go back to RM Domestic — see §5.1. | 6 |

### What decision 4 costs — measured, not assumed

Removing the Last-Minute branch redistributes its 2,945,686 bookings **exactly** as
`rule_confidence.py` predicted: **84.1% (2,476,607) to `Budget/Adventure`**, 15.9% (469,079) to
`Unassigned`. Nothing else moves.

| | before | after |
|---|---|---|
| `Budget/Adventure` | 9,037,176 | **11,513,783** (+27%, and **50.3% of the whole book**) |
| `Unassigned` | 2,194,061 | 2,663,140 (+21%) |
| `Last-Minute` | 2,945,686 | 0 — becomes a flag |

**The flag is strictly more informative than the segment was.** As a segment it caught only bookings
that fell through eight higher-priority rules: 2.95M. As a flag it applies wherever `lead_days <= 3`:
**4,411,666 bookings (19.26%)** — including 864,292 OFW/Migrant, 315,333 Corporate and 196,364
Balikbayan/VFR that were short-lead all along and invisible as such. **That is a 50% gain in visible
short-lead volume**, and it is the strongest argument for the change.

⚠️ **But it concentrates half the book into one segment.** `Budget/Adventure` at 50.3% is not a useful
unit for targeting. This re-opens decision 3 from the other end: PAL approved *Ultra Wealthy Leisure*
at the top of a leisure ladder while the bottom rung swells to half the population — so the missing
**middle rung** is now the live taxonomy question, and worth raising before the waterfall change ships.

### Go back to the SME

- **Row 46 is unimplementable** — no PNR party size. (§4)
- **The Power BI wishlist sheet is empty.** That was half the ask and nobody filled it in.
- **Four segments got no input:** Mabuhay Loyalist, Family, Budget/Adventure, Digital Nomad.
  Digital Nomad especially — it is the one segment in the requirement we have never implemented, and our
  own seeded row 13 is marked *weak / pending SME input*. It came back untouched.
- **The ask was for domestic constraints; the answer is mostly international.** Of 39 rows: **1** names
  domestic routes (row 27), **14** name international corridors or international-only concepts, and 24
  are route-agnostic. Three of the new segments (Intl. Student, Catholic Pilgrimage, OFW) are inherently
  international. Usable — but the domestic-specific ask is substantially unanswered, and two fields the
  domestic rules would need are weakest there: `Age` is populated for **international operations only**,
  and `stay_nights` is undefined for one-ways, which is most of the domestic point-to-point book.
- **Ask for `Isupgrade`, `IsTourCode`, `IsFrequentFlyer`** as replacement validation anchors (§6, option 3).
- **Ask for the Ultra Wealthy / Premium Bleisure spend threshold** (§5.2).

---

## 8. Suggested order

1. ~~**Probe first, transcribe second.**~~ ✅ **Done 17 Aug** — `src/probe_stay_length.py` and
   `src/probe_constraint_coverage.py`. Gulf claim confirmed (AUC 0.676), East-Asia grouping refuted,
   45-night claim null, 29 of 39 rules usable, and the route-direction trap caught before it cost us
   23× the volume on the best rule.
2. ✅ **Done 17 Aug — features built.** `stay_nights`, `dep_dow`, `turn_dest`, `route_theme` and
   `any_cabin_j` are in `pal_features_booking.parquet`; route themes in `data/reference/route_theme.csv`.
   Methodology v1.7. **The waterfall is untouched, which is what keeps the anchor decision open.**
   A pre-existing reproducibility defect surfaced and was fixed along the way — coupons were ordered on
   a non-unique key, so `round_trip` flipped on ~20 bookings between identical runs.
3. ✅ **Done 17 Aug — rules transcribed.** 15 hard + 42 soft in `data/constraints/`, with row 21
   narrowed to the Gulf and made direction-agnostic, rows 34 and 38 demoted from `cannot_be` to soft,
   row 9 demoted from `must_be`, and the nine thin rules marked `too_thin` rather than dropped.
   `src/check_constraints.py` validates every condition against the live feature table and **found three
   errors during authoring** — a stale count, a mis-parsed condition, and a rule 2.3× larger than
   recorded because our own probe had matched only the outbound direction. Still **nothing enforced.**
4. **Take decisions #2–#5 to PAL** as a single taxonomy conversation, not five separate ones. Bring the
   coverage table: three of the proposed new segments rest largely on rules that fire on <10k bookings.
5. **Return to RM Domestic in one note:** the route-direction problem (their `MNLxxx` notation vs the
   9.9× larger inbound flow), row 46's missing party size, the four thin Pilgrimage rules, the
   `[Middle East / East Asia Hubs]` bracket, the empty Power BI sheet, and the four untouched segments.
6. **Request `FarebasisCode`** — it is the only way to close the fare-rule confound on the 30-night
   finding (§3.6), and it is already in their own data dictionary.

---

*Companions: `data/constraints/README.md` (the ask) · `docs/methodology.md` §Stage 3, §Plan B ·
`docs/knowledge-base.md` §15 · `docs/continuum-levers-plan.md` Lever A*
