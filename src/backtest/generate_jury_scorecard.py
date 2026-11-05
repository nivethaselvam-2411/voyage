"""
Marina Sentinel: Generate Reconciled Master Jury Scorecard Image
Synchronized with Final Audited Pitch Numbers.
"""
import os
import tempfile
os.environ['MPLCONFIGDIR'] = tempfile.gettempdir()

from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_CHARTS = ROOT / "outputs/backtest/charts"
OUT_CHARTS.mkdir(parents=True, exist_ok=True)

plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
fig = plt.figure(figsize=(18, 12), dpi=300)
fig.patch.set_facecolor('#F8FAFC')

# Main Super Title & Header
fig.text(0.5, 0.965, "TRANSIT-IQ : EXECUTIVE SYSTEM PERFORMANCE & ML SCORECARD", 
         ha='center', va='center', fontsize=22, fontweight='bold', color='#0F172A', fontfamily='sans-serif')
fig.text(0.5, 0.942, "Benchmarked on 67.8M Real ETM Tickets (31 Days) | 5-Day Out-of-Time Test Set (March 27-31, 2026) | Strict 60-Min Ex-Ante Horizon", 
         ha='center', va='center', fontsize=12, color='#475569', fontfamily='sans-serif')

gs = fig.add_gridspec(2, 3, left=0.06, right=0.95, top=0.90, bottom=0.07, wspace=0.28, hspace=0.32)

NAVY = '#1E293B'
TEAL = '#0EA5E9'
GREEN = '#10B981'
AMBER = '#F59E0B'
CORAL = '#EF4444'
GRAY = '#94A3B8'
LIGHT_BG = '#F1F5F9'

# ──────────────────────────────────────────────────────────────────────────────
# SUBPLOT 1: 1-HOUR PASSENGER FORECAST ACCURACY (MAE FOCUS)
# ──────────────────────────────────────────────────────────────────────────────
ax1 = fig.add_subplot(gs[0, 0])
ax1.set_facecolor('white')
models = ['Prev-Week Persistence\n(Lag-7d Baseline)', 'Train Schedule Mean\n(Strongest Baseline)', 'Marina Sentinel ML\n(60-Min Ex-Ante)']
mae_vals = [51.16, 50.24, 39.35]
wape_vals = [23.72, 23.30, 18.25]

x = np.arange(len(models))
width = 0.36

b1 = ax1.bar(x - width/2, mae_vals, width, label='MAE (Passengers)', color=['#CBD5E1', '#94A3B8', TEAL], edgecolor='none', zorder=3)
b2 = ax1.bar(x + width/2, wape_vals, width, label='WAPE (%)', color=['#E2E8F0', '#CBD5E1', GREEN], edgecolor='none', zorder=3)

ax1.set_title("1. Forecast Error vs Baselines [MEASURED]", fontsize=13, fontweight='bold', pad=12, color=NAVY)
ax1.set_ylabel("Error Metric", fontsize=11, fontweight='semibold', color=NAVY)
ax1.set_xticks(x)
ax1.set_xticklabels(models, fontsize=9.5, fontweight='medium')
ax1.set_ylim(0, 68)
ax1.legend(loc='upper right', frameon=True, facecolor='white', framealpha=0.9)
ax1.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)

for bar in b1:
    h = bar.get_height()
    ax1.annotate(f"{h:.2f}", xy=(bar.get_x() + bar.get_width()/2, h),
                 xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9.5, fontweight='bold', color=NAVY)
for bar in b2:
    h = bar.get_height()
    ax1.annotate(f"{h:.1f}%", xy=(bar.get_x() + bar.get_width()/2, h),
                 xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9.5, fontweight='bold', color=NAVY)

ax1.text(0.5, 0.86, "21.7% MAE Error Reduction vs Schedule Baseline", transform=ax1.transAxes,
         ha='center', fontsize=9.5, fontweight='bold', color='#065F46',
         bbox=dict(boxstyle='round,pad=0.4', facecolor='#D1FAE5', edgecolor='#10B981', lw=1.2))

# ──────────────────────────────────────────────────────────────────────────────
# SUBPLOT 2: OVERCROWDING CLASSIFICATION AT 60-MIN LEAD TIME
# ──────────────────────────────────────────────────────────────────────────────
ax2 = fig.add_subplot(gs[0, 1])
ax2.set_facecolor('white')
metrics_clf = ['ROC-AUC\nDiscrimination', 'PR-AUC\n(Precision-Recall)', 'Early Capture\nRecall Rate', 'Full Test WAPE\n(Uncertainty)']
scores_clf = [91.78, 78.16, 88.60, 18.25]
colors_clf = ['#3B82F6', '#8B5CF6', '#10B981', '#06B6D4']

