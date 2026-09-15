"""
AgriTech: Mandi-to-Market Supply Chain Optimizer
Bonus AI Analytics Agent — TransOrg AgentIQ Datathon Track 3

Executive Theme: AgriTech Deep Navy & Cyan Glassmorphism
Technologies: Python, Streamlit, Pandas, Plotly, NumPy
"""

import os
import re
import datetime
from typing import Dict, Any, Optional, Tuple, List

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ==============================================================================
# CONFIGURATION & THEME
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))

# Executive Theme Palette (matching the AgriTech UI theme)
COLOR_PALETTE = {
    "cyan_glow": "#00d2ff",      # Vibrant Cyan
    "sky_blue": "#38bdf8",       # Sky Blue
    "electric_blue": "#0ea5e9",  # Electric Blue
    "deep_blue": "#0284c7",      # Accent Blue
    "gold_wheat": "#f59e0b",     # Golden Wheat
    "leaf_green": "#22c55e",     # Leaf Green
    "emerald": "#10b981",        # Emerald
    "danger_coral": "#ef4444",   # Alert / Crash Coral
    "purple": "#a855f7",         # Purple
    "bg_dark": "#040d1a",        # Deepest Midnight
    "card_bg": "#091a33",        # Glass Dark Navy
    "card_border": "rgba(56, 189, 248, 0.25)",
    "grid_color": "rgba(56, 189, 248, 0.1)",
    "text_light": "#f8fafc",     # Off White
    "text_muted": "#94a3b8",     # Slate Blue
}

CANONICAL_CROPS = ["Wheat", "Rice", "Paddy", "Maize", "Cotton", "Mustard", "Sugarcane"]

CROP_SYNONYMS = {
    "wheat": "Wheat", "gehun": "Wheat", "gehu": "Wheat", "kanak": "Wheat",
    "rice": "Rice", "chawal": "Rice", "basmati": "Rice",
    "paddy": "Paddy", "dhaan": "Paddy", "dhan": "Paddy",
    "maize": "Maize", "corn": "Maize", "makka": "Maize", "makki": "Maize",
    "cotton": "Cotton", "kapas": "Cotton", "narma": "Cotton",
    "mustard": "Mustard", "sarson": "Mustard", "sarso": "Mustard", "rai": "Mustard",
    "sugarcane": "Sugarcane", "ganna": "Sugarcane", "ganne": "Sugarcane",
}

WAREHOUSE_LIST = ["WH-North", "WH-South", "WH-East", "WH-West", "WH-Central", "Export-Terminal"]
DELAY_THRESHOLD_HOURS = 12.0


