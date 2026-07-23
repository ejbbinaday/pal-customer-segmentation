# Real PAL Data — Cleaning · EDA · Feature Engineering Plan

Plan for taking the real coupon-level extract (`data/PAL-data/*.txt.gz`, 38,116,260 rows, 2024–2027)
from raw gz to a model-ready feature table for the **trip-purpose × value** segmentation.
Grounded in `outputs/profile_raw/summary.md` and the **authoritative data dictionary**
`data/PAL-data/DataDictionary.v1.xlsx` (sheets `Dictionary` + `Farebrand_relationship`), mirrored to the
tracked **`docs/data-dictionary.md`**. Companion to `docs/methodology.md` (the authoritative spec once
these stages are implemented in `src/`).

> **Dictionary provenance.** `DataDictionary.v1.xlsx` (V1) describes the **real** data and wins on every
> conflict. The older `data/raw/PAL_PNR_Synthetic_Data_1000-v2.csv` describes the 1,000-row **synthetic**
> set and is stale for the real extract — it wrongly called `UniqueID` a PNR and `CurrentCouponStatus`
> "ticketed/unticketed". Both are corrected below and verified against the data.

Toolchain: **DuckDB** for the heavy out-of-core work (the 38M rows never fully enter pandas);
**Parquet** (`data/interim/pal_parquet/`) as the fast intermediate; **pandas/sklearn** only on the
aggregated, model-grain table.

---

## 0. What the data + V1 dictionary tell us (constraints that shape the plan)

| Fact | Value | Implication |
|---|---|---|
| Rows / grain | 38.1M **coupons** (flight legs; 1 sector = 1 `Pax Count`) | must aggregate up before segmenting |
| `UniqueID` | 13.45M distinct — V1: **"Unique customer identifier"** | **customer key** (anonymised, 0 null). *Verified:* IDs span up to **1,162 days (~3.2 yr)**, 26% make >1 booking → tracks a person across bookings |
| Coupons per customer | mean 2.83, median 2, p95 8, max 771 | repeat behaviour is measurable; long tail = frequent flyers / agency / crew (see §1, §3) |
| `CurrentCouponStatus` | F 93.4% / O 6.6% — V1: **F = flown, O = open** | *Verified:* every future departure is `O`, every past is `F` (0 future-flown). Realised travel = flown coupons |
| Booking classes → **Farebrand** | 26 RBD letters map to 8 farebrands + non-rev/groups/award (§0a) | gives a proper ordinal **value ladder** — supersedes the ad-hoc `FARE_TIER` map |
| `OperatingCabinClass` | Y 94% / W 3% / J 3% — V1: J=Business, W=Prem-Econ, Y=Economy | economy-dominated; premium is rare & signal-rich |
| `OperatingCarrierCode` | 100% `PR` | **constant — drop** |
| `Age` | **57% NULL** — V1: DOB vs issuance, **"only international operations"** | **not missing-at-random** (structural: intl only, verified ~46% vs ~17% known) → `age_known` is itself a signal; never a primary clustering driver |
| `Gender` | **in V1 dict header list? no** — absent from real data | no gender features |
| `Pax Count` | ~always 1 — V1: **"sectoral pax count, 1 sector = 1 pax"** | by design, not party size → group signal comes from `BookingType` / Groups farebrand |
| `Revenues w YQ` (V1 `NetRevenue`: base fare + YQ fuel surcharge) | median 82.6, p99 1,150, max 290k; 7,385 <0, 92,867 =0, 1,771 null | total value measure; heavy right skew → log/robust; repair neg/zero |
| `Net Fare` (V1 `NetFare`: total base fare) | 38,442 <0; only 89 > revenue | negatives = refunds/ADMs; handle sign |
| `BookingType` (V1 `Booking Type`: Group/Individual of a PNR) | Non-Group 97.4% / Group 2.6% | reliable group indicator |
| `is_nonstop` | 72% nonstop / 28% connecting | connection behaviour is a purpose signal |
| Channels (`Channel Category`) | 12 incl. **Sea Crew**, NDC, TMC, OTA; 90,898 null | Sea Crew ⇒ maritime-crew segment; channel ⇒ purpose/value |
| Geography | `POO` = origin **airport** (V1 confirms); 1,386 (MNL 38%); `CountryCodeOfIssue` 223 (PH 62%, US 10%) | origin airport vs issue country ⇒ domestic vs OFW/diaspora split |
| `TripOD` vs `OnlineOD` | V1: TripOD includes OAL-operated (codeshare) sectors; OnlineOD is **PR-only** | use TripOD for full journey, OnlineOD for PR-network behaviour |
| Compound cols | `TripOD_Path` "AAE-ALG ALG-DOH …", `TripOD_Coupons` "9-10-11-12", `*_CouponStatus` "Z-Z-F-F" | space/hyphen-delimited "pairs for a path" → must parse |
| `DaysBeforeMonthEnd` | −7…315 — V1: days before end of **travel month**, a revenue-accounting snapshot for YoY same-point comparison; >month-length values are accounting overrides | **not a customer feature — drop from segmentation** |
| `PurchaseLeadTime` | V1 lists it as **"to be made in feature engineering"** = Flight Date − DateOfIssuance | build it (booking lead time) |
| Dates (UTC) | departure 2024-05-01 → 2027-05-31; issuance 2023-03-24 → 2026-07-20 | lead time & tenure both derivable |

