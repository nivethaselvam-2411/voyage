"""
TransitIQ Senior ML Evaluator — Detailed Audit Checks on Corrected 60-Min Model
Workspace: c:/Users/nivet/Downloads/Theme 4/Theme 4
"""
import os, sys, json
from pathlib import Path
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import precision_score, recall_score

ROOT = Path("c:/Users/nivet/Downloads/Theme 4/Theme 4")
BUS_RATED_CAPACITY = 70.0

# ── 1. LOAD & PREPARE CLEAN STRICT EX-ANTE DATASET ────────────────────────────
print("Loading route_hour_capacity dataset...")
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

# Ex-ante planned capacity
grid['lag_1d_buses'] = grid.groupby('route_id')['active_buses'].shift(24)
grid['rolling_buses_7d'] = grid.groupby(['route_id', 'hour'])['active_buses'].transform(
    lambda s: s.shift(1).rolling(7, min_periods=1).median().fillna(1.0)
)
grid['ex_ante_planned_buses'] = grid['lag_1d_buses'].fillna(grid['rolling_buses_7d']).fillna(1.0)
grid['ex_ante_capacity'] = grid['ex_ante_planned_buses'] * BUS_RATED_CAPACITY

# Ground truth DCR
grid['ground_truth_capacity'] = grid['active_buses'] * BUS_RATED_CAPACITY
grid['ground_truth_dcr'] = np.where(grid['ground_truth_capacity'] > 0, grid['pax'] / grid['ground_truth_capacity'], 0.0)
grid['ground_truth_overcrowded'] = (grid['ground_truth_dcr'] > 1.0).astype(int)

# Rolling stats
grid['rolling_mean_7d'] = grid.groupby(['route_id', 'hour'])['pax'].transform(lambda s: s.shift(1).rolling(7, min_periods=1).mean())
grid['rolling_std_7d'] = grid.groupby(['route_id', 'hour'])['pax'].transform(lambda s: s.shift(1).rolling(7, min_periods=1).std().fillna(0))

data = grid[grid['active_buses'] > 0].dropna(subset=['lag_7d_pax', 'lag_1d_pax', 'lag_2h_pax']).reset_index(drop=True)

train_df = data[(data['timestamp'] >= '2026-03-08') & (data['timestamp'] < '2026-03-22')].copy()
val_df   = data[(data['timestamp'] >= '2026-03-22') & (data['timestamp'] < '2026-03-27')].copy()
test_df  = data[data['timestamp'] >= '2026-03-27'].copy()

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

# ──────────────────────────────────────────────────────────────────────────────
# PART 1: FAIR BASELINE (HISTORICAL OVERCROWD SHARE ON TRAIN)
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("PART 1: FAIR HISTORICAL BASELINE VS CORRECTED ML MODEL")
print("=" * 80)

# In TRAIN: share of days route x hour x is_weekend has DCR > 1.0
train_share = train_df.groupby(['route_id', 'hour', 'is_weekend'])['ground_truth_overcrowded'].agg(
    train_overcrowd_share='mean',
    train_pax_mean='mean'
).reset_index()

test_df = test_df.merge(train_share, on=['route_id', 'hour', 'is_weekend'], how='left')
test_df['train_overcrowd_share'] = test_df['train_overcrowd_share'].fillna(0.0)
test_df['train_pax_mean'] = test_df['train_pax_mean'].fillna(0.0)

for k in [20, 50]:
    ml_tp = sum(grp.sort_values('pred_proba', ascending=False).head(k)['ground_truth_overcrowded'].sum() for _, grp in test_df.groupby('date'))
    # Fair baseline: rank by train_overcrowd_share descending, tie-break by train_pax_mean
    base_tp = sum(grp.sort_values(['train_overcrowd_share', 'train_pax_mean'], ascending=[False, False]).head(k)['ground_truth_overcrowded'].sum() for _, grp in test_df.groupby('date'))
    tot = k * 5
    print(f"Top-{k}/day Queue (Total {tot} alerts over 5 days):")
    print(f"  * Corrected ML Model (60m):      {ml_tp/tot*100:.2f}% Precision ({ml_tp}/{tot})")
    print(f"  * Fair Historical Share Baseline: {base_tp/tot*100:.2f}% Precision ({base_tp}/{tot})")
    print(f"  * Advantage over Fair Baseline:   +{(ml_tp - base_tp)/tot*100:.2f}% absolute precision\n")

