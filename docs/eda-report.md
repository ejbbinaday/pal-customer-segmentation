# EDA Report: PAL Sample Features (`sample-features.csv`)

**Date:** 19 April 2026
**Rows:** 29,999 | **Columns:** 27

---

## 1. Dataset Overview

| Attribute | Value |
|-----------|-------|
| Records | 29,999 |
| Features | 27 |
| Target (`Market Segment`) | **100% null** — labels must be created via ML pipeline |
| Key 3 features that are fully null | `Departure Time`, `Loyalty status`, `Length of stay` |
| Entity split | 63.6% Domestic (DOM) / 36.4% International (INT) |
| Date range (flight dates) | Jan 2025 bookings visible; PNR creation dates span 2024–2025 |

---

## 2. Feature-by-Feature Summary

### 2.1 Features With Good Coverage

| Feature | Nulls | Type | Notes |
|---------|-------|------|-------|
| `Flight Date` | 0% | Datetime | All records present |
| `Entity` | 0% | Binary | DOM (19,085) / INT (10,914) |
| `Region` | 0% | Categorical | 10 values; MNL HUB dominant (54%) |
| `Route` | 0% | Categorical | Destination code; BCD top route |
| `Flight Number` | 0% | Categorical | PR prefix |
| `Farebrand` | 0% | Categorical | 8 values; Economy Saver most common |
| `Itinerary Type` | 0% | Categorical | 5 types; Point-to-Point 64% |
| `Cabin` | 0% | Categorical | Y=95.2%, W=2.9%, J=2.2% |
| `Sector` | 0% | Categorical | IATA O&D pair |
| `Capture Step` | 0% | Categorical | FTD Farebasis dominant (90.3%) |
| `DOW` | 0% | Categorical | Friday most common |
| `PAX Count` | 0% | Integer | Mean 1.66; 67% solo travelers |
| `Average Fare` | 0% | Float (after cleaning) | $1.70–$5,382.90; mean $160.31 |
| `POS Region` | 6.6% | Categorical | ROW dominant |

### 2.2 Features With Moderate Missingness (~10%)

| Feature | Nulls | Notes |
|---------|-------|-------|
| `FareBasis` | 9.26% | IATA fare code |
| `Ticketed Itinerary` | 9.26% | Full routing string |
| `POO` | 9.26% | Point of origin airport |
| `Issue Date` | 9.26% | Ticket issue date |
| `POO Country` | 9.26% | Origin country |
| `Ticketing Channel` | 10.19% | 9 channel types (TTA dominant) |
| `POS Country` | 10.19% | Point-of-sale country |
| `POS City` | 10.19% | Point-of-sale city |
| `PNRCreationDate` | 0.05% | Used for lead time derivation |

### 2.3 Features That Are 100% Null (Need Data From PAL)

| Feature | Business Requirement | Segment Signal |
|---------|---------------------|---------------|
| `Loyalty status` | Critical — Mabuhay Miles tier data not yet provided | Corporate, Mabuhay Loyalist |
| `Length of stay` | Must be derived or sourced from return PNR pairing | Leisure (long stay) vs. Corporate (short stay) |
| `Departure Time` | Must come from flight schedule data | Corporate (early AM) vs. Leisure (midday/evening) |

---

## 3. Key EDA Findings Relevant to Business Requirements

### 3.1 Segment Proxy Analysis

#### Corporate Segment Signals
- **671 Business cabin (J) records** (2.2% of dataset) — cleanest proxy for this segment
- Median lead time: **15 days** (short, consistent with business travel)
- Top region: **ASEAN (72% of Business cabin bookings)**
- Average fare: **$440** vs. $160 overall — highest revenue segment
- Top channels: WEB/APP and OTA (surprisingly, not Corporate Web Portal — only 1 record)
- **Gap:** Corporate Web Portal channel is severely under-represented (367 total records, only 1 in Business cabin) — likely a data quality or channel-tagging issue

