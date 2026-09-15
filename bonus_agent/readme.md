
# 🤖 Mandi-to-Market AI Analytics Agent

Bonus AI Agent for the **TransOrg AgentIQ Datathon – Track 3: AgriTech – Mandi-to-Market Supply Chain Optimizer**.

This Streamlit-based natural-language analytics agent allows users to ask questions about mandi arrivals, crop prices, MSP, transport and weather. It interprets the question, performs the required analysis on the cleaned project data, automatically selects an appropriate visualization, and provides a concise analytical insight.

---

## 🚀 Live Demo

🔗 **Streamlit App:**  
https://agri-tech-mandi-to-market-supply-chain-optimizer-egapmnofzfnzc.streamlit.app/

---

## 🎯 Objective

The objective of the Bonus AI Agent is to provide a simple natural-language interface for exploring the cleaned agricultural supply-chain data.

Instead of manually creating filters and charts, users can ask questions such as:

> "Show the daily arrival trend for Wheat."

The agent identifies the analytical intent, processes the relevant data, generates an interactive chart, and summarizes the result.

### Agent Workflow

```text
Natural Language Question
          ↓
   Intent Understanding
          ↓
    Data Selection
          ↓
 Filtering & Aggregation
          ↓
 Automatic Chart Selection
          ↓
    Interactive Chart
          ↓
   Analytical Insight
```

---

## 📊 Data Sources

The agent uses the cleaned datasets generated for the main project:

| Dataset | Purpose |
|---|---|
| `dim_mandi.csv` | Mandi master and location information |
| `fact_arrivals.csv` | Crop arrival quantities and farmer counts |
| `fact_price_msp.csv` | Wholesale prices and MSP |
| `fact_transport.csv` | Transport and logistics information |
| `dim_weather_daily.csv` | Daily national weather aggregates |

The agent works with the cleaned analytics layer and does not modify the source datasets.

---

## 💬 Example Questions

### 📦 Arrivals

- "Show the daily arrival trend for Wheat."
- "What are the top 10 mandis by arrival volume?"
- "Which mandis have the highest Wheat arrivals?"
- "Show arrivals by crop."
- "Show arrivals by state."
- "Show Wheat arrivals in Amritsar."

### 💰 Price & MSP

- "Compare modal price and MSP for Wheat."
- "Which crops have the most price crashes?"
- "Show price crashes by crop."
- "Which mandis are below MSP?"
- "Show the price trend for Wheat."

### 🚚 Transport

- "Show average transit time by warehouse."
- "Which warehouse has the highest transit time?"
- "Show transit time by mandi."
- "Show distance versus transit time."
- "Which trips are delayed?"

### 🌧️ Weather

- "Show rainfall over time."
- "Show temperature over time."
- "Show rainfall and arrivals over time."
- "Does rainfall affect arrivals?"
- "Show temperature versus arrivals."

---

## 📈 Supported Analytics

### Arrival Analysis

- Total arrival quantity
- Daily arrival trends
- Arrival volume by crop
- Arrival volume by mandi
- Top-N mandis
- Arrivals by state
- Crop-specific analysis
- Date-based analysis

### Price & MSP Analysis

- Average modal price
- Average MSP
- Modal price vs MSP
- Price crash instances
- Price crash rate
- Price crashes by crop
- Price crashes by mandi
- Price trends

### Transport Analysis

- Average transit time
- Transit time by warehouse
- Transit time by mandi
- Distance vs transit time
- Delayed trips
- Transit delay rate

### Weather Analysis

- Rainfall trends
- Temperature trends
- Humidity trends
- Rainfall vs arrivals
- Temperature vs arrivals

---

## 📊 Automatic Chart Selection

The agent automatically selects an appropriate visualization based on the user's question.

