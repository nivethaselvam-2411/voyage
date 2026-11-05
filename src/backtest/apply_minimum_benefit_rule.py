import pandas as pd
import numpy as np

df = pd.read_csv('outputs/backtest/tables/single_allocation_rebalance_pairs.csv')
deficit = df['pax_rec'] - df['buses_rec'] * 70.0
df_filtered = df[deficit >= 70.0].copy().reset_index(drop=True)

k_old = int(df['k_transfer'].sum())
k_new = int(df_filtered['k_transfer'].sum())
norm_old = int(df['reaches_1_0'].sum())
norm_new = int(df_filtered['reaches_1_0'].sum())

print("=" * 80)
print("MINIMUM BENEFIT RULE REBALANCING AUDIT (DEFICIT >= 70 PAX)")
print("=" * 80)
print(f"Old count: {len(df)} pairs -> New count: {len(df_filtered)} pairs (removed {len(df) - len(df_filtered)} low-benefit operations)")
print(f"Old buses: {k_old} buses -> New buses: {k_new} buses (reduced by {k_old - k_new} buses)")
print(f"Old normalized: {norm_old}/{len(df)} ({norm_old/len(df)*100:.2f}%) -> New normalized: {norm_new}/{len(df_filtered)} ({norm_new/len(df_filtered)*100:.2f}%)")
print(f"Receiver Pre-DCR:  Mean {df_filtered['pre_dcr_rec'].mean():.2f}x (Median: {df_filtered['pre_dcr_rec'].median():.2f}x)")
print(f"Receiver Post-DCR: Mean {df_filtered['post_dcr_rec'].mean():.2f}x (Median: {df_filtered['post_dcr_rec'].median():.2f}x)")
print(f"Donor Pre-DCR:     Mean {df_filtered['pre_dcr_don'].mean():.2f}x (Median: {df_filtered['pre_dcr_don'].median():.2f}x)")
print(f"Donor Post-DCR:    Mean {df_filtered['post_dcr_don'].mean():.2f}x (Median: {df_filtered['post_dcr_don'].median():.2f}x, p95: {df_filtered['post_dcr_don'].quantile(0.95):.2f}x, max: {df_filtered['post_dcr_don'].max():.2f}x)")
print(f"Capacity moved (pax): {df_filtered['capacity_moved_pax'].sum():.0f} seats")
print(f"Actual passenger reduction: {df_filtered['actual_passenger_reduction'].sum():.0f} pax")

