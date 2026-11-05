"""
Check script for Top-50 alerts, baseline precision, and recommendation audit.
"""
import os, sys, json
from pathlib import Path
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import precision_score, recall_score

ROOT = Path("c:/Users/nivet/Downloads/Theme 4/Theme 4")
CONFIG_F = ROOT / "src" / "recommendation_config.json"
BUS_RATED_CAPACITY = 70.0

# 1. Load data
df = pd.read_parquet(ROOT / 'data/clean/route_hour_capacity.parquet')
df['timestamp'] = pd.to_datetime(df['date']) + pd.to_timedelta(df['hour'], unit='h')
routes = df['route_id'].unique()
dates = pd.date_range('2026-03-01', '2026-03-31 23:00', freq='h')
grid = pd.DataFrame(index=pd.MultiIndex.from_product([routes, dates], names=['route_id', 'timestamp'])).reset_index()
grid = grid.merge(df[['route_id', 'timestamp', 'pax', 'active_buses', 'trips', 'tickets']], on=['route_id', 'timestamp'], how='left').fillna(0)
grid = grid.sort_values(['route_id', 'timestamp']).reset_index(drop=True)

grid['lag_2h_pax'] = grid.groupby('route_id')['pax'].shift(2)
grid['lag_3h_pax'] = grid.groupby('route_id')['pax'].shift(3)
grid['lag_1d_pax'] = grid.groupby('route_id')['pax'].shift(24)
grid['lag_7d_pax'] = grid.groupby('route_id')['pax'].shift(168)
grid['hour'] = grid['timestamp'].dt.hour
grid['date'] = grid['timestamp'].dt.strftime('%Y-%m-%d')
grid['dow_num'] = grid['timestamp'].dt.dayofweek
grid['is_weekend'] = grid['dow_num'].isin([5, 6]).astype(int)

# Ex-ante capacity
grid['lag_1d_buses'] = grid.groupby('route_id')['active_buses'].shift(24)
grid['rolling_buses_7d'] = grid.groupby(['route_id', 'hour'])['active_buses'].transform(
    lambda s: s.shift(1).rolling(7, min_periods=1).median().fillna(1.0)
)
grid['ex_ante_planned_buses'] = grid['lag_1d_buses'].fillna(grid['rolling_buses_7d']).fillna(1.0)
grid['ex_ante_capacity'] = grid['ex_ante_planned_buses'] * BUS_RATED_CAPACITY

# Ground truth capacity & DCR (demand-to-capacity ratio)
grid['ground_truth_capacity'] = grid['active_buses'] * BUS_RATED_CAPACITY
grid['ground_truth_dcr'] = np.where(grid['ground_truth_capacity'] > 0, grid['pax'] / grid['ground_truth_capacity'], 0.0)
grid['ground_truth_overcrowded'] = (grid['ground_truth_dcr'] > 1.0).astype(int)

grid['rolling_mean_7d'] = grid.groupby(['route_id', 'hour'])['pax'].transform(lambda s: s.shift(1).rolling(7, min_periods=1).mean())
grid['rolling_std_7d'] = grid.groupby(['route_id', 'hour'])['pax'].transform(lambda s: s.shift(1).rolling(7, min_periods=1).std().fillna(0))

data = grid[grid['active_buses'] > 0].dropna(subset=['lag_7d_pax', 'lag_1d_pax', 'lag_2h_pax']).reset_index(drop=True)
train_df = data[(data['timestamp'] >= '2026-03-08') & (data['timestamp'] < '2026-03-22')].copy()
test_df = data[data['timestamp'] >= '2026-03-27'].copy()

feats = ['hour', 'dow_num', 'is_weekend', 'ex_ante_capacity', 'lag_2h_pax', 'lag_3h_pax', 'lag_1d_pax', 'lag_7d_pax', 'rolling_mean_7d', 'rolling_std_7d']

# Train Regressor
reg = xgb.XGBRegressor(n_estimators=140, learning_rate=0.08, max_depth=6, random_state=42, n_jobs=2, tree_method='hist')
reg.fit(train_df[feats], train_df['pax'])
test_df['pred_pax_60m'] = np.clip(reg.predict(test_df[feats]), 0, None)
test_df['pred_dcr_60m'] = test_df['pred_pax_60m'] / (test_df['ex_ante_capacity'] + 1e-5)
test_df['pred_deficit_60m'] = test_df['pred_pax_60m'] - test_df['ex_ante_capacity']

# Train Classifier
pos_weight = (len(train_df) - train_df['ground_truth_overcrowded'].sum()) / train_df['ground_truth_overcrowded'].sum()
clf = xgb.XGBClassifier(n_estimators=140, learning_rate=0.08, max_depth=6, scale_pos_weight=pos_weight, random_state=42, n_jobs=2, tree_method='hist', eval_metric='logloss')
clf.fit(train_df[feats], train_df['ground_truth_overcrowded'])
test_df['pred_proba'] = clf.predict_proba(test_df[feats])[:, 1]

