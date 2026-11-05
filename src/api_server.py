"""
Marina Sentinel Backend REST API Server
Provides production and demo-ready endpoints for the Frontend.
Supports DEMO_MODE=1 to run strictly on precomputed outputs with zero raw data dependencies.

Endpoints:
- GET /
- GET /api/kpis
- GET /api/control-room-alerts?date=...&hour=...&limit=...
- GET /api/rebalance-pairs?depot=...&date=...&limit=...
- GET /api/routes?date=...&hour=...&depot=...&limit=...
- GET /api/dataset-manifest
- GET /api/hourly-summary
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
    title="Marina Sentinel Predictive Transit Dispatch API",
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

# In-memory caches for fast querying
_routes_df_cache = None
_dataset_manifest_cache = None
_hourly_summary_cache = None

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
        "service": "Marina Sentinel Predictive Transit Dispatch API (Replay-mode demo)",
        "demo_mode": DEMO_MODE,
        "telemetry_source": "67.8M ETM Telemetry Replay Feed (March 2026)",
        "endpoints": [
            "/api/kpis",
            "/api/control-room-alerts",
            "/api/rebalance-pairs",
            "/api/routes",
            "/api/dataset-manifest",
            "/api/hourly-summary",
            "/api/dashboard",
            "/openapi.json"
        ]
    }

@app.get("/api/kpis")
def get_kpis():
    """
    Returns verified headline model performance and operational backtest metrics.
    Provides dual-compatibility: top-level objects matching frontend TypeScript types
    and comprehensive nested audit sections.
    """
    return {
        # Frontend TypeScript KpisResponse schema compatibility
        "mae_reduction_pct": {
            "value": 21.7,
            "type": "MEASURED",
            "definition": "XGBoost 60-Min Ex-Ante Corridor MAE reduction vs strongest historical baseline (MAE 39.35 vs 50.24)."
        },
        "wape": {
            "value": 18.25,
            "type": "MEASURED",
            "definition": "Citywide Weighted Absolute Percentage Error across 56,781 holdout test slots."
        },
        "r2": {
            "value": 0.9571,
            "type": "MEASURED",
            "definition": "Coefficient of determination (R²) for 60-min ex-ante passenger arrivals."
        },
        "roc_auc": {
            "value": 0.9178,
            "type": "MEASURED",
            "definition": "Receiver Operating Characteristic AUC for DCR > 1.0 overcrowding early warning."
        },
        "pr_auc": {
            "value": 0.7816,
            "type": "MEASURED",
            "definition": "Precision-Recall AUC across all 56,781 test route-hours."
        },
        "wide_net": {
            "recall": 88.60,
            "precision": 59.20,
            "type": "MEASURED",
            "definition": "Stage 1 candidate screening (DCR >= 1.0, 60-min lead time) across entire network."
        },
        "priority_queue": {
            "precision": 97.20,
            "hits": 243,
            "total": 250,
            "cap_per_day": 50,
            "type": "MEASURED",
            "definition": "Stage 2 operator dispatch queue precision (capped at top 50 high-confidence cards/day)."
        },
        "anomalies_flagged": {
            "value": 881,
            "type": "MEASURED",
            "definition": "Telemetry anomalies flagged and isolated by Isolation Forest prior to dispatch scoring."
        },
        "rebalancing": {
            "operations": 204,
            "buses_moved": 748,
            "share_reaching_dcr_1": 47.06,
            "receiver_mean_dcr_before": 1.45,
            "receiver_mean_dcr_after": 1.12,
            "type": "SIMULATED",
            "definition": "Strict single-allocation same-depot rebalancing with >= 70 pax minimum benefit rule (donor cap DCR <= 0.80x)."
        },
        "recurrence_baseline": {
            "route_hour_precision": 99.20,
            "daily_route_precision": 53.20,
            "type": "MEASURED",
            "definition": "Top 50/day baseline by historical recurrence."
        },

        # Backtest audit report structure
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
            "route_hour_recurrence_baseline_precision_percent": 99.20,
            "route_hour_recurrence_baseline_description": "Top 50/day by historical route-hour recurrence >= 70%",
            "historical_daily_recurrence_baseline_precision_percent": 53.20,
            "excess_riders_addressed_pax": 143589,
            "excess_riders_share_percent": 11.45,
            "share_of_queue_alerts_on_non_chronic_routes": 1.20,
            "tag": "MEASURED"
        },
        "depot_rebalancing_simulation": {
            "constraint": "Strict Single-Allocation Same-Depot Gate Matching with Deficit >= 70 Pax Rule",
            "unique_operations_count": 204,
            "total_fleet_transferred": 748,
            "total_capacity_moved_pax": 52360,
            "total_predicted_passenger_reduction": 49722,
            "total_observed_passenger_reduction": 49137,
            "receiver_pre_dcr_mean": 1.45,
            "receiver_post_dcr_mean": 1.12,
            "donor_pre_dcr_mean": 0.35,
            "donor_post_dcr_mean": 0.49,
            "donor_post_dcr_p95": 0.73,
            "donor_post_dcr_max": 0.80,
            "donor_safety_cap": "DCR <= 0.80x by design (Retains >= 60% fleet)",
            "overcrowded_receivers_normalized_percent": 47.06,
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
    Supports date and hour filtering, compatible with frontend ControlRoomAlert interface.
    """
    queue_path = ROOT / "outputs/backtest/tables/priority_queue_top50_daily.csv"
    if not queue_path.exists():
        return []
    
    df = pd.read_csv(queue_path)
    if isinstance(date, str) and date in df['date'].astype(str).values:
        df = df[df['date'].astype(str) == str(date)]
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
        
        action_type = "fleet_injection" if cat == 'Fleet Injection' else "short_turn"
        if action_type == 'fleet_injection':
            needed_buses = max(1, int(math.ceil(defic / 70.0)))
            action_text = f"Priority 1: Fleet Injection (+{needed_buses} Reserve Buses)"
            reason = f"Route {rt} projected at {p_dcr:.2f}x Demand-to-Capacity Ratio (+{defic} passenger deficit)."
            impact = f"Decompresses corridor towards 1.0x capacity limit before departure."
        else:
            needed_buses = 0
            action_text = f"Priority 2: Short-Turn Loop at Major Midpoint Terminal"
            reason = f"Route {rt} projected at {p_dcr:.2f}x DCR with headway clustering."
            impact = f"Turns trailing bus early to clear passenger queue at bottleneck corridor."

        alert_id = f"ALT-{dt}-{hr:02d}-{rt}"
        alerts.append({
            "id": alert_id,
            "alert_id": alert_id,
            "route": rt,
            "route_id": rt,
            "depot": depot_name,
            "date": dt,
            "hour": hr,
            "time_window": f"{hr:02d}:00 - {hr+1:02d}:00",
            "priority": prio,
            "action_type": action_type,
            "action_category": cat,
            "planned_buses": planned_buses,
            "planned_capacity_seats": planned_cap,
            "predicted_pax": pred_pax,
            "predicted_dcr": round(p_dcr, 2),
            "predicted_deficit_pax": defic,
            "expected_deficit_pax": defic,
            "reserve_buses_needed": needed_buses,
            "recommended_action": action_text,
            "reason": reason,
            "operational_reason": reason,
            "expected_impact": impact,
            "type": "MEASURED",
            "observed_active_buses_ex_post": active_buses_obs,
            "verified_same_hour_overcrowded": bool(r['ground_truth_dcr'] > 1.0)
        })
    return alerts