#### OFW Traveler Signals
- **1,189 Middle East records** (4.0% of dataset) — proxy for OFW corridor
- Top sectors: RUHMNL (275), MNLDOH (271), MNLRUH (257) — Riyadh and Doha dominant
- Average fare: **$351** | Average lead time: **59 days** (plan far ahead)
- Channel: **Traditional Travel Agency (TTA) dominant (59%)** — OFWs rely on agents
- Farebrand: Economy Saver (41%) and Economy Value (32%)
- **Sea Crew channel** (849 records) is a related proxy — economy class, mixed regions, avg fare $185

#### Budget Leisure Signals
- Economy Supersaver + Economy Saver = **14,376 records (48%)** of dataset
- **MNL HUB dominant** — avg fare only $73.50 (vs $460 for Australasia)
- WEB/APP channel significant for domestic budget booking (6,306 DOM records)
- Average PAX count slightly above 1 (group/couple travel common)

#### Balikbayan / VFR Signals
- **Beyond (INT–DOM) itinerary type: 5,376 records (18%)** — strongest Balikbayan proxy
- North America + Middle East routes connecting to domestic destinations
- Group size: PAX Count ≥ 2 more common in this group
- Economy Saver with long lead times (plan holiday trips months ahead)

#### Premium Bleisure Signals
- **Premium Economy (W cabin): 871 records (2.9%)**
- Average fare: **$141** — positioned between Economy and Business
- Short median lead time (**7 days** — flexible, higher-income traveler)
- ASEAN and Australasia routes dominant

#### Last-Minute Traveler Signals
- **0–3 day lead time: 4,659 records (15.5%)**
- Economy Flex is the dominant farebrand (flexible ticket needed)
- Spread across all regions — cuts across multiple segments
- Higher fare paid per ticket (urgency premium)

---

### 3.2 Lead Time Distribution

| Bucket | Count | % | Key Segment |
|--------|-------|---|------------|
| Same-day (0d) | 687 | 2.3% | Last-minute |
| 1–3 days | 3,972 | 13.2% | Last-minute |
| 4–7 days | 4,222 | 14.1% | Corporate / Last-minute |
| 8–14 days | 4,012 | 13.4% | Corporate |
| 15–30 days | 4,566 | 15.2% | Mixed |
| 31–60 days | 4,434 | 14.8% | OFW / Balikbayan |
| 60+ days | 8,092 | 27.0% | OFW / Budget Leisure |

**Insight:** 27% of bookings are made 60+ days ahead — this cohort likely spans OFW, Balikbayan, and vacation-planning Budget Leisure passengers. Lead time is one of the most differentiating features for segmentation.

---

### 3.3 Fare Distribution by Region

| Region | Mean Fare | Key Segment Implication |
|--------|-----------|------------------------|
| North America | $778 | Balikbayan with high spend; occasional Corporate |
| Australasia | $459 | Premium Bleisure, holiday travelers |
| Middle East | $351 | OFW Traveler |
| Japan | $276 | Premium Bleisure / leisure |
| ASEAN | $192 | Corporate (short-haul biz) + Bleisure |
| MNL HUB | $74 | Budget Leisure (domestic) |
| CEB HUB | $46 | Budget Leisure (domestic) |

---

### 3.4 Ticketing Channel Analysis

| Channel | DOM | INT | Key Segment |
|---------|-----|-----|------------|
| Traditional Travel Agency | 6,469 | 3,556 | OFW, Balikbayan, Budget Leisure |
| WEB/APP | 6,306 | 2,119 | Budget Leisure, Corporate |
| OTA | 908 | 3,054 | International leisure, Corporate |
| Ticket Office | 1,458 | 243 | Last-minute, walk-in |
| Sea Crew | 519 | 330 | OFW sub-type |
| Contact Center | 747 | 350 | Elderly/complex itineraries |
| TMC | 119 | 268 | Corporate (Travel Management Companies) |
| Corporate Web Portal | 351 | 16 | Corporate |

**Insight:** TMC (Travel Management Company) + Corporate Web Portal are strong Corporate signals. Sea Crew is a distinct OFW sub-type worth treating as a separate indicator. TTA is likely the strongest OFW/Balikbayan proxy available in this dataset.

