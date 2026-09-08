import subprocess
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, "-m", "pip", "install", "-e", ".[dev]"], cwd=R, check=True)
subprocess.run(["npm", "install"], cwd=R / "frontend", check=True, shell=sys.platform == "win32")
