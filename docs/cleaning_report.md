# Track 3 - Data Rescue & Cleaning Report

## 1. dim_mandi (track3_mandi_master.csv)

- Raw rows: 60
- Exact duplicate mandi_id rows removed: 3
- Missing district after cleaning: 4 (kept as NaN, no reliable source to impute from)
- Missing mandi_type: 11 -> filled 'Unknown'
- Missing total_area_acres: 6 -> left NaN (not used in core KPIs)
- Cleaned rows: 57

## 2. fact_arrivals (track3_mandi_arrivals.csv)

- Raw rows: 25750
- Exact duplicate rows removed: 750
- Missing arrival_id: 476 -> generated synthetic IDs (ARR_GEN_######), flagged in arrival_id_was_missing
- Rows dropped for duplicate arrival_id (after synthetic ID assignment): 0
- Unparseable dates: 0
- Arrival rows whose mandi_id has no match in dim_mandi: 0
- Rows where unit could not be resolved even after parsing embedded text: 0 (quantity left NaN)
- Negative quantities corrected to absolute value (flagged qty_was_negative): 1233
- Missing farmer_count: 3800 -> imputed with median farmer_count per crop, flagged farmer_count_was_missing
- Cleaned rows: 25000 (from 25750 raw rows)

## 3. fact_price_msp (track3_price_and_msp.json)

- Raw rows: 12000
- Exact duplicate rows removed: 0
- Unparseable dates: 0
- Missing mandi_id: 1235 (kept as NaN; can't be safely guessed)
- min_price: cleaned currency symbols/commas; missing/unparseable after cleaning: 598
- max_price: cleaned currency symbols/commas; missing/unparseable after cleaning: 598
- modal_price: cleaned currency symbols/commas; missing/unparseable after cleaning: 610
- msp: cleaned currency symbols/commas; missing/unparseable after cleaning: 2377
- Missing district: 1546 -> 271 after backfilling from dim_mandi via mandi_id
- Cleaned rows: 12000 (from 12000 raw rows)

## 4. fact_transport (track3_transport_logistics.csv)

- Raw rows: 10400
- Exact duplicate rows removed: 400
- Unparseable departure timestamps: 0
- Missing/unparseable arrival timestamps: 1006
- Missing distance_unit: 992 -> assumed 'km' (documented assumption), flagged distance_unit_assumed
- Transit_hours recomputed from timestamps where possible; rows with negative/invalid transit_hours corrected or left NaN: 675
- Missing vehicle_no: 1560 -> filled 'Unknown'
- Missing driver_id: 1512 -> filled 'Unknown'
- Cleaned rows: 10000 (from 10400 raw rows)

## 5. dim_weather_daily (track3_weather_sensors.xlsx)

- Raw rows: 15000
- Missing/unparseable timestamps: 1555 (rows dropped, cannot bucket by date)
- Timestamps converted from UTC to IST: 5141
- Timestamps with no explicit tz label: 2266 -> assumed already IST (documented assumption)
- Temperature values standardized to Celsius; missing after parsing: 0
- Rainfall converted inches->mm where flagged; negative/impossible rainfall values nulled: 1342
- Missing rainfall after cleaning: 2035
- Cleaned rows: 252 daily records (from 15000 raw sensor readings, 51 sensors)