---

### 3.5 PAX Count Distribution

| PAX Count | Count | % | Segment Implication |
|-----------|-------|---|---------------------|
| 1 | 20,106 | 67% | Solo travel → Corporate, OFW, Budget solo |
| 2 | 5,829 | 19.4% | Couple → Bleisure, VFR |
| 3–4 | 2,953 | 9.8% | Small family → Balikbayan, VFR |
| 5+ | 1,111 | 3.7% | Group → Balikbayan, tour groups |

---

### 3.6 Negative Learning Rule Feasibility

Cross-referencing the pitch deck's negative learning rules against available columns:

| Rule | Columns Required | Available? |
|------|-----------------|------------|
| "Booked 60+ days · Economy · No Loyalty ID" → Not Corporate | lead_time, Cabin, Loyalty status | Partially — Loyalty status is NULL |
| "Cargo add-on · Economy · Manila–Riyadh route" → Not Premium Bleisure | Cargo flag, Cabin, Sector | Cargo flag NOT in dataset |
| "0–3 day booking · Promo fare · No flexibility" → Not Last-Minute Emergency | lead_time, Farebrand | Yes |
| "Group booking 5+ · Dec–Jan travel" → Not Solo Budget Leisure | PAX Count, Flight Date | Yes |
| "Business cabin · Same-day return · Loyalty status" → Corporate/Bleisure | Cabin, Loyalty status, Length of stay | Partially — Loyalty & LOS are NULL |
| "Middle East corridor · No Mabuhay Miles · Cargo" → OFW/Balikbayan | Sector/Region, Loyalty status, Cargo | Partially — Loyalty NULL, Cargo absent |

**Critical gap:** 4 of 6 negative learning rules depend on `Loyalty status` or `Cargo add-on` — both missing from the current dataset.

---

## 4. Recommended Features Not Present in `sample-features.csv`

These features are either mentioned in the pitch deck as needed, implied by the negative learning rules, or standard in airline PNR data that PAL almost certainly has but hasn't included in the sample.

### Priority 1 — Critical for Segmentation (Blocking Without These)

| Feature | Source | Why Needed | Target Segments |
|---------|--------|-----------|----------------|
| **Loyalty status / Mabuhay Miles tier** | Mabuhay Miles program DB | Directly identifies Loyalists and Corporate; required for 4/6 negative rules | Corporate, Mabuhay Loyalist |
| **Loyalty program miles balance** | Mabuhay Miles program DB | High balance = long-tenure loyalist; low = occasional | Mabuhay Loyalist |
| **Cargo / baggage add-on flag** | PNR ancillary data | Cargo add-on is a strong OFW/Balikbayan signal; rules it out for Bleisure | OFW, Balikbayan |
| **Length of stay (days)** | Return PNR or itinerary data | Short stay (<4d) = Corporate; Long stay (14d+) = Leisure/Balikbayan | All segments |
| **Departure time** | Flight schedule data | Early AM = Corporate; midday/evening = Leisure | Corporate, Budget Leisure |

### Priority 2 — High Value for Enrichment

| Feature | Source | Why Needed | Target Segments |
|---------|--------|-----------|----------------|
| **Number of prior PAL bookings (12-month window)** | PNR historical DB | Frequency = loyalty proxy before Miles data is available | Mabuhay Loyalist, Corporate |
| **Meal preference / special service request (SSR) codes** | PNR data | Frequent SSR = Corporate/Loyalist; Halal meal = OFW/Middle East signal | OFW, Corporate |
| **Seat selection indicator** | PNR ancillary data | Pre-selected aisle/window = experienced traveler; no selection = price-focused | Corporate, Budget Leisure |
| **Advance seat purchase (paid vs complimentary)** | PNR ancillary data | Paid seat = willingness to spend; complimentary = loyalty benefit | Corporate, Mabuhay Loyalist |
| **Companion PNR count** | PNR cross-reference | Whether the booking is linked to other PNRs in same group | Balikbayan, VFR |
| **Passenger nationality / passport country** | PNR passenger data | Filipino passport on international = OFW/Balikbayan proxy | OFW, Balikbayan |
| **Return ticket indicator** | Ticketed itinerary parse | One-way = OFW departure leg; Round-trip = leisure/Balikbayan return | OFW, Balikbayan |
| **Booking modification count** | PNR change history | Multiple changes = Corporate (flexible travel); Zero = committed leisure booker | Corporate, Budget Leisure |