# ──────────────────────────────────────────────────────────────────────────────
# PART 2: CHRONIC VS NON-CHRONIC ROUTES IN TOP-50 ALERTS
# ──────────────────────────────────────────────────────────────────────────────
print("=" * 80)
print("PART 2: TOP-50 ALERTS BREAKDOWN (CHRONIC VS NON-CHRONIC ROUTES)")
print("=" * 80)

# Define Chronic Route: Overcrowded on 70%+ of operational route-hours in TRAIN
route_train_overcrowd = train_df.groupby('route_id')['ground_truth_overcrowded'].agg(
    total_train_hours='count',
    overcrowded_train_hours='sum',
    overcrowd_rate='mean'
).reset_index()

chronic_routes_set = set(route_train_overcrowd[route_train_overcrowd['overcrowd_rate'] >= 0.70]['route_id'].unique())
print(f"Identified {len(chronic_routes_set)} chronic routes out of {len(routes)} routes in TRAIN (>= 70% overcrowding rate).")

# Extract Top-50 alerts per day
daily_top50 = []
for d, grp in test_df.groupby('date'):
    top_50 = grp.sort_values('pred_proba', ascending=False).head(50).copy()
    daily_top50.append(top_50)
df_top50 = pd.concat(daily_top50).reset_index(drop=True)
df_top50['is_chronic'] = df_top50['route_id'].isin(chronic_routes_set)

# Precision for Chronic vs Non-Chronic in Top-50
chronic_alerts = df_top50[df_top50['is_chronic']]
non_chronic_alerts = df_top50[~df_top50['is_chronic']]

p_chronic = chronic_alerts['ground_truth_overcrowded'].mean() * 100.0
p_non_chronic = non_chronic_alerts['ground_truth_overcrowded'].mean() * 100.0

# Overall Test Set ground truth counts for recall
test_df['is_chronic'] = test_df['route_id'].isin(chronic_routes_set)
total_chronic_overcrowded = test_df[test_df['is_chronic']]['ground_truth_overcrowded'].sum()
total_non_chronic_overcrowded = test_df[~test_df['is_chronic']]['ground_truth_overcrowded'].sum()

rec_chronic_covered = chronic_alerts['ground_truth_overcrowded'].sum()
rec_non_chronic_covered = non_chronic_alerts['ground_truth_overcrowded'].sum()

print(f"\nTop-50 Alerts Partition ({len(df_top50)} total alerts across 5 days):")
print(f"  * Chronic Routes Group (>= 70% Train Overcrowd Rate):")
print(f"      - Alerts in Top-50:  {len(chronic_alerts)} alerts ({len(chronic_alerts)/5:.1f}/day, {len(chronic_alerts)/250*100:.1f}% of queue)")
print(f"      - Precision:         {p_chronic:.2f}% ({chronic_alerts['ground_truth_overcrowded'].sum()}/{len(chronic_alerts)})")
print(f"      - Test Coverage:     {rec_chronic_covered}/{total_chronic_overcrowded} ({rec_chronic_covered/total_chronic_overcrowded*100:.2f}% of test chronic overcrowding)")
print(f"  * Non-Chronic Routes Group (< 70% Train Overcrowd Rate):")
print(f"      - Alerts in Top-50:  {len(non_chronic_alerts)} alerts ({len(non_chronic_alerts)/5:.1f}/day, {len(non_chronic_alerts)/250*100:.1f}% of queue)")
print(f"      - Precision:         {p_non_chronic:.2f}% ({non_chronic_alerts['ground_truth_overcrowded'].sum()}/{len(non_chronic_alerts)})")
print(f"      - Test Coverage:     {rec_non_chronic_covered}/{total_non_chronic_overcrowded} ({rec_non_chronic_covered/total_non_chronic_overcrowded*100:.2f}% of test non-chronic overcrowding)")

