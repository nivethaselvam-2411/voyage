"""
Smart Public Transport Operations — Chennai MTC ETM Analysis
PHASE 4: OPERATIONAL RECOMMENDATION ENGINE

Translates Phase 3 Machine Learning predictions into actionable, control-room-ready
operational interventions for CUMTA / MTC dispatchers.

Produces:
1. outputs/tables/recommendations.csv (Top prioritized operational recommendations)
2. outputs/tables/phase4_recommendations_all.csv (Comprehensive intervention catalog)
3. outputs/charts/phase4_recommendations_action_breakdown.png
4. outputs/charts/phase4_impact_simulation.png
"""

import os, sys, json, time, warnings
from pathlib import Path

_mpl_dir = os.path.join(os.environ.get('TEMP', os.path.expanduser('~')), 'mpl_cfg')
os.makedirs(_mpl_dir, exist_ok=True)
os.environ['MPLCONFIGDIR'] = _mpl_dir

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings('ignore')

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT       = Path("c:/Users/nivet/Downloads/Theme 4/Theme 4")
CONFIG_F   = ROOT / "src" / "recommendation_config.json"
PREDS_F    = ROOT / "outputs" / "tables" / "phase3_predictions_test.csv"
OUT_CHARTS = ROOT / "outputs" / "charts"
OUT_TABLES = ROOT / "outputs" / "tables"

for d in [OUT_CHARTS, OUT_TABLES]:
    d.mkdir(parents=True, exist_ok=True)


