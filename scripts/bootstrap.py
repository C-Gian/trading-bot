import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
if importlib.util.find_spec("pip"):
    subprocess.run([sys.executable, "-m", "pip", "install", "-e", ".[dev]"], cwd=R, check=True)
else:
    uv = shutil.which("uv") or os.environ.get("UV_EXE") or str(R / ".tools" / "uv" / "uv.exe")
    subprocess.run([uv, "sync", "--python", sys.executable, "--extra", "dev"], cwd=R, check=True)
subprocess.run(["npm", "ci"], cwd=R / "frontend", check=True, shell=sys.platform == "win32")
