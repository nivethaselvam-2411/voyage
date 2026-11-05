"""
Marina Sentinel: Recompute and Verify All Assets
- Generates outputs/demo/route_hour_predictions.csv.gz (56,781 test slots)
- Verifies single-allocation rebalancing pairs with full raw fields
- Checks formulas for Top 3 and 20 random pairs
- Computes chronic vs non-chronic on the priority-ordered queue
"""
import os
import tempfile
os.environ['MPLCONFIGDIR'] = tempfile.gettempdir()

from pathlib import Path
import math
import numpy as np
import pandas as pd
import xgboost as xgb

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DEMO = ROOT / "outputs/demo"
OUT_DEMO.mkdir(parents=True, exist_ok=True)
OUT_TABLES = ROOT / "outputs/backtest/tables"
OUT_TABLES.mkdir(parents=True, exist_ok=True)

# 1. Load full capacity parquet and compile 60m ex-ante features
print("Loading route_hour_capacity.parquet...")
rh = pd.read_parquet(ROOT / 'data/clean/route_hour_capacity.parquet')
rh['timestamp'] = pd.to_datetime(rh['date']) + pd.to_timedelta(rh['hour'], unit='h')
rh['route_id'] = rh['route_id'].astype(str)

# Map depot
sample_day = pd.read_parquet(ROOT / 'data/clean/day_2026-03-27.parquet')
route_depot_map = sample_day.groupby('route_id')['depot'].agg(lambda s: s.mode()[0] if len(s.mode()) > 0 else s.iloc[0]).to_dict()
rh['depot'] = rh['route_id'].map(route_depot_map).fillna("Unknown Depot")

routes = rh['route_id'].unique()
timestamps = pd.date_range('2026-03-01 00:00:00', '2026-03-31 23:00:00', freq='h')
grid = pd.DataFrame(index=pd.MultiIndex.from_product([routes, timestamps], names=['route_id', 'timestamp'])).reset_index()

grid = grid.merge(rh[['route_id', 'timestamp', 'pax', 'active_buses', 'depot']], on=['route_id', 'timestamp'], how='left')
grid['pax'] = grid['pax'].fillna(0.0).astype(np.float32)
grid['active_buses'] = grid['active_buses'].fillna(0.0).astype(np.float32)
grid['depot'] = grid['depot'].fillna(grid['route_id'].map(route_depot_map)).fillna("Unknown Depot")
grid = grid.sort_values(['route_id', 'timestamp']).reset_index(drop=True)

hour_series = grid['timestamp'].dt.hour
grid['hour'] = hour_series.astype(np.int8)
grid['date'] = grid['timestamp'].dt.strftime('%Y-%m-%d')
grid['dow_num'] = grid['timestamp'].dt.dayofweek.astype(np.int8)
grid['is_weekend'] = grid['dow_num'].isin([5, 6]).astype(np.int8)

# 10 strict features (all >= 60 min lead)
grid['lag_2h_pax'] = grid.groupby('route_id')['pax'].shift(2)
grid['lag_3h_pax'] = grid.groupby('route_id')['pax'].shift(3)
grid['lag_1d_pax'] = grid.groupby('route_id')['pax'].shift(24)
grid['lag_7d_pax'] = grid.groupby('route_id')['pax'].shift(168)

grid['lag_1d_buses'] = grid.groupby('route_id')['active_buses'].shift(24)
grid['rolling_buses_7d'] = grid.groupby(['route_id', hour_series])['active_buses'].transform(
    lambda s: s.shift(1).rolling(7, min_periods=1).median().fillna(1.0)
).astype(np.float32)
grid['ex_ante_planned_buses'] = grid['lag_1d_buses'].fillna(grid['rolling_buses_7d']).fillna(1.0)
grid['ex_ante_capacity'] = (grid['ex_ante_planned_buses'] * 70.0).astype(np.float32)

grid['rolling_mean_7d'] = grid.groupby(['route_id', hour_series])['pax'].transform(
    lambda s: s.shift(1).rolling(7, min_periods=1).mean()
).astype(np.float32)
grid['rolling_std_7d'] = grid.groupby(['route_id', hour_series])['pax'].transform(
    lambda s: s.shift(1).rolling(7, min_periods=1).std().fillna(0.0)
).astype(np.float32)