x2 = np.arange(len(metrics_clf))
bars2 = ax2.bar(x2, scores_clf, color=colors_clf, width=0.52, zorder=3)
ax2.set_title("2. Alerting Quality at 60-Min Horizon [MEASURED]", fontsize=13, fontweight='bold', pad=12, color=NAVY)
ax2.set_ylabel("Score (%)", fontsize=11, fontweight='semibold', color=NAVY)
ax2.set_ylim(0, 108)
ax2.set_xticks(x2)
ax2.set_xticklabels(metrics_clf, fontsize=9.5, fontweight='medium')
ax2.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)

for bar in bars2:
    h = bar.get_height()
    ax2.annotate(f"{h:.2f}%" if h < 90 and h != 18.25 else (f"{h:.1f}%" if h != 18.25 else f"{h:.2f}%"), 
                 xy=(bar.get_x() + bar.get_width()/2, h),
                 xytext=(0, 4), textcoords="offset points", ha='center', va='bottom', fontsize=10.5, fontweight='bold', color=NAVY)

ax2.text(0.5, 0.86, "88.6% Capture: Catches ~9 in 10 Overcrowded Slots", transform=ax2.transAxes,
         ha='center', fontsize=9.5, fontweight='bold', color='#1E40AF',
         bbox=dict(boxstyle='round,pad=0.4', facecolor='#DBEAFE', edgecolor='#3B82F6', lw=1.2))

# ──────────────────────────────────────────────────────────────────────────────
# SUBPLOT 3: DISPATCH OPERATOR QUEUE PRECISION
# ──────────────────────────────────────────────────────────────────────────────
ax3 = fig.add_subplot(gs[0, 2])
ax3.set_facecolor('white')
queues = ['Priority Dispatch Queue\n(50 Alerts/Day Capped)', 'Probability-Ranked Queue\n(Top 50 Alerts/Day)']
prec_scores = [97.20, 98.80]
prec_colors = ['#0EA5E9', '#10B981']

xq = np.arange(len(queues))
wq = 0.42

bq = ax3.bar(xq, prec_scores, wq, color=prec_colors, edgecolor='none', zorder=3)
ax3.set_title("3. Dispatch Precision on Capped 50/Day Queue [MEASURED]", fontsize=13, fontweight='bold', pad=12, color=NAVY)
ax3.set_ylabel("Strict Precision (DCR > 1.0)", fontsize=11, fontweight='semibold', color=NAVY)
ax3.set_xticks(xq)
ax3.set_xticklabels(queues, fontsize=9.5, fontweight='medium')
ax3.set_ylim(80, 106)
ax3.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)

for bar in bq:
    h = bar.get_height()
    ax3.annotate(f"{h:.2f}%", xy=(bar.get_x() + bar.get_width()/2, h),
                 xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=11, fontweight='bold', color=NAVY)

ax3.text(0.5, 0.86, "97.20% Precision (243 / 250 True Overcrowded)", transform=ax3.transAxes,
         ha='center', fontsize=9.5, fontweight='bold', color='#065F46',
         bbox=dict(boxstyle='round,pad=0.4', facecolor='#D1FAE5', edgecolor='#10B981', lw=1.2))

# ──────────────────────────────────────────────────────────────────────────────
# SUBPLOT 4: CHRONIC VS DYNAMIC DEMAND GENERALIZATION
# ──────────────────────────────────────────────────────────────────────────────
ax4 = fig.add_subplot(gs[1, 0])
ax4.set_facecolor('white')
cats = ['Chronic Routes\n(≥70% Historic Overcrowd)', 'Non-Chronic Routes\n(<70% Dynamic Surges)']
prec_cat = [99.29, 98.18]
share_cat = [56.0, 44.0]

xc = np.arange(len(cats))
wc = 0.35

bc1 = ax4.bar(xc - wc/2, prec_cat, wc, label='Model Precision (%)', color=['#0284C7', '#0EA5E9'], zorder=3)
bc2 = ax4.bar(xc + wc/2, share_cat, wc, label='Share of Top-50 Queue (%)', color=['#F59E0B', '#FBBF24'], zorder=3)

ax4.set_title("4. Robustness: Chronic vs Dynamic Surges [MEASURED]", fontsize=13, fontweight='bold', pad=12, color=NAVY)
ax4.set_ylabel("Percentage (%)", fontsize=11, fontweight='semibold', color=NAVY)
ax4.set_xticks(xc)
ax4.set_xticklabels(cats, fontsize=9.5, fontweight='medium')
ax4.set_ylim(0, 115)
ax4.legend(loc='upper right', frameon=True, facecolor='white', framealpha=0.9)
ax4.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)

for bar in bc1:
    h = bar.get_height()
    ax4.annotate(f"{h:.1f}%", xy=(bar.get_x() + bar.get_width()/2, h),
                 xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=10, fontweight='bold', color='#0369A1')
for bar in bc2:
    h = bar.get_height()
    ax4.annotate(f"{h:.1f}%", xy=(bar.get_x() + bar.get_width()/2, h),
                 xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=10, fontweight='bold', color='#B45309')

ax4.text(0.5, 0.86, "44% of Alerts are Non-Chronic Dynamic Surges", transform=ax4.transAxes,
         ha='center', fontsize=9.5, fontweight='bold', color='#92400E',
         bbox=dict(boxstyle='round,pad=0.4', facecolor='#FEF3C7', edgecolor='#F59E0B', lw=1.2))

