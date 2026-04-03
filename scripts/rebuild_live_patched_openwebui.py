#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_patched_openwebui.py"), "--force"], check=True, cwd=ROOT)
    print("Patched Open WebUI image rebuilt.")
    print("Restart the launcher or run `python launcher.py restart` to redeploy it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