@app.get("/api/rebalance-pairs")
def get_rebalance_pairs(
    depot: Optional[str] = Query(None, description="Filter by depot name, e.g. Tambaram"),
    date: Optional[str] = Query(None, description="Filter by date, e.g. 2026-03-30"),
    limit: int = Query(250, description="Max pairs to return")
):
    """
    Returns single-allocation donor-receiver depot rebalancing pairs.
    Supports depot and date filtering, compatible with frontend RebalancePair interface.
    """
    pairs_path = ROOT / "outputs/backtest/tables/single_allocation_rebalance_pairs.csv"
    if not pairs_path.exists():
        return []
    
    df = pd.read_csv(pairs_path)
    if isinstance(depot, str) and depot.lower() != 'all':
        df = df[df['depot'].str.contains(depot, case=False, na=False)]
    if isinstance(date, str) and date in df['date'].astype(str).values:
        df = df[df['date'].astype(str) == str(date)]
    actual_limit = limit.default if hasattr(limit, "default") else int(limit)
        
    records = []
    for idx, r in df.head(actual_limit).iterrows():
        rec_rt = str(r['receiver_route']).replace("Route ", "").strip()
        don_rt = str(r['donor_route']).replace("Route ", "").strip()
        k_val = int(r['k_transfer'])
        b_rec = int(r['buses_rec'])
        b_don = int(r['buses_don'])
        p_rec = int(r['pax_rec'])
        p_don = int(r['pax_don'])
        pre_dcr_rec = round(float(r['pre_dcr_rec']), 2)
        post_dcr_rec = round(float(r['post_dcr_rec']), 2)
        pre_dcr_don = round(float(r['pre_dcr_don']), 2)
        post_dcr_don = round(float(r['post_dcr_don']), 2)
        op_id = f"REBAL-{r['date']}-{int(r['hour']):02d}-{r['depot'][:3].upper()}-{idx+1}"

        records.append({
            "id": op_id,
            "operation_id": op_id,
            "depot": r['depot'],
            "date": str(r['date']),
            "hour": int(r['hour']),
            "time_window": f"{int(r['hour']):02d}:00 - {int(r['hour'])+1:02d}:00",
            "receiver_route": rec_rt,
            "donor_route": don_rt,
            "k": k_val,
            "buses_transferred_k": k_val,
            "receiver_buses": b_rec,
            "donor_buses": b_don,
            "receiver_passengers": p_rec,
            "donor_passengers": p_don,
            "receiver_dcr_before": pre_dcr_rec,
            "receiver_pre_dcr": pre_dcr_rec,
            "receiver_dcr_after": post_dcr_rec,
            "receiver_post_dcr": post_dcr_rec,
            "donor_dcr_before": pre_dcr_don,
            "donor_pre_dcr": pre_dcr_don,
            "donor_dcr_after": post_dcr_don,
            "donor_post_dcr": post_dcr_don,
            "donor_safety_verified": bool(r['post_dcr_don'] <= 0.80),
            "receiver_reaches_capacity_target": bool(r['reaches_1_0'] == 1),
            "capacity_moved_pax": int(r['capacity_moved_pax']),
            "predicted_passenger_reduction": int(r.get('predicted_passenger_reduction', 0)),
            "observed_passenger_reduction": int(r.get('observed_passenger_reduction', 0)),
            "type": "SIMULATED",
            "tag": "SIMULATED"
        })
    return records

