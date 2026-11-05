import os
import sys
import time
import subprocess
import shutil
from pathlib import Path

ROOT = Path(".").resolve()
CHECK_DIR = ROOT / "clean_check"

print("================================================================================")
print("1. CLONING CLEAN REPO: git clone . clean_check")
print("================================================================================")
if CHECK_DIR.exists():
    shutil.rmtree(CHECK_DIR, ignore_errors=True)

clone_res = subprocess.run(["git", "clone", str(ROOT), str(CHECK_DIR)], capture_output=True, text=True)
print(clone_res.stdout)
print(clone_res.stderr)

print("================================================================================")
print("2. GIT LOG & STATUS IN clean_check")
print("================================================================================")
log_res = subprocess.run(["git", "log", "-1", "--oneline"], cwd=str(CHECK_DIR), capture_output=True, text=True)
print(log_res.stdout.strip())
stat_res = subprocess.run(["git", "status"], cwd=str(CHECK_DIR), capture_output=True, text=True)
print(stat_res.stdout.strip())

print("\n================================================================================")
print("3. CREATING VIRTUAL ENVIRONMENT & INSTALLING REQUIREMENTS")
print("================================================================================")
venv_dir = CHECK_DIR / "v"
subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
print("Virtual environment created at clean_check/v.")

venv_python = str(venv_dir / "Scripts" / "python.exe")
venv_pip = str(venv_dir / "Scripts" / "pip.exe")
venv_uvicorn = str(venv_dir / "Scripts" / "uvicorn.exe")

pip_res = subprocess.run([venv_pip, "install", "--no-warn-script-location", "-r", "requirements.txt"], cwd=str(CHECK_DIR), capture_output=True, text=True)
print("Pip install completed successfully.")
for line in pip_res.stdout.strip().split("\n")[-5:]:
    print(" ", line)

print("\n================================================================================")
print("4. LAUNCHING UVICORN (WITHOUT DEMO_MODE ENV VAR SET)")
print("================================================================================")
# Strip DEMO_MODE from environment completely
clean_env = os.environ.copy()
if "DEMO_MODE" in clean_env:
    del clean_env["DEMO_MODE"]

proc = subprocess.Popen(
    [venv_python, "-m", "uvicorn", "src.api_server:app", "--host", "127.0.0.1", "--port", "8000"],
    cwd=str(CHECK_DIR),
    env=clean_env,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

time.sleep(3)
if proc.poll() is not None:
    stdout, stderr = proc.communicate()
    print("Server failed to start!")
    print("STDOUT:", stdout.decode())
    print("STDERR:", stderr.decode())
    sys.exit(1)

print("Uvicorn server running on http://127.0.0.1:8000 (DEMO_MODE defaulted to True).")

print("\n================================================================================")
print("5. CURL /api/kpis WITH ORIGIN HEADER")
print("================================================================================")
curl_cmd = [
    "curl.exe", "-i", "-s",
    "-H", "Origin: http://localhost:3000",
    "http://127.0.0.1:8000/api/kpis"
]
curl_res = subprocess.run(curl_cmd, capture_output=True, text=True)
print(curl_res.stdout)

print("Terminating server...")
proc.terminate()
proc.wait(timeout=5)
print("Server stopped cleanly.")