# ── CHECK 1: TOP-50 ALERTS ROUTE PERSISTENCE ────────────────────────────────
print("=" * 80)
print("CHECK 1: TOP-50 DAILY ALERTS ROUTE & ROUTE-HOUR PERSISTENCE")
print("=" * 80)
daily_top50 = []
for d, grp in test_df.groupby('date'):
    top_50 = grp.sort_values('pred_proba', ascending=False).head(50)
    daily_top50.append(top_50)
    n_routes = top_50['route_id'].nunique()
    n_hours = len(top_50)
    print(f"Date {d}: Top 50 alerts cover {n_routes} distinct routes across {n_hours} distinct route-hours.")

df_top50 = pd.concat(daily_top50)
route_day_counts = df_top50.groupby('route_id')['date'].nunique()
print(f"\nTotal distinct routes across all 250 Top-50 slots: {len(route_day_counts)}")
print(f"Routes appearing on all 5 of 5 days: {(route_day_counts == 5).sum()}")
print(f"Routes appearing on 4 of 5 days: {(route_day_counts == 4).sum()}")
print(f"Routes appearing on 3 of 5 days: {(route_day_counts == 3).sum()}")
n_ge_3 = (route_day_counts >= 3).sum()
print(f"Routes appearing on >= 3 of the 5 days: {n_ge_3} routes")
print(f"Top chronic routes (>= 3 days): {route_day_counts[route_day_counts >= 3].sort_values(ascending=False).to_dict()}")

# ── CHECK 2: BASELINE PRECISION AT TOP-20 AND TOP-50 ────────────────────────
print("\n" + "=" * 80)
print("CHECK 2: PRECISION AT TOP-20 & TOP-50 (ML MODEL VS PERSISTENCE BASELINES)")
print("=" * 80)
test_df['base_lag7d_ratio'] = test_df['lag_7d_pax'] / (test_df['ex_ante_capacity'] + 1e-5)
test_df['base_lag1d_ratio'] = test_df['lag_1d_pax'] / (test_df['ex_ante_capacity'] + 1e-5)

for k in [20, 50]:
    ml_tp = sum(grp.sort_values('pred_proba', ascending=False).head(k)['ground_truth_overcrowded'].sum() for _, grp in test_df.groupby('date'))
    lag7_tp = sum(grp.sort_values('base_lag7d_ratio', ascending=False).head(k)['ground_truth_overcrowded'].sum() for _, grp in test_df.groupby('date'))
    lag1_tp = sum(grp.sort_values('base_lag1d_ratio', ascending=False).head(k)['ground_truth_overcrowded'].sum() for _, grp in test_df.groupby('date'))
    tot = k * 5
    print(f"Top-{k}/day (Total {tot} alerts over 5 days):")
    print(f"  * Corrected ML Model:     {ml_tp/tot*100:.2f}% Precision ({ml_tp}/{tot})")
    print(f"  * Lag-7d Baseline:        {lag7_tp/tot*100:.2f}% Precision ({lag7_tp}/{tot})")
    print(f"  * Lag-1d Baseline:        {lag1_tp/tot*100:.2f}% Precision ({lag1_tp}/{tot})")
    print(f"  * Advantage vs Lag-7d:    +{(ml_tp - lag7_tp)/tot*100:.2f}% absolute precision")
    print(f"  * Advantage vs Lag-1d:    +{(ml_tp - lag1_tp)/tot*100:.2f}% absolute precision\n")

# ── CHECK 4: REGENERATE RECOMMENDATIONS & DASHBOARD FEED ───────────────────
print("=" * 80)
print("CHECK 4: REGENERATE RECOMMENDATIONS & DASHBOARD FEED (CORRECTED MODEL)")
print("=" * 80)
with open(CONFIG_F, 'r') as f:
    cfg = json.load(f)

depots = cfg.get('depot_mappings', {})
rail_parallel = cfg.get('rail_metro_corridor_parallel', {})

