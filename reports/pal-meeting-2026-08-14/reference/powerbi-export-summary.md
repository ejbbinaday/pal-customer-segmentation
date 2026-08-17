# Power BI export — preliminary segmented fact table

## What this is

Coupon-grain fact table with the rule-based `CustomerSegment` joined on from booking grain. `CustomerSegment` is the **preliminary proxy segmentation** — validated against the proxy rules themselves (circular) until SME labels land. See `docs/methodology.md`.

## Outputs

| Output | Rows | Size | Use for |
|---|---|---|---|
| `detail/fact_coupons/` | 38,116,259 | 1432.4 MB | only for Age / UniqueID |
| `model/fact_flight/` | 20,629,605 | 463.9 MB | **full dashboard — load this** |
| `model/fact_dashboard.parquet` | 2,110,606 | 30.4 MB | fast summary visuals |
| `model/dim_date.csv` | 1,826 | — | mark as Date table for YoY / 12-mo trend |
| `model/dim_segment.csv` | 11 | — | **persona cards** + segment colours, penalty weights, caveats |
| `model/scorecard_segment_month.csv` | 1,835 | — | **per-segment scorecards** — segment × travel month, additive |
| `qa/sample_100k.csv` | 100,000 | — | build + validate DAX first |
| `START-HERE.md` | — | — | **read this first** |

## Per-segment scorecards — `model/scorecard_segment_month.csv`

Built for exactly this job. Grain is **segment × travel month**, plus only the flags a scorecard has to filter on (`IsInternational`, the two completeness flags, and the `IsRefund` / `IsAward` / `IsNonRev` exclusions). A few hundred rows, so you can open it in Excel and check totals before writing a single measure. Relate `scorecard_segment_month[CustomerSegment]` → `dim_segment[Segment]` and `[TravelMonth]` → `dim_date[Date]`.

**Every numeric column is additive: `Coupons`, `Bookings`, `PaxCount`, `NetRevenue`, `NetFare`.** Sum them at any level and the answer is right.

**⚠️ There are no percentages, shares or ratios in this file, and that is deliberate — do not add any.** A stored share is only correct for the filter context it was computed in; the moment the report slices to one region or one month it is silently wrong and nothing visibly breaks. Write them as measures instead:

```dax
Bookings = SUM ( scorecard_segment_month[Bookings] )
Net Revenue = SUM ( scorecard_segment_month[NetRevenue] )
Rev per Booking = DIVIDE ( [Net Revenue], [Bookings] )
Segment Share of Bookings =
    DIVIDE ( [Bookings], CALCULATE ( [Bookings], REMOVEFILTERS ( dim_segment ) ) )
Bookings LY = CALCULATE ( [Bookings], SAMEPERIODLASTYEAR ( dim_date[Date] ) )
```

**Three things that will otherwise produce a wrong scorecard:**

1. **`Bookings` is `sum(IsPrimaryCoupon)`, not a distinct count** — so it stays additive. Never replace it with `DISTINCTCOUNT`.
2. **Filter `IsCompleteTravelMonth = TRUE` on every trend and YoY tile.** Travel months past the extract boundary are still-filling forward book, not demand — an unfiltered trend draws a **fake cliff**. For full-year comparisons use `IsCompleteTravelYear`.
3. **Exclude `IsRefund` / `IsNonRev` / `RevMissing` from commercial tiles** (and usually `IsAward`, whose revenue is taxes only). They ship as flags rather than being pre-filtered so your totals can still reconcile to the full extract. **Every flag in this file is guaranteed non-NULL** — they are coalesced to FALSE on write, because a NULL would make `IsRefund = FALSE` silently drop those rows and quietly break reconciliation. The ~542 bookings whose refund status is genuinely unknown are all `RevMissing = TRUE`, so they stay identifiable.

This file is **asserted to reconcile to the fact table on every build** — coupons and bookings must match exactly or the export fails. Verified this run.

**There is no model-accuracy or recall KPI in this export, on purpose.** Per-segment recall needs SME ground-truth labels, which have not landed yet; every accuracy figure computable today is measured against the rules that produced the labels, i.e. circular. `dim_segment` carries `PenaltyWeight` and `RevenueAtRiskPerError` if you want to build a *cost-weighted risk* tile, but **do not build an accuracy gauge** — there is no honest number to put in it.

## Persona cards — `model/dim_segment.csv`