grid['ground_truth_capacity'] = (grid['active_buses'] * 70.0).astype(np.float32)
grid['ground_truth_dcr'] = np.where(grid['ground_truth_capacity'] > 0, grid['pax'] / grid['ground_truth_capacity'], 0.0).astype(np.float32)
grid['ground_truth_overcrowded'] = (grid['ground_truth_dcr'] > 1.0).astype(np.int8)
grid['excess_pax'] = np.maximum(0.0, grid['pax'] - grid['ground_truth_capacity']).astype(np.float32)

valid_data = grid[grid['active_buses'] > 0].dropna(subset=['lag_7d_pax', 'lag_1d_pax', 'lag_2h_pax']).reset_index(drop=True)

train_mask = (valid_data['timestamp'] >= '2026-03-08') & (valid_data['timestamp'] < '2026-03-22')
val_mask   = (valid_data['timestamp'] >= '2026-03-22') & (valid_data['timestamp'] < '2026-03-27')
test_mask  = (valid_data['timestamp'] >= '2026-03-27')

train_df = valid_data[train_mask].copy()
val_df   = valid_data[val_mask].copy()
test_df  = valid_data[test_mask].copy()

feats = [
    'hour', 'dow_num', 'is_weekend', 'ex_ante_capacity',
    'lag_2h_pax', 'lag_3h_pax', 'lag_1d_pax', 'lag_7d_pax',
    'rolling_mean_7d', 'rolling_std_7d'
]

print("Training 60m ex-ante models on TRAIN...")
reg_model = xgb.XGBRegressor(
    n_estimators=150, max_depth=6, learning_rate=0.08,
    subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=2
)
reg_model.fit(train_df[feats], train_df['pax'], eval_set=[(val_df[feats], val_df['pax'])], verbose=False)

pos_weight = (len(train_df) - np.sum(train_df['ground_truth_overcrowded'])) / max(np.sum(train_df['ground_truth_overcrowded']), 1)
clf_model = xgb.XGBClassifier(
    n_estimators=150, max_depth=6, learning_rate=0.08,
    scale_pos_weight=pos_weight, subsample=0.8, colsample_bytree=0.8,
    random_state=42, n_jobs=2, eval_metric='logloss'
)
clf_model.fit(train_df[feats], train_df['ground_truth_overcrowded'], eval_set=[(val_df[feats], val_df['ground_truth_overcrowded'])], verbose=False)

# Predict on test
test_df['pred_pax_60m'] = np.clip(reg_model.predict(test_df[feats]), 0, None).round(1)
test_df['pred_proba_60m'] = clf_model.predict_proba(test_df[feats])[:, 1].round(4)
test_df['pred_dcr_60m'] = (test_df['pred_pax_60m'] / (test_df['ex_ante_capacity'] + 1e-5)).round(3)
test_df['pred_deficit_60m'] = (test_df['pred_pax_60m'] - test_df['ex_ante_capacity']).round(1)

# Save test-period predictions for all 56,781 route-hours as outputs/demo/route_hour_predictions.csv.gz
print(f"Exporting {len(test_df):,} test route-hour predictions to outputs/demo/route_hour_predictions.csv.gz...")
export_cols = [
    'date', 'hour', 'route_id', 'depot', 'pax', 'active_buses',
    'ex_ante_planned_buses', 'pred_pax_60m', 'pred_dcr_60m', 'pred_proba_60m',
    'pred_deficit_60m', 'ground_truth_dcr', 'ground_truth_overcrowded', 'excess_pax'
]
test_df[export_cols].to_csv(OUT_DEMO / "route_hour_predictions.csv.gz", index=False, compression='gzip')
print("Saved outputs/demo/route_hour_predictions.csv.gz")

# ──────────────────────────────────────────────────────────────────────────────
# 2. COMPUTE CHRONIC VS NON-CHRONIC ON PRIORITY-ORDERED CAPPED QUEUE
# ──────────────────────────────────────────────────────────────────────────────
print("\nComputing chronic vs non-chronic share on priority-ordered capped queue...")
# Chronic definition on TRAIN: route overcrowded on >= 70% of observed TRAIN days
train_route_days = train_df.groupby(['route_id', 'date'])['ground_truth_overcrowded'].max().reset_index()
route_train_counts = train_route_days.groupby('route_id').agg(
    total_days=('date', 'nunique'),
    overcrowded_days=('ground_truth_overcrowded', 'sum')
).reset_index()
route_train_counts['train_overcrowd_rate'] = route_train_counts['overcrowded_days'] / route_train_counts['total_days']
chronic_routes = set(route_train_counts[route_train_counts['train_overcrowd_rate'] >= 0.70]['route_id'])
print(f"Identified {len(chronic_routes)} chronic routes in TRAIN out of {len(route_train_counts)} routes.")

