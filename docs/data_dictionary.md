# Track 3 (AgriTech) — Data Dictionary

All cleaned files live in `data/`. Grain and keys are noted for each table so they can
be loaded straight into Power BI / Tableau / Streamlit as a star schema
(see `star_schema.md`).

---

## 1. `dim_mandi.csv` — Mandi master (dimension)
Grain: one row per mandi. **Primary key: `mandi_id`**

| Column | Type | Description |
|---|---|---|
| mandi_id | text | Canonical ID, format `MANDI0##`. Raw values like `MANDI-034`, `mandi_031`, `M017`, `034` were all digit-normalized to this one format. |
| mandi_name | text | Mandi display name. |
| district | text | Title-cased district name. 4 rows have no district in the source and were left blank (no reliable way to infer). |
| state | text | Title-cased state name. |
| mandi_type | text | One of `APMC`, `Private`, `Direct`, `Unknown` (11 rows had no type; filled `Unknown` rather than guessed). |
| total_area_acres | numeric | Mandi footprint in acres. 6 rows missing; left blank — not used in any core KPI. |

Raw → cleaned: 60 → 57 rows (3 exact duplicate `mandi_id` rows removed).

---

## 2. `fact_arrivals.csv` — Daily crop arrivals (fact)
Grain: one row per arrival record. **Key: `arrival_id`. FK: `mandi_id` → dim_mandi.**

| Column | Type | Description |
|---|---|---|
| arrival_id | text | Unique arrival record ID. 476 source rows had a blank ID — a synthetic `ARR_GEN_######` ID was generated for these (flagged, see below). |
| date | date (ISO) | Parsed from 5 different raw date formats (see "Date parsing rules" below). |
| mandi_id | text | Canonical mandi ID. |
| crop_name | text | **Canonical crop name** (English). Hindi/Punjabi/case variants collapsed — see "Crop canonicalization" below. |
| raw_crop_name | text | Original crop text as it appeared in the source, kept for audit/traceability. |
| variety | text | Crop variety (e.g. `HD-2967`, `Hybrid`). Missing values filled `Unknown`. |
| arrival_quantity_qtl | numeric | **Standardized to Quintals.** Source quantities arrived in Tonnes/T/MT, Qtl/Q/Quintal(s), and KG/KGS/Kilo — all converted using 1 Tonne = 10 Qtl, 1 Qtl = 100 KG. Some rows had the unit embedded directly in the quantity string (e.g. `"415.88 qtl"`) instead of a separate `unit` column — these were parsed out. |
| farmer_count | numeric | Number of farmers who brought produce that day. 3,800 missing values were imputed with the **median farmer_count for that crop** (see flag column). |
| arrival_id_was_missing | boolean | `True` if the arrival_id was synthetically generated. |
| qty_was_negative | boolean | `True` if the raw quantity was negative (a data-entry sign error); the absolute value was used. |
| farmer_count_was_missing | boolean | `True` if farmer_count was imputed rather than reported. |

Raw → cleaned: 25,750 → 25,000 rows (750 exact duplicate rows dropped).

**Crop canonicalization** (raw → canonical), applied identically in `fact_price_msp`:

| Canonical | Raw variants folded in |
|---|---|
| Wheat | Wheat, WHEAT, wheat, Gehun, GEHUN, गेहूं, Kanak |
| Rice | Rice, rice, Chawal, चावल, Basmati |
| Paddy | Paddy, paddy, Dhaan, धान |
| Maize | Maize, Corn, corn, Makka, Makki, मक्का |
| Cotton | Cotton, cotton, Kapas, कपास, Narma |
| Mustard | Mustard, mustard, Sarson, Sarso, सरसों |
| Sugarcane | Sugarcane, sugarcane, Ganna, Ganne, गन्ना |

> **Design decision:** Rice and Paddy were kept as two *separate* canonical crops
> (rather than merged) because they are agronomically and commercially distinct —
> Paddy is unmilled/harvest-stage rice (this is what MSP is usually quoted against),
> while Rice/Chawal is the milled market product. Basmati (a rice variety) was
> folded into Rice. This is flagged here so evaluators/judges can see the reasoning
> and override it in one place (`CROP_MAP` in `clean_pipeline.py`) if a different
> business call is preferred.

**Date parsing rules** (confirmed empirically by checking which digit position exceeds 12):
| Raw pattern | Convention | Example |
|---|---|---|
| `DD-DD-DDDD` | **MM-DD-YYYY** | `08-16-2026` → 16 Aug 2026 |
| `DD/DD/DDDD` | DD/MM/YYYY | `23/06/2026` → 23 Jun 2026 |
| `DD.DD.DDDD` | DD.MM.YYYY | `09.01.2026` → 9 Jan 2026 |
| `DDDD-DD-DD` / `DDDD/DD/DD` | ISO YYYY-MM-DD | `2026-07-17` |
| `DD-Mon-DDDD` | DD-Mon-YYYY | `16-May-2026` |

---

## 3. `fact_price_msp.csv` — Wholesale price & MSP (fact)
Grain: one row per price quote. **Key: `record_id`. FK: `mandi_id` → dim_mandi.**