One row per segment, joined on `Segment` = `CustomerSegment`. **Step-by-step build recipe for the cards — which visual, which fields, in what order — is in `START-HERE.md` §3b.**

⚠️ **The `Profile*` columns are whole-population and whole-period: they do NOT respond to report slicers.** Live, filter-aware numbers come from measures over `scorecard_segment_month` instead. Never put the two side by side unlabelled — a card showing a filtered `[Bookings]` next to an unfiltered `ProfileMedianLeadDays` gives the reader no cue that only half of it moved when they sliced. Every row carries a `ProfileScope` caption for exactly this purpose, and the `Profile` prefix also keeps `Bookings` meaning one unambiguous thing in the model.

Three kinds of column, and the distinction matters when someone asks *how do you know*:

- **Measured** (`Profile` prefix: `ProfileMedianLeadDays`, `ProfileRoundTripPct`, `ProfileInternationalPct`, `ProfilePremiumCabinPct`, `ProfileConnectingPct`, `ProfileGroupBookingPct`, `ProfileMedian`/`ProfileAvgRevenuePerBooking`, `ProfileAvgCouponsPerBooking`, `ProfileTopDestinationRegions`, `ProfileModalChannel`, `ProfileModalIssueCountry`, `ProfileBookings`, `ProfileBookingSharePct`) — recomputed from the booking table on every build, at **booking grain** so multi-coupon segments are not over-weighted.
- **Editorial** (`PersonaName`, `PersonaHeadline`, `WhyTheyFly`, `WhatTheyWant`, `WhatNotToDo`) — written by the project team. Motivation cannot be measured from a booking extract; these are informed inference and must not be presented as findings.

**`Trust` and `DataCaveat` are not optional decoration — put them on the card.** Persona cards persuade, so a card reading *Mabuhay Loyalist · 0.03% of bookings* invites the conclusion that the loyalty programme is irrelevant, when the truth is that we cannot see it (no loyalty-tier field; award redemption is the only signal). Same for `Family`, which means *ticketed as a group*, not *is a family*.

`SegmentColorHex` carries the project palette (`src/pal_colors.py`) so Power BI, the Python figures and the slide deck all colour a segment identically. `PenaltyWeight` and `RevenueAtRiskPerError` are **PAL's own estimates** from the requirements document, in pesos — unlike the extract's revenue columns, whose unit is undocumented.

Filter `IsModelledSegment = FALSE` out of commercial visuals — it flags `Unassigned` (a real gap awaiting a PAL definition) and `Excluded (non-revenue)` (staff/industry travel, present only so totals reconcile).

**Reconciliation:** cleaned coupons **38,116,259** → exported **38,116,259** (match ✅). The join adds no rows and drops none.

## ⚠️ Data completeness — read before building any trend visual

The extract has a hard boundary at **2026-07-21** (last flown departure). Travel months after **June 2026** are still-filling forward book, not demand: Sep-2026 holds ~22% of a mature month's coupons purely because those bookings have not been made yet. A 12-month trend that includes them shows a **fake cliff**.

- **Default every trend/YoY visual to `IsCompleteTravelMonth = TRUE`.**
- **`IsCompleteTravelYear = TRUE` only for 2025** — 2024 starts in May (8 months) and 2026/2027 are partial, so an unfiltered full-year YoY compares 12 months against 8.
- `DataAsOfDate` carries **2026-07-21** on every row so the boundary is visible in the model.

| complete_month   |   coupons |   pct | first_month         | last_month          |   rev_musd |
|:-----------------|----------:|------:|:--------------------|:--------------------|-----------:|
| True             |  34857779 | 91.45 | 2024-05-01 00:00:00 | 2026-06-01 00:00:00 |     5606   |
| False            |   3258480 |  8.55 | 2026-07-01 00:00:00 | 2027-05-01 00:00:00 |      613.3 |

## Grain & booking identity

- **38,116,259** coupons across **22,924,577** bookings (1.66 coupons per booking).
- `IsPrimaryCoupon` is TRUE on exactly **22,924,577** rows — one per booking (✅ matches the booking count — no hash collisions).
- **Booking-level measures:** filter `IsPrimaryCoupon = TRUE` rather than DISTINCTCOUNT over a composite key. **Coupon/sector measures:** use all rows.
- `Route` repeats per leg, so counting coupons by `Route` double-counts connecting journeys — use `BookingID` to dedupe.
- In both aggregates, **`Bookings` = `sum(IsPrimaryCoupon)`, not a distinct count.** A pre-aggregated DISTINCTCOUNT cannot be re-aggregated — summing it across groups would double-count bookings that span groups. Counting primary coupons is additive and exact: each booking contributes 1 to exactly one group, so the measure totals correctly at every level.

