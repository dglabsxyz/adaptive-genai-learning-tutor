"""Smoke the major API contracts without starting a network server."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.main import app


def main() -> None:
    client = TestClient(app)
    headers = {
        "x-tutor-user-id": "api-smoke-learner",
        "x-tutor-role": "learner",
        "x-tutor-tenant-id": "local",
    }
    diagnostic = client.post(
        "/diagnostic",
        headers=headers,
        json={"learner_id": "api-smoke-learner", "goal": "I want to learn AI agents", "answers": []},
    )
    diagnostic.raise_for_status()
    plan = client.post(
        "/study-plan",
        headers=headers,
        json={"learner_id": "api-smoke-learner", "goal": "I want to learn AI agents"},
    )
    plan.raise_for_status()
    exercise = client.post(
        "/exercise",
        headers=headers,
        json={"learner_id": "api-smoke-learner", "goal": "I want to learn AI agents"},
    )
    exercise.raise_for_status()
    answer = client.post(
        "/answer",
        headers=headers,
        json={
            "learner_id": "api-smoke-learner",
            "exercise_id": exercise.json()["exercise"]["id"],
            "answer": "Retrieve source records, ground with citations, preserve unknowns, and evaluate faithfulness.",
        },
    )
    answer.raise_for_status()
    progress = client.get("/progress/api-smoke-learner", headers=headers)
    progress.raise_for_status()
    denied = client.get("/admin/integrations", headers=headers)
    assert denied.status_code == 403
    admin = client.get(
        "/admin/integrations",
        headers={**headers, "x-tutor-user-id": "admin-local", "x-tutor-role": "admin"},
    )
    admin.raise_for_status()
    print("api contract smoke ok")


if __name__ == "__main__":
    main()
