"""Create timestamped local state backups with retention and restore-drill support."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.settings import get_settings
from scripts.export_state import write_export
from scripts.restore_state import restore_payload


def _backup_name() -> str:
    return f"state_backup_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"


def _prune_backups(output_dir: Path, retention_days: int, min_keep: int) -> list[str]:
    backups = sorted(output_dir.glob("state_backup_*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if retention_days <= 0:
        return []
    cutoff = time.time() - (retention_days * 24 * 60 * 60)
    removed: list[str] = []
    for index, path in enumerate(backups):
        if index < min_keep:
            continue
        if path.stat().st_mtime < cutoff:
            path.unlink()
            removed.append(str(path))
    return removed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=None, help="Backup directory. Defaults to data/backups.")
    parser.add_argument("--retention-days", type=int, default=30, help="Delete backups older than this many days.")
    parser.add_argument("--min-keep", type=int, default=3, help="Always keep at least this many newest backups.")
    parser.add_argument("--restore-drill", action="store_true", help="Restore the new backup into a temp dir to validate it.")
    args = parser.parse_args()

    settings = get_settings()
    output_dir = Path(args.output_dir) if args.output_dir else settings.data_dir / "backups"
    output_dir.mkdir(parents=True, exist_ok=True)
    backup_path = write_export(output_dir / _backup_name())
    payload = json.loads(backup_path.read_text(encoding="utf-8"))
    drill_summary = None
    if args.restore_drill:
        with tempfile.TemporaryDirectory(prefix="tutor_restore_drill_") as tmp_dir:
            drill_summary = restore_payload(payload, data_dir=Path(tmp_dir), dry_run=False)
    removed = _prune_backups(output_dir, args.retention_days, max(0, args.min_keep))
    print(
        json.dumps(
            {
                "backup": str(backup_path),
                "retention_days": args.retention_days,
                "removed": removed,
                "restore_drill": drill_summary,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