# ==============================================================================
# DATA LOADER & CACHING
# ==============================================================================
@st.cache_data(show_spinner=False)
def load_datasets(data_dir: str) -> Dict[str, pd.DataFrame]:
    """Loads all 5 cleaned datasets with appropriate datatypes."""
    files = {
        "dim_mandi": "dim_mandi.csv",
        "fact_arrivals": "fact_arrivals.csv",
        "fact_price_msp": "fact_price_msp.csv",
        "fact_transport": "fact_transport.csv",
        "dim_weather_daily": "dim_weather_daily.csv",
    }
    dfs = {}
    for key, filename in files.items():
        filepath = os.path.join(data_dir, filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Missing required dataset: {filepath}")
        dfs[key] = pd.read_csv(filepath)

    # Date parsing
    dfs["fact_arrivals"]["date"] = pd.to_datetime(dfs["fact_arrivals"]["date"])
    dfs["fact_price_msp"]["date"] = pd.to_datetime(dfs["fact_price_msp"]["date"])
    dfs["dim_weather_daily"]["date"] = pd.to_datetime(dfs["dim_weather_daily"]["date"])
    dfs["fact_transport"]["departure_time"] = pd.to_datetime(dfs["fact_transport"]["departure_time"], errors="coerce")
    dfs["fact_transport"]["arrival_time"] = pd.to_datetime(dfs["fact_transport"]["arrival_time"], errors="coerce")

    # Joined views
    dim_mandi = dfs["dim_mandi"]
    dfs["arrivals_joined"] = dfs["fact_arrivals"].merge(
        dim_mandi[["mandi_id", "mandi_name", "district", "state", "mandi_type"]],
        on="mandi_id",
        how="left"
    )
    dfs["price_joined"] = dfs["fact_price_msp"].merge(
        dim_mandi[["mandi_id", "mandi_name", "state", "mandi_type"]],
        on="mandi_id",
        how="left"
    )
    dfs["transport_joined"] = dfs["fact_transport"].merge(
        dim_mandi[["mandi_id", "mandi_name", "district", "state"]],
        on="mandi_id",
        how="left"
    )

    return dfs


# ==============================================================================
# NATURAL LANGUAGE INTENT & ENTITY PARSER
# ==============================================================================
class NLUParser:
    """Parses natural language queries into structured intents and filters."""

    def __init__(self, mandi_df: pd.DataFrame):
        self.mandi_names = mandi_df["mandi_name"].dropna().unique().tolist()
        self.districts = mandi_df["district"].dropna().unique().tolist()
        self.states = mandi_df["state"].dropna().unique().tolist()
        self.mandi_map = {name.lower(): name for name in self.mandi_names}
        self.district_map = {dist.lower(): dist for dist in self.districts}
        self.state_map = {state.lower(): state for state in self.states}

    def parse(self, query: str) -> Dict[str, Any]:
        q = query.strip().lower()
        entities: Dict[str, Any] = {
            "crop": None,
            "mandi": None,
            "district": None,
            "state": None,
            "warehouse": None,
            "top_n": 10,
            "sort_order": "desc",
            "metric": None,
            "intent": None,
            "domain": None,
        }

        # 1. Crop
        for syn, canonical in CROP_SYNONYMS.items():
            if re.search(r"\b" + re.escape(syn) + r"\b", q):
                entities["crop"] = canonical
                break

        # 2. Mandi
        for name_lower, canonical in self.mandi_map.items():
            base_name = name_lower.replace(" grain market", "").replace(" apmc", "").replace(" market", "").replace(" mandi", "")
            if base_name in q or name_lower in q:
                entities["mandi"] = canonical
                break

        # 3. District
        for dist_lower, canonical in self.district_map.items():
            if re.search(r"\b" + re.escape(dist_lower) + r"\b", q):
                entities["district"] = canonical
                break

        # 4. State
        for state_lower, canonical in self.state_map.items():
            if re.search(r"\b" + re.escape(state_lower) + r"\b", q):
                entities["state"] = canonical
                break

        # 5. Warehouse
        for wh in WAREHOUSE_LIST:
            wh_clean = wh.lower().replace("-", " ")
            if wh.lower() in q or wh_clean in q or wh.split("-")[-1].lower() in q:
                entities["warehouse"] = wh
                break

        # 6. Top N / Ranking
        top_match = re.search(r"\b(?:top|highest|first|best)\s+(\d+)\b", q)
        if top_match:
            entities["top_n"] = int(top_match.group(1))
            entities["sort_order"] = "desc"
        elif re.search(r"\b(?:bottom|lowest|least)\s+(\d+)\b", q):
            bottom_match = re.search(r"\b(?:bottom|lowest|least)\s+(\d+)\b", q)
            entities["top_n"] = int(bottom_match.group(1))
            entities["sort_order"] = "asc"
        elif "top 5" in q:
            entities["top_n"] = 5
        elif "top 10" in q:
            entities["top_n"] = 10

        # 7. Intent Classification
        # Weather & Cross-domain
        if any(w in q for w in ["rain", "rainfall", "temperature", "temp", "weather"]):
            entities["domain"] = "weather"
            if any(w in q for w in ["arrival", "arrivals", "volume", "affect", "compare", "versus", "vs"]):
                entities["intent"] = "WEATHER_VS_ARRIVALS"
                entities["metric"] = "total_rainfall_mm" if "rain" in q else "avg_temperature_c"
            elif "rain" in q or "rainfall" in q:
                entities["intent"] = "WEATHER_TREND_RAIN"
                entities["metric"] = "total_rainfall_mm"
            elif "temp" in q or "temperature" in q:
                entities["intent"] = "WEATHER_TREND_TEMP"
                entities["metric"] = "avg_temperature_c"
            else:
                entities["intent"] = "WEATHER_TREND_RAIN"
                entities["metric"] = "total_rainfall_mm"

        # Transport & Logistics
        elif any(w in q for w in ["transit", "transport", "trip", "trips", "warehouse", "distance", "delayed", "delay", "vehicle"]):
            entities["domain"] = "transport"
            if any(w in q for w in ["delay rate", "delayed", "delay percentage", "how many delayed"]):
                entities["intent"] = "TRANSPORT_DELAY_RATE"
                entities["metric"] = "delay_rate"
            elif "distance" in q and ("transit" in q or "time" in q or "versus" in q or "vs" in q):
                entities["intent"] = "TRANSPORT_DISTANCE_VS_TIME"
                entities["metric"] = "distance_vs_transit"
            elif "warehouse" in q:
                entities["intent"] = "TRANSPORT_BY_WAREHOUSE"
                entities["metric"] = "transit_hours"
            elif "mandi" in q:
                entities["intent"] = "TRANSPORT_BY_MANDI"
                entities["metric"] = "transit_hours"
            else:
                entities["intent"] = "TRANSPORT_BY_WAREHOUSE"
                entities["metric"] = "transit_hours"

        # Price & MSP
        elif any(w in q for w in ["price", "msp", "crash", "crashes", "modal price", "below msp", "cost"]):
            entities["domain"] = "price_msp"
            if "crash" in q or "crashes" in q:
                entities["intent"] = "PRICE_CRASH_BY_CROP"
                entities["metric"] = "is_price_crash"
            elif "below msp" in q:
                entities["intent"] = "PRICE_BELOW_MSP_MANDIS"
                entities["metric"] = "modal_price_vs_msp"
            elif "trend" in q or "over time" in q or "daily" in q:
                entities["intent"] = "PRICE_TREND"
                entities["metric"] = "modal_price"
            elif any(w in q for w in ["compare", "vs", "versus"]) and "msp" in q:
                entities["intent"] = "PRICE_MSP_COMPARE"
                entities["metric"] = "modal_price_vs_msp"
            elif "average" in q or "avg" in q or "mean" in q:
                entities["intent"] = "PRICE_AVERAGE_SUMMARY"
                entities["metric"] = "modal_price"
            else:
                if entities["crop"]:
                    entities["intent"] = "PRICE_MSP_COMPARE"
                else:
                    entities["intent"] = "PRICE_CRASH_BY_CROP"
                entities["metric"] = "modal_price"

        # Arrivals
        elif any(w in q for w in ["arrival", "arrivals", "volume", "quantity", "incoming", "qtl", "farmer", "farmers"]):
            entities["domain"] = "arrivals"
            if any(w in q for w in ["top", "highest", "which mandi", "mandis with", "rank"]):
                entities["intent"] = "ARRIVALS_BY_MANDI"
                entities["metric"] = "arrival_quantity_qtl"
            elif "by state" in q or ("state" in q and not entities["mandi"] and not entities["district"]):
                entities["intent"] = "ARRIVALS_BY_STATE"
                entities["metric"] = "arrival_quantity_qtl"
            elif "by crop" in q or ("crop" in q and not entities["crop"]):
                entities["intent"] = "ARRIVALS_BY_CROP"
                entities["metric"] = "arrival_quantity_qtl"
            elif any(w in q for w in ["trend", "over time", "daily", "timeline", "time"]):
                entities["intent"] = "ARRIVALS_TREND"
                entities["metric"] = "arrival_quantity_qtl"
            elif entities["mandi"] or entities["district"]:
                entities["intent"] = "ARRIVALS_BY_MANDI"
                entities["metric"] = "arrival_quantity_qtl"
            elif entities["crop"]:
                if "total" in q or "summary" in q:
                    entities["intent"] = "ARRIVALS_CROP_TOTAL"
                else:
                    entities["intent"] = "ARRIVALS_TREND"
                entities["metric"] = "arrival_quantity_qtl"
            else:
                entities["intent"] = "ARRIVALS_BY_CROP"
                entities["metric"] = "arrival_quantity_qtl"

        # Implicit Crop fallback
        elif entities["crop"]:
            entities["domain"] = "arrivals"
            entities["intent"] = "ARRIVALS_TREND"
            entities["metric"] = "arrival_quantity_qtl"

        else:
            entities["domain"] = "unsupported"
            entities["intent"] = "UNSUPPORTED"

        return entities


# ==============================================================================
# ANALYTICS & CALCULATION ENGINE
# ==============================================================================
class AnalyticsEngine:
    """Executes deterministic pandas calculations."""

    def __init__(self, dfs: Dict[str, pd.DataFrame]):
        self.dfs = dfs

    def execute(self, parsed: Dict[str, Any]) -> Tuple[Optional[pd.DataFrame], str, Dict[str, Any]]:
        intent = parsed["intent"]
        crop = parsed["crop"]
        mandi = parsed["mandi"]
        district = parsed["district"]
        state = parsed["state"]
        top_n = parsed.get("top_n", 10)

        # ----------------------------------------------------------------------
        # ARRIVALS
        # ----------------------------------------------------------------------
        if intent == "ARRIVALS_TREND":
            df = self.dfs["arrivals_joined"].copy()
            title_parts = ["Daily Arrivals"]
            if crop:
                df = df[df["crop_name"] == crop]
                title_parts.append(f"for {crop}")
            if district:
                df = df[df["district"] == district]
                title_parts.append(f"in {district} District")
            if mandi:
                df = df[df["mandi_name"] == mandi]
                title_parts.append(f"at {mandi}")
            if state:
                df = df[df["state"] == state]
                title_parts.append(f"in {state}")

            if df.empty:
                return None, "empty", {"message": "No arrival records match the requested filters."}

            res = df.groupby("date")["arrival_quantity_qtl"].sum().reset_index().sort_values("date")
            peak_row = res.loc[res["arrival_quantity_qtl"].idxmax()]
            total_qty = res["arrival_quantity_qtl"].sum()
            avg_daily = res["arrival_quantity_qtl"].mean()

            meta = {
                "title": " ".join(title_parts),
                "peak_date": peak_row["date"].strftime("%Y-%m-%d"),
                "peak_val": peak_row["arrival_quantity_qtl"],
                "total_qty": total_qty,
                "avg_daily": avg_daily,
                "crop": crop,
                "count_days": len(res),
            }
            return res, "line", meta

        elif intent in ["ARRIVALS_BY_MANDI", "ARRIVALS_SPECIFIC_LOCATION"]:
            df = self.dfs["arrivals_joined"].copy()
            if crop:
                df = df[df["crop_name"] == crop]
            if district:
                df = df[df["district"] == district]
            if state:
                df = df[df["state"] == state]

            if df.empty:
                return None, "empty", {"message": "No arrival records match the requested filters."}

            if mandi:
                df_mandi = df[df["mandi_name"] == mandi]
                if df_mandi.empty:
                    return None, "empty", {"message": f"No records found for mandi '{mandi}'."}
                res = df_mandi.groupby("date")["arrival_quantity_qtl"].sum().reset_index().sort_values("date")
                meta = {
                    "title": f"Arrival Trend at {mandi}" + (f" ({crop})" if crop else ""),
                    "mandi": mandi,
                    "total_qty": res["arrival_quantity_qtl"].sum(),
                    "peak_val": res["arrival_quantity_qtl"].max(),
                    "crop": crop,
                }
                return res, "line", meta

            res = df.groupby("mandi_name")["arrival_quantity_qtl"].sum().reset_index()
            res = res.sort_values("arrival_quantity_qtl", ascending=False).head(top_n)
            res = res.sort_values("arrival_quantity_qtl", ascending=True)

            top_mandi = res.iloc[-1]["mandi_name"]
            top_val = res.iloc[-1]["arrival_quantity_qtl"]
            total_crop_all = df["arrival_quantity_qtl"].sum()
            share_pct = (top_val / total_crop_all * 100) if total_crop_all > 0 else 0

            meta = {
                "title": f"Top {top_n} Mandis by Arrival Volume" + (f" ({crop})" if crop else ""),
                "top_mandi": top_mandi,
                "top_val": top_val,
                "share_pct": share_pct,
                "crop": crop,
                "district": district,
                "state": state,
            }
            return res, "horizontal_bar", meta

        elif intent == "ARRIVALS_BY_CROP":
            df = self.dfs["arrivals_joined"].copy()
            if state:
                df = df[df["state"] == state]
            if district:
                df = df[df["district"] == district]

            res = df.groupby("crop_name")["arrival_quantity_qtl"].sum().reset_index()
            res = res.sort_values("arrival_quantity_qtl", ascending=False)

            top_crop = res.iloc[0]["crop_name"]
            top_val = res.iloc[0]["arrival_quantity_qtl"]
            total_all = res["arrival_quantity_qtl"].sum()
            pct = (top_val / total_all * 100) if total_all > 0 else 0

            meta = {
                "title": "Total Arrivals by Canonical Crop" + (f" in {state}" if state else ""),
                "top_crop": top_crop,
                "top_val": top_val,
                "top_pct": pct,
                "total_all": total_all,
            }
            return res, "bar", meta

        elif intent == "ARRIVALS_BY_STATE":
            df = self.dfs["arrivals_joined"].copy()
            if crop:
                df = df[df["crop_name"] == crop]

            df = df.dropna(subset=["state"])
            res = df.groupby("state")["arrival_quantity_qtl"].sum().reset_index()
            res = res.sort_values("arrival_quantity_qtl", ascending=False)

            top_state = res.iloc[0]["state"]
            top_val = res.iloc[0]["arrival_quantity_qtl"]
            total_all = res["arrival_quantity_qtl"].sum()
            pct = (top_val / total_all * 100) if total_all > 0 else 0

            meta = {
                "title": f"Arrival Volume by State" + (f" ({crop})" if crop else ""),
                "top_state": top_state,
                "top_val": top_val,
                "top_pct": pct,
                "crop": crop,
            }
            return res, "bar", meta

        elif intent == "ARRIVALS_CROP_TOTAL":
            df = self.dfs["arrivals_joined"].copy()
            if crop:
                df = df[df["crop_name"] == crop]
            res = df.groupby("date")["arrival_quantity_qtl"].sum().reset_index().sort_values("date")
            total_qty = res["arrival_quantity_qtl"].sum()
            meta = {
                "title": f"Total Arrival Volume for {crop or 'All Crops'}",
                "total_qty": total_qty,
                "crop": crop,
            }
            return res, "line", meta

        # ----------------------------------------------------------------------
        # PRICE & MSP
        # ----------------------------------------------------------------------
        elif intent == "PRICE_MSP_COMPARE":
            df = self.dfs["fact_price_msp"].copy().dropna(subset=["modal_price", "msp"])
            if crop:
                df = df[df["crop_name"] == crop]
                res = df.groupby("date")[["modal_price", "msp"]].mean().reset_index().sort_values("date")
                chart_type = "line_multivariate"
                avg_modal = res["modal_price"].mean()
                avg_msp = res["msp"].mean()
                diff = avg_modal - avg_msp
                pct_diff = (diff / avg_msp * 100) if avg_msp > 0 else 0
                meta = {
                    "title": f"Modal Price vs MSP Trend: {crop}",
                    "crop": crop,
                    "avg_modal": avg_modal,
                    "avg_msp": avg_msp,
                    "diff": diff,
                    "pct_diff": pct_diff,
                }
            else:
                res = df.groupby("crop_name")[["modal_price", "msp"]].mean().reset_index()
                chart_type = "grouped_bar"
                meta = {
                    "title": "Average Modal Price vs MSP across Crops",
                    "df": res,
                }
            return res, chart_type, meta

        elif intent == "PRICE_CRASH_BY_CROP":
            df = self.dfs["fact_price_msp"].copy()
            res = df.groupby("crop_name")["is_price_crash"].agg(
                crash_count="sum", total_records="count"
            ).reset_index()
            res["crash_rate_pct"] = (res["crash_count"] / res["total_records"] * 100).round(2)
            res = res.sort_values("crash_count", ascending=False)

            top_crop = res.iloc[0]["crop_name"]
            top_count = int(res.iloc[0]["crash_count"])
            top_rate = res.iloc[0]["crash_rate_pct"]

            meta = {
                "title": "Price Crash Frequency & Rate by Crop (modal_price < MSP)",
                "top_crop": top_crop,
                "top_count": top_count,
                "top_rate": top_rate,
            }
            return res, "bar_crash", meta

        elif intent == "PRICE_BELOW_MSP_MANDIS":
            df = self.dfs["price_joined"].copy()
            crashes = df[df["is_price_crash"] == True].dropna(subset=["mandi_name"])

            res = crashes.groupby("mandi_name")["is_price_crash"].count().reset_index()
            res.columns = ["mandi_name", "crash_count"]
            res = res.sort_values("crash_count", ascending=True).tail(top_n)

            top_mandi = res.iloc[-1]["mandi_name"]
            top_crashes = res.iloc[-1]["crash_count"]

            meta = {
                "title": f"Top Mandis Trading Below MSP (Price Crashes)",
                "top_mandi": top_mandi,
                "top_crashes": top_crashes,
                "total_below_msp": len(crashes),
            }
            return res, "horizontal_bar_crashes", meta

        elif intent == "PRICE_TREND":
            df = self.dfs["fact_price_msp"].copy().dropna(subset=["modal_price"])
            if crop:
                df = df[df["crop_name"] == crop]
            res = df.groupby("date")["modal_price"].mean().reset_index().sort_values("date")

            peak_date = res.loc[res["modal_price"].idxmax()]["date"].strftime("%Y-%m-%d")
            peak_price = res["modal_price"].max()
            min_price = res["modal_price"].min()
            avg_price = res["modal_price"].mean()

            meta = {
                "title": f"Modal Price Trend ({crop or 'All Crops'})",
                "crop": crop,
                "peak_date": peak_date,
                "peak_price": peak_price,
                "min_price": min_price,
                "avg_price": avg_price,
            }
            return res, "line_price", meta

        elif intent == "PRICE_AVERAGE_SUMMARY":
            df = self.dfs["fact_price_msp"].copy().dropna(subset=["modal_price"])
            res = df.groupby("crop_name")[["modal_price", "min_price", "max_price"]].mean().reset_index()
            res = res.sort_values("modal_price", ascending=False)
            highest_crop = res.iloc[0]["crop_name"]
            highest_val = res.iloc[0]["modal_price"]
            meta = {
                "title": "Average Wholesale Price by Crop (₹ / Qtl)",
                "highest_crop": highest_crop,
                "highest_val": highest_val,
                "overall_avg": df["modal_price"].mean(),
            }
            return res, "bar_price_summary", meta

        # ----------------------------------------------------------------------
        # TRANSPORT & LOGISTICS
        # ----------------------------------------------------------------------
        elif intent == "TRANSPORT_BY_WAREHOUSE":
            df = self.dfs["fact_transport"].dropna(subset=["transit_hours"]).copy()
            res = df.groupby("destination_warehouse").agg(
                avg_transit_hours=("transit_hours", "mean"),
                total_trips=("trip_id", "count"),
                delayed_trips=("transit_hours", lambda s: (s > DELAY_THRESHOLD_HOURS).sum())
            ).reset_index()
            res["delay_rate_pct"] = (res["delayed_trips"] / res["total_trips"] * 100).round(2)
            res = res.sort_values("avg_transit_hours", ascending=False)

            highest_wh = res.iloc[0]["destination_warehouse"]
            highest_hours = res.iloc[0]["avg_transit_hours"]

            meta = {
                "title": "Average Transit Time by Destination Warehouse",
                "highest_wh": highest_wh,
                "highest_hours": highest_hours,
                "overall_avg": df["transit_hours"].mean(),
            }
            return res, "bar_transport_wh", meta

        elif intent == "TRANSPORT_BY_MANDI":
            df = self.dfs["transport_joined"].dropna(subset=["transit_hours", "mandi_name"]).copy()
            res = df.groupby("mandi_name")["transit_hours"].mean().reset_index()
            res = res.sort_values("transit_hours", ascending=True).tail(top_n)

            longest_mandi = res.iloc[-1]["mandi_name"]
            longest_hours = res.iloc[-1]["transit_hours"]

            meta = {
                "title": f"Top {top_n} Mandis by Average Transit Time (Hours)",
                "longest_mandi": longest_mandi,
                "longest_hours": longest_hours,
            }
            return res, "horizontal_bar_mandi_transit", meta

        elif intent == "TRANSPORT_DISTANCE_VS_TIME":
            df = self.dfs["fact_transport"].dropna(subset=["distance_km", "transit_hours"]).copy()
            sample_df = df.sample(3000, random_state=42) if len(df) > 3000 else df
            corr = df["distance_km"].corr(df["transit_hours"])

            meta = {
                "title": "Distance (km) vs Transit Time (Hours)",
                "correlation": corr,
                "trip_count": len(df),
            }
            return sample_df, "scatter_distance_time", meta

        elif intent == "TRANSPORT_DELAY_RATE":
            df = self.dfs["fact_transport"].dropna(subset=["transit_hours"]).copy()
            total_trips = len(df)
            delayed_trips = (df["transit_hours"] > DELAY_THRESHOLD_HOURS).sum()
            delay_rate = (delayed_trips / total_trips * 100) if total_trips > 0 else 0

            res = df.groupby("destination_warehouse").agg(
                total_trips=("trip_id", "count"),
                delayed_trips=("transit_hours", lambda s: (s > DELAY_THRESHOLD_HOURS).sum())
            ).reset_index()
            res["delay_rate_pct"] = (res["delayed_trips"] / res["total_trips"] * 100).round(2)
            res = res.sort_values("delay_rate_pct", ascending=False)

            worst_wh = res.iloc[0]["destination_warehouse"]
            worst_rate = res.iloc[0]["delay_rate_pct"]

            meta = {
                "title": f"Transport Delay Rate (> {DELAY_THRESHOLD_HOURS} Hours Threshold)",
                "total_trips": total_trips,
                "delayed_trips": delayed_trips,
                "delay_rate": delay_rate,
                "worst_wh": worst_wh,
                "worst_rate": worst_rate,
            }
            return res, "bar_delay_rate", meta

        # ----------------------------------------------------------------------
        # WEATHER
        # ----------------------------------------------------------------------
        elif intent == "WEATHER_TREND_RAIN":
            res = self.dfs["dim_weather_daily"].sort_values("date").copy()
            peak_day = res.loc[res["total_rainfall_mm"].idxmax()]
            total_rain = res["total_rainfall_mm"].sum()
            avg_rain = res["total_rainfall_mm"].mean()
            meta = {
                "title": "Daily National Rainfall Trend (Aggregated Across Sensors)",
                "peak_date": peak_day["date"].strftime("%Y-%m-%d"),
                "peak_val": peak_day["total_rainfall_mm"],
                "total_rain": total_rain,
                "avg_rain": avg_rain,
                "metric_name": "Rainfall (mm)",
            }
            return res, "line_weather_rain", meta

        elif intent == "WEATHER_TREND_TEMP":
            res = self.dfs["dim_weather_daily"].sort_values("date").copy()
            max_day = res.loc[res["avg_temperature_c"].idxmax()]
            min_day = res.loc[res["avg_temperature_c"].idxmin()]
            avg_temp = res["avg_temperature_c"].mean()
            meta = {
                "title": "Daily National Temperature Trend (°C)",
                "max_date": max_day["date"].strftime("%Y-%m-%d"),
                "max_temp": max_day["avg_temperature_c"],
                "min_date": min_day["date"].strftime("%Y-%m-%d"),
                "min_temp": min_day["avg_temperature_c"],
                "avg_temp": avg_temp,
            }
            return res, "line_weather_temp", meta

        elif intent == "WEATHER_VS_ARRIVALS":
            weather = self.dfs["dim_weather_daily"].copy()
            arrivals = self.dfs["fact_arrivals"].copy()
            if crop:
                arrivals = arrivals[arrivals["crop_name"] == crop]

            daily_arrivals = arrivals.groupby("date")["arrival_quantity_qtl"].sum().reset_index()
            merged = pd.merge(weather, daily_arrivals, on="date", how="inner").sort_values("date")

            metric_col = parsed.get("metric", "total_rainfall_mm")
            if metric_col not in merged.columns:
                metric_col = "total_rainfall_mm"

            metric_label = "Total Rainfall (mm)" if metric_col == "total_rainfall_mm" else "Avg Temperature (°C)"
            corr = merged[metric_col].corr(merged["arrival_quantity_qtl"])

            meta = {
                "title": f"National {metric_label} vs Daily Arrivals" + (f" ({crop})" if crop else ""),
                "correlation": corr,
                "crop": crop,
                "metric_col": metric_col,
                "metric_label": metric_label,
            }
            return merged, "dual_weather_arrivals", meta

        # Fallback
        else:
            return None, "unsupported", {
                "message": "I couldn't match this query to our analytical catalog. Please try one of the example questions below."
            }


# ==============================================================================
# VISUALIZER (AGRITECH THEMED PLOTLY CHARTS)
# ==============================================================================
class Visualizer:
    """Creates sleek, deep-navy & cyan Plotly figures."""

    @staticmethod
    def apply_theme(fig: go.Figure, title: str):
        fig.update_layout(
            title=dict(
                text=f"<b>{title}</b>",
                font=dict(size=18, color=COLOR_PALETTE["text_light"], family="'Inter', sans-serif"),
                x=0.02,
                y=0.96,
            ),
            template="plotly_dark",
            paper_bgcolor="#091a33",     # Deep Glass Navy
            plot_bgcolor="#051022",      # Deep Midnight
            font=dict(color=COLOR_PALETTE["text_muted"], family="'Inter', sans-serif"),
            hoverlabel=dict(
                bgcolor="#051022",
                bordercolor=COLOR_PALETTE["sky_blue"],
                font_size=13,
                font_family="'Inter', sans-serif",
            ),
            margin=dict(l=40, r=40, t=60, b=40),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=12, color=COLOR_PALETTE["text_light"]),
            ),
        )
        fig.update_xaxes(
            gridcolor=COLOR_PALETTE["grid_color"],
            zerolinecolor=COLOR_PALETTE["grid_color"],
            tickfont=dict(color=COLOR_PALETTE["text_muted"]),
        )
        fig.update_yaxes(
            gridcolor=COLOR_PALETTE["grid_color"],
            zerolinecolor=COLOR_PALETTE["grid_color"],
            tickfont=dict(color=COLOR_PALETTE["text_muted"]),
        )
        return fig

    def render(self, df: pd.DataFrame, chart_type: str, meta: Dict[str, Any]) -> go.Figure:
        title = meta.get("title", "Data Analysis")

        # 1. Line Chart
        if chart_type in ["line", "line_price"]:
            y_col = "arrival_quantity_qtl" if "arrival_quantity_qtl" in df.columns else "modal_price"
            y_label = "Arrival Quantity (Qtl)" if y_col == "arrival_quantity_qtl" else "Modal Price (₹/Qtl)"
            color = COLOR_PALETTE["cyan_glow"] if y_col == "arrival_quantity_qtl" else COLOR_PALETTE["gold_wheat"]

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["date"],
                y=df[y_col],
                mode="lines+markers",
                name=y_label,
                line=dict(color=color, width=2.8),
                marker=dict(size=4.5, color=color),
                hovertemplate="<b>Date:</b> %{x|%Y-%m-%d}<br><b>" + y_label + ":</b> %{y:,.2f}<extra></extra>",
            ))
            fig.update_yaxes(title_text=y_label)
            fig.update_xaxes(title_text="Date")
            return self.apply_theme(fig, title)

        # 2. Horizontal Bar Chart
        elif chart_type in ["horizontal_bar", "horizontal_bar_crashes", "horizontal_bar_mandi_transit"]:
            x_col = "arrival_quantity_qtl"
            y_col = "mandi_name"
            x_label = "Arrival Quantity (Qtl)"
            bar_color = COLOR_PALETTE["sky_blue"]

            if chart_type == "horizontal_bar_crashes":
                x_col = "crash_count"
                x_label = "Price Crash Instances"
                bar_color = COLOR_PALETTE["danger_coral"]
            elif chart_type == "horizontal_bar_mandi_transit":
                x_col = "transit_hours"
                x_label = "Avg Transit Hours"
                bar_color = COLOR_PALETTE["electric_blue"]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df[x_col],
                y=df[y_col],
                orientation="h",
                marker=dict(
                    color=bar_color,
                    line=dict(color=COLOR_PALETTE["cyan_glow"], width=1)
                ),
                text=df[x_col].apply(lambda v: f"{v:,.1f}" if isinstance(v, float) else f"{v:,}"),
                textposition="auto",
                hovertemplate="<b>%{y}</b><br>" + x_label + ": %{x:,.2f}<extra></extra>",
            ))
            fig.update_xaxes(title_text=x_label)
            fig.update_yaxes(title_text="Mandi")
            return self.apply_theme(fig, title)

        # 3. Bar Chart
        elif chart_type == "bar":
            cat_col = "crop_name" if "crop_name" in df.columns else "state"
            fig = px.bar(
                df,
                x=cat_col,
                y="arrival_quantity_qtl",
                text="arrival_quantity_qtl",
                color=cat_col,
                color_discrete_sequence=[
                    COLOR_PALETTE["cyan_glow"], COLOR_PALETTE["sky_blue"], COLOR_PALETTE["gold_wheat"],
                    COLOR_PALETTE["emerald"], COLOR_PALETTE["purple"], "#38bdf8", "#0284c7"
                ],
            )
            fig.update_traces(
                texttemplate="%{text:,.0f} Qtl",
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>Arrivals: %{y:,.2f} Qtl<extra></extra>",
            )
            fig.update_yaxes(title_text="Arrivals (Quintals)")
            fig.update_xaxes(title_text="Crop" if cat_col == "crop_name" else "State")
            return self.apply_theme(fig, title)

        # 4. Multivariate Line Chart
        elif chart_type == "line_multivariate":
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["date"],
                y=df["modal_price"],
                mode="lines",
                name="Modal Price (₹)",
                line=dict(color=COLOR_PALETTE["cyan_glow"], width=2.8),
                hovertemplate="<b>Date:</b> %{x|%Y-%m-%d}<br>Modal Price: ₹%{y:,.2f}<extra></extra>",
            ))
            fig.add_trace(go.Scatter(
                x=df["date"],
                y=df["msp"],
                mode="lines",
                name="MSP (₹)",
                line=dict(color=COLOR_PALETTE["gold_wheat"], width=2.5, dash="dash"),
                hovertemplate="<b>Date:</b> %{x|%Y-%m-%d}<br>MSP: ₹%{y:,.2f}<extra></extra>",
            ))
            fig.update_yaxes(title_text="Price (₹ / Qtl)")
            fig.update_xaxes(title_text="Date")
            return self.apply_theme(fig, title)

        # 5. Grouped Bar Chart
        elif chart_type == "grouped_bar":
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df["crop_name"],
                y=df["modal_price"],
                name="Avg Modal Price (₹)",
                marker_color=COLOR_PALETTE["cyan_glow"],
                text=df["modal_price"].round(1),
                textposition="auto",
            ))
            fig.add_trace(go.Bar(
                x=df["crop_name"],
                y=df["msp"],
                name="Avg MSP (₹)",
                marker_color=COLOR_PALETTE["gold_wheat"],
                text=df["msp"].round(1),
                textposition="auto",
            ))
            fig.update_layout(barmode="group")
            fig.update_yaxes(title_text="Price (₹ / Qtl)")
            fig.update_xaxes(title_text="Crop")
            return self.apply_theme(fig, title)

        # 6. Price Crash Bar Chart
        elif chart_type == "bar_crash":
            fig = px.bar(
                df,
                x="crop_name",
                y="crash_count",
                text="crash_rate_pct",
                color="crash_rate_pct",
                color_continuous_scale=["#0284c7", "#f59e0b", "#ef4444"],
            )
            fig.update_traces(
                texttemplate="%{y} crashes<br>(%{text:.1f}%)",
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>Crashes: %{y}<br>Rate: %{text:.2f}%<extra></extra>",
            )
            fig.update_yaxes(title_text="Crash Instances (modal_price < MSP)")
            fig.update_xaxes(title_text="Crop")
            return self.apply_theme(fig, title)

        # 7. Price Summary Bar
        elif chart_type == "bar_price_summary":
            fig = px.bar(
                df,
                x="crop_name",
                y="modal_price",
                text="modal_price",
                color="crop_name",
                color_discrete_sequence=[
                    COLOR_PALETTE["cyan_glow"], COLOR_PALETTE["gold_wheat"], COLOR_PALETTE["emerald"],
                    COLOR_PALETTE["sky_blue"], COLOR_PALETTE["purple"], "#0284c7", "#f97316"
                ],
            )
            fig.update_traces(
                texttemplate="₹%{text:,.1f}",
                textposition="outside",
                hovertemplate="<b>%{x}</b>: ₹%{y:,.2f}<extra></extra>",
            )
            fig.update_yaxes(title_text="Average Modal Price (₹/Qtl)")
            fig.update_xaxes(title_text="Crop")
            return self.apply_theme(fig, title)

        # 8. Transport Warehouse Transit Time Bar
        elif chart_type == "bar_transport_wh":
            fig = px.bar(
                df,
                x="destination_warehouse",
                y="avg_transit_hours",
                text="avg_transit_hours",
                color="avg_transit_hours",
                color_continuous_scale=["#0c2d5e", "#0284c7", "#38bdf8", "#00d2ff"],
            )
            fig.update_traces(
                texttemplate="%{y:.2f} hrs",
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>Avg Transit: %{y:.2f} hrs<extra></extra>",
            )
            fig.update_yaxes(title_text="Average Transit Time (Hours)")
            fig.update_xaxes(title_text="Destination Warehouse")
            return self.apply_theme(fig, title)

        # 9. Scatter Plot
        elif chart_type == "scatter_distance_time":
            fig = px.scatter(
                df,
                x="distance_km",
                y="transit_hours",
                color="destination_warehouse",
                color_discrete_sequence=[
                    COLOR_PALETTE["cyan_glow"], COLOR_PALETTE["sky_blue"], COLOR_PALETTE["gold_wheat"],
                    COLOR_PALETTE["emerald"], COLOR_PALETTE["purple"], "#f97316"
                ],
                opacity=0.65,
                hover_data=["vehicle_no"],
            )
            fig.add_hline(
                y=DELAY_THRESHOLD_HOURS,
                line_dash="dot",
                line_color=COLOR_PALETTE["danger_coral"],
                annotation_text=f"Delay Threshold ({DELAY_THRESHOLD_HOURS} hrs)",
                annotation_position="bottom right",
            )
            fig.update_xaxes(title_text="Distance (km)")
            fig.update_yaxes(title_text="Transit Time (Hours)")
            return self.apply_theme(fig, title)

        # 10. Transport Delay Rate Bar
        elif chart_type == "bar_delay_rate":
            fig = px.bar(
                df,
                x="destination_warehouse",
                y="delay_rate_pct",
                text="delay_rate_pct",
                color="delay_rate_pct",
                color_continuous_scale=["#0284c7", "#f59e0b", "#ef4444"],
            )
            fig.update_traces(
                texttemplate="%{y:.1f}%",
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>Delay Rate: %{y:.2f}%<extra></extra>",
            )
            fig.update_yaxes(title_text=f"Trips > {DELAY_THRESHOLD_HOURS} Hours (%)")
            fig.update_xaxes(title_text="Destination Warehouse")
            return self.apply_theme(fig, title)

        # 11. Weather Trends
        elif chart_type in ["line_weather_rain", "line_weather_temp"]:
            col = "total_rainfall_mm" if chart_type == "line_weather_rain" else "avg_temperature_c"
            label = "Rainfall (mm)" if chart_type == "line_weather_rain" else "Temperature (°C)"
            color = COLOR_PALETTE["cyan_glow"] if chart_type == "line_weather_rain" else COLOR_PALETTE["gold_wheat"]

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["date"],
                y=df[col],
                mode="lines",
                name=label,
                line=dict(color=color, width=2.5),
                hovertemplate="<b>Date:</b> %{x|%Y-%m-%d}<br>" + label + ": %{y:.2f}<extra></extra>",
            ))
            fig.update_yaxes(title_text=label)
            fig.update_xaxes(title_text="Date")
            return self.apply_theme(fig, title)

        # 12. Dual-Axis Weather vs Arrivals
        elif chart_type == "dual_weather_arrivals":
            metric_col = meta.get("metric_col", "total_rainfall_mm")
            metric_label = meta.get("metric_label", "Rainfall (mm)")
            metric_color = COLOR_PALETTE["cyan_glow"] if "rain" in metric_col else COLOR_PALETTE["gold_wheat"]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df["date"],
                y=df["arrival_quantity_qtl"],
                name="Daily Arrivals (Qtl)",
                marker_color="rgba(14, 165, 233, 0.45)",
                yaxis="y",
                hovertemplate="<b>Date:</b> %{x|%Y-%m-%d}<br>Arrivals: %{y:,.2f} Qtl<extra></extra>",
            ))
            fig.add_trace(go.Scatter(
                x=df["date"],
                y=df[metric_col],
                name=metric_label,
                line=dict(color=metric_color, width=2.8),
                yaxis="y2",
                hovertemplate="<b>Date:</b> %{x|%Y-%m-%d}<br>" + metric_label + ": %{y:.2f}<extra></extra>",
            ))

            fig.update_layout(
                yaxis=dict(title="Arrivals (Quintals)", side="left"),
                yaxis2=dict(
                    title=metric_label,
                    side="right",
                    overlaying="y",
                    showgrid=False,
                ),
            )
            return self.apply_theme(fig, title)

        fig = px.line(df, x=df.columns[0], y=df.columns[1])
        return self.apply_theme(fig, title)


