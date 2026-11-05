"""
TransitIQ Backend REST API Server
Provides production and demo-ready endpoints for the Frontend.
Supports DEMO_MODE=1 to run strictly on precomputed outputs with zero raw data dependencies.

Endpoints:
- GET /
- GET /api/kpis
- GET /api/control-room-alerts?date=...&hour=...&limit=...
- GET /api/rebalance-pairs?depot=...&date=...&limit=...
- GET /api/routes?date=...&hour=...&depot=...&limit=...
- GET /api/dashboard
"""
import os
import json
import math
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

ROOT = Path(__file__).resolve().parent.parent
DEMO_MODE = os.environ.get("DEMO_MODE", "1") == "1"

app = FastAPI(
    title="TransitIQ Predictive Transit Dispatch API",
    description="Replay-mode demo ETM predictive dispatch and depot rebalancing engine for urban bus networks.",
    version="2.1.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache for fast querying
_routes_df_cache = None

def get_cached_routes_df():
    global _routes_df_cache
    if _routes_df_cache is None:
        gz_path = ROOT / "outputs/demo/route_hour_predictions.csv.gz"
        if gz_path.exists():
            _routes_df_cache = pd.read_csv(gz_path, compression="gzip")
        else:
            queue_path = ROOT / "outputs/backtest/tables/priority_queue_top50_daily.csv"
            if queue_path.exists():
                _routes_df_cache = pd.read_csv(queue_path)
            else:
                _routes_df_cache = pd.DataFrame()
    return _routes_df_cache

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "TransitIQ Predictive Transit Dispatch API (Replay-mode demo)",
        "demo_mode": DEMO_MODE,
        "telemetry_source": "67.8M ETM Telemetry Replay Feed (March 2026)",
        "endpoints": [
            "/api/kpis",
            "/api/control-room-alerts",
            "/api/rebalance-pairs",
            "/api/routes",
            "/api/dashboard",
            "/openapi.json"
        ]
    }

@app.get("/api/kpis")
def get_kpis():
    """Returns verified headline model performance and operational backtest metrics."""
    return {
        "model_version": "XGBoost 60-Min Ex-Ante (10 Strict Cutoff Features)",
        "evaluation_period": "March 27-31, 2026 (5-Day Out-of-Time Test Set, 56,781 slots)",
        "forecast_accuracy": {
            "mae_reduction_pct_vs_strongest_baseline": 21.7,
            "model_mae_passengers": 39.35,
            "baseline_mae_passengers": 50.24,
            "citywide_wape_percent": 18.25,
            "r2_score": 0.9571,
            "tag": "MEASURED"
        },
        "overcrowding_early_warning": {
            "lead_time_minutes": 60,
            "early_capture_recall_percent": 88.60,
            "roc_auc": 0.9178,
            "pr_auc": 0.7816,
            "tag": "MEASURED"
        },
        "operational_queue_precision": {
            "queue_policy": "Priority-Ordered Dispatch Queue (Capped at 50 Actions/Day)",
            "strict_precision_percent": 97.20,
            "true_positives": 243,
            "total_alerts_evaluated": 250,
            "fleet_injection_precision": 98.32,
            "fleet_injection_count": 238,
            "short_turn_precision": 75.00,
            "short_turn_count": 12,
            "historical_recurrence_baseline_precision_percent": 53.20,
            "historical_recurrence_baseline_description": "Top 50/day by historical recurrence >=70% (Route daily recurrence)",
            "excess_riders_addressed_pax": 143589,
            "excess_riders_share_percent": 11.45,
            "share_of_queue_alerts_on_non_chronic_routes": 1.20,
            "tag": "MEASURED"
        },
        "depot_rebalancing_simulation": {
            "constraint": "Strict Single-Allocation Same-Depot Gate Matching",
            "unique_operations_count": 216,
            "total_fleet_transferred": 759,
            "total_capacity_moved_pax": 53130,
            "total_actual_passenger_reduction": 49485,
            "receiver_pre_dcr_mean": 1.43,
            "receiver_post_dcr_mean": 1.11,
            "donor_pre_dcr_mean": 0.35,
            "donor_post_dcr_mean": 0.49,
            "donor_post_dcr_p95": 0.73,
            "donor_post_dcr_max": 0.80,
            "donor_safety_cap": "DCR <= 0.80x by design (Retains >= 60% fleet)",
            "overcrowded_receivers_normalized_percent": 50.46,
            "tag": "SIMULATED"
        },
        "production_readiness": {
            "batch_inference_latency_ms": 138,
            "runtime_ram_footprint_mb": 245,
            "routes_evaluated": 705,
            "depots_covered": 16,
            "tag": "MEASURED"
        }
    }