# ──────────────────────────────────────────────────────────────────────────────
# PART 3: CAPPED RECOMMENDATIONS AT 50 PER DAY BY PRIORITY
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("PART 3: CAPPED RECOMMENDATIONS (TOP-50 / DAY) BY PRIORITY & TYPE")
print("=" * 80)

# Generate all recommendations from corrected 60m predictions
all_recs = []
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

    if pred_dcr >= 1.25 and deficit >= 300:
        needed = int(np.ceil(deficit / 70.0))
        all_recs.append({
            'date': dt,
            'hour': hr,
            'route_id': rt,
            'priority': 1,
            'action_category': 'Fleet Injection',
            'pred_dcr': pred_dcr,
            'deficit': deficit,
            'actual_dcr': actual_dcr,
            'actual_buses': actual_buses,
            'is_success_strict': (actual_dcr >= 1.20),
            'is_success_broad': (actual_dcr > 1.00)
        })
    elif 1.10 <= pred_dcr < 1.25 and deficit >= 150:
        all_recs.append({
            'date': dt,
            'hour': hr,
            'route_id': rt,
            'priority': 2,
            'action_category': 'Short-Turn Loop',
            'pred_dcr': pred_dcr,
            'deficit': deficit,
            'actual_dcr': actual_dcr,
            'actual_buses': actual_buses,
            'is_success_strict': (actual_dcr >= 1.00),
            'is_success_broad': (actual_dcr >= 1.00)
        })
    elif pred_dcr <= 0.40 and planned_buses >= 4:
        all_recs.append({
            'date': dt,
            'hour': hr,
            'route_id': rt,
            'priority': 3,
            'action_category': 'Fleet Reallocation',
            'pred_dcr': pred_dcr,
            'deficit': deficit,
            'actual_dcr': actual_dcr,
            'actual_buses': actual_buses,
            'is_success_strict': (actual_dcr <= 0.40 and actual_buses >= 4),
            'is_success_broad': (actual_dcr <= 0.50)
        })

df_raw_recs = pd.DataFrame(all_recs)

# Cap at 50 recommendations per day by Priority ascending (1, then 2, then 3) and pred_dcr / deficit severity
capped_daily_recs = []
for d, grp in df_raw_recs.groupby('date'):
    # Sort by priority (1=Injection first, then 2=Short-turn, then 3=Surplus) and deficit/DCR severity
    # For priority 1 & 2: sort pred_dcr descending. For priority 3: sort pred_dcr ascending
    p1_p2 = grp[grp['priority'].isin([1, 2])].sort_values(['priority', 'pred_dcr'], ascending=[True, False])
    p3    = grp[grp['priority'] == 3].sort_values('pred_dcr', ascending=True)
    combined = pd.concat([p1_p2, p3]).head(50)
    capped_daily_recs.append(combined)

df_capped = pd.concat(capped_daily_recs).reset_index(drop=True)
print(f"Capped queue total across 5 days: {len(df_capped)} recommendations (exactly 50/day).")

print("\nCAPPED QUEUE (TOP-50 / DAY) ACCURACY BY ACTION TYPE:")
for cat in ['Fleet Injection', 'Short-Turn Loop', 'Fleet Reallocation']:
    sub = df_capped[df_capped['action_category'] == cat]
    if len(sub) > 0:
        p_strict = sub['is_success_strict'].mean() * 100.0
        p_broad  = sub['is_success_broad'].mean() * 100.0
        print(f"  * {cat} ({len(sub)} alerts in capped queue; {len(sub)/5:.1f}/day):")
        print(f"      - Strict Precision: {p_strict:.2f}% ({sub['is_success_strict'].sum()}/{len(sub)})")
        print(f"      - Broad Precision:  {p_broad:.2f}% ({sub['is_success_broad'].sum()}/{len(sub)})")
    else:
        print(f"  * {cat}: 0 alerts in capped queue.")

