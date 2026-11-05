"""
Marina Sentinel Full System Backtest Runner
Command: python -m src.backtest.run_all
Runs all phases A through H sequentially and generates all reports.
"""
import sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.backtest.audit_leakage import run_phase_a
from src.backtest.phase_b_to_h_pipeline import run_phases_b_to_h

def main():
    t0 = time.time()
    print("=" * 80)
    print("TRANSIT IQ FULL SYSTEM BACKTEST: ALL PHASES A THROUGH H")
    print("=" * 80)
    
    # 1. Phase A: Leakage Audit
    run_phase_a()
    
    # 2. Phases B to H: Forecasting, Alerts, Anomalies, Headways, Rebalancing, Benchmarks
    run_phases_b_to_h()
    
    elapsed = time.time() - t0
    print("=" * 80)
    print(f"ALL BACKTEST PHASES COMPLETED IN {elapsed:.1f} SECONDS.")
    print("=" * 80)

if __name__ == '__main__':
    main()
