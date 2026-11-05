"""
TransitIQ: Submission Verification Script (Tasks 8 & 9)
- Stages and commits all files to Git
- Runs git count-objects -vH
- Lists largest 10 files in Git tracking
- Starts uvicorn server in background on test port
- Curls every endpoint, checks Access-Control-Allow-Origin header, and prints first 2 items
"""
import os
import sys
import time
import json
import urllib.request
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# Step 1: Git staging & commit
print("=" * 80)
print("1. GIT STAGING, COMMIT & REPO SIZE AUDIT")
print("=" * 80)

subprocess.run(["git", "add", "."], cwd=ROOT, check=True)
try:
    subprocess.run(["git", "commit", "-m", "chore: prepare project for final submission"], cwd=ROOT, check=True)
except subprocess.CalledProcessError:
    print("Working tree already clean.")

# Git count-objects -vH
print("\n--- git count-objects -vH ---")
res_count = subprocess.run(["git", "count-objects", "-vH"], cwd=ROOT, capture_output=True, text=True, check=True)
print(res_count.stdout)

# Largest 10 files in Git index
print("--- Largest 10 Files in Git Index ---")
res_ls = subprocess.run(["git", "ls-tree", "-r", "-l", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True)
files = []
for line in res_ls.stdout.splitlines():
    parts = line.split()
    if len(parts) >= 5:
        # mode type sha size path
        try:
            sz = int(parts[3])
            path = " ".join(parts[4:])
            files.append((path, sz))
        except ValueError:
            pass

files.sort(key=lambda x: x[1], reverse=True)
for i, (p, sz) in enumerate(files[:10], 1):
    print(f"  {i}. {p}: {sz / (1024*1024):.2f} MB ({sz:,} bytes)")

# Step 2: Test API Server with uvicorn and curl endpoints
print("\n" + "=" * 80)
print("2. UVICORN SERVER & ENDPOINT CURL AUDIT (WITH CORS HEADERS)")
print("=" * 80)

env = os.environ.copy()
env["DEMO_MODE"] = "1"
port = 8765

# Launch uvicorn process
server_proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "src.api_server:app", "--host", "127.0.0.1", "--port", str(port)],
    cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE
)

print(f"Started uvicorn server on port {port} (PID: {server_proc.pid}). Waiting for startup...")
time.sleep(3)

base_url = f"http://127.0.0.1:{port}"
endpoints = [
    "/",
    "/openapi.json",
    "/api/kpis",
    "/api/control-room-alerts?limit=2",
    "/api/rebalance-pairs?limit=2",
    "/api/routes?limit=2",
    "/api/dashboard"
]

try:
    for ep in endpoints:
        url = base_url + ep
        req = urllib.request.Request(url, headers={"Origin": "http://localhost:3000"})
        with urllib.request.urlopen(req, timeout=5) as response:
            status = response.status
            headers = dict(response.headers)
            cors_origin = headers.get("access-control-allow-origin", "MISSING")
            body = response.read().decode("utf-8")
            data = json.loads(body)
            
            print(f"\n[ENDPOINT] {ep}")
            print(f"  * Status: {status} OK")
            print(f"  * Access-Control-Allow-Origin: {cors_origin}")
            
            if isinstance(data, list):
                print(f"  * Response: List of {len(data)} items. First 2 items:")
                for item in data[:2]:
                    print(f"    - {json.dumps(item)[:160]}...")
            elif isinstance(data, dict):
                keys = list(data.keys())
                print(f"  * Response: Dict with {len(keys)} keys: {keys[:6]}")
                # print sample preview
                sample_preview = {k: data[k] for k in keys[:3]}
                print(f"    - Preview: {json.dumps(sample_preview)[:160]}...")
finally:
    print(f"\nTerminating test uvicorn server (PID: {server_proc.pid})...")
    server_proc.terminate()
    server_proc.wait(timeout=3)
    print("Test server stopped cleanly.")
