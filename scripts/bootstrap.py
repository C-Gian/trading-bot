import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
policy = json.loads(
    (R / "governance/NUMERICAL_DEPENDENCY_IDENTITY_V1.json").read_text(encoding="utf-8")
)
uv = shutil.which("uv") or os.environ.get("UV_EXE") or str(R / ".tools" / "uv" / "uv.exe")
version = subprocess.run([uv, "--version"], check=True, capture_output=True, text=True).stdout
if not version.startswith(f"uv {policy['uv_version']} "):
    raise SystemExit(f"uv version mismatch: {version.strip()}, governed=uv {policy['uv_version']}")
subprocess.run(
    [uv, "sync", "--frozen", "--python", sys.executable, "--extra", "dev"],
    cwd=R,
    check=True,
)
subprocess.run(["npm", "ci"], cwd=R / "frontend", check=True, shell=sys.platform == "win32")
