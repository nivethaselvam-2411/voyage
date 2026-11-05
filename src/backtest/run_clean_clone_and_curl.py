import os
import sys
import time
import subprocess
import shutil
from pathlib import Path

ROOT = Path(".").resolve()
TEMP_DIR = Path(os.environ.get("TEMP", "C:/temp")) / "clean_clone_test"

print(f"Creating clean clone at {TEMP_DIR}...")
if TEMP_DIR.exists():
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Export clean tracked files
prefix_path = str(TEMP_DIR).replace("\\", "/") + "/"
subprocess.run(["git", "checkout-index", "-a", "-f", f"--prefix={prefix_path}"], check=True)
print("Clean checkout exported successfully.")

# Verify no raw data exists in clean directory
assert not (TEMP_DIR / "data").exists(), "data/ directory should not exist in clean checkout"
assert not (TEMP_DIR / "ETM").exists(), "ETM/ directory should not exist in clean checkout"
print("Confirmed: Zero raw data in clean checkout.")

# Start uvicorn server in clean clone directory with DEMO_MODE=1
env = os.environ.copy()
env["DEMO_MODE"] = "1"
env["PYTHONPATH"] = str(TEMP_DIR)

print("\nStarting uvicorn server on http://127.0.0.1:8000 in clean directory...")
server_proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "src.api_server:app", "--host", "127.0.0.1", "--port", "8000"],
    cwd=str(TEMP_DIR),
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

time.sleep(3)
if server_proc.poll() is not None:
    stdout, stderr = server_proc.communicate()
    print("Server failed to start!")
    print("STDOUT:", stdout.decode())
    print("STDERR:", stderr.decode())
    sys.exit(1)

print("Uvicorn server is running. Executing curl requests...\n")

endpoints = [
    "/",
    "/openapi.json",
    "/api/kpis",
    "/api/dashboard",
    "/api/routes?limit=2&date=2026-03-27&hour=8",
    "/api/control-room-alerts?limit=2&date=2026-03-27&hour=8",
    "/api/rebalance-pairs?limit=2"
]

try:
    for ep in endpoints:
        url = f"http://127.0.0.1:8000{ep}"
        print("=" * 80)
        print(f"curl -i -H 'Origin: http://localhost:3000' \"{url}\"")
        print("=" * 80)
        curl_cmd = [
            "curl.exe", "-i", "-s",
            "-H", "Origin: http://localhost:3000",
            url
        ]
        res = subprocess.run(curl_cmd, capture_output=True, text=True)
        print(res.stdout)
        if res.stderr:
            print("STDERR:", res.stderr)
finally:
    print("\nTerminating uvicorn server...")
    server_proc.terminate()
    server_proc.wait(timeout=5)
    print("Server stopped cleanly.")

