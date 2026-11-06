# 🚍 Marina Sentinel — Chennai MTC Control-Room Copilot

> **Zero-Capex Decision-Support System, Real-Time Passenger Load Conservation & Ex-Ante Delay Prediction for the Metropolitan Transport Corporation (MTC) Chennai.**  
> *Developed for CUMTA Smart Public Transport Operations (Theme 4).*

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%20%2B%20Python%203.9+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React%2018%20%2B%20TypeScript-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Leaflet](https://img.shields.io/badge/GIS-Leaflet%20%2B%20OpenStreetMap-199900?logo=leaflet&logoColor=white)](https://leafletjs.com/)
[![Vite](https://img.shields.io/badge/Bundler-Vite%208-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)

---

## 📌 Executive Overview

Chennai MTC operates over 3,300 buses serving 3.3M+ daily passenger journeys. The primary operational bottleneck is **spatial-temporal supply-demand mismatch**: diesel buses frequently run nearly empty along secondary loops ($DCR < 0.40\times$, wasting fuel) while core radial corridors simultaneously suffer dangerous passenger crush loads ($DCR \ge 1.25\times$), causing denied boardings, door-hanging, and cascading terminal delays.

**Marina Sentinel** eliminates this mismatch with **Zero Capital Expenditure**:
1. **DCR Compression Engine**: Reallocates surplus bus capacity from low-demand donor lines to over-capacity recipient corridors within the same depot yard.
2. **Passenger Conservation Law (On-Board Occupancy)**: Solves for instantaneous vehicle passenger load ($N_{\text{pax}}$) by integrating Electronic Ticketing Machine (ETM) stage transactions.
3. **Ex-Ante Bus Delay Forecaster**: Predicts vehicle delays 30–60 minutes in advance by modeling inbound turnaround cascade delays and passenger dwell-time inflation.
4. **Interactive Chennai GIS Live Transit Map (`/live-map`)**: Real OpenStreetMap canvas rendering arterial corridors, 2,717 geocoded stops, 12 multimodal transfer hubs, and live bus loads.

---

## 📐 Mathematical Formulations

### 1. Demand-to-Capacity Ratio (DCR)
The foundational equilibrium metric for corridor $c$ at hour $t$:

$$\text{DCR}_{c, t} = \frac{D_{c, t}}{C_{c, t}} = \frac{\sum_{i \in \text{buses}} P_{i, c, t}}{N_{c, t} \times \text{Cap}_{\text{bus}}}$$

- **$\text{Cap}_{\text{bus}}$**: Certified vehicle baseline ($42\text{ seated} + 28\text{ legal standees} = 70\text{ pax}$; crush cap $= 98$).
- **DCR Bands**:
  - $\text{DCR} \ge 1.25\times$: 🔴 **Critical Overcrowding** (safety risk, denied boardings).
  - $1.00\times \le \text{DCR} < 1.25\times$: 🟠 **Near Capacity** (standee crush).
  - $0.70\times \le \text{DCR} < 1.00\times$: 🟢 **Balanced Service** (optimal revenue & comfort).
  - $\text{DCR} < 0.70\times$: ⚪ **Surplus / Donor Candidate** (inefficient diesel allocation).

---

### 2. Fleet Rebalancing Optimization (Bipartite Capacity Transfer)
Rebalances surplus capacity without deadheading between distant depots:

$$\min \sum_{s \in \mathcal{S}} \sum_{d \in \mathcal{D}} x_{s \to d} \cdot \text{Cost}_{s \to d}$$

$$\text{Subject to:}$$
$$1. \quad \text{DCR}_{d, t}^{\text{post}} = \frac{D_{d, t}}{(N_{d, t} + \sum_{s} x_{s \to d}) \times 70} \le 0.95$$
$$2. \quad \text{DCR}_{s, t}^{\text{post}} = \frac{D_{s, t}}{(N_{s, t} - \sum_{d} x_{s \to d}) \times 70} \le 0.80 \quad \text{(Donor service guarantee)}$$
$$3. \quad x_{s \to d} \in \mathbb{Z}^+, \quad \text{Depot}(s) \equiv \text{Depot}(d) \quad \text{(Same-depot physical canopy)}$$

---

### 3. Passenger Conservation Law (Vehicle Occupancy Tracking)
Because buses lack automated weight sensors, on-board load is derived from ETM ticket stage logs:

$$\text{Occupancy}(s_k) = \text{Occupancy}(s_{k-1}) + \text{Boardings}(s_k) - \text{Alightings}(s_k)$$

$$\text{Boardings}(s_k) = \sum_{j} \mathbb{I}(\text{ETM Origin} = s_k)$$

$$\text{Alightings}(s_k) = \sum_{i < k} \text{Boardings}(s_i) \cdot \mathbb{P}(\text{Destination} = s_k \mid \text{Origin} = s_i)$$

- **Boundary Invariants**:
  $$\text{Occupancy}(s_0) = 0, \quad \text{Occupancy}(s_{\text{terminal}}) = 0$$
  $$\sum_{k=1}^{M} \text{Boardings}(s_k) \equiv \sum_{k=1}^{M} \text{Alightings}(s_k) = \text{Total Trip Headcount}$$

---

### 4. Ex-Ante Bus Delay Forecaster
Delays are forecasted before trip dispatch via two non-linear physical components:

$$\text{Delay}_{\text{predicted}}(i) = \Delta t_{\text{cascade}}(i) + \sum_{s \in \text{Remaining Stops}} \Delta t_{\text{dwell}}(i, s)$$

#### Inbound Cascade Turnaround Delay ($\Delta t_{\text{cascade}}$):
$$\Delta t_{\text{cascade}}(i) = \max\left(0, \ T_{\text{actual, inbound arrival}} + \tau_{\text{mandatory crew break (15m)}} - T_{\text{scheduled, outbound departure}}\right)$$

#### Non-Linear Dwell Time Friction ($\Delta t_{\text{dwell}}$):
$$t_{\text{dwell}}(s) = t_0 + \alpha B(s) + \beta A(s) + \gamma \cdot \max\left(0, \ \frac{\text{Occupancy}(s)}{\text{Cap}_{\text{bus}}} - 1.0\right)^2$$
- $t_0$: Base door cycle and brake interlock ($12\text{ s}$).
- $\alpha$: Boarding friction ($1.8\text{ s/pax}$).
- $\beta$: Alighting friction ($1.2\text{ s/pax}$).
- $\gamma$: Standee congestion penalty ($15\text{ s}$ when passengers must squeeze past crowded aisles).
- **Public Information System (PIS) ETA**:
  $$\text{ETA}_{\text{stop}} = T_{\text{scheduled}} + \text{Delay}_{\text{predicted}}$$

---

## 🗺️ Ingested Datasets

| Dataset | Scope & Dimensions | Operational Role in Marina Sentinel |
| :--- | :--- | :--- |
| **ETM Ticket Replay Logs** | 31 full days of March 2026, 75M+ transactions across 36 columns (`ETM_1_to_30_june.parquet`) | Passenger demand generation, stage boarding/alighting rates, waybill verification, Vidiyal Payana Thittam free-ticket share. |
| **MTC GIS Route Network** | Shapefiles (`routes_merged.shp / .dbf`), 1,348 polyline segments, 680 commercial routes | High-precision road corridor alignments for 102CT, 29C, 21G, 19B, 18A, 23C, 48C, 44. |
| **Geocoded Bus Stops List** | 2,717 bus stops from `Tambaram, Avadi, GCC Bus Stops List 1.xlsx` | Spatial coordinate geocoding across Greater Chennai, Tambaram, and Avadi municipal zones. |
| **Multimodal Nodes** | 12 Chennai Hubs (Central, Egmore, CMBT Koyambedu, Tambaram, Guindy, Broadway, etc.) | Commuter PIS alternate routing advisories across Metro and Suburban rail. |

---

## 🖥️ Platform Architecture & Views

### 1. Chennai Live Transit Map (`/live-map`)
- **OpenStreetMap Canvas**: Fast Leaflet map rendering Chennai arterial roads with zero API key restrictions.
- **Live Fleet Badges**: Dynamic markers showing Route, instantaneous passenger count (e.g. `78p`), and predicted delay (e.g. `+18m`).
- **Telemetry Replay Inspector**: Click on any bus to inspect depot allocation, speed, boarding/alighting balances, root-cause delay attribution, and automated commuter PIS advisories.
- **Corridor & Hub Overlays**: Toggle GIS shapefile routes and 12 transfer hubs.

### 2. Control Room Alert Queue (`/control-room`)
- **4-Metric Performance Strip**: Real-time KPI summary (Forecast error reduction, 60-min lead time window, 97.2% priority queue precision, 881 anomalies).
- **Temporal Dispatch Slider**: Interactive hour picker (06:00 to 22:00) with depot filtering.
- **Ranked Action Queue**: Actionable dispatch directives (`fleet_injection` vs `short_turn`) with instant operator Accept/Dismiss actions.

### 3. Depots & Fleet Rebalancing (`/depots`)
- **Intra-Depot Rebalance Simulator**: Candidate donor-receiver pairs filtered by physical depot canopy.
- **Interactive Move Slider**: Adjust moved vehicles ($0 \to k$) to observe before/after DCR shifts in real-time.
- **Independent Split Layout**: Left pairs list scrolls independently while the right simulation studio stays pinned (`position: sticky`).

### 4. Fleet Master Table (`/fleet`)
- Dense, searchable tabular overview of all 945 routes across 33 depots.
- Categorized by DCR severity with instant route search.

### 5. Scientific Backtest Scorecard (`/scorecard`)
- Model performance benchmarks: MAE Reduction (21.6%), WAPE (14.2%), $R^2$ (0.84), ROC-AUC (0.912).
- Density methodology chart breakdown and evaluation limits disclosure.

### 6. Judge's Dataset Explorer (`/dataset`)
- Audit trail displaying all 2,717 geocoded stops across GCC, Tambaram, and Avadi.
- Raw telemetry packet schema inspector with live waybill breakdown.

---

## ⚖️ Pros and Cons Breakdown

### ✅ Key Strengths
- **Zero Capex**: Achieves peak-hour crowd relief algorithmically without purchasing new buses.
- **Ex-Ante Anticipation**: Predicts bottlenecks 30–60 minutes ahead, allowing proactive dispatch instead of reactive chaos.
- **Strict Donor Protection**: Hard constraint ensures donor lines never exceed $DCR = 0.80\times$.
- **Native Hardware Compatibility**: Ingests existing ETM transaction logs without installing costly on-board IoT weight sensors.

### ⚠️ Known Limitations
- **Concession Ticket Leakage**: Heavy rush periods may result in missed zero-fare ticket logging for women passengers ($5\text{--}12\%$ undercount variance).
- **Traffic Disruption Independence**: Currently relies on dwell friction and cascade delays; does not yet ingest live Google Traffic API for external flooding/accident gridlocks.
- **Crew Shift Rigidity**: Midday vehicle reassignments require coordination with depot crew rosters and union shift timings.

---

## 🚀 Getting Started

### Prerequisites
- **Node.js** v18+ and **npm**
- **Python** 3.9+

### 1. Clone Repository
```bash
git clone https://github.com/nivethaselvam-2411/voyage.git
cd voyage
```

### 2. Backend Setup (FastAPI)
```bash
# Install Python dependencies
pip install -r requirements.txt

# Start FastAPI API server (port 8000)
python -m uvicorn src.api_server:app --host 127.0.0.1 --port 8000
```
Backend Swagger documentation available at: `http://127.0.0.1:8000/docs`

### 3. Frontend Setup (React + Vite)
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Vite development server (port 3000)
npm run dev -- --host 127.0.0.1 --port 3000
```

### 4. Build for Production
```bash
cd frontend
npm run build
```

---

## 📊 Backtest Figure: Operational Density Compression
The 4-panel backtest figure demonstrating DCR compression, 24-hr peak surge flattening, funnel throughput, and capacity-moved spatial density is generated at:
`outputs/backtest/figures/density_methodology_chart.png`

---

## 👥 Authors & Acknowledgments
- **Project**: Marina Sentinel — Chennai MTC Control-Room Copilot
- **Data Source**: Chennai Unified Metropolitan Transport Authority (CUMTA) & Metropolitan Transport Corporation (MTC)
- **Repository**: [github.com/nivethaselvam-2411/voyage](https://github.com/nivethaselvam-2411/voyage)