### 0a. Farebrand & SME business rules (from V1 `Farebrand_relationship` + client)

Every booking class maps to a **farebrand** (fare product). This is the authoritative value ladder and
replaces the hand-rolled `FARE_TIER` in `features_v3.py`:

| Farebrand (value tier) | Booking classes | Treatment |
|---|---|---|
| Business Flex (7) | J, C, D | paid value ladder |
| Business Value (6) | I, Z | paid value ladder |
| Premium Economy (5) | W, N | paid value ladder |
| Economy Flex (4) | Y, S, L, M, H | paid value ladder |
| Economy Value (3) | Q, V, B, X | paid value ladder |
| Economy Saver (2) | K, E, T | paid value ladder |
| Economy Supersaver (1) | U, O | paid value ladder |
| **Business/Economy Non-revenue** | A, R (business); P (economy) | **staff/industry/comp — exclude from customer segmentation** |
| **Groups** | **G** — *only Apr-2026 onwards; before that G = Mabuhay miles* | group product (distinct from `BookingType`) |
| **Mabuhay Miles Award Redemption** | **F** — *only Apr-2026 onwards; before that F = Economy Non-revenue* | **loyalty signal, not a fare tier** |

**Time-dependent coding (critical).** The `F`/`G` meanings **flip at 2026-04-01**:
- **Award redemption (Mabuhay Loyalist signal)** = (`DateOfIssuance ≥ 2026-04-01` AND class `F`)
  **OR** (`DateOfIssuance < 2026-04-01` AND class `G`). *Verified counts:* 1,031 (post-F) + 8,121
  (pre-G) ≈ **9,152 award coupons across the full span** — far more coverage than the F-only rule.
- **Groups (booking-class level)** = `DateOfIssuance ≥ 2026-04-01` AND class `G` (49,821 coupons).
- Pre-Apr-2026 `F` (94) = economy non-revenue, **not** award.
- Applies to both `BookingClass` (flown) and `SoldBookingClass` (issued).

### 0b. Column renames vs the legacy synthetic dictionary (`...v2.csv`)

`Unique Identifier`→`UniqueID` (**customer**, per V1 — v2 wrongly said PNR); `PointofOrigin`→`POO`
(airport); `PaxCount`→`Pax Count`; `NetRevenue`→`Revenues w YQ`; `NetFare`→`Net Fare`;
`Group/Individual`→`BookingType`; `Channel`→`Channel Category`; `Gender` dropped.

---

## 1. Grain — coupon → booking → customer

`UniqueID` is a **customer** key (V1 + verified 3-yr spans). There is no explicit PNR id, so the
purpose-bearing "journey" must be reconstructed. Two candidate journey keys, *checked against the data*:

