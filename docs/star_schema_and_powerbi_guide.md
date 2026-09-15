# Star Schema & Power BI Setup Guide — Track 3

## 1. Model overview

```
                         ┌───────────────┐
                         │   dim_mandi   │
                         │  mandi_id (PK)│
                         │  mandi_name   │
                         │  district     │
                         │  state        │
                         │  mandi_type   │
                         └───────┬───────┘
              ┌──────────────────┼──────────────────┐
              │                  │                   │
    ┌─────────▼────────┐ ┌───────▼─────────┐ ┌───────▼──────────┐
    │  fact_arrivals    │ │ fact_price_msp  │ │  fact_transport   │
    │  mandi_id (FK)    │ │ mandi_id (FK)   │ │  mandi_id (FK)    │
    │  date             │ │ date            │ │  departure_time   │
    │  crop_name        │ │ crop_name       │ │  destination_wh   │
    │  arrival_qty_qtl  │ │ modal/min/max   │ │  transit_hours    │
    │  farmer_count     │ │ msp             │ │  distance_km      │
    └─────────┬─────────┘ └────────┬────────┘ └─────────┬─────────┘
              │                    │                     │
              └────────────┬───────┴──────────┬──────────┘
                            │                  │
                     ┌──────▼──────┐   ┌───────▼─────────┐
                     │  dim_date   │   │ dim_weather_daily│
                     │  date (PK)  │◄──┤  date (PK, join  │
                     │             │   │  is by date only)│
                     └─────────────┘   └──────────────────┘
```

`dim_weather_daily` has **no mandi/district key** (see data dictionary — no sensor
mapping exists in source), so it only joins to the facts through a shared `dim_date`
table, not through `dim_mandi`. Build correlation visuals (e.g. rainfall vs.
arrivals) using `date` as the only common axis.

## 2. Steps in Power BI Desktop

1. **Get Data → Text/CSV** for all five files in `data/`.
2. Create a `dim_date` calendar table (Modeling → New Table):
   ```
   dim_date = CALENDAR(MIN(fact_arrivals[date]), MAX(fact_arrivals[date]))
   ```
   Then mark it as a Date Table (Modeling → Mark as Date Table).
3. **Relationships** (Model view):
   - `dim_mandi[mandi_id]` (1) → `fact_arrivals[mandi_id]` (*)
   - `dim_mandi[mandi_id]` (1) → `fact_price_msp[mandi_id]` (*)
   - `dim_mandi[mandi_id]` (1) → `fact_transport[mandi_id]` (*)
   - `dim_date[date]` (1) → `fact_arrivals[date]` (*)
   - `dim_date[date]` (1) → `fact_price_msp[date]` (*)
   - `dim_date[date]` (1) → `dim_weather_daily[date]` (*)
   - For `fact_transport`, add a calculated column `trip_date = DATE(YEAR(departure_time), MONTH(departure_time), DAY(departure_time))` and relate that to `dim_date`.
4. Set all relationships to **single direction** from dim → fact to avoid ambiguity, except where you specifically need bidirectional filtering (e.g. filtering weather by a crop slicer via arrivals — usually not needed).

## 3. Core DAX measures

```DAX
Total Arrivals (Qtl) = SUM(fact_arrivals[arrival_quantity_qtl])

Avg Modal Price = AVERAGE(fact_price_msp[modal_price])

Avg MSP = AVERAGE(fact_price_msp[msp])

Price Crash Instances =
CALCULATE(COUNTROWS(fact_price_msp), fact_price_msp[is_price_crash] = TRUE)

Price Crash Rate =
DIVIDE([Price Crash Instances], COUNTROWS(fact_price_msp))

Avg Transit Time (hrs) = AVERAGE(fact_transport[transit_hours])

-- Define "delayed" as anything above the 75th percentile transit time,
-- or hardcode a business threshold (e.g. 12 hours) once agreed with the client.
Transit Delay Rate =
VAR Threshold = 12
RETURN DIVIDE(
    CALCULATE(COUNTROWS(fact_transport), fact_transport[transit_hours] > Threshold),
    COUNTROWS(fact_transport)
)

Top Mandi by Arrivals =
CALCULATE([Total Arrivals (Qtl)], TOPN(5, ALL(dim_mandi[mandi_name]), [Total Arrivals (Qtl)]))
```

For the **rainfall vs. arrivals correlation**, since weather is at national daily
grain, build a table visual/scatter of `dim_date[date]` × `[Total Arrivals (Qtl)]`
× `dim_weather_daily[total_rainfall_mm]`, or use a Python/R visual in Power BI with
`scipy.stats.pearsonr` for a single correlation coefficient.

## 4. Suggested dashboard pages (maps to the rubric's "Storytelling" criterion)

1. **Executive Overview** — KPI cards (Total Arrivals, Avg Modal Price vs MSP, Price
   Crash Rate, Avg Transit Time), a date slicer, and a state/crop slicer.
2. **Price Discovery** — Modal price vs MSP trend line by crop, table of mandis
   currently below MSP (`is_price_crash = TRUE`), price distribution by crop.
3. **Supply Chain** — Transit time by warehouse, distance vs. transit time
   scatter, delay-rate by route, top mandis by arrival volume.
4. **Weather Impact** — Daily rainfall/temperature trend overlaid with total
   arrivals, to visually support the correlation story.
