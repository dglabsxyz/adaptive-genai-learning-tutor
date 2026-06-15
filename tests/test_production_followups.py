from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from langgraph.types import Command

import backend.rate_limit as rate_limit
from backend.corpus import CorpusDocument
from backend.graph import _format_graph_result, _thread_config, build_tutor_graph, run_tutor_turn
from backend.main import app
from backend.pgvector_store import PGVectorIndex
from backend.settings import get_settings
from backend.tools import tutor_get_next_exercise_impl

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_runtime_settings():
    get_settings.cache_clear()
    rate_limit._limiter = None
    yield
    get_settings.cache_clear()
    rate_limit._limiter = None


def _headers(user_id: str, role: str = "learner", tenant_id: str = "tenant-prod") -> dict[str, str]:
    return {
        "x-tutor-user-id": user_id,
        "x-tutor-role": role,
        "x-tutor-tenant-id": tenant_id,
    }


def test_jwt_auth_validates_signature_issuer_and_audience(monkeypatch):
    monkeypatch.setenv("TUTOR_AUTH_MODE", "jwt")
    secret = "test-secret-with-at-least-32-bytes"
    monkeypatch.setenv("TUTOR_AUTH_JWT_SECRET", secret)
    monkeypatch.setenv("TUTOR_AUTH_JWT_ALGORITHMS", "HS256")
    monkeypatch.setenv("TUTOR_AUTH_ISSUER", "https://issuer.example")
    monkeypatch.setenv("TUTOR_AUTH_AUDIENCE", "adaptive-tutor")
    get_settings.cache_clear()

    token = jwt.encode(
        {
            "sub": "jwt-learner",
            "tenant_id": "tenant-jwt",
            "role": "learner",
            "iss": "https://issuer.example",
            "aud": "adaptive-tutor",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        secret,
        algorithm="HS256",
    )

    ok = client.get("/progress/jwt-learner", headers={"authorization": f"Bearer {token}"})
    denied = client.get("/progress/jwt-learner")

    assert ok.status_code == 200
    assert ok.json()["learner_id"] == "jwt-learner"
    assert denied.status_code == 401


def test_rate_limit_blocks_per_tenant_user_action(monkeypatch):
    monkeypatch.setenv("TUTOR_RATE_LIMIT_BACKEND", "memory")
    monkeypatch.setenv("TUTOR_RATE_LIMIT_SOURCE_SEARCH", "1")
    monkeypatch.setenv("TUTOR_RATE_LIMIT_WINDOW_SECONDS", "60")
    get_settings.cache_clear()
    rate_limit._limiter = None
    learner_id = f"limited-{uuid4()}"

    first = client.get("/sources/search?q=RAG", headers=_headers(learner_id))
    second = client.get("/sources/search?q=MCP", headers=_headers(learner_id))

    assert first.status_code == 200
    assert second.status_code == 429
    assert "Retry-After" in second.headers


def test_graph_resume_uses_durable_checkpoint_with_fresh_graph():
    learner_id = f"resume-{uuid4()}"
    thread_id = learner_id
    tutor_get_next_exercise_impl(learner_id, skill="RAG")

    interrupted = run_tutor_turn(learner_id, "answer: maybe", thread_id=thread_id)
    assert interrupted["needs_clarification"] is True
    assert interrupted["interrupt"]["reason"] == "ambiguous_answer"

    fresh_graph = build_tutor_graph()
    tenant, base_thread_id, config = _thread_config(learner_id, thread_id, "local")
    result = fresh_graph.invoke(
        Command(
            resume={
                "answer": "Retrieve records with vector search, ground with citations, preserve unknowns, and evaluate faithfulness."
            }
        ),
        config=config,
    )
    resumed = _format_graph_result(result, learner_id=learner_id, tenant_id=tenant, thread_id=base_thread_id)

    assert resumed["intent"] == "submit_answer"
    assert resumed["grading"]["score"] >= 0.75
    assert resumed["grading"]["mastery_update"]["evidence"]


class FakeSupabaseClient:
    def __init__(self):
        self.upserts = []
        self.rpc_calls = []

    def upsert(self, table, rows, conflict):
        self.upserts.append((table, rows, conflict))

    def get(self, table, params):
        if table == "vector_indexes":
            return [
                {
                    "built_at": "2026-06-14T00:00:00+00:00",
                    "document_count": 1,
                    "provider": "pgvector_hash_embedding",
                    "metadata": {"dimensions": 1536},
                }
            ]
        return []

    def rpc(self, function_name, payload):
        self.rpc_calls.append((function_name, payload))
        return [
            {
                "source_id": "topic:rag",
                "record_type": "topic",
                "slug": "rag",
                "title": "RAG",
                "path": "genai_research/topics/rag/topic_summary.json",
                "content": "RAG retrieves records and grounds answers with citations.",
                "metadata": {
                    "source_id": "topic:rag",
                    "record_type": "topic",
                    "title": "RAG",
                    "path": "genai_research/topics/rag/topic_summary.json",
                    "citations": ["https://example.com/rag"],
                    "last_researched_at": "2026-01-01",
                },
                "score": 0.91,
            }
        ]


def test_pgvector_adapter_builds_embeddings_and_queries_rpc(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role")
    monkeypatch.setenv("TUTOR_VECTOR_TENANT_ID", "00000000-0000-0000-0000-000000000001")
    get_settings.cache_clear()
    fake = FakeSupabaseClient()
    index = PGVectorIndex(client=fake)
    docs = [
        CorpusDocument(
            id="topic:rag",
            content="RAG retrieves records and cites evidence.",
            metadata={
                "source_id": "topic:rag",
                "record_type": "topic",
                "slug": "rag",
                "title": "RAG",
                "path": "genai_research/topics/rag/topic_summary.json",
                "citations": ["https://example.com/rag"],
            },
        )
    ]

    index.build(docs)
    embedding_rows = [rows for table, rows, _ in fake.upserts if table == "corpus_embeddings"]

    assert embedding_rows
    assert embedding_rows[0][0]["embedding"].startswith("[")

    hits = index.search("RAG citations", k=1)

    assert fake.rpc_calls[-1][0] == "match_corpus_embeddings"
    assert fake.rpc_calls[-1][1]["match_count"] == 5
    assert hits[0].source_ref.path.startswith("genai_research/")
    assert hits[0].score > 0
