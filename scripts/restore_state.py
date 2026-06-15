"""Restore local learner state from an exported backup JSON."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import AUDIT_LOG_PATH, EXERCISE_STORE_PATH, LEARNER_STORE_PATH
from backend.models import utc_now
from backend.settings import get_settings


def _validate_payload(payload: dict) -> None:
    if not isinstance(payload.get("learners", {}), dict):
        raise ValueError("Backup payload must contain a learners object")
    if not isinstance(payload.get("exercises", {}), dict):
        raise ValueError("Backup payload must contain an exercises object")
    if not isinstance(payload.get("audit_events", []), list):
        raise ValueError("Backup payload must contain an audit_events list")


def _target_paths(data_dir: Path | None = None) -> tuple[Path, Path, Path]:
    if data_dir is None:
        return LEARNER_STORE_PATH, EXERCISE_STORE_PATH, AUDIT_LOG_PATH
    return data_dir / "learners.json", data_dir / "exercises.json", data_dir / "audit_events.jsonl"


def _backup_existing(paths: tuple[Path, Path, Path], data_dir: Path) -> Path:
    stamp = utc_now().replace(":", "").replace("+", "Z")
    backup_dir = data_dir / f"restore_pre_{stamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    for path in paths:
        if path.exists():
            shutil.copy2(path, backup_dir / path.name)
    return backup_dir


def restore_payload(payload: dict, *, data_dir: Path | None = None, dry_run: bool = False) -> dict:
    _validate_payload(payload)
    settings = get_settings()
    target_dir = data_dir or settings.data_dir
    paths = _target_paths(data_dir)
    learner_path, exercise_path, audit_path = paths
    summary = {
        "learners": len(payload.get("learners", {})),
        "exercises": len(payload.get("exercises", {})),
        "audit_events": len(payload.get("audit_events", [])),
        "data_dir": str(target_dir),
    }
    if dry_run:
        return summary
    target_dir.mkdir(parents=True, exist_ok=True)
    backup_dir = _backup_existing(paths, target_dir)
    learner_path.write_text(json.dumps({"learners": payload.get("learners", {})}, indent=2) + "\n", encoding="utf-8")
    exercise_path.write_text(json.dumps({"exercises": payload.get("exercises", {})}, indent=2) + "\n", encoding="utf-8")
    with audit_path.open("w", encoding="utf-8") as handle:
        for event in payload.get("audit_events", []):
            handle.write(json.dumps(event, sort_keys=True) + "\n")
    return {**summary, "pre_restore_backup": str(backup_dir)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Backup JSON path produced by scripts/export_state.py.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and summarize without writing state.")
    parser.add_argument("--data-dir", default=None, help="Optional restore target directory.")
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    data_dir = Path(args.data_dir).resolve() if args.data_dir else None
    summary = restore_payload(payload, data_dir=data_dir, dry_run=args.dry_run)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