@app.get("/api/routes")
def get_routes(
    date: Optional[str] = Query(None, description="Filter by date, e.g. 2026-03-27"),
    hour: Optional[int] = Query(None, description="Filter by hour, e.g. 8"),
    depot: Optional[str] = Query(None, description="Filter by depot name, e.g. Adyar"),
    limit: int = Query(250, description="Max records to return")
):
    """
    Returns route predictions and loads across route-hours.
    Supports filtering by date, hour, and depot; compatible with frontend RouteItem interface.
    """
    df = get_cached_routes_df()
    if df.empty:
        return []
    
    if isinstance(date, str) and date in df['date'].astype(str).values:
        df = df[df['date'].astype(str) == date]
    if isinstance(hour, (int, str)) and not hasattr(hour, "default"):
        df = df[df['hour'] == int(hour)]
    if isinstance(depot, str) and depot.lower() != 'all':
        df = df[df['depot'].str.contains(depot, case=False, na=False)]
    actual_limit = limit.default if hasattr(limit, "default") else int(limit)
        
    records = []
    for idx, r in df.head(actual_limit).iterrows():
        rt = str(r['route_id'])
        pred_pax = round(float(r.get('pred_pax_60m', r.get('pred_pax', 0))), 1)
        act_pax = int(r.get('pax', 0))
        pred_dcr = round(float(r.get('pred_dcr_60m', r.get('pred_dcr', 0))), 2)
        act_dcr = round(float(r.get('ground_truth_dcr', 0)), 2)
        pred_prob = round(float(r.get('pred_proba_60m', r.get('pred_proba', 0))), 4)
        planned_b = int(r.get('ex_ante_planned_buses', r.get('active_buses', 1)))
        active_b = int(r.get('active_buses', 1))
        is_over_act = bool(r.get('ground_truth_overcrowded', 0) == 1 or act_dcr > 1.0)
        is_over_pred = bool(pred_dcr > 1.0)

        action_text = "Inject Reserve Fleet" if pred_dcr >= 1.25 else ("Short-Turn Loop" if pred_dcr > 1.0 else "Maintain Normal Headway")

        records.append({
            "route_id": rt,
            "depot": str(r.get('depot', 'Operating Depot')),
            "date": str(r['date']),
            "hour": int(r['hour']),
            "planned_buses": planned_b,
            "planned_buses_ex_ante": planned_b,
            "active_buses": active_b,
            "actual_active_buses": active_b,
            "predicted_pax": pred_pax,
            "predicted_passengers": pred_pax,
            "actual_pax": act_pax,
            "actual_passengers": act_pax,
            "predicted_dcr": pred_dcr,
            "predicted_demand_to_capacity_ratio": pred_dcr,
            "actual_dcr": act_dcr,
            "actual_demand_to_capacity_ratio": act_dcr,
            "predicted_overcrowding_probability": pred_prob,
            "overcrowding_risk_probability": pred_prob,
            "is_overcrowded": is_over_act,
            "is_overcrowded_predicted": is_over_pred,
            "is_overcrowded_actual": is_over_act,
            "recommended_action": action_text,
            "type": "MEASURED"
        })
    return records