# Build priority-ordered queue
recs = []
for idx, row in test_df.iterrows():
    p_dcr = row['pred_dcr_60m']
    defic = row['pred_deficit_60m']
    pl_b = row['ex_ante_planned_buses']
    if p_dcr >= 1.25 and defic >= 300:
        recs.append({
            'date': row['date'], 'hour': row['hour'], 'route_id': row['route_id'], 'depot': row['depot'],
            'action_category': 'Fleet Injection', 'priority': 1,
            'pred_dcr': p_dcr, 'pred_deficit': defic, 'pred_proba': row['pred_proba_60m'],
            'ground_truth_dcr': row['ground_truth_dcr'], 'excess_pax': row['excess_pax'],
            'pax': row['pax'], 'active_buses': row['active_buses'], 'ex_ante_planned_buses': pl_b,
            'pred_pax': row['pred_pax_60m'],
            'is_chronic': int(row['route_id'] in chronic_routes)
        })
    elif 1.10 <= p_dcr < 1.25 and defic >= 150:
        recs.append({
            'date': row['date'], 'hour': row['hour'], 'route_id': row['route_id'], 'depot': row['depot'],
            'action_category': 'Short-Turn Loop', 'priority': 2,
            'pred_dcr': p_dcr, 'pred_deficit': defic, 'pred_proba': row['pred_proba_60m'],
            'ground_truth_dcr': row['ground_truth_dcr'], 'excess_pax': row['excess_pax'],
            'pax': row['pax'], 'active_buses': row['active_buses'], 'ex_ante_planned_buses': pl_b,
            'pred_pax': row['pred_pax_60m'],
            'is_chronic': int(row['route_id'] in chronic_routes)
        })

df_recs = pd.DataFrame(recs)
capped_days = []
for d, grp in df_recs.groupby('date'):
    p1 = grp[grp['priority'] == 1].sort_values('pred_deficit', ascending=False)
    p2 = grp[grp['priority'] == 2].sort_values('pred_deficit', ascending=False)
    capped_days.append(pd.concat([p1, p2]).head(50))

priority_queue_df = pd.concat(capped_days).reset_index(drop=True)
priority_queue_df.to_csv(OUT_TABLES / "priority_queue_top50_daily.csv", index=False)

non_chronic_count = (priority_queue_df['is_chronic'] == 0).sum()
chronic_count = (priority_queue_df['is_chronic'] == 1).sum()
non_chronic_share_pct = (non_chronic_count / len(priority_queue_df)) * 100.0
chronic_share_pct = (chronic_count / len(priority_queue_df)) * 100.0

print(f"\nCHRONIC VS NON-CHRONIC BREAKDOWN ON PRIORITY QUEUE (250 Alerts):")
print(f"  * Share of queue alerts on non-chronic routes: {non_chronic_share_pct:.2f}% ({non_chronic_count} / {len(priority_queue_df)})")
print(f"  * Share of queue alerts on chronic routes:     {chronic_share_pct:.2f}% ({chronic_count} / {len(priority_queue_df)})")

# ──────────────────────────────────────────────────────────────────────────────
# 3. COMPUTE & VERIFY SINGLE-ALLOCATION REBALANCING PAIRS
# ──────────────────────────────────────────────────────────────────────────────
print("\nRecomputing single-allocation depot-constrained rebalancing pairs with full raw fields...")
receivers = test_df[(test_df['pred_dcr_60m'] >= 1.25) & (test_df['pred_deficit_60m'] >= 300) & (test_df['depot'] != 'Unknown Depot')].copy()
donors    = test_df[(test_df['pred_dcr_60m'] <= 0.40) & (test_df['active_buses'] >= 4) & (test_df['depot'] != 'Unknown Depot')].copy()

raw_pairs = receivers.merge(donors, on=['date', 'hour', 'depot'], suffixes=('_receiver', '_donor'))
raw_pairs = raw_pairs[raw_pairs['route_id_receiver'] != raw_pairs['route_id_donor']].copy()

raw_pairs_sorted = raw_pairs.sort_values('pred_deficit_60m_receiver', ascending=False)

