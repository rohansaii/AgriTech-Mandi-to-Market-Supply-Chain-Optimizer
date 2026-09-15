import json
import re
import numpy as np
import pandas as pd
from pathlib import Path

RAW_DIR = Path("../raw_data")
OUT_DIR = Path("../data")
DOC_DIR = Path("../docs")
OUT_DIR.mkdir(parents=True, exist_ok=True)
DOC_DIR.mkdir(parents=True, exist_ok=True)

report_lines = []


def log(msg):
    print(msg)
    report_lines.append(msg)


# Confirmed from pattern analysis of raw dates across all files:
#   DD-DD-DDDD           -> MM-DD-YYYY   (max first-group value = 9 -> month)
#   DD/DD/DDDD           -> DD/MM/YYYY
#   DD.DD.DDDD           -> DD.MM.YYYY
#   DDDD-DD-DD / DDDD/DD/DD -> YYYY-MM-DD (ISO)
#   DD-Mon-DDDD           -> DD-Mon-YYYY (e.g. 16-May-2026)
DATE_RE_ISO_DASH = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATE_RE_ISO_SLASH = re.compile(r"^\d{4}/\d{2}/\d{2}$")
DATE_RE_MDY_DASH = re.compile(r"^\d{2}-\d{2}-\d{4}$")
DATE_RE_DMY_SLASH = re.compile(r"^\d{2}/\d{2}/\d{4}$")
DATE_RE_DMY_DOT = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
DATE_RE_MON = re.compile(r"^\d{2}-[A-Za-z]{3}-\d{4}$")


def parse_mixed_date(raw):
    if pd.isna(raw):
        return pd.NaT
    s = str(raw).strip()
    try:
        if DATE_RE_ISO_DASH.match(s):
            return pd.to_datetime(s, format="%Y-%m-%d")
        if DATE_RE_ISO_SLASH.match(s):
            return pd.to_datetime(s, format="%Y/%m/%d")
        if DATE_RE_MDY_DASH.match(s):
            return pd.to_datetime(s, format="%m-%d-%Y")
        if DATE_RE_DMY_SLASH.match(s):
            return pd.to_datetime(s, format="%d/%m/%Y")
        if DATE_RE_DMY_DOT.match(s):
            return pd.to_datetime(s, format="%d.%m.%Y")
        if DATE_RE_MON.match(s):
            return pd.to_datetime(s, format="%d-%b-%Y")
    except Exception:
        return pd.NaT
    return pd.NaT


def parse_mixed_datetime(raw):
    if pd.isna(raw):
        return pd.NaT
    s = str(raw).strip()
    s_clean = re.sub(r"\s*(IST|UTC)\s*$", "", s)
    fmts = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%m-%d-%Y %I:%M %p",
        "%m-%d-%Y",
        "%d-%b-%Y %H:%M:%S",
        "%d-%b-%Y",
    ]
    for f in fmts:
        try:
            return pd.to_datetime(s_clean, format=f)
        except Exception:
            continue
    # last resort
    try:
        return pd.to_datetime(s_clean)
    except Exception:
        return pd.NaT


def normalize_mandi_id(raw):
    if pd.isna(raw):
        return np.nan
    digits = re.sub(r"\D", "", str(raw))
    if digits == "":
        return np.nan
    return f"MANDI{int(digits):03d}"


CROP_MAP = {
    # Wheat
    "wheat": "Wheat", "gehun": "Wheat", "kanak": "Wheat", "गेहूं": "Wheat",
    # Rice (milled)
    "rice": "Rice", "chawal": "Rice", "चावल": "Rice", "basmati": "Rice",
    # Paddy (unmilled rice) - kept distinct from Rice, see data dictionary note
    "paddy": "Paddy", "dhaan": "Paddy", "धान": "Paddy",
    # Maize / Corn
    "maize": "Maize", "corn": "Maize", "makka": "Maize", "makki": "Maize", "मक्का": "Maize",
    # Cotton
    "cotton": "Cotton", "kapas": "Cotton", "narma": "Cotton", "कपास": "Cotton",
    # Mustard
    "mustard": "Mustard", "sarson": "Mustard", "sarso": "Mustard", "सरसों": "Mustard",
    # Sugarcane
    "sugarcane": "Sugarcane", "ganna": "Sugarcane", "ganne": "Sugarcane", "गन्ना": "Sugarcane",
}


