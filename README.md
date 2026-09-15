# Track 3 – AgriTech: Mandi-to-Market Supply Chain Optimizer

TransOrg AgentIQ Datathon submission. Takes messy, real-world mandi/crop data and turns it into a clean, query-ready analytics layer — with a Power BI dashboard on top and a text-to-chart AI agent as a bonus layer.

> **Note:** This is a data cleaning + Power BI analytics project, not a production system. All cleaning decisions (including the judgment calls) are documented in `docs/data_dictionary.md` so the pipeline is auditable, not a black box.

🔗 **Live Dashboard:** _coming soon — will be linked here once published_

---

## 📊 Project Overview

- **Source files cleaned:** 5 raw datasets → 5 query-ready CSVs
- **Domains covered:** Mandi arrivals, price vs. MSP, transport/logistics, weather
- **Core metrics:** Total arrivals (Quintals), Modal Price vs. MSP, Price Crash instances, Transit time & delay rate, Top mandis by volume
- **Data source:** raw CSV/Excel files with mandi IDs, crop names, arrival quantities, prices, transport records, and daily weather — all inconsistently formatted (see cleaning table below)

---

## 🗂️ Pipeline Stages

### 1. Data Rescue (`scripts/clean_pipeline.py`)
Reads the raw files and regenerates everything in `data/` plus `docs/cleaning_report.md`. Fully reproducible and idempotent — re-run it as many times as you like.

### 2. Analytics Layer (`data/`)
Five clean, star-schema-ready CSVs:
- `dim_mandi.csv`
- `fact_arrivals.csv`
- `fact_price_msp.csv`
- `fact_transport.csv`
- `dim_weather_daily.csv`

### 3. Power BI Dashboard
Built on top of the cleaned CSVs, following `docs/star_schema_and_powerbi_guide.md` — relationships, DAX measures, and four dashboard pages covering arrivals, price/MSP comparison, transport, and weather trends.

### 4. Bonus Agent (`bonus_agent/app.py`)
A Streamlit text-to-chart agent. Type a question like *"Plot the daily arrival trend of Wheat in Amritsar mandi vs MSP for the last 30 days"* and it picks the right chart type and generates it, plus a one-line summary.

---

## 🧮 Key Cleaning Logic

| Issue | Fix |
|---|---|
| 4 different mandi_id formats (`MANDI001`, `MANDI-034`, `mandi_031`, `M017`, `034`) | Regex-normalized to `MANDI0##` everywhere |
| Crop names in English/Hindi/Punjabi, mixed case | Canonical crop mapping, raw value preserved in `raw_crop_name` |
| Quantities in Tonnes/Quintals/KG, sometimes with the unit embedded in the number | Parsed and converted to Quintals throughout |
| 5 different date formats across all files | Format detected per-pattern, parsed to ISO dates |
| Negative arrival quantities & transit hours | Treated as sign errors, corrected and flagged rather than dropped |
| Prices as `₹1,234`, `Rs. 1,234`, `INR 1234`, `1234/-` | Currency symbols/commas stripped, converted to numeric |
| Weather timestamps in UTC/IST, temps in °C/°F, rainfall in mm/inches | Standardized to IST / Celsius / mm |
| Vehicle numbers in 6+ spacing/casing styles | Standardized to `SS-NN-LL-NNNN` |
| Duplicate rows across every file | Exact duplicates dropped; near-duplicates re-keyed with synthetic IDs |
| No sensor→district mapping in weather file | Not fabricated — weather aggregated to a national daily series, documented as a limitation |

Full detail and reasoning for every decision (including the ones that could reasonably go another way, like Rice vs. Paddy or assuming missing distance units are km) is in `docs/data_dictionary.md`.

---

## 🛠️ Tech Stack

- **Python (pandas, numpy, openpyxl)** – cleaning pipeline
- **Power BI Desktop** – data modeling, DAX measures, report design
- **Streamlit + Plotly** – bonus text-to-chart agent

---

## 📁 Repository Structure

```
track3_clean/
│
├── README.md
│
├── data/
│   ├── dim_mandi.csv
│   ├── fact_arrivals.csv
│   ├── fact_price_msp.csv
│   ├── fact_transport.csv
│   └── dim_weather_daily.csv
│
├── scripts/
│   └── clean_pipeline.py
│
├── docs/
│   ├── data_dictionary.md
│   ├── cleaning_report.md
│   └── star_schema_and_powerbi_guide.md
│
├── bonus_agent/
│   └── app.py
│
└── images/
    ├── cover_page.png
    ├── executive_overview.png
    ├── price_discovery.png
    ├── supply_chain.png
    ├── weather_impact.png
    └── advanced_insights.png
```

---

## ▶️ How to Run

**Cleaning pipeline** (cleaned CSVs are already in `data/`, so this is optional):
```bash
pip install pandas numpy openpyxl
cd scripts
python3 clean_pipeline.py
```

**Power BI dashboard:**
Load the 5 CSVs from `data/`, then follow `docs/star_schema_and_powerbi_guide.md` for relationships, DAX measures, and dashboard pages.

**Bonus agent:**
```bash
pip install streamlit plotly pandas
cd bonus_agent
streamlit run app.py
```

---

## 📸 Preview

| Cover | Executive Overview & Price Discovery |
|---|---|
| ![Cover](images/cover_page.png) | ![Executive Overview](images/executive_overview.png) |

| Price Discovery | Supply Chain |
|---|---|
| ![Price Discovery](images/price_discovery.png) | ![Supply Chain](images/supply_chain.png) |

| Weather Impact | Advanced Insights |
|---|---|
| ![Weather Impact](images/weather_impact.png) | ![Advanced Insights](images/advanced_insights.png) |

---

## 🚀 Future Improvements

- Add district-level weather mapping once sensor metadata is available
- Automate cleaning + refresh on a schedule instead of manual re-runs
- Add year-over-year arrival and price trend comparisons as more seasons of data come in