# ──────────────────────────────────────────────────────────────────────────────
# PART 4: REAL DEPOT-CONSTRAINED DONOR-RECEIVER PAIRS
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("PART 4: REAL DEPOT-CONSTRAINED DONOR-RECEIVER PAIRS")
print("=" * 80)

# Get true primary depot per route from clean parquet tickets
# In day_*.parquet, we can map each route to its primary depot
print("Extracting primary operating depot for each route from clean tickets...")
sample_day = pd.read_parquet(ROOT / 'data/clean/day_2026-03-27.parquet')
route_depot_map = sample_day.groupby('route_id')['depot'].agg(lambda s: s.mode()[0] if len(s.mode()) > 0 else s.iloc[0]).to_dict()
print(f"Mapped {len(route_depot_map)} routes to their primary home depot.")

test_df['depot'] = test_df['route_id'].map(route_depot_map).fillna("Unknown Depot")

# Identify Deficit slots (Receiver candidate) & Surplus slots (Donor candidate)
# Deficit: Pred DCR >= 1.25 and deficit >= 300
# Surplus: Pred DCR <= 0.40 and active_buses >= 4 (to safely donate 1-2 buses without starving)
receivers = test_df[(test_df['pred_dcr_60m'] >= 1.25) & (test_df['pred_deficit_60m'] >= 300) & (test_df['depot'] != 'Unknown Depot')].copy()
donors    = test_df[(test_df['pred_dcr_60m'] <= 0.40) & (test_df['active_buses'] >= 4) & (test_df['depot'] != 'Unknown Depot')].copy()

# Join on (date, hour, SAME DEPOT)
pairs = receivers.merge(
    donors,
    on=['date', 'hour', 'depot'],
    suffixes=('_receiver', '_donor')
)
# Exclude self-matches
pairs = pairs[pairs['route_id_receiver'] != pairs['route_id_donor']].copy()

print(f"\nTotal valid depot-constrained donor-receiver pairs found in 5-day TEST: {len(pairs):,}")
for d, grp in pairs.groupby('date'):
    print(f"  Date {d}: {len(grp)} valid pairs across {grp['depot'].nunique()} depots.")

# Select 5 representative, distinct depot-constrained pairs
pairs['deficit_pax'] = pairs['pred_deficit_60m_receiver']
top_pairs = pairs.sort_values('deficit_pax', ascending=False).drop_duplicates(subset=['depot']).head(5)

print("\n5 CONCRETE DEPOT-CONSTRAINED DONOR-RECEIVER EXAMPLES:")
pair_rows = []
for idx, r in top_pairs.iterrows():
    rec_pax = r['pax_receiver']
    rec_buses = r['active_buses_receiver']
    don_pax = r['pax_donor']
    don_buses = r['active_buses_donor']
    
    rec_pre_dcr = rec_pax / (rec_buses * 70.0)
    rec_post_dcr_1 = rec_pax / ((rec_buses + 1) * 70.0)
    rec_post_dcr_2 = rec_pax / ((rec_buses + 2) * 70.0)
    
    don_pre_dcr = don_pax / (don_buses * 70.0)
    don_post_dcr_1 = don_pax / (max(don_buses - 1, 1) * 70.0)
    don_post_dcr_2 = don_pax / (max(don_buses - 2, 1) * 70.0)
    
    print(f"Pair #{len(pair_rows)+1}: [{r['depot']}] @ {r['date']} {int(r['hour']):02d}:00")
    print(f"  * Receiver: Route {r['route_id_receiver']} ({int(rec_buses)} buses, {int(rec_pax)} pax) -> DCR Before: {rec_pre_dcr:.2f}x | After +1 bus: {rec_post_dcr_1:.2f}x | After +2 buses: {rec_post_dcr_2:.2f}x")
    print(f"  * Donor:    Route {r['route_id_donor']} ({int(don_buses)} buses, {int(don_pax)} pax) -> DCR Before: {don_pre_dcr:.2f}x | After -1 bus: {don_post_dcr_1:.2f}x | After -2 buses: {don_post_dcr_2:.2f}x\n")
    
    pair_rows.append({
        'Depot': r['depot'],
        'Date_Time': f"{r['date']} {int(r['hour']):02d}:00",
        'Receiver_Route': f"Route {r['route_id_receiver']}",
        'Receiver_Pre_DCR': round(rec_pre_dcr, 2),
        'Receiver_Post_DCR_1Bus': round(rec_post_dcr_1, 2),
        'Receiver_Post_DCR_2Bus': round(rec_post_dcr_2, 2),
        'Donor_Route': f"Route {r['route_id_donor']}",
        'Donor_Pre_DCR': round(don_pre_dcr, 2),
        'Donor_Post_DCR_1Bus': round(don_post_dcr_1, 2),
        'Donor_Post_DCR_2Bus': round(don_post_dcr_2, 2)
    })