@app.get("/api/control-room-alerts")
def get_control_room_alerts(
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD), e.g. 2026-03-27"),
    hour: Optional[int] = Query(None, description="Filter by hour (0-23), e.g. 8"),
    limit: int = Query(50, description="Max alerts to return")
):
    """
    Returns prioritized actionable dispatch cards for the control room.
    Supports date and hour filtering.
    """
    queue_path = ROOT / "outputs/backtest/tables/priority_queue_top50_daily.csv"
    if not queue_path.exists():
        return []
    
    df = pd.read_csv(queue_path)
    if isinstance(date, str):
        df = df[df['date'] == str(date)]
    if isinstance(hour, (int, str)) and not hasattr(hour, "default"):
        df = df[df['hour'] == int(hour)]
    actual_limit = limit.default if hasattr(limit, "default") else int(limit)
        
    alerts = []
    for idx, r in df.head(actual_limit).iterrows():
        rt = str(r['route_id'])
        dt = str(r['date'])
        hr = int(r['hour'])
        p_dcr = float(r['pred_dcr'])
        defic = int(r['pred_deficit'])
        cat = str(r['action_category'])
        prio = int(r['priority'])
        planned_buses = int(r.get('ex_ante_planned_buses', r.get('active_buses', 0)))
        planned_cap = planned_buses * 70
        pred_pax = int(r.get('pred_pax', r.get('pax', 0)))
        active_buses_obs = int(r.get('active_buses', 0))
        depot_name = str(r.get('depot', 'Operating Depot'))
        
        if cat == 'Fleet Injection':
            needed_buses = max(1, int(math.ceil(defic / 70.0)))
            action_text = f"Priority 1: Fleet Injection (+{needed_buses} Reserve Buses)"
            reason = f"Route {rt} projected at {p_dcr:.2f}x Demand-to-Capacity Ratio (+{defic} passenger deficit)."
            impact = f"Decompresses corridor towards 1.0x capacity limit before departure."
        else:
            needed_buses = 0
            action_text = f"Priority 2: Short-Turn Loop at Major Midpoint Terminal"
            reason = f"Route {rt} projected at {p_dcr:.2f}x DCR with headway clustering."
            impact = f"Turns trailing bus early to clear passenger queue at bottleneck corridor."

        alerts.append({
            "alert_id": f"ALT-{dt}-{hr:02d}-{rt}",
            "route_id": rt,
            "depot": depot_name,
            "date": dt,
            "hour": hr,
            "time_window": f"{hr:02d}:00 - {hr+1:02d}:00",
            "priority": prio,
            "action_category": cat,
            "planned_buses": planned_buses,
            "planned_capacity_seats": planned_cap,
            "predicted_pax": pred_pax,
            "predicted_dcr": round(p_dcr, 2),
            "predicted_deficit_pax": defic,
            "reserve_buses_needed": needed_buses,
            "recommended_action": action_text,
            "operational_reason": reason,
            "expected_impact": impact,
            "observed_active_buses_ex_post": active_buses_obs,
            "verified_same_hour_overcrowded": bool(r['ground_truth_dcr'] > 1.0)
        })
    return alerts