def normalize_crop(raw):
    if pd.isna(raw):
        return np.nan
    key = str(raw).strip().lower()
    return CROP_MAP.get(key, str(raw).strip().title())


def clean_price_string(raw):
    """₹1,234.56 / Rs. 1,234 / INR 1234 / 1234/- / '' -> float or NaN."""
    if pd.isna(raw):
        return np.nan
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).strip()
    if s == "":
        return np.nan
    s = s.replace("₹", "").replace("Rs.", "").replace("Rs", "") \
         .replace("INR", "").replace(",", "").replace("/-", "").strip()
    try:
        return float(s)
    except ValueError:
        return np.nan


def normalize_vehicle_no(raw):
    """Standardize Indian vehicle reg numbers to SS-NN-LL-NNNN, uppercase."""
    if pd.isna(raw):
        return np.nan
    s = str(raw).upper().replace(" ", "").replace("-", "")
    m = re.match(r"^([A-Z]{2})(\d{2})([A-Z]{2})(\d{4})$", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}-{m.group(4)}"
    return str(raw).strip()  # fallback: leave as-is, flagged separately


# ---------------------------------------------------------------------------
# 1. MANDI MASTER (dimension table)
# ---------------------------------------------------------------------------
log("## 1. dim_mandi (track3_mandi_master.csv)\n")
mm_raw = pd.read_csv(RAW_DIR / "track3_mandi_master.csv", dtype=str)
raw_rows = len(mm_raw)
log(f"- Raw rows: {raw_rows}")

mm = mm_raw.copy()
mm["mandi_id"] = mm["mandi_id"].apply(normalize_mandi_id)
mm["mandi_name"] = mm["mandi_name"].str.strip()
mm["district"] = mm["district"].str.strip().str.title()
mm["district"] = mm["district"].replace({"": np.nan})
mm["state"] = mm["state"].str.strip().str.title()
mm["mandi_type"] = mm["mandi_type"].str.strip().str.upper().replace(
    {"PRIVATE": "Private", "DIRECT": "Direct", "APMC": "APMC"}
)
mm["mandi_type"] = mm["mandi_type"].str.title().replace({"Apmc": "APMC"})
mm["total_area_acres"] = pd.to_numeric(mm["total_area_acres"], errors="coerce")

before_dedupe = len(mm)
mm = mm.drop_duplicates(subset=["mandi_id"], keep="first")
log(f"- Exact duplicate mandi_id rows removed: {before_dedupe - len(mm)}")
log(f"- Missing district after cleaning: {mm['district'].isna().sum()} (kept as NaN, no reliable source to impute from)")
log(f"- Missing mandi_type: {mm['mandi_type'].isna().sum()} -> filled 'Unknown'")
mm["mandi_type"] = mm["mandi_type"].fillna("Unknown")
log(f"- Missing total_area_acres: {mm['total_area_acres'].isna().sum()} -> left NaN (not used in core KPIs)")
log(f"- Cleaned rows: {len(mm)}\n")

mm.to_csv(OUT_DIR / "dim_mandi.csv", index=False)
mandi_district_lookup = mm.set_index("mandi_id")["district"].to_dict()

# ---------------------------------------------------------------------------
# 2. MANDI ARRIVALS (fact table)
# ---------------------------------------------------------------------------
log("## 2. fact_arrivals (track3_mandi_arrivals.csv)\n")
ar_raw = pd.read_csv(RAW_DIR / "track3_mandi_arrivals.csv", dtype=str)
raw_rows = len(ar_raw)
log(f"- Raw rows: {raw_rows}")

ar = ar_raw.copy()