# ──────────────────────────────────────────────────────────────────────────────
# SUBPLOT 5: DEPOT REBALANCING (SINGLE-ALLOCATION RE-RUN)
# ──────────────────────────────────────────────────────────────────────────────
ax5 = fig.add_subplot(gs[1, 1])
ax5.set_facecolor('white')

metrics_rebal = ['Overcrowded Receivers\n(Pre-Transfer Mean)', 'Overcrowded Receivers\n(Post-Transfer Mean)',
                 'Donors\n(Pre-Transfer Mean)', 'Donors\n(Post-Transfer Mean)']
dcr_vals = [1.43, 1.11, 0.35, 0.49]
dcr_colors = [CORAL, '#F97316', '#38BDF8', '#0284C7']

x5 = np.arange(len(metrics_rebal))
bars5 = ax5.bar(x5, dcr_vals, color=dcr_colors, width=0.52, zorder=3)
ax5.axhline(1.0, color='#64748B', linestyle='--', lw=1.5, label='Rated Capacity (DCR = 1.0x)', zorder=2)
ax5.axhline(0.8, color='#0284C7', linestyle=':', lw=1.2, label='Donor Safety Cap (DCR ≤ 0.80x)', zorder=2)

ax5.set_title("5. Single-Allocation Rebalancing [SIMULATED]", fontsize=13, fontweight='bold', pad=12, color=NAVY)
ax5.set_ylabel("Demand-to-Capacity Ratio (DCR)", fontsize=11, fontweight='semibold', color=NAVY)
ax5.set_ylim(0, 1.75)
ax5.set_xticks(x5)
ax5.set_xticklabels(metrics_rebal, fontsize=8.5, fontweight='medium')
ax5.legend(loc='upper right', frameon=True, facecolor='white', framealpha=0.9, fontsize=8.5)
ax5.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)

for bar in bars5:
    h = bar.get_height()
    ax5.annotate(f"{h:.2f}x", xy=(bar.get_x() + bar.get_width()/2, h),
                 xytext=(0, 4), textcoords="offset points", ha='center', va='bottom', fontsize=10.5, fontweight='bold', color=NAVY)

ax5.text(0.5, 0.86, "212 Single-Allocation Pairs | 49.1% Normalized", transform=ax5.transAxes,
         ha='center', fontsize=9.5, fontweight='bold', color='#1E40AF',
         bbox=dict(boxstyle='round,pad=0.4', facecolor='#DBEAFE', edgecolor='#3B82F6', lw=1.2))

# ──────────────────────────────────────────────────────────────────────────────
# SUBPLOT 6: PRODUCTION SCALE & SERVING LATENCY
# ──────────────────────────────────────────────────────────────────────────────
ax6 = fig.add_subplot(gs[1, 2])
ax6.set_facecolor('white')
ax6.axis('off')

ax6.set_title("6. Production Readiness & Scale [MEASURED]", fontsize=13, fontweight='bold', pad=12, color=NAVY)

kpis = [
    ("67,800,000", "Total Real Tickets Processed", "31 Calendar Days in March 2026", "#0284C7"),
    ("705 Routes / 16 Depots", "Citywide Fleet Network Coverage", "Metropolitan Transit Scope", "#4F46E5"),
    ("138 Milliseconds", "Full-City Batch Scoring Latency", "All 705 routes scored in parallel", "#059669"),
    ("< 250 MB", "Total Runtime RAM Footprint", "Runs seamlessly on edge commodity CPU", "#D97706"),
    ("128,809 Pax (10.27%)", "Excess Riders Addressed", "Captured by top 50 priority actions/day", "#DC2626")
]

y_pos = 0.84
for val, label, sub, color in kpis:
    rect = patches.FancyBboxPatch((0.02, y_pos - 0.13), 0.96, 0.14, boxstyle="round,pad=0.02",
                                  facecolor=LIGHT_BG, edgecolor='#E2E8F0', lw=1.2, transform=ax6.transAxes)
    ax6.add_patch(rect)
    
    bar = patches.FancyBboxPatch((0.02, y_pos - 0.13), 0.02, 0.14, boxstyle="round,pad=0.01",
                                 facecolor=color, edgecolor='none', transform=ax6.transAxes)
    ax6.add_patch(bar)
    
    ax6.text(0.07, y_pos - 0.03, val, transform=ax6.transAxes, fontsize=11.5, fontweight='bold', color=color)
    ax6.text(0.07, y_pos - 0.08, f"{label}  •  {sub}", transform=ax6.transAxes, fontsize=8.2, color='#475569', fontweight='medium')
    
    y_pos -= 0.17

out_path = OUT_CHARTS / "jury_model_metrics_scorecard.png"
plt.savefig(out_path, dpi=300, bbox_inches='tight')
plt.close()
print(f"Reconciled Master Jury Scorecard saved to: {out_path}")
