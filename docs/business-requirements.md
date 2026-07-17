# Business Requirements: Optimized Market Segmentation for Philippine Airlines

**Project:** PAL Customer Segmentation (CPT 3)
**Team:** Edyll Joshua Binaday, Jeremy Jay Lim, Arien Jadd Versoza, Martin Aloysius Yamzon (PL)
**Date:** 16 April 2026

---

## 1. Company & Context

Philippine Airlines (PAL) is a full-service carrier flying 16 million passengers annually across North America, Asia-Pacific, Oceania, and the Middle East. PAL's strategic identity is built on "heart-felt care" — a premium, personalized service philosophy.

**Competitive pressures:**
- Low-cost carriers (Cebu Pacific, AirAsia) aggressively dropping domestic fares via promos
- Full-service competitors offering superior service on key international routes
- Annual market capacity increases from all players

---

## 2. Problem Statement

> *"There is an opportunity for Philippine Airlines to optimize its customer segmentation models, using machine learning, to further personalize its service and maximize opportunities within each segment."*

PAL currently lacks a data-driven, ML-powered framework to automatically classify passengers into actionable customer segments from booking/transaction data. Manual or rule-based methods cannot scale to 16M annual passengers across diverse routes and booking patterns.

---

## 3. Business Objectives

| # | Objective | Business Owner | KPI |
|---|-----------|---------------|-----|
| BR-01 | Automatically classify each PNR into one of 6 customer segments | Data Science / RM | Model confidence ≥ 90% on hold-out set |
| BR-02 | Enable targeted pricing strategies per segment to maximize revenue | Revenue Management | Avg revenue per passenger |
| BR-03 | Personalize marketing engagement to maximize Customer Lifetime Value (CLV) and loyalty | Marketing | CLV delta, churn rate |
| BR-04 | Identify and prioritize sales channels that are most profitable per segment | Sales & Distribution | Channel contribution margin |
| BR-05 | Minimize customer churn through optimized platform experience | Customer Experience | NPS by segment, churn rate |

---

## 4. Target Customer Segments

Six segments identified through domain knowledge and initial clustering analysis:

| Segment | Misclassification Penalty Weight | Description |
|---------|----------------------------------|-------------|
| **Corporate** | ×10 (Highest) | Business travelers, short lead times, business cabin, loyalty program members |
| **Mabuhay Loyalist** | ×8 (Very High) | Frequent flyers with active Mabuhay Miles, high CLV, repeat bookings |
| **OFW Traveler** | ×5 (High) | Overseas Filipino Workers, Middle East / international corridors, economy class, TTA channel |
| **Premium Bleisure** | ×4 (Moderate) | Business + leisure blend, premium economy / business cabin, ASEAN routes |
| **Balikbayan / VFR** | ×2 (Low) | Visiting Friends & Relatives, beyond itineraries (INT→DOM), group travel |
| **Budget Leisure** | ×1 (Baseline) | Price-sensitive leisure, economy saver/supersaver, domestic-heavy, promos |

> Note: **Last-Minute** travelers (0–3 day lead time, economy flex) appear as a behavioral sub-segment that cuts across the above groups.

---

## 5. Functional Requirements

### 5.1 Data Ingestion

| ID | Requirement |
|----|-------------|
| FR-01 | Ingest Passenger Name Record (PNR) data with at minimum 2 years of flown historical data |
| FR-02 | Ingest 1 year of booked and ticketed forward-booking passenger data |
| FR-03 | Support O&D (Origin–Destination) pair as the unit of analysis, partitioned by travel month |
| FR-04 | Ingest a data dictionary mapping fare bases, sales channels, and booking codes |
| FR-05 | Accept a small sample of manually labelled market segments as ground truth |
| FR-06 | Cover both domestic (DOM) and international (INT) PAL commercial passenger network |

### 5.2 Feature Engineering

| ID | Requirement |
|----|-------------|
| FR-07 | Compute booking lead time (days between PNRCreationDate and FlightDate) per PNR |
| FR-08 | Encode fare brand, fare basis, and cabin class per PNR |
| FR-09 | Encode O&D pair, region, and entity (DOM/INT) per PNR |
| FR-10 | Encode ticketing channel and point-of-sale (POS) country/city per PNR |
| FR-11 | Encode day-of-week (DOW) of departure and itinerary type (point-to-point vs. beyond) |
| FR-12 | Use PAX count per booking as a group-travel signal |
| FR-13 | Include loyalty status (Mabuhay Miles tier) as a feature when available |
| FR-14 | Include length of stay as a feature when available |
| FR-15 | Include departure time as a feature when available |
| FR-16 | Encode capture step (FTD/FTW/FTM BCC/Farebasis) as a booking-behavior signal |
| FR-17 | The ingestion pipeline must support 40+ features per PNR record |

### 5.3 Clustering Model

| ID | Requirement |
|----|-------------|
| FR-18 | Apply unsupervised clustering (KNN and/or DBSCAN) as the base grouping mechanism |
| FR-19 | The model must operate at the O&D level, per travel month |
| FR-20 | The model must identify centroids (most representative PNR per cluster) for human annotation |

### 5.4 Annotation Pipeline (Multi-Step)

> **⚠️ Superseded (2026-07-17).** The human-annotation steps below (FR-22 Reveal Centroids,
> FR-23/24 Annotate Tracers) and **§5.5 Label Diffusion** (FR-25/26) were **replaced by automated
> noise auto-assignment**: HDBSCAN flags borderline records and they are assigned to their nearest
> proxy-segment centroid — no human-annotation or graph label-spreading step. **Negative Learning
> (FR-21) is retained** as methodology §Stage P3b. See `methodology.md` §Stage P4 and
> `knowledge-base.md` §15 (2026-07-17). Requirements below are kept for historical context.

