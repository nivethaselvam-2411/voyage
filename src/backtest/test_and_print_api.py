import os
import sys
import json
import subprocess

# Ensure repo root is on sys.path
sys.path.insert(0, os.path.abspath("."))
# Ensure DEMO_MODE is set
os.environ["DEMO_MODE"] = "1"

from fastapi.testclient import TestClient
from src.api_server import app

client = TestClient(app)

print("="*80)
print("FASTAPI TESTCLIENT AUDIT (DEMO_MODE=1)")
print("="*80)

endpoints = [
    ("/", {}),
    ("/openapi.json", {}),
    ("/api/kpis", {}),
    ("/api/control-room-alerts?limit=2", {}),
    ("/api/rebalance-pairs?limit=2", {}),
    ("/api/routes?limit=2", {}),
    ("/api/dashboard", {})
]

for url, _ in endpoints:
    res = client.get(url)
    cors = res.headers.get("access-control-allow-origin", "Not Found")
    print(f"\n--- GET {url} ---")
    print(f"Status: {res.status_code}")
    print(f"Access-Control-Allow-Origin: {cors}")
    try:
        data = res.json()
        if isinstance(data, list):
            sample = data[:2]
            print(f"Items Returned: {len(data)}, Showing First 2:")
            print(json.dumps(sample, indent=2))
        elif isinstance(data, dict):
            # If dict contains lists, trim them
            trimmed = {}
            for k, v in data.items():
                if isinstance(v, list):
                    trimmed[k] = v[:2]
                elif isinstance(v, dict):
                    trimmed[k] = dict(list(v.items())[:3])
                else:
                    trimmed[k] = v
            print(json.dumps(trimmed, indent=2))
    except Exception as e:
        print(res.text[:300])

print("\n" + "="*80)
print("GIT OBJECT METRICS & REPO SIZE AUDIT")
print("="*80)
git_count = subprocess.run(["git", "count-objects", "-vH"], capture_output=True, text=True)
print(git_count.stdout)

print("\n--- Top 10 Largest Tracked Files in Repo ---")
git_ls = subprocess.run(["git", "ls-tree", "-r", "-l", "HEAD"], capture_output=True, text=True)
files = []
for line in git_ls.stdout.strip().split("\n"):
    parts = line.split()
    if len(parts) >= 5:
        size = parts[3]
        path = parts[4]
        try:
            files.append((int(size), path))
        except:
            pass

files.sort(key=lambda x: x[0], reverse=True)
for sz, path in files[:10]:
    print(f"{sz / (1024*1024):8.3f} MB  {path}")
