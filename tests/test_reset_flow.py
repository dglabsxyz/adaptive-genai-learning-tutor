"""Tests for the real, audited destructive reset (backend + API).

The deep-agent tutor exposes consequential writes behind its own human-in-the-loop
gate (``commit_progress``); the graph-level reset interrupt is gone. The reset
*function* and the guarded ``/progress/{id}/reset`` endpoint remain and are tested
here directly (no LLM required).
"""

from uuid import uuid4

from fastapi.testclient import TestClient

from backend.audit import read_audit_events
from backend.main import app
from backend.stores import reset_learner_progress
from backend.tools import tutor_submit_answer_impl, tutor_get_next_exercise_impl, tutor_view_progress_impl


client = TestClient(app)


def _headers(user_id: str, role: str = "learner", tenant_id: str = "tenant-reset") -> dict[str, str]:
    return {"x-tutor-user-id": user_id, "x-tutor-role": role, "x-tutor-tenant-id": tenant_id}


def _build_some_progress(learner_id: str, tenant_id: str) -> None:
    ex = tutor_get_next_exercise_impl(learner_id, skill="RAG", exercise_type="multiple_choice", tenant_id=tenant_id)
    tutor_submit_answer_impl(
        learner_id,
        "B. retrieve local corpus records, cite sources, keep unknown metadata unknown",
        exercise_id=ex["exercise"]["id"],
        tenant_id=tenant_id,
    )


def test_reset_function_clears_progress_and_audits():
    learner_id = f"reset-fn-{uuid4()}"
    tenant_id = "tenant-reset"
    _build_some_progress(learner_id, tenant_id)

    before = tutor_view_progress_impl(learner_id=learner_id, tenant_id=tenant_id)
    assert any(entry["attempts"] > 0 for entry in before["progress"].values())

    result = reset_learner_progress(learner_id, tenant_id=tenant_id)
    after = tutor_view_progress_impl(learner_id=learner_id, tenant_id=tenant_id)

    assert result["reset"] is True
    assert all(entry["attempts"] == 0 for entry in after["progress"].values())
    assert after["active_exercise_id"] is None
    events = read_audit_events(tenant_id=tenant_id, learner_id=learner_id, event_type="progress_reset", limit=5)
    assert events and events[-1]["metadata"]["scope"] == "all"


def test_reset_endpoint_requires_confirm_and_enforces_boundary():
    learner_id = f"reset-api-{uuid4()}"
    other_id = f"other-{uuid4()}"

    missing_confirm = client.post(f"/progress/{learner_id}/reset", json={}, headers=_headers(learner_id))
    assert missing_confirm.status_code == 400

    cross = client.post(f"/progress/{learner_id}/reset", json={"confirm": True}, headers=_headers(other_id))
    assert cross.status_code == 403

    ok = client.post(f"/progress/{learner_id}/reset", json={"confirm": True}, headers=_headers(learner_id))
    assert ok.status_code == 200
    assert ok.json()["reset"] is True
