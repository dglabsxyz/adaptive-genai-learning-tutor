from uuid import uuid4

from fastapi.testclient import TestClient

from backend.audit import read_audit_events
from backend.main import app
from backend.source_governance import citation_audit, retrieval_evaluation_report, source_quality_report
from backend.tools import tutor_assess_skills_impl, tutor_get_next_exercise_impl


client = TestClient(app)


def _headers(user_id: str, role: str = "learner", tenant_id: str = "tenant-test") -> dict[str, str]:
    return {
        "x-tutor-user-id": user_id,
        "x-tutor-role": role,
        "x-tutor-tenant-id": tenant_id,
    }


def test_api_enforces_learner_boundary():
    learner_id = f"learner-{uuid4()}"
    other_id = f"other-{uuid4()}"

    ok = client.get(f"/progress/{learner_id}", headers=_headers(learner_id))
    denied = client.get(f"/progress/{other_id}", headers=_headers(learner_id))

    assert ok.status_code == 200
    assert denied.status_code == 403
    assert "request_id" in denied.json()


def test_role_gated_enterprise_endpoints():
    learner_id = f"learner-{uuid4()}"

    educator = client.get("/cohort/progress", headers=_headers(learner_id, role="educator"))
    educator_admin_denied = client.get("/admin/integrations", headers=_headers(learner_id, role="educator"))
    admin = client.get("/admin/integrations", headers=_headers(learner_id, role="admin"))

    assert educator.status_code == 200
    assert educator_admin_denied.status_code == 403
    assert admin.status_code == 200
    assert admin.json()["repository_backend"] in {"json", "supabase"}


def test_json_repository_scopes_same_learner_by_tenant():
    learner_id = f"shared-{uuid4()}"

    tutor_assess_skills_impl(learner_id, "I want to learn RAG", tenant_id="tenant-a")
    tutor_assess_skills_impl(learner_id, "I want to learn MCP", tenant_id="tenant-b")

    a = client.get(f"/progress/{learner_id}", headers=_headers(learner_id, tenant_id="tenant-a")).json()
    b = client.get(f"/progress/{learner_id}", headers=_headers(learner_id, tenant_id="tenant-b")).json()

    assert "I want to learn RAG" in a["goals"]
    assert "I want to learn MCP" in b["goals"]
    assert "I want to learn MCP" not in a["goals"]


def test_audit_events_are_appended_for_enterprise_actions():
    learner_id = f"audit-{uuid4()}"
    tenant_id = "tenant-audit"

    tutor_get_next_exercise_impl(learner_id, skill="RAG", tenant_id=tenant_id)
    events = read_audit_events(tenant_id=tenant_id, learner_id=learner_id, event_type="exercise_created", limit=5)

    assert events
    assert events[-1]["metadata"]["skill"] == "RAG"


def test_source_governance_reports_and_citation_audit():
    learner_id = f"source-{uuid4()}"
    payload = tutor_assess_skills_impl(learner_id, "I want to learn AI agents")
    quality = source_quality_report()
    audit = citation_audit(payload)
    evaluation = retrieval_evaluation_report(["RAG", "MCP"])

    assert quality["document_count"] >= 150
    assert audit["has_source_refs"] is True
    assert all(item["has_topic_or_course"] for item in evaluation["results"])