### Priority 3 — Useful Context, Available from External/Schedule Data

| Feature | Source | Why Needed | Target Segments |
|---------|--------|-----------|----------------|
| **Travel season / holiday flag** | PAL calendar + PH public holidays | Dec–Jan = Balikbayan/holiday travel season; peak = leisure | Balikbayan, Budget Leisure |
| **Route competition intensity** | Market data | Routes with LCC competition = fare-sensitive segment pressure | Budget Leisure |
| **Flight on-time performance (OTP) of booked flight** | PAL ops data | OTP matters most to Corporate; less to OFW/leisure | Corporate |
| **Promo fare indicator** | Fare basis decode | Promo = Budget Leisure or Last-Minute; Full = Corporate/Loyalist | Budget Leisure, Last-Minute |

---

## 5. Data Quality Issues to Address Before Modeling

| Issue | Affected Columns | Recommended Action |
|-------|-----------------|-------------------|
| `Average Fare` stored as string with `$` prefix | `Average Fare` | Strip `$` and cast to float — already needed for analysis |
| 3 key features are 100% null in sample | `Loyalty status`, `Departure Time`, `Length of stay` | Escalate to PAL data owners immediately; these are blocking |
| ~10% null in Ticketing Channel / POS columns | `Ticketing Channel`, `POS Country`, `POS City` | Investigate whether nulls correspond to specific booking flows (e.g., group bookings, non-PAL ticketing) |
| Capture Step encoding unclear | `Capture Step` | Map FTD/FTW/FTM + BCC/Farebasis combinations to business meanings via data dictionary |
| `Market Segment` is 100% null | `Market Segment` | Expected — this is the target column to be filled via the ML pipeline |

---

## 6. Derived Features to Engineer

These can be computed directly from existing columns:

| Derived Feature | Formula / Logic | Segment Signal |
|----------------|----------------|---------------|
| `lead_time_days` | `Flight Date - PNRCreationDate` | Already computed in EDA; strong differentiator |
| `lead_time_bucket` | Categorical: same_day / 1-3d / 4-7d / 8-14d / 15-30d / 31-60d / 60d+ | More interpretable for negative rules |
| `is_group_booking` | `PAX Count >= 5` | Balikbayan / group tour signal |
| `is_solo` | `PAX Count == 1` | Corporate / OFW solo signal |
| `is_couple_or_small_family` | `PAX Count in [2,3,4]` | Bleisure / VFR signal |
| `is_domestic` | `Entity == 'DOM'` | Budget Leisure / domestic corporate |
| `is_middle_east` | `Region == 'Middle East'` | OFW proxy |
| `is_beyond_itinerary` | `Itinerary Type.str.contains('Beyond')` | Balikbayan / VFR proxy |
| `is_business_cabin` | `Cabin == 'J'` | Corporate / Bleisure signal |
| `is_economy_promo` | `Farebrand in ['Economy Supersaver', 'Economy Saver']` | Budget Leisure signal |
| `is_flexible_fare` | `Farebrand in ['Economy Flex', 'Business Flex']` | Corporate / Last-Minute signal |
| `is_tmc_channel` | `Ticketing Channel == 'TMC'` | Corporate signal |
| `is_tta_channel` | `Ticketing Channel == 'Traditional Travel Agency'` | OFW / Balikbayan signal |
| `travel_month` | Month extracted from `Flight Date` | Seasonality: Dec-Jan = Balikbayan season |
| `is_holiday_season` | `travel_month in [12, 1, 3, 4]` | Balikbayan / leisure indicator |
| `fare_per_pax` | `Average Fare / PAX Count` | Normalized spend signal |
