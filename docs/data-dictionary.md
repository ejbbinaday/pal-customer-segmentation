# PAL Data Dictionary (real coupon-level extract)

**Authoritative** field reference for `data/PAL-data/*.txt.gz` (~38M coupon rows, 2024–2027).
Faithful mirror of the client's `data/PAL-data/DataDictionary.v1.xlsx` (git-ignored with the bulk data),
kept here so it is version-controlled and available on clone.

> This V1 dictionary supersedes the legacy `data/raw/PAL_PNR_Synthetic_Data_1000-v2.csv`, which describes
> the 1,000-row **synthetic** prototype and is stale for the real data (it mislabels `UniqueID` as a PNR
> and `CurrentCouponStatus` as "ticketed/unticketed"). See `docs/real-data-plan.md` for the reconciled
> plan and `docs/knowledge-base.md` §15 for verification notes.

## Sheet 1 — `Dictionary` (fields)

| Column Name | Description | Notes |
|---|---|---|
| DateOfIssuance | The date the ticket was issued | |
| POO | The airport point of origin of a ticketed itinerary | |
| CountryCodeOfIssue | The country code where the ticket was issued | |
| CouponNumber | The coupon number of a ticket | |
| CurrentCouponStatus | Tags tickets whether F (flown) or O (open) | At any point in time, a ticket can already be flown or still open |
| BookingClass | The booking class used when the ticket was **flown** | Booking class is a subset of farebrand; farebrands split into booking classes with different prices (e.g. Supersaver → O and U, priced differently) |
| SoldBookingClass | The booking class used when the ticket was **issued** | Booking class when the ticket was sold |
| SoldOperatingCabinClass | The cabin class used when the ticket was issued | |
| TripOD | Directional origin-destination pair including both **OAL-operated and PR-operated** sectors | |
| OnlineOD | Directional origin-destination pair including **only PR-operated** sectors | |
| Sector | The directional flight pair of a route | |
| DepartureDate | The departure date of a ticket | |
| DaysBeforeMonthEnd | Number of days prior to the end of the **travel month** | Revenue snapshot for like-for-like YoY comparison at the same days-before-month-end. DBME date can exceed the historical date only so accounting can edit/override revenue still needing correction |
| OperatingCarrierCode | The operating carrier of a ticket's flight | |
| OperatingFlightNumber | The operating flight number of a ticket's flight | |
| DepartureDateTime | The departure date and time of a ticket | |
| ArrivalDateTime | The arrival date and time of a ticket | |
| OperatingCabinClass | The cabin class used when the ticket was **flown** | J = Business, W = Premium Economy, Y = Economy |
| TripOD_DepartureDate | The departure date pairs for a Trip OD Path | Any `TripOD` field can refer to a part of the network operated by another carrier under a codeshare agreement |
| TripOD_Path | The sectors a passenger used for a Trip OD | |
| TripOD_Coupons | The coupon number pairs for a Trip OD Path | |
| TripOD_FlightSequence | The operating flight number pairs for a Trip OD Path | |
| TripOD_CouponStatus | The coupon status pairs for a Trip OD Path | |
| TripOD_OperatingCabinClass | The flown cabin class pairs for a Trip OD Path | |
| TripOD_BookingClass | The flown booking class pairs for a Trip OD Path | |
| OnlineOD_DepartureDate | The departure date pairs for an Online OD Path | Any `OnlineOD` field refers to a part of the network operated **only** by PAL |
| OnlineOD_Path | The sectors a passenger used for an Online OD | |
| OnlineOD_Coupons | The coupon number pairs for an Online OD Path | |
| OnlineOD_FlightSequence | The operating flight number pairs for an Online OD Path | |
| OnlineOD_CouponStatus | The coupon status pairs for an Online OD Path | |
| OnlineOD_OperatingCabinClass | The flown cabin class pairs for an Online OD Path | |
| OnlineOD_BookingClass | The flown booking class pairs for an Online OD Path | |
| is_nonstop | Nonstop indicator | 1 = non-stop flight, 0 = has stopovers |
| PaxCount | The **sectoral** passenger count of a ticket (1 sector = 1 pax count) | |
| NetRevenue | Total revenues based on base fare **and YQ surcharge** of a ticket | YQ is fuel surcharge |
| NetFare | Total base fare of a ticket | |
| Booking Type | Group/Individual booking indicator of a PNR | |
| Age | Computed as date of birth over the ticket issuance date | Only involves **international** operations (e.g. Manila → Los Angeles) |
| Unique Identifier | Unique **customer** identifier | |
| Channel | The sales channel where the ticket was issued | |
| PurchaseLeadTime | Number of days before the passenger's trip (Flight Date − DateOfIssuance) | To be made in feature engineering |
| Farebrand | Refer to `Farebrand_relationship` | To be made in feature engineering |

### Real-column name mapping
The delivered CSVs rename some dictionary fields: `POO`, `CountryCodeOfIssue`, `Pax Count` (=`PaxCount`),
`Revenues w YQ` (=`NetRevenue`), `Net Fare` (=`NetFare`), `BookingType` (=`Booking Type`),
`Channel Category` (=`Channel`), `UniqueID` (=`Unique Identifier`). `PurchaseLeadTime` and `Farebrand`
are **derived** (not shipped). `Gender` is not present in the real data.

## Sheet 2 — `Farebrand_relationship` (booking class → fare product)

Authoritative value ladder (used instead of any ad-hoc fare-tier map).

| Booking Class | Farebrand | Notes |
|---|---|---|
| J | Business Flex | |
| C | Business Flex | |
| D | Business Flex | |
| I | Business Value | |
| Z | Business Value | |
| A | Business, Non-revenue | staff/industry/comp |
| R | Business, Non-revenue | staff/industry/comp |
| W | Premium Economy | |
| N | Premium Economy | |
| Y | Economy Flex | |
| S | Economy Flex | |
| L | Economy Flex | |
| M | Economy Flex | |
| H | Economy Flex | |
| Q | Economy Value | |
| V | Economy Value | |
| B | Economy Value | |
| X | Economy Value | |
| K | Economy Saver | |
| E | Economy Saver | |
| T | Economy Saver | |
| U | Economy Supersaver | |
| O | Economy Supersaver | |
| G | Groups | **True only for tickets issued Apr 2026 onwards; previously = Mabuhay Miles** |
| P | Economy, Non-revenue | staff/industry/comp |
| F | Mabuhay Miles Award Redemption | **True only for tickets issued Apr 2026 onwards; previously = Economy, Non-revenue** |

### Ordinal paid-value tier (derived, for features)

7 Business Flex · 6 Business Value · 5 Premium Economy · 4 Economy Flex · 3 Economy Value ·
2 Economy Saver · 1 Economy Supersaver. **Excluded from the value ladder** (handled as separate flags):
Non-revenue (A, R, P — and `F` when issued < 2026-04-01), Groups (`G` when issued ≥ 2026-04-01),
Award redemption (`F` when issued ≥ 2026-04-01, or `G` when issued < 2026-04-01).

*Last updated: 22 July 2026 — mirror of DataDictionary.v1.xlsx*