- Directional `TripOD` key (`UniqueID`×`TripOD_DepartureDate`×`TripOD_Path`): 33.7M rows but averages
  only **1.13 coupons** each — it treats an outbound and its return as two separate journeys, which
  fractures purpose (a return leg looks like a one-way).
- **Booking key = (`UniqueID`, `DateOfIssuance`):** **43% contain a 2-direction round-trip** (out+return),
  55% one direction — a far better proxy for one purchase decision / one purpose.

| Grain | Unit | ~N rows | Role |
|---|---|---|---|
| Coupon | one flight leg | 38.1M | raw input — aggregate up |
| **Booking** (`UniqueID`,`DateOfIssuance`) | one purchase ≈ PNR (groups round-trips) | ~23M | **primary feature row** — the purpose unit |
| **Customer** | `UniqueID` across bookings | 13.45M | **rollup layer** — frequency, tenure, value, loyalty |

**Approach (refines the "trip + customer rollup" decision).** Engineer at **booking grain**
(trip-purpose × value), keeping directional/leg detail as attributes; then roll up to **customer grain**.
Caveat: issuance date is an imperfect PNR proxy (same-day multi-bookings, reissues) — add a round-trip
pairing check (return origin = outbound destination, close dates) if EDA shows it matters.

> **Customer-rollup reality check:** only **26% of customers book more than once** (6.6% have 4+). So
> tenure / repeat-frequency / lifetime-value features are informative for that **minority**; for the 74%
> single-booking majority, customer ≡ their one booking. Loyalty rests on award flags + that 26%, not on
> deep histories. Honest, not fatal — state it in outputs.

> Scale note: ~23M bookings is still too many for HDBSCAN directly. Clustering fits on a **stratified
> sample** (200–500k, stratified by cabin × channel × region × season) and the fitted scorer labels the
> full set inductively (same pattern as `prototype_v3.py`).

---

## 2. Stage C — Cleaning (DuckDB, writes `data/interim/pal_clean/`)

