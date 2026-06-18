"""Unit coverage for the graph checkpointer factory backend selection.

The sqlite path is exercised end-to-end by
``test_production_followups.test_graph_resume_uses_durable_checkpoint_with_fresh_graph``;
these tests cover the memory and postgres branches (including graceful fallback)
without requiring a live Postgres.
"""

import pytest
from langgraph.checkpoint.memory import MemorySaver

import backend.checkpoints as checkpoints
from backend.checkpoints import build_checkpointer
from backend.settings import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_memory_backend_returns_memory_saver(monkeypatch):
    monkeypatch.setenv("TUTOR_GRAPH_CHECKPOINTER_BACKEND", "memory")
    get_settings.cache_clear()

    assert isinstance(build_checkpointer(), MemorySaver)


def test_postgres_backend_without_url_falls_back_to_memory(monkeypatch):
    monkeypatch.setenv("TUTOR_GRAPH_CHECKPOINTER_BACKEND", "postgres")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TUTOR_DATABASE_URL", raising=False)
    get_settings.cache_clear()

    assert isinstance(build_checkpointer(), MemorySaver)


def test_postgres_backend_with_url_uses_postgres_saver(monkeypatch):
    monkeypatch.setenv("TUTOR_GRAPH_CHECKPOINTER_BACKEND", "postgres")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db.example:5432/postgres")
    get_settings.cache_clear()

    captured: dict[str, str] = {}
    sentinel = object()

    def fake_build(url: str):
        captured["url"] = url
        return sentinel

    monkeypatch.setattr(checkpoints, "_build_postgres_saver", fake_build)

    saver = build_checkpointer()

    assert saver is sentinel
    assert captured["url"] == "postgresql://u:p@db.example:5432/postgres"


def test_postgres_backend_with_failing_saver_falls_back_to_memory(monkeypatch):
    monkeypatch.setenv("TUTOR_GRAPH_CHECKPOINTER_BACKEND", "postgres")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db.example:5432/postgres")
    get_settings.cache_clear()

    def boom(url: str):
        raise RuntimeError("no postgres reachable")

    monkeypatch.setattr(checkpoints, "_build_postgres_saver", boom)

    assert isinstance(build_checkpointer(), MemorySaver)
