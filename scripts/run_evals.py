"""Run the retrieval + grading evaluation suites.

Offline by default (safe in CI, no keys needed):

    uv run python scripts/run_evals.py

Upload as a LangSmith experiment (requires a valid LANGSMITH_API_KEY):

    uv run python scripts/run_evals.py --upload
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.evaluation import run_langsmith, run_offline  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upload", action="store_true", help="Upload results to LangSmith")
    parser.add_argument("--suite", action="append", help="Limit to suite name(s): retrieval, grading")
    args = parser.parse_args()

    if args.upload:
        report = run_langsmith(args.suite, upload=True)
    else:
        report = run_offline(args.suite)
    print(json.dumps(report, indent=2))
    return 0 if report.get("passed", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