# 2a. Drop exact full-row duplicates
before = len(ar)
ar = ar.drop_duplicates()
log(f"- Exact duplicate rows removed: {before - len(ar)}")

# 2b. Missing arrival_id -> synthetic, flagged
missing_id_mask = ar["arrival_id"].isna()
ar.loc[missing_id_mask, "arrival_id"] = [
    f"ARR_GEN_{i:06d}" for i in range(missing_id_mask.sum())
]
ar["arrival_id_was_missing"] = missing_id_mask
log(f"- Missing arrival_id: {missing_id_mask.sum()} -> generated synthetic IDs (ARR_GEN_######), flagged in arrival_id_was_missing")

# remaining duplicate arrival_ids among originally-present ids (data entry re-keying) -> drop, keep first
before = len(ar)
ar = ar.drop_duplicates(subset=["arrival_id"], keep="first")
log(f"- Rows dropped for duplicate arrival_id (after synthetic ID assignment): {before - len(ar)}")

# 2c. Date
ar["arrival_date"] = ar["date"].apply(parse_mixed_date)
log(f"- Unparseable dates: {ar['arrival_date'].isna().sum()}")

# 2d. Mandi ID
ar["mandi_id"] = ar["mandi_id"].apply(normalize_mandi_id)
unmatched_mandi = (~ar["mandi_id"].isin(mm["mandi_id"])).sum()
log(f"- Arrival rows whose mandi_id has no match in dim_mandi: {unmatched_mandi}")

# 2e. Crop name canonicalization (store both raw + canonical)
ar["raw_crop_name"] = ar["crop_name"]
ar["crop_name"] = ar["crop_name"].apply(normalize_crop)

# 2f. Variety
ar["variety"] = ar["variety"].fillna("Unknown")

# 2g. Quantity + unit: some rows have unit embedded in the quantity string
def split_qty_unit(qty_raw, unit_raw):
    qty_raw = str(qty_raw).strip()
    # remove thousands separators
    qty_clean = qty_raw.replace(",", "")
    m = re.match(r"^(-?[\d.]+)\s*([A-Za-z]+)?$", qty_clean)
    if m:
        num = float(m.group(1))
        embedded_unit = m.group(2)
        unit = unit_raw if pd.notna(unit_raw) and str(unit_raw).strip() != "" else embedded_unit
        return num, unit
    try:
        return float(qty_clean), unit_raw
    except ValueError:
        return np.nan, unit_raw


qty_unit = ar.apply(lambda r: split_qty_unit(r["arrival_quantity"], r["unit"]), axis=1)
ar["quantity_raw_value"] = [q for q, u in qty_unit]
ar["unit_resolved"] = [u for q, u in qty_unit]

UNIT_TO_QTL = {
    "t": 10, "tonnes": 10, "tonne": 10, "mt": 10,
    "qtl": 1, "q": 1, "quintal": 1, "quintals": 1,
    "kg": 0.01, "kgs": 0.01, "kilo": 0.01,
}


def to_qtl(value, unit):
    if pd.isna(value) or pd.isna(unit):
        return np.nan
    factor = UNIT_TO_QTL.get(str(unit).strip().lower())
    if factor is None:
        return np.nan
    return value * factor


ar["arrival_quantity_qtl"] = ar.apply(
    lambda r: to_qtl(r["quantity_raw_value"], r["unit_resolved"]), axis=1
)
still_missing_unit = ar["arrival_quantity_qtl"].isna().sum()
log(f"- Rows where unit could not be resolved even after parsing embedded text: {still_missing_unit} (quantity left NaN)")

# 2h. Negative quantities -> impossible; treat as sign/typo error, take abs, flag
neg_mask = ar["arrival_quantity_qtl"] < 0
ar["qty_was_negative"] = neg_mask.fillna(False)
ar.loc[neg_mask, "arrival_quantity_qtl"] = ar.loc[neg_mask, "arrival_quantity_qtl"].abs()
log(f"- Negative quantities corrected to absolute value (flagged qty_was_negative): {neg_mask.sum()}")