## Field dictionary

| Field | Source |
|---|---|
| `CustomerSegment` | model output (booking grain) |
| `PaxCount` | passthrough — ⚠️ *sectoral* count, ≈always 1, NOT party size |
| `NetRevenue` | passthrough — V1 `Revenues w YQ` = base fare + YQ surcharge |
| `NetFare` | passthrough — V1 `Net Fare` = total base fare, EXCLUDES YQ |
| `DepartureDate` | passthrough |
| `DateOfIssuance` | passthrough |
| `CurrentCouponStatus` | passthrough — F = flown, O = open |
| `DaysBeforeMonthEnd` | passthrough — ⚠️ departure-month metadata, NOT a snapshot; cannot drive pickup |
| `OnlineOD` | passthrough — PR-operated O&D |
| `TripOD` | passthrough — full journey incl. interline |
| `Sector` | passthrough — the single flown leg |
| `OperatingFlightNumber` | passthrough |
| `OperatingCabinClass` | passthrough (nulls → 'Unknown') |
| `OperatingCarrierCode` | passthrough — ⚠️ constant 'PR'; dead filter |
| `is_nonstop` | passthrough — 1 nonstop / 0 connecting |
| `BookingType` | passthrough — Group / Non-Group |
| `Channel` | passthrough — V1 `Channel Category` (nulls → 'Unknown') |
| `Age` | passthrough — 57% NULL by design (international ops only) |
| `UniqueID` | passthrough — customer key (anonymised) |
| `CountryCodeOfIssue` | passthrough |
| `POO` | passthrough — point of origin (airport) |
| `Farebrand` | **derived** — V1 ladder + date-dependent F/G award rule |
| `BookingID` | **added** — surrogate booking key = hash(UniqueID, DateOfIssuance) |
| `CouponNumber` | **added** — leg identity within the booking (Stage C passthrough) |
| `IsPrimaryCoupon` | **added** — exactly one TRUE per booking; filter on it for booking-level measures |
| `BookingCoupons` | **added** — legs in this booking (Stage F) |
| `DataAsOfDate` | **added** — extract boundary: last flown departure |
| `IsCompleteTravelMonth` | **added** — FALSE = still-filling forward book; default every trend visual to TRUE |
| `IsCompleteTravelYear` | **added** — FALSE for the partial 2024 start and the 2026/2027 forward tail |
| `CustomerDominantSegment` | added — customer grain |
| `DestRegion` | **added** — route region (Stage F) |
| `RoundTrip` | **added** — booking returns to origin (Stage F) |
| `IsInternational` | **added** — Stage F |
| `TravelMonth` | added — Travel Month filter |
| `IssueMonth` | added — on-hand timing |
| `LeadTimeDays` | added — departure − issuance; **use this for pickup** |
| `Route` | added — resolved per your rule |
| `NLegs` | **added** — legs on the ticketed journey |
| `IsConnecting` | **added** — complement of is_nonstop |
| `IsFlown` | **added** — boolean form of CurrentCouponStatus |
| `FarebrandValueTier` | added — 7 Business Flex … 1 Supersaver; NULL = award/group/non-rev |
| `IsRefund` | added — negative money; exclude or net out in measures |
| `RevMissing` | **added** — revenue null or zero |
| `IsAward` | **added** — Mabuhay award redemption; exclude from revenue |
| `IsNonRev` | **added** — staff/industry/comp; exclude from revenue |
| `IsGroupFare` | **added** — group-fare inventory |
| `AgeKnown` | **added** — filter age visuals on this instead of null-handling |
| `IsReissue` | **added** — issued after departure; negative lead time |

## Segment mix (the model output)

