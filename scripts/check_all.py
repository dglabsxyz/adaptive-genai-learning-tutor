"""Run the local CI-style quality gates."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# tutor-ui is the canonical frontend (the legacy frontend/ folder was retired).
FRONTEND = ROOT / "tutor-ui"

COMMANDS = [
    ["uv", "run", "pytest"],
    ["uv", "run", "python", "scripts/api_contract_smoke.py"],
    ["uv", "run", "python", "scripts/corpus_immutability_check.py"],
    ["uv", "run", "python", "scripts/demo_flow.py"],
    [
        "uv",
        "run",
        "python",
        "scripts/backup_state.py",
        "--restore-drill",
        "--output-dir",
        "data/backups/check_all",
        "--retention-days",
        "1",
        "--min-keep",
        "1",
    ],
    ["uv", "run", "python", "mcp_server/server.py", "--smoke"],
    # Frontend gate: production build must compile (run `npm install` in tutor-ui first).
    ["npm", "run", "build"],
    ["npm", "audit", "--audit-level=high"],
]


def main() -> int:
    for command in COMMANDS:
        cwd = FRONTEND if command[0] == "npm" else ROOT
        print(f"\n$ {' '.join(command)}")
        result = subprocess.run(command, cwd=cwd, check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
