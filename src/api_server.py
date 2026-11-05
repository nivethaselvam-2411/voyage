"""
TransitIQ Backend REST API Server
Provides production and demo-ready endpoints for the Frontend.
Supports DEMO_MODE=1 to run strictly on precomputed outputs with zero raw data dependencies.

Endpoints:
- GET /
- GET /api/kpis
- GET /api/control-room-alerts
- GET /api/rebalance-pairs
- GET /api/routes
- GET /api/dashboard
"""
import os
import json
import math
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

ROOT = Path(__file__).resolve().parent.parent
DEMO_MODE = os.environ.get("DEMO_MODE", "1") == "1"

app = FastAPI(
    title="TransitIQ Predictive Transit Dispatch API",
    description="Real-time ETM predictive dispatch and depot rebalancing engine for urban bus networks.",
    version="2.0.0"
)

# Pre-configure CORS for frontend development (Vite, React, Next.js, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "TransitIQ Predictive Transit Dispatch API",
        "demo_mode": DEMO_MODE,
        "telemetry_source": "67.8M ETM Telemetry Replay Feed (March 2026)",
        "endpoints": [
            "/api/kpis",
            "/api/control-room-alerts",
            "/api/rebalance-pairs",
            "/api/routes",
            "/api/dashboard"
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
            "excess_riders_addressed_pax": 143589,
            "excess_riders_share_percent": 11.45,
            "tag": "MEASURED"
        },
        "depot_rebalancing_simulation": {
            "constraint": "Strict Single-Allocation Same-Depot Gate Matching",
            "unique_operations_count": 212,
            "total_fleet_transferred": 733,
            "receiver_pre_dcr_mean": 1.43,
            "receiver_post_dcr_mean": 1.11,
            "donor_pre_dcr_mean": 0.35,
            "donor_post_dcr_mean": 0.49,
            "donor_safety_cap": "DCR <= 0.80x by design (Retains >= 60% fleet)",
            "overcrowded_receivers_normalized_percent": 49.1,
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
def get_control_room_alerts(limit: int = 50):
    """
    Returns prioritized actionable dispatch cards for the control room.
    Reads dynamically from outputs/backtest/tables/priority_queue_top50_daily.csv.
    """
    queue_path = ROOT / "outputs/backtest/tables/priority_queue_top50_daily.csv"
    if not queue_path.exists():
        return []
    
    df = pd.read_csv(queue_path)
    alerts = []
    for idx, r in df.head(limit).iterrows():
        rt = str(r['route_id'])
        dt = str(r['date'])
        hr = int(r['hour'])
        p_dcr = float(r['pred_dcr'])
        defic = int(r['pred_deficit'])
        cat = str(r['action_category'])
        prio = int(r['priority'])
        buses = int(r.get('active_buses', 0))
        pax = int(r.get('pax', 0))
        
        if cat == 'Fleet Injection':
            needed_buses = max(1, int(np.ceil(defic / 70.0)))
            action_text = f"Priority 1: Fleet Injection (+{needed_buses} Reserve Buses)"
            reason = f"Route {rt} projected at {p_dcr:.2f}x Demand-to-Capacity Ratio (+{defic} passenger deficit)."
            impact = f"Decompresses corridor towards 1.0x capacity limit before departure."
        else:
            action_text = f"Priority 2: Short-Turn Loop at Major Midpoint Terminal"
            reason = f"Route {rt} projected at {p_dcr:.2f}x DCR with headway clustering."
            impact = f"Turns trailing bus early to clear passenger queue at bottleneck corridor."

        alerts.append({
            "alert_id": f"ALT-{dt}-{hr:02d}-{rt}",
            "route_id": rt,
            "date": dt,
            "time_window": f"{hr:02d}:00 - {hr+1:02d}:00",
            "priority": prio,
            "action_category": cat,
            "predicted_dcr": round(p_dcr, 2),
            "predicted_deficit_pax": defic,
            "predicted_pax": int(r.get('pred_pax', pax)),
            "active_buses": buses,
            "recommended_action": action_text,
            "operational_reason": reason,
            "expected_impact": impact,
            "verified_same_hour_overcrowded": bool(r['ground_truth_dcr'] > 1.0)
        })
    return alerts

@app.get("/api/rebalance-pairs")
def get_rebalance_pairs(limit: int = 100):
    """
    Returns single-allocation donor-receiver depot rebalancing pairs.
    Reads dynamically from outputs/backtest/tables/single_allocation_rebalance_pairs.csv.
    """
    pairs_path = ROOT / "outputs/backtest/tables/single_allocation_rebalance_pairs.csv"
    if not pairs_path.exists():
        return []
    
    df = pd.read_csv(pairs_path)
    records = []
    for idx, r in df.head(limit).iterrows():
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
            "net_deficit_pax_relieved": int(r['k_transfer'] * 70.0),
            "tag": "SIMULATED"
        })
    return records

@app.get("/api/routes")
def get_routes():
    """
    Returns live route status list with predicted vs actual passenger loads and DCR.
    """
    queue_path = ROOT / "outputs/backtest/tables/priority_queue_top50_daily.csv"
    if queue_path.exists():
        df = pd.read_csv(queue_path)
        routes = []
        for idx, r in df.iterrows():
            routes.append({
                "route_id": str(r['route_id']),
                "date": str(r['date']),
                "hour": int(r['hour']),
                "planned_buses": int(r.get('ex_ante_planned_buses', r.get('active_buses', 1))),
                "active_buses": int(r.get('active_buses', 1)),
                "predicted_pax": round(float(r.get('pred_pax', r.get('pax', 0))), 1),
                "actual_pax": int(r.get('pax', 0)),
                "predicted_dcr": round(float(r['pred_dcr']), 2),
                "actual_dcr": round(float(r['ground_truth_dcr']), 2),
                "predicted_overcrowding_probability": round(float(r['pred_proba']), 4),
                "recommended_action": str(r['action_category'])
            })
        return routes
    return []

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
