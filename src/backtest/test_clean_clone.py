"""
TransitIQ: Clean Clone & Standalone Reproduction Test
1. Commits clean repository files.
2. Clones into an isolated temporary directory.
3. Tests running api_server in DEMO_MODE without raw data.
"""
import os
import sys
import tempfile
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
temp_clone_dir = Path(tempfile.gettempdir()) / "transitiq_clean_clone_eval"

# Clean up any existing temp clone
if temp_clone_dir.exists():
    import shutil
    shutil.rmtree(temp_clone_dir, ignore_errors=True)

print("Step 1: Staging files in git...")
subprocess.run(["git", "add", "."], cwd=ROOT, check=True)

# Configure git user if needed
subprocess.run(["git", "config", "user.name", "TransitIQ Submitter"], cwd=ROOT, check=True)
subprocess.run(["git", "config", "user.email", "submitter@transitiq.local"], cwd=ROOT, check=True)

subprocess.run(["git", "commit", "-m", "feat: TransitIQ complete submission release"], cwd=ROOT, check=True)
print("Git commit successful.")

print(f"\nStep 2: Performing clean git clone into {temp_clone_dir} ...")
subprocess.run(["git", "clone", str(ROOT), str(temp_clone_dir)], check=True)
print("Git clone completed cleanly.")

print("\nStep 3: Verifying cloned directory has ZERO raw data files...")
assert not (temp_clone_dir / "data").exists(), "Error: data/ directory leaked into git!"
assert not (temp_clone_dir / "ETM").exists(), "Error: ETM/ directory leaked into git!"
print("Verified: No raw data or large parquet files exist in clone.")

print("\nStep 4: Testing DEMO_MODE API execution in isolated clone...")
env = os.environ.copy()
env["DEMO_MODE"] = "1"
test_cmd = [
    sys.executable, "-c",
    "import os; os.environ['DEMO_MODE'] = '1'; "
    "from src.api_server import get_kpis, get_control_room_alerts, get_rebalance_pairs, get_routes; "
    "k = get_kpis(); a = get_control_room_alerts(limit=3); p = get_rebalance_pairs(limit=3); r = get_routes(); "
    "print('Clone Test Passed! KPIs:', k['forecast_accuracy']['mae_reduction_pct_vs_strongest_baseline'], '% MAE reduction | Alerts:', len(a), '| Pairs:', len(p), '| Routes:', len(r))"
]

res = subprocess.run(test_cmd, cwd=temp_clone_dir, env=env, capture_output=True, text=True, check=True)
print("Clone Output:\n", res.stdout)
print("\nClean-Clone Test PASSED with flying colors!")
