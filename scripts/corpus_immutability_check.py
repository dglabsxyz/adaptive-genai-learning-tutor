"""Verify runtime state is outside the read-only genai_research corpus."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import CORPUS_DIR, DATA_DIR
from backend.source_governance import corpus_file_inventory


def main() -> None:
    inventory = corpus_file_inventory()
    if not inventory:
        raise AssertionError("corpus inventory is empty")
    if not all(item["path"].startswith("genai_research/") for item in inventory):
        raise AssertionError()
    if DATA_DIR == CORPUS_DIR or CORPUS_DIR in DATA_DIR.parents:
        raise AssertionError(
            "TUTOR_DATA_DIR must not point inside the corpus"
        )
    print(f"corpus immutable check ok ({len(inventory)} files)")


if __name__ == "__main__":
    main()
