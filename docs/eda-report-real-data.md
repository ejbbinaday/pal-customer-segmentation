# EDA Report — Real PAL Coupon Extract (38M rows)

**Date:** 5 August 2026
**Data:** `data/PAL-data/*.txt.gz` → `data/interim/pal_clean/` (38,116,260 coupons · 42 columns)
**Sources:** `outputs/profile_raw/summary.md` (Stage B), `outputs/clean_report/summary.md` (Stage C),
`outputs/eda_real/confirmations.md` (Stage E), `outputs/features_real/summary.md` (Stage F)

> This report covers the **real-data pipeline** and supersedes `docs/eda-report.md`, which profiled
> the 30k-row prototype sample (`sample-features.csv`) — do not quote results from that track.

---

## 0. The story in plain language

Think of the dataset as **every flight coupon PAL issued for travel between May 2024 and May 2027** —
38 million "boarding-pass stubs". Each stub knows *who* bought it (a hashed `UniqueID`), *when* it was
bought and flown, *what* fare brand and cabin, *where* it was sold, and *how much* it earned.

Three facts shape everything downstream:

1. **Most customers are occasional flyers.** The median customer has 2 coupons; 95% of IDs have
   fewer than 8. A tiny heavy tail (≈5k customers with 100+ coupons) is dominated by sea-crew and
   agency-style buying, not ordinary travellers.
2. **This is overwhelmingly an economy, Philippines-centred airline.** 95% of coupons are economy
   cabin, ~88% sit in the three cheapest economy fare brands, and 58% of bookings are domestic.
3. **The data is remarkably clean but demographically thin.** Nulls are near-zero on the core
   operational fields, but `Age` is 57% missing and loyalty signal (award tickets) is vanishingly
   rare (0.02% of coupons) — so segmentation must lean on *behaviour* (lead time, route, fare tier,
   channel, party size), not on who the customer says they are.

---

## 1. Dataset overview

| Attribute | Value |
|---|---|
| Coupon rows (raw) | 38,116,260 |
| Columns | 42 |
| Distinct customers (`UniqueID`) | 13,447,672 (0 nulls) |
| Coupons per customer | mean 2.83 · median 2 · p95 8 · max 771 |
| Bookings (`customer_id × issue_date`) | 22,924,577 (avg 1.66 coupons each) |
| Departure dates | 2024-05-01 → 2027-05-31 |
| Issuance dates | 2023-03-24 → 2026-07-20 |
| Operating carrier | PR only (100%) |

### Coverage by source file

| File | Rows | Departures covered |
|---|---:|---|
| `newQuery2024.txt.gz` | 10,445,443 | May–Dec 2024 |
| `newQuery2025.txt.gz` | 16,248,222 | full-year 2025 |
| `newQuery2026Jan_to_May.txt.gz` | 7,069,964 | Jan–May 2026 |
| `newQuery2026Jun_to_2027May.txt.gz` | 4,352,631 | Jun 2026–May 2027 (forward bookings, still filling) |

19.73% of customers appear in more than one source file with consistent behaviour, confirming
`UniqueID` persists across extracts and the customer-level rollup is valid.

---

## 2. Data quality (Stage C cleaning)

Cleaning removed exactly **1 row** (junk `SoldOperatingCabinClass`); a streaming approx-distinct
check found ~0 exact duplicates on the natural coupon key, so no dedup was applied.
**38,116,259 rows out.**

| Check | Result | Handling |
|---|---|---|
| Flown vs open coupons | 93.42% flown · 6.58% open | flag |
| Non-revenue (staff/comp) | 0.082% of coupons | flag; all-non-rev customers excluded in FE |
| Award (Mabuhay) | 0.024% | flag |
| Group fare | 0.131% | flag |
| Revenue missing/zero | 0.248% | flag |
| Refunds (negative revenue) | 0.101% (7,385 negative-revenue rows raw) | flag, excluded from revenue sums |
| Negative lead time (reissues) | 1,728 rows (0.005%) | clamp/flag in FE |
| `Age` | 57% null (43% known) | treat as low-coverage auxiliary |
| NULL `value_tier` (award/group/non-rev classes) | 0.237% | expected by design |

Currency sanity: median revenue spread across the 26 major issue countries is 7.3× — consistent
with a single reporting currency.

---

## 3. Key distributions

### Cabin & fare brand — an economy airline

- Cabin: **Y 95.2% · J 2.9% · W 2.8%** (operated).
- Fare brands: Economy Saver 38.6% + Supersaver 29.7% + Value 19.8% ≈ **88% of all coupons** in the
  three cheapest economy brands; Business (Value+Flex) is just 2.8%.
- Value tiers (1 = Supersaver … 7 = Business Flex): heavily bottom-loaded — tiers 1–2 hold 26.0M of
  38.1M coupons.

### Geography — Manila-centred, strong diaspora corridors

- Top origins (`POO`): MNL 14.4M, CEB 2.3M, DVO 2.1M; LAX (0.77M) and ICN (0.64M) lead
  international origins.
- Country of issue: PH 61.6%, then US, SG, JP, HK, CA, KR, AU — the classic OFW/diaspora footprint.
  **38.4% of coupons are foreign-issued.**