| ID | Requirement |
|----|-------------|
| FR-21 | Apply **Negative Learning** first: run rule-based impossibility filters across the full dataset before human annotators see any records (e.g., "Booked 60+ days out, Economy, No Loyalty ID → Cannot be Corporate") |
| FR-22 | **Reveal Centroids**: present the most representative PNR per cluster to domain annotators (RM Domestic, RM International, Network Planning, Frequent Flyer Product Owner) for labeling |
| FR-23 | **Annotate Tracers**: reveal 2% tracer samples (pre-filtered 10% set + priority centroid tracers) for annotator confirmation |
| FR-24 | Annotation should confirm rather than cold-classify — impossibility rules must reduce the decision space from 6 to 2–3 choices per record |

### 5.5 Label Diffusion

| ID | Requirement |
|----|-------------|
| FR-25 | After annotation, propagate labels outward from annotated seeds to cover the remaining ~98% of unlabeled records |
| FR-26 | Each passenger record is modeled as a node connected to its most behaviorally similar neighbors (graph-based label spreading) |

### 5.6 Validation

| ID | Requirement |
|----|-------------|
| FR-27 | Apply a **cost-sensitive asymmetric penalty matrix** during validation — misclassification costs are not equal across segments |
| FR-28 | Misclassifying a Corporate passenger as Budget Leisure should carry the highest penalty (~₱40,000 revenue loss per record); the inverse carries near-zero penalty (over-served, not harmful) |
| FR-29 | Penalty weights must be configurable per segment (see Section 4 table) |

### 5.7 Reporting & Dashboard

| ID | Requirement |
|----|-------------|
| FR-30 | Deliver an executive dashboard (Power BI or equivalent) showing total passengers, avg revenue per passenger, model confidence, and segments identified |
| FR-31 | Dashboard must support filtering by segment, route, and travel quarter |
| FR-32 | Dashboard must show **service touchpoint priority by segment** (radar chart: seat comfort, schedule reliability, price transparency, lounge access, baggage handling, staff service) |
| FR-33 | Dashboard must show a **pain point heatmap by segment** (Check-in, Baggage, Rebooking, Lounge, In-flight service; scored 0–10) |
| FR-34 | Dashboard must show **NPS by segment** |
| FR-35 | Dashboard must include a **passenger record explorer** showing sample labeled PNRs with model-assigned segment and confidence score |

---

## 6. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-01 | Model must achieve ≥ 91% hold-out accuracy (label spreading confidence) |
| NFR-02 | Pipeline must process domestic and international commercial passenger PNRs only (no cargo, no private charter) |
| NFR-03 | Output must be compatible with Power BI or similar BI tools |
| NFR-04 | All PNR data must be handled in compliance with PAL's data governance and NDA/MOA requirements |
| NFR-05 | The model must be documented sufficiently to be handed off for future production integration |

---

## 7. Scope

### In Scope
- Baseline ML segmentation model (not production-ready)
- O&D-level classification, per travel month
- Domestic and international online commercial passenger network
- Executive dashboard for insights (Power BI or equivalent)

### Out of Scope
- Production-level ML model for live website/app integration
- Production-level Power BI database
- Real-time passenger scoring/tagging on PAL's website or app

---

## 8. Data Requirements

### 8.1 Data Available (from PAL)
| Source | Contents |
|--------|----------|
| PNR Records | Passenger demographic info, transaction history, fare basis, cabin, channel, O&D, booking dates |
| Historical Flown Data | At least 2 years of flown passenger records |
| Forward Bookings | At least 1 year of booked and ticketed future-travel data |
| Labelled Sample | Small sample of PNRs with manually assigned market segments |

### 8.2 Additional Data Needed
| Source | Why Needed |
|--------|-----------|
| Mabuhay Miles Loyalty Program | Loyalty tier and flight history are critical for identifying Corporate and Mabuhay Loyalist segments |
| Web & App Usage Logs | Browsing and booking behavior signals (e.g., search flexibility, ancillary interest) help differentiate leisure vs. business intent |

---

## 9. Key Negative Learning Rules (Business Logic)

These impossibility rules are applied before annotation to eliminate invalid segment candidates per record:

| Condition | Ruled-Out Segment |
|-----------|-------------------|
| Booked 60+ days out · Economy · No Loyalty ID | Cannot be Corporate |
| Cargo add-on · Economy · Manila–Riyadh route | Cannot be Premium Bleisure |
| 0–3 day booking · Promo fare · No flexibility | Cannot be Last-Minute Emergency |
| Group booking 5+ · Dec–Jan travel dates | Cannot be Solo Budget Leisure |
| Business cabin · Same-day return · Loyalty status | Narrow to: Corporate or Premium Bleisure only |
| Middle East corridor · No Mabuhay Miles · Cargo | Narrow to: OFW Traveler or Balikbayan only |

---

## 10. Stakeholder & Process Requirements

| Item | Requirement |
|------|-------------|
| NDA/MOA | Data sharing agreements must be in place before PNR data access |
| Data/Workflow Constraints | Must identify data access restrictions and software constraints upfront |
| POCs per Commercial Group | Dedicated points of contact required: RM Domestic, RM International, Network Planning, Frequent Flyer Product Owner |
| Cadence & Communication | Regular check-in cadence between team and PAL commercial groups |
| ToR Sign-off | Terms of Reference revisions and sign-off path must be agreed before work begins |