# 2i. Farmer count
ar["farmer_count"] = pd.to_numeric(ar["farmer_count"], errors="coerce")
missing_fc = ar["farmer_count"].isna().sum()
ar["farmer_count_was_missing"] = ar["farmer_count"].isna()
ar["farmer_count"] = ar.groupby("crop_name")["farmer_count"].transform(
    lambda s: s.fillna(s.median())
)
log(f"- Missing farmer_count: {missing_fc} -> imputed with median farmer_count per crop, flagged farmer_count_was_missing")

# Final column selection
ar_final = ar[[
    "arrival_id", "arrival_date", "mandi_id", "crop_name", "raw_crop_name",
    "variety", "arrival_quantity_qtl", "farmer_count",
    "arrival_id_was_missing", "qty_was_negative", "farmer_count_was_missing",
]].rename(columns={"arrival_date": "date"})

ar_final.to_csv(OUT_DIR / "fact_arrivals.csv", index=False)
log(f"- Cleaned rows: {len(ar_final)} (from {raw_rows} raw rows)\n")

# ---------------------------------------------------------------------------
# 3. PRICE & MSP (fact table)
# ---------------------------------------------------------------------------
log("## 3. fact_price_msp (track3_price_and_msp.json)\n")
with open(RAW_DIR / "track3_price_and_msp.json") as f:
    pr_data = json.load(f)
pr = pd.DataFrame(pr_data)
raw_rows = len(pr)
log(f"- Raw rows: {raw_rows}")

before = len(pr)
pr = pr.drop_duplicates()
log(f"- Exact duplicate rows removed: {before - len(pr)}")

pr["price_date"] = pr["date"].apply(parse_mixed_date)
log(f"- Unparseable dates: {pr['price_date'].isna().sum()}")

pr["mandi_id"] = pr["mandi_id"].apply(normalize_mandi_id)
missing_mandi = pr["mandi_id"].isna().sum()
log(f"- Missing mandi_id: {missing_mandi} (kept as NaN; can't be safely guessed)")

pr["raw_crop_name"] = pr["crop_name"]
pr["crop_name"] = pr["crop_name"].apply(normalize_crop)

for col in ["min_price", "max_price", "modal_price", "msp"]:
    n_before = pr[col].isna().sum() if pr[col].dtype != object else (pr[col] == "").sum()
    pr[col] = pr[col].apply(clean_price_string)
    log(f"- {col}: cleaned currency symbols/commas; missing/unparseable after cleaning: {pr[col].isna().sum()}")

# Fill missing district from mandi master where possible
district_missing_before = pr["district"].isna().sum() + (pr["district"] == "").sum()
pr["district"] = pr["district"].replace({"": np.nan})
pr["district"] = pr.apply(
    lambda r: r["district"] if pd.notna(r["district"]) else mandi_district_lookup.get(r["mandi_id"], np.nan),
    axis=1,
)
log(f"- Missing district: {district_missing_before} -> {pr['district'].isna().sum()} after backfilling from dim_mandi via mandi_id")
pr["district"] = pr["district"].str.title() if pr["district"].dtype == object else pr["district"]

# Price sanity flag: modal price below MSP (price crash) - this is a business metric, not an error
pr["is_price_crash"] = pr["modal_price"] < pr["msp"]

pr_final = pr[[
    "record_id", "price_date", "mandi_id", "district", "crop_name", "raw_crop_name",
    "min_price", "max_price", "modal_price", "msp", "is_price_crash",
]].rename(columns={"price_date": "date"})

pr_final.to_csv(OUT_DIR / "fact_price_msp.csv", index=False)
log(f"- Cleaned rows: {len(pr_final)} (from {raw_rows} raw rows)\n")

# ---------------------------------------------------------------------------
# 4. TRANSPORT LOGISTICS (fact table)
# ---------------------------------------------------------------------------
log("## 4. fact_transport (track3_transport_logistics.csv)\n")
tr_raw = pd.read_csv(RAW_DIR / "track3_transport_logistics.csv", dtype=str)
raw_rows = len(tr_raw)
log(f"- Raw rows: {raw_rows}")

