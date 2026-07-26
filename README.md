# 🔍 CrimeGraph — AI-Powered Crime Analytics Platform

<div align="center">

![KSP Datathon 2026](https://img.shields.io/badge/KSP%20Datathon-2026-blue?style=for-the-badge)
![Challenge](https://img.shields.io/badge/Challenge-02%20Crime%20Analytics-red?style=for-the-badge)
![Team](https://img.shields.io/badge/Team-G--One-green?style=for-the-badge)

**An end-to-end AI-powered crime analytics platform built for Karnataka State Police**  
*Transforming fragmented crime records into actionable intelligence*

</div>

---

## 📌 Problem Statement

Karnataka State Police manages crime data from **1100+ police stations** across the state. The existing systems suffer from:

- ❌ Siloed, fragmented data with no unified view
- ❌ Manual reporting with no real-time insights
- ❌ No predictive or proactive policing capabilities
- ❌ Limited ability to detect criminal networks or repeat offenders
- ❌ No correlation between crime patterns and socio-economic factors

---

## 💡 Our Solution — CrimeGraph

CrimeGraph is a modern **AI-driven crime analytics and visualization platform** that transforms raw police records into deep, actionable intelligence for investigators and decision-makers.

> "Don't just record crime — understand it, predict it, prevent it."

---

## ✨ Key Features

### 🗺️ 1. Geospatial Crime Heatmaps
- Interactive map showing crime density across Karnataka districts
- **Time-of-day filtering** — morning, afternoon, evening, night
- Hotspot detection highlighting high-risk zones
- Built with **Leaflet.js + leaflet.heat**

### 🕸️ 2. Criminal Network Analysis
- Graph-based **link analysis** connecting accused, victims, and police stations
- **Louvain community detection** to identify criminal clusters and gangs
- Visual node-edge network with color-coded roles:
  - 🔴 Accused persons
  - 🔵 Victims  
  - 🟡 Police stations
- Built with **NetworkX + D3.js**

### 📈 3. Trend Alerts & Anomaly Detection
- **Z-score based statistical anomaly detection** on crime trends
- District-level red-zone alerts when crime spikes beyond threshold
- Real-time severity scoring per district
- Identifies unusual patterns before they escalate

### ⚠️ 4. Predictive Risk Scoring
- **LightGBM ML model** trained on case features to predict risk
- Flags open cases with high probability of going undetected
- Risk score between 0–1 with explainability via **SHAP values**
- Helps investigators prioritize which cases need immediate attention

### 📊 5. Socio-Economic Crime Correlation
- Overlays crime data with **district-level socio-economic indicators**
- Correlates crime rates with unemployment, literacy, poverty metrics
- Helps policymakers understand root causes, not just symptoms

### 🔁 6. Repeat Offender Tracking
- **MO (Modus Operandi) signature profiling** for each accused
- Identifies repeat offenders across different cases and districts
- Entity resolution to match same person across name variations
- Tracks behavioral patterns over time

---

## 🏗️ System Architecture
```

┌─────────────────────────────────────────────────────┐
│ FRONTEND (React) │
│ Heatmap Tab │ Network Graph Tab │ Intelligence Tab  │
└──────────────────────┬──────────────────────────────┘
                       │ REST API calls
┌──────────────────────▼──────────────────────────────┐
│ BACKEND (FastAPI)                                   │
│ /heatmap /network /risk-scores /trend-alerts        │
│ /socioeconomic /repeat-offenders /anomalies         │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│ ML / ANALYTICS LAYER                                │                            
│ LightGBM Risk Scoring │ NetworkX Graph Analysis     │
│ Z-Score Anomaly Detection │ SHAP Explainability     │
│ Louvain Community Detection │ MO Profiling          │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│ SYNTHETIC DATA LAYER (CSV)                          │
│ CaseMaster │ Accused │ Victim │ District            │
│ ArrestSurrender │ ChargesheetDetails │ ...          │
└─────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React + Vite | UI framework |
| **Maps** | Leaflet.js + leaflet.heat | Geospatial heatmaps |
| **Network Viz** | D3.js | Criminal network graphs |
| **Backend** | FastAPI (Python) | REST API server |
| **ML - Risk** | LightGBM + SHAP | Predictive risk scoring |
| **ML - Network** | NetworkX + python-louvain | Graph analysis |
| **ML - Anomaly** | Scipy (Z-score) | Trend detection |
| **Data Processing** | Pandas + NumPy | Data pipeline |
| **Visualization** | Plotly | Charts & graphs |

---

## 📁 Project Structure
```
CRIMEGRAPH/
│
├── frontend/ # React frontend
│ ├── src/
│ │ ├── App.jsx # Main app + routing
│ │ ├── Dashboard.jsx # Intelligence tab
│ │ ├── HeatmapLayer.jsx # Crime heatmap
│ │ ├── NetworkView.jsx # Criminal network graph
│ │ └── tokens.css # Design system
│ ├── package.json
│ └── vite.config.js
│
├── Generator/ # Python backend + ML
│ ├── api_server.py # FastAPI server (main entry)
│ ├── risk_scoring.py # LightGBM risk model
│ ├── anomaly_detection.py # Z-score trend alerts
│ ├── network_graph.py # NetworkX graph builder
│ ├── socioeconomic_correlation.py # Socio-economic analysis
│ ├── entity_resolution.py # Repeat offender matching
│ ├── mo_extraction.py # MO signature profiling
│ ├── score_open_cases.py # Open case risk pipeline
│ └── requirements.txt # Python dependencies
│
├── synthetic_data/ # KSP-schema synthetic datasets
│ ├── CaseMaster.csv # Core case records
│ ├── Accused.csv # Accused persons
│ ├── Victim.csv # Victim records
│ ├── District.csv # Karnataka districts
│ ├── case_risk_scores.csv # ML model output
│ ├── trend_alerts.csv # Anomaly detection output
│ ├── network_graph.json # Graph data for visualization
│ ├── repeat_offender_profiles.csv
│ └── ... # 30+ structured CSV files
│
├── RISK_SCORING_RESULTS.md # Model evaluation & methodology
└── README.md

```
---

## 🚀 Getting Started

### Prerequisites
- Python 3.13+
- Node.js 18+
- npm

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/CRIMEGRAPH.git
cd CRIMEGRAPH
```

### 2. Start the Backend
```bash
cd Generator
pip install -r requirements.txt
python api_server.py
```
Backend runs at `http://localhost:8000`

### 3. Start the Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend runs at `http://localhost:5173`

### 4. Open in Browser
Navigate to `http://localhost:5173` and explore:
- **Heatmap Tab** — Crime density across Karnataka
- **Network Tab** — Criminal relationship graphs
- **Intelligence Tab** — Risk scores, alerts, socio-economic insights

---

## 📊 Data Schema

The synthetic dataset follows the **official KSP FIR database schema** with 30+ interconnected tables covering:

| Category | Tables |
|----------|--------|
| Case Records | CaseMaster, CaseCategory, CaseStatusMaster |
| Persons | Accused, Victim, ComplainantDetails |
| Legal | Act, Section, ChargesheetDetails, Court |
| Geography | District, Unit, State |
| Personnel | Employee, Rank, Designation |
| Analytics | case_risk_scores, trend_alerts, network_graph |

---

## 🧠 ML Models

### Risk Scoring (LightGBM)
- **Input:** Case features (crime type, district, time, accused count, etc.)
- **Output:** Risk score 0–1 (probability case goes undetected)
- **Explainability:** SHAP feature importance values
- **Threshold:** 0.6 = high risk flag

### Anomaly Detection (Z-Score)
- **Input:** District-wise crime counts over time
- **Output:** Z-score per district, red-zone alert if z > 2.0
- **Window:** Rolling 30-day baseline

### Network Analysis (Louvain)
- **Input:** Accused-Victim-Station relationships
- **Output:** Community clusters, centrality scores
- **Algorithm:** Louvain community detection on undirected graph

---

## 👥 Team INNOVATE X

Built for **KSP Datathon 2026**  
Karnataka State Police Hackathon — Challenge 02: AI-Driven Crime Analytics & Visualization Platform

---

## 📄 License

This project was built for hackathon purposes using **synthetic data only**.  
No real police records or PII were used.