pd.DataFrame(pair_rows).to_csv(ROOT / "outputs/backtest/tables/depot_rebalance_pairs_examples.csv", index=False)
print("Saved outputs/backtest/tables/depot_rebalance_pairs_examples.csv")

# ──────────────────────────────────────────────────────────────────────────────
# PART 5: CONFIRMATION OF DATE PARTITIONS AND MARCH 1-7 BURN-IN WINDOW
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("PART 5: DATE PARTITION CONFIRMATION & MARCH 1-7 LOOKBACK WINDOW")
print("=" * 80)

# Load full route_hour_capacity to inspect date distribution
rh_full = pd.read_parquet(ROOT / 'data/clean/route_hour_capacity.parquet')
rh_full['timestamp'] = pd.to_datetime(rh_full['date']) + pd.to_timedelta(rh_full['hour'], unit='h')

all_dates = sorted(rh_full['date'].unique())
train_dates = [d for d in all_dates if '2026-03-08' <= d < '2026-03-22']
val_dates   = [d for d in all_dates if '2026-03-22' <= d < '2026-03-27']
test_dates  = [d for d in all_dates if d >= '2026-03-27']
unused_dates = [d for d in all_dates if d < '2026-03-08']

print(f"Total calendar days in dataset: {len(all_dates)} days ({all_dates[0]} to {all_dates[-1]})")
print(f"  * Unused Lookback Burn-in Days: {len(unused_dates)} days ({unused_dates[0]} to {unused_dates[-1]})")
print(f"  * TRAIN Period:                 {len(train_dates)} days ({train_dates[0]} to {train_dates[-1]})")
print(f"  * VALIDATION Period:            {len(val_dates)} days ({val_dates[0]} to {val_dates[-1]})")
print(f"  * TEST Period (Out-of-time):    {len(test_dates)} days ({test_dates[0]} to {test_dates[-1]})")

n_burnin = len(rh_full[rh_full['date'].isin(unused_dates)])
n_train  = len(rh_full[rh_full['date'].isin(train_dates)])
n_val    = len(rh_full[rh_full['date'].isin(val_dates)])
n_test   = len(rh_full[rh_full['date'].isin(test_dates)])

print(f"\nSlot row counts by partition:")
print(f"  * Lookback Burn-in: {n_burnin:,} route-hour slots")
print(f"  * Train set:        {n_train:,} route-hour slots")
print(f"  * Val set:          {n_val:,} route-hour slots")
print(f"  * Test set:         {n_test:,} route-hour slots")
print(f"  * Total:            {len(rh_full):,} route-hour slots")

print("""
EXPLANATION FOR MARCH 1 TO MARCH 7:
1. Autoregressive Lags: Feature `lag_7d_pax` represents ridership exactly 168 hours (7 days) prior.
   For any date prior to March 8, the 7-day lookback falls into February 2026, which is not in the dataset.
2. Rolling Window Statistics: Features `rolling_mean_7d` and `rolling_std_7d` require a continuous 7-day
   historical buffer to compute rolling statistics without artificial zero-padding or NaN imputation.
3. Strict Leakage Prevention: March 1 to 7 is preserved strictly as the uncorrupted historical lookback
   reservoir, ensuring every training example from March 8 onwards has 100% verified, observed historical features.
""")