tr = tr_raw.copy()
before = len(tr)
tr = tr.drop_duplicates()
log(f"- Exact duplicate rows removed: {before - len(tr)}")

tr["mandi_id"] = tr["mandi_id"].apply(normalize_mandi_id)
tr["departure_dt"] = tr["departure_time"].apply(parse_mixed_datetime)
tr["arrival_dt"] = tr["arrival_time"].apply(parse_mixed_datetime)
log(f"- Unparseable departure timestamps: {tr['departure_dt'].isna().sum()}")
log(f"- Missing/unparseable arrival timestamps: {tr['arrival_dt'].isna().sum()}")

# distance -> km
tr["distance"] = pd.to_numeric(tr["distance"], errors="coerce")
missing_unit = tr["distance_unit"].isna().sum()
tr["distance_unit_assumed"] = tr["distance_unit"].isna()
tr["distance_unit"] = tr["distance_unit"].fillna("km")  # documented assumption: majority unit, most trips regional
log(f"- Missing distance_unit: {missing_unit} -> assumed 'km' (documented assumption), flagged distance_unit_assumed")
tr["distance_km"] = np.where(
    tr["distance_unit"].str.lower() == "miles",
    tr["distance"] * 1.60934,
    tr["distance"],
)

# transit hours: recompute from timestamps where possible, else use given value if positive
computed_hours = (tr["arrival_dt"] - tr["departure_dt"]).dt.total_seconds() / 3600
given_hours = pd.to_numeric(tr["transit_hours"], errors="coerce")

tr["transit_hours_final"] = np.where(
    computed_hours.notna() & (computed_hours > 0), computed_hours,
    np.where(given_hours > 0, given_hours, np.nan),
)
invalid_transit = ((given_hours < 0) | (tr["transit_hours_final"].isna())).sum()
log(f"- Transit_hours recomputed from timestamps where possible; rows with negative/invalid transit_hours corrected or left NaN: {invalid_transit}")

# vehicle_no standardization
tr["vehicle_no_raw"] = tr["vehicle_no"]
tr["vehicle_no"] = tr["vehicle_no"].apply(normalize_vehicle_no)
missing_vehicle = tr["vehicle_no"].isna().sum()
tr["vehicle_no"] = tr["vehicle_no"].fillna("Unknown")
log(f"- Missing vehicle_no: {missing_vehicle} -> filled 'Unknown'")

missing_driver = tr["driver_id"].isna().sum()
tr["driver_id"] = tr["driver_id"].fillna("Unknown")
log(f"- Missing driver_id: {missing_driver} -> filled 'Unknown'")

tr_final = tr[[
    "trip_id", "mandi_id", "destination_warehouse", "departure_dt", "arrival_dt",
    "transit_hours_final", "distance_km", "distance_unit_assumed", "vehicle_no",
    "vehicle_no_raw", "driver_id",
]].rename(columns={
    "departure_dt": "departure_time", "arrival_dt": "arrival_time",
    "transit_hours_final": "transit_hours",
})

tr_final.to_csv(OUT_DIR / "fact_transport.csv", index=False)
log(f"- Cleaned rows: {len(tr_final)} (from {raw_rows} raw rows)\n")

# ---------------------------------------------------------------------------
# 5. WEATHER SENSORS (aggregated daily dimension)
# ---------------------------------------------------------------------------
log("## 5. dim_weather_daily (track3_weather_sensors.xlsx)\n")
we_raw = pd.read_excel(RAW_DIR / "track3_weather_sensors.xlsx")
raw_rows = len(we_raw)
log(f"- Raw rows: {raw_rows}")

we = we_raw.copy()


def parse_weather_ts(raw):
    if pd.isna(raw):
        return pd.NaT, None
    s = str(raw).strip()
    tz = None
    if s.endswith("IST"):
        tz = "IST"
    elif s.endswith("UTC"):
        tz = "UTC"
    dt = parse_mixed_datetime(s)
    return dt, tz


