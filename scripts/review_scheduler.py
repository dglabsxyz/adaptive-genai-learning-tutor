"""Persist due review status updates for all local learner profiles."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.stores import learner_store


def main() -> None:
    count = 0
    for profile in learner_store.list_profiles():
        refreshed = learner_store.get(profile.learner_id, tenant_id=profile.tenant_id)
        learner_store.save(refreshed, tenant_id=profile.tenant_id)
        count += 1
    print(f"review scheduler refreshed {count} learner profiles")


if __name__ == "__main__":
    main()