1. **Deduplicate.** Check for exact duplicate coupons (same `UniqueID`, flight, dates, coupon #); dedupe.
2. **Flown vs open.** `CurrentCouponStatus` F = flown, O = open. Realised-behaviour features use **flown**
   coupons; keep open (future) coupons flagged for forward-looking demand. (Confirm the `E`/`Z` codes in
   the `TripOD_/OnlineOD_CouponStatus` path-pairs with PAL.)
3. **Farebrand & award decode.** Map booking class → farebrand (§0a); derive `award_ticket` and
   `is_group_fare` with the **date-dependent F/G rule**; tag **non-revenue** (A/R/P + era-specific F).
4. **Type & format repair** (mostly in Parquet build): timestamps from `.0000000`; money → float; BOM
   stripped (DuckDB handles it).
5. **Money repair.** Flag `rev_missing` (null 1,771 / zero 92,867) — don't treat 0 as cheap; tag
   `is_refund` (negative revenue 7,385 / negative `Net Fare` 38,442) and net them at customer grain;
   winsorize the extreme right tail (max 290k vs p99 1,150) for scaling, keep raw for reporting.
6. **Drop / quarantine.** Drop `OperatingCarrierCode` (constant) and `DaysBeforeMonthEnd` (accounting
   snapshot, not a customer feature). Quarantine the 2 junk `SoldOperatingCabinClass` rows (`K`, `nan`).
7. **Missingness policy.** `Age` structurally missing (intl only) → `age_known` flag + median impute,
   never a clustering driver. Cabin nulls (~1.5%) / channel nulls (0.24%) → "Unknown" level.
8. **Parse compound fields.** From `TripOD_Path` → `n_legs`, origin, final destination, connections;
   from `TripOD_CouponStatus` the per-leg flown pattern; reconcile `TripOD` (codeshare) vs `OnlineOD`
   (PR-only) vs `Sector`.
9. **Canonicalise geography.** Map `POO` airport → city/country/region; domestic-PH vs international;
   diaspora corridor (US/CA/AU/ME/EU/Asia) from `CountryCodeOfIssue` vs travel region.

Output: cleaned coupon Parquet + a data-quality report (`outputs/clean_report/`).

## 3. Stage E — EDA (DuckDB aggregates → matplotlib/seaborn on summaries)

Canonical palette (`src/pal_colors.py`); EDA runs on aggregates, not raw rows.

- **Univariate:** farebrand/value tier, cabin, channel, booking type, is_nonstop, POO/country/region,
  revenue (log), age (where known).
- **Temporal:** rows by departure & issuance month; **booking lead time**; seasonality (Dec, Holy Week,
  summer); day-of-week; **award-ticket volume over time** (watch the Apr-2026 coding change — don't read
  the jump as loyalty growth).
- **Route/network:** top ODs & sectors, domestic vs international, connection rates, hub reliance
  (MNL/CEB/DVO), codeshare (TripOD≠OnlineOD) share.
- **Value:** revenue by farebrand/cabin/channel/route; revenue concentration (Lorenz / top-decile).
- **Customer behaviour:** coupons/trips per customer, **tenure & repeat-purchase** distributions, the
  heavy tail (who has 100+ coupons — frequent flyer vs agency vs crew), one-time vs repeat mix.
- **Relationships:** cabin × channel × region cross-tabs; correlation heatmap (drives Tier-3 pruning).
- **Segment sanity:** how the 10 segments *could* surface (Sea Crew → maritime crew; award/repeat/business
  → Mabuhay Loyalist; group + leisure route → Family; US-issued economy round-trip → OFW/Balikbayan).

Output: `outputs/eda_real/` (figures + EDA summary).

## 4. Stage F — Feature engineering (booking grain, then customer rollup)

Mirrors the four v3 feature families (`src/features_v3.py`), rebuilt for real data.
Aggregation: **coupon → booking → customer**.

- **Value:** **farebrand value tier** (§0a, replaces `FARE_TIER`), cabin (Y/W/J), trip revenue & net
  fare (sum over legs), revenue-per-leg, refund flag, premium flag, log-revenue. Award/non-rev tickets
  carry little/no cash — score their value separately, never as "cheap". (Per-km/yield needs an external
  airport-coordinate lookup — **not in the data**; optional, only if we add a coords table.)
- **Loyalty (Mabuhay):** `award_ticket` (date-dependent F/G rule, §0a) **plus** customer-level repeat
  signals now possible — trips/yr, tenure, business/premium share, redemption count. Award seeds the
  segment; repeat behaviour broadens it.
- **Timing:** booking lead time, season/holiday flags, day-of-week, one-way vs round-trip, trip duration
  (days at destination), last-minute flag.
- **Product / route:** n_legs, nonstop vs connecting, domestic vs international, region/corridor, hub
  usage, distinct destinations, OD entropy, pilgrimage-route flags, long-haul flag, codeshare usage.
- **Party / demographic / channel:** `BookingType` group flag (+ Groups farebrand), channel category
  (self-service vs agency vs corporate TMC/NDC vs **Sea Crew**), age band + `age_known`, issue country
  vs travel region (diaspora). No gender.
- **Customer rollup:** trips/yr, tenure (first→last issuance), total & mean value, cabin mix, dominant
  purpose proxy, channel loyalty, domestic/intl ratio, award history.

**Segmentation method (settled 2026-07-23, evidence-based).** A mixed-type diagnostic
(`src/cluster_diagnostic.py`: LCA + k-prototypes, 60k sample) showed the base is a **continuum**
(BIC no elbow → no natural *k*) whose structure follows the rule axes, with only moderate
cluster–taxonomy agreement (ARI ≈ 0.2–0.34). So the **rule-based proxy waterfall is the PRIMARY
segmentation** (the 10 named segments), and **LCA is the refinement/validation layer** — used to
**sub-segment oversized groups** (esp. Budget/Adventure) into actionable sub-types and to validate the
axes. HDBSCAN is dropped for the real data (categorical-heavy, not density-separable).

Output: `data/interim/pal_features_booking.parquet` (+ customer variant) and a feature-profile summary.

> **Built & run 2026-07-23** (`src/features_real.py`): 22.9M bookings / 13.4M customers; guards passed
> (UniqueID cross-file valid; revenue single-currency 7.3× spread). Proxy seeds look sound — avg revenue is
> monotonic across segments ($53 Budget → $1,468 Premium Bleisure). **Follow-ups for the clustering stage:**
> Corporate proxy is thin (restrictive rule), Mabuhay Loyalist is award-only (enrich with repeat+premium at
> customer grain), and **Digital Nomad has no seed** — expected per §5; leave to Unassigned/clustering.

---

## 5. Segment feasibility — honest reality check

The 10 target segments are a **business taxonomy**; this anonymous data supports them **unevenly**.
Clustering is unlikely to recover all 10 cleanly, and (as in v3) validation stays **proxy-circular
until SME ground-truth labels arrive** (`data/labels/sme_sample.csv`).

| Segment | Signal in this data | Strength |
|---|---|---|
| Last-Minute | short booking lead time (`PurchaseLeadTime`) | **strong** — direct |
| Mabuhay Loyalist | award tickets (F/G rule) + repeat + premium | **good** (much improved) |
| Corporate | premium cabin + TMC/NDC channel + short lead + repeat | **good** |
| Budget/Adventure | Economy Saver/Supersaver + domestic leisure routes | **good** |
| OFW/Migrant | foreign `CountryCodeOfIssue` (38%) + economy + long-haul | **moderate** |
| Family | `BookingType`=Group (2.7%) + leisure route (Pax Count is useless here) | **moderate/weak** |
| Balikbayan/VFR | diaspora issue + round-trip to PH — **overlaps OFW**, hard to separate | **weak** |
| Premium Bleisure | premium cabin + leisure route + weekend timing | **weak** |
| Pilgrimage | route to religious destinations — needs a route lookup; limited PR network | **weak** |
| Digital Nomad | long stay + flexible + intl — hard to infer anonymously | **weak/uncertain** |

**Implication:** expect ~5–6 segments to emerge with reasonable confidence and 3–4 to be thin,
overlapping, or dependent on hand-built route/rule lookups. Plan for a **"Unassigned"/low-confidence
bucket** (already in `prototype_v3.py`) and set stakeholder expectations that the count/definition of
recovered segments is an output, not a guarantee. A small SME-labelled sample would de-risk this most.

---

## Decisions (signed off 2026-07-22; grain/status reinstated after V1 dictionary)

1. **Model grain → booking + customer rollup.** `UniqueID` is a customer key (V1 + verified 3-yr spans).
   Refined after checking the data: the purpose unit is a **booking** = (`UniqueID`,`DateOfIssuance`),
   which groups round-trips (43% are 2-direction), *not* the directional `TripOD` key (1.13 coupons each);
   then roll up to customer for value/loyalty. *(The interim "PNR-only, no passenger layer" note — from
   the stale v2 dictionary — is withdrawn.)*
2. **Coupon scope → flown drives behaviour, open kept flagged.** `CurrentCouponStatus` F = flown /
   O = open (verified). *(The interim "ticketed/unticketed" reading is withdrawn.)*
3. **Population → exclude all-non-revenue customers only** *(settled 2026-07-23 via EDA).* Drop the
   **12,306 customers (0.09%)** whose every coupon is non-revenue (staff/comp). **Keep** the heavy tail —
   EDA shows it is heterogeneous (crew/agency/corporate/genuine frequent flyers), i.e. real signal, not
   noise; Sea Crew is its own segment cue.
4. **Deliverable unit → booking primary + customer rollup** *(settled 2026-07-23).* Label each booking by
   trip-purpose×value; roll up a dominant-segment view per customer for CRM.
5. **Route lookup → we build it** *(settled 2026-07-23).* Curate a PH-airport + country/region map
   (`data/reference/airport_region.csv`) covering PAL's network; tail → 'Unknown'. Now **essential**, not
   optional: EDA A6 shows value is non-discriminative (~71% cheap economy), so domestic-vs-international
   route split is what separates domestic-budget from international-OFW/diaspora.
6. **Time window → full 2024–2027 span.** Use all data; account for uneven coverage (2024 starts May,
   2027 partial) and the **Apr-2026 F/G coding change** when reading trends.

*Last updated: 22 July 2026*