parsed = we["timestamp"].apply(parse_weather_ts)
we["dt_raw"] = [p[0] for p in parsed]
we["tz_raw"] = [p[1] for p in parsed]
missing_ts = we["dt_raw"].isna().sum()
log(f"- Missing/unparseable timestamps: {missing_ts} (rows dropped, cannot bucket by date)")
we = we.dropna(subset=["dt_raw"])

# Convert UTC -> IST (UTC+5:30). Untagged ISO-T timestamps (no tz label) are
# assumed already local (IST) per dataset notes; documented assumption below.
we["dt_ist"] = np.where(
    we["tz_raw"] == "UTC",
    we["dt_raw"] + pd.Timedelta(hours=5, minutes=30),
    we["dt_raw"],
)
we["dt_ist"] = pd.to_datetime(we["dt_ist"])
we["date"] = we["dt_ist"].dt.date
n_utc = (we["tz_raw"] == "UTC").sum()
n_untagged = we["tz_raw"].isna().sum()
log(f"- Timestamps converted from UTC to IST: {n_utc}")
log(f"- Timestamps with no explicit tz label: {n_untagged} -> assumed already IST (documented assumption)")


# temperature -> Celsius
def parse_temp(value, unit):
    if pd.isna(value):
        return np.nan
    s = str(value).strip()
    embedded_c = s.upper().endswith("C") and "°" in s
    embedded_f = s.upper().endswith("F") and "°" in s
    num = re.sub(r"[^\d.\-]", "", s)
    try:
        num = float(num)
    except ValueError:
        return np.nan
    unit_str = str(unit).strip().lower() if pd.notna(unit) else ""
    is_f = embedded_f or unit_str in ("f", "fahrenheit")
    is_c = embedded_c or unit_str in ("c", "celsius", "°c")
    if is_f:
        return round((num - 32) * 5 / 9, 2)
    return num  # already Celsius (explicit or default assumption)


we["temperature_c"] = we.apply(lambda r: parse_temp(r["temperature"], r["temp_unit"]), axis=1)
log(f"- Temperature values standardized to Celsius; missing after parsing: {we['temperature_c'].isna().sum()}")

# rainfall -> mm
we["rain_unit_norm"] = we["rain_unit"].str.strip().str.lower()
we["rainfall_mm"] = np.where(
    we["rain_unit_norm"].isin(["in", "inch", "inches"]),
    we["rainfall"] * 25.4,
    we["rainfall"],
)
neg_rain = we["rainfall_mm"] < 0
we.loc[neg_rain, "rainfall_mm"] = np.nan
log(f"- Rainfall converted inches->mm where flagged; negative/impossible rainfall values nulled: {neg_rain.sum()}")
log(f"- Missing rainfall after cleaning: {we['rainfall_mm'].isna().sum()}")

we["humidity_percent"] = pd.to_numeric(we["humidity_percent"], errors="coerce")

# Sensor -> district mapping: NOT present in the raw data (no join key connects
# sensor_id to mandi_id/district). Per dataset notes this is "implied" but no
# concrete mapping exists, so we aggregate at NATIONAL daily level rather than
# fabricate a sensor-to-district join. This is documented as a key assumption
# in the data dictionary / README.
daily = we.groupby("date").agg(
    avg_temperature_c=("temperature_c", "mean"),
    total_rainfall_mm=("rainfall_mm", "sum"),
    avg_humidity_percent=("humidity_percent", "mean"),
    sensor_reading_count=("sensor_id", "count"),
).reset_index()

daily.to_csv(OUT_DIR / "dim_weather_daily.csv", index=False)
log(f"- Cleaned rows: {len(daily)} daily records (from {raw_rows} raw sensor readings, {we['sensor_id'].nunique()} sensors)\n")


with open(DOC_DIR / "cleaning_report.md", "w") as f:
    f.write("# Track 3 - Data Rescue & Cleaning Report\n\n")
    f.write("\n".join(report_lines))

print("\nDone. Cleaned files written to", OUT_DIR)
