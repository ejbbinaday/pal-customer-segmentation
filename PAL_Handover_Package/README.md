# PAL Customer Segmentation Pipeline: Technical Handover Guide

## 1. Project Overview
This repository contains the end-to-end data engineering and machine learning pipeline for Philippine Airlines (PAL) Customer Segmentation. It processes raw Passenger Name Record (PNR) coupon data (45 columns), engineers flight and booking-level behavioral features, applies SME-driven proxy rules to determine the core segment, and uses Machine Learning (Latent Class Analysis) to assign every booking into distinct, actionable behavioral sub-segments.

The final output is a suite of dimension and fact tables heavily optimized for direct ingestion into Power BI.

## 2. Current Model Quality Metrics (Sep 2026)
Based on the integration of the complete 46.3M row dataset and the 5 new fields (`FareBasisCode`, `TourCode`, `RevPaxInd`, `ItinType`, `FF_Ind`), the model achieves the following highly-validated metrics:

* **Data Volume Evaluated:** 46,339,091 flight coupons → rolled up into **22,911,450 unique bookings**.
* **Mabuhay Loyalist Capture:** **~17% of all bookings** (Expanded from 0.03% by tracking `FF_Ind` rather than just non-revenue award tickets).
* **Corporate vs. Leisure Separation (Construct Validity AUC): 0.878**
  * *What this means:* The model cleanly separates these behaviors without looking at the rules' own inputs, largely due to the successful parsing of advance purchase days and flexibility flags from the `FareBasisCode`.
* **Balikbayan vs. Pilgrimage Separation:** **AUC 0.955** (Highly distinct behaviors).
* **Gulf Route 30-Day Stay Spike:** **Resolved (Chi-squared p=0.00)**.
  * *What this means:* The 30-day spike on Middle East routes was mathematically proven to be driven by specific economy fare families (e.g., `TARI`, `TLFS`), proving it is a fare-rule artifact rather than an organic behavioral trend.

## 3. Technical Architecture
* **Core Data Engine:** DuckDB (Handles out-of-memory processing for 46M+ row datasets on standard hardware in minutes).
* **Machine Learning (Sub-segmentation only):** Scikit-Learn, StepMix (Latent Class Analysis).
* **Data Format:** Parquet (Snappy/ZSTD compressed) for all intermediate and output files to ensure rapid I/O.
* **Language:** Python 3.11+

## 4. End-to-End Pipeline Execution
To run the pipeline from raw data to Power BI extracts, execute the following scripts in order from the project root:

### Stage 1: Data Ingestion & Engineering
1. `python src/build_parquet.py`
   * *Purpose:* Converts raw `data/PAL-data/*.txt.gz` CSVs into typed, partitioned Parquet files. Natively handles 45-column data.
2. `python src/clean_real.py`
   * *Purpose:* Cleanses columns, handles timezones, standardizes nomenclature, and passes through critical new fields (`FareBasisCode`, `FF_Ind`, `TourCode`).
3. `python src/features_real.py`
   * *Purpose:* Aggregates coupon-level data into booking-level itineraries. Extracts rich features via regex from `FareBasisCode` (Advance Purchase days, Seasonality, Promo flags). Executes the **Proxy Waterfall** to assign ground-truth seed labels based on hard business rules.

### Stage 2: Machine Learning Sub-segmentation (LCA)
*Note: As proven in the continuum analysis, no top-level ML clustering (like HDBSCAN) is used. The rule waterfall is the primary model. ML is strictly used for sub-segment refinement.*
4. `python src/subsegment_assign.py`
   * *Purpose:* Uses Latent Class Analysis (LCA) via StepMix to divide the massive parent segments (e.g., Leisure, OFW) into 4 distinct behavioral sub-segments each.
   * *Execution Note:* This runs on the count-weighted cell table, exactly scoring all 21.7M eligible bookings.

### Stage 3: Dashboard Export
5. `python src/export_powerbi.py`
   * *Purpose:* Joins the ML sub-segments back onto the 46.3M individual coupons. Generates aggregated fact tables, flight-level summaries, and dimension tables specifically structured for Power BI.
   * *Output Location:* `outputs/powerbi_export/`