# ==============================================================================
# INSIGHT GENERATOR
# ==============================================================================
class InsightGenerator:
    """Generates strictly factual insights derived from computed numbers."""

    @staticmethod
    def generate(parsed: Dict[str, Any], df: Optional[pd.DataFrame], meta: Dict[str, Any]) -> str:
        if df is None or df.empty:
            return "Insufficient data to answer this question."

        intent = parsed.get("intent")

        if intent == "ARRIVALS_TREND":
            crop_str = f" for {meta['crop']}" if meta.get("crop") else ""
            return (
                f"Peak arrival volume{crop_str} was recorded on **{meta['peak_date']}** "
                f"at **{meta['peak_val']:,.2f} Quintals**. Over the observed period of {meta['count_days']} days, "
                f"total cumulative arrivals reached **{meta['total_qty']:,.2f} Quintals** "
                f"(averaging {meta['avg_daily']:,.2f} Qtl/day)."
            )

        elif intent in ["ARRIVALS_BY_MANDI", "ARRIVALS_SPECIFIC_LOCATION"]:
            if "mandi" in meta and "top_mandi" not in meta:
                crop_str = f" of {meta['crop']}" if meta.get("crop") else ""
                return (
                    f"**{meta['mandi']}** logged a cumulative total of **{meta['total_qty']:,.2f} Quintals**{crop_str}, "
                    f"peaking at {meta['peak_val']:,.2f} Quintals in a single day."
                )
            crop_str = f" {meta['crop']}" if meta.get("crop") else ""
            dist_str = f" in {meta['district']} District" if meta.get("district") else ""
            return (
                f"**{meta['top_mandi']}** recorded the highest{crop_str} arrival volume{dist_str} "
                f"with **{meta['top_val']:,.2f} Quintals**, accounting for **{meta['share_pct']:.2f}%** "
                f"of the total reported volume in this selection."
            )

        elif intent == "ARRIVALS_CROP_TOTAL":
            crop_name = meta.get("crop", "All Crops")
            return (
                f"Total cumulative arrivals for **{crop_name}** reached **{meta['total_qty']:,.2f} Quintals** "
                f"across the recorded agricultural timeframe."
            )

        elif intent == "ARRIVALS_BY_CROP":
            state_str = f" in {parsed['state']}" if parsed.get("state") else ""
            return (
                f"**{meta['top_crop']}** leads market arrivals{state_str} with **{meta['top_val']:,.2f} Quintals**, "
                f"constituting **{meta['top_pct']:.2f}%** of total supply across all 7 canonical crops "
                f"(Total: {meta['total_all']:,.2f} Qtl)."
            )

        elif intent == "ARRIVALS_BY_STATE":
            crop_str = f" for {meta['crop']}" if meta.get("crop") else ""
            return (
                f"**{meta['top_state']}** logged the highest aggregate arrivals{crop_str} "
                f"at **{meta['top_val']:,.2f} Quintals** ({meta['top_pct']:.2f}% market share)."
            )

        elif intent == "PRICE_MSP_COMPARE":
            if "diff" in meta:
                status = "above" if meta["diff"] >= 0 else "below"
                return (
                    f"Average modal price for **{meta['crop']}** stands at **₹{meta['avg_modal']:,.2f}/Qtl**, "
                    f"which is **₹{abs(meta['diff']):,.2f} ({abs(meta['pct_diff']):.2f}%) {status}** "
                    f"the benchmark MSP of ₹{meta['avg_msp']:,.2f}/Qtl."
                )
            else:
                return (
                    "Modal prices generally track above MSP across major staples, "
                    "with individual mandi quotes exhibiting localized volatility."
                )

        elif intent == "PRICE_CRASH_BY_CROP":
            return (
                f"**{meta['top_crop']}** recorded the highest number of price crashes with "
                f"**{meta['top_count']:,} instances** trading below MSP (**{meta['top_rate']:.2f}%** crash rate). "
                f"A price crash occurs strictly when modal price drops below the official MSP."
            )

        elif intent == "PRICE_BELOW_MSP_MANDIS":
            return (
                f"**{meta['top_mandi']}** experienced the highest frequency of quotes below MSP "
                f"with **{meta['top_crashes']} crash occurrences** out of {meta['total_below_msp']:,} total crash events."
            )

        elif intent == "PRICE_TREND":
            crop_str = f" for {meta['crop']}" if meta.get("crop") else ""
            return (
                f"Average modal price{crop_str} peaked on **{meta['peak_date']}** at **₹{meta['peak_price']:,.2f}/Qtl** "
                f"(overall range: ₹{meta['min_price']:,.2f} to ₹{meta['peak_price']:,.2f}/Qtl, mean: ₹{meta['avg_price']:,.2f}/Qtl)."
            )

        elif intent == "PRICE_AVERAGE_SUMMARY":
            return (
                f"**{meta['highest_crop']}** commands the highest average modal price at **₹{meta['highest_val']:,.2f}/Qtl** "
                f"(overall marketplace average across all crops is ₹{meta['overall_avg']:,.2f}/Qtl)."
            )

        elif intent == "TRANSPORT_BY_WAREHOUSE":
            return (
                f"**{meta['highest_wh']}** recorded the longest average transit time at **{meta['highest_hours']:.2f} hours** "
                f"(benchmark fleet average: {meta['overall_avg']:.2f} hours)."
            )

        elif intent == "TRANSPORT_BY_MANDI":
            return (
                f"Dispatches originating from **{meta['longest_mandi']}** experienced the highest transit duration, "
                f"averaging **{meta['longest_hours']:.2f} hours**."
            )

        elif intent == "TRANSPORT_DISTANCE_VS_TIME":
            corr = meta["correlation"]
            strength = "strong" if abs(corr) > 0.7 else "moderate" if abs(corr) > 0.4 else "weak"
            return (
                f"Trip distance and transit duration exhibit a **{strength} positive correlation (r = {corr:.4f})** "
                f"across {meta['trip_count']:,} validated shipments."
            )

        elif intent == "TRANSPORT_DELAY_RATE":
            return (
                f"Overall transport delay rate (> {DELAY_THRESHOLD_HOURS} hours threshold) stands at "
                f"**{meta['delay_rate']:.2f}%** ({meta['delayed_trips']:,} of {meta['total_trips']:,} completed trips). "
                f"**{meta['worst_wh']}** logged the highest delay incidence at **{meta['worst_rate']:.2f}%**."
            )

        elif intent == "WEATHER_TREND_RAIN":
            return (
                f"National daily rainfall reached a peak of **{meta['peak_val']:.2f} mm** on **{meta['peak_date']}** "
                f"(total seasonal accumulation: {meta['total_rain']:.2f} mm, daily average: {meta['avg_rain']:.2f} mm). "
                f"*(Note: Rainfall reflects national multi-sensor aggregates; no mandi-specific sensor linkage exists)*."
            )

        elif intent == "WEATHER_TREND_TEMP":
            return (
                f"National daily average temperatures ranged between **{meta['min_temp']:.1f}°C** ({meta['min_date']}) "
                f"and **{meta['max_temp']:.1f}°C** ({meta['max_date']}), with an overall mean of **{meta['avg_temp']:.1f}°C**."
            )

        elif intent == "WEATHER_VS_ARRIVALS":
            corr = meta["correlation"]
            interp = (
                "strong correlation" if abs(corr) > 0.6 else
                "moderate correlation" if abs(corr) > 0.3 else
                "negligible/weak correlation"
            )
            crop_str = f" for {meta['crop']}" if meta.get("crop") else ""
            return (
                f"The Pearson correlation between national {meta['metric_label'].lower()} and daily arrivals{crop_str} "
                f"is **r = {corr:.4f}**, indicating **{interp}** over this timeframe. "
                f"*(Note: Weather is joined strictly on calendar date as a national aggregate)*."
            )

        return "Analysis completed successfully based on verified project records."


