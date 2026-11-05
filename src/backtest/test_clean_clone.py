"""
TransitIQ: Clean Checkout & Standalone Reproduction Test
1. Verifies git staging and commits clean repository files.
2. Exports a 100% clean, isolated checkout via `git checkout-index`.
3. Asserts zero raw data files (data/, ETM/, *.parquet, *.bz2) exist in the export.
4. Executes src/api_server in DEMO_MODE inside the clean directory.
"""
import os
import sys
import tempfile
import subprocess
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
temp_export_dir = Path(tempfile.gettempdir()) / "transitiq_clean_export_eval"

if temp_export_dir.exists():
    shutil.rmtree(temp_export_dir, ignore_errors=True)
temp_export_dir.mkdir(parents=True, exist_ok=True)

print("Step 1: Staging tracked files in Git...")
subprocess.run(["git", "add", "."], cwd=ROOT, check=True)

# Ensure git user config
subprocess.run(["git", "config", "user.name", "TransitIQ Submitter"], cwd=ROOT, check=True)
subprocess.run(["git", "config", "user.email", "submitter@transitiq.local"], cwd=ROOT, check=True)

try:
    subprocess.run(["git", "commit", "-m", "feat: TransitIQ complete submission release"], cwd=ROOT, check=True)
    print("Git commit created.")
except subprocess.CalledProcessError:
    print("Working tree already committed.")

print(f"\nStep 2: Exporting clean checkout into {temp_export_dir} ...")
prefix = str(temp_export_dir) + "\\"
subprocess.run(["git", "checkout-index", "-a", "-f", f"--prefix={prefix}"], cwd=ROOT, check=True)
print("Clean checkout exported successfully.")

print("\nStep 3: Verifying zero raw data or large parquets in clean export...")
assert not (temp_export_dir / "data").exists(), "Error: data/ directory leaked into git!"
assert not (temp_export_dir / "ETM").exists(), "Error: ETM/ directory leaked into git!"
for p in temp_export_dir.rglob("*.parquet"):
    raise AssertionError(f"Leaked parquet file found: {p}")
for p in temp_export_dir.rglob("*.csv.bz2"):
    raise AssertionError(f"Leaked bz2 file found: {p}")
print("Verified: Zero raw data or large files exist in clean checkout.")

print("\nStep 4: Testing DEMO_MODE standalone execution in isolated directory...")
env = os.environ.copy()
env["DEMO_MODE"] = "1"

code = (
    "import os\n"
    "os.environ['DEMO_MODE'] = '1'\n"
    "from src.api_server import get_kpis, get_control_room_alerts, get_rebalance_pairs, get_routes\n"
    "k = get_kpis()\n"
    "a = get_control_room_alerts(limit=5)\n"
    "p = get_rebalance_pairs(limit=5)\n"
    "r = get_routes()\n"
    "mae_red = k['forecast_accuracy']['mae_reduction_pct_vs_strongest_baseline']\n"
    "q_prec = k['operational_queue_precision']['strict_precision_percent']\n"
    "print(f'SUCCESS: Standalone Clone Verified!')\n"
    "print(f'  - Forecast MAE Reduction: {mae_red}%')\n"
    "print(f'  - Priority Queue Precision: {q_prec}%')\n"
    "print(f'  - Alert Cards Loaded: {len(a)} (First: Route {a[0][\"route_id\"]})')\n"
    "print(f'  - Rebalance Pairs Loaded: {len(p)} (First: {p[0][\"receiver_route\"]} <- {p[0][\"donor_route\"]})')\n"
    "print(f'  - Total Active Routes: {len(r)}')\n"
)

res = subprocess.run([sys.executable, "-c", code], cwd=str(temp_export_dir), env=env, capture_output=True, text=True, check=True)
print(res.stdout)
print("Clean-Clone & Standalone Reproduction Test PASSED.")