@app.get("/api/dataset-manifest")
def get_dataset_manifest():
    """Serves metadata and telemetry sample details for the CUMTA Theme 4 dataset."""
    global _dataset_manifest_cache
    if _dataset_manifest_cache is None:
        manifest_path = ROOT / "frontend/src/mocks/dataset-manifest.json"
        if manifest_path.exists():
            with open(manifest_path, "r", encoding="utf-8") as f:
                _dataset_manifest_cache = json.load(f)
        else:
            _dataset_manifest_cache = {
                "generated_at": "2026-03-31T00:00:00Z",
                "total_tickets_sampled": 67800000,
                "total_routes": 705,
                "total_depots": 29,
                "depots": []
            }
    return _dataset_manifest_cache

@app.get("/api/hourly-summary")
def get_hourly_summary():
    """Serves network-wide hourly boarding and overcrowding aggregates."""
    global _hourly_summary_cache
    if _hourly_summary_cache is None:
        summary_path = ROOT / "frontend/src/mocks/hourly-summary.json"
        if summary_path.exists():
            with open(summary_path, "r", encoding="utf-8") as f:
                _hourly_summary_cache = json.load(f)
        else:
            _hourly_summary_cache = {}
    return _hourly_summary_cache

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
            "model_version": "Marina Sentinel Dual XGBoost (60-Min Strict Ex-Ante)",
            "status": "Operational",
            "demo_mode": DEMO_MODE
        },
        "kpis": kpis,
        "critical_alerts_preview": alerts,
        "depot_rebalance_preview": pairs
    }

if __name__ == "__main__":
    print(f"Starting Marina Sentinel REST API Server (DEMO_MODE={DEMO_MODE}) on http://localhost:8000 ...")
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=False, app_dir=str(ROOT / "src"))
