# TransitIQ — Chennai MTC Control-Room Copilot

TransitIQ is a 60-minute ex-ante corridor overcrowding prediction and operational copilot designed specifically for control-room operators managing Chennai's Metropolitan Transport Corporation (MTC) bus network.

---

## Core Operational Metric: DCR

$$\text{DCR} = \frac{\text{Hourly Boardings}}{\text{Active Buses} \times 70\text{ Seats}}$$

- **Over capacity threshold**: $\text{DCR} > 1.0$ (passenger demand exceeds available seating capacity).
- **Near capacity**: $0.85 < \text{DCR} \le 1.0$.
- **Balanced service**: $0.41 \le \text{DCR} \le 0.85$.
- **Surplus / Donor**: $\text{DCR} \le 0.40$ (candidate for dispatch rebalancing).

*Important:* DCR measures corridor passenger throughput against scheduled seat-hours, **not** instantaneous on-board vehicle passenger load.

---

## Design System Rules

- **Palette**:
  - Sky `#E8EFF5` (base background and atmospheric fog)
  - Cream `#F4ECD8` (panels, dialogs, cards)
  - Ink `#1F2630` (text, borders)
  - Accent Orange `#E8692A` (primary MTC brand accent)
  - **Status colours are strictly restricted to DCR**:
    - Green $\le 0.85$
    - Amber $0.85 - 1.0$
    - Red $> 1.0$
    - Blue $\le 0.40$ (donor surplus)
- **Typography**:
  - Headings in **Georgia** (serif)
  - Body and metrics in **Inter** (sans-serif)
  - Sentence case everywhere
- **Aesthetic discipline**: Flat fills, 1px hairline borders, 8px grid, no purple, no glassmorphism, no soft glow, no emoji.
- **Figure provenance**: Every KPI carries an explicit `MEASURED` or `SIMULATED` tag. Rebalancing figures are always `SIMULATED`.

---

## Architecture & Views

### 1. Drive Mode (`/`)
- **Procedural 3D WebGL scene**: Flat-shaded low-poly terrain, winding asphalt road with dashed markings, instanced trees and modern flat-roof structures.
- **Low-poly MTC Chase Bus**: Orange chassis `#E8692A`, cream windows `#F4ECD8`, arcade steering physics, ground elevation clamping.
- **Dashed Ring Zones**:
  1. *Control room* (`[0, 0, -45]`): Features active alert count badge.
  2. *Depot yard* (`[55, 0, 10]`): Canopy architecture and bay markers.
  3. *Fleet* (`[-50, 0, 35]`): Terminal board display.
  4. *Scorecard* (`[15, 0, 65]`): Calibration obelisk.
- **Interactive Proximity**: Entering a zone prompts `"Press Enter to open"`, sliding in the matching classic screen component as a side drawer (`Esc` to close).
- **"Take me there" Menu**: Auto-steers the bus directly to any zone.
- **Hardware Fallback**: Automatically bypasses WebGL and routes to `/control-room` if hardware acceleration is unavailable or if `prefers-reduced-motion` is detected.

### 2. Classic Screens
- **Control Room (`/control-room`)**:
  - 4-metric KPI strip (forecast error reduction, 60-min lead time, priority queue precision, telemetry anomalies).
  - Date and hour picker (06:00 to 22:00) with depot filtering.
  - Ranked alert queue displaying predicted DCR bar, expected passenger deficit, recommended action (`fleet_injection` or `short_turn`), reason, impact, and local state Accept/Dismiss controls.
- **Depots (`/depots`)**:
  - Depot selector and candidate rebalancing pairs.
  - Interactive slider for movable buses ($0$ to $k$) recalculating before/after DCR live:
    $$\text{New DCR} = \frac{\text{Passengers}}{(\text{Buses} \pm \text{Moved}) \times 70}$$
  - Dynamic plain note: *"partly relieved: donor service is protected"*.
- **Fleet (`/fleet`)**:
  - Searchable by route ID and depot.
  - Category filters: All, Over capacity, Near capacity, Balanced, Surplus.
  - Dense bordered table with DCR color chips and risk probability indicators.
- **Scorecard (`/scorecard`)**:
  - Comprehensive model evaluation: MAE reduction (21.6%), WAPE (14.2%), $R^2$ (0.84), ROC-AUC (0.912), PR-AUC (0.884), 2-stage wide-net & priority queue precision (97.2%), anomaly counters (881), simulated rebalance metrics (49.1% resolved).
  - Dedicated **Limits** section detailing evaluation boundaries (31-day CUMTA ticket replay, DCR vs on-board load, 70-seat baseline assumption, simulated rebalance dispatch).
- **Judge's Dataset Explorer (`/dataset`)**:
  - Direct integration and telemetry audit of CUMTA Hackathon Theme 4 datasets:
    1. **ETM Ticket Replay**: 31 days (March 01–31, 2026), 75M+ passenger trip records across 36 columns.
    2. **MTC GIS Route Network**: 1,348 spatial polyline records (680 commercial routes) from `routes_merged.shp / .dbf`.
    3. **CMA Geocoded Bus Stops**: 2,720 bus stops across Greater Chennai Corporation (2,228), Tambaram Corporation (348), and Avadi Corporation (144).
    4. **Multimodal Layers**: Chennai Metro Rail (CMRL), Suburban Rail (Beach-Tambaram, MRTS), and CMA arterial roads.
  - Interactive raw telemetry packet stream inspector, depot distribution matrix, and geocoded stop lookup.
- **Footer Pill**: Present on all screens:
  `"Telemetry: ETM ticket replay | Engine: 60-minute ex-ante XGBoost"`

---

## Running the Project

### Installation
```bash
npm install
```

### Development Server
```bash
npm run dev
```
Navigate to `http://localhost:5173/`.

### Production Build
```bash
npm run build
npm run preview
```
