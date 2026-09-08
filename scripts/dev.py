import subprocess
import sys
import time
import urllib.request
from pathlib import Path

R = Path(__file__).resolve().parents[1]
procs = []
try:
    procs = [
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            cwd=R / "backend",
        ),
        subprocess.Popen(["npm", "run", "dev"], cwd=R / "frontend", shell=sys.platform == "win32"),
    ]
    for _ in range(30):
        try:
            urllib.request.urlopen("http://127.0.0.1:8000/api/v1/system/health")
            break
        except Exception:
            time.sleep(0.5)
    print("Trading Bot: http://127.0.0.1:5173")
    [p.wait() for p in procs]
finally:
    [p.terminate() for p in procs if p.poll() is None]