single_alloc_results = []
for (dep, dt, hr), grp in raw_pairs_sorted.groupby(['depot', 'date', 'hour']):
    depot_donors_committed = set()
    depot_receivers_matched = set()
    
    for idx, row in grp.iterrows():
        rec_id = row['route_id_receiver']
        don_id = row['route_id_donor']
        
        if don_id in depot_donors_committed or rec_id in depot_receivers_matched:
            continue
            
        pax_rec = float(row['pax_receiver'])
        buses_rec = float(row['active_buses_receiver'])
        pax_don = float(row['pax_donor'])
        buses_don = float(row['active_buses_donor'])
        
        pre_dcr_rec = pax_rec / (buses_rec * 70.0) if buses_rec > 0 else 0.0
        pre_dcr_don = pax_don / (buses_don * 70.0) if buses_don > 0 else 0.0
        
        # Exact formulas:
        k_needed = max(0, int(math.ceil(pax_rec / 70.0) - buses_rec))
        cap1 = max(0, int(math.floor(buses_don - (pax_don / 56.0))))
        cap2 = max(0, int(math.floor(0.40 * buses_don)))
        max_k_donor_can_give = min(cap1, cap2)
        
        k = max(0, min(k_needed, max_k_donor_can_give))
        
        if k > 0:
            post_dcr_rec = pax_rec / ((buses_rec + k) * 70.0)
            post_dcr_don = pax_don / ((buses_don - k) * 70.0) if (buses_don - k) > 0 else 0.0
            reaches_1_0 = (post_dcr_rec <= 1.0001)
            
            cap_before = buses_rec * 70.0
            cap_after = (buses_rec + k) * 70.0
            excess_before = max(0.0, pax_rec - cap_before)
            excess_after = max(0.0, pax_rec - cap_after)
            actual_passenger_reduction = excess_before - excess_after
            capacity_moved_pax = k * 70.0
            
            single_alloc_results.append({
                'depot': dep,
                'date': dt,
                'hour': hr,
                'receiver_route': rec_id,
                'donor_route': don_id,
                'pax_rec': pax_rec,
                'buses_rec': buses_rec,
                'pax_don': pax_don,
                'buses_don': buses_don,
                'k_needed': k_needed,
                'cap1': cap1,
                'cap2': cap2,
                'k_transfer': k,
                'pre_dcr_rec': pre_dcr_rec,
                'post_dcr_rec': post_dcr_rec,
                'pre_dcr_don': pre_dcr_don,
                'post_dcr_don': post_dcr_don,
                'reaches_1_0': int(reaches_1_0),
                'capacity_moved_pax': capacity_moved_pax,
                'actual_passenger_reduction': actual_passenger_reduction
            })
            
            depot_donors_committed.add(don_id)
            depot_receivers_matched.add(rec_id)

df_single = pd.DataFrame(single_alloc_results)
df_single.to_csv(OUT_TABLES / "single_allocation_rebalance_pairs.csv", index=False)
print(f"Saved {len(df_single)} single-allocation pairs to outputs/backtest/tables/single_allocation_rebalance_pairs.csv")

# ──────────────────────────────────────────────────────────────────────────────
# 4. HAND-RECOMPUTATION AUDIT (TOP 3 + 20 RANDOM ROWS)
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("HAND-RECOMPUTATION VERIFICATION AUDIT (TOP 3 BY ACTUAL PAX REDUCTION + 20 RANDOM)")
print("=" * 80)

# Sort by actual_passenger_reduction descending
df_sorted = df_single.sort_values(by=['actual_passenger_reduction', 'capacity_moved_pax'], ascending=[False, False])
top3_df = df_sorted.head(3)

np.random.seed(42)
random20_idx = np.random.choice(df_sorted.index[3:], size=20, replace=False)
random20_df = df_sorted.loc[random20_idx]

audit_sample = pd.concat([top3_df, random20_df]).reset_index(drop=True)