- Route regions (bookings): domestic PH 57.7%, East Asia 14.8%, Southeast Asia 11.8%,
  North America 8.4%, Middle East 4.0%, Oceania 3.3%. (South Asia/Europe ≈ 0 — no own-metal
  service in the extract.)
- 72.4% of coupons are nonstop; 27.6% connecting.

### Channel

WEB/APP 35.4% · Traditional Travel Agency 27.8% · OTA 14.9% · Ticket Office 6.1% ·
Contact Center 4.7% · **Sea Crew 3.7%** (a distinct, contract-driven population) · NDC 2.4% · TMC 1.8%.

### Booking behaviour

- **Lead time** (issue → departure), **coupon grain**: median **25 days**, mean 53.2, max 679.
  **13.3% of coupons are booked 0–3 days out.** At the booking grain used for modelling (§4) the same
  distribution is median **18 days**, mean 43.3, **19.26% inside three days** — a large genuine
  last-minute population. Quote the booking-grain pair anywhere the 22.9M-booking figures are shown.
- Party size (`Pax Count`): 1–5, mostly solo; group `BookingType` is only 2.6% of coupons.

---

## 4. Booking grain & customer-level confirmations (Stage E)

The plan's grain assumption — a *booking* = `(customer_id, issue_date)` — holds up:

- 22.9M bookings; **42.7% are round-trips** (journey returns to origin), 55.3% single-direction
  (true one-ways or separately issued returns), only 1.4% have >2 directions.
- **Heavy tail:** customers with 100+ coupons number just 4,896; 21.7% of them touch the Sea Crew
  channel and their volume concentrates in WEB/APP + agency channels — treat as a distinct
  crew/agency population, not typical customers.
- **All-non-revenue customers:** 12,306 (0.092%) — cleanly excluded before feature engineering.
- **Loyalty signal is thin:** only 6,259 customers (0.047%) ever used an award ticket; 6.9% ever
  flew premium (J/W); but **26.1% are repeat customers** (≥2 bookings) — repeat behaviour, not
  loyalty status, is the usable signal. Avg tenure (first→last issuance) is 82 days **across all
  customers — a number 74% of whom contribute a structural zero** (one booking ⇒ tenure 0). Among
  customers who actually returned, first→last spans a **median 285 days / mean 314 days**. Quote 285,
  not 82, if the question is "how long is a relationship".
  **Right-censoring warning:** 26.1% counts repeats *inside the extract's ~27-month issuance window*
  (issuance runs 2024-04 → 2026-07-20 at full volume). On a fixed horizon it is **26.5% within 12
  months** of the first booking (8.11M customers with a full year of runway); by first-booking cohort
  it falls monotonically with remaining runway — **40.5%** for 2024 Q2 down to **2.9%** for 2026 Q3.
  Never state the complement as "74% never return".

---

## 5. Proxy-segment magnitudes (Stage F — indicative, not final labels)

After excluding the 12,306 all-non-revenue customers: **22,911,450 booking rows ·
13,435,365 customer rows.**

| Proxy segment | Bookings % | Avg revenue | Dominant-segment customers % |
|---|---:|---:|---:|
| Budget/Adventure | 39.4% | $74 | 38.4% |
| OFW/Migrant | 17.1% | $312 | 19.0% |
| Last-Minute | 12.9% | $137 | 9.9% |
| Balikbayan/VFR | 12.7% | $618 | 16.4% |
| Unassigned | 9.6% | $360 | 8.8% |
| Corporate | 4.4% | $493 | 3.2% |
| Premium Bleisure | 2.1% | $1,504 | 2.0% |
| Family | 1.6% | $235 | 2.0% |
| Pilgrimage | 0.2% | $404 | 0.3% |
| Mabuhay Loyalist | 0.03% | $113 | 0.03% |

Reading: the value story is inverted from the volume story — Budget/Adventure is 39% of bookings at
$74 average revenue, while Premium Bleisure is 2% of bookings at $1,504. Mabuhay Loyalist is too
rare to learn as a cluster and is handled by rule. These are coarse seed rules to gauge signal
size; final segments come from the HDBSCAN pipeline (`docs/methodology.md`).

---

## 6. Implications for modelling

1. **Behavioural features carry the segmentation.** Age (57% null) and loyalty (0.05% of customers)
   can't anchor segments; lead time, fare tier, route region, foreign-issue, channel, and party
   size can.
2. **Exclude, don't model, the operational populations** — all-non-revenue customers and the
   sea-crew/agency heavy tail distort clusters far beyond their headcount.
3. **The booking grain works.** `(customer_id, issue_date)` recovers round-trips cleanly and gives
   1.66 coupons per booking, matching PNR intuition.
4. **Guard against calendar censoring.** The 2026-Jun→2027-May file is forward bookings only —
   lead-time and volume features from that window are right-censored.
5. **Rare segments need rules or asymmetric costs.** Mabuhay Loyalist and Pilgrimage are far below
   any density threshold HDBSCAN can find unaided — consistent with the penalty-weighted design.

---

*Generated from pipeline stage outputs; regenerate the underlying stats with
`python src/profile_raw.py`, `src/clean_real.py`, `src/eda_real.py`, `src/features_real.py`.*