@app.get("/api/rebalance-pairs")
def get_rebalance_pairs(
    depot: Optional[str] = Query(None, description="Filter by depot name, e.g. Tambaram Depot"),
    date: Optional[str] = Query(None, description="Filter by date, e.g. 2026-03-30"),
    limit: int = Query(100, description="Max pairs to return")
):
    """
    Returns single-allocation donor-receiver depot rebalancing pairs.
    Supports depot and date filtering.
    """
    pairs_path = ROOT / "outputs/backtest/tables/single_allocation_rebalance_pairs.csv"
    if not pairs_path.exists():
        return []
    
    df = pd.read_csv(pairs_path)
    if isinstance(depot, str):
        df = df[df['depot'].str.contains(depot, case=False, na=False)]
    if isinstance(date, str):
        df = df[df['date'] == str(date)]
    actual_limit = limit.default if hasattr(limit, "default") else int(limit)
        
    records = []
    for idx, r in df.head(actual_limit).iterrows():
        records.append({
            "operation_id": f"REBAL-{r['date']}-{int(r['hour']):02d}-{r['depot'][:3].upper()}-{idx+1}",
            "depot": r['depot'],
            "date": r['date'],
            "hour": int(r['hour']),
            "time_window": f"{int(r['hour']):02d}:00 - {int(r['hour'])+1:02d}:00",
            "receiver_route": f"Route {r['receiver_route']}",
            "donor_route": f"Route {r['donor_route']}",
            "buses_transferred_k": int(r['k_transfer']),
            "receiver_pre_dcr": round(float(r['pre_dcr_rec']), 2),
            "receiver_post_dcr": round(float(r['post_dcr_rec']), 2),
            "donor_pre_dcr": round(float(r['pre_dcr_don']), 2),
            "donor_post_dcr": round(float(r['post_dcr_don']), 2),
            "donor_safety_verified": bool(r['post_dcr_don'] <= 0.80),
            "receiver_reaches_capacity_target": bool(r['reaches_1_0'] == 1),
            "capacity_moved_pax": int(r['capacity_moved_pax']),
            "actual_passenger_reduction": int(r['actual_passenger_reduction']),
            "tag": "SIMULATED"
        })
    return records

@app.get("/api/routes")
def get_routes(
    date: Optional[str] = Query(None, description="Filter by date, e.g. 2026-03-27"),
    hour: Optional[int] = Query(None, description="Filter by hour, e.g. 8"),
    depot: Optional[str] = Query(None, description="Filter by depot name, e.g. Adyar"),
    limit: int = Query(100, description="Max records to return")
):
    """
    Returns route predictions and loads for all 56,781 route-hours.
    Supports filtering by date, hour, and depot.
    """
    df = get_cached_routes_df()
    if df.empty:
        return []
    
    if isinstance(date, str):
        df = df[df['date'] == date]
    if isinstance(hour, (int, str)) and not hasattr(hour, "default"):
        df = df[df['hour'] == int(hour)]
    if isinstance(depot, str):
        df = df[df['depot'].str.contains(depot, case=False, na=False)]
    actual_limit = limit.default if hasattr(limit, "default") else int(limit)
        
    records = []
    for idx, r in df.head(actual_limit).iterrows():
        records.append({
            "route_id": str(r['route_id']),
            "depot": str(r.get('depot', 'Unknown')),
            "date": str(r['date']),
            "hour": int(r['hour']),
            "planned_buses": int(r.get('ex_ante_planned_buses', r.get('active_buses', 1))),
            "active_buses": int(r.get('active_buses', 1)),
            "predicted_pax": round(float(r.get('pred_pax_60m', r.get('pred_pax', 0))), 1),
            "actual_pax": int(r.get('pax', 0)),
            "predicted_dcr": round(float(r.get('pred_dcr_60m', r.get('pred_dcr', 0))), 2),
            "actual_dcr": round(float(r.get('ground_truth_dcr', 0)), 2),
            "predicted_overcrowding_probability": round(float(r.get('pred_proba_60m', r.get('pred_proba', 0))), 4),
            "is_overcrowded": bool(r.get('ground_truth_overcrowded', 0) == 1)
        })
    return records

@app.get("/api/dashboard")
def get_dashboard():
    """Combined executive overview payload for the full frontend dashboard."""
    kpis = get_kpis()
    alerts = get_control_room_alerts(limit=10)
    pairs = get_rebalance_pairs(limit=5)
    return {
        "system_metadata": {
            "city": "Chennai",
            "operator": "Metropolitan Transport Corporation (MTC)",
            "telemetry_source": "67.8M ETM Ticket Logs Replay Feed",
            "model_version": "TransitIQ Dual XGBoost (60-Min Strict Ex-Ante)",
            "status": "Operational",
            "demo_mode": DEMO_MODE
        },
        "kpis": kpis,
        "critical_alerts_preview": alerts,
        "depot_rebalance_preview": pairs
    }

if __name__ == "__main__":
    print(f"Starting TransitIQ REST API Server (DEMO_MODE={DEMO_MODE}) on http://localhost:8000 ...")
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=False, app_dir=str(ROOT / "src"))