# ==============================================================================
# STREAMLIT UI — AGRITECH EXECUTIVE THEME (GLASSMORPHISM)
# ==============================================================================
def setup_page():
    st.set_page_config(
        page_title="AgriTech | Mandi-to-Market Supply Chain Optimizer",
        page_icon="🌾",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    /* ─── Global Atmosphere ─── */
    html, .stApp {
        background: linear-gradient(160deg, #040f22 0%, #071829 40%, #030d1a 100%);
        color: #f0f4f8;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* ─── Sidebar Reskin ─── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #071628 0%, #040f1e 100%) !important;
        border-right: 1px solid rgba(56,189,248,0.15) !important;
        backdrop-filter: blur(20px);
    }
    [data-testid="stSidebar"] * { color: #c8d6e5 !important; }
    [data-testid="stSidebar"] h3 { color: #00d2ff !important; }
    .sidebar-brand {
        display: flex; align-items: center; gap: 10px;
        padding: 6px 0 14px 0;
        border-bottom: 1px solid rgba(56,189,248,0.18);
        margin-bottom: 18px;
    }
    .sidebar-brand-icon {
        width: 38px; height: 38px; border-radius: 10px;
        background: linear-gradient(135deg, rgba(56,189,248,0.25), rgba(2,132,199,0.3));
        border: 1px solid rgba(56,189,248,0.4);
        display: flex; align-items: center; justify-content: center;
        font-size: 1.3rem;
    }
    .sidebar-brand-text-main { font-size: 1.05rem; font-weight: 800; color: #00d2ff !important; line-height:1; }
    .sidebar-brand-text-sub  { font-size: 0.72rem; color: #64748b !important; }
    .sidebar-divider {
        border: none; border-top: 1px solid rgba(56,189,248,0.12);
        margin: 14px 0;
    }
    .sidebar-section-label {
        font-size: 0.68rem; font-weight: 700; color: #38bdf8 !important;
        letter-spacing: 0.12em; text-transform: uppercase;
        margin: 14px 0 8px 0;
    }
    .sidebar-stat-row {
        display: flex; align-items: center; justify-content: space-between;
        padding: 7px 10px;
        background: rgba(14,165,233,0.07);
        border: 1px solid rgba(56,189,248,0.12);
        border-radius: 8px;
        margin-bottom: 6px;
    }
    .sidebar-stat-label { font-size: 0.78rem; color: #94a3b8 !important; font-weight: 500; }
    .sidebar-stat-val   { font-size: 0.88rem; color: #ffffff !important; font-weight: 700; }
    .sidebar-rule-item {
        display: flex; align-items: flex-start; gap: 8px;
        padding: 5px 0; font-size: 0.77rem; color: #94a3b8 !important; line-height: 1.4;
    }
    .sidebar-rule-dot {
        width: 5px; height: 5px; border-radius: 50%;
        background: #38bdf8; flex-shrink: 0; margin-top: 6px;
    }

    /* ─── Hero Header ─── */
    .hero-wrapper {
        background: linear-gradient(135deg, rgba(8,30,60,0.9) 0%, rgba(5,18,38,0.95) 100%);
        border: 1px solid rgba(56,189,248,0.22);
        border-radius: 22px;
        padding: 34px 40px 28px 40px;
        margin-bottom: 24px;
        backdrop-filter: blur(16px);
        box-shadow: 0 20px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(56,189,248,0.08) inset;
        text-align: center;
        position: relative;
        overflow: hidden;
    }
    .hero-wrapper::before {
        content: '';
        position: absolute; top: 0; left: 0; right: 0; height: 1px;
        background: linear-gradient(90deg, transparent, rgba(56,189,248,0.6), transparent);
    }
    .hero-eyebrow {
        font-size: 0.75rem; font-weight: 700; letter-spacing: 0.28em;
        text-transform: uppercase; color: #38bdf8;
        margin-bottom: 14px;
    }
    .hero-logo-icon {
        font-size: 3.6rem; line-height: 1;
        filter: drop-shadow(0 0 16px rgba(56,189,248,0.6));
        margin-bottom: 8px;
    }
    .hero-brand-name {
        font-size: 2.6rem; font-weight: 900; letter-spacing: -0.03em;
        background: linear-gradient(135deg, #ffffff 0%, #38bdf8 50%, #00d2ff 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        line-height: 1.05;
    }
    .hero-leaf { font-size: 2rem; -webkit-text-fill-color: initial !important; }
    .hero-title {
        font-size: 1.25rem; font-weight: 700; color: #e2e8f0;
        margin: 6px 0 10px 0; letter-spacing: -0.01em;
    }
    .hero-tagline {
        font-size: 0.8rem; font-weight: 600; letter-spacing: 0.2em;
        text-transform: uppercase;
        color: #64748b;
    }
    .hero-tagline span { color: #38bdf8; }
    .hero-cursive {
        position: absolute; top: 22px; right: 26px;
        font-size: 0.88rem; color: #38bdf8; font-style: italic;
        line-height: 1.5; text-align: right; opacity: 0.8;
    }
    .hero-datathon-badge {
        display: inline-block;
        margin-top: 16px;
        background: rgba(14,165,233,0.1);
        border: 1px solid rgba(56,189,248,0.3);
        border-radius: 9999px;
        padding: 5px 18px;
        font-size: 0.78rem; font-weight: 600; color: #7dd3fc;
        letter-spacing: 0.05em;
    }

    /* ─── Glass Cards ─── */
    .agri-card {
        background: linear-gradient(145deg, rgba(10,28,55,0.85) 0%, rgba(5,16,34,0.9) 100%);
        border: 1px solid rgba(56,189,248,0.25);
        box-shadow: 0 8px 32px rgba(0,0,0,0.4), 0 0 0 1px rgba(56,189,248,0.07) inset;
        border-radius: 18px; padding: 22px 22px 18px 22px;
        backdrop-filter: blur(14px);
        height: 100%;
    }
    .card-heading {
        display: flex; align-items: center; gap: 10px;
        font-size: 1.1rem; font-weight: 700; color: #ffffff;
        margin-bottom: 16px; padding-bottom: 12px;
        border-bottom: 1px solid rgba(56,189,248,0.15);
    }

    /* ─── Objectives ─── */
    .obj-item {
        display: flex; align-items: center; gap: 12px;
        padding: 9px 0; color: #cbd5e1;
        font-size: 0.92rem; font-weight: 500;
        border-bottom: 1px solid rgba(56,189,248,0.07);
    }
    .obj-item:last-child { border-bottom: none; }
    .obj-icon {
        width: 30px; height: 30px; border-radius: 8px; flex-shrink: 0;
        background: rgba(14,165,233,0.13);
        border: 1px solid rgba(56,189,248,0.22);
        display: flex; align-items: center; justify-content: center;
        font-size: 0.88rem;
    }

    /* ─── 2×2 Metric Tiles ─── */
    .metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .metric-tile {
        background: linear-gradient(135deg, rgba(14,165,233,0.1) 0%, rgba(5,20,45,0.75) 100%);
        border: 1px solid rgba(56,189,248,0.28); border-radius: 14px;
        padding: 14px 12px;
        display: flex; align-items: center; gap: 12px;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .metric-tile:hover {
        transform: translateY(-2px);
        box-shadow: 0 0 20px rgba(0,210,255,0.2);
        border-color: #00d2ff;
    }
    .tile-icon {
        width: 40px; height: 40px; border-radius: 10px; flex-shrink: 0;
        background: linear-gradient(135deg,rgba(56,189,248,0.22),rgba(2,132,199,0.28));
        border: 1px solid rgba(56,189,248,0.35);
        display: flex; align-items: center; justify-content: center;
        font-size: 1.2rem;
    }
    .tile-label { font-size: 0.72rem; color: #94a3b8; font-weight: 500; margin-bottom: 2px; }
    .tile-val   { font-size: 1.4rem; font-weight: 800; color: #ffffff; line-height: 1.1; }
    .tile-sub   { font-size: 0.67rem; color: #4a5568; margin-top: 2px; }

    /* ─── Section Divider ─── */
    .section-divider {
        border: none; border-top: 1px solid rgba(56,189,248,0.1);
        margin: 24px 0;
    }

    /* ─── Analytics Pane Header ─── */
    .analytics-pane-header {
        background: linear-gradient(135deg, rgba(10,28,55,0.8) 0%, rgba(5,16,34,0.85) 100%);
        border: 1px solid rgba(56,189,248,0.2);
        border-radius: 14px; padding: 16px 22px;
        margin-bottom: 16px;
        display: flex; align-items: center; justify-content: space-between;
        backdrop-filter: blur(12px);
    }
    .analytics-pane-title {
        font-size: 1.05rem; font-weight: 700; color: #ffffff;
        display: flex; align-items: center; gap: 8px;
    }
    .analytics-pane-sub { font-size: 0.78rem; color: #38bdf8; font-weight: 600; }

    /* ─── NLU Badges ─── */
    .nlu-badge {
        display: inline-block; padding: 4px 12px;
        border-radius: 9999px; font-size: 0.75rem; font-weight: 600;
        margin-right: 6px; margin-bottom: 6px;
        background: rgba(14,165,233,0.12);
        border: 1px solid rgba(56,189,248,0.3); color: #38bdf8;
    }

    /* ─── Insight Card ─── */
    .insight-card {
        background: linear-gradient(135deg, rgba(14,165,233,0.12) 0%, rgba(5,16,34,0.95) 100%);
        border: 1.5px solid rgba(0,210,255,0.5);
        border-radius: 14px; padding: 18px 22px; margin-top: 18px;
        box-shadow: 0 0 28px rgba(0,210,255,0.15);
    }
    .insight-title {
        font-size: 0.78rem; font-weight: 800; text-transform: uppercase;
        letter-spacing: 0.1em; color: #00d2ff;
        display: flex; align-items: center; gap: 6px; margin-bottom: 8px;
    }
    .insight-text { font-size: 1rem; color: #e2e8f0; line-height: 1.7; }

    /* ─── Footer ─── */
    .agri-footer {
        margin-top: 36px; padding: 14px 22px;
        border-top: 1px solid rgba(56,189,248,0.1);
        display: flex; align-items: center; justify-content: space-between;
        color: #4a5568; font-size: 0.78rem;
    }

    /* ─── Streamlit Component Overrides ─── */
    div.stButton > button {
        background: rgba(10,28,55,0.75) !important;
        border: 1px solid rgba(56,189,248,0.25) !important;
        color: #c8d6e5 !important; border-radius: 9px !important;
        font-size: 0.82rem !important; font-weight: 500 !important;
        padding: 8px 12px !important;
        transition: all 0.2s ease !important;
    }
    div.stButton > button:hover {
        border-color: #00d2ff !important;
        color: #38bdf8 !important;
        box-shadow: 0 0 12px rgba(0,210,255,0.25) !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px; background: transparent !important;
        border-bottom: 1px solid rgba(56,189,248,0.12) !important;
        padding-bottom: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        background: rgba(10,28,55,0.55) !important;
        border: 1px solid rgba(56,189,248,0.2) !important;
        border-radius: 9999px !important; color: #64748b !important;
        padding: 5px 16px !important; font-weight: 600 !important;
        font-size: 0.83rem !important;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg,rgba(14,165,233,0.28),rgba(2,132,199,0.35)) !important;
        border-color: rgba(0,210,255,0.7) !important;
        color: #ffffff !important;
        box-shadow: 0 0 10px rgba(0,210,255,0.25) !important;
    }
    div[data-testid="stForm"] {
        background: rgba(8,22,46,0.7) !important;
        border: 1px solid rgba(56,189,248,0.22) !important;
        border-radius: 14px !important; padding: 14px !important;
        backdrop-filter: blur(12px);
    }
    div[data-testid="stTextInput"] input {
        background: #040f1e !important;
        border: 1px solid rgba(56,189,248,0.35) !important;
        color: #f0f4f8 !important; border-radius: 9px !important;
        font-size: 0.98rem !important;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #00d2ff !important;
        box-shadow: 0 0 14px rgba(0,210,255,0.3) !important;
    }
    div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] button {
        background: linear-gradient(135deg, #0ea5e9, #00d2ff) !important;
        color: #040f1e !important; font-weight: 800 !important;
        border: none !important;
        box-shadow: 0 0 20px rgba(0,210,255,0.4) !important;
        border-radius: 9px !important;
    }
    div[data-testid="stMetric"] {
        background: rgba(14,165,233,0.06) !important;
        border: 1px solid rgba(56,189,248,0.12) !important;
        border-radius: 8px !important; padding: 8px 10px !important;
    }
    .stExpander {
        background: rgba(8,22,46,0.65) !important;
        border: 1px solid rgba(56,189,248,0.18) !important;
        border-radius: 12px !important;
    }
    </style>
    """, unsafe_allow_html=True)


def main():
    setup_page()

    # ── Load datasets ──────────────────────────────────────────────────────────
    try:
        with st.spinner("Initialising AgriTech Data Pipeline…"):
            dfs = load_datasets(DATA_DIR)
    except Exception as e:
        st.error(f"Error loading datasets from `{DATA_DIR}`: {e}")
        st.info("Please verify the cleaned CSV files are located in the specified `DATA_DIR` directory.")
        return

    nlu         = NLUParser(dfs["dim_mandi"])
    analytics   = AnalyticsEngine(dfs)
    visualizer  = Visualizer()
    insight_gen = InsightGenerator()

    # ── Live KPI Calculations ──────────────────────────────────────────────────
    total_qtl    = dfs["fact_arrivals"]["arrival_quantity_qtl"].sum()
    arr_display  = f"{total_qtl / 1_000_000:.2f}M"

    crashes      = int(dfs["fact_price_msp"]["is_price_crash"].sum())
    crash_disp   = f"{crashes / 1000:.1f}K" if crashes > 999 else str(crashes)

    crash_rate   = crashes / len(dfs["fact_price_msp"]) * 100
    avg_transit  = dfs["fact_transport"]["transit_hours"].dropna().mean()

    # ══════════════════════════════════════════════════════════════════════════
    # SIDEBAR — compact, professional glassmorphism pane
    # ══════════════════════════════════════════════════════════════════════════
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-brand">
            <div class="sidebar-brand-icon">🌾</div>
            <div>
                <div class="sidebar-brand-text-main">AgriTech</div>
                <div class="sidebar-brand-text-sub">Supply Chain Optimizer</div>
            </div>
        </div>
        <div style="font-size:0.78rem;color:#64748b;margin-bottom:14px;">
            TransOrg AgentIQ Datathon · Track 3
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="sidebar-section-label">📂 Dataset Overview</div>', unsafe_allow_html=True)
        rows_data = [
            ("Arrivals",   f"{len(dfs['fact_arrivals']):,} rows"),
            ("Price & MSP",f"{len(dfs['fact_price_msp']):,} rows"),
            ("Transport",  f"{len(dfs['fact_transport']):,} rows"),
            ("Weather",    f"{len(dfs['dim_weather_daily'])} days"),
            ("Mandis",     f"{len(dfs['dim_mandi'])} mandis"),
        ]
        for label, val in rows_data:
            st.markdown(f"""
            <div class="sidebar-stat-row">
                <span class="sidebar-stat-label">{label}</span>
                <span class="sidebar-stat-val">{val}</span>
            </div>""", unsafe_allow_html=True)

        st.markdown('<hr class="sidebar-divider"><div class="sidebar-section-label">🔒 Data Rules</div>', unsafe_allow_html=True)
        rules = [
            "Rice & Paddy kept as separate crops",
            "Price crash: modal_price &lt; msp only",
            "Weather = national aggregate by date",
            "Delay threshold = 12 hours",
            "Zero paid API — fully local",
        ]
        for r in rules:
            st.markdown(f'<div class="sidebar-rule-item"><div class="sidebar-rule-dot"></div><span>{r}</span></div>', unsafe_allow_html=True)

        st.markdown(f'<hr class="sidebar-divider"><div style="font-size:0.7rem;color:#374151;">Data: <code style="color:#38bdf8;font-size:0.68rem;">{os.path.basename(DATA_DIR)}/</code></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # HERO HEADER — proper Streamlit native render, no broken SVG
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("""
    <div class="hero-wrapper">
        <div class="hero-cursive">From Fields<br>to Better Futures</div>
        <div class="hero-eyebrow">TransOrg AgentIQ Datathon &nbsp;·&nbsp; Track 3 &nbsp;·&nbsp; Bonus AI Agent</div>
        <div class="hero-logo-icon">🌾</div>
        <div class="hero-brand-name">AgriTech <span class="hero-leaf">🌱</span></div>
        <div class="hero-title">Mandi-to-Market Supply Chain Optimizer</div>
        <div class="hero-tagline">
            <span>DATA</span> &nbsp;|&nbsp; <span>INSIGHTS</span> &nbsp;|&nbsp; <span>BETTER FARMER OUTCOMES</span>
        </div>
        <div class="hero-datathon-badge">AI Analytics Agent · Powered by Pandas + Plotly · Zero External API</div>
    </div>
    """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # EXECUTIVE INFO ROW — Objectives + Key Insights
    # ══════════════════════════════════════════════════════════════════════════
    col_obj, col_kpi = st.columns([1, 1], gap="medium")

    with col_obj:
        st.markdown("""
        <div class="agri-card">
            <div class="card-heading"><span>🎯</span> Project Objectives</div>
            <div class="obj-item"><div class="obj-icon">🔍</div><span>Identify supply chain inefficiencies</span></div>
            <div class="obj-item"><div class="obj-icon">📈</div><span>Analyse price trends & market risks</span></div>
            <div class="obj-item"><div class="obj-icon">🌧️</div><span>Assess national weather impact on arrivals</span></div>
            <div class="obj-item"><div class="obj-icon">🚚</div><span>Optimise mandi-to-market logistics</span></div>
            <div class="obj-item"><div class="obj-icon">🧠</div><span>Enable data-driven decision making</span></div>
        </div>
        """, unsafe_allow_html=True)

    with col_kpi:
        st.markdown(f"""
        <div class="agri-card">
            <div class="card-heading"><span>📊</span> Key Insights at a Glance</div>
            <div class="metric-grid">
                <div class="metric-tile">
                    <div class="tile-icon">🌾</div>
                    <div>
                        <div class="tile-label">Total Arrivals</div>
                        <div class="tile-val">{arr_display}</div>
                        <div class="tile-sub">Quintals · across mandis</div>
                    </div>
                </div>
                <div class="metric-tile">
                    <div class="tile-icon">📉</div>
                    <div>
                        <div class="tile-label">Price Crash Instances</div>
                        <div class="tile-val">{crash_disp}</div>
                        <div class="tile-sub">modal_price &lt; MSP events</div>
                    </div>
                </div>
                <div class="metric-tile">
                    <div class="tile-icon">⚠️</div>
                    <div>
                        <div class="tile-label">Price Crash Rate</div>
                        <div class="tile-val">{crash_rate:.1f}%</div>
                        <div class="tile-sub">Market volatility signal</div>
                    </div>
                </div>
                <div class="metric-tile">
                    <div class="tile-icon">🚚</div>
                    <div>
                        <div class="tile-label">Avg Transit Time</div>
                        <div class="tile-val">{avg_transit:.2f} hrs</div>
                        <div class="tile-sub">Mandi → Warehouse</div>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # NATURAL LANGUAGE TEXT-TO-CHART AI ANALYTICS PANE
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown("""
    <div class="analytics-pane-header">
        <div class="analytics-pane-title"><span>⚡</span> Natural Language Analytics</div>
        <div class="analytics-pane-sub">Text → Intent → Chart → Insight</div>
    </div>
    """, unsafe_allow_html=True)

    if "user_query" not in st.session_state:
        st.session_state["user_query"] = "Show the daily arrival trend for Wheat."

    tab_arr, tab_price, tab_trans, tab_weather = st.tabs([
        "📦  Arrivals",
        "💰  Price & MSP",
        "🚚  Transport",
        "🌦️  Weather",
    ])

    with tab_arr:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Daily arrival trend for Wheat",         key="q_arr1", use_container_width=True):
                st.session_state["user_query"] = "Show the daily arrival trend for Wheat."
            if st.button("Top 10 mandis by arrival volume",       key="q_arr2", use_container_width=True):
                st.session_state["user_query"] = "What are the top 10 mandis by arrival volume?"
            if st.button("Mandis with highest Wheat arrivals",    key="q_arr3", use_container_width=True):
                st.session_state["user_query"] = "Which mandis have the highest Wheat arrivals?"
        with c2:
            if st.button("Arrivals by crop",                      key="q_arr4", use_container_width=True):
                st.session_state["user_query"] = "Show arrivals by crop."
            if st.button("Arrivals by state",                     key="q_arr5", use_container_width=True):
                st.session_state["user_query"] = "Show arrivals by state."
            if st.button("Wheat arrivals in Amritsar",            key="q_arr6", use_container_width=True):
                st.session_state["user_query"] = "Show Wheat arrivals in Amritsar."

    with tab_price:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Modal price vs MSP for Wheat",          key="q_pr1", use_container_width=True):
                st.session_state["user_query"] = "Compare modal price and MSP for Wheat."
            if st.button("Modal price vs MSP — all crops",        key="q_pr2", use_container_width=True):
                st.session_state["user_query"] = "Show modal price vs MSP."
            if st.button("Crops with most price crashes",         key="q_pr3", use_container_width=True):
                st.session_state["user_query"] = "Which crops have the most price crashes?"
        with c2:
            if st.button("Mandis trading below MSP",              key="q_pr4", use_container_width=True):
                st.session_state["user_query"] = "Which mandis are below MSP?"
            if st.button("Price trend for Wheat",                 key="q_pr5", use_container_width=True):
                st.session_state["user_query"] = "Show the price trend for Wheat."
            if st.button("Average modal price by crop",           key="q_pr6", use_container_width=True):
                st.session_state["user_query"] = "What is the average modal price?"

    with tab_trans:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Avg transit time by warehouse",         key="q_tr1", use_container_width=True):
                st.session_state["user_query"] = "Show average transit time by warehouse."
            if st.button("Warehouse with highest transit time",   key="q_tr2", use_container_width=True):
                st.session_state["user_query"] = "Which warehouse has the highest transit time?"
            if st.button("Transit time by mandi",                 key="q_tr3", use_container_width=True):
                st.session_state["user_query"] = "Show transit time by mandi."
        with c2:
            if st.button("Distance vs transit time scatter",      key="q_tr4", use_container_width=True):
                st.session_state["user_query"] = "Show distance versus transit time."
            if st.button("Delayed trips analysis",                key="q_tr5", use_container_width=True):
                st.session_state["user_query"] = "Which trips are delayed?"
            if st.button("Transport delay rate by warehouse",     key="q_tr6", use_container_width=True):
                st.session_state["user_query"] = "Show the transport delay rate."

    with tab_weather:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("National rainfall trend",               key="q_wt1", use_container_width=True):
                st.session_state["user_query"] = "Show rainfall over time."
            if st.button("National temperature trend",            key="q_wt2", use_container_width=True):
                st.session_state["user_query"] = "Show temperature over time."
            if st.button("Rainfall & arrivals over time",         key="q_wt3", use_container_width=True):
                st.session_state["user_query"] = "Show rainfall and arrivals over time."
        with c2:
            if st.button("Does rainfall affect arrivals?",        key="q_wt4", use_container_width=True):
                st.session_state["user_query"] = "Does rainfall affect arrivals?"
            if st.button("Temperature vs arrivals",               key="q_wt5", use_container_width=True):
                st.session_state["user_query"] = "Show temperature versus arrivals."
            if st.button("Rainfall vs total arrivals (compare)",  key="q_wt6", use_container_width=True):
                st.session_state["user_query"] = "Compare rainfall with total arrivals."

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Query Input Form ──────────────────────────────────────────────────────
    with st.form(key="query_form"):
        col_in, col_btn = st.columns([5, 1])
        with col_in:
            query = st.text_input(
                "query",
                value=st.session_state.get("user_query", ""),
                placeholder="Ask anything: e.g. 'Compare modal price and MSP for Wheat' or 'Show transit delay rate'…",
                label_visibility="collapsed"
            )
        with col_btn:
            st.form_submit_button("Analyze 🚀", use_container_width=True, type="primary")

    if not query.strip():
        st.info("Enter a question above or click any suggested query chip to begin.")
        return

    # ── NLU Parse ─────────────────────────────────────────────────────────────
    parsed = nlu.parse(query)

    if parsed["domain"] == "unsupported" or parsed["intent"] == "UNSUPPORTED":
        st.warning(f"⚠️ Could not interpret: *\"{query}\"*")
        st.markdown("""
        **This agent supports queries in four domains:**
        - **Arrivals** — trends, top mandis, crop/state comparisons, district filters
        - **Price & MSP** — modal price vs MSP, crash rates, price trends, below-MSP mandis
        - **Transport** — transit time, warehouse comparison, distance scatter, delay rate
        - **Weather** — national rainfall/temperature trends, correlation with arrivals
        """)
        return

    # ── NLU Transparency Badges ───────────────────────────────────────────────
    badges = (
        f'<span class="nlu-badge">DOMAIN: {parsed["domain"].upper()}</span>'
        f'<span class="nlu-badge">INTENT: {parsed["intent"]}</span>'
    )
    if parsed.get("crop"):     badges += f'<span class="nlu-badge">CROP: {parsed["crop"]}</span>'
    if parsed.get("district"): badges += f'<span class="nlu-badge">DISTRICT: {parsed["district"]}</span>'
    if parsed.get("state"):    badges += f'<span class="nlu-badge">STATE: {parsed["state"]}</span>'
    if parsed.get("mandi"):    badges += f'<span class="nlu-badge">MANDI: {parsed["mandi"]}</span>'
    if parsed.get("warehouse"):badges += f'<span class="nlu-badge">WAREHOUSE: {parsed["warehouse"]}</span>'
    if parsed.get("top_n") and "top" in query.lower():
        badges += f'<span class="nlu-badge">TOP {parsed["top_n"]}</span>'

    st.markdown(f'<div style="margin:10px 0 14px 0;">{badges}</div>', unsafe_allow_html=True)

    # ── Execute Analytics ─────────────────────────────────────────────────────
    with st.spinner("Analysing data and generating chart…"):
        res_df, chart_type, meta = analytics.execute(parsed)

    if chart_type == "empty" or res_df is None or res_df.empty:
        st.warning(f"⚠️ {meta.get('message', 'Insufficient data to answer this question.')}")
        return

    # ── Render Chart ──────────────────────────────────────────────────────────
    fig = visualizer.render(res_df, chart_type, meta)
    st.plotly_chart(fig, use_container_width=True)

    # ── Factual Insight Card ──────────────────────────────────────────────────
    insight = insight_gen.generate(parsed, res_df, meta)
    st.markdown(f"""
    <div class="insight-card">
        <div class="insight-title"><span>💡</span> Factual Analytical Insight</div>
        <div class="insight-text">{insight}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Data Expander ─────────────────────────────────────────────────────────
    with st.expander("🔍 View Underlying Calculated Data"):
        st.dataframe(res_df, use_container_width=True)

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="agri-footer">
        <div>AgriTech Dashboard v1.0 &nbsp;·&nbsp; TransOrg AgentIQ Datathon Track 3</div>
        <div>🌱 Sustainable Agriculture &nbsp;|&nbsp; Stronger Markets</div>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
