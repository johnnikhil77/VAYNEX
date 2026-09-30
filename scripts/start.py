"""Container entrypoint: migrate -> (optionally) seed -> serve.

Written in Python (not shell) so it is immune to CRLF line-ending issues when
the repository is checked out on Windows.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> None:
    print(f"[vaynex] $ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def truthy(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
    if truthy("RUN_MIGRATIONS", "true"):
        run([sys.executable, "-m", "alembic", "upgrade", "head"])
    if truthy("SEED_DEMO_DATA", "false"):
        run([sys.executable, "scripts/seed_demo.py"])
    host = os.getenv("HOST", "0.0.0.0")
    port = os.getenv("PORT", "8000")
    os.chdir(ROOT)
    os.execvp(
        sys.executable,
        [
            sys.executable,
            "-m",
            "uvicorn",
            "apps.api.main:app",
            "--host",
            host,
            "--port",
            port,
            "--no-access-log",
            "--proxy-headers",
        ],
    )


if __name__ == "__main__":
    main()
