# AgriTech Data Cleaning & Pipeline Audit Report

## Executive Summary
This report documents the automated data cleaning and schema validation audit performed across all AgriTech datasets in the `data/` directory.

---

## 1. Dataset Schemas & Operational Audit

### 1.1 `dim_mandi.csv` (Mandi Dimension Table)
- **Primary Key:** `mandi_id`
- **Fields:** `mandi_id`, `mandi_name`, `state`, `district`, `market_type`
- **Cleaned Record Count:** 57
- **Quality Rules Applied:** ID standardization (`MANDIXXX`), state and district mapping, default market classification (`APMC`).

### 1.2 `fact_arrivals.csv` (Commodity Arrivals Fact Table)
- **Primary Key:** `arrival_id`
- **Foreign Key:** `mandi_id` -> `dim_mandi.mandi_id`
- **Fields:** `arrival_id`, `date`, `mandi_id`, `crop_name`, `raw_crop_name`, `variety`, `arrival_quantity_qtl`, `farmer_count`, `arrival_id_was_missing`, `qty_was_negative`, `farmer_count_was_missing`
- **Cleaned Record Count:** 25000
- **Quality Rules Applied:** Date standardization to ISO `YYYY-MM-DD`, absolute value conversion for negative arrival quantities, missing farmer count imputation.

### 1.3 `fact_price_msp.csv` (Price & MSP Fact Table)
- **Primary Key:** `record_id`
- **Foreign Key:** `mandi_id` -> `dim_mandi.mandi_id`
- **Fields:** `record_id`, `date`, `mandi_id`, `district`, `crop_name`, `raw_crop_name`, `min_price`, `max_price`, `modal_price`, `msp`, `is_price_crash`
- **Cleaned Record Count:** 12000
- **Quality Rules Applied:** Currency symbol/comma stripping, `min_price <= max_price` sanity correction, automated recalculation of `is_price_crash` (`modal_price < msp`).

### 1.4 `dim_weather_daily.csv` (Daily Weather Dimension Table)
- **Primary Key:** `date`
- **Fields:** `date`, `avg_temperature_c`, `total_rainfall_mm`, `avg_humidity_percent`, `sensor_reading_count`
- **Cleaned Record Count:** 252
- **Quality Rules Applied:** ISO date validation, non-negative rainfall enforcement (`clip(lower=0)`), humidity bounded to `[0, 100]%`.

### 1.5 `fact_transport.csv` (Logistics Fact Table)
- **Primary Key:** `trip_id`
- **Foreign Key:** `mandi_id` -> `dim_mandi.mandi_id`
- **Fields:** `trip_id`, `mandi_id`, `destination_warehouse`, `departure_time`, `arrival_time`, `transit_hours`, `distance_km`, `distance_unit_assumed`, `vehicle_no`, `vehicle_no_raw`, `driver_id`
- **Cleaned Record Count:** 10000
- **Quality Rules Applied:** Non-negative transit hours and distance validation, string whitespace normalization for vehicle and driver IDs.

---

## 2. Pipeline Execution Summary

- **Script:** `pipeline/clean_pipeline.py`
- **Status:** Execution Completed Successfully
- **Output Directory:** `data/`
- **Audit Verification:** All 5 core tables validated, cleaned, and updated.