| segment                |   coupons |   pct |   bookings |      net_revenue |   rev_pct |   avg_fare |
|:-----------------------|----------:|------:|-----------:|-----------------:|----------:|-----------:|
| Budget/Adventure       |  13584390 | 35.64 |    9037176 |      6.72921e+08 |     10.82 |      43.85 |
| Balikbayan/VFR         |   7599599 | 19.94 |    2911290 |      1.80199e+09 |     28.97 |     173.98 |
| OFW/Migrant            |   5252311 | 13.78 |    3919216 |      1.22347e+09 |     19.67 |     193.48 |
| Unassigned             |   4310427 | 11.31 |    2194061 |      7.89475e+08 |     12.69 |     163.12 |
| Last-Minute            |   3875112 | 10.17 |    2945686 |      4.03313e+08 |      6.48 |      95.34 |
| Corporate              |   1699321 |  4.46 |    1001638 |      4.93751e+08 |      7.94 |     259.59 |
| Premium Bleisure       |   1040096 |  2.73 |     481666 |      7.24157e+08 |     11.64 |     634.7  |
| Family                 |    661804 |  1.74 |     370647 |      8.72386e+07 |      1.4  |     120.06 |
| Pilgrimage             |     68334 |  0.18 |      43617 |      1.76002e+07 |      0.28 |     233.93 |
| Excluded (non-revenue) |     15073 |  0.04 |      13127 |      4.66019e+06 |      0.07 |     308.19 |
| Mabuhay Loyalist       |      9792 |  0.03 |       6453 | 727403           |      0.01 |      64.53 |

## `NetFare` vs `NetRevenue` — the fare-basis confirmation you asked for

- Median `NetFare` **71.81** · median `NetRevenue` **82.62** · median difference (the YQ fuel surcharge) **7.11**.
- `NetRevenue >= NetFare` on **100.0%** of coupons.
- **Confirmed:** `NetFare` is the base-fare basis (**excludes** the YQ surcharge); `NetRevenue` = base fare + YQ. Use `NetFare` for **Avg Fare** and `NetRevenue` for revenue share / YoY — that matches your field mapping.
- **Caveat:** `NetFare` is negative on **0.101%** of coupons (refunds/ADMs).

## Exclusion flags — build commercial measures on these

A clean revenue measure filters `IsRefund = FALSE AND RevMissing = FALSE AND IsAward = FALSE AND IsNonRev = FALSE`.

|   refund_pct |   rev_missing_pct |   award_pct |   nonrev_pct |   group_fare_pct |   reissue_pct |
|-------------:|------------------:|------------:|-------------:|-----------------:|--------------:|
|        0.101 |             0.248 |       0.024 |        0.082 |            0.131 |         0.005 |

## Date dimension

`model/dim_date.csv` covers **1,826** days. Mark it as the Date table in Power BI. There are **two date roles** — `DepartureDate` (travel) and `DateOfIssuance` (sales). Model one active relationship (travel) and reach the other with `USERELATIONSHIP`, or load a second copy as a sales-date table. `IsCompleteTravelMonth` is repeated here so the filter works from either side.

## Known limitations

- **⚠️ `DaysBeforeMonthEnd` cannot drive LY-vs-CY pickup.** Verified: across all 37 departure months it takes exactly **one** distinct value per departure month, even though each month is sold across 13–15 different issue months. It is a deterministic function of the departure month against a *single* extract date — constant `-7` through Jun-2026, then stepping by month length. It carries **zero booking-timing information**. Use **`LeadTimeDays`** for booking-curve pickup ('on hand at ≤N days before departure'), which *is* LY-vs-CY comparable. A true snapshot anchor needs repeated dated extracts of the same departure months; this is one extract.
- **`PaxCount` is a *sectoral* count** (1 sector = 1 pax) — ≈always 1, **not party size**. Segment pax = coupon count; for party size use `BookingType = 'Group'`.
- **`OperatingCarrierCode` is constant `PR`** — the PR-operated filter is a no-op on this extract. Kept because it was requested; interline surfaces as `TripOD` ≠ `OnlineOD`.
- **`Age` is 57% NULL by design** (international operations only) — filter on `AgeKnown`; never show an unqualified average age, it is not missing at random.
- **Currency is undocumented.** Stage F established only that revenue is *plausibly* single-currency (7.3× median spread across 26 issue countries). Confirm with PAL before summing revenue across countries.
- **`is_nonstop`** is the one snake_case column (it was requested that way); everything else is PascalCase.
- **`Excluded (non-revenue)`** rows are coupons whose customer had *every* coupon non-revenue. Kept so totals tie to the full extract — filter them out of commercial measures.
- **`Unassigned`** is a real model state (no proxy rule matched), mostly PH-issued *outbound* international economy — a known taxonomy gap raised with PAL, not a data error.
- **`Mabuhay Loyalist` is 0.03% and `Digital Nomad` is absent** — both blocked on the missing `Loyalty status` field. Do not present them as populated segments.