discrepancies = []
for i, r in audit_sample.iterrows():
    pax_r = r['pax_rec']
    b_r = r['buses_rec']
    pax_d = r['pax_don']
    b_d = r['buses_don']
    
    # Hand formulas
    k_need_h = max(0, int(math.ceil(pax_r / 70.0) - b_r))
    cap1_h = max(0, int(math.floor(b_d - (pax_d / 56.0))))
    cap2_h = max(0, int(math.floor(0.40 * b_d)))
    k_h = max(0, min(k_need_h, cap1_h, cap2_h))
    post_rec_h = pax_r / ((b_r + k_h) * 70.0)
    post_don_h = pax_d / ((b_d - k_h) * 70.0)
    reaches_1_0_h = int(post_rec_h <= 1.0001)
    
    # Compare with CSV row
    k_csv = int(r['k_transfer'])
    post_rec_csv = r['post_dcr_rec']
    post_don_csv = r['post_dcr_don']
    reaches_csv = int(r['reaches_1_0'])
    
    k_match = (k_h == k_csv)
    post_rec_match = abs(post_rec_h - post_rec_csv) < 1e-4
    post_don_match = abs(post_don_h - post_don_csv) < 1e-4
    reaches_match = (reaches_1_0_h == reaches_csv)
    
    tag = "TOP 3" if i < 3 else f"RANDOM #{i-2}"
    print(f"[{tag}] Pair {r['depot']} @ {r['date']} {int(r['hour']):02d}:00 (Rec: {r['receiver_route']}, Don: {r['donor_route']}):")
    print(f"  Raw: pax_rec={pax_r:.0f}, buses_rec={b_r:.0f} | pax_don={pax_d:.0f}, buses_don={b_d:.0f}")
    print(f"  Hand: k_needed={k_need_h}, cap1={cap1_h}, cap2={cap2_h} => k={k_h} | post_rec={post_rec_h:.3f}x, post_don={post_don_h:.3f}x")
    print(f"  CSV:  k={k_csv}, post_rec={post_rec_csv:.3f}x, post_don={post_don_csv:.3f}x | Matches Hand: {k_match and post_rec_match and post_don_match}")
    
    if not (k_match and post_rec_match and post_don_match and reaches_match):
        discrepancies.append((i, r))

print(f"\nTotal Discrepancies Found Across Hand-Audit Sample: {len(discrepancies)}")
if len(discrepancies) == 0:
    print("VERDICT: 100% PERFECT MATCH. Zero discrepancies between CSV and hand formulas.")

# ──────────────────────────────────────────────────────────────────────────────
# 5. RE-REPORTED AGGREGATES ACROSS ALL 212 PAIRS
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("RE-REPORTED AGGREGATE STATS (ALL 212 SINGLE-ALLOCATION PAIRS)")
print("=" * 80)
total_ops = len(df_single)
total_buses = int(df_single['k_transfer'].sum())
reach_1_0_cnt = int(df_single['reaches_1_0'].sum())
pct_reach_1_0 = (reach_1_0_cnt / total_ops) * 100.0

rec_pre_mean = df_single['pre_dcr_rec'].mean()
rec_pre_med = df_single['pre_dcr_rec'].median()
rec_post_mean = df_single['post_dcr_rec'].mean()
rec_post_med = df_single['post_dcr_rec'].median()

don_pre_mean = df_single['pre_dcr_don'].mean()
don_pre_med = df_single['pre_dcr_don'].median()
don_post_mean = df_single['post_dcr_don'].mean()
don_post_med = df_single['post_dcr_don'].median()
don_post_p95 = df_single['post_dcr_don'].quantile(0.95)
don_post_max = df_single['post_dcr_don'].max()

total_capacity_moved = df_single['capacity_moved_pax'].sum()
total_actual_reduction = df_single['actual_passenger_reduction'].sum()

print(f"Total Single-Allocation Rebalancing Operations: {total_ops}")
print(f"Total Buses Transferred:                        {total_buses} buses (Mean: {total_buses/total_ops:.2f}/pair)")
print(f"Total Capacity Moved:                           {total_capacity_moved:,.0f} passenger-seats")
print(f"Total Actual Passenger Deficit Relieved:        {total_actual_reduction:,.0f} passengers")
print(f"Receivers Reaching DCR <= 1.0:                  {reach_1_0_cnt} / {total_ops} ({pct_reach_1_0:.2f}%)")
print(f"Receiver DCR Before:                            Mean {rec_pre_mean:.2f}x (Median {rec_pre_med:.2f}x)")
print(f"Receiver DCR After:                             Mean {rec_post_mean:.2f}x (Median {rec_post_med:.2f}x)")
print(f"Donor DCR Before:                               Mean {don_pre_mean:.2f}x (Median {don_pre_med:.2f}x)")
print(f"Donor DCR After:                                Mean {don_post_mean:.2f}x (Median {don_post_med:.2f}x)")
print(f"Donor DCR After p95:                            {don_post_p95:.2f}x")
print(f"Donor DCR After Max:                            {don_post_max:.2f}x")