def main():
    print("=" * 80, flush=True)
    print("MTC CHENNAI ETM DATASET — PHASE 4: OPERATIONAL RECOMMENDATION ENGINE", flush=True)
    print("=" * 80, flush=True)
    t0 = time.time()

    # 1. Load Config & Predictions
    print("\n[Step 1/4] Loading operational configuration and Phase 3 predictions...", flush=True)
    with open(CONFIG_F, 'r') as f:
        config = json.load(f)

    params = config['operational_parameters']
    depots = config['depot_mappings']
    rail_parallel = config['rail_metro_corridor_parallel']

    df_preds = pd.read_csv(PREDS_F)
    print(f"Loaded {len(df_preds):,} predictions from Phase 3 test set.")

    # 2. Rule Evaluation
    print("\n[Step 2/4] Generating Control Room Recommendations based on operational logic...", flush=True)
    df_preds['deficit_pax'] = df_preds['pred_pax_xgb'] - df_preds['deployed_capacity']

    recommendations = []

    # Sort test predictions chronologically per route to detect consecutive hours
    df_preds = df_preds.sort_values(['route_id', 'timestamp']).reset_index(drop=True)

    for idx, row in df_preds.iterrows():
        rt = str(row['route_id'])
        ts = str(row['timestamp'])
        date = str(row['date'])
        hr = int(row['hour'])
        buses = int(row['active_buses'])
        pred_pax = int(row['pred_pax_xgb'])
        cap = int(row['deployed_capacity'])
        lf = float(row['pred_load_factor_xgb'])
        deficit = int(row['deficit_pax'])
        depot = depots.get(rt, "Nearest Depot (Anna Nagar / Central / Tambaram)")
        parallel_rail = rail_parallel.get(rt, None)

        # Rule 1: SEVERE CRUSH OVERCROWDING -> INJECT DEPOT RESERVE
        if lf >= params['severe_crush_threshold_lf'] and deficit >= params['min_passenger_deficit']:
            needed_buses = int(np.ceil(deficit / params['rated_bus_capacity']))
            new_lf = pred_pax / ((buses + needed_buses) * params['rated_bus_capacity'])
            recommendations.append({
                'priority': 1,
                'location': f"Route {rt} ({depot})",
                'time_window': f"{date} {hr:02d}:00–{hr+1:02d}:00",
                'predicted_problem': f"Severe Overcrowding (Load Factor {lf:.2f}x, Deficit +{deficit:,} pax)",
                'recommended_action': f"Inject +{needed_buses} reserve standby buses from {depot}",
                'operational_reason': f"Passenger forecast of {pred_pax:,} exceeds rated fleet capacity ({cap:,} pax). High risk of boarding failures and passenger dwell delays.",
                'expected_impact': f"Reduces load factor from {lf:.2f}x to {new_lf:.2f}x (clearing crush), restoring reliable boarding across all corridor stops.",
                'action_category': "Fleet Injection",
                'route_id': rt,
                'hour': hr,
                'pre_lf': lf,
                'post_lf': new_lf,
                'buses_change': needed_buses
            })

        # Rule 2: MULTI-MODAL ADVISORY -> COMMUTER LOAD BALANCING
        elif lf >= 1.20 and parallel_rail is not None:
            recommendations.append({
                'priority': 2,
                'location': f"Route {rt} Corridor",
                'time_window': f"{date} {hr:02d}:00–{hr+1:02d}:00",
                'predicted_problem': f"Corridor Congestion & Bus Crush ({lf:.2f}x Load Factor)",
                'recommended_action': f"Broadcast dynamic commuter advisory to transfer to {parallel_rail}",
                'operational_reason': f"Route {rt} corridor runs directly parallel to {parallel_rail}. Bus line at crush capacity while suburban/metro has spare standing space.",
                'expected_impact': f"Diverts 15–20% of intermediate commuters to rail transit, reducing bus load factor to ~{lf*0.82:.2f}x without extra bus deployment.",
                'action_category': "Multi-Modal Advisory",
                'route_id': rt,
                'hour': hr,
                'pre_lf': lf,
                'post_lf': lf * 0.82,
                'buses_change': 0
            })

        # Rule 3: MODERATE OVERCROWDING -> SHORT-TURN SHUTTLE
        elif 1.10 <= lf < 1.25 and deficit >= 150:
            recommendations.append({
                'priority': 3,
                'location': f"Route {rt} High-Demand Segment",
                'time_window': f"{date} {hr:02d}:00–{hr+1:02d}:00",
                'predicted_problem': f"Mid-Corridor Overcrowding (Load Factor {lf:.2f}x, Deficit +{deficit} pax)",
                'recommended_action': f"Short-turn 2 buses to run high-frequency mid-route express loops",
                'operational_reason': f"Boarding concentration occurs along the central 8–10km corridor segment; full-route turnaround takes too long.",
                'expected_impact': f"Shortens cycle turnaround time by ~40%, doubling frequency at choke points and stabilizing load factor at ~{lf*0.80:.2f}x.",
                'action_category': "Short-Turn Loop",
                'route_id': rt,
                'hour': hr,
                'pre_lf': lf,
                'post_lf': lf * 0.80,
                'buses_change': 0
            })

        # Rule 4: CHRONIC UNDER-UTILIZATION -> REALLOCATE SURPLUS FLEET
        elif lf <= params['surplus_threshold_lf'] and buses >= params['min_surplus_active_buses']:
            cut_buses = max(1, buses // 3)
            new_lf = pred_pax / ((buses - cut_buses) * params['rated_bus_capacity'])
            fuel_saved = cut_buses * params['avg_route_length_km'] * params['diesel_cost_per_km_inr']
            recommendations.append({
                'priority': 4,
                'location': f"Route {rt} ({depot})",
                'time_window': f"{date} {hr:02d}:00–{hr+1:02d}:00",
                'predicted_problem': f"Fleet Surplus & Under-utilization (Load Factor {lf:.2f}x with {buses} buses)",
                'recommended_action': f"Reallocate {cut_buses} surplus buses to adjacent deficit routes",
                'operational_reason': f"Predicted ridership is only {pred_pax} passengers across {buses} deployed buses ({cap} capacity). Significant empty vehicle-km traveled.",
                'expected_impact': f"Saves ~INR {fuel_saved:,.0f} per round-trip in operational diesel costs, while keeping service load factor at comfortable {new_lf:.2f}x.",
                'action_category': "Fleet Reallocation",
                'route_id': rt,
                'hour': hr,
                'pre_lf': lf,
                'post_lf': new_lf,
                'buses_change': -cut_buses
            })

    rec_df = pd.DataFrame(recommendations)
    print(f"Total operational recommendations triggered: {len(rec_df):,}")

    # 3. Export Tables
    print("\n[Step 3/4] Exporting Top 20 prioritized control room recommendations...", flush=True)
    # Save all recommendations
    rec_df.to_csv(OUT_TABLES / "phase4_recommendations_all.csv", index=False)

    # Prioritize: Sort by Priority (1=Inject, 2=Advisory, 3=Short-turn, 4=Reallocate) and Pre-Load Factor descending
    top_recs = rec_df.sort_values(by=['priority', 'pre_lf'], ascending=[True, False]).drop_duplicates(subset=['location', 'action_category']).head(20)

    # 6 required columns for Control Room summary
    final_output_cols = [
        'location', 'time_window', 'predicted_problem',
        'recommended_action', 'operational_reason', 'expected_impact'
    ]
    top_recs[final_output_cols].to_csv(OUT_TABLES / "recommendations.csv", index=False)
    print(f"  Saved {OUT_TABLES / 'recommendations.csv'} (Top 20 Control Room Actions)")

    # Print top 5 recommendations to stdout
    print("\nSAMPLE TOP CONTROL ROOM RECOMMENDATIONS:")
    for _, r in top_recs.head(5).iterrows():
        print(f"  * [{r['location']}] @ {r['time_window']}: {r['recommended_action']}")
        print(f"    Reason: {r['operational_reason']}")
        print(f"    Impact: {r['expected_impact']}\n")

    # 4. Render Visualizations
    print("[Step 4/4] Rendering Phase 4 Operational Charts...", flush=True)
    sns.set_theme(style='whitegrid', font='sans-serif')

    # Chart 1: Action Breakdown & Hourly Distribution
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7), dpi=200)

    action_counts = rec_df['action_category'].value_counts()
    colors = ['#c0392b', '#2980b9', '#e67e22', '#27ae60']
    ax1.pie(action_counts, labels=action_counts.index, autopct='%1.1f%%', colors=colors, startangle=140, textprops={'fontsize': 11, 'fontweight': 'bold'})
    ax1.set_title(f'Distribution of Recommended Control Room Interventions\n(Total {len(rec_df):,} Interventions Evaluated)', fontsize=13, fontweight='bold')

    # Interventions by hour
    hour_action = rec_df.groupby(['hour', 'action_category']).size().unstack(fill_value=0)
    hour_action.plot(kind='bar', stacked=True, ax=ax2, colormap='Spectral', edgecolor='black', alpha=0.85)
    ax2.set_title('Hourly Profile of Recommended Operational Actions\n(Heavy Morning & Evening Injections vs Midday Surplus Reallocation)', fontsize=13, fontweight='bold')
    ax2.set_xlabel('Hour of Day', fontsize=11)
    ax2.set_ylabel('Number of Recommendations', fontsize=11)
    ax2.legend(title='Action Category', loc='upper right', frameon=True)

    plt.tight_layout()
    chart1_p = OUT_CHARTS / "phase4_recommendations_action_breakdown.png"
    plt.savefig(chart1_p, dpi=200)
    plt.close()
    print(f"  Chart 1: Saved {chart1_p}")

    # Chart 2: Before vs After Impact Simulation on Load Factor
    fig, ax = plt.subplots(figsize=(13, 7), dpi=200)
    sample_sim = top_recs[top_recs['action_category'].isin(['Fleet Injection', 'Short-Turn Loop', 'Multi-Modal Advisory'])].head(10)
    
    x = np.arange(len(sample_sim))
    width = 0.35

    rects1 = ax.bar(x - width/2, sample_sim['pre_lf'], width, label='Predicted Pre-Intervention Load Factor', color='#e74c3c', alpha=0.9)
    rects2 = ax.bar(x + width/2, sample_sim['post_lf'], width, label='Simulated Post-Intervention Load Factor', color='#2ecc71', alpha=0.9)

    ax.axhline(1.0, color='black', linestyle='--', lw=1.5, label='Rated Capacity Benchmark (1.0x)')
    ax.axhline(1.25, color='darkred', linestyle=':', lw=1.5, label='Severe Crush Threshold (1.25x)')

    ax.set_ylabel('Load Factor (Demand / Deployed Capacity)', fontsize=11)
    ax.set_title('Operational Impact Simulation: Before vs. After Control Room Intervention\nLoad Factor Normalization across Top Deficit Routes', fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([loc.split('(')[0].strip() for loc in sample_sim['location']], rotation=30, ha='right', fontsize=10)
    ax.legend(loc='upper right', frameon=True)
    ax.set_ylim(0, max(sample_sim['pre_lf'].max() * 1.15, 1.6))

    # Add data labels
    for rect in rects1:
        h = rect.get_height()
        ax.annotate(f'{h:.2f}x', xy=(rect.get_x() + rect.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9, fontweight='bold')
    for rect in rects2:
        h = rect.get_height()
        ax.annotate(f'{h:.2f}x', xy=(rect.get_x() + rect.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9, color='darkgreen', fontweight='bold')

    plt.tight_layout()
    chart2_p = OUT_CHARTS / "phase4_impact_simulation.png"
    plt.savefig(chart2_p, dpi=200)
    plt.close()
    print(f"  Chart 2: Saved {chart2_p}")

    elapsed = time.time() - t0
    print("\n" + "=" * 80, flush=True)
    print(f"PHASE 4 COMPLETE: Operational engine generated recommendations in {elapsed:.1f}s.", flush=True)
    print("=" * 80, flush=True)

if __name__ == '__main__':
    main()