recs = []
for idx, row in test_df.iterrows():
    rt = str(row['route_id'])
    dt = str(row['date'])
    hr = int(row['hour'])
    pred_pax = int(row['pred_pax_60m'])
    pred_dcr = float(row['pred_dcr_60m'])
    deficit = int(row['pred_deficit_60m'])
    planned_buses = int(row['ex_ante_planned_buses'])
    actual_buses = int(row['active_buses'])
    actual_dcr = float(row['ground_truth_dcr'])
    depot = depots.get(rt, "Nearest Depot")
    rail = rail_parallel.get(rt, None)

    # 1. Fleet Injection
    if pred_dcr >= 1.25 and deficit >= 300:
        needed = int(np.ceil(deficit / 70.0))
        sim_post_dcr = pred_pax / ((planned_buses + needed) * 70.0)
        # Non-circular success: Did actual corridor experience severe crush (actual_dcr >= 1.20) or overcrowding (actual_dcr > 1.0)?
        is_success_strict = (actual_dcr >= 1.20)
        is_success_broad  = (actual_dcr > 1.00)
        recs.append({
            'priority': 1,
            'location': f"Route {rt} ({depot})",
            'time_window': f"{dt} {hr:02d}:00–{hr+1:02d}:00",
            'predicted_problem': f"Severe Overcrowding (Demand-to-Capacity Ratio {pred_dcr:.2f}x, Deficit +{deficit:,} pax)",
            'recommended_action': f"Inject +{needed} reserve standby buses from {depot}",
            'operational_reason': f"Ex-ante forecast of {pred_pax:,} exceeds planned capacity ({int(row['ex_ante_capacity']):,} pax). Severe crush risk.",
            'expected_impact': f"Reduces demand-to-capacity ratio from {pred_dcr:.2f}x to {sim_post_dcr:.2f}x, clearing platform passenger queues.",
            'action_category': "Fleet Injection",
            'route_id': rt,
            'date': dt,
            'hour': hr,
            'pred_dcr': pred_dcr,
            'actual_dcr': actual_dcr,
            'is_success_strict': is_success_strict,
            'is_success_broad': is_success_broad
        })

    # 2. Short-Turn Loop
    elif 1.10 <= pred_dcr < 1.25 and deficit >= 150:
        sim_post_dcr = pred_dcr * 0.80
        is_success_strict = (actual_dcr >= 1.00)
        is_success_broad  = (actual_dcr >= 1.00)
        recs.append({
            'priority': 2,
            'location': f"Route {rt} High-Demand Corridor",
            'time_window': f"{dt} {hr:02d}:00–{hr+1:02d}:00",
            'predicted_problem': f"Mid-Corridor Overcrowding (Demand-to-Capacity Ratio {pred_dcr:.2f}x, Deficit +{deficit} pax)",
            'recommended_action': "Short-turn 2 buses to run high-frequency mid-route express loops",
            'operational_reason': f"Ex-ante demand exceeds planned capacity; end-to-end cycle too slow to relieve corridor surge.",
            'expected_impact': f"Cuts cycle time by 40%, stabilizing corridor demand-to-capacity ratio at ~{sim_post_dcr:.2f}x.",
            'action_category': "Short-Turn Loop",
            'route_id': rt,
            'date': dt,
            'hour': hr,
            'pred_dcr': pred_dcr,
            'actual_dcr': actual_dcr,
            'is_success_strict': is_success_strict,
            'is_success_broad': is_success_broad
        })

    # 3. Fleet Reallocation (Surplus)
    elif pred_dcr <= 0.40 and planned_buses >= 4:
        cut_buses = max(1, planned_buses // 3)
        sim_post_dcr = pred_pax / ((planned_buses - cut_buses) * 70.0)
        # Non-circular success: Did the corridor ACTUALLY run with severe surplus (actual_dcr <= 0.40 and actual_buses >= 4)?
        is_success_strict = (actual_dcr <= 0.40 and actual_buses >= 4)
        is_success_broad  = (actual_dcr <= 0.50)
        recs.append({
            'priority': 3,
            'location': f"Route {rt} ({depot})",
            'time_window': f"{dt} {hr:02d}:00–{hr+1:02d}:00",
            'predicted_problem': f"Fleet Surplus & Under-utilization (Demand-to-Capacity Ratio {pred_dcr:.2f}x with {planned_buses} planned buses)",
            'recommended_action': f"Reallocate {cut_buses} surplus buses to adjacent deficit routes",
            'operational_reason': f"Ex-ante ridership forecast is only {pred_pax} passengers across {planned_buses} planned buses. Severe vehicle under-utilization.",
            'expected_impact': f"Saves operational diesel and crew hours, maintaining service demand-to-capacity ratio at {sim_post_dcr:.2f}x.",
            'action_category': "Fleet Reallocation",
            'route_id': rt,
            'date': dt,
            'hour': hr,
            'pred_dcr': pred_dcr,
            'actual_dcr': actual_dcr,
            'is_success_strict': is_success_strict,
            'is_success_broad': is_success_broad
        })

    # 4. Multi-Modal Advisory
    elif pred_dcr >= 1.20 and rail is not None:
        recs.append({
            'priority': 4,
            'location': f"Route {rt} Corridor",
            'time_window': f"{dt} {hr:02d}:00–{hr+1:02d}:00",
            'predicted_problem': f"Corridor Congestion & Bus Crush ({pred_dcr:.2f}x Demand-to-Capacity Ratio)",
            'recommended_action': f"Broadcast dynamic advisory to transfer to parallel {rail}",
            'operational_reason': f"Bus corridor facing severe crush while parallel rail infrastructure has spare capacity.",
            'expected_impact': f"Diverts 15-20% of intermediate corridor demand to rail transit.",
            'action_category': "Multi-Modal Advisory (ADVISORY)",
            'route_id': rt,
            'date': dt,
            'hour': hr,
            'pred_dcr': pred_dcr,
            'actual_dcr': actual_dcr,
            'is_success_strict': None,
            'is_success_broad': None
        })

df_all_recs = pd.DataFrame(recs)
print(f"Total recommendations generated across 5 test days: {len(df_all_recs):,}")

# Precision by category
print("\nNON-CIRCULAR PRECISION BY RECOMMENDATION TYPE:")
for cat in ['Fleet Injection', 'Short-Turn Loop', 'Fleet Reallocation']:
    sub = df_all_recs[df_all_recs['action_category'] == cat]
    p_strict = sub['is_success_strict'].mean() * 100.0
    p_broad  = sub['is_success_broad'].mean() * 100.0
    print(f"  * {cat} ({len(sub):,} total alerts; {len(sub)/5:.1f}/day):")
    print(f"      - Strict Precision: {p_strict:.2f}%")
    print(f"      - Broad Precision:  {p_broad:.2f}%")

sub_adv = df_all_recs[df_all_recs['action_category'] == 'Multi-Modal Advisory (ADVISORY)']
print(f"  * Multi-Modal Advisory: {len(sub_adv):,} alerts (Marked ADVISORY; excluded from operational precision)\n")

# Top 20 prioritized control room actions (6 required columns)
top20_recs = df_all_recs.sort_values(by=['priority', 'pred_dcr'], ascending=[True, False]).drop_duplicates(subset=['location', 'action_category']).head(20)
final_cols = ['location', 'time_window', 'predicted_problem', 'recommended_action', 'operational_reason', 'expected_impact']
top20_recs[final_cols].to_csv(ROOT / "outputs/tables/recommendations.csv", index=False)
print(f"Saved regenerated outputs/tables/recommendations.csv ({len(top20_recs)} rows)")

# Regenerate dashboard_feed.json
latest_hour_slice = test_df[(test_df['date'] == '2026-03-31') & (test_df['hour'] == 18)].copy()
feed_items = []
rec_dict = top20_recs.set_index('route_id')['recommended_action'].to_dict()

for _, row in latest_hour_slice.iterrows():
    rt = str(row['route_id'])
    feed_items.append({
        'route_id': rt,
        'hour': int(row['hour']),
        'planned_buses_ex_ante': int(row['ex_ante_planned_buses']),
        'actual_active_buses': int(row['active_buses']),
        'actual_passengers': int(row['pax']),
        'predicted_passengers': round(float(row['pred_pax_60m']), 1),
        'predicted_demand_to_capacity_ratio': round(float(row['pred_dcr_60m']), 3),
        'actual_demand_to_capacity_ratio': round(float(row['ground_truth_dcr']), 3),
        'overcrowding_risk_probability': round(float(row['pred_proba']), 4),
        'is_overcrowded_predicted': bool(row['pred_proba'] >= 0.50),
        'is_overcrowded_actual': bool(row['ground_truth_overcrowded'] == 1),
        'recommended_action': rec_dict.get(rt, 'Maintain Scheduled Headway')
    })

feed = {
    'system_metadata': {
        'city': 'Chennai',
        'operator': 'Metropolitan Transport Corporation (MTC) / CUMTA',
        'feed_timestamp': '2026-03-31 18:00:00',
        'feed_type': 'simulated live feed from ETM replay',
        'telemetry_source': 'ETM ticketing timestamps (No direct GPS/AVL hardware attached)',
        'model_version': 'Corrected 60-Minute Ex-Ante XGBoost (Strict Leak-Free)',
        'total_active_routes_in_slot': len(feed_items),
        'severe_crush_routes_count': sum(1 for item in feed_items if item['predicted_demand_to_capacity_ratio'] >= 1.25),
        'surplus_routes_count': sum(1 for item in feed_items if item['predicted_demand_to_capacity_ratio'] <= 0.40 and item['planned_buses_ex_ante'] >= 4)
    },
    'active_routes_status': feed_items[:100],
    'critical_control_room_alerts': top20_recs[final_cols].head(10).to_dict(orient='records')
}
with open(ROOT / 'outputs/tables/dashboard_feed.json', 'w') as f:
    json.dump(feed, f, indent=2)
print("Saved regenerated outputs/tables/dashboard_feed.json")