---

## 5. Quick Start: Automated "One-Click" Execution
For non-data scientists, we have provided an intuitive wrapper script. To run the entire pipeline end-to-end on a new data extract, simply open your terminal and run these commands:
```bash
# 1. Navigate into the unzipped project folder
cd path/to/PAL_Handover_Package

# 2. Create and activate a virtual environment (First time only)
python3 -m venv .venv
source .venv/bin/activate  # (On Windows, use: .venv\Scripts\activate)

# 3. Install required dependencies (First time only)
pip install -r requirements-pipeline.txt

# 4. Run the automated pipeline
python run_pal_pipeline.py
```
This script will safely execute all 5 stages in order, print progress, and summarize the model metrics upon completion.

---

## 6. Required Data Format & Anomalies
* **Input Schema:** The pipeline strictly expects the 45-column schema defined in `docs/new-pal-data/List of Fields for Data Extraction.xlsx`.
* **Historical Data Coverage:** All files in `data/PAL-data/` must conform to this 45-column layout (including historical 2024 and 2025 data).
* **Known CSV Anomalies:** The `TourCode` field frequently contains unescaped internal quotes (e.g., `\"HRPINO\"`). The pipeline natively handles this by utilizing DuckDB's `ignore_errors=true` parameter in `src/build_parquet.py`. Do not remove this parameter, or the CSV parser will crash on future data dumps.

## 7. Future-Proofing: Updating Business Logic & Constraints
Because customer behavior evolves over time (concept drift) or new products launch, you may occasionally see the `Unassigned` segment grow. The model is intentionally designed to be tunable by Revenue Management SMEs without requiring deep machine learning knowledge.

### How to Fix an Increasing "Unassigned" Segment
If the `Unassigned` volume rises above acceptable levels (e.g., >5% of bookings), it means customers are behaving in ways not captured by the current rules. To capture them:
1. **Identify the Pattern:** Use the Power BI dashboard to filter on `Segment = 'Unassigned'`. Look for common denominators (e.g., a new fare class, a new route, or a shift in booking windows).
2. **Update the Rule Waterfall:** Open `src/features_real.py` and locate the core `CASE WHEN` statement inside the `build_booking` function (this is the Proxy Waterfall).
3. **Insert the New Rule:** Add a new `WHEN [condition] THEN '[Segment]'` clause to capture the new behavior *before* it hits the `ELSE 'Unassigned'` bucket.
   * *Important: Order matters!* Place your new rule vertically according to its business priority (e.g., strict Corporate rules must execute before broad Leisure rules).
4. **Safeguard with Constraints:** The pipeline mathematically protects business logic via `data/constraints/hard_constraints.csv`. If a new strict rule needs to be globally protected (e.g., "H12: All new premium economy routes must be Premium Bleisure"), add it to this CSV. The pipeline will automatically fail if your waterfall modifications accidentally violate these constraints.
5. **Re-run:** Simply run `python run_pal_pipeline.py` to re-assign all bookings under the newly updated logic.

### Handling Partner / Codeshare Airports (OAL)
You will occasionally see airport codes in the data that PAL does not fly to directly. This happens when PAL issues a ticket that includes a connecting flight on a partner airline (e.g., Manila to LAX on PAL, connecting to Las Vegas on a partner).
* **The Behavior:** The pipeline safely preserves these bookings. It will never delete a booking just because the airport is unrecognized; it will simply leave the region as `NULL` or "Unknown".
* **The Fix:** To categorize these revenues correctly, a business user simply needs to open `data/reference/airport_region.csv`, add the missing partner airport code as a new row (along with its country and region), and re-run the pipeline.

## 8. Continuous Validation (V1 - V4)
If the PAL Data Science team needs to re-validate the model after significantly changing the proxy rules (e.g., to generate new AUC metrics for a presentation), run the validation test suite:
1. `python src/validate_construct.py` (Tests V1 Construct Validity using gradient boosting)
2. `python src/validate_criterion.py` (Tests V2 Criterion Validity against outcomes)
