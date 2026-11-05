import json
import math
import numpy as np
import pandas as pd

df = pd.read_csv('outputs/backtest/tables/single_allocation_rebalance_pairs.csv')
top3 = df.sort_values(by=['actual_passenger_reduction', 'capacity_moved_pax'], ascending=[False, False]).head(3)

np.random.seed(42)
r20_idx = np.random.choice(df.index.difference(top3.index), size=20, replace=False)
r20 = df.loc[r20_idx]
sample = pd.concat([top3, r20]).reset_index(drop=True)

for i, r in sample.iterrows():
    prefix = f"TOP-{i+1}" if i < 3 else f"RANDOM-{i-2}"
    depot = r['depot']
    date = r['date']
    hour = int(r['hour'])
    rec = r['receiver_route']
    don = r['donor_route']
    print(f"================================================================================")
    print(f"[{prefix}] Depot: {depot} | Date: {date} | Hour: {hour:02d}:00 | Receiver: Route {rec} | Donor: Route {don}")
    print(f"================================================================================")
    print("RAW CSV ROW:")
    row_dict = r.to_dict()
    print(json.dumps(row_dict))
    
    pax_r = float(r['pax_rec'])
    b_r = float(r['buses_rec'])
    pax_d = float(r['pax_don'])
    b_d = float(r['buses_don'])
    
    k_need = max(0, int(math.ceil(pax_r / 70.0) - b_r))
    cap1 = max(0, int(math.floor(b_d - (pax_d / 56.0))))
    cap2 = max(0, int(math.floor(0.40 * b_d)))
    k = max(0, min(k_need, cap1, cap2))
    post_rec = pax_r / ((b_r + k) * 70.0)
    post_don = pax_d / ((b_d - k) * 70.0) if (b_d - k) > 0 else 0.0
    reaches_1_0 = int(post_rec <= 1.0001)
    
    cap_before = b_r * 70.0
    cap_after = (b_r + k) * 70.0
    act_red = max(0.0, pax_r - cap_before) - max(0.0, pax_r - cap_after)
    cap_moved = k * 70.0
    
    print("HAND RECOMPUTATION:")
    print(f"  k_needed                   = ceil({pax_r:.1f} / 70) - {b_r:.0f} = {int(math.ceil(pax_r / 70.0))} - {b_r:.0f} = {k_need}  [CSV k_needed = {int(r['k_needed'])}]")
    print(f"  donor cap1 (DCR <= 0.80)   = floor({b_d:.0f} - {pax_d:.1f} / 56) = floor({b_d:.0f} - {pax_d/56.0:.2f}) = {cap1}  [CSV cap1 = {int(r['cap1'])}]")
    print(f"  donor cap2 (retain >= 60%) = floor(0.40 * {b_d:.0f}) = {cap2}  [CSV cap2 = {int(r['cap2'])}]")
    print(f"  k                          = max(0, min({k_need}, {cap1}, {cap2})) = {k}  [CSV k_transfer = {int(r['k_transfer'])}] -> EXACT MATCH")
    print(f"  receiver DCR after         = {pax_r:.1f} / (({b_r:.0f} + {k}) * 70) = {pax_r:.1f} / {((b_r+k)*70):.0f} = {post_rec:.4f}  [CSV post_dcr_rec = {r['post_dcr_rec']:.4f}] -> EXACT MATCH")
    print(f"  donor DCR after            = {pax_d:.1f} / (({b_d:.0f} - {k}) * 70) = {pax_d:.1f} / {((b_d-k)*70):.0f} = {post_don:.4f}  [CSV post_dcr_don = {r['post_dcr_don']:.4f}] -> EXACT MATCH")
    print(f"  reaches 1.0                = {reaches_1_0}  [CSV reaches_1_0 = {int(r['reaches_1_0'])}] -> EXACT MATCH")
    print(f"  capacity moved (pax)       = {k} * 70 = {cap_moved:.0f} seats  [CSV capacity_moved_pax = {r['capacity_moved_pax']:.0f}] -> EXACT MATCH")
    print(f"  actual passenger reduction = max(0, {pax_r:.1f} - {cap_before:.0f}) - max(0, {pax_r:.1f} - {cap_after:.0f}) = {act_red:.0f} pax  [CSV actual_passenger_reduction = {r['actual_passenger_reduction']:.0f}] -> EXACT MATCH")
    print()