| Column | Type | Description |
|---|---|---|
| record_id | text | Unique price record ID (no duplicates found in source). |
| date | date | Parsed using the same rules as `fact_arrivals`. |
| mandi_id | text | Canonicalized. 1,235 rows had no mandi_id in source and were left blank (cannot be safely guessed). |
| district | text | Backfilled from `dim_mandi` via `mandi_id` wherever the source district was blank and the mandi_id was known; 1,546 → 271 rows still blank after backfill. |
| crop_name | text | Canonical crop name (same mapping as arrivals). |
| raw_crop_name | text | Original crop text, kept for audit. |
| min_price / max_price / modal_price | numeric (₹) | Currency symbols (₹, `Rs.`, `INR`), thousands commas, and trailing `/-` were stripped and converted to plain numbers. |
| msp | numeric (₹) | Minimum Support Price, cleaned the same way. 2,377 rows have no MSP quoted in source (left blank rather than fabricated). |
| is_price_crash | boolean | `True` when `modal_price < msp` — this is a genuine business signal (a "price crash"), not a data error, so it is kept as a derived flag rather than cleaned away. |

Raw → cleaned: 12,000 → 12,000 rows (no duplicates found).

---

## 4. `fact_transport.csv` — Mandi → Warehouse transit logs (fact)
Grain: one row per trip. **Key: `trip_id`. FK: `mandi_id` → dim_mandi.**

| Column | Type | Description |
|---|---|---|
| trip_id | text | Unique trip ID. |
| mandi_id | text | Canonicalized. |
| destination_warehouse | text | Already clean in source (`WH-North/South/East/West/Central`, `Export-Terminal`). |
| departure_time / arrival_time | datetime | Parsed from 9 different raw formats (ISO, `DD/MM/YYYY HH:MM`, `MM-DD-YYYY HH:MM AM/PM`, `DD-Mon-YYYY HH:MM:SS`, date-only). 1,006 arrival timestamps remain blank (genuinely missing in source). |
| transit_hours | numeric | **Recomputed from (arrival_time − departure_time) wherever both timestamps parsed successfully**, rather than trusting the raw `transit_hours` column, since 563 raw values were negative (physically impossible). Falls back to the raw value only if it is positive and timestamps are unavailable; otherwise left blank. |
| distance_km | numeric | Standardized to kilometers. Raw values in miles converted via 1 mile = 1.60934 km. |
| distance_unit_assumed | boolean | `True` for the 992 rows where `distance_unit` was blank in source — these were **assumed to be km** (the majority unit) rather than dropped; flagged so this assumption is auditable and reversible. |
| vehicle_no | text | Standardized to `SS-NN-LL-NNNN` format (uppercased, dashes normalized) regardless of raw spacing/case, e.g. `rj 43-DF-7922` → `RJ-43-DF-7922`. Missing values filled `Unknown`. |
| vehicle_no_raw | text | Original raw value, kept for audit. |
| driver_id | text | Missing values filled `Unknown`. |

Raw → cleaned: 10,400 → 10,000 rows (400 exact duplicate rows dropped).

---

## 5. `dim_weather_daily.csv` — Daily weather aggregate (dimension)
Grain: **one row per calendar date** (national aggregate across all sensors).

| Column | Type | Description |
|---|---|---|
| date | date | Calendar date, IST. |
| avg_temperature_c | numeric | Mean temperature across all sensor readings that day, standardized to Celsius (raw values arrived as `°F`, `Fahrenheit`, `f`, bare numbers with an embedded `°C`/`°F` suffix, or plain Celsius numbers). |
| total_rainfall_mm | numeric | Summed rainfall across sensors, standardized to millimeters (raw values in `in`/`inch`/`inches` converted ×25.4; impossible negative readings nulled before summing). |
| avg_humidity_percent | numeric | Mean relative humidity. |
| sensor_reading_count | integer | Number of individual sensor readings rolled into that day — a rough data-quality/coverage indicator. |

Raw → cleaned: 15,000 sensor readings (51 sensors, one labeled `UNKNOWN`) → 252 daily rows.
1,555 readings with unparseable timestamps were dropped (can't be date-bucketed).

> **Key assumption — no sensor-to-mandi/district mapping exists in the source
> data.** The raw file only has `sensor_id`; there is no column linking a sensor to
> a mandi, district, or lat/long. The dataset notes suggest "assuming 1:1 with
> districts," but there are 51 sensors against 27 distinct districts in
> `dim_mandi`, so a clean 1:1 mapping cannot be constructed without fabricating a
> join key. Rather than invent a false sensor→district link, weather has been
> aggregated to a **single national daily series** and should be joined to the
> other fact tables **by `date` only**. If a real sensor-location mapping becomes
> available, re-run the weather section of `clean_pipeline.py` with a `sensor_id →
> district` lookup and re-aggregate at district level — the rest of the pipeline
> does not need to change.

> **Timezone handling:** raw timestamps were tagged `IST`, `UTC`, or had no tag at
> all. `UTC` timestamps were converted with `+5:30`. Untagged timestamps (mostly
> plain ISO strings with a `T` separator) were assumed to already be local (IST) —
> documented here so it can be revisited if evidence suggests otherwise.
