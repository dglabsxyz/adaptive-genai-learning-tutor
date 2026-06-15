"""Export learner state, exercises, and audit events for backup or review."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.audit import read_audit_events
from backend.config import EXERCISE_STORE_PATH, LEARNER_STORE_PATH
from backend.models import utc_now
from backend.settings import get_settings


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_export_payload() -> dict:
    return {
        "exported_at": utc_now(),
        "learners": _read_json(LEARNER_STORE_PATH).get("learners", {}),
        "exercises": _read_json(EXERCISE_STORE_PATH).get("exercises", {}),
        "audit_events": read_audit_events(limit=10_000),
    }


def write_export(output: Path) -> Path:
    payload = build_export_payload()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=None, help="Output JSON path. Defaults to data/state_export.json.")
    args = parser.parse_args()
    settings = get_settings()
    output = Path(args.output) if args.output else settings.data_dir / "state_export.json"
    print(write_export(output))


if __name__ == "__main__":
    main()
