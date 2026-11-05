import math
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(".")
OUT_TABLES = ROOT / "outputs/backtest/tables"

# Load test predictions
test_df = pd.read_csv(ROOT / "outputs/demo/route_hour_predictions.csv.gz")

# Filter candidate receivers and donors
# Receiver: predicted DCR >= 1.25 and predicted deficit >= 300
receivers = test_df[(test_df['pred_dcr_60m'] >= 1.25) & (test_df['pred_deficit_60m'] >= 300) & (test_df['depot'] != 'Unknown Depot')].copy()
# Donor: predicted DCR <= 0.40 and active buses >= 4
donors = test_df[(test_df['pred_dcr_60m'] <= 0.40) & (test_df['active_buses'] >= 4) & (test_df['depot'] != 'Unknown Depot')].copy()

raw_pairs = receivers.merge(donors, on=['date', 'hour', 'depot'], suffixes=('_receiver', '_donor'))
raw_pairs = raw_pairs[raw_pairs['route_id_receiver'] != raw_pairs['route_id_donor']].copy()

# Sort pairs by receiver predicted deficit descending
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
        
        pred_pax_rec = float(row['pred_pax_60m_receiver'])
        planned_buses_rec = float(row['ex_ante_planned_buses_receiver'])
        
        # Minimum-benefit rule: deficit must be at least 70 pax (one bus's worth)
        deficit_rec = pax_rec - (buses_rec * 70.0)
        if deficit_rec < 70.0:
            continue
            
        pre_dcr_rec = pax_rec / (buses_rec * 70.0) if buses_rec > 0 else 0.0
        pre_dcr_don = pax_don / (buses_don * 70.0) if buses_don > 0 else 0.0
        
        # Formulas:
        k_needed = max(0, int(math.ceil(pax_rec / 70.0) - buses_rec))
        cap1 = max(0, int(math.floor(buses_don - (pax_don / 56.0))))
        cap2 = max(0, int(math.floor(0.40 * buses_don)))
        max_k_donor_can_give = min(cap1, cap2)
        
        k = max(0, min(k_needed, max_k_donor_can_give))
        
        if k > 0:
            post_dcr_rec = pax_rec / ((buses_rec + k) * 70.0)
            post_dcr_don = pax_don / ((buses_don - k) * 70.0) if (buses_don - k) > 0 else 0.0
            reaches_1_0 = (post_dcr_rec <= 1.0001)
            
            # Observed passenger reduction (computed with actual pax and active buses)
            cap_before_obs = buses_rec * 70.0
            cap_after_obs = (buses_rec + k) * 70.0
            excess_before_obs = max(0.0, pax_rec - cap_before_obs)
            excess_after_obs = max(0.0, pax_rec - cap_after_obs)
            observed_passenger_reduction = excess_before_obs - excess_after_obs
            
            # Predicted passenger reduction (simulated using predicted pax and planned buses)
            cap_before_pred = planned_buses_rec * 70.0
            cap_after_pred = (planned_buses_rec + k) * 70.0
            excess_before_pred = max(0.0, pred_pax_rec - cap_before_pred)
            excess_after_pred = max(0.0, pred_pax_rec - cap_after_pred)
            predicted_passenger_reduction = excess_before_pred - excess_after_pred
            
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
                'pred_pax_rec': pred_pax_rec,
                'planned_buses_rec': planned_buses_rec,
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
                'predicted_passenger_reduction': predicted_passenger_reduction,
                'observed_passenger_reduction': observed_passenger_reduction
            })
            
            depot_donors_committed.add(don_id)
            depot_receivers_matched.add(rec_id)

df_single = pd.DataFrame(single_alloc_results)
df_single.to_csv(OUT_TABLES / "single_allocation_rebalance_pairs.csv", index=False)

print(f"Generated {len(df_single)} single-allocation rebalance pairs with minimum-benefit rule.")
print(f"Total buses transferred: {df_single['k_transfer'].sum()}")
print(f"Overcrowded receivers normalized (<= 1.0x): {df_single['reaches_1_0'].sum()} ({df_single['reaches_1_0'].mean()*100:.2f}%)")
print(f"Total capacity moved: {df_single['capacity_moved_pax'].sum():.0f} seats")
print(f"Total predicted passenger reduction (simulated): {df_single['predicted_passenger_reduction'].sum():.0f} pax")
print(f"Total observed passenger reduction (actual): {df_single['observed_passenger_reduction'].sum():.0f} pax")
print(f"Receiver pre-DCR: Mean {df_single['pre_dcr_rec'].mean():.2f}x (Median: {df_single['pre_dcr_rec'].median():.2f}x)")
print(f"Receiver post-DCR: Mean {df_single['post_dcr_rec'].mean():.2f}x (Median: {df_single['post_dcr_rec'].median():.2f}x)")
print(f"Donor post-DCR: Mean {df_single['post_dcr_don'].mean():.2f}x (p95: {df_single['post_dcr_don'].quantile(0.95):.2f}x, max: {df_single['post_dcr_don'].max():.2f}x)")
