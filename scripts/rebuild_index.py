"""Rebuild the local sparse vector index and print corpus/index metadata."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.dependencies import get_vector_index
from backend.source_governance import corpus_version_metadata, index_status


def main() -> None:
    get_vector_index(rebuild=True)
    print(json.dumps({"corpus": corpus_version_metadata(), "index": index_status()}, indent=2))


if __name__ == "__main__":
    main()