| Analytical Request | Chart |
|---|---|
| Trend over time | Line chart |
| Top-N / ranking | Horizontal bar chart |
| Category comparison | Bar chart |
| Modal Price vs MSP | Comparison chart |
| Distance vs Transit Time | Scatter plot |
| Rainfall vs Arrivals | Scatter / time-series chart |
| Temperature vs Arrivals | Scatter / time-series chart |

The user does not need to manually select a chart type.

---

## 🧠 Natural Language Understanding

The agent identifies important elements from the user's question, including:

- Analytical intent
- Crop
- Mandi
- State
- Warehouse
- Date range
- Metric
- Ranking / Top-N requirement
- Comparison requirement

### Example

Question:

```text
Show the top 5 Wheat mandis by arrival volume.
```

The agent interprets it as:

```text
Crop       → Wheat
Metric     → Arrival Quantity
Grouping   → Mandi
Ranking    → Top 5
```

It then performs the required calculation and generates the corresponding visualization.

---

## ⚠️ Important Data Rules

### Rice and Paddy

Rice and Paddy are maintained as **separate crop categories** in the cleaned data and are not automatically merged.

### Price Crash

A price crash is defined as:

```text
modal_price < msp
```

Price-crash analysis is performed only where the required price and MSP values are available.

### Weather Limitation

The weather dataset is a **national daily aggregate**.

There is no sensor-to-mandi or sensor-to-district mapping in the source data.

Therefore:

- Weather is not presented as mandi-specific.
- Weather is not presented as district-specific.
- Weather analysis uses `date` as the common relationship with the other datasets.
- The agent does not make unsupported mandi-level rainfall claims.

### Transport Delay

The default transport delay threshold is:

```text
12 hours
```

---

## 🛠️ Technology Stack

- **Python**
- **Streamlit**
- **Pandas**
- **NumPy**
- **Plotly**

The application is designed to operate without a paid external AI API.

---

## 📁 Files

```text
bonus_agent/
├── app.py
├── requirements.txt
└── README.md
```

### `app.py`
Main Streamlit application containing the natural-language analytics, data processing and visualization logic.

### `requirements.txt`
Contains the Python packages required to run the application.

### `README.md`
Documentation for the Bonus AI Agent.

---

## ▶️ Run Locally

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
streamlit run app.py
```

The Streamlit application will open in the browser.

---

## 🔍 Example Agent Flow

### User Question

```text
Show the daily arrival trend for Wheat.
```

### Agent Interpretation

```text
Domain: Arrivals
Intent: Arrival Trend
Crop: Wheat
```

### Processing

1. Filter arrival records for Wheat.
2. Aggregate arrival quantity by date.
3. Generate a Plotly line chart.
4. Calculate relevant statistics.
5. Display a factual analytical insight.

### Output

The agent produces:

- Interactive Plotly visualization
- Date-wise arrival trend
- Calculated analytical insight
- Underlying calculated data where applicable

---

## 🏆 Datathon Value

The Bonus AI Agent extends the main Power BI analytics solution by adding a natural-language interface to the cleaned data.

Instead of manually navigating dashboard filters, users can directly ask analytical questions.

For example:

```text
Which 10 mandis had the highest Wheat arrivals?
```

The agent converts the question into an analytical operation and returns a visualization and insight.

### Overall Project Flow

```text
Raw Agricultural Data
        ↓
Data Cleaning Pipeline
        ↓
Clean Analytics Layer
        ↓
Power BI Dashboard
        ↓
Natural Language AI Analytics Agent
```

---

## 🔮 Future Enhancements

- More natural-language query patterns
- Conversational follow-up questions
- Advanced statistical analysis
- Forecasting
- Anomaly detection
- Multilingual queries
- Additional agricultural datasets

---

## 🏁 Project Information

**Datathon:** TransOrg AgentIQ Datathon

**Track:** Track 3 – AgriTech

**Project:** Mandi-to-Market Supply Chain Optimizer

**Component:** Bonus AI Analytics Agent

**Platform:** Streamlit
